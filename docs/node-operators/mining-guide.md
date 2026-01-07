# Mining Guide

Run a mining node on the XAI testnet.

## Overview

XAI uses Proof-of-Work consensus. Mining nodes:
- Create new blocks
- Process transactions
- Earn block rewards and transaction fees

## Prerequisites

- Running XAI node (see [Join Testnet](join-testnet.md))
- Mining node hardware (see [Hardware Requirements](../getting-started/hardware-requirements.md))
- XAI wallet address for rewards

## Quick Start

```bash
# Start node with mining enabled
python -m xai.core.node \
  --host 0.0.0.0 \
  --port 8545 \
  --p2p-port 8333 \
  --miner YOUR_XAI_ADDRESS \
  --peers https://testnet-rpc.xaiblockchain.com
```

## Configuration

### Environment Variables

```bash
# Enable mining
export XAI_MINING_ENABLED=true

# Set miner address (receives rewards)
export XAI_MINER_ADDRESS=xaitest1your_address_here

# Allow mining empty blocks (testnet only)
export XAI_ALLOW_EMPTY_MINING=true

# Heartbeat interval for empty blocks
export XAI_MINING_HEARTBEAT_SECONDS=10
```

### Systemd Service for Mining

```ini
[Unit]
Description=XAI Mining Node
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=xai
WorkingDirectory=/home/xai/xai
Environment=PYTHONUNBUFFERED=1
Environment=XAI_NETWORK=testnet
Environment=XAI_MINING_ENABLED=true
Environment=XAI_MINER_ADDRESS=xaitest1your_address_here
Environment=XAI_ALLOW_EMPTY_MINING=true
ExecStart=/home/xai/xai/venv/bin/python -m xai.core.node \
  --host 0.0.0.0 \
  --port 8545 \
  --p2p-port 8333 \
  --miner xaitest1your_address_here
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## Mining Economics

### Block Rewards

| Year | Blocks | Reward per Block |
|------|--------|------------------|
| 1 | 0 - 262,799 | 12 XAI |
| 2 | 262,800 - 525,599 | 6 XAI |
| 3 | 525,600 - 788,399 | 3 XAI |
| 4 | 788,400 - 1,051,199 | 1.5 XAI |
| ... | continues halving | ... |

### Streak Bonus

Consecutive block mining earns streak bonuses:
- 5+ consecutive blocks: +2% bonus
- 10+ consecutive blocks: +5% bonus
- 20+ consecutive blocks: +10% bonus
- Maximum bonus: 20%

### Transaction Fees

Miners also receive all transaction fees from blocks they mine.

## Monitoring Mining

### Check Mining Status

```bash
# Node stats including mining info
curl -s http://localhost:8545/stats | jq

# Check if mining is active
curl -s http://localhost:8545/stats | jq -r '.mining_enabled'

# Get miner address
curl -s http://localhost:8545/stats | jq -r '.miner_address'
```

### View Mining Logs

```bash
# Watch for mined blocks
journalctl -u xai -f | grep -E "(mined|Block|mining)"

# Example output:
# Block mined! Hash: 0000abc123...
# Block 1234 mined, hash=0000abc123...
```

### Check Rewards

```bash
# Check balance
xai-wallet balance --address YOUR_MINER_ADDRESS

# Or via API
curl -s "http://localhost:8545/balance/YOUR_MINER_ADDRESS"
```

## Difficulty

### Testnet Difficulty

Testnet uses capped difficulty for reliable block production:
- Maximum difficulty: 4 (4 leading zeros in hash)
- Auto-enabled via fast mining mode
- 20-minute reset rule if no blocks found

### Difficulty Adjustment

- Adjusts every 2016 blocks
- Target block time: configurable (default ~10s on testnet)
- Maximum 4x adjustment per period

## Troubleshooting

### Mining Not Starting

```bash
# Check if mining is enabled
echo $XAI_MINING_ENABLED

# Check miner address is set
echo $XAI_MINER_ADDRESS

# Verify in logs
journalctl -u xai | grep -i "mining"
```

### Low Hash Rate

- Check CPU usage: `top` or `htop`
- Ensure no other mining processes running
- Verify difficulty isn't too high: `curl -s http://localhost:8545/stats | jq '.difficulty'`

### Blocks Not Propagating

- Check peer connections: `curl -s http://localhost:8545/peers | jq`
- Verify P2P port is open: `sudo ufw status`
- Check network connectivity to bootstrap nodes

## Security Best Practices

1. **Separate mining keys** - Use dedicated address for mining rewards
2. **Regular backups** - Backup wallet keys securely
3. **Monitor balance** - Set up alerts for reward payouts
4. **Firewall** - Only expose necessary ports
5. **Updates** - Keep node software updated
