# XAI Lightweight Node Guide

Complete guide for running XAI on resource-constrained devices including Raspberry Pi, low-power VPS, NAS devices, and mobile platforms.

## Overview

XAI supports three node operation modes optimized for different resource constraints:
- **Light Client**: Headers-only, minimal storage and bandwidth
- **Pruned Node**: Full validation with limited history
- **Full Node**: Complete blockchain with all features

## Node Mode Comparison

| Mode | Storage | RAM | Bandwidth | Validation | Use Case |
|------|---------|-----|-----------|------------|----------|
| Light | <100MB | 256MB | ~80 bytes/block | SPV proofs | Mobile, wallets |
| Pruned | 100MB-1GB | 512MB-1GB | Full blocks | Full validation | Raspberry Pi, VPS |
| Full | 10GB+ | 2GB+ | Full blocks + history | Full validation | Validators, exchanges |

## Supported Platforms

### Raspberry Pi
- **Raspberry Pi 4 (4GB+)**: Pruned or Full node
- **Raspberry Pi 4 (2GB)**: Pruned node only
- **Raspberry Pi 3/Zero**: Light client only

### VPS/Cloud
- **1GB RAM VPS**: Pruned node
- **2GB+ RAM VPS**: Full node
- **512MB RAM**: Light client only

### NAS/Home Server
- **Synology/QNAP**: Docker-based pruned or full node
- **TrueNAS**: Docker or direct installation

### Mobile
- **Android/iOS**: Light client via mobile apps
- **Tablets**: Light client recommended

## Quick Setup

### Light Client Mode (Minimal Resources)

**Requirements**: 256MB RAM, 100MB storage, Python 3.8+

```bash
# Install XAI
pip install -e /path/to/xai

# Configure light client mode
export XAI_NODE_MODE=light
export XAI_CHECKPOINT_SYNC=1

# Start light client
python -m xai.core.node --mode light
```

**Configuration**:
```bash
# Environment variables
export XAI_NODE_MODE=light
export XAI_CHECKPOINT_SYNC=1
export XAI_NETWORK=testnet
export XAI_HOST=127.0.0.1
export XAI_PORT=18545
```

### Pruned Node Mode (Resource-Constrained)

**Requirements**: 512MB-1GB RAM, 100MB-1GB storage, Python 3.8+

```bash
# Configure pruned mode
export XAI_NODE_MODE=pruned
export XAI_PRUNE_BLOCKS=1000  # Keep last 1000 blocks
export XAI_CHECKPOINT_SYNC=1

# Start pruned node
python -m xai.core.node --mode pruned
```

**Storage Management**:
```bash
# Keep only recent blocks (saves disk space)
export XAI_PRUNE_BLOCKS=500   # Last 500 blocks (~16 hours)
export XAI_PRUNE_BLOCKS=1000  # Last 1000 blocks (~1.4 days)
export XAI_PRUNE_BLOCKS=5000  # Last 5000 blocks (~6.9 days)
```

### Full Node Mode

**Requirements**: 2GB+ RAM, 10GB+ storage, Python 3.8+

```bash
# Configure full node
export XAI_NODE_MODE=full
export XAI_CHECKPOINT_SYNC=1

# Start full node
python -m xai.core.node
```

## Platform-Specific Setup

### Raspberry Pi 4 Setup

**Requirements**:
- Raspberry Pi 4 (2GB+ RAM)
- 32GB+ microSD card (Class 10) or USB SSD
- Raspberry Pi OS Lite (64-bit recommended)
- Internet connection

**Installation**:
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3 python3-pip python3-venv git

# Clone XAI repository
cd ~
git clone https://github.com/yourusername/xai.git
cd xai

# Create virtual environment (optional)
python3 -m venv venv
source venv/bin/activate

# Install XAI
pip install -e .

# Configure for Raspberry Pi (pruned mode)
cat > ~/.xai_config << 'EOF'
export XAI_NODE_MODE=pruned
export XAI_PRUNE_BLOCKS=1000
export XAI_CHECKPOINT_SYNC=1
export XAI_NETWORK=testnet
export XAI_HOST=0.0.0.0
export XAI_PORT=18545
export XAI_RPC_PORT=18546
EOF

