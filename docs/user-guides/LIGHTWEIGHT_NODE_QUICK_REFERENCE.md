# XAI Lightweight Node Quick Reference

Quick reference card for lightweight node operators.

## Node Modes

| Mode | Command | RAM | Storage | Use Case |
|------|---------|-----|---------|----------|
| Light | `XAI_NODE_MODE=light` | 256MB | <100MB | Mobile wallets |
| Pruned | `XAI_NODE_MODE=pruned` | 512MB-1GB | 100MB-1GB | Raspberry Pi, VPS |
| Full | `XAI_NODE_MODE=full` | 2GB+ | 10GB+ | Validators |

## Quick Start Commands

### Light Client (Minimal)
```bash
export XAI_NODE_MODE=light
export XAI_CHECKPOINT_SYNC=1
python -m xai.core.node --mode light
```

### Pruned Node (Raspberry Pi)
```bash
export XAI_NODE_MODE=pruned
export XAI_PRUNE_BLOCKS=1000
export XAI_CHECKPOINT_SYNC=1
python -m xai.core.node
```

### Full Node
```bash
export XAI_NODE_MODE=full
export XAI_CHECKPOINT_SYNC=1
python -m xai.core.node
```

## Essential Environment Variables

```bash
# Node operation
XAI_NODE_MODE=light|pruned|full
XAI_PRUNE_BLOCKS=1000          # Blocks to keep (pruned mode)
XAI_CHECKPOINT_SYNC=1          # Fast sync enabled

# Network
XAI_NETWORK=testnet|mainnet
XAI_HOST=0.0.0.0
XAI_PORT=18545                 # P2P port (testnet)
XAI_RPC_PORT=18546

# Performance
XAI_NETWORK_MAX_PEERS=15       # Reduce for low resources
XAI_NETWORK_SYNC_INTERVAL=120  # Seconds between syncs

# Storage
XAI_STORAGE_DATA_DIR=/path/to/data
XAI_STORAGE_ENABLE_COMPRESSION=1
```

## Resource Profiles

### Ultra Low (512MB RAM, microSD)
```bash
XAI_NODE_MODE=pruned
XAI_PRUNE_BLOCKS=500
XAI_NETWORK_MAX_PEERS=5
```

### Low (1GB RAM, microSD)
```bash
XAI_NODE_MODE=pruned
XAI_PRUNE_BLOCKS=1000
XAI_NETWORK_MAX_PEERS=10
```

### Medium (2GB RAM, SSD)
```bash
XAI_NODE_MODE=pruned
XAI_PRUNE_BLOCKS=5000
XAI_NETWORK_MAX_PEERS=20
```

### High (4GB+ RAM, SSD)
```bash
XAI_NODE_MODE=full
XAI_NETWORK_MAX_PEERS=50
```

## Common Operations

### Check Node Status
```bash
curl http://localhost:18546/api/v2/node/status
```

### Get Current Height
```bash
curl http://localhost:18546/api/v2/blockchain/height
```

### List Peers
```bash
curl http://localhost:18546/api/v2/node/peers
```

### Monitor Logs
```bash
tail -f logs/node.log
```

## Systemd Service

### Create Service
```bash
sudo tee /etc/systemd/system/xai-node.service > /dev/null << 'EOF'
[Unit]
Description=XAI Blockchain Node
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/home/youruser/xai
EnvironmentFile=/home/youruser/.xai_env
ExecStart=/home/youruser/xai/venv/bin/python -m xai.core.node
Restart=on-failure
RestartSec=30

[Install]
WantedBy=multi-user.target
EOF
```

### Service Commands
```bash
sudo systemctl enable xai-node   # Auto-start on boot
sudo systemctl start xai-node    # Start now
sudo systemctl stop xai-node     # Stop
sudo systemctl restart xai-node  # Restart
sudo systemctl status xai-node   # Check status
```

## Troubleshooting Quick Fixes

### Out of Memory
```bash
# Add swap
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Reduce pruning
export XAI_PRUNE_BLOCKS=500
export XAI_NETWORK_MAX_PEERS=5
```

### Sync Stalled
```bash
# Enable checkpoint sync
export XAI_CHECKPOINT_SYNC=1

# Restart node
sudo systemctl restart xai-node
```

### Storage Full
```bash
# Enable compression
export XAI_STORAGE_ENABLE_COMPRESSION=1

# Aggressive pruning
export XAI_PRUNE_BLOCKS=500

# Or move to larger disk
export XAI_STORAGE_DATA_DIR=/mnt/external/xai-data
```

### High CPU Usage
```bash
# Reduce peers
export XAI_NETWORK_MAX_PEERS=10

# Increase sync interval
export XAI_NETWORK_SYNC_INTERVAL=180

# Enable checkpoint sync
export XAI_CHECKPOINT_SYNC=1
```

## Monitoring Commands

### System Resources (Raspberry Pi)
```bash
# Temperature
vcgencmd measure_temp

# Memory
free -h

# Disk
df -h

# CPU
top -bn1 | grep "Cpu(s)"
```

### Network
```bash
# Bandwidth
ifstat

# Connections
netstat -an | grep 18545
```

## Port Reference

| Network | P2P Port | RPC Port |
|---------|----------|----------|
| Testnet | 18545 | 18546 |
| Mainnet | 8545 | 8546 |

## Firewall Rules

```bash
# Allow P2P (testnet)
sudo ufw allow 18545/tcp

# Block RPC from external (security)
sudo ufw deny 18546/tcp

# Check rules
sudo ufw status
```

## Backup Commands

### Wallet Backup
```bash
tar -czf wallet-backup-$(date +%Y%m%d).tar.gz \
  ~/.xai/wallets
```

### Config Backup
```bash
tar -czf config-backup-$(date +%Y%m%d).tar.gz \
  ~/.xai ~/.xai_env
```

### Full Backup
```bash
tar -czf xai-full-backup-$(date +%Y%m%d).tar.gz \
  ~/.xai ~/.xai_env /mnt/ssd/xai-data/wallets
```

## Performance Benchmarks

### Light Client
- Sync time: <5 minutes
- Storage growth: ~10KB/day
- Bandwidth: ~50KB/hour

### Pruned Node (1000 blocks)
- Sync time: 1-2 hours
- Storage growth: ~1MB/day
- Bandwidth: ~500KB/hour

### Full Node
- Sync time: 4-8 hours
- Storage growth: ~10MB/day
- Bandwidth: ~2MB/hour

## Support Resources

- **Full Guide**: [LIGHTWEIGHT_NODE_GUIDE.md](LIGHTWEIGHT_NODE_GUIDE.md)
- **Raspberry Pi**: [RASPBERRY_PI_SETUP.md](RASPBERRY_PI_SETUP.md)
- **Troubleshooting**: [troubleshooting.md](troubleshooting.md)
- **API Docs**: [../api/README.md](../api/README.md)
