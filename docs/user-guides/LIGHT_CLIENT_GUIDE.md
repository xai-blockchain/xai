# XAI Light Client Guide

Run a lightweight XAI node with minimal hardware requirements. Perfect for Raspberry Pi, mobile devices, or resource-constrained environments.

---

## Overview

A light client allows you to verify transactions and interact with the XAI blockchain without downloading the entire blockchain. Light clients use **Simplified Payment Verification (SPV)** to verify transactions using only block headers and merkle proofs.

### Benefits

- **Low Storage:** Only ~80 bytes per block header (vs. full blocks)
- **Low Bandwidth:** Downloads only relevant data
- **Fast Sync:** Syncs in minutes, not hours
- **Mobile-Friendly:** Runs on smartphones and tablets
- **Raspberry Pi Compatible:** Perfect for low-power devices

### Trade-offs

- **Trust Model:** Relies on full nodes for transaction data
- **Privacy:** May reveal addresses to connected nodes
- **Limited Functionality:** Cannot mine or validate all consensus rules

---

## SPV Verification Explained

### How It Works

1. **Download Headers:** Light client downloads only block headers (~80 bytes each)
2. **Verify PoW:** Validates proof-of-work for each header
3. **Build Chain:** Constructs header chain with cumulative difficulty
4. **Request Proofs:** Asks full nodes for merkle proofs of relevant transactions
5. **Verify Inclusion:** Confirms transactions are in blocks using merkle roots

### Security Model

SPV provides strong security guarantees:

- **PoW Protection:** Headers include proof-of-work, making forgery expensive
- **Merkle Proof:** Transactions are cryptographically proven to be in blocks
- **Checkpoint Anchors:** Hardcoded checkpoints prevent long-range attacks
- **Multiple Peers:** Queries multiple full nodes to detect inconsistencies

**Note:** SPV clients trust that the most-work chain is valid but don't verify all consensus rules.

---

## Minimum Hardware Requirements

### Recommended (Optimal Performance)

- **CPU:** 1 GHz dual-core processor
- **RAM:** 512 MB available
- **Storage:** 2 GB free space
- **Network:** 500 Kbps sustained bandwidth

### Minimum (Functional)

- **CPU:** 700 MHz single-core
- **RAM:** 256 MB available
- **Storage:** 500 MB free space
- **Network:** 256 Kbps sustained bandwidth

### Tested Devices

| Device | Status | Notes |
|--------|--------|-------|
| Raspberry Pi 4 (4GB) | ✅ Excellent | Recommended |
| Raspberry Pi 3 B+ | ✅ Good | Slight delay on initial sync |
| Raspberry Pi Zero W | ⚠️ Marginal | Slow sync, usable for wallets |
| Android (4GB+ RAM) | ✅ Good | Mobile wallet integration |
| iOS (2GB+ RAM) | ✅ Good | Mobile wallet integration |
| PC/Laptop | ✅ Excellent | Any modern device |

---

## Installation

### Standard Installation

```bash
# Clone repository
git clone https://github.com/your-org/xai.git
cd xai

# Install with light client support
pip install -e ".[light-client]"
```

### Raspberry Pi Installation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.10+
sudo apt install python3 python3-pip python3-venv -y

# Clone and install XAI
git clone https://github.com/your-org/xai.git
cd xai
python3 -m pip install -e ".[light-client]"
```

---

## Configuration

### Basic Light Client Configuration

Create `~/.xai/light-client.yaml`:

```yaml
# Light Client Configuration
mode: light_client

# Network settings
network:
  type: testnet
  max_peers: 8
  bootstrap_peers:
    - "testnet-node1.xai.io:18545"
    - "testnet-node2.xai.io:18545"

# SPV settings
spv:
  header_download_batch: 2000
  checkpoint_interval: 10000
  max_headers_in_memory: 50000
  require_merkle_proofs: true

# Storage settings
storage:
  header_db_path: "~/.xai/headers.db"
  max_db_size_mb: 100
  enable_pruning: true

# Performance settings
performance:
  sync_mode: fast
  header_verification_threads: 2
  bloom_filter_enabled: true
  bloom_false_positive_rate: 0.0001
```

### Advanced Configuration

```yaml
# Security settings
security:
  min_checkpoint_confirmations: 6
  trusted_checkpoints:
    - height: 100000
      hash: "0x123abc..."
    - height: 200000
      hash: "0x456def..."
  verify_headers_from_genesis: false  # Use checkpoints
  reject_low_difficulty_chains: true

# Privacy settings
privacy:
  bloom_filter_randomization: true
  rotate_peer_connections: true
  connection_rotation_minutes: 30
  address_query_delay_ms: 1000  # Slow down queries for privacy

# Bandwidth management
bandwidth:
  max_download_kbps: 500
  max_upload_kbps: 100
  rate_limit_enabled: true
```

---

## Running a Light Client

### Start Light Client Node

```bash
# Set environment
export XAI_NETWORK=testnet
export XAI_NODE_MODE=light_client

# Start light client
python -m xai.core.light_client

# Output:
# [INFO] Starting XAI Light Client
# [INFO] Downloading headers from bootstrap peers...
# [INFO] Synced 10000 headers (Height: 10000, Progress: 45%)
# [INFO] Light client sync complete! Current height: 22341
# [INFO] Light client ready for queries
```

### Command Line Options

```bash
# Specify config file
python -m xai.core.light_client --config ~/.xai/light-client.yaml

# Testnet mode
python -m xai.core.light_client --testnet

# Mainnet mode
python -m xai.core.light_client --mainnet

# Custom bootstrap peers
python -m xai.core.light_client --peers node1.xai.io:18545,node2.xai.io:18545

