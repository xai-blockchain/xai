# Local Development Setup

Quick guide to set up XAI blockchain for local development.

## Prerequisites

- **Python 3.10+** (check with `python3 --version`)
- **pip** package manager
- **Git** for version control
- 4GB RAM, 10GB disk space minimum

## Installation

```bash
# Clone the repository
git clone https://github.com/xai-blockchain/xai.git
cd xai

# Install with dependencies
pip install -c constraints.txt -e ".[dev]"

# Verify installation
python -m pytest --co -q
```

Optional virtual environment:
```bash
python -m venv venv && source venv/bin/activate
pip install -c constraints.txt -e ".[dev]"
```

## Running the Node

```bash
# Set network (development/testnet/mainnet)
export XAI_NETWORK=development

# Start the node
python -m xai.core.node

# Ports: RPC :12001, P2P :12002, WebSocket :12003
```

With mining:
```bash
export MINER_ADDRESS=YOUR_XAI_ADDRESS
python -m xai.core.node --miner $MINER_ADDRESS
```

## Running Tests

```bash
pytest                                    # All tests
pytest --cov=src/xai --cov-report=html   # With coverage
make quick                                # Quick validation
make ci                                   # Full CI pipeline
```

## Code Quality

```bash
black src tests && isort src tests   # Format
pylint src && mypy src               # Lint
bandit -r src                        # Security scan
pre-commit run --all-files           # All hooks
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `XAI_NETWORK` | development | Network: development/testnet/mainnet |
| `XAI_RPC_PORT` | 12001 | RPC API port |
| `XAI_LOG_LEVEL` | INFO | Logging level |
| `XAI_DATA_DIR` | ~/.xai | Blockchain data directory |
| `MINER_ADDRESS` | - | Address for mining rewards |

## Common Issues

- **"Module not found"**: Run `pip install -e .`
- **"Port in use"**: `lsof -i :12001` and kill conflicting process
- **"Tests failing"**: Update deps with `pip install -c constraints.txt -e ".[dev]"`

## Next Steps

- [QUICKSTART Guide](../QUICKSTART.md) - Full getting started tutorial
- [Testing Guide](TESTING-GUIDE.md) - Comprehensive testing documentation
- [API Reference](../api/rest-api.md) - REST API documentation
- [Architecture](../architecture/overview.md) - System design overview
