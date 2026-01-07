#!/bin/bash
# XAI Testnet One-Line Installer
# Usage: curl -sL https://raw.githubusercontent.com/xai-blockchain/xai/main/scripts/install-testnet.sh | bash

set -e

# Configuration
CHAIN_ID="xai-testnet-1"
XAI_HOME="$HOME/xai"
BOOTSTRAP="https://testnet-rpc.xaiblockchain.com"
GENESIS_URL="https://raw.githubusercontent.com/xai-blockchain/xai/main/genesis/genesis.json"
REPO_URL="https://github.com/xai-blockchain/xai.git"
MIN_PYTHON_VERSION="3.10"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}╔══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     XAI Testnet Node Installer           ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"
echo ""

# Check Python version
check_python() {
    echo -e "${YELLOW}Checking Python version...${NC}"
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}Python 3 not found. Please install Python 3.10+${NC}"
        exit 1
    fi

    PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

    if [ "$MAJOR" -lt 3 ] || ([ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 10 ]); then
        echo -e "${RED}Python $PYTHON_VERSION found. Python 3.10+ required.${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Python $PYTHON_VERSION${NC}"
}

# Check dependencies
check_deps() {
    echo -e "${YELLOW}Checking dependencies...${NC}"
    for cmd in git curl; do
        if ! command -v $cmd &> /dev/null; then
            echo -e "${RED}$cmd not found. Please install it first.${NC}"
            exit 1
        fi
    done
    echo -e "${GREEN}✓ Dependencies OK${NC}"
}

# Clone or update repository
setup_repo() {
    echo -e "${YELLOW}Setting up XAI repository...${NC}"
    if [ -d "$XAI_HOME/.git" ]; then
        echo "Updating existing installation..."
        cd "$XAI_HOME"
        git fetch origin
        git reset --hard origin/main
    else
        echo "Cloning repository..."
        git clone "$REPO_URL" "$XAI_HOME"
        cd "$XAI_HOME"
    fi
    echo -e "${GREEN}✓ Repository ready${NC}"
}

# Setup virtual environment
setup_venv() {
    echo -e "${YELLOW}Setting up Python virtual environment...${NC}"
    cd "$XAI_HOME"

    if [ ! -d "venv" ]; then
        python3 -m venv venv
    fi

    source venv/bin/activate
    pip install --upgrade pip -q
    pip install -r requirements.txt -q
    pip install -e . -q
    echo -e "${GREEN}✓ Virtual environment ready${NC}"
}

# Download genesis file
setup_genesis() {
    echo -e "${YELLOW}Downloading genesis file...${NC}"
    mkdir -p "$XAI_HOME/data"
    curl -sL "$GENESIS_URL" > "$XAI_HOME/genesis.json"
    echo -e "${GREEN}✓ Genesis file downloaded${NC}"
}

# Configure environment
setup_env() {
    echo -e "${YELLOW}Configuring environment...${NC}"
    if [ ! -f "$XAI_HOME/.env" ]; then
        cp "$XAI_HOME/.env.example" "$XAI_HOME/.env" 2>/dev/null || true
    fi

    # Set testnet network
    grep -q "XAI_NETWORK=" "$XAI_HOME/.env" 2>/dev/null && \
        sed -i 's/XAI_NETWORK=.*/XAI_NETWORK=testnet/' "$XAI_HOME/.env" || \
        echo "XAI_NETWORK=testnet" >> "$XAI_HOME/.env"

    echo -e "${GREEN}✓ Environment configured${NC}"
}

# Setup systemd service
setup_service() {
    echo -e "${YELLOW}Setting up systemd service...${NC}"

    # Create service file
    sudo tee /etc/systemd/system/xai.service > /dev/null <<EOF
[Unit]
Description=XAI Node
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$XAI_HOME
Environment=PYTHONUNBUFFERED=1
Environment=XAI_NETWORK=testnet
ExecStart=$XAI_HOME/venv/bin/python -m xai.core.node --host 0.0.0.0 --port 8545 --p2p-port 8333 --peers $BOOTSTRAP
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    echo -e "${GREEN}✓ Systemd service created${NC}"
}

# Offer checkpoint download
offer_checkpoint() {
    echo ""
    echo -e "${YELLOW}Would you like to download a checkpoint for faster sync?${NC}"
    echo "This will download ~1GB but save hours of sync time."
    read -p "Download checkpoint? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Downloading checkpoint...${NC}"
        CHECKPOINT_URL="https://artifacts.xaiblockchain.com/snapshots/latest.tar.gz"
        mkdir -p "$XAI_HOME/data"
        curl -sL "$CHECKPOINT_URL" | tar -xzf - -C "$XAI_HOME/data/" 2>/dev/null || \
            echo -e "${YELLOW}Checkpoint not available, will sync from genesis${NC}"
        echo -e "${GREEN}✓ Checkpoint downloaded${NC}"
    fi
}

# Start node
start_node() {
    echo ""
    read -p "Start node now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        sudo systemctl enable xai
        sudo systemctl start xai
        echo -e "${GREEN}✓ Node started${NC}"
    fi
}

# Print summary
print_summary() {
    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║     Installation Complete!               ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"
    echo ""
    echo "Installation directory: $XAI_HOME"
    echo ""
    echo "Useful commands:"
    echo "  sudo systemctl start xai     # Start node"
    echo "  sudo systemctl stop xai      # Stop node"
    echo "  sudo systemctl status xai    # Check status"
    echo "  sudo journalctl -u xai -f    # View logs"
    echo ""
    echo "Check sync status:"
    echo "  curl -s http://localhost:8545/stats | jq"
    echo ""
    echo "Public endpoints:"
    echo "  RPC:      https://testnet-rpc.xaiblockchain.com"
    echo "  Explorer: https://testnet-explorer.xaiblockchain.com"
    echo "  Faucet:   https://testnet-faucet.xaiblockchain.com"
    echo ""
    echo "Documentation: https://github.com/xai-blockchain/xai/tree/main/docs"
    echo ""
}

# Main
main() {
    check_python
    check_deps
    setup_repo
    setup_venv
    setup_genesis
    setup_env
    setup_service
    offer_checkpoint
    start_node
    print_summary
}

main
