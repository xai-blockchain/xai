# XAI Blockchain

A proof-of-work blockchain with AI governance capabilities and integrated wallet functionality.

## Overview

XAI is a blockchain implementation featuring proof-of-work consensus, smart contracts, atomic swap support for multiple cryptocurrencies, and an AI-based governance system. The project includes wallet management, time-locked transactions, and compliance tooling.

**Current Status**: Version 0.2.0 - Testnet active, mainnet in preparation

## Key Features

- **Consensus**: Proof-of-work with SHA-256 mining
- **Supply**: 121 million XAI maximum supply
- **Block Time**: 2 minutes target
- **Atomic Swaps**: Cross-chain trading with 11 cryptocurrencies
- **Smart Contracts**: On-chain programmable logic
- **AI Governance**: Proposal and voting system with AI analysis
- **Time Capsules**: Time-locked coin storage
- **Multi-signature Wallets**: Shared wallet control
- **Token Burning**: Supply reduction mechanism
- **AML Compliance**: Built-in transaction monitoring and reporting

## Quick Start

### Prerequisites

- Python 3.9+
- 2GB+ RAM
- 10GB+ disk space

### Installation

```bash
git clone https://github.com/decristofaroj/xai.git
cd xai
pip install -r requirements.txt
```

### Run a Node

```bash
python src/aixn/core/node.py
```

The node will start on port 8545 (mainnet) or 18545 (testnet).

### Start Mining

```bash
python src/aixn/core/node.py --miner YOUR_XAI_ADDRESS
```

Replace `YOUR_XAI_ADDRESS` with your wallet address.

### Configuration

Set the network environment variable:

```bash
# For testnet (default)
export XAI_NETWORK=testnet

# For mainnet
export XAI_NETWORK=mainnet
```

Additional configuration options are available in `src/aixn/config/` and can be overridden via environment variables. See `docs/README.md` for configuration details.

## Documentation

- **[Whitepaper](WHITEPAPER.md)** - Comprehensive technical overview
- **[Technical Specifications](TECHNICAL.md)** - Detailed system specifications
- **[Project Structure](PROJECT_STRUCTURE.md)** - Codebase organization
- **[Documentation Hub](docs/README.md)** - All documentation and guides
- **[API Documentation](docs/api/)** - REST API reference
- **[Security Policy](SECURITY.md)** - Vulnerability reporting

## Architecture

```
crypto/
├── src/aixn/          # Core blockchain implementation
│   ├── core/          # Consensus, mining, validation
│   ├── ai/            # AI governance and assistant
│   ├── wallets/       # Wallet management
│   └── config/        # Configuration files
├── tests/             # Test suite
├── scripts/           # Deployment and utility scripts
├── docs/              # Documentation
└── exchange/          # Trading interface (frontend)
```

## Network Information

### Testnet
- Network ID: `0xABCD`
- Port: `18545`
- RPC Port: `18546`
- Address Prefix: `TXAI`
- Faucet: Enabled (100 test XAI)

### Mainnet
- Network ID: `0x5841`
- Port: `8545`
- RPC Port: `8546`
- Address Prefix: `AIXN`

## Testing

Run the test suite:

```bash
# Quick tests
python -m pytest

# All tests including slow tests
python -m pytest -m slow

# Specific test module
python -m pytest tests/aixn_tests/test_blockchain.py
```

## Development

### Setting Up Development Environment

1. Clone the repository
2. Install development dependencies: `pip install -r requirements.txt`
3. Configure testnet: `export XAI_NETWORK=testnet`
4. Run tests to verify setup: `python -m pytest`

### Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.

## Roadmap

### Completed (v0.1.0 - v0.2.0)
- Core blockchain implementation
- Proof-of-work consensus
- Atomic swap support
- Smart contracts
- AI governance system
- Time capsule functionality
- Directory-based blockchain storage
- Electron desktop wallet
- Block explorer

### In Progress
- Multi-node network deployment
- Enhanced security audits
- Documentation improvements
- Performance optimization

### Planned
- Hardware wallet integration (Ledger)
- Light client implementation
- Mobile wallet bridge
- Embedded wallet solutions
- Fiat on-ramp integration (post-Nov 2026)

## License

MIT License - See [LICENSE](LICENSE) file for details

## Security

Report security vulnerabilities to the maintainers. See [SECURITY.md](SECURITY.md) for details.

## Disclaimer

This software is experimental. Users should understand the risks involved in cryptocurrency systems. The network is under active development and should be used with appropriate caution.

## Links

- **GitHub**: https://github.com/decristofaroj/xai
- **Documentation**: [docs/README.md](docs/README.md)
- **Issue Tracker**: https://github.com/decristofaroj/xai/issues

## Community Guidelines

See [docs/aixn_docs/community_expectations.md](docs/aixn_docs/community_expectations.md) for security, transparency, and privacy expectations.
