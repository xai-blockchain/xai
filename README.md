# XAI Blockchain

![Build](https://github.com/decristofaroj/xai/workflows/Comprehensive%20CI%2FCD%20Pipeline/badge.svg)
![Coverage](https://codecov.io/gh/decristofaroj/xai/branch/main/graph/badge.svg)
![Quality](https://sonarcloud.io/api/project_badges/measure?project=decristofaroj_xai&metric=alert_status)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

## A Proof-of-Work Blockchain with AI Governance and Integrated Wallets

XAI is a production-ready blockchain implementation featuring proof-of-work consensus, intelligent AI-based governance, atomic swap support for cross-chain trading, and comprehensive wallet management. Built for both individual users and enterprise compliance needs.

## Key Features

- **Proof-of-Work Consensus** - SHA-256 mining with adjustable difficulty targeting 2-minute block times
- **AI Governance System** - Intelligent proposal analysis and voting mechanism with AI-generated insights
- **Cross-Chain Atomic Swaps** - Direct trading with 11+ cryptocurrencies without intermediaries
- **Smart Contracts** - On-chain programmable logic for complex transaction flows
- **Multi-Signature Wallets** - Shared wallet control with configurable signature thresholds
- **Time-Locked Transactions** - Scheduled coin releases and time capsule functionality
- **AML Compliance** - Built-in transaction monitoring, reporting, and risk assessment tools

## Quick Start (< 5 Minutes)

### Prerequisites

- Python 3.10 or higher
- 2GB RAM minimum
- 10GB+ disk space for blockchain data
- Git

### Installation

```bash
# Clone the repository
git clone https://github.com/decristofaroj/xai.git
cd xai

# Install dependencies
pip install -r requirements.txt

# Verify installation
python -m pytest --co -q
```

### Start a Node

```bash
# Set network (testnet by default)
export XAI_NETWORK=testnet

# Run a node
python src/aixn/core/node.py
```

The node will start on port 18545 (testnet) or 8545 (mainnet).

### Start Mining

```bash
# Generate a wallet address first (or use existing)
python src/aixn/wallet/cli.py generate-address

# Start mining with your address
export MINER_ADDRESS=YOUR_XAI_ADDRESS
python src/aixn/core/node.py --miner $MINER_ADDRESS
```

### Get Test Coins

**Testnet only**: Use the built-in faucet to receive 100 test XAI:

```bash
python src/aixn/wallet/cli.py request-faucet --address YOUR_XAI_ADDRESS
```

## Configuration

### Network Selection

```bash
# Testnet (default) - Network ID: 0xABCD
export XAI_NETWORK=testnet
export XAI_RPC_PORT=18546

# Mainnet - Network ID: 0x5841
export XAI_NETWORK=mainnet
export XAI_RPC_PORT=8546
```

### Environment Variables

```bash
XAI_NETWORK          # testnet or mainnet (default: testnet)
XAI_PORT             # P2P port (default: 18545 testnet, 8545 mainnet)
XAI_RPC_PORT         # RPC port (default: 18546 testnet, 8546 mainnet)
XAI_LOG_LEVEL        # DEBUG, INFO, WARNING, ERROR (default: INFO)
XAI_DATA_DIR         # Blockchain data directory
MINER_ADDRESS        # Address to receive mining rewards
```

See `src/aixn/config/` for additional configuration options.

## Performance Optimizations

XAI includes several performance optimizations for production use:

- **Response Caching**: Block explorer uses intelligent caching to reduce node load (configurable TTL)
- **LRU Cache**: Config file loading is cached to avoid repeated I/O operations
- **Connection Pooling**: Efficient HTTP connection reuse for API calls
- **Async Operations**: Support for asynchronous blockchain operations
- **Optimized Validation**: Fast nonce verification and transaction validation

Performance can be tuned via environment variables - see Configuration section.

## Basic Usage Examples

### Create and Manage Wallets

```bash
# Generate a new wallet
python src/aixn/wallet/cli.py generate-address

# Check wallet balance
python src/aixn/wallet/cli.py balance --address YOUR_ADDRESS

# Export private key (secure this safely!)
python src/aixn/wallet/cli.py export-key --address YOUR_ADDRESS
```

### Send Transactions

```bash
# Simple transaction
python src/aixn/wallet/cli.py send \
  --from YOUR_ADDRESS \
  --to RECIPIENT_ADDRESS \
  --amount 10.5 \
  --private-key YOUR_PRIVATE_KEY

# Multi-signature transaction
python src/aixn/wallet/cli.py send-multisig \
  --multisig-address MULTISIG_ADDRESS \
  --to RECIPIENT_ADDRESS \
  --amount 5.0
```

### Atomic Swaps

```bash
# Initiate swap with Bitcoin
python src/aixn/core/atomic_swap.py initiate \
  --asset BTC \
  --amount 0.5 \
  --recipient btc_address_here

# Complete swap
python src/aixn/core/atomic_swap.py complete \
  --swap-id SWAP_ID \
  --secret SECRET_HASH
```

### Query Blockchain Data

```bash
# Get block information
curl http://localhost:18546/block/12345

# Get transaction status
curl http://localhost:18546/transaction/tx_hash

# Get account balance
curl http://localhost:18546/account/YOUR_ADDRESS
```

## Architecture Overview

### System Components

```
XAI Blockchain
├── Consensus Layer
│   ├── Proof-of-Work (SHA-256)
│   ├── Difficulty Adjustment
│   └── Block Validation
├── Core Modules
│   ├── Transaction Pool (Mempool)
│   ├── UTXO Management
│   └── State Database
├── Features
│   ├── Smart Contracts Engine
│   ├── Atomic Swap Handler
│   ├── AI Governance System
│   └── AML Compliance Tools
├── Wallet Layer
│   ├── Key Management
│   ├── Multi-Signature Support
│   └── HD Wallet (BIP-32/BIP-39)
└── P2P Network
    ├── Peer Discovery
    ├── Message Broadcasting
    └── Blockchain Sync
```

### Network Topology

- **Testnet**: Independent test network with relaxed parameters for experimentation
- **Mainnet**: Production network with strict validation rules and permanent consensus
- **RPC Interface**: RESTful API for wallet integration and dApp development

## Testing

Run the comprehensive test suite:

```bash
# Quick test run
python -m pytest

# Full test suite including slow tests
python -m pytest -m "not slow"

# Coverage report
python -m pytest --cov=src --cov-report=html

# Specific module tests
python -m pytest tests/aixn_tests/test_blockchain.py -v
```

## Configuration

### Environment Variables

XAI supports extensive configuration through environment variables:

```bash
# Network Configuration
export XAI_NETWORK=testnet          # Network type: testnet/mainnet
export XAI_NODE_URL=http://localhost:8545  # Node RPC endpoint

# Block Explorer Configuration
export XAI_CACHE_TTL=60             # Response cache TTL in seconds (default: 60)
export XAI_CACHE_SIZE=128           # Maximum cached items (default: 128)

# Node Configuration
export XAI_ENVIRONMENT=development  # Environment: development/staging/production
export XAI_NETWORK_PORT=8545        # Network port
export XAI_NETWORK_RPC_PORT=8546    # RPC port
```

See `.env.example` for complete configuration options.

## Development Setup

### Prerequisites for Development

- Python 3.10+
- pip with virtual environment support
- Git

### Initial Setup

```bash
# Clone and setup
git clone https://github.com/decristofaroj/xai.git
cd xai

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dev dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run tests
python -m pytest

# Format code
black src tests
isort src tests

# Lint code
pylint src
mypy src
```

### Pre-commit Hooks

```bash
# Install pre-commit
pip install pre-commit

# Setup hooks
pre-commit install

# Manual run
pre-commit run --all-files
```

## Documentation

- **[Whitepaper](WHITEPAPER.md)** - Complete technical specification and design rationale
- **[Technical Specifications](TECHNICAL.md)** - Detailed system documentation
- **[Project Structure](PROJECT_STRUCTURE.md)** - Codebase organization and module descriptions
- **[API Documentation](docs/api/)** - REST API endpoint reference
- **[Security Policy](SECURITY.md)** - Vulnerability disclosure and security best practices
- **[Contributing Guide](CONTRIBUTING.md)** - Development guidelines and contribution process

## Network Parameters

### Testnet Configuration

| Parameter | Value |
|-----------|-------|
| Network ID | 0xABCD |
| Port | 18545 |
| RPC Port | 18546 |
| Address Prefix | TXAI |
| Block Time | 2 minutes |
| Max Supply | 121,000,000 XAI |

### Mainnet Configuration

| Parameter | Value |
|-----------|-------|
| Network ID | 0x5841 |
| Port | 8545 |
| RPC Port | 8546 |
| Address Prefix | AIXN |
| Block Time | 2 minutes |
| Max Supply | 121,000,000 XAI |

## Roadmap

### Completed (v0.1.0 - v0.2.0)
- Core blockchain with proof-of-work consensus
- Atomic swap functionality for 11+ cryptocurrencies
- Smart contract engine
- AI governance system
- Time capsule functionality
- Desktop wallet (Electron)
- Block explorer

### In Progress
- Multi-node network deployment
- Security audit completion
- Performance optimization
- Documentation expansion

### Planned
- Hardware wallet support (Ledger, Trezor)
- Light client implementation
- Mobile wallet bridge
- Embedded wallet solutions
- Fiat on-ramp integration (Q4 2026+)

## Contributing

We welcome contributions from developers, researchers, and blockchain enthusiasts.

**Before contributing, please:**

1. Read [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines
2. Review [SECURITY.md](SECURITY.md) for security considerations
3. Check existing issues and pull requests
4. Follow the code style and testing requirements

**Contribution areas:**
- Bug fixes and optimizations
- Documentation improvements
- Test coverage expansion
- Feature implementations
- Security audits

See [CONTRIBUTING.md](CONTRIBUTING.md) for the complete contribution guidelines.

## License

MIT License - See [LICENSE](LICENSE) file for complete text.

This project is released under the MIT License, allowing both commercial and non-commercial use.

## Contact & Support

- **GitHub Issues**: [Report bugs and request features](https://github.com/decristofaroj/xai/issues)
- **Discussions**: [Community discussions and Q&A](https://github.com/decristofaroj/xai/discussions)
- **Email**: Contact maintainers through GitHub issues or discussions
- **Documentation**: [Full documentation site](docs/README.md)

## Security Notice

**Important**: This software is experimental and under active development. Cryptocurrency systems carry inherent risks:

- Test thoroughly on testnet before mainnet use
- Secure your private keys carefully
- Never share seed phrases or private keys
- Understand the technology before committing funds
- Review [SECURITY.md](SECURITY.md) for vulnerability reporting

For security concerns, see [SECURITY.md](SECURITY.md).

## Disclaimer

XAI is a proof-of-concept blockchain implementation. While striving for production quality, users should understand the experimental nature of cryptocurrency systems. The network is under active development and should be used with appropriate caution. The developers make no guarantees regarding future viability, feature availability, or network stability.

## Additional Resources

- **GitHub Repository**: https://github.com/decristofaroj/xai
- **Issue Tracker**: https://github.com/decristofaroj/xai/issues
- **Documentation**: [docs/README.md](docs/README.md)
- **Whitepaper**: [WHITEPAPER.md](WHITEPAPER.md)
- **Community Guidelines**: [docs/aixn_docs/community_expectations.md](docs/aixn_docs/community_expectations.md)

---

**Latest Update**: January 2025 | **Version**: 0.2.0 | **Status**: Testnet Active
