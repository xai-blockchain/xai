# XAI Raspberry Pi Setup Guide

Complete step-by-step guide for running an XAI node on Raspberry Pi.

## Hardware Requirements

### Minimum (Pruned Node)
- Raspberry Pi 4 Model B (2GB RAM)
- 32GB microSD card (Class 10 or UHS-1)
- Official Raspberry Pi Power Supply (5V/3A USB-C)
- Ethernet cable or WiFi connection

### Recommended (Full Node)
- Raspberry Pi 4 Model B (4GB or 8GB RAM)
- 64GB+ USB 3.0 SSD (for better performance)
- Official Raspberry Pi Power Supply
- Ethernet connection (more stable than WiFi)
- Case with cooling (active fan recommended)

### Not Recommended
- Raspberry Pi 3 or older (too slow, use light client only)
- Raspberry Pi Zero (insufficient resources)
- microSD card only for full node (too slow)

## Operating System Setup

### Step 1: Download Raspberry Pi OS

**Recommended**: Raspberry Pi OS Lite (64-bit)
- Smaller footprint
- Better performance
- No GUI overhead

Download from: https://www.raspberrypi.com/software/operating-systems/

### Step 2: Flash OS to microSD Card

**Using Raspberry Pi Imager** (recommended):
```bash
# On your computer (Linux/Mac/Windows)
# 1. Download Raspberry Pi Imager
# 2. Select "Raspberry Pi OS Lite (64-bit)"
# 3. Select your microSD card
# 4. Click "Write"
```

**Manual Method**:
```bash
# On Linux
sudo dd if=raspios-lite-arm64.img of=/dev/sdX bs=4M status=progress
sync
```

### Step 3: Enable SSH (Headless Setup)

```bash
# Mount the boot partition
cd /media/username/boot

# Create empty ssh file to enable SSH
touch ssh

# Optional: Configure WiFi
cat > wpa_supplicant.conf << 'EOF'
country=US
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network={
    ssid="YourWiFiSSID"
    psk="YourWiFiPassword"
}
EOF

# Unmount and eject
cd ~
sync
# Remove microSD card
```

### Step 4: First Boot

```bash
# Insert microSD card into Raspberry Pi
# Connect power
# Wait 30-60 seconds for first boot

# Find Raspberry Pi IP address
# Option 1: Check your router's DHCP client list
# Option 2: Scan network
nmap -sn 192.168.1.0/24 | grep -i raspberry

# SSH into Raspberry Pi (default password: raspberry)
ssh pi@192.168.1.XXX
```

## System Configuration

### Step 1: Basic Setup

```bash
# Update system
sudo apt update
sudo apt upgrade -y

# Configure system settings
sudo raspi-config

# In raspi-config:
# 1. System Options > Password > Change default password
# 2. System Options > Hostname > Set to "xai-node"
# 3. Localisation Options > Timezone > Set your timezone
# 4. Performance Options > GPU Memory > Set to 16 (minimal)
# 5. Advanced Options > Expand Filesystem
# 6. Finish and reboot
```

### Step 2: Install Dependencies

```bash
# Core dependencies
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    git \
    build-essential \
    libssl-dev \
    libffi-dev

# Optional but recommended
sudo apt install -y \
    htop \
    tmux \
    vim \
    curl \
    wget
```

### Step 3: Configure USB SSD (Recommended)

**Connect USB SSD**:
```bash
# Check connected drives
lsblk

# Should show something like:
# sda      8:0    0  120G  0 disk
# └─sda1   8:1    0  120G  0 part

# Format SSD (WARNING: This erases all data!)
sudo mkfs.ext4 /dev/sda1

# Create mount point
sudo mkdir -p /mnt/ssd

# Mount SSD
sudo mount /dev/sda1 /mnt/ssd

# Set permissions
sudo chown -R pi:pi /mnt/ssd

# Get UUID for automatic mounting
sudo blkid /dev/sda1
# Copy the UUID value

# Add to /etc/fstab for automatic mounting
echo "UUID=your-uuid-here /mnt/ssd ext4 defaults,nofail 0 2" | sudo tee -a /etc/fstab

# Test fstab
sudo mount -a
df -h
```

**Enable USB Boot** (optional, for booting from SSD):
```bash
# Check bootloader version
sudo rpi-eeprom-update

# If update available, install it
sudo rpi-eeprom-update -a

# Reboot
sudo reboot

# After reboot, configure boot order
sudo raspi-config
# Select: Advanced Options > Boot Order > USB Boot
# Reboot again
```

## XAI Node Installation

### Step 1: Clone Repository

```bash
# Create working directory
mkdir -p ~/blockchain
cd ~/blockchain

# Clone XAI repository
git clone https://github.com/yourusername/xai.git
cd xai
```

