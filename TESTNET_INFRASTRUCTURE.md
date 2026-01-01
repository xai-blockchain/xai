# XAI Blockchain Testnet Infrastructure

> **Last Updated**: 2026-01-01
> **Maintainer**: Jeff DeCristofaro <info@xaiblockchain.org>
> **License**: Apache 2.0

## Quick Reference

| Item | Value |
|------|-------|
| **Server IP** | 54.39.129.11 |
| **SSH Access** | `ssh xai-testnet` (from WSL2) |
| **VPN IP** | 10.10.0.3 |
| **Chain Type** | Python-based (not Cosmos SDK) |
| **Node Port** | 8545 |
| **Binary** | Python application |
| **Home Dir** | `~/xai` |

---

## 1. Server Access

### SSH Configuration (from WSL2)
```bash
# Direct access
ssh xai-testnet

# Or explicitly
ssh ubuntu@54.39.129.11
```

SSH is configured in `~/.ssh/config` on WSL2 with key-based authentication.

### WireGuard VPN
- **Interface**: wg0
- **Private IP**: 10.10.0.3/24
- **Config**: `/etc/wireguard/wg0.conf`
- **Peers**: AURA (10.10.0.1), PAW (10.10.0.2)

```bash
# Check VPN status
sudo wg show

# Ping other nodes
ping 10.10.0.1  # AURA
ping 10.10.0.2  # PAW
```

---

## 2. Directory Structure

```
~/xai/                    # Source code repository
├── src/
│   └── xai/
│       ├── cli/
│       │   ├── enhanced_cli.py   # Python CLI
│       │   └── main.py
│       ├── core/
│       │   ├── blockchain.py
│       │   ├── node.py
│       │   └── node_api.py
│       └── ...
├── venv/                 # Python virtual environment
├── pyproject.toml
└── README.md

~/xai-cli.sh              # Bash wrapper for quick commands
```

---

## 3. CLI Tools

### Option 1: Bash Wrapper Script (Recommended)
```bash
# Location
~/xai-cli.sh

# Usage
~/xai-cli.sh info       # Node information
~/xai-cli.sh stats      # Blockchain statistics
~/xai-cli.sh blocks     # List recent blocks
~/xai-cli.sh block <n>  # Get specific block
~/xai-cli.sh balance <addr>  # Check balance
~/xai-cli.sh pending    # Pending transactions
~/xai-cli.sh peers      # Connected peers
~/xai-cli.sh health     # Health check
```

### Option 2: Python CLI
```bash
# Activate virtual environment
source ~/xai/venv/bin/activate

# Run CLI
cd ~/xai/src
python -m xai.cli.enhanced_cli --node-url http://localhost:8545 <command>

# Example commands
python -m xai.cli.enhanced_cli --node-url http://localhost:8545 blockchain info
python -m xai.cli.enhanced_cli --node-url http://localhost:8545 blockchain block 0
python -m xai.cli.enhanced_cli --node-url http://localhost:8545 blockchain mempool
```

### Option 3: Direct curl
```bash
# Stats
curl -s http://localhost:8545/stats | jq

# Blocks
curl -s http://localhost:8545/blocks | jq

# Specific block
curl -s http://localhost:8545/blocks/0 | jq

# Health
curl -s http://localhost:8545/health | jq

# Peers
curl -s http://localhost:8545/peers | jq

# Pending transactions
curl -s http://localhost:8545/transactions | jq
```

---

## 4. Node API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Node root info |
| `/stats` | GET | Blockchain statistics |
| `/health` | GET | Health check |
| `/blocks` | GET | List blocks |
| `/blocks/{id}` | GET | Get block by index/hash |
| `/transactions` | GET | Pending transactions |
| `/transaction/{hash}` | GET | Get transaction |
| `/balance/{address}` | GET | Get balance |
| `/peers` | GET | Connected peers |
| `/auto-mine/start` | POST | Start auto-mining |
| `/auto-mine/stop` | POST | Stop auto-mining |

---

## 5. Service Management

### Check Node Status
```bash
# Check if running
ps aux | grep -E "python.*xai|node" | grep -v grep

# Check port
sudo lsof -i :8545
```

### Start Node
```bash
# Activate venv and start
cd ~/xai
source venv/bin/activate
nohup python -m xai.core.node > ~/xai/logs/node.log 2>&1 &
```

### Stop Node
```bash
pkill -f "python.*xai"
```

### View Logs
```bash
tail -f ~/xai/logs/node.log
```

---

## 6. Configuration

XAI uses Python configuration, not TOML files:

### Node Configuration
Configuration is typically in environment variables or code:
```bash
# Default port
export XAI_NODE_PORT=8545

# Mining address
export XAI_MINER_ADDRESS="your_address"
```

### Key Locations
```bash
# Node data
~/.xai/data/           # If exists

# Wallet keys
~/.xai/wallets/        # If exists
```

