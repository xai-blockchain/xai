# XAI Lightweight Node Guide

Run XAI blockchain on resource-constrained devices like Raspberry Pi, IoT devices, or low-power servers. This guide covers installation, configuration, and optimization for minimal hardware.

---

## Overview

A lightweight node is optimized for devices with limited:
- **CPU:** Single-core or low-power processors
- **RAM:** 512 MB - 2 GB
- **Storage:** Limited disk space (< 32 GB)
- **Bandwidth:** Slow or metered connections

**Lightweight vs Light Client:**
- **Lightweight Node:** Full node with optimizations (validates all blocks, lower resource usage)
- **Light Client:** SPV mode (header-only sync, minimal validation)
- See [Light Client Mode](light_client_mode.md) for header-only sync

---

## Minimum Requirements

### Tested Configurations

| Device | CPU | RAM | Storage | Status |
|--------|-----|-----|---------|--------|
| Raspberry Pi 4 (4GB) | 1.5 GHz quad | 4 GB | 32 GB SD | ✅ Excellent |
| Raspberry Pi 4 (2GB) | 1.5 GHz quad | 2 GB | 16 GB SD | ✅ Good |
| Raspberry Pi 3 B+ | 1.4 GHz quad | 1 GB | 16 GB SD | ⚠️ Marginal |
| Raspberry Pi Zero 2 W | 1.0 GHz quad | 512 MB | 8 GB SD | ❌ Light client only |
| Orange Pi 5 | 2.4 GHz octa | 8 GB | 32 GB | ✅ Excellent |
| Rock Pi 4 | 1.8 GHz hexa | 4 GB | 32 GB | ✅ Excellent |
| Intel NUC (Celeron) | 2.0 GHz dual | 4 GB | 128 GB SSD | ✅ Excellent |

### Absolute Minimum

- **CPU:** 700 MHz single-core (1 GHz recommended)
- **RAM:** 512 MB available (1 GB recommended)
- **Storage:** 8 GB free (16 GB recommended)
- **Network:** 1 Mbps sustained (5 Mbps recommended)

---

## Raspberry Pi Installation

### Step 1: Prepare SD Card

```bash
# Download Raspberry Pi OS Lite (64-bit recommended)
# Flash to SD card using Raspberry Pi Imager or balenaEtcher
# Enable SSH before first boot
```

### Step 2: Initial Setup

```bash
# SSH into Pi
ssh pi@raspberrypi.local
# Default password: raspberry

# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y \
  python3 \
  python3-pip \
  python3-venv \
  git \
  sqlite3 \
  build-essential \
  libssl-dev \
  libffi-dev
```

### Step 3: Install XAI

```bash
# Clone repository
cd ~
git clone https://github.com/your-org/xai.git
cd xai

# Create virtual environment (recommended for Pi)
python3 -m venv venv
source venv/bin/activate

# Install with lightweight optimizations
pip install -c constraints.txt -e ".[light]"

# Verify installation
python -m xai.core.node --version
```

### Step 4: Configure for Low Resources

Create `~/.xai/lightweight.yaml`:

```yaml
# Lightweight Node Configuration for Raspberry Pi
node:
  mode: lightweight
  data_dir: /home/pi/.xai/data

# Memory limits
memory:
  max_cache_mb: 128          # Limit cache to 128 MB
  block_cache_size: 50       # Keep only 50 recent blocks in memory
  tx_pool_max_size: 500      # Limit mempool to 500 transactions
  utxo_cache_mb: 64          # UTXO cache limited to 64 MB

# Storage optimizations
storage:
  enable_pruning: true       # Prune old blocks
  pruning_keep_blocks: 1000  # Keep only last 1000 blocks
  db_cache_mb: 32           # Database cache
  use_compression: true      # Compress blockchain data

# Network settings
network:
  max_peers: 4              # Limit to 4 peers (saves bandwidth)
  max_inbound_peers: 2      # Allow 2 inbound connections
  connection_timeout: 30     # 30 second timeout
  bandwidth_limit_kbps: 512  # Limit to 512 Kbps

# Performance settings
performance:
  worker_threads: 2          # Use 2 threads max
  validation_batch_size: 10  # Validate 10 blocks at a time
  sync_mode: slow           # Slower but lower memory usage
  enable_checkpoints: true   # Use checkpoint sync

# Logging (reduce disk I/O)
logging:
  level: WARNING            # Only warnings and errors
  max_file_mb: 10          # Max 10 MB log file
  max_files: 2             # Keep only 2 log files
```

