# https://github.com/impel-intelligence/dippy-bittensor-subnet/blob/main/scripts/start_validator.py

"""
------------------
Validator Auto-Updater Script

PM2 is required for this script. 

------------------

This script runs a validator process and automatically updates it when a new version is released.
Ideally you are in /bt/bitrecs-subnet (root path) directory when running this script and in the correct virtual environment.
Command-line arguments will be forwarded to validator (`neurons/validator.py`)

1) SUGGESTED (Set it and forget it) - Run this script with PM2

pm2 start --name sn122-vali-updater --interpreter python ./start_validator.py -- --pm2_name 'sn122vali' --netuid 296 --wallet.name default --wallet.hotkey default --logging.trace --wallet.path /root/.bittensor/wallets --neuron.vpermit_tao_limit 10_000 --r2.sync_on

You should end up with two PM2 processes running, the updater itself (sn122-vali-updater) and the actual validator (sn122vali).

2) MANUAL (Have to keep this script running) - Run this script manually (not recommended, good for debugging)

python3 ./start_validator.py --pm2_name 'sn122vali' --netuid 296 --wallet.name default --wallet.hotkey default --logging.trace --wallet.path /root/.bittensor/wallets --neuron.vpermit_tao_limit 10_000 --r2.sync_on

3) DEFAULT - (No auto update, just runs the validator in PM2)

pm2 start ./neurons/validator.py --name 'sn122vali' --  --netuid 296 --wallet.name default --wallet.hotkey default --logging.trace --wallet.path /root/.bittensor/wallets --neuron.vpermit_tao_limit 10_000 --r2.sync_on

Auto-updates are enabled by default and will make sure that the latest version is always running
by pulling the latest version from git and upgrading python packages. This is done periodically.
Local changes may prevent the update, but they will be preserved.

The script will use the same virtual environment as the one used to run it. If you want to run
validator within virtual environment, run this auto-update script from the virtual environment.

This script will start a PM2 process using the name provided by the --pm2_name argument.

You should 'pm2 save' and reboot to make sure all processes are restarted on reboot

"""

import json
import os
import sys
import time
import datetime
import argparse
import logging
import subprocess
import requests
import random
from shlex import split
from typing import List, Dict, Any
from bitrecs.utils import constants as CONST
from bitrecs.utils.version import LocalMetadata
from bitrecs import __version__ as this_version
from dotenv import load_dotenv
load_dotenv()

log = logging.getLogger(__name__)

BITRECS_PROXY_URL = os.environ.get("BITRECS_PROXY_URL").removesuffix("/")
if not BITRECS_PROXY_URL:
    raise ValueError("BITRECS_PROXY_URL environment variable is not set.")
NETWORK = os.environ.get("NETWORK", "").strip().lower()


