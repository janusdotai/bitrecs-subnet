# Bitrecs Validator Setup Guide

This guide ensures the Bitrecs validator works on **Ubuntu 24.10 LTS**. Follow the steps below.

## 1. Installation script
Update your packages before running the install script.

```bash
sudo apt-get update && sudo apt-get upgrade -y
curl -sL https://raw.githubusercontent.com/janusdotai/bitrecs-subnet/docs/scripts/install_vali.sh | bash
```

## 2. Keys on machine and register
Put your keys on the machine, register and stake. 

## 3. Environment Configuration

Before running the validator, edit the .env environment file and fill it in to match your config specs.

## 4. Firewall Configuration
Configure the firewall using UFW. These rules allow SSH access and communication on the miner port (8091):

```bash
sudo ufw allow 22
sudo ufw allow proto tcp to 0.0.0.0/0 port 8091
sudo ufw allow proto tcp to 0.0.0.0/0 port 7779
sudo ufw enable
sudo ufw reload
```

## 5. Start Validator (No Auto-Updates)
Monitor output with `pm2 logs 0`.

```bash
pm2 start ./neurons/validator.py --name v -- \
        --netuid 122 \
        --wallet.name default --wallet.hotkey default \
        --neuron.vpermit_tao_limit 1_000_000 \
        --subtensor.network wss://entrypoint-finney.opentensor.ai:443 \
        --logging.debug \
        --r2.sync_on 

pm2 save
```

## 5.1 Start Validator (With Auto-Updates)

Use the start_validator.py script to run the auto-updater which will:

- create a pm2 process to handle updates automatically
- create a pm2 process to run the validator.py

see: [start_validator.py](/start_validator.py)

This is the recommended way for running a validator with worry free updates.