# Bitrecs Miner Setup Guide

This guide provides detailed instructions for setting up and configuring the Bitrecs miner on **Ubuntu 24.10 LTS**. The Bitrecs subnet is designed to be accessible to miners with varying computational resources, making it suitable for home enthusiasts, local mining operations, and industrial-scale farms.

For quick deployment, you can use the installation script, otherwise follow the manual guide below. Update your packages before running the install script. 
```bash
sudo apt-get update && sudo apt-get upgrade -y
curl -sL https://raw.githubusercontent.com/janusdotai/bitrecs-subnet/docs/scripts/install_miner.sh | bash
```

## 1. System Prerequisites and Network Configuration

### Initial System Updates
Begin by ensuring your system packages are current and installing the Uncomplicated Firewall (UFW) for network security:

```bash
sudo apt-get update && sudo apt-get upgrade -y
sudo apt install ufw
```

### Firewall Configuration
## UFW Firewall
Configure the firewall using UFW. These rules allow SSH access and communication on the miner port (8091):

```bash
sudo ufw allow 22
sudo ufw allow proto tcp to 0.0.0.0/0 port 8091
sudo ufw enable
sudo ufw reload
```

## 2. System Resource Configuration

### Temporary Storage
Increase the temporary directory size:

```bash
sudo mount -o remount,size=8G /tmp
```

### Python Environment Prerequisites
Install Python and pip:

```bash
sudo apt-get update && sudo apt-get upgrade -y
apt install python3-pip
sudo apt install python3.12-venv
```

## 3. Directory Structure Setup

Create a dedicated working directory for your Bittensor operations:

```bash
mkdir bt
cd bt
```

## 4. Python Virtual Environment Configuration

### Environment Creation and Activation
Create python virtual environment:

```bash
python3.12 -m venv bt_venv
source bt_venv/bin/activate
```

### Bittensor Installation
Install Bittensor:

```bash
pip3 install bittensor[torch]
```

### Persistent Environment Configuration
Configure automatic environment activation for future sessions:

```bash
echo "source /root/bt/bt_venv/bin/activate" >> ~/.bashrc
```

**System Restart Required:** Reboot to ensure all configurations take effect:
```bash
reboot now
```

## 5. Bitrecs Miner Installation

### Repository Setup
After system restart, navigate to your working directory and clone the Bitrecs subnet repository:

```bash
cd bt
git clone https://github.com/janusdotai/bitrecs-subnet.git
cd bitrecs-subnet
```

### Dependency Installation
Install all required Python packages:

```bash
pip3 install -r requirements.txt
python3 -m pip install -e .
```

### Process Management Setup
Install Node.js and PM2:

```bash
sudo apt install -y nodejs npm
sudo npm install -g pm2
```

## 6. Wallet Configuration and Subnet Registration

### New Wallet Creation
If you don't have an existing Bittensor wallet, complete the following steps:

1. **Install BTCLI:** Follow the official [Installation Guide](https://docs.bittensor.com/getting-started/install-btcli)
2. **Create Wallet Keys:** Use the [BTCLI Wallet Guide](https://docs.bittensor.com/btcli#btcli-wallet) to generate your coldkey and hotkey

### Existing Wallet Integration
For users with existing wallets, regenerate the necessary keys on your mining server:

```bash
btcli w regen_coldkeypub
btcli w regen_hotkey
```

### Subnet Registration
Register your miner on the Bitrecs testnet UID 296:

```bash
btcli subnet register --netuid 296 --network wss://test.finney.opentensor.ai:443 --wallet.name default --wallet.hotkey default
```

**Note:** Ensure your wallet.name and wallet.hotkey parameters match the names you configured during wallet creation.

## 7. Environment Configuration

### Configuration File Setup
Before initiating the miner, you must configure the environment variables in the `.env` file. 

## 8. Miner Deployment and Monitoring

### Starting the Miner Process
Launch your miner using PM2 with comprehensive logging and monitoring:

```bash
pm2 start ./neurons/miner.py --name miner -- \
        --netuid 296 \
        --subtensor.network wss://test.finney.opentensor.ai:443 \
        --wallet.name default \
        --wallet.hotkey default \
        --logging.trace \
        --llm.model openrouter/google/gemini-2.5-flash-preview-05-20
```

### Process Management and Monitoring
Utilize the following PM2 commands for ongoing miner management:

```bash
pm2 list
pm2 logs miner     
pm2 restart miner
```

## 9. Troubleshooting

### Common Troubleshooting Steps
If you encounter issues:

1. **Dependency Conflicts:** Ensure you're operating within the virtual environment
2. **Network Issues:** Verify firewall rules and port accessibility
3. **Wallet Problems:** Confirm wallet names match between registration and miner startup

---

**Setup Complete:** Your Bitrecs miner is now configured and operational on the testnet. 