# https://github.com/impel-intelligence/dippy-bittensor-subnet/blob/main/scripts/start_validator.py

"""
------------------

PM2 is required for this script. 

------------------

This script runs a validator process and automatically updates it when a new version is released.
Ideally you are in /bt/bitrecs-subnet (root path) directory when running this script.

Command-line arguments will be forwarded to validator (`neurons/validator.py`), so you can pass
them like this:    

    python ./start_validator.py --pm2_name 'sn122vali' --netuid 296 --wallet.name default --wallet.hotkey default --logging.trace --wallet.path /root/.bittensor/wallets --neuron.vpermit_tao_limit 10_000 --r2.sync_on

Auto-updates are enabled by default and will make sure that the latest version is always running
by pulling the latest version from git and upgrading python packages. This is done periodically.
Local changes may prevent the update, but they will be preserved.

The script will use the same virtual environment as the one used to run it. If you want to run
validator within virtual environment, run this auto-update script from the virtual environment.

This script will start a PM2 process using the name provided by the --pm2_name argument.

"""

import os
import sys
import time
import datetime
import argparse
import logging
import subprocess
import requests
from shlex import split
from typing import List, Dict, Any
from datetime import timedelta
from dataclasses import asdict, dataclass, field
from bitrecs.utils import constants as CONST
from bitrecs.utils.version import LocalMetadata
from dotenv import load_dotenv
load_dotenv()


log = logging.getLogger(__name__)

UPDATES_CHECK_TIME = timedelta(minutes=1)
BITRECS_PROXY_URL = os.environ.get("BITRECS_PROXY_URL").removesuffix("/")
if not BITRECS_PROXY_URL:
    raise ValueError("BITRECS_PROXY_URL environment variable is not set.")


@dataclass
class ValidatorHealthReport:
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    hot_key: str = field(default_factory=str)
    val_uid: int = field(default=0)
    step: str = field(default_factory=str)
    commit_hash: str = field(default_factory=str)
    version: str = field(default_factory=str)
    requests_total: int = field(default=0)
    requests_recent_total: int = field(default=0)

    def to_dict(self) -> Dict[str, Any]:
        """Convert dataclass to dictionary for JSON serialization"""
        return asdict(self)
    


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



def _remote_log(payload: Dict[str, Any]):

    final_payload = {
        "signature": "x",
        "payload": payload,
        "commit": "x",
        "btversion": "x",
        "uid": "0",
        "hotkey": "x",
        "coldkey": "x",
    }

    log.info(f"remote logging with payload {final_payload}")
    return

    event_report_endpoint = f"{BITRECS_PROXY_URL}/validator/health_report"
    try:
        response = requests.post(event_report_endpoint, json=final_payload)
        response.raise_for_status()  # Raise an exception for HTTP errors
        log.info(f"successfully sent event_report with payload {final_payload}")
    except Exception as e:
        log.error(f"could not remote log: {e}. This error is ok to ignore if you are a validator")


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
        _remote_log({"error": str(exc), "message": "Failed to pull from git, reverting"})

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
    This will check for updates every `UPDATES_CHECK_TIME` and update the validator
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
            _remote_log(
                {
                    "current_version": str(current_version),
                    "latest_version": str(latest_version),
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
                except Exception as e:
                    log.error(f"Failed to create payload: {e}")
                    payload["error"] = str(e)
                finally:
                    _remote_log(payload)
                stop_validator_process(validator)
                validator = start_validator_process(pm2_name, args, current_version)
                current_version = latest_version

            time.sleep(UPDATES_CHECK_TIME.total_seconds())

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
