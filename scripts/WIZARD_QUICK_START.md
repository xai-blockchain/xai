# XAI Setup Wizard - Quick Start Guide

## One-Liner Setup

```bash
python scripts/setup_wizard.py
```

## What You'll Get

After 5 minutes of answering prompts, you'll have:
- Fully configured XAI node
- Generated .env file with all settings
- Optional wallet with private keys
- Systemd service file (Linux)
- Ready-to-start node

## Prerequisites

- Python 3.10+
- 10-500 GB free disk space (depending on mode)
- Internet connection (for syncing)

## Quick Answers for Common Scenarios

### Testnet Development Node (Beginner)
```
Network: testnet
Mode: full
Data dir: ~/.xai (default)
RPC port: 12001 (default)
P2P port: 12002 (default)
Mining: yes
Create wallet: yes
Metrics: yes
```

### Mainnet Full Node (Production)
```
Network: mainnet
Mode: full
Data dir: /var/lib/xai
RPC port: 12001
P2P port: 12002
Mining: yes (with hardware wallet address)
Metrics: yes
Systemd: yes
```

### Light Client (Minimal Resources)
```
Network: testnet/mainnet
Mode: light
Data dir: ~/.xai
Ports: defaults
Mining: no
Metrics: optional
```

## After Setup

### Start Your Node
```bash
python -m xai.core.node
```

### Check Status
```bash
curl http://localhost:12001/health
```

### View Metrics (if enabled)
```bash
curl http://localhost:12090/metrics
```

### Auto-start with Systemd (Linux)
```bash
# Install service
sudo cp xai-node-testnet.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable xai-node-testnet
sudo systemctl start xai-node-testnet

# Check status
sudo systemctl status xai-node-testnet
```

## Files Generated

1. **/.env** - Main configuration (0600 permissions)
2. **xai-node-{network}.service** - Systemd service file
3. **{data_dir}/wallets/wallet_*.json** - Wallet file (if created)

## Important Notes

- **Backup your .env file** - Contains secrets
- **Save your mnemonic** - Only shown once
- **Secure your wallet** - Use hardware wallet for large amounts
- **Testnet first** - Always test on testnet before mainnet

## Getting Help

- Full documentation: `scripts/SETUP_WIZARD.md`
- Test results: `scripts/SETUP_WIZARD_TEST.md`
- Enhancements: `scripts/SETUP_WIZARD_ENHANCEMENTS.md`
- Main README: `README.md`

## Troubleshooting

### Port Already in Use
```bash
# Find what's using the port
sudo lsof -i :12001

# Change ports during wizard or edit .env after
```

### Insufficient Disk Space
```bash
# Check available space
df -h ~

# Choose light mode or free up space
```

### Python Version Too Old
```bash
# Check version
python3 --version

# Upgrade Python (Ubuntu/Debian)
sudo apt update && sudo apt install python3.10
```

### Missing Dependencies
```bash
# Install required packages
pip install flask requests cryptography eth_keys ecdsa
```

## Re-running the Wizard

The wizard will:
- Detect existing .env
- Offer to back it up
- Allow you to overwrite or cancel

Backups are saved as `.env.backup.{timestamp}`
