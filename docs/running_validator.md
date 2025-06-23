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

## 4. Start Validator
Monitor output with `pm2 logs 0`.

```bash
pm2 start ./neurons/validator.py --name v -- \
        --netuid 122 \
        --wallet.name default --wallet.hotkey default \
        --neuron.vpermit_tao_limit 1_000_000 \
        --subtensor.network wss://entrypoint-finney.opentensor.ai:443 \
        --logging.trace \
        --r2.sync_on 

```
