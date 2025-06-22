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
    
    # Clear screen and move to top
    clear
    
    # Print logo
    echo -e "$LOGO"
    
    # Print status line
    echo -e "\n${YELLOW}Status: $status${NC}\n"
    
    # Print last 10 lines of log
    echo -e "${YELLOW}Recent Output:${NC}"
    tail -n 10 "$LOGFILE"
    
    # Print progress bar at bottom
    local term_lines=$(tput lines)
    tput cup $((term_lines-2)) 0
    printf "${YELLOW}Progress: [%-50s] %d%%${NC}" $(printf "%${progress}s" | tr ' ' '▇') $progress
}

# Function to run command and capture output
run_command() {
    local cmd="$1"
    local msg="$2"
    local progress="$3"
    
    # Update status
    update_screen "$progress" "$msg"
    
    # Run command and capture output
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

# Installation steps
run_command "apt install ufw -y" "Installing UFW..." 10
run_command "apt-get update && apt-get upgrade -y" "Updating system packages..." 20
# Firewall rules are now configured manually. See docs/running_validator.md "UFW Firewall" section.
# run_command "ufw allow 22" "Configuring firewall (SSH)..." 30
# run_command "ufw allow proto tcp to 0.0.0.0/0 port 8091" "Configuring firewall (Port 8091)..." 35
# run_command "ufw allow proto tcp to 0.0.0.0/0 port 7779" "Configuring firewall (Port 7779)..." 36
# run_command "yes | ufw enable" "Enabling firewall..." 40
# run_command "ufw reload" "Reloading firewall..." 45

# Node.js + PM2
run_command "apt install -y curl gnupg" "Installing curl & gnupg..." 50
run_command 'curl -fsSL https://deb.nodesource.com/setup_18.x | bash -' "Adding Node.js 18 repo..." 51
run_command "apt install -y nodejs" "Installing Node.js..." 52
run_command "npm install -g pm2" "Installing PM2..." 53

run_command "mount -o remount,size=8G /tmp" "Configuring temporary storage..." 55
run_command "apt install python3-pip python3.12-venv -y" "Installing Python requirements..." 60
run_command "mkdir -p \$HOME/bt && cd \$HOME/bt" "Creating working directory..." 65

# Python environment setup
run_command "python3.12 -m venv \$HOME/bt/bt_venv" "Creating Python virtual environment..." 70
run_command "source \$HOME/bt/bt_venv/bin/activate && pip3 install bittensor[torch]" "Installing Bittensor..." 80
run_command "grep -qxF 'source \$HOME/bt/bt_venv/bin/activate' ~/.bashrc || echo 'source \$HOME/bt/bt_venv/bin/activate' >> ~/.bashrc" "Configuring environment..." 85

# Validator installation
run_command "cd \$HOME/bt && rm -rf bitrecs-subnet || true" "Cleaning old installation..." 90
run_command "cd \$HOME/bt && git clone https://github.com/janusdotai/bitrecs-subnet.git" "Cloning Bitrecs repository..." 95
run_command "cd \$HOME/bt/bitrecs-subnet && source \$HOME/bt/bt_venv/bin/activate && pip3 install -r requirements.txt && python3 -m pip install -e ." "Installing Bitrecs..." 100

# Final update
update_screen 100 "Installation Complete to \$HOME/bt"

# Return to normal terminal
tput rmcup
echo -e "\n${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║         Installation Complete          ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}\n"
echo -e "${BLUE}Next steps:${NC}"
echo -e "1. Configure your wallet if you haven't already"
echo -e "2. Start the validator with your preferred configuration\n"
