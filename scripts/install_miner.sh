
#!/bin/bash

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Logs
LOGFILE=$(mktemp)
OUTPUTFILE=$(mktemp)
trap 'rm -f $LOGFILE $OUTPUTFILE; tput cnorm; tput rmcup' EXIT

# Fullscreen mode
tput smcup
tput civis

# Logo
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

# Update screen display
update_screen() {
    local progress=$1
    local status=$2
    clear
    echo -e "$LOGO"
    echo -e "\n${YELLOW}Status: $status${NC}\n"
    echo -e "${YELLOW}Recent Output:${NC}"
    tail -n 10 "$LOGFILE"
    local term_lines=$(tput lines)
    tput cup $((term_lines-2)) 0
    printf "${YELLOW}Progress: [%-50s] %d%%${NC}" "$(printf "%${progress}s" | tr ' ' '▇')" "$progress"
}

# Run command with logging and progress display
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

# Must be root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run as root (use sudo)${NC}"
    exit 1
fi

# Swap
run_command "fallocate -l 4G /swapfile" "Creating swap file..." 5
run_command "chmod 600 /swapfile" "Setting swap file permissions..." 6
run_command "mkswap /swapfile" "Formatting swap file..." 7
run_command "swapon /swapfile" "Enabling swap file..." 8
run_command "grep -q '/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab" "Persisting swap file..." 9

# Firewall
run_command "apt install ufw -y" "Installing UFW..." 10
run_command "apt-get update && apt-get upgrade -y" "Updating system packages..." 20
run_command "ufw allow 22" "Allowing SSH (port 22)..." 30
run_command "ufw allow proto tcp to 0.0.0.0/0 port 8091" "Allowing port 8091..." 35
run_command "yes | ufw enable" "Enabling UFW..." 40
run_command "ufw reload" "Reloading firewall..." 45

# Node.js & PM2
run_command "apt install -y curl gnupg" "Installing curl and gnupg..." 50
run_command 'curl -fsSL https://deb.nodesource.com/setup_18.x | bash -' "Adding Node.js 18 repo..." 51
run_command "apt install -y nodejs" "Installing Node.js..." 52
run_command "npm install -g pm2" "Installing PM2..." 53

# Python setup
run_command "apt install python3-pip python3.12-venv -y" "Installing Python and venv..." 60
run_command "python3.12 -m venv \$HOME/bt/bt_venv" "Creating virtual environment..." 70
run_command "source \$HOME/bt/bt_venv/bin/activate && pip install bittensor[torch]" "Installing Bittensor..." 80

# Optional btcli if needed (leave out if repo handles it)
# run_command "source \$HOME/bt/bt_venv/bin/activate && pip install btcli" "Installing btcli..." 81

run_command "grep -qxF 'source \$HOME/bt/bt_venv/bin/activate' ~/.bashrc || echo 'source \$HOME/bt/bt_venv/bin/activate' >> ~/.bashrc" "Adding venv activation to .bashrc..." 82

# Clone + install Bitrecs
run_command "mkdir -p \$HOME/bt && cd \$HOME/bt" "Creating working directory..." 90
run_command "cd \$HOME/bt && rm -rf bitrecs-subnet || true" "Cleaning previous repo..." 91
run_command "cd \$HOME/bt && git clone https://github.com/janusdotai/bitrecs-subnet.git" "Cloning Bitrecs repo..." 95
run_command "cd \$HOME/bt/bitrecs-subnet && source \$HOME/bt/bt_venv/bin/activate && pip install -r requirements.txt && pip install -e ." "Installing Bitrecs from source..." 100

# Final message
update_screen 100 "Installation Complete! 🚀"
tput rmcup
echo -e "\n${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║       Installation Complete! 🚀         ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}\n"
echo -e "${BLUE}Next steps:${NC}"
echo -e "1. Your Python venv is auto-activated in new terminals"
echo -e "2. Run ${YELLOW}btcli --help${NC} to get started"
echo -e "3. cd ~/bt/bitrecs-subnet to view the miner repo\n"

