#!/bin/bash

# Colors for pretty output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Temp files for output control
LOGFILE=$(mktemp)
OUTPUTFILE=$(mktemp)

# Cleanup on exit
trap 'rm -f $LOGFILE $OUTPUTFILE; tput cnorm; tput rmcup' EXIT

# Save current screen and switch to alternate screen buffer
tput smcup
tput civis  # Hide cursor

# The BITRECS logo
LOGO="${BLUE}
 ▄▄▄▄    ██▓▄▄▄█████▓ ██▀███  ▓█████  ▄████▄    ██████ 
▓█████▄ ▓██▒▓  ██▒ ▓▒▓██ ▒ ██▒▓█   ▀ ▒██▀ ▀█  ▒██    ▒ 
▒██▒ ▄██▒██▒▒ ▓██░ ▒░▓██ ░▄█ ▒▒███   ▒▓█    ▄ ░ ▓██▄   
▒██░█▀  ░██░░ ▓██▓ ░ ▒██▀▀█▄  ▒▓█  ▄ ▒▓▓▄ ▄██▒  ▒   ██▒
░▓█  ▀█▓░██░  ▒██▒ ░ ░██▓ ▒██▒░▒████▒▒ ▓███▀ ░▒██████▒▒
░▒▓███▀▒░▓    ▒ ░░   ░ ▒▓ ░▒▓░░░ ▒░ ░░ ░▒ ▒  ░▒ ▒▓▒ ▒ ░
▒░▒   ░  ▒ ░    ░      ░▒ ░ ▒░ ░ ░  ░  ░  ▒   ░ ░▒  ░ ░
 ░    ░  ▒ ░  ░        ░░   ░    ░   ░        ░  ░  ░  
 ░       ░              ░        ░  ░ ░ ░            ░  
      ░                                ░                 ${NC}"

# Function to update the screen
update_screen() {
    local progress=$1
    local status=$2
    
    clear
    echo -e "$LOGO"
    echo -e "\n${YELLOW}Status: $status${NC}\n"
    echo -e "${YELLOW}Recent Output:${NC}"
    tail -n 10 "$LOGFILE"
    
    local term_lines
    term_lines=$(tput lines)
    tput cup $((term_lines-2)) 0
    printf "${YELLOW}Progress: [%-50s] %d%%${NC}" "$(printf "%${progress}s" | tr ' ' '▇')" "$progress"
}

# Function to run command and capture output
run_command() {
    local cmd="$1"
    local msg="$2"
    local progress="$3"
    
    update_screen "$progress" "$msg"
    
    {
        eval "$cmd" 2>&1 | while IFS= read -r line; do
            echo "$line" >> "$LOGFILE"
            update_screen "$progress" "$msg"
        done
    } || {
        echo "Error executing: $cmd" >> "$LOGFILE"
        update_screen "$progress" "ERROR: $msg"
        exit 1
    }
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run as root (use sudo)${NC}"
    exit 1
fi

# Create swap file and persist it
run_command "fallocate -l 4G /swapfile" "Creating swap file..." 5
run_command "chmod 600 /swapfile" "Setting swap file permissions..." 6
run_command "mkswap /swapfile" "Formatting swap file..." 7
run_command "swapon /swapfile" "Enabling swap file..." 8
run_command "grep -q '/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab" "Persisting swap file..." 9

# Installation steps
run_command "apt install ufw -y" "Installing UFW..." 10
run_command "apt-get update && apt-get upgrade -y" "Updating system packages..." 20
run_command "ufw allow 22" "Configuring firewall (SSH)..." 30
run_command "ufw allow proto tcp to 0.0.0.0/0 port 8091" "Configuring firewall (Port 8091)..." 35
run_command "yes | ufw enable" "Enabling firewall..." 40
run_command "ufw reload" "Reloading firewall..." 45

run_command "mount -o remount,size=8G /tmp" "Configuring temporary storage..." 50
run_command "apt install python3-pip python3.12-venv -y" "Installing Python requirements..." 60

run_command "mkdir -p $HOME/bt && cd $HOME/bt" "Creating working directory..." 65

# Python environment setup
run_command "python3.12 -m venv $HOME/bt/bt_venv" "Creating Python virtual environment..." 70
run_command "source $HOME/bt/bt_venv/bin/activate && pip3 install bittensor[torch]" "Installing Bittensor..." 80
run_command "echo 'source \$HOME/bt/bt_venv/bin/activate' >> ~/.bashrc" "Configuring environment..." 85

# Miner installation
run_command "cd $HOME/bt && rm -rf bitrecs-subnet || true" "Cleaning old installation..." 90
run_command "cd $HOME/bt && git clone https://github.com/janusdotai/bitrecs-subnet.git" "Cloning Bitrecs repository..." 95
run_command "cd $HOME/bt/bitrecs-subnet && pip3 install -r requirements.txt && python3 -m pip install -e ." "Installing Bitrecs..." 100

# Final update
update_screen 100 "Installation Complete! 🚀"

# Return to normal terminal
tput rmcup
echo -e "\n${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║       Installation Complete! 🚀         ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}\n"
echo -e "${BLUE}Next steps:${NC}"
echo -e "1. Configure your wallet if you haven't already"
echo -e "2. Start the miner with your preferred configuration\n"