### Step 2: Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip
```

### Step 3: Install XAI

```bash
# Install XAI and dependencies
pip install -e .

# Verify installation
python -c "import xai; print('XAI installed successfully')"
```

## Node Configuration

### Step 1: Create Configuration File

```bash
# Create config directory
mkdir -p ~/.xai

# Create configuration file
cat > ~/.xai/config.yaml << 'EOF'
# XAI Node Configuration for Raspberry Pi

network:
  port: 18545
  rpc_port: 18546
  host: "0.0.0.0"
  max_peers: 15
  peer_timeout: 60
  sync_interval: 120

blockchain:
  difficulty: 2
  block_time_target: 120

storage:
  data_dir: "/mnt/ssd/xai-data"  # Use SSD if available, otherwise: "/home/pi/xai-data"
  blockchain_file: "blockchain_testnet.json"
  enable_compression: true
  backup_enabled: false

logging:
  level: "INFO"
  enable_file_logging: true
  log_file: "/mnt/ssd/xai-data/logs/node.log"

security:
  rate_limit_enabled: true
  rate_limit_requests: 50
  rate_limit_window: 60
EOF
```

### Step 2: Create Environment File

```bash
# Create environment variables file
cat > ~/.xai_env << 'EOF'
# XAI Node Environment Variables

# Node mode (pruned recommended for Raspberry Pi)
export XAI_NODE_MODE=pruned
export XAI_PRUNE_BLOCKS=1000

# Network
export XAI_NETWORK=testnet
export XAI_HOST=0.0.0.0
export XAI_PORT=18545
export XAI_RPC_PORT=18546

# Performance tuning for Raspberry Pi
export XAI_NETWORK_MAX_PEERS=15
export XAI_NETWORK_PEER_TIMEOUT=60
export XAI_NETWORK_SYNC_INTERVAL=120

# Storage
export XAI_STORAGE_DATA_DIR=/mnt/ssd/xai-data
export XAI_STORAGE_ENABLE_COMPRESSION=1

# Enable checkpoint sync (faster initial sync)
export XAI_CHECKPOINT_SYNC=1

# Logging
export XAI_LOGGING_LEVEL=INFO
EOF

# Add to .bashrc for automatic loading
echo "source ~/.xai_env" >> ~/.bashrc

# Load now
source ~/.xai_env
```

### Step 3: Create Data Directories

```bash
# Create data directories on SSD
mkdir -p /mnt/ssd/xai-data/logs
mkdir -p /mnt/ssd/xai-data/wallets

# Or on SD card if no SSD
mkdir -p ~/xai-data/logs
mkdir -p ~/xai-data/wallets
```

## Running the Node

### Manual Start

```bash
# Activate virtual environment
cd ~/blockchain/xai
source venv/bin/activate

# Load environment
source ~/.xai_env

# Start node
python -m xai.core.node

# Or run in tmux for detached session
tmux new -s xai-node
python -m xai.core.node
# Press Ctrl+B, then D to detach
# Reattach with: tmux attach -t xai-node
```

### Systemd Service (Automatic Start)

```bash
# Create systemd service file
sudo tee /etc/systemd/system/xai-node.service > /dev/null << 'EOF'
[Unit]
Description=XAI Blockchain Node
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=pi
Group=pi
WorkingDirectory=/home/pi/blockchain/xai
EnvironmentFile=/home/pi/.xai_env

# Use virtual environment Python
ExecStart=/home/pi/blockchain/xai/venv/bin/python -m xai.core.node

# Restart policy
Restart=on-failure
RestartSec=30

# Resource limits (optional but recommended)
MemoryMax=1500M
CPUQuota=80%

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=xai-node

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
sudo systemctl daemon-reload

# Enable service (start on boot)
sudo systemctl enable xai-node

# Start service
sudo systemctl start xai-node

# Check status
sudo systemctl status xai-node

# View logs
sudo journalctl -u xai-node -f
```

## Monitoring

### Check Node Status

```bash
# Via systemd
sudo systemctl status xai-node

# Via logs
tail -f /mnt/ssd/xai-data/logs/node.log

# Via API
curl http://localhost:18546/api/v2/node/status | jq
curl http://localhost:18546/api/v2/blockchain/height
curl http://localhost:18546/api/v2/node/peers
```

### System Resources

```bash
# CPU and memory usage
htop

# Disk usage
df -h
du -sh /mnt/ssd/xai-data

# Temperature (Raspberry Pi specific)
vcgencmd measure_temp

# Network usage
ifconfig
```

### Create Monitoring Script

```bash
cat > ~/monitor-xai.sh << 'EOF'
#!/bin/bash

