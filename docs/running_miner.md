# Bitrecs Miner Setup Guide

This guide ensures the Bitrecs miner works on **Ubuntu 24.10 LTS**. Follow the steps below.

Feel free to use scripts/install_miner.sh which is the same as below and can be curl'd as

```bash
curl -sL https://raw.githubusercontent.com/janusdotai/bitrecs-subnet/docs/scripts/install_miner.sh | bash
```

## 1. Networking Setup

```bash
sudo apt install ufw
sudo apt-get update && sudo apt-get upgrade -y
ufw allow 22
ufw allow proto tcp to 0.0.0.0/0 port 8091
ufw enable
ufw reload
```

## 2. Server Setup

```bash
sudo mount -o remount,size=8G /tmp
sudo apt-get update && sudo apt-get upgrade -y
apt install python3-pip
sudo apt install python3.12-venv
```

## 3. Create Working Directory

```bash
mkdir bt
cd bt
```

## 4. Python Environment Setup

```bash
python3.12 -m venv bt_venv
source bt_venv/bin/activate
pip3 install bittensor[torch]
echo "source /root/bt/bt_venv/bin/activate" >> ~/.bashrc
reboot now
```

## 5. Miner Installation

```bash
sudo apt-get update && sudo apt-get upgrade -y
cd /bt
git clone https://github.com/janusdotai/bitrecs-subnet.git
cd bitrecs-subnet
pip3 install -r requirements.txt
python3 -m pip install -e .
sudo apt install -y nodejs npm
sudo npm install -g pm2
```

## 6. Wallet Setup + Subnet Registration

If you do not have a **Bittensor coldkey**:

1. Install btcli: [Installation Guide](https://docs.bittensor.com/getting-started/install-btcli)
2. Create coldkey and hotkey: [BTCLI Wallet Guide](https://docs.bittensor.com/btcli#btcli-wallet)

If you already have a wallet, run the following on the miner:

```bash
btcli w regen_coldkeypub
btcli w regen_hotkey
```

### Register Your Miner on the Subnet (Testnet 296)

```bash
btcli subnet register --netuid 296 --network wss://test.finney.opentensor.ai:443 --wallet.name default --wallet.hotkey default
```

## 7. Environment Configuration

Before running the miner, edit the environment file and fill in the necessary details.

## 8. Start Miner & Validator

```bash
pm2 start ./neurons/miner.py --name m -- --netuid 296 --subtensor.network  wss://test.finney.opentensor.ai:443 --wallet.name default --wallet.hotkey default --logging.trace --llm.model openrouter/quasar-alpha
```

## 9. Final Steps

- Verify the miner and validator are running.
- Use `pm2 list` to check running processes.

---

**Congratulations! Your Bitrecs miner is now set up and running.** 🚀


