#!/usr/bin/env bash
#
# Example: Automated setup wizard usage with pre-configured answers
#
# This demonstrates how to use the setup wizard in scripts or CI/CD pipelines.
# For interactive use, just run: ./scripts/setup_wizard.sh
#

set -e

# Example 1: Testnet setup with default values
# (Interactive - user provides answers)
echo "Example 1: Interactive testnet setup"
echo "--------------------------------------"
echo "./scripts/setup_wizard.sh"
echo ""

# Example 2: Pre-configure via environment variables
# This sets defaults that the wizard will use
echo "Example 2: Pre-configured testnet setup"
echo "----------------------------------------"
cat << 'EOF'
export XAI_NETWORK=testnet
export XAI_NODE_MODE=full
export XAI_DATA_DIR=~/.xai
export XAI_NODE_PORT=12001
export XAI_P2P_PORT=12002
export XAI_WS_PORT=12003
./scripts/setup_wizard.sh
EOF
echo ""

# Example 3: Manual .env creation (non-interactive)
echo "Example 3: Manual .env creation"
echo "--------------------------------"
cat << 'EOF'
cat > .env << 'ENVFILE'
# Network Configuration
XAI_NETWORK=testnet
XAI_NODE_MODE=full

# Port Configuration
XAI_NODE_PORT=12001
XAI_P2P_PORT=12002
XAI_WS_PORT=12003
XAI_RPC_URL=http://localhost:12001

# Data Directory
XAI_DATA_DIR=/home/username/.xai

# Mining Configuration
XAI_MINING_ENABLED=true
XAI_MINER_ADDRESS=XAI1your_address_here

# Security Secrets (generate with: python3 -c "import secrets; print(secrets.token_hex(32))")
XAI_JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
XAI_WALLET_TRADE_PEER_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
XAI_ENCRYPTION_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
ENVFILE

chmod 600 .env
EOF
echo ""

# Example 4: Production mainnet setup
echo "Example 4: Production mainnet setup"
echo "------------------------------------"
echo "For mainnet, always use the interactive wizard to ensure"
echo "you understand all security implications."
echo ""
echo "export XAI_NETWORK=mainnet"
echo "./scripts/setup_wizard.sh"
echo ""

# Example 5: Multiple node setup
echo "Example 5: Multiple nodes on same machine"
echo "------------------------------------------"
cat << 'EOF'
# Node 1
export XAI_NODE_PORT=12001
export XAI_P2P_PORT=12002
export XAI_WS_PORT=12003
export XAI_DATA_DIR=~/.xai/node1
./scripts/setup_wizard.sh

# Node 2
export XAI_NODE_PORT=12011
export XAI_P2P_PORT=12012
export XAI_WS_PORT=12013
export XAI_DATA_DIR=~/.xai/node2
./scripts/setup_wizard.sh

# Node 3
export XAI_NODE_PORT=12021
export XAI_P2P_PORT=12022
export XAI_WS_PORT=12023
export XAI_DATA_DIR=~/.xai/node3
./scripts/setup_wizard.sh
EOF
echo ""

echo "See SETUP_WIZARD.md for complete documentation."