### Step 5: Start Node

```bash
# Start with config
python -m xai.core.node --config ~/.xai/lightweight.yaml

# Or use environment variables
export XAI_NETWORK=testnet
export XAI_NODE_MODE=lightweight
export XAI_CACHE_SIZE=128
export XAI_MAX_PEERS=4
python -m xai.core.node
```

---

## Systemd Service (Auto-Start)

### Create Service

```bash
sudo tee /etc/systemd/system/xai-node.service > /dev/null <<EOF
[Unit]
Description=XAI Lightweight Node
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/xai
Environment="PATH=/home/pi/xai/venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="XAI_NETWORK=testnet"
Environment="XAI_NODE_MODE=lightweight"
ExecStart=/home/pi/xai/venv/bin/python -m xai.core.node --config /home/pi/.xai/lightweight.yaml
Restart=on-failure
RestartSec=30
StandardOutput=journal
StandardError=journal

# Resource limits
MemoryMax=512M
CPUQuota=80%

[Install]
WantedBy=multi-user.target
EOF
```

### Enable and Start

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable auto-start
sudo systemctl enable xai-node

# Start service
sudo systemctl start xai-node

# Check status
sudo systemctl status xai-node

# View logs
sudo journalctl -u xai-node -f
```

---

## Optimization Tips

### 1. Use External Storage (SSD/HDD)

SD cards are slow and wear out. Use USB SSD for blockchain data:

```bash
# Mount USB SSD
sudo mkdir -p /mnt/xai-data
sudo mount /dev/sda1 /mnt/xai-data
sudo chown pi:pi /mnt/xai-data

# Update config
sed -i 's|/home/pi/.xai/data|/mnt/xai-data|' ~/.xai/lightweight.yaml

# Make permanent (add to /etc/fstab)
echo '/dev/sda1 /mnt/xai-data ext4 defaults 0 2' | sudo tee -a /etc/fstab
```

### 2. Enable Swap (if RAM < 1 GB)

```bash
# Create 2 GB swap file
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Make permanent
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# Reduce swappiness (use swap only when necessary)
echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

### 3. Disable GUI (Raspberry Pi OS)

```bash
# Free up ~200 MB RAM
sudo systemctl set-default multi-user.target
sudo reboot
```

### 4. Optimize Database

```bash
# Compact database weekly
cat > ~/xai-maintenance.sh <<'EOF'
#!/bin/bash
# Stop node
sudo systemctl stop xai-node

# Compact database
python3 -m xai.tools.db_compact ~/.xai/data/blockchain.db

# Restart node
sudo systemctl start xai-node
EOF

chmod +x ~/xai-maintenance.sh

# Add to crontab (run weekly on Sunday at 2 AM)
(crontab -l 2>/dev/null; echo "0 2 * * 0 /home/pi/xai-maintenance.sh") | crontab -
```

### 5. Monitor Resources

```bash
# Install monitoring tools
sudo apt install -y htop iotop

# Check CPU and memory
htop

# Check disk I/O
sudo iotop

# Monitor node status
curl http://localhost:12001/health
```

---

## Performance Tuning

### CPU Optimization

```yaml
# In lightweight.yaml
performance:
  worker_threads: 1          # Single thread for RPi Zero
  worker_threads: 2          # Two threads for RPi 3/4
  nice_level: 10            # Lower priority (nice)
  cpu_affinity: [0, 1]      # Pin to specific cores
```

