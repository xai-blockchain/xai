# XAI Blockchain

![XAI Testnet](https://img.shields.io/badge/Testnet-Active-success)
![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue)
![License MIT](https://img.shields.io/badge/License-MIT-green)

## A Proof-of-Work Blockchain with AI Governance and Integrated Wallets

XAI is a production-ready blockchain implementation featuring proof-of-work consensus, intelligent AI-based governance, atomic swap support for cross-chain trading, and comprehensive wallet management. Built for both individual users and enterprise compliance needs.

---

## 🚀 Get Started in 5 Minutes

### Interactive Setup Wizard (Recommended)

The easiest way to set up your XAI node is using our interactive wizard:

```bash
# Clone and enter the repository
git clone https://github.com/xai-blockchain/xai.git
cd xai

# Run the setup wizard
python scripts/setup_wizard.py
```

The wizard will guide you through:
- Network selection (testnet/mainnet)
- Node mode configuration (full/pruned/light/archival)
- Port configuration with conflict detection
- Wallet creation
- Security configuration
- Optional systemd service installation

**[→ See Setup Wizard Documentation](scripts/SETUP_WIZARD.md)**

### Manual Setup

**New to XAI?** Follow our **[QUICKSTART Guide](docs/QUICKSTART.md)** - get running in 5 minutes:
- ✅ Multiple installation options (pip, Docker, packages)
- ✅ Create your first wallet
- ✅ Get free testnet tokens from faucet
- ✅ Send your first transaction
- ✅ View it in the block explorer

**[→ START HERE: QUICKSTART Guide](docs/QUICKSTART.md)** ← **Complete beginner's guide**

**Choose Your Path:**
- **Desktop/Server:** [QUICKSTART Guide](docs/QUICKSTART.md)
- **Mobile Development:** [Mobile Quick Start](docs/user-guides/mobile_quickstart.md) (React Native/Flutter)
- **Raspberry Pi/IoT:** [Lightweight Node Guide](docs/user-guides/lightweight_node_guide.md)
- **Light Client:** [Light Client Mode](docs/user-guides/light_client_mode.md) (SPV, minimal resources)

### 💧 Testnet Faucet - Get Free XAI

**Official Public Faucet:** https://faucet.xai.network

Get 100 free testnet XAI tokens instantly for testing and development!

#### Quick Access Methods

**1. Web UI (Easiest):**
```
Visit: https://faucet.xai.network
Enter your TXAI address
Click "Request Tokens"
```

**2. Command Line:**
```bash
python src/xai/wallet/cli.py request-faucet --address TXAI_YOUR_ADDRESS
```

**3. Direct API Call:**
```bash
curl -X POST https://faucet.xai.network/claim \
  -H "Content-Type: application/json" \
  -d '{"address": "TXAI_YOUR_ADDRESS"}'

# Or local node faucet:
curl -X POST http://localhost:12001/faucet/claim \
  -H "Content-Type: application/json" \
  -d '{"address": "TXAI_YOUR_ADDRESS"}'
```

#### Faucet Specifications

| Parameter | Value |
|-----------|-------|
| **Amount** | 100 XAI per request |
| **Rate Limit** | 1 request per address per hour |
| **Delivery Time** | Next block (~2 minutes) |
| **Token Value** | Testnet only - no real value |
| **Public Faucet** | https://faucet.xai.network |
| **Local Endpoint** | `http://localhost:12001/faucet/claim` |

**Note:** Testnet XAI has no real value. Use it freely for development and testing.

**[→ Complete Faucet Documentation](docs/user-guides/TESTNET_FAUCET.md)** | **[→ Testnet Guide](docs/user-guides/TESTNET_GUIDE.md)**

---

## Overview

XAI is a Python-based blockchain implementing a production-grade proof-of-work (PoW) chain with a UTXO transaction model, a modular node, wallet CLI, governance primitives, and a simple web explorer. The codebase is structured as a professional Python project with clear separation of concerns and tests.

---

## Key Features

- Proof-of-Work (SHA-256) with adjustable difficulty
- UTXO-based transactions with signatures, inputs/outputs, and RBF flag
- Merkle proofs for light client verification
- Wallet CLI: generate, balance, send, import/export, faucet helper
- Node API (Flask) with CORS policies and request validation
- P2P networking and consensus manager skeleton
- Governance modules (proposal manager, vote locker, quadratic voting)
- Security middleware and structured metrics
- Basic block explorer (Flask)
- Wallet trade manager with advanced order types (TWAP scheduler, VWAP profiles, iceberg, trailing stop)

## Quick Start (< 5 Minutes)

### Prerequisites

- Python 3.10 or higher
- 2GB RAM minimum
- 10GB+ disk space for blockchain data

### Installation

```bash
# From the project root, install dependencies (with constraints for reproducibility)
pip install -c constraints.txt -e ".[dev]"
# Optional: enable QUIC support
pip install -e ".[network]"

# Verify installation
python -m pytest --co -q
```

### Start a Node

```bash
# Run a node (defaults shown)
export XAI_NETWORK=development
xai-node
```

The node will start on port 12001 (RPC), 12002 (P2P), and 12003 (WebSocket).

### Start Mining

```bash
# Generate a wallet address first (or use existing)
xai-wallet generate-address

# Start mining with your address
export MINER_ADDRESS=YOUR_XAI_ADDRESS
xai-node --miner $MINER_ADDRESS
```

### CLI Tooling

After installing the package (`pip install -e .`), three console commands are available:

- `xai` - Main CLI with blockchain, wallet, mining, AI, and network commands
- `xai-wallet` - Wallet-specific CLI (legacy interface)
- `xai-node` - Node management

```bash
# Main CLI (recommended)
xai wallet balance --address YOUR_XAI_ADDRESS
xai blockchain info
xai ai submit-job --model gpt-4 --data "..."

# Legacy wallet CLI (still supported)
xai-wallet request-faucet --address YOUR_XAI_ADDRESS
xai-wallet generate-address
```

For development without installation, use Python module syntax:
```bash
python -m xai.cli.main --help
python -m xai.wallet.cli --help
python -m xai.core.node --help
```

### Get Test Coins

Use the faucet to receive test coins from a configured node:

```bash
# Using main CLI
xai wallet request-faucet --address YOUR_XAI_ADDRESS

# Using legacy wallet CLI
xai-wallet request-faucet --address YOUR_XAI_ADDRESS

# Optional: override API host (defaults to http://localhost:12001)
xai-wallet request-faucet --address YOUR_XAI_ADDRESS --base-url http://remote-node:18545
```

## Configuration

### Network Selection

```bash
# Development (default)
export XAI_NETWORK=development
export XAI_RPC_PORT=18546
```

### Environment Variables

```bash
XAI_NETWORK          # testnet or mainnet (default: testnet)
XAI_PORT             # P2P port (default: 18545 testnet, 8545 mainnet)
XAI_RPC_PORT         # RPC port (default: 18546 testnet, 8546 mainnet)
XAI_LOG_LEVEL        # DEBUG, INFO, WARNING, ERROR (default: INFO)
XAI_DATA_DIR         # Blockchain data directory
MINER_ADDRESS        # Address to receive mining rewards
XAI_PARTIAL_SYNC_ENABLED         # Enable checkpoint/bootstrap flow (default: 1)
XAI_P2P_PARTIAL_SYNC_ENABLED     # Allow P2P manager to run checkpoint sync (default: 1)
XAI_P2P_PARTIAL_SYNC_MIN_DELTA   # Minimum height delta before checkpoint sync (default: 100)
XAI_FORCE_PARTIAL_SYNC           # Force checkpoint bootstrap even if chain is non-empty
```

See `src/xai/config/` for additional configuration options.

### Checkpoint / Partial Sync

- Nodes can bootstrap from signed checkpoints instead of downloading the full chain.
- Configure the variables above plus `CHECKPOINT_QUORUM`, `CHECKPOINT_MIN_PEERS`, and `TRUSTED_CHECKPOINT_PUBKEYS` to enforce quorum/diversity.
- Detailed deployment and operations guidance: `docs/deployment/partial-sync.md`.

## Performance Notes

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
python src/xai/wallet/cli.py generate-address

# Check wallet balance
python src/xai/wallet/cli.py balance --address YOUR_ADDRESS

# Export private key (secure this safely!)
python src/xai/wallet/cli.py export-key --address YOUR_ADDRESS
```

### Send Transactions

```bash
# Secure local signing with hash preview (recommended)
python src/xai/wallet/cli.py send \
  --from YOUR_ADDRESS \
  --to RECIPIENT_ADDRESS \
  --amount 10.5
  # The CLI will fetch your nonce, display the canonical payload and signing
  # hash, require you to type the first 8+ characters of that hash, and only
  # then prompt for your private key (never sent to the node). The node /send
  # endpoint receives a fully signed payload with timestamp/txid.

# Multi-signature transaction (prepare and collect sigs)
python src/xai/wallet/cli.py send-multisig \
  --multisig-address MULTISIG_ADDRESS \
  --to RECIPIENT_ADDRESS \
  --amount 5.0
```

> **API clients:** when submitting directly to `/send`, include `timestamp` (UNIX seconds) and optionally `txid`. When calling `/wallet/sign`, you must display the SHA-256 hash to the signer and pass the acknowledged prefix via `ack_hash_prefix`. See `docs/api/wallet_signing.md` for the canonical payload schema and examples.

### Merkle Proof Verification

```python
from xai.core.blockchain import Block

# Given txid and a block:
valid = Block.verify_merkle_proof(txid, proof, block.merkle_root)
```

### Query Blockchain Data

```bash
# Get block information
curl http://localhost:12001/block/12345

# Get transaction status
curl http://localhost:12001/transaction/tx_hash

# Get account balance
curl http://localhost:12001/account/YOUR_ADDRESS
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

### 🚨 MANDATORY: Local Testing Policy

Run the full test suite locally before making changes:

```bash
# RECOMMENDED: Full CI pipeline (before every push)
make ci

# MINIMUM: Quick validation (1-2 minutes)
make quick

# Windows PowerShell
.\local-ci.ps1          # Full CI
.\local-ci.ps1 -Quick   # Quick validation
```

### Comprehensive Test Suite

```bash
# Quick test run
python -m pytest

# Full test suite including slow tests
python -m pytest -m "not slow"

# Coverage report
python -m pytest --cov=src --cov-report=html

# Specific module tests
python -m pytest tests/xai_tests/test_blockchain.py -v

# Run all quality checks
make all  # Linting + Security + Tests + Coverage

# Run only security tests
pytest -m security

# P2P security-focused subset
make test-p2p-security
# Static P2P hardening check
make p2p-hardening-check
# CI-friendly aggregate (hardening + P2P tests)
scripts/ci/run_p2p_checks.sh
# Install with constraints (pin deps in CI)
scripts/ci/install_with_constraints.sh

# Test with coverage requirement
pytest --cov=src/xai --cov-fail-under=80
```

### Testing Documentation

| Document | Purpose |
|----------|---------|
| **[TESTING-GUIDE.md](TESTING-GUIDE.md)** | Complete testing guide with examples and best practices |
| **[LOCAL-TESTING-QUICK-REF.md](LOCAL-TESTING-QUICK-REF.md)** | Quick reference for common test commands |

### Test Coverage

- **Minimum**: 80% overall coverage
- **Critical Modules**: 90%+ (blockchain, consensus, wallet, security validation)
- **Current**: Tracked in codecov dashboard

### Test Organization

- **Unit Tests**: `pytest -m unit` - Fast, isolated component tests
- **Integration Tests**: `pytest -m integration` - Multi-component interaction
- **Security Tests**: `pytest -m security` - Security validation and attack vectors
- **Performance Tests**: `pytest -m performance` - Benchmarking and stress tests

### Test Requirements for Contributors

Before submitting a PR:
- All tests pass locally: `make ci`
- Coverage meets thresholds: `pytest --cov=src/xai --cov-fail-under=80`
- New code has corresponding tests
- Security tests included for security-critical code
- Pre-commit hooks pass: `pre-commit run --all-files`

## Configuration

### Environment Variables

XAI supports extensive configuration through environment variables:

```bash
# Network Configuration
export XAI_NETWORK=testnet          # Network type: testnet/mainnet
export XAI_NODE_URL=http://localhost:12001  # Node RPC endpoint

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

### Initial Setup

```bash
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

### Local Testing

```bash
python -m pytest -q
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

### Getting Started

- **[QUICKSTART Guide](docs/QUICKSTART.md)** ⭐ - THE complete beginner's guide (5 minutes)
- **[Mobile Quick Start](docs/user-guides/mobile_quickstart.md)** - React Native & Flutter SDK setup
- **[Lightweight Node Guide](docs/user-guides/lightweight_node_guide.md)** - Raspberry Pi, IoT devices
- **[Light Client Mode](docs/user-guides/light_client_mode.md)** - SPV mode for minimal resources
- **[Testnet Guide](docs/user-guides/TESTNET_GUIDE.md)** - Join the testnet, use the faucet, explore
- **[Wallet Setup](docs/user-guides/wallet-setup.md)** - Advanced wallet features and security
- **[Mining Guide](docs/user-guides/mining.md)** - Start mining on XAI

### Technical Documentation

- **[Whitepaper](WHITEPAPER.md)** - Complete technical specification and design rationale
- **[Technical Specifications](TECHNICAL.md)** - Detailed system documentation
- **[Project Structure](PROJECT_STRUCTURE.md)** - Codebase organization and module descriptions
- **[API Documentation](docs/api/)** - REST API endpoint reference
- **[CLI Guide](docs/CLI_GUIDE.md)** - Complete command-line reference

### Development & Security

- **[Security Policy](SECURITY.md)** - Vulnerability disclosure and security best practices
- **[Contributing Guide](CONTRIBUTING.md)** - Development guidelines and contribution process
- **[Testing Guide](TESTING-GUIDE.md)** - Comprehensive testing documentation

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
| Address Prefix | XAI |
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

- Support: Use your organization’s standard support channel
- Documentation: See docs/ and docs/api

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

- Source Code: Provided by your organization
- Issue Tracker: Provided by your organization
- **Documentation**: [docs/README.md](docs/README.md)
- **Whitepaper**: [WHITEPAPER.md](WHITEPAPER.md)
- **Community Guidelines**: [docs/xai_docs/community_expectations.md](docs/xai_docs/community_expectations.md)
- **P2P Security Profiles**: See `docs/security/env_profiles.md` and `.env.example` for validator/seeder/devnet env blocks.

---

**Latest Update**: January 2025 | **Version**: 0.2.0 | **Status**: Testnet Active
