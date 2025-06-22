#!/bin/bash


GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

LOGFILE=$(mktemp)
OUTPUTFILE=$(mktemp)
trap 'rm -f $LOGFILE $OUTPUTFILE; tput cnorm; tput rmcup' EXIT

tput smcup
tput civis

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

if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run as root (use sudo)${NC}"
    exit 1
fi

# 1. Create swap
run_command "fallocate -l 4G /swapfile" "Creating swap file..." 5
run_command "chmod 600 /swapfile" "Setting swap file permissions..." 6
run_command "mkswap /swapfile" "Formatting swap file..." 7
run_command "swapon /swapfile" "Enabling swap file..." 8
run_command "grep -q '/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab" "Persisting swap file..." 9

# 2. Firewall
# Firewall rules are now configured manually. See docs/running_miner.md "UFW Firewall" section.
run_command "apt install ufw -y" "Installing UFW..." 10
run_command "apt-get update && apt-get upgrade -y" "Updating system packages..." 20
# run_command "ufw allow 22" "Allowing SSH..." 30
# run_command "ufw allow proto tcp to 0.0.0.0/0 port 8091" "Allowing port 8091..." 35
# run_command "yes | ufw enable" "Enabling firewall..." 40
# run_command "ufw reload" "Reloading firewall..." 45

# 3. Clean up for space
run_command "apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* ~/.cache/pip" "Freeing up disk space..." 46

# 4. Node.js + PM2
run_command "apt install -y curl gnupg" "Installing curl & gnupg..." 50
run_command 'curl -fsSL https://deb.nodesource.com/setup_18.x | bash -' "Adding Node.js 18 repo..." 51
run_command "apt install -y nodejs" "Installing Node.js..." 52
run_command "npm install -g pm2" "Installing PM2..." 53

# 5. Python venv
run_command "apt install -y python3-pip python3.12-venv" "Installing Python & venv..." 60
run_command "mkdir -p \$HOME/tmp" "Preparing pip temp dir..." 61
run_command "python3.12 -m venv \$HOME/bt/bt_venv" "Creating venv..." 70

# 6. Install Bittensor carefully
run_command "source \$HOME/bt/bt_venv/bin/activate && TMPDIR=\$HOME/tmp pip install --no-cache-dir bittensor[torch]" "Installing Bittensor[torch] safely..." 80

# 7. Setup environment auto-activation
run_command "grep -qxF 'source \$HOME/bt/bt_venv/bin/activate' ~/.bashrc || echo 'source \$HOME/bt/bt_venv/bin/activate' >> ~/.bashrc" "Adding venv to bashrc..." 81

# 8. Clone and install Bitrecs repo
run_command "mkdir -p \$HOME/bt && cd \$HOME/bt && rm -rf bitrecs-subnet || true" "Preparing repo..." 90
run_command "cd \$HOME/bt && git clone https://github.com/janusdotai/bitrecs-subnet.git" "Cloning Bitrecs..." 91
run_command "cd \$HOME/bt/bitrecs-subnet && source \$HOME/bt/bt_venv/bin/activate && pip install -r requirements.txt && pip install -e ." "Installing Bitrecs with pip -e ..." 100

# Done
update_screen 100 "Installation Complete!"
tput rmcup
echo -e "\n${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║        Installation Complete           ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}\n"
echo -e "✔️  Repo at: ${YELLOW}~/bt/bitrecs-subnet${NC}"
echo -e "💡 ${YELLOW}To use your environment, please open a new terminal (re-ssh) ${NC}"
echo -e "   Your Python venv will activate automatically."
echo -e "   Touch .env and fill out the values."
echo -e "   Then run: ${GREEN}btcli --help${NC} or ${GREEN}cd ~/bt/bitrecs-subnet${NC} to get started.\n"
