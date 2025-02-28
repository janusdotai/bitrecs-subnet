# Bitrecs Validator Setup Guide

This guide ensures the Bitrecs validator works on **Ubuntu 24.10 LTS**. Follow the steps below.

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

## 5. Validator Installation

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

If you already have a wallet, run the following on the validator:

```bash
btcli w regen_coldkeypub
btcli w regen_hotkey
```

### Register Your Validator on the Subnet

```bash
btcli subnet register --wallet.name default --wallet.hotkey default --network ws://138.197.163.127:9944
```

### Add at least 10 TAU Stake to get picked up by the Network

```bash
btcli stake add --wallet.name default --wallet.hotkey default --network ws://138.197.163.127:9944
```

## 7. Environment Configuration

Before running the validator, edit the environment file and fill in the necessary details.

## 8. Start Validator

```bash
pm2 start ./neurons/validator.py --name v -- --netuid 296 --subtensor.chain_endpoint wss://test.finney.opentensor.ai:443 --wallet.name default --wallet.hotkey default --logging.debug 
```

## 9. Final Steps

- Verify the validator is running.
- Use `pm2 list` to check running processes.

---

**Congratulations! Your Bitrecs validator is now set up and running.** 🚀

``
