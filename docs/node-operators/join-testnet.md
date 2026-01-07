# Join XAI Testnet

Connect your node to the XAI testnet network.

## Quick Start

```bash
curl -sL https://raw.githubusercontent.com/xai-blockchain/xai/main/scripts/install-testnet.sh | bash
```

## Manual Installation

### Prerequisites

- Ubuntu 22.04+ or macOS
- Python 3.10+
- 4 CPU / 8GB RAM / 100GB SSD
- See [Hardware Requirements](../getting-started/hardware-requirements.md)

### Step 1: Install XAI

```bash
git clone https://github.com/xai-blockchain/xai.git
cd xai
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

### Step 2: Configure for Testnet

```bash
# Copy example configuration
cp .env.example .env

# Set testnet network
echo "XAI_NETWORK=testnet" >> .env
```

### Step 3: Download Genesis File

```bash
curl -sL https://raw.githubusercontent.com/xai-blockchain/xai/main/genesis/genesis.json \
  > genesis.json
```

### Step 4: Start Node

```bash
# Start with default settings
python -m xai.core.node \
  --host 0.0.0.0 \
  --port 8545 \
  --p2p-port 8333 \
  --peers https://testnet-rpc.xaiblockchain.com

# Or use the CLI
xai-node --testnet
```

### Step 5: Verify Sync

```bash
# Check node status
curl -s http://localhost:8545/stats | jq

# Watch sync progress
watch -n 5 'curl -s http://localhost:8545/stats | jq ".chain_height"'
```

## Public Endpoints

| Service | URL |
|---------|-----|
| JSON-RPC | https://testnet-rpc.xaiblockchain.com |
| REST API | https://testnet-api.xaiblockchain.com |
| WebSocket | wss://testnet-ws.xaiblockchain.com |
| Explorer | https://testnet-explorer.xaiblockchain.com |
| Faucet | https://testnet-faucet.xaiblockchain.com |
| Monitoring | https://monitoring.xaiblockchain.com |

## Chain Information

| Parameter | Value |
|-----------|-------|
| Chain ID | xai-testnet-1 |
| Network | testnet |
| Native Token | XAI |
| Block Time | ~10 seconds |
| Python Version | 3.10+ |

## Get Testnet Tokens

Visit the faucet: https://testnet-faucet.xaiblockchain.com

Or use the CLI:

```bash
xai-wallet request-faucet --address YOUR_ADDRESS
```

Limits: 10 XAI per request, 24-hour cooldown.

## Running as a Service

Create a systemd service for automatic startup:

```bash
sudo tee /etc/systemd/system/xai.service > /dev/null <<EOF
[Unit]
Description=XAI Node
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$HOME/xai
Environment=PYTHONUNBUFFERED=1
Environment=XAI_NETWORK=testnet
ExecStart=$HOME/xai/venv/bin/python -m xai.core.node --host 0.0.0.0 --port 8545 --p2p-port 8333
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable xai
sudo systemctl start xai
```

## Useful Commands

```bash
# Check sync status
curl -s http://localhost:8545/stats | jq

# Get block height
curl -s http://localhost:8545/stats | jq -r '.chain_height'

# Check peers
curl -s http://localhost:8545/peers | jq

# View logs (systemd)
sudo journalctl -u xai -f

# Restart node
sudo systemctl restart xai
```

## Checkpoint Sync (Fast)

For faster sync, download a recent checkpoint:

```bash
# Stop node
sudo systemctl stop xai

# Download checkpoint
curl -sL https://artifacts.xaiblockchain.com/snapshots/latest.tar.gz \
  | tar -xzf - -C ~/xai/data/

# Start node
sudo systemctl start xai
```

## Troubleshooting

See [Troubleshooting Guide](../troubleshooting/common-issues.md) for solutions to common problems.
