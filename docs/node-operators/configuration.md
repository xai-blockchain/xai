# Configuration Reference

Complete reference for XAI node configuration options.

## Environment Variables

XAI uses environment variables for configuration. Set these in `.env` or export them.

### Network Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `XAI_NETWORK` | `testnet` | Network type: `mainnet`, `testnet`, `devnet` |
| `XAI_DATA_DIR` | `~/xai/data` | Data directory for chain data |
| `XAI_LOG_LEVEL` | `INFO` | Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |

### API Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `XAI_API_HOST` | `127.0.0.1` | RPC API bind address |
| `XAI_API_PORT` | `8545` | RPC API port |
| `XAI_API_KEYS` | - | Comma-separated API keys for authentication |

### P2P Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `XAI_P2P_HOST` | `0.0.0.0` | P2P bind address |
| `XAI_P2P_PORT` | `8333` | P2P port |
| `XAI_BOOTSTRAP_PEERS` | - | Comma-separated bootstrap peer URLs |
| `XAI_MAX_PEERS` | `50` | Maximum peer connections |

### Mining Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `XAI_MINING_ENABLED` | `false` | Enable mining |
| `XAI_MINER_ADDRESS` | - | Address to receive mining rewards |
| `XAI_ALLOW_EMPTY_MINING` | `false` | Mine blocks without transactions |
| `XAI_MINING_HEARTBEAT_SECONDS` | `10` | Seconds between heartbeat transactions |

### Testnet Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `XAI_FAST_MINING` | auto | Auto-enabled for testnet (caps difficulty) |
| `XAI_MAX_TEST_MINING_DIFFICULTY` | `4` | Maximum difficulty on testnet |

## Port Configuration

### Default Ports

| Port | Service | Description |
|------|---------|-------------|
| 8333 | P2P | Node-to-node communication |
| 8545 | JSON-RPC | Main API endpoint |
| 8766 | WebSocket | Real-time subscriptions |
| 8081 | Faucet | Testnet token faucet |
| 8082 | Explorer | Block explorer |
| 8084 | Indexer | Transaction indexer API |

### Multi-Node Configuration

Running multiple nodes on one machine:

| Node | RPC | P2P | WebSocket |
|------|-----|-----|-----------|
| Node 1 | 12545 | 12333 | 12766 |
| Node 2 | 12555 | 12334 | 12767 |
| Node 3 | 12565 | 12335 | 12768 |
| Node 4 | 12575 | 12336 | 12769 |

## Configuration File

Create `config.yaml` in your data directory:

```yaml
# Network
network: testnet
chain_id: xai-testnet-1

# API
api:
  host: 127.0.0.1
  port: 8545
  cors_origins:
    - "*"

# P2P
p2p:
  host: 0.0.0.0
  port: 8333
  max_peers: 50
  bootstrap_nodes:
    - https://testnet-rpc.xaiblockchain.com

# Mining
mining:
  enabled: false
  miner_address: ""
  allow_empty_mining: false
  heartbeat_seconds: 10

# Logging
logging:
  level: INFO
  format: json
  file: logs/node.log

# Database
database:
  path: data/chaindata
  cache_mb: 256

# Checkpoints
checkpoints:
  enabled: true
  interval: 1000
  keep_recent: 5
```

## Command Line Arguments

Override configuration via command line:

```bash
python -m xai.core.node \
  --host 0.0.0.0 \
  --port 8545 \
  --p2p-port 8333 \
  --data-dir /var/lib/xai \
  --miner YOUR_ADDRESS \
  --peers https://peer1.example.com https://peer2.example.com \
  --log-level DEBUG
```

### Available Arguments

| Argument | Description |
|----------|-------------|
| `--host` | API bind address |
| `--port` | API port |
| `--p2p-port` | P2P port |
| `--data-dir` | Data directory |
| `--miner` | Miner address (enables mining) |
| `--peers` | Space-separated peer URLs |
| `--log-level` | Logging level |
| `--testnet` | Use testnet configuration |
| `--mainnet` | Use mainnet configuration |

## Logging Configuration

### Log Levels

- `DEBUG`: Verbose debugging information
- `INFO`: General operational information
- `WARNING`: Warning conditions
- `ERROR`: Error conditions

### Log Output

```bash
# View logs (systemd)
journalctl -u xai -f

# View logs (direct)
tail -f ~/xai/logs/node.log

# Filter by level
journalctl -u xai -f | grep ERROR
```

## Security Configuration

### Firewall Rules

```bash
# Allow P2P
sudo ufw allow 8333/tcp

# Allow RPC (only if public)
sudo ufw allow 8545/tcp

# Enable firewall
sudo ufw enable
```

### Running as Non-Root

```bash
# Create xai user
sudo useradd -m -s /bin/bash xai

# Set ownership
sudo chown -R xai:xai /home/xai/xai

# Run as xai user
sudo -u xai /home/xai/xai/venv/bin/python -m xai.core.node
```
