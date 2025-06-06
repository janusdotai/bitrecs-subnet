# Bitrecs Miner Setup Guide

This guide ensures the Bitrecs miner works on Ubuntu 24.10 LTS. Bitrecs miners don’t have minimum compute requirements, making our subnet attractive to home enthusiasts, local miners, and industry farms.

## 1. Run installer script 
```bash
curl -sL https://raw.githubusercontent.com/janusdotai/bitrecs-subnet/docs/scripts/install_miner.sh | bash
```

## 1. Wallet Setup

If you do not have a **Bittensor coldkey**:

1. Install btcli: [Installation Guide](https://docs.bittensor.com/getting-started/install-btcli)
2. Create coldkey and hotkey: [btcli wallet guide](https://docs.bittensor.com/btcli#btcli-wallet)

If you already have a wallet, run the following on the miner:

```bash
btcli w regen_coldkeypub
btcli w regen_hotkey
```

## 2. Register Your Miner on the Subnet (Testnet 296)

Make sure wallet.name and wallet.hotkey match the names you set above.

```bash
btcli subnet register --netuid 296 --network wss://test.finney.opentensor.ai:443 --wallet.name default --wallet.hotkey default
```

## 3. Environment Configuration

Before running the miner, edit the .env environment file to match your miner specs. 

## 4. Start Miner

You can check logs with pm2 ls to see processes and pm2 logs 0 to monitor output

```bash
pm2 start ./neurons/miner.py --name m -- \
        --netuid 296 \
        --subtensor.network wss://test.finney.opentensor.ai:443 \
        --wallet.name default \
        --wallet.hotkey default \
        --logging.trace \
        --llm.model openrouter/quasar-alpha
```