echo "=== XAI Node Monitor ==="
echo ""

# System info
echo "Temperature: $(vcgencmd measure_temp)"
echo "Memory: $(free -h | grep Mem | awk '{print $3 "/" $2}')"
echo ""

# Service status
echo "Service Status:"
systemctl is-active xai-node
echo ""

# Node info
echo "Node Height:"
curl -s http://localhost:18546/api/v2/blockchain/height | jq -r '.height'
echo ""

echo "Peer Count:"
curl -s http://localhost:18546/api/v2/node/peers | jq '. | length'
echo ""

# Disk usage
echo "Disk Usage:"
df -h /mnt/ssd | grep -v Filesystem
EOF

chmod +x ~/monitor-xai.sh

# Run monitor
~/monitor-xai.sh
```

## Performance Optimization

### CPU Governor

```bash
# Check current governor
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor

# Set to performance mode (temporary)
echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor

# Make permanent
sudo apt install cpufrequtils
echo 'GOVERNOR="performance"' | sudo tee /etc/default/cpufrequtils
sudo systemctl restart cpufrequtils
```

### Swap Configuration

```bash
# Check current swap
free -h

# Increase swap size (if needed)
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
# Set: CONF_SWAPSIZE=2048 (2GB)
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

### Network Performance

```bash
# Use Ethernet instead of WiFi for stability
# Disable power management on WiFi (if using WiFi)
sudo iw dev wlan0 set power_save off

# Make permanent
echo "iw dev wlan0 set power_save off" | sudo tee -a /etc/rc.local
```

## Troubleshooting

### Node Won't Start

```bash
# Check logs
sudo journalctl -u xai-node -n 50

# Check permissions
ls -la /mnt/ssd/xai-data

# Test manual start
cd ~/blockchain/xai
source venv/bin/activate
source ~/.xai_env
python -m xai.core.node
```

### High Temperature

```bash
# Check temperature
vcgencmd measure_temp

# If > 70°C:
# 1. Add heatsinks to CPU
# 2. Use active cooling (fan)
# 3. Improve case ventilation
# 4. Reduce CPU usage:
export XAI_NETWORK_MAX_PEERS=10
export XAI_PRUNE_BLOCKS=500
```

### Slow Sync

```bash
# Enable checkpoint sync
export XAI_CHECKPOINT_SYNC=1

# Reduce other resource usage
# Stop other services temporarily

# Use SSD instead of microSD

# Increase sync interval to reduce CPU load
export XAI_NETWORK_SYNC_INTERVAL=180
```

### Out of Memory

```bash
# Switch to more aggressive pruning
export XAI_NODE_MODE=pruned
export XAI_PRUNE_BLOCKS=500

# Reduce peer connections
export XAI_NETWORK_MAX_PEERS=10

# Add swap space (see Performance Optimization)

# Restart service
sudo systemctl restart xai-node
```

## Backup and Restore

### Backup Wallet

```bash
# Backup wallet directory
tar -czf wallet-backup-$(date +%Y%m%d).tar.gz /mnt/ssd/xai-data/wallets

# Copy to safe location (USB drive, cloud storage, etc.)
```

### Backup Configuration

```bash
# Backup config files
tar -czf config-backup-$(date +%Y%m%d).tar.gz ~/.xai ~/.xai_env
```

### Restore

```bash
# Stop node
sudo systemctl stop xai-node

# Restore wallets
tar -xzf wallet-backup-YYYYMMDD.tar.gz -C /

# Restore config
tar -xzf config-backup-YYYYMMDD.tar.gz -C ~

# Start node
sudo systemctl start xai-node
```

## Security

### Firewall Configuration

```bash
# Install ufw
sudo apt install ufw

# Default policies
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH
sudo ufw allow 22/tcp

# Allow P2P port
sudo ufw allow 18545/tcp

# Enable firewall
sudo ufw enable

# Check status
sudo ufw status
```

### SSH Security

```bash
# Disable password authentication (use SSH keys)
sudo nano /etc/ssh/sshd_config
# Set: PasswordAuthentication no
# Set: PermitRootLogin no

# Restart SSH
sudo systemctl restart ssh
```

### Updates

```bash
# Create update script
cat > ~/update-xai.sh << 'EOF'
#!/bin/bash
cd ~/blockchain/xai
git pull
source venv/bin/activate
pip install -e .
sudo systemctl restart xai-node
EOF

chmod +x ~/update-xai.sh

# Run updates
~/update-xai.sh
```

## Additional Resources

- [Lightweight Node Guide](LIGHTWEIGHT_NODE_GUIDE.md)
- [Node Monitoring Guide](../monitoring/README.md)
- [Troubleshooting Guide](troubleshooting.md)