def read_node_info() -> Dict[str, Any]:
    node_info_file = 'node_info.json'
    full_path = os.path.join(CONST.ROOT_DIR, node_info_file)
    if not os.path.exists(full_path):
        log.warning(f"Node info file does not exist at {full_path}")
        return {}
    try:
        with open(node_info_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        log.warning(f"Node info file not found: {node_info_file}")
        return {}
    except json.JSONDecodeError as e:
        log.error(f"Error parsing node info JSON: {e}")
        return {}
    except Exception as e:
        log.error(f"Error reading node info: {e}")
        return {}


def get_version() -> str:
    v = LocalMetadata.local_metadata()
    return v.head


def start_validator_process(pm2_name: str, args: List[str], current_version: str = "0") -> subprocess.Popen:
    """
    Spawn a new python process running neurons.validator.
    `sys.executable` ensures thet the same python interpreter is used as the one
    used to run this auto-updater.
    """
    assert sys.executable, "Failed to get python executable"

    log.info("Starting validator process with pm2, name: %s", pm2_name)
    process = subprocess.Popen(
        (
            "pm2",
            "start",
            sys.executable,
            "--name",
            pm2_name,
            "--",
            "-m",
            "neurons.validator",
            *args,
        ),
        cwd=CONST.ROOT_DIR,
    )
    process.pm2_name = pm2_name
    log.info("Started validator process with pm2, name: %s, version: %s", pm2_name, current_version)

    return process



def post_node_report(payload: Dict[str, Any]) -> bool:
    """Send node info"""

    if NETWORK != "mainnet":
        log.info("Skipping node report for testnet.")
        return False
    
    node = read_node_info()
    post_data = {
        "node": node,
        "payload": payload        
    }
    log.info(f"Sending node report with payload: {post_data}")

    node_report_endpoint = f"{BITRECS_PROXY_URL}/node/report"
    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ.get('BITRECS_API_KEY')}",            
            'User-Agent': f'Bitrecs-Node/{this_version}'
        }        
        response = requests.post(
            node_report_endpoint,
            json=post_data,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()
        log.info(f"Successfully sent node report: {response.status_code}")
        return True
        
    except Exception as e:
        log.error(f"Failed to send node report: {e}")


def stop_validator_process(process: subprocess.Popen) -> None:
    """Stop the validator process"""
    subprocess.run(("pm2", "delete", process.pm2_name), cwd=CONST.ROOT_DIR, check=True)


def pull_latest_version() -> None:
    """
    Pull the latest version from git.
    This uses `git pull --rebase`, so if any changes were made to the local repository,
    this will try to apply them on top of origin's changes. This is intentional, as we
    don't want to overwrite any local changes. However, if there are any conflicts,
    this will abort the rebase and return to the original state.
    The conflicts are expected to happen rarely since validator is expected
    to be used as-is.
    """
    try:
        subprocess.run(split("git pull --rebase --autostash"), check=True, cwd=CONST.ROOT_DIR)
    except subprocess.CalledProcessError as exc:
        log.error("Failed to pull, reverting: %s", exc)
        post_node_report({"error": str(exc), "message": "Failed to pull from git, reverting"})

        subprocess.run(split("git rebase --abort"), check=True, cwd=CONST.ROOT_DIR)


def upgrade_packages() -> None:
    """
    Upgrade python packages by running `pip install --upgrade -r requirements.txt`.
    Notice: this won't work if some package in `requirements.txt` is downgraded.
    Ignored as this is unlikely to happen.
    """
    log.info("Upgrading requirements")
    try:
        subprocess.run(
            split(f"{sys.executable} -m pip install -r requirements.txt"),
            check=True,
            cwd=CONST.ROOT_DIR,
        )
    except subprocess.CalledProcessError as exc:
        log.error("Failed to upgrade packages, proceeding anyway. %s", exc)

    log.info("Upgrading packages")
    try:
        subprocess.run(
            split(f"{sys.executable} -m pip install -e ."),
            check=True,
            cwd=CONST.ROOT_DIR,
        )
    except subprocess.CalledProcessError as exc:
        log.error("Failed to upgrade packages, proceeding anyway. %s", exc)


def main(pm2_name: str, args: List[str]) -> None:
    """
    Run the validator process and automatically update it when a new version is released.
    This will check for updates every few minutes.
    if a new version is available. Update is performed as simple `git pull --rebase`.
    """

    validator = start_validator_process(pm2_name, args)
    current_version = get_version()

    log.info("Current version: %s", current_version)

    try:
        while True:
            pull_latest_version()
            latest_version = get_version()
            log.info("Latest version: %s", latest_version)
            post_node_report(
                {
                    "current_version": str(current_version),
                    "latest_version": str(latest_version),
                    "time": str(datetime.datetime.now(datetime.timezone.utc)),
                    "message": "start_validator_check_update",
                }
            )

            if latest_version != current_version:
                log.info(
                    "Upgraded to latest version: %s -> %s",
                    current_version,
                    latest_version,
                )
                upgrade_packages()
                current_version = get_version()
                payload = {}
                try:
                    payload["current_version"] = str(current_version)
                    payload["latest_version"] = str(latest_version)
                    payload["time"] = str(datetime.datetime.now(datetime.timezone.utc))
                    payload["message"] = "end_validator_check_update"
                except Exception as e:
                    log.error(f"Failed to create payload: {e}")
                    payload["error"] = str(e)
                finally:
                    post_node_report(payload)
                stop_validator_process(validator)
                validator = start_validator_process(pm2_name, args, current_version)
                current_version = latest_version

            sleep = random.choice([60, 90, 120, 150, 180, 240, 300])
            log.info(f"Sleeping for {sleep} seconds before checking for updates again.")
            time.sleep(sleep)

    finally:
        stop_validator_process(validator)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    parser = argparse.ArgumentParser(
        description="Automatically update and restart the validator process when a new version is released.",
        epilog="Example usage: python ./start_validator.py --pm2_name 'sn122vali' --wallet_name 'wallet1' --wallet_hotkey 'key123'",
    )

    parser.add_argument("--pm2_name", default="sn122val", help="Name of the PM2 process.")

    flags, extra_args = parser.parse_known_args()

    main(flags.pm2_name, extra_args)