# Verbose logging
python -m xai.core.light_client --log-level DEBUG
```

---

## Using the Light Client

### Wallet Operations

Light clients support full wallet functionality:

```bash
# Check balance (SPV verified)
python src/xai/wallet/cli.py balance --address TXAI_ADDRESS --light-client

# Send transaction
python src/xai/wallet/cli.py send \
  --from TXAI_FROM \
  --to TXAI_TO \
  --amount 10.0 \
  --light-client

# Verify transaction
python src/xai/wallet/cli.py verify-tx TX_HASH --light-client
```

### Querying the Blockchain

```python
from xai.core.light_client import LightClient

# Initialize light client
client = LightClient(config_path="~/.xai/light-client.yaml")
await client.start()

# Get block header
header = await client.get_header(block_height=12345)

# Verify transaction with merkle proof
is_valid = await client.verify_transaction(
    txid="abc123...",
    merkle_proof=proof,
    block_height=12345
)

# Get address balance (with SPV verification)
balance = await client.get_balance("TXAI_ADDRESS")
```

---

## Bandwidth and Storage Requirements

### Initial Sync

| Metric | Value |
|--------|-------|
| Headers Downloaded | ~22,000 (current testnet) |
| Data Per Header | 80 bytes |
| Total Download | ~1.8 MB |
| Sync Time (500 Kbps) | ~30 seconds |

### Ongoing Usage

| Operation | Bandwidth | Frequency |
|-----------|-----------|-----------|
| New Header Download | 80 bytes | Every 2 minutes |
| Transaction Verification | 1-5 KB | Per transaction |
| Merkle Proof | 300-500 bytes | Per verification |
| Peer Discovery | 100-500 bytes | Hourly |

**Daily Bandwidth:** ~1-5 MB for typical wallet usage

### Storage Growth

| Component | Current Size | Growth Rate |
|-----------|--------------|-------------|
| Header Database | 1.8 MB | +2 MB/year |
| Bloom Filters | 100 KB | Stable |
| Transaction Cache | 500 KB | Stable (pruned) |
| Peer Database | 50 KB | Stable |

**Total Storage:** ~3 MB, growing ~2 MB/year

---

## Raspberry Pi Deployment

### Setup Script

```bash
#!/bin/bash
# xai-light-setup.sh - Raspberry Pi light client setup

set -e

echo "Installing XAI Light Client on Raspberry Pi..."

# Update system
sudo apt update
sudo apt install -y python3 python3-pip git

# Clone XAI
cd ~
git clone https://github.com/your-org/xai.git
cd xai

# Install
pip3 install -e ".[light-client]"

# Create systemd service
sudo tee /etc/systemd/system/xai-light.service > /dev/null <<EOF
[Unit]
Description=XAI Light Client
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$HOME/xai
Environment="XAI_NETWORK=testnet"
Environment="XAI_NODE_MODE=light_client"
ExecStart=/usr/bin/python3 -m xai.core.light_client
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl enable xai-light
sudo systemctl start xai-light

echo "XAI Light Client installed and running!"
echo "Check status: sudo systemctl status xai-light"
echo "View logs: sudo journalctl -u xai-light -f"
```

### Run the Setup

```bash
chmod +x xai-light-setup.sh
./xai-light-setup.sh
```

---

## Monitoring and Maintenance

### Check Light Client Status

```bash
# Via API
curl http://localhost:12001/light-client/status

# Response:
# {
#   "mode": "light_client",
#   "synced": true,
#   "height": 22341,
#   "peers": 8,
#   "headers_in_db": 22341,
#   "db_size_mb": 1.8
# }
```

### View Logs

```bash
# If running as systemd service
sudo journalctl -u xai-light -f

# If running manually
tail -f ~/.xai/logs/light-client.log
```

### Maintenance Tasks

```bash
# Compact header database (reduces size)
python -m xai.core.light_client --compact-db

# Verify header chain integrity
python -m xai.core.light_client --verify-chain

# Re-sync from checkpoint
python -m xai.core.light_client --resync-from 100000
```

---

## Troubleshooting

### Sync is slow

- Check your internet connection speed
- Reduce `header_download_batch` in config
- Try different bootstrap peers

### High memory usage

- Reduce `max_headers_in_memory` in config
- Enable pruning: `enable_pruning: true`
- Restart light client periodically

### Transaction verification fails

- Ensure you're connected to at least 3 peers
- Check that peers are on the correct chain (testnet/mainnet)
- Verify merkle proofs are being received

### Cannot connect to peers

- Check firewall settings
- Verify bootstrap peers are reachable
- Try alternative bootstrap peers

---

## Security Considerations

### SPV Security Model

**What SPV Verifies:**
- Transaction is in a block (merkle proof)
- Block has valid proof-of-work
- Block is on the most-work chain

**What SPV Doesn't Verify:**
- Transaction signatures (trusts full nodes)
- UTXO set validity
- All consensus rules

### Improving Security

1. **Use Multiple Peers:** Connect to 8+ peers for redundancy
2. **Enable Checkpoints:** Use hardcoded checkpoints for additional security
3. **Verify Critical Transactions:** For large amounts, wait for more confirmations
4. **Run Your Own Full Node:** Connect your light client to your trusted full node

---

## Next Steps

- **[Testnet Guide](TESTNET_GUIDE.md)** - Join the XAI testnet
- **[Wallet Setup](wallet-setup.md)** - Advanced wallet features
- **[API Documentation](../api/)** - Build light client applications
- **[Mining Guide](mining.md)** - Run a full node for mining

---

*Last Updated: January 2025 | XAI Version: 0.2.0*