# Load configuration
source ~/.xai_config

# Start node
python -m xai.core.node
```

**Systemd Service** (auto-start on boot):
```bash
# Create systemd service
sudo tee /etc/systemd/system/xai-node.service > /dev/null << 'EOF'
[Unit]
Description=XAI Blockchain Node
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/xai
EnvironmentFile=/home/pi/.xai_config
ExecStart=/home/pi/xai/venv/bin/python -m xai.core.node
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl enable xai-node
sudo systemctl start xai-node

# Check status
sudo systemctl status xai-node
```

**USB SSD Boot** (recommended for better performance):
```bash
# Enable USB boot (Raspberry Pi 4 only)
sudo raspi-config
# Select: Advanced Options > Boot Order > USB Boot

# Move data directory to SSD
sudo mkdir -p /mnt/ssd/xai-data
sudo chown pi:pi /mnt/ssd/xai-data
export XAI_DATA_DIR=/mnt/ssd/xai-data
```

### Docker on Synology/QNAB NAS

**Synology DSM 7.0+**:
```bash
# Create docker-compose.yml
version: '3.8'
services:
  xai-node:
    image: xai/node:latest
    container_name: xai-node
    restart: unless-stopped
    ports:
      - "18545:18545"
      - "18546:18546"
    environment:
      - XAI_NODE_MODE=pruned
      - XAI_PRUNE_BLOCKS=1000
      - XAI_CHECKPOINT_SYNC=1
      - XAI_NETWORK=testnet
    volumes:
      - /volume1/docker/xai:/data
    command: python -m xai.core.node
```

**Deployment**:
```bash
# Via SSH to Synology
cd /volume1/docker/xai
docker-compose up -d

# View logs
docker-compose logs -f xai-node

# Stop node
docker-compose down
```

### Low-Memory VPS (1GB RAM)

**Optimization for 1GB VPS**:
```bash
# Install swap (if not present)
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# Configure pruned mode with aggressive pruning
export XAI_NODE_MODE=pruned
export XAI_PRUNE_BLOCKS=500  # Keep minimal blocks
export XAI_CHECKPOINT_SYNC=1

# Reduce peer connections
export XAI_NETWORK_MAX_PEERS=10

# Start node with memory limits
python -m xai.core.node
```

## Configuration

### Environment Variables

**Node Mode**:
```bash
XAI_NODE_MODE=light|pruned|full       # Node operation mode
XAI_PRUNE_BLOCKS=1000                 # Blocks to keep (pruned mode)
XAI_CHECKPOINT_SYNC=1                 # Enable checkpoint sync
```

**Network**:
```bash
XAI_NETWORK=testnet|mainnet           # Network type
XAI_HOST=127.0.0.1                    # Bind address
XAI_PORT=18545                        # P2P port (testnet)
XAI_RPC_PORT=18546                    # RPC port
```

**Performance**:
```bash
XAI_NETWORK_MAX_PEERS=50              # Max peer connections
XAI_NETWORK_PEER_TIMEOUT=30           # Peer timeout (seconds)
XAI_NETWORK_SYNC_INTERVAL=60          # Sync interval (seconds)
```

**Storage**:
```bash
XAI_STORAGE_DATA_DIR=./data           # Data directory
XAI_STORAGE_BACKUP_ENABLED=1          # Enable backups
XAI_STORAGE_ENABLE_COMPRESSION=1      # Compress blockchain data
```

### Configuration Files

Create `~/.xai/config.yaml`:
```yaml
# XAI Node Configuration

network:
  port: 18545
  rpc_port: 18546
  host: "0.0.0.0"
  max_peers: 20
  peer_timeout: 30
  sync_interval: 60

blockchain:
  difficulty: 2
  block_time_target: 120

storage:
  data_dir: "./data"
  enable_compression: true
  backup_enabled: false

logging:
  level: "INFO"
  enable_file_logging: true
  log_file: "logs/node.log"
