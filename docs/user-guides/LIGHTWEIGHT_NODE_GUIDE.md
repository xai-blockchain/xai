# XAI Lightweight Node Operator Guide

Complete guide for running XAI nodes on resource-constrained devices including Raspberry Pi, IoT devices, low-power VPS, and mobile platforms.

## Table of Contents

- [Overview](#overview)
- [Hardware Requirements](#hardware-requirements)
- [Quick Start](#quick-start)
- [Installation Methods](#installation-methods)
- [Configuration](#configuration)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)
- [Security](#security)

## Overview

XAI supports multiple node operation modes optimized for different resource constraints:

| Mode | Storage | RAM | Bandwidth | Features | Best For |
|------|---------|-----|-----------|----------|----------|
| **Light** | <100MB | 256MB | ~80 bytes/block | SPV verification | Mobile wallets, IoT |
| **Pruned** | 100MB-2GB | 512MB-1GB | Full blocks | Full validation, limited history | Raspberry Pi, VPS |
| **Full** | 10GB+ | 2GB+ | Full blocks + history | All features, snapshots | Validators, services |
| **Archival** | 50GB+ | 4GB+ | Full blocks + indices | Complete history + queries | Block explorers, analytics |

### Node Mode Features

**Light Client**:
- Downloads only block headers (80 bytes each)
- Verifies transactions using SPV (Merkle) proofs
- Minimal storage and bandwidth requirements
- Cannot validate full blocks independently
- Relies on full nodes for transaction data

**Pruned Node**:
- Full block validation and consensus participation
- Keeps only recent N blocks (configurable)
- Can archive old blocks to compressed storage
- Maintains chain headers for all blocks
- Significantly reduced storage footprint

**Full Node**:
- Complete blockchain with all blocks
- Creates periodic state snapshots for fast sync
- Can serve light clients and pruned nodes
- Full RPC API access
- Default mode for most operators

**Archival Node**:
- Never prunes any data
- Maintains additional indices (tx, address, block)
- Required for block explorers
- Historical query capabilities
- Highest resource requirements

## Hardware Requirements

### Raspberry Pi

| Model | Recommended Mode | Notes |
|-------|-----------------|-------|
| **Pi 5 (8GB)** | Full or Archival | Best performance, can run all modes |
| **Pi 4 (4GB+)** | Pruned or Full | Recommended for most users |
| **Pi 4 (2GB)** | Pruned only | Aggressive pruning recommended |
| **Pi 3/Zero** | Light only | Limited resources |

**Storage Recommendations**:
- microSD Class 10 or UHS-1 (minimum)
- USB 3.0 SSD strongly recommended for better I/O
- 32GB minimum, 64GB+ recommended

### VPS/Cloud

| RAM | Recommended Mode | Storage | Monthly Cost |
|-----|-----------------|---------|--------------|
| 512MB | Light | 10GB | $3-5 |
| 1GB | Pruned | 20GB | $5-10 |
| 2GB | Full | 50GB | $10-20 |
| 4GB+ | Archival | 100GB+ | $20-40 |

### IoT Devices

- **BeagleBone Black**: Light client only
- **Intel NUC**: Full or archival node
- **Synology/QNAP NAS**: Full node via Docker
- **Orange Pi/Rock Pi**: Similar to Raspberry Pi

## Quick Start

### Light Client (Minimal Resources)

```bash
# Install XAI
pip install -e /path/to/xai

# Configure light client
export XAI_NODE_MODE=light
export XAI_NETWORK=testnet
export XAI_API_PORT=12001

# Start node
python -m xai.core.node
```

### Pruned Node (Raspberry Pi)

```bash
# Configure pruning
export XAI_NODE_MODE=pruned
export XAI_PRUNE_MODE=blocks
export XAI_PRUNE_KEEP_BLOCKS=1000
export XAI_PRUNE_ARCHIVE=true
export XAI_NETWORK=testnet

# Start node
python -m xai.core.node
```

### Docker (Any Platform)

```bash
# Create docker-compose.yml (see Docker section)
docker-compose up -d

# View logs
docker-compose logs -f xai-node
```

## Installation Methods

### Method 1: Raspberry Pi Native Installation

#### Step 1: Prepare Raspberry Pi

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y \
    python3 python3-pip python3-venv \
    git build-essential libssl-dev libffi-dev

# Clone repository
git clone https://github.com/your-org/xai.git ~/xai
cd ~/xai
```

#### Step 2: Configure Storage (SSD Recommended)

```bash
# Check connected drives
lsblk

# Format USB SSD (WARNING: Erases data!)
sudo mkfs.ext4 /dev/sda1

# Create mount point
sudo mkdir -p /mnt/ssd
sudo mount /dev/sda1 /mnt/ssd
sudo chown -R pi:pi /mnt/ssd

# Auto-mount on boot
echo "UUID=$(sudo blkid -s UUID -o value /dev/sda1) /mnt/ssd ext4 defaults,nofail 0 2" | sudo tee -a /etc/fstab
```

#### Step 3: Install XAI

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install XAI
pip install -e .
```

#### Step 4: Configure Node

```bash
# Create configuration file
mkdir -p ~/.xai
cat > ~/.xai/.env << 'EOF'
# Node mode
XAI_NODE_MODE=pruned
XAI_PRUNE_MODE=blocks
XAI_PRUNE_KEEP_BLOCKS=1000
XAI_PRUNE_KEEP_DAYS=30
XAI_PRUNE_ARCHIVE=true
XAI_PRUNE_ARCHIVE_PATH=/mnt/ssd/xai-data/archive
XAI_PRUNE_DISK_THRESHOLD_GB=15.0
XAI_PRUNE_MIN_FINALIZED_DEPTH=100
XAI_PRUNE_KEEP_HEADERS=true

# Network
XAI_NETWORK=testnet
XAI_API_PORT=12001
XAI_P2P_PORT=12000
XAI_METRICS_PORT=12090

# Storage
XAI_DATA_DIR=/mnt/ssd/xai-data
XAI_LOG_DIR=/mnt/ssd/xai-data/logs
XAI_LOG_LEVEL=INFO

# Performance tuning
XAI_MAX_PEERS=15
XAI_P2P_SYNC_INTERVAL_SECONDS=60
XAI_CHECKPOINT_SYNC=1

# Enable Prometheus metrics
XAI_PROMETHEUS_ENABLED=1
EOF

# Load configuration
source ~/.xai/.env
```

#### Step 5: Create Systemd Service

```bash
sudo tee /etc/systemd/system/xai-node.service > /dev/null << 'EOF'
[Unit]
Description=XAI Blockchain Node
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/xai
EnvironmentFile=/home/pi/.xai/.env
ExecStart=/home/pi/xai/venv/bin/python -m xai.core.node
Restart=on-failure
RestartSec=30

# Resource limits
MemoryMax=1500M
CPUQuota=90%

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=xai-node

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable xai-node
sudo systemctl start xai-node

# Check status
sudo systemctl status xai-node
```

### Method 2: Docker Deployment (ARM64/AMD64)

#### Docker Compose for ARM64 (Raspberry Pi)

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  xai-node:
    image: xai/node:latest-arm64
    container_name: xai-node
    restart: unless-stopped
    ports:
      - "12001:12001"  # API/RPC
      - "12000:12000"  # P2P
      - "12090:12090"  # Metrics
    environment:
      # Node mode
      XAI_NODE_MODE: pruned
      XAI_PRUNE_MODE: blocks
      XAI_PRUNE_KEEP_BLOCKS: 1000
      XAI_PRUNE_ARCHIVE: "true"
      XAI_PRUNE_ARCHIVE_PATH: /data/archive

      # Network
      XAI_NETWORK: testnet
      XAI_API_PORT: 12001
      XAI_P2P_PORT: 12000

      # Storage
      XAI_DATA_DIR: /data
      XAI_LOG_DIR: /data/logs
      XAI_LOG_LEVEL: INFO

      # Performance
      XAI_MAX_PEERS: 15
      XAI_CHECKPOINT_SYNC: 1
      XAI_PROMETHEUS_ENABLED: 1
    volumes:
      - xai-data:/data
      - xai-logs:/data/logs
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:12001/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

volumes:
  xai-data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /mnt/ssd/xai-data
  xai-logs:
    driver: local
```

#### Deploy

```bash
# Start node
docker-compose up -d

# View logs
docker-compose logs -f xai-node

# Check status
docker-compose ps

# Stop node
docker-compose down
```

### Method 3: Low-Resource VPS (1GB RAM)

```bash
# Create swap space
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# Install XAI
git clone https://github.com/your-org/xai.git ~/xai
cd ~/xai
pip install -e .

# Configure for low memory
cat > ~/.xai/.env << 'EOF'
XAI_NODE_MODE=pruned
XAI_PRUNE_MODE=both
XAI_PRUNE_KEEP_BLOCKS=500
XAI_PRUNE_KEEP_DAYS=7
XAI_PRUNE_ARCHIVE=false
XAI_MAX_PEERS=8
XAI_NETWORK=testnet
XAI_CHECKPOINT_SYNC=1
EOF

# Start node
source ~/.xai/.env
python -m xai.core.node
```

## Configuration

### Pruning Modes

XAI supports multiple pruning strategies:

#### 1. Block Count Mode (Simple)

Keep only the most recent N blocks:

```bash
export XAI_PRUNE_MODE=blocks
export XAI_PRUNE_KEEP_BLOCKS=1000  # Keep last 1000 blocks
```

**Use when**: Fixed storage budget, don't care about time-based retention

#### 2. Time-Based Mode

Keep blocks from the last N days:

```bash
export XAI_PRUNE_MODE=days
export XAI_PRUNE_KEEP_DAYS=30  # Keep 30 days of blocks
```

**Use when**: Need consistent time window for compliance/auditing

#### 3. Combined Mode (Most Conservative)

Keep whichever is more blocks (most conservative):

```bash
export XAI_PRUNE_MODE=both
export XAI_PRUNE_KEEP_BLOCKS=1000
export XAI_PRUNE_KEEP_DAYS=14
```

**Use when**: Need to satisfy both constraints

#### 4. Disk Space Mode

Automatically prune when disk usage exceeds threshold:

```bash
export XAI_PRUNE_MODE=space
export XAI_PRUNE_DISK_THRESHOLD_GB=10.0  # Prune when >10GB used
```

**Use when**: Limited disk space, dynamic pruning needed

### Archive Configuration

Archive old blocks before deleting:

```bash
# Enable archiving
export XAI_PRUNE_ARCHIVE=true
export XAI_PRUNE_ARCHIVE_PATH=/mnt/ssd/xai-data/archive

# Blocks are compressed (gzip level 9) before archiving
# Typical compression: 60-80% space savings
```

**Benefits**:
- Can restore old blocks if needed
- Historical audit trail
- Compressed storage (60-80% smaller)

**Drawbacks**:
- Slightly slower pruning
- Uses disk space for archives

### Safety Settings

```bash
# Never prune blocks younger than this depth (safety buffer)
export XAI_PRUNE_MIN_FINALIZED_DEPTH=100

# Keep headers for pruned blocks (recommended)
export XAI_PRUNE_KEEP_HEADERS=true
```

### Complete Configuration Example

```bash
# ~/.xai/.env for Raspberry Pi 4 (4GB) with 32GB SSD

# Node mode
XAI_NODE_MODE=pruned

# Pruning policy
XAI_PRUNE_MODE=both
XAI_PRUNE_KEEP_BLOCKS=2000
XAI_PRUNE_KEEP_DAYS=14
XAI_PRUNE_ARCHIVE=true
XAI_PRUNE_ARCHIVE_PATH=/mnt/ssd/xai-data/archive
XAI_PRUNE_DISK_THRESHOLD_GB=20.0
XAI_PRUNE_MIN_FINALIZED_DEPTH=100
XAI_PRUNE_KEEP_HEADERS=true

# Network
XAI_NETWORK=testnet
XAI_API_PORT=12001
XAI_P2P_PORT=12000
XAI_METRICS_PORT=12090

# Storage
XAI_DATA_DIR=/mnt/ssd/xai-data
XAI_LOG_DIR=/mnt/ssd/xai-data/logs
XAI_LOG_LEVEL=INFO

# P2P tuning
XAI_MAX_PEERS=20
XAI_P2P_SYNC_INTERVAL_SECONDS=60
XAI_P2P_MAX_BANDWIDTH_IN=524288   # 512 KB/s
XAI_P2P_MAX_BANDWIDTH_OUT=524288  # 512 KB/s

# Mempool limits
XAI_MEMPOOL_MAX_SIZE=5000
XAI_MEMPOOL_MAX_PER_SENDER=50

# Performance
XAI_CHECKPOINT_SYNC=1
XAI_PROMETHEUS_ENABLED=1

# Security
XAI_API_AUTH_REQUIRED=0  # Only if behind firewall
```

### Light Client Configuration

```bash
# ~/.xai/.env for light client (mobile/IoT)

XAI_NODE_MODE=light
XAI_NETWORK=testnet
XAI_API_PORT=12001
XAI_DATA_DIR=~/.xai/data
XAI_LOG_LEVEL=WARNING
XAI_CHECKPOINT_SYNC=1

# Minimal peer connections
XAI_MAX_PEERS=5
XAI_P2P_SYNC_INTERVAL_SECONDS=120
```

## Monitoring

### Check Pruning Status

```bash
# Via API
curl http://localhost:12001/api/v2/node/pruning/status | jq

# Example response:
{
  "mode": "both",
  "enabled": true,
  "policy": {
    "retain_blocks": 2000,
    "retain_days": 14,
    "archive_enabled": true,
    "disk_threshold_gb": 20.0,
    "min_finalized_depth": 100,
    "keep_headers": true
  },
  "stats": {
    "total_blocks": 5000,
    "pruned_blocks": 2800,
    "archived_blocks": 2800,
    "headers_only_blocks": 2800,
    "disk_space_saved": 1458617344,
    "last_prune_time": 1702933845.12
  },
  "chain": {
    "total_blocks": 5000,
    "prunable_height": 2899,
    "eligible_blocks": 100,
    "disk_usage_gb": 4.2
  },
  "would_prune": true
}
```

### Monitor Node Performance

```bash
# Node status
curl http://localhost:12001/api/v2/node/status | jq

# Chain height
curl http://localhost:12001/api/v2/blockchain/height | jq

# Peer count
curl http://localhost:12001/api/v2/node/peers | jq '. | length'

# Prometheus metrics
curl http://localhost:12090/metrics
```

### System Resources

```bash
# Monitor script
cat > ~/monitor-xai.sh << 'EOF'
#!/bin/bash
echo "=== XAI Node Monitor ==="

# System
echo "Temperature: $(vcgencmd measure_temp 2>/dev/null || echo 'N/A')"
echo "Memory: $(free -h | grep Mem | awk '{print $3 "/" $2}')"
echo "Disk: $(df -h /mnt/ssd 2>/dev/null | grep -v Filesystem | awk '{print $3 "/" $2 " (" $5 ")"}')"
echo ""

# Node
HEIGHT=$(curl -s http://localhost:12001/api/v2/blockchain/height 2>/dev/null | jq -r '.height // "N/A"')
PEERS=$(curl -s http://localhost:12001/api/v2/node/peers 2>/dev/null | jq '. | length // 0')
echo "Height: $HEIGHT"
echo "Peers: $PEERS"
echo ""

# Pruning
PRUNED=$(curl -s http://localhost:12001/api/v2/node/pruning/status 2>/dev/null | jq -r '.stats.pruned_blocks // 0')
SAVED=$(curl -s http://localhost:12001/api/v2/node/pruning/status 2>/dev/null | jq -r '.stats.disk_space_saved // 0')
SAVED_MB=$((SAVED / 1024 / 1024))
echo "Pruned blocks: $PRUNED"
echo "Space saved: ${SAVED_MB}MB"
EOF

chmod +x ~/monitor-xai.sh
~/monitor-xai.sh
```

### Grafana Dashboard (Optional)

If using Prometheus metrics:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'xai-node'
    static_configs:
      - targets: ['localhost:12090']
```

Import dashboard from `docs/monitoring/grafana-dashboard.json`

## Troubleshooting

### Out of Memory

**Symptoms**: Node crashes, OOM killer messages in `dmesg`

**Solutions**:

1. **Switch to aggressive pruning**:
```bash
export XAI_PRUNE_MODE=blocks
export XAI_PRUNE_KEEP_BLOCKS=500  # More aggressive
sudo systemctl restart xai-node
```

2. **Add swap space**:
```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

3. **Reduce peer connections**:
```bash
export XAI_MAX_PEERS=8
```

4. **Switch to light client**:
```bash
export XAI_NODE_MODE=light
```

### Storage Full

**Symptoms**: "No space left on device" errors

**Solutions**:

1. **Check current usage**:
```bash
du -sh /mnt/ssd/xai-data/*
```

2. **Enable disk-based pruning**:
```bash
export XAI_PRUNE_MODE=space
export XAI_PRUNE_DISK_THRESHOLD_GB=10.0
```

3. **Manual pruning**:
```bash
# Trigger immediate pruning via API
curl -X POST http://localhost:12001/api/v2/node/pruning/prune
```

4. **Clean up archives** (if not needed):
```bash
rm -rf /mnt/ssd/xai-data/archive/*
```

### Sync Stalling

**Symptoms**: Block height not increasing

**Solutions**:

1. **Check peer connectivity**:
```bash
curl http://localhost:12001/api/v2/node/peers | jq
```

2. **Enable checkpoint sync**:
```bash
export XAI_CHECKPOINT_SYNC=1
sudo systemctl restart xai-node
```

3. **Check logs**:
```bash
sudo journalctl -u xai-node -f
```

### High CPU Usage

**Symptoms**: CPU at 100%, device overheating

**Solutions**:

1. **Reduce sync frequency**:
```bash
export XAI_P2P_SYNC_INTERVAL_SECONDS=120
```

2. **Limit CPU usage** (systemd):
```ini
# /etc/systemd/system/xai-node.service
[Service]
CPUQuota=60%
```

3. **Reduce peer count**:
```bash
export XAI_MAX_PEERS=10
```

### Pruning Not Working

**Check pruning status**:
```bash
curl http://localhost:12001/api/v2/node/pruning/status | jq
```

**Common issues**:

1. **Pruning disabled**: Check `XAI_PRUNE_MODE` is not "none"
2. **Chain too short**: Need more than `PRUNE_KEEP_BLOCKS + MIN_FINALIZED_DEPTH` blocks
3. **Threshold not met**: Disk usage below `PRUNE_DISK_THRESHOLD_GB`

**Force pruning**:
```bash
curl -X POST http://localhost:12001/api/v2/node/pruning/prune?dry_run=false
```

### Light Client Issues

**Transaction not verified**:
- Ensure you have the block header: `curl http://localhost:12001/api/v2/light/headers/<height>`
- Request SPV proof: `curl http://localhost:12001/api/v2/light/proof/<txid>`

**Header sync failed**:
- Check PoW validation in logs
- Verify connection to full nodes

## Security

### Firewall Configuration

```bash
# UFW (Ubuntu/Debian/Raspberry Pi OS)
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 12000/tcp   # P2P
sudo ufw deny 12001/tcp    # API (localhost only)
sudo ufw enable

# Check status
sudo ufw status
```

### API Security

```bash
# Bind API to localhost only
export XAI_HOST=127.0.0.1

# Or enable authentication
export XAI_API_AUTH_REQUIRED=1
export XAI_API_KEYS=your-secret-key-here
```

### SSH Hardening

```bash
# Disable password auth
sudo nano /etc/ssh/sshd_config
# Set: PasswordAuthentication no
# Set: PermitRootLogin no
sudo systemctl restart ssh
```

### Regular Updates

```bash
# Update script
cat > ~/update-xai.sh << 'EOF'
#!/bin/bash
set -e
cd ~/xai
git pull
source venv/bin/activate
pip install -e .
sudo systemctl restart xai-node
echo "Update complete. Check status with: sudo systemctl status xai-node"
EOF

chmod +x ~/update-xai.sh
```

## Performance Optimization

### Use SSD Storage

SSDs provide 10-100x better I/O than microSD cards:
- Boot from USB SSD (Raspberry Pi 4+)
- Move data directory to SSD
- Use external SSD enclosure

### CPU Governor

```bash
# Set to performance mode
echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor
```

### Network Optimization

```bash
# Use Ethernet instead of WiFi
# If WiFi is required, disable power saving:
sudo iw dev wlan0 set power_save off
```

### Reduce Logging

```bash
export XAI_LOG_LEVEL=WARNING  # Only warnings and errors
```

## Advanced Topics

### Restoring Archived Blocks

```bash
# List archived blocks
ls /mnt/ssd/xai-data/archive/

# Restore via API
curl -X POST http://localhost:12001/api/v2/node/pruning/restore/<height>
```

### State Snapshots (Full Nodes)

Full nodes create periodic snapshots for fast sync:

```bash
# Check snapshot status
curl http://localhost:12001/api/v2/node/snapshots | jq

# Export snapshot
curl -X POST http://localhost:12001/api/v2/node/snapshots/export?height=1000
```

### Custom Pruning Schedule

```bash
# Run pruning via cron (alternative to automatic)
crontab -e

# Add: Run pruning daily at 2 AM
0 2 * * * curl -X POST http://localhost:12001/api/v2/node/pruning/prune
```

## Resource Estimates

### Storage Growth (Testnet)

Assuming 2-minute block time:
- **Blocks per day**: ~720
- **Blocks per month**: ~21,600
- **Average block size**: ~2KB (varies with transactions)
- **Monthly growth**: ~43MB (no pruning)

With pruning (1000 blocks):
- **Steady state**: ~2MB blockchain data
- **Archive storage**: ~43MB/month (compressed)

### Bandwidth Usage

- **Initial sync**: 10MB-1GB (depends on mode and checkpoint)
- **Daily operation**:
  - Light: ~58KB (headers only)
  - Pruned: ~1.4MB (full blocks)
  - Full: ~1.4MB + historical queries

### Memory Usage

- **Light**: 64-128MB
- **Pruned**: 256-512MB
- **Full**: 512MB-2GB
- **Archival**: 1-4GB

## Support and Resources

- **Documentation**: https://docs.xai-blockchain.org
- **GitHub Issues**: https://github.com/your-org/xai/issues
- **Discord**: [Community Discord Link]
- **Node API Reference**: `docs/api/README.md`
- **Raspberry Pi Setup**: `docs/user-guides/RASPBERRY_PI_SETUP.md`

## Quick Reference Card

```bash
# Check node status
curl http://localhost:12001/api/v2/node/status | jq

# Check pruning
curl http://localhost:12001/api/v2/node/pruning/status | jq

# Force pruning
curl -X POST http://localhost:12001/api/v2/node/pruning/prune

# View logs
sudo journalctl -u xai-node -f

# Restart node
sudo systemctl restart xai-node

# Monitor resources
htop
df -h
vcgencmd measure_temp  # Raspberry Pi only
```