### Memory Optimization

```yaml
memory:
  max_cache_mb: 64          # Very limited RAM
  max_cache_mb: 128         # 512 MB RAM
  max_cache_mb: 256         # 1 GB RAM
  max_cache_mb: 512         # 2+ GB RAM

  # Aggressive cleanup
  cache_cleanup_interval: 300  # Clean every 5 minutes
  force_gc: true               # Force garbage collection
```

### Network Optimization

```yaml
network:
  # Metered/slow connection
  bandwidth_limit_kbps: 256
  max_peers: 3
  connection_timeout: 60

  # Normal connection
  bandwidth_limit_kbps: 1024
  max_peers: 4
  connection_timeout: 30

  # Good connection
  bandwidth_limit_kbps: 0     # No limit
  max_peers: 8
  connection_timeout: 15
```

### Storage Optimization

```yaml
storage:
  # Aggressive pruning (minimal disk)
  pruning_keep_blocks: 500    # Keep ~16 hours of blocks
  compression_level: 9        # Maximum compression

  # Balanced pruning
  pruning_keep_blocks: 2000   # Keep ~3 days
  compression_level: 6        # Moderate compression

  # Archive mode (disabled pruning)
  enable_pruning: false       # Keep all blocks
```

---

## Checkpoint Sync (Fast Initial Sync)

Skip downloading the entire blockchain by using checkpoints:

```yaml
# In lightweight.yaml
sync:
  enable_checkpoint_sync: true
  checkpoint_url: "https://checkpoints.xai.network/testnet/latest"
  checkpoint_quorum: 3        # Require 3 checkpoint sources
  checkpoint_interval: 10000  # Every 10000 blocks

  # Trusted checkpoints
  trusted_checkpoints:
    - height: 100000
      hash: "0x123abc..."
      timestamp: 1704067200
    - height: 200000
      hash: "0x456def..."
      timestamp: 1708723200
```

**Benefits:**
- Sync in minutes instead of hours
- Lower bandwidth usage
- Less CPU/memory during sync

---

## Monitoring and Maintenance

### Health Check

```bash
# Check node status
curl http://localhost:12001/health

# Response:
# {
#   "status": "healthy",
#   "synced": true,
#   "height": 22341,
#   "peers": 4,
#   "memory_usage_mb": 156
# }
```

### Resource Monitoring

```bash
# Create monitoring script
cat > ~/check-xai-health.sh <<'EOF'
#!/bin/bash

echo "=== XAI Node Health ==="
systemctl is-active --quiet xai-node && echo "Service: Running" || echo "Service: Stopped"

echo ""
echo "=== Resource Usage ==="
free -h | grep Mem
df -h /mnt/xai-data | tail -1

echo ""
echo "=== Node Status ==="
curl -s http://localhost:12001/health | python3 -m json.tool

echo ""
echo "=== Recent Logs ==="
sudo journalctl -u xai-node -n 5 --no-pager
EOF

chmod +x ~/check-xai-health.sh

# Run health check
./check-xai-health.sh
```

### Automated Alerts

```bash
# Install email notifications
sudo apt install -y mailutils

# Create alert script
cat > ~/xai-alert.sh <<'EOF'
#!/bin/bash

STATUS=$(systemctl is-active xai-node)
if [ "$STATUS" != "active" ]; then
  echo "XAI node is down!" | mail -s "XAI Node Alert" your@email.com
fi

DISK_USAGE=$(df /mnt/xai-data | tail -1 | awk '{print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 90 ]; then
  echo "Disk usage at ${DISK_USAGE}%" | mail -s "XAI Disk Alert" your@email.com
fi
EOF

chmod +x ~/xai-alert.sh

# Run every 5 minutes
(crontab -l; echo "*/5 * * * * /home/pi/xai-alert.sh") | crontab -
```