```

## Performance Tuning

### Reduce Peer Connections
```bash
# Lower peer count reduces bandwidth and memory
export XAI_NETWORK_MAX_PEERS=10  # Default: 50
```

### Enable Checkpoint Sync
```bash
# Start from recent checkpoint instead of genesis
export XAI_CHECKPOINT_SYNC=1
```

### Use SSD Storage
```bash
# Move data to SSD for better I/O performance
export XAI_STORAGE_DATA_DIR=/mnt/ssd/xai-data
```

### Swap Configuration (Linux)
```bash
# Add swap for low-memory systems
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### Compression
```bash
# Enable blockchain data compression
export XAI_STORAGE_ENABLE_COMPRESSION=1
```

## Monitoring

### Check Node Status
```bash
# Via RPC API
curl http://localhost:12001/api/v2/node/status

# Check sync progress
curl http://localhost:12001/api/v2/blockchain/height
```

### Monitor Resources
```bash
# Memory usage
free -h

# Disk usage
df -h

# Process stats
top -p $(pgrep -f "xai.core.node")
```

### View Logs
```bash
# Tail logs
tail -f logs/node.log

# Search for errors
grep ERROR logs/node.log
```

## Troubleshooting

### Out of Memory Errors

**Symptoms**: Node crashes, OOM killer messages in `dmesg`

**Solutions**:
1. Switch to pruned mode with aggressive pruning:
   ```bash
   export XAI_NODE_MODE=pruned
   export XAI_PRUNE_BLOCKS=500
   ```

2. Add swap space (see Performance Tuning section)

3. Reduce peer connections:
   ```bash
   export XAI_NETWORK_MAX_PEERS=5
   ```

4. Consider light client mode for very constrained devices

### Sync Stalling

**Symptoms**: Block height not increasing, peer count low

**Solutions**:
1. Check network connectivity:
   ```bash
   curl http://localhost:12001/api/v2/node/peers
   ```

2. Enable checkpoint sync:
   ```bash
   export XAI_CHECKPOINT_SYNC=1
   ```

3. Manually add bootstrap peers (if available)

### Storage Full

**Symptoms**: "No space left on device" errors

**Solutions**:
1. Enable pruning:
   ```bash
   export XAI_NODE_MODE=pruned
   export XAI_PRUNE_BLOCKS=500
   ```

2. Enable compression:
   ```bash
   export XAI_STORAGE_ENABLE_COMPRESSION=1
   ```

3. Move data to larger disk:
   ```bash
   export XAI_STORAGE_DATA_DIR=/mnt/external/xai-data
   ```

### High CPU Usage

**Symptoms**: CPU constantly at 100%, slow sync

**Solutions**:
1. Use checkpoint sync to skip initial sync:
   ```bash
   export XAI_CHECKPOINT_SYNC=1
   ```

2. Reduce peer connections:
   ```bash
   export XAI_NETWORK_MAX_PEERS=10
   ```

3. Increase sync interval:
   ```bash
   export XAI_NETWORK_SYNC_INTERVAL=120
   ```

## Security Considerations

### Firewall Configuration
```bash
# Allow P2P port (testnet)
sudo ufw allow 18545/tcp

# Allow RPC only from localhost (default)
# Do NOT expose RPC port externally

# Check firewall status
sudo ufw status
```

### Running as Non-Root User
```bash
# Never run node as root
# Create dedicated user
sudo useradd -m -s /bin/bash xai
sudo su - xai
```

### Secure RPC Access
```bash
# Bind RPC to localhost only
export XAI_HOST=127.0.0.1

# If remote access needed, use reverse proxy with auth
# Example: nginx with basic auth
```

## Additional Resources

- [Raspberry Pi Setup Guide](RASPBERRY_PI_SETUP.md)
- [Node API Documentation](../api/README.md)
- [Getting Started Guide](getting-started.md)
- [Troubleshooting Guide](troubleshooting.md)

## Support

For issues or questions:
- GitHub Issues: https://github.com/yourusername/xai/issues
- Community Discord: [Link to Discord]
- Documentation: https://docs.xai-blockchain.org
