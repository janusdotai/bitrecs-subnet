# Bitrecs Miner Setup Guide

This guide ensures the Bitrecs miner works on **Ubuntu 24.10 LTS**. Follow the steps below.

## 0. Run installer script which configures networking and python packages 
```bash
curl -sL https://raw.githubusercontent.com/janusdotai/bitrecs-subnet/docs/scripts/install_miner.sh | bash
```

## 1. Wallet Setup + Subnet Registration

If you do not have a **Bittensor coldkey**:

1. Install btcli: [Installation Guide](https://docs.bittensor.com/getting-started/install-btcli)
2. Create coldkey and hotkey: [BTCLI Wallet Guide](https://docs.bittensor.com/btcli#btcli-wallet)

If you already have a wallet, run the following on the miner (note: we recommend creating your wallet on a separate machine):

```bash
btcli w regen_coldkeypub
btcli w regen_hotkey
```

## 2. Register Your Miner on the Subnet (Testnet 296)

```bash
btcli subnet register --netuid 296 --network wss://test.finney.opentensor.ai:443 --wallet.name default --wallet.hotkey default
```

## 3. Environment Configuration

Before running the miner, edit the environment file (.env) and fill in the necessary details.

## 4. Start Miner

```bash
pm2 start ./neurons/miner.py --name m -- --netuid 296 --subtensor.network  wss://test.finney.opentensor.ai:443 --wallet.name default --wallet.hotkey default --logging.trace --llm.model openrouter/quasar-alpha
```

## 5. Final Steps

- Verify the miner and validator are running.
- Use `pm2 list` to check running processes and `pm2 logs 0` to check logs of process 0.