---

## Wallet Operations on Lightweight Node

All wallet operations work normally:

```bash
# Generate wallet
python src/xai/wallet/cli.py generate-address

# Check balance
python src/xai/wallet/cli.py balance --address TXAI_ADDRESS

# Send transaction
python src/xai/wallet/cli.py send \
  --from TXAI_FROM \
  --to TXAI_TO \
  --amount 10.0

# Request testnet tokens
python src/xai/wallet/cli.py request-faucet --address TXAI_ADDRESS
```

---

## Troubleshooting

### Node Crashes / Out of Memory

**Solution:**
1. Reduce cache sizes in config
2. Enable swap
3. Use light client mode instead
4. Increase RAM (upgrade to Pi 4 with 4GB+)

```yaml
# Emergency low-memory config
memory:
  max_cache_mb: 32
  block_cache_size: 20
  tx_pool_max_size: 100
```

### Slow Sync

**Solution:**
1. Enable checkpoint sync
2. Use faster storage (SSD)
3. Increase peer count
4. Check network speed

```yaml
sync:
  enable_checkpoint_sync: true
  validation_batch_size: 20  # Larger batches
```

### High Disk I/O

**Solution:**
1. Move data to SSD
2. Increase database cache
3. Reduce logging

```yaml
storage:
  db_cache_mb: 64  # Larger cache
logging:
  level: ERROR     # Minimal logging
```

### Network Issues

**Solution:**
1. Check firewall rules
2. Verify peer connectivity
3. Use different bootstrap peers

```bash
# Test peer connection
telnet testnet-node1.xai.network 18545

# Check firewall
sudo ufw status
sudo ufw allow 18545/tcp
```

---

## Advanced: Cluster Setup

Run multiple lightweight nodes for redundancy:

```yaml
# Node 1 (Primary)
network:
  listen_address: 0.0.0.0:18545
  rpc_address: 0.0.0.0:18546
  bootstrap_peers:
    - "testnet-node1.xai.network:18545"

# Node 2 (Backup)
network:
  listen_address: 0.0.0.0:18547
  rpc_address: 0.0.0.0:18548
  bootstrap_peers:
    - "192.168.1.10:18545"  # Node 1
    - "testnet-node1.xai.network:18545"
```

---

## IoT Integration Examples

### Home Automation

```python
# Monitor wallet and trigger actions
from xai.core.client import XAIClient
import RPi.GPIO as GPIO

client = XAIClient('http://localhost:12001')
LED_PIN = 18

GPIO.setmode(GPIO.BCM)
GPIO.setup(LED_PIN, GPIO.OUT)

# Flash LED when transaction received
def on_transaction(tx):
    if tx['to'] == MY_ADDRESS:
        GPIO.output(LED_PIN, GPIO.HIGH)
        time.sleep(1)
        GPIO.output(LED_PIN, GPIO.LOW)

client.subscribe_transactions(on_transaction)
```

### Sensor Data to Blockchain

```python
# Log sensor readings to blockchain
import Adafruit_DHT

sensor = Adafruit_DHT.DHT22
pin = 4

while True:
    humidity, temperature = Adafruit_DHT.read_retry(sensor, pin)

    # Store on blockchain
    client.transaction.send({
        'from': SENSOR_ADDRESS,
        'to': DATA_CONTRACT_ADDRESS,
        'data': f'temp={temperature},humidity={humidity}',
    })

    time.sleep(3600)  # Every hour
```

---

## Next Steps

- **[Light Client Mode](light_client_mode.md)** - Even lower resource usage
- **[Mining Guide](mining.md)** - Mine on Raspberry Pi (not recommended)
- **[Wallet Setup](wallet-setup.md)** - Advanced wallet features
- **[API Documentation](../api/rest-api.md)** - Build IoT dApps

---

*Last Updated: January 2025 | XAI Version: 0.2.0*