---

## 7. Mining

### Check Mining Status
```bash
curl -s http://localhost:8545/stats | jq '.is_mining, .miner_address'
```

### Start Auto-Mining
```bash
curl -X POST http://localhost:8545/auto-mine/start \
  -H "Content-Type: application/json" \
  -d '{"miner_address": "YOUR_ADDRESS"}'
```

### Stop Auto-Mining
```bash
curl -X POST http://localhost:8545/auto-mine/stop
```

---

## 8. Monitoring & Debugging

### Check Node Stats
```bash
~/xai-cli.sh stats
# Returns: chain_height, difficulty, pending transactions, etc.
```

### Check Health
```bash
curl -s http://localhost:8545/health | jq
```

### View Recent Blocks
```bash
curl -s "http://localhost:8545/blocks?limit=5" | jq
```

---

## 9. Source Code Repository

### Location on Server
```bash
~/xai/
```

### GitHub
```
git@github.com:xai-blockchain/xai.git
```

### Update Code
```bash
cd ~/xai
git pull origin main

# Reinstall if needed
source venv/bin/activate
pip install . --upgrade
```

### Recent Fix Applied
**Commit**: `b02a82a` - "Fix CLI endpoint mismatches to match actual node API"

Fixed endpoints in `src/xai/cli/enhanced_cli.py`:
- `/block/{id}` → `/blocks/{id}`
- `/info` → `/stats`
- `/mining/status` → derived from `/stats`
- `/mining/start` → `/auto-mine/start`
- `/mining/stop` → `/auto-mine/stop`
- `/mempool` → `/transactions`

---

## 10. Network Topology

```
┌─────────────────────────────────────────────────────────────────┐
│                     OVHcloud KS-5 Servers                       │
├─────────────────┬─────────────────┬─────────────────────────────┤
│   AURA Testnet  │   PAW Testnet   │        XAI Testnet          │
│  158.69.119.76  │  54.39.103.49   │       54.39.129.11          │
│   10.10.0.1     │   10.10.0.2     │        10.10.0.3            │
│   (wg0)         │   (wg0)         │        (wg0)                │
│   Cosmos SDK    │   Cosmos SDK    │        Python               │
└────────┬────────┴────────┬────────┴────────────┬────────────────┘
         │                 │                     │
         └─────────────────┼─────────────────────┘
                           │
                    WireGuard Mesh
                    (Port 51820)
```

---

## 11. Ports Summary

| Port | Service | Binding |
|------|---------|---------|
| 8545 | Node API | 0.0.0.0 |
| 51820 | WireGuard | 0.0.0.0 |

---

## 12. Troubleshooting

### Node Not Responding
```bash
# Check if process is running
ps aux | grep xai

# Check port binding
sudo lsof -i :8545

# Restart
pkill -f "python.*xai"
cd ~/xai && source venv/bin/activate
nohup python -m xai.core.node > ~/xai/logs/node.log 2>&1 &
```

### CLI Errors
```bash
# Ensure using correct endpoints
# Old: /info, /mempool, /mining/start
# New: /stats, /transactions, /auto-mine/start

# Use the wrapper script for simplicity
~/xai-cli.sh help
```

### Python Environment Issues
```bash
# Recreate venv if needed
cd ~/xai
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install .
```

---

## 13. Key Differences from Cosmos Chains

| Aspect | AURA/PAW (Cosmos) | XAI (Python) |
|--------|-------------------|--------------|
| **Framework** | Cosmos SDK | Custom Python |
| **Consensus** | CometBFT | Custom PoW/PoI |
| **Config** | TOML files | Python/env vars |
| **CLI** | Single binary | Python + bash wrapper |
| **API Port** | 1317 (REST), 9090 (gRPC) | 8545 (HTTP) |
| **RPC Port** | 26657 | N/A |

---

## 14. Development Notes

### CLI Enhancement
The CLI is in `src/xai/cli/enhanced_cli.py` and uses Click framework:
```python
# Transport modes
--transport http   # HTTP to node API
--transport local  # Direct blockchain access
```

### API Routes
Defined in `src/xai/core/node_api.py` and related files.

---

## 15. Contact & Support

| Resource | Link |
|----------|------|
| **Maintainer** | Jeff DeCristofaro |
| **Email** | info@xaiblockchain.org |
| **Bug Reports** | GitHub Issues |
| **Security Issues** | See SECURITY.md |

---

## 16. Related Documentation

- [Python Click Documentation](https://click.palletsprojects.com/)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [CONTRIBUTING.md](./CONTRIBUTING.md) - Contribution guidelines
- [LICENSE](./LICENSE) - Apache 2.0 License
- [AUTHORS](./AUTHORS) - Project authors and contributors
- [SECURITY.md](./SECURITY.md) - Security policy and reporting
