# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- Nothing yet

### Changed
- Nothing yet

### Fixed
- Nothing yet

---

## [0.2.0] - 2025-12-23

### Added
- **Docusaurus documentation site** with comprehensive technical documentation
- **GitHub Actions CI/CD workflows** for automated testing and deployment
- **Production-ready TypeScript/JavaScript SDK** for application development
- **Biometric authentication framework** for mobile applications with FIDO2/WebAuthn support
- **Hardware wallet UI** for browser-based hardware wallet integration (Ledger, Trezor)
- **Light client verification** supporting both EVM and Cosmos consensus
- **Progressive/chunked state sync** for mobile clients with bandwidth constraints
- **Block pruning system** with configurable retention policies and archival mode
- **QR payment code generation** endpoints for mobile wallet integration
- **XUTX format** (unsigned transaction format, PSBT-equivalent) for offline signing
- **Multisig CLI commands** for M-of-N transactions
- **EIP-712/EIP-191 equivalent** typed data signing for structured messages
- **Interactive setup wizard** with network selection, node configuration, and systemd service installation
- **CLI entry points** (`xai`, `xai-node`, `xai-wallet`) for system-wide command access
- **Header sync progress API** for light client synchronization tracking
- **Payment QR API documentation** with usage examples
- **Kubernetes production-grade infrastructure** including:
  - Vertical Pod Autoscaler (VPA) configuration
  - External Secrets Operator with Vault integration
  - Chaos engineering test suite
  - Advanced network policies with egress restrictions
  - 24-hour soak testing for stability validation
  - Volume snapshot support
  - ArgoCD GitOps integration
- **Comprehensive user guides** for lightweight nodes, testnet onboarding, and mobile quick start
- **SDK verification reports** and quick start guides
- Brand assets and public release templates
- Complete testing documentation and verification scripts

### Changed
- **Enhanced logging system** with structured output and log rotation
- **Improved testnet infrastructure** with comprehensive validation and explorer integration
- **Updated block explorer** with better caching and performance optimization
- **Refined API documentation** with comprehensive endpoint reference
- **Upgraded deployment guides** for AWS, GCP, and Azure platforms

### Fixed
- **UTXO processing order** in block mining for correct transaction sequencing
- **Mining journey test** to expect correct testnet address prefix (TXAI)
- **Network latency test issues** in integration test suite
- **Genesis block validation** in chain structure verification
- **LogRecord 'message' key conflict** in structured logging calls
- **Address checksum verification** in transaction signature validation
- **Kubernetes namespace standardization** to xai-staging across all manifests
- **ArgoCD sync** automation and duplicate ConfigMap removal
- **All critical security blockers** for mainnet readiness including:
  - Genesis block previous_hash validation
  - Malformed signature handling
  - Comprehensive timestamp validation for blocks
  - BlockHeader validation for malformed inputs
  - SPV checkpoint test rewrites for current API
- **JWT expiration security** in API authentication

### Security
- **Wallet signing protection**: `/wallet/sign` now requires `ack_hash_prefix` to prevent blind signing
- **Transaction validation**: `/send` endpoint enforces timestamp/txid validation for every payload
- **Security audit framework** with pre-commit hooks and Bandit scanning
- **Comprehensive validation** for genesis blocks, signatures, and timestamps
- **Hardware wallet integration** with secure key management
- **Advanced network policies** in Kubernetes for production security
- **Chaos engineering hardening** with network partition and failure testing

---

## [0.1.0] - 2025-01-15

### Added
- Initial blockchain implementation with proof-of-work consensus (SHA-256)
- UTXO-based transaction model with inputs, outputs, and RBF support
- Merkle proof system for light client verification
- Wallet CLI with key generation, balance checking, and transaction creation
- HD wallet support (BIP-32/BIP-39 compatible) with mnemonic seed phrases
- Node API (Flask) with CORS policies and request validation
- P2P networking with peer discovery and message broadcasting
- Consensus manager with difficulty adjustment
- Governance modules:
  - Proposal manager for on-chain governance
  - Vote locker for stake-based voting
  - Quadratic voting implementation
- AI integration components for intelligent governance
- Atomic swap support for cross-chain trading (11+ cryptocurrencies)
- Basic block explorer (Flask) with transaction and block browsing
- Wallet trade manager with advanced order types:
  - TWAP (Time-Weighted Average Price) scheduler
  - VWAP (Volume-Weighted Average Price) profiles
  - Iceberg orders
  - Trailing stop orders
- Security middleware and structured metrics
- Faucet functionality for testnet token distribution
- Docker support for containerized deployment
- Basic Kubernetes manifests
- Prometheus monitoring integration
- Comprehensive test suite with pytest
- Pre-commit hooks for code quality (black, isort, pylint, flake8, mypy)

### Security
- Cryptographic primitives with secp256k1 for signatures
- Secure key derivation with Argon2
- AML compliance tools framework
- Input validation across all API endpoints

---

## Links

- [0.2.0]: https://github.com/xai-blockchain/xai/releases/tag/v0.2.0
- [0.1.0]: https://github.com/xai-blockchain/xai/releases/tag/v0.1.0
