# XAI Blockchain

Python-based proof-of-work blockchain for AI compute task pooling and trading.

## Quick Start

### One-Line Install (Testnet)

```bash
curl -sL https://raw.githubusercontent.com/xai-blockchain/xai/main/scripts/install-testnet.sh | bash
```

### Manual Install

```bash
# Clone and install
git clone https://github.com/xai-blockchain/xai.git
cd xai
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e .

# Start node
python -m xai.core.node --port 8545 --p2p-port 8333 --peers https://testnet-rpc.xaiblockchain.com
```

## Testnet Information

| Parameter | Value |
|-----------|-------|
| **Network** | XAI Testnet |
| **Chain ID** | xai-testnet-1 |
| **Native Token** | XAI |
| **Block Time** | ~10 seconds |
| **Python** | 3.10+ required |

### Public Endpoints

| Service | URL |
|---------|-----|
| **RPC** | https://testnet-rpc.xaiblockchain.com |
| **REST API** | https://testnet-api.xaiblockchain.com |
| **WebSocket** | wss://testnet-ws.xaiblockchain.com |
| **Explorer** | https://testnet-explorer.xaiblockchain.com |
| **Faucet** | https://testnet-faucet.xaiblockchain.com |
| **Monitoring** | https://monitoring.xaiblockchain.com |

### Get Testnet Tokens

Visit: https://testnet-faucet.xaiblockchain.com

## Documentation

### Getting Started
- [Hardware Requirements](docs/getting-started/hardware-requirements.md)
- [Installation Guide](docs/getting-started/installation.md)

### Node Operators
- [Join Testnet](docs/node-operators/join-testnet.md)
- [Configuration Reference](docs/node-operators/configuration.md)
- [Mining Guide](docs/node-operators/mining-guide.md)

### Developers
- [REST API Reference](docs/api/rest-api.md)
- [WebSocket API](docs/api/websocket.md)
- [Protocol Specification](docs/protocol/PROTOCOL_SPECIFICATION.md)

### Troubleshooting
- [Common Issues](docs/troubleshooting/common-issues.md)

## Useful Commands

```bash
# Check node status
curl -s http://localhost:8545/stats | jq

# Get block height
curl -s http://localhost:8545/stats | jq -r '.chain_height'

# Check peers
curl -s http://localhost:8545/peers | jq

# View logs (systemd)
sudo journalctl -u xai -f

# Restart node
sudo systemctl restart xai
```

## Development

```bash
# Setup development environment
python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run linting
ruff check src/
mypy src/
```

## Project Structure

```
xai/
├── src/xai/           # Main Python package
│   ├── core/          # Core blockchain logic
│   ├── consensus/     # Consensus mechanisms
│   └── api/           # REST/WebSocket APIs
├── docs/              # Documentation
├── genesis/           # Genesis configuration
├── network/           # Network configuration
├── scripts/           # Utility scripts
├── tests/             # Test suite
└── docker/            # Docker configuration
```

## Subprojects

- `explorer/` - Block explorer (React frontend, Python backend)
- `mobile/` - Mobile wallet apps
- `sdk/` - Client SDKs (TypeScript, Flutter, Kotlin, Swift)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Security

See [SECURITY.md](SECURITY.md) for security policy and reporting vulnerabilities.

## License

Apache 2.0. See [LICENSE](LICENSE).
