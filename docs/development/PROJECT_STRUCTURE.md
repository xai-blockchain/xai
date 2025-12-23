# XAI Project Structure

Complete guide to the XAI blockchain codebase organization.

---

## Repository Overview

```
xai/
├── src/xai/              # Main source code
├── tests/                # Test suite
├── docs/                 # Documentation
├── scripts/              # Utility scripts
├── deploy/               # Deployment configs
├── k8s/                  # Kubernetes manifests
├── monitoring/           # Grafana/Prometheus
├── explorer/             # Block explorer
└── sdk/                  # Client SDKs
```

---

## Source Code (src/xai/)

### Core Modules (src/xai/core/)

**Blockchain Components**:
- `blockchain.py` - Main blockchain class, consensus logic
- `transaction.py` - Transaction model and validation
- `block_header.py` - Block header structure
- `block_index.py` - Block indexing for fast retrieval

**Node Components**:
- `node.py` - Main node orchestrator
- `node_api.py` - REST API endpoints (Flask)
- `node_p2p.py` - P2P networking and peer management
- `node_consensus.py` - Consensus algorithm implementation
- `node_mining.py` - Mining logic

**Validation & Security**:
- `transaction_validator.py` - Transaction validation pipeline
- `chain_validator.py` - Blockchain validation
- `validation.py` - General validation utilities
- `security_middleware.py` - API security layer
- `nonce_tracker.py` - Replay attack prevention

**Storage & State**:
- `blockchain_storage.py` - Persistent storage layer
- `blockchain_persistence.py` - Data serialization
- `utxo_manager.py` - UTXO set management
- `state_manager.py` - Blockchain state tracking

**Wallet & Keys**:
- `wallet.py` - Wallet implementation
- `hardware_wallet.py` - Ledger/Trezor support
- `wallet_encryption.py` - AES encryption for exports
- `typed_signing.py` - Type-safe transaction signing

**Smart Contracts & EVM**:
- `vm/` - EVM interpreter and opcodes
- `contracts/` - Smart contract management
- `account_abstraction.py` - ERC-4337 support

**Governance & AI**:
- `ai_governance.py` - AI-powered governance system
- `ai_safety_controls.py` - AI safety mechanisms
- `ai_trading_bot.py` - Automated trading strategies

**Monitoring & Metrics**:
- `monitoring.py` - System monitoring
- `prometheus_metrics.py` - Prometheus integration
- `logging_config.py` - Structured logging

**Network & Sync**:
- `checkpoint_sync.py` - Fast blockchain sync
- `chunked_sync.py` - Chunked data transfer
- `peer_discovery.py` - P2P peer discovery
- `p2p_security.py` - P2P security hardening

### Wallet Module (src/xai/wallet/)

- `cli.py` - Wallet command-line interface
- `multisig_wallet.py` - Multi-signature support
- `offline_signing.py` - Cold wallet signing
- `spending_limits.py` - Transaction limits
- `time_locked_withdrawals.py` - Time-locked funds

### CLI Module (src/xai/cli/)

- `main.py` - Main CLI entry point (`xai` command)
- Enhanced CLI with rich terminal output
- Sub-commands for wallet, blockchain, mining, AI

### SDK Module (src/xai/sdk/)

**Python SDK** (`sdk/python/`):
- Client library for XAI integration
- Transaction building and signing
- Wallet management utilities

**TypeScript SDK** (`sdk/typescript/`):
- JavaScript/TypeScript client
- Web3-compatible interface
- Error handling and types

**Biometric SDK** (`sdk/biometric/`):
- Mobile biometric authentication
- Secure key storage
- Platform-specific integrations

### Additional Modules

**Mobile** (`src/xai/mobile/`):
- Mobile wallet bridge
- Push notification service
- Mobile-optimized API

**Merchant** (`src/xai/merchant/`):
- Payment processing
- Invoice generation
- Merchant integrations

**Network** (`src/xai/network/`):
- Network utilities
- Protocol definitions

**Tools** (`src/xai/tools/`):
- Development utilities
- Debugging tools

---

## Tests (tests/)

### Test Organization

```
tests/
├── xai_tests/          # Main test suite
│   ├── unit/           # Unit tests (fast, isolated)
│   │   ├── test_blockchain_core.py
│   │   ├── test_wallet_operations.py
│   │   └── test_transaction_validation.py
│   ├── integration/    # Integration tests
│   │   ├── test_api_integration.py
│   │   └── test_p2p_network.py
│   ├── security/       # Security tests
│   │   ├── test_signature_verification.py
│   │   └── test_replay_protection.py
│   ├── performance/    # Performance benchmarks
│   ├── consensus/      # Consensus algorithm tests
│   ├── contracts/      # Smart contract tests
│   └── fuzzing/        # Fuzz testing
├── api/                # API endpoint tests
├── e2e/                # End-to-end scenarios
├── chaos/              # Chaos engineering tests
└── testnet/            # Testnet-specific tests
```

**Key Test Files**:
- `conftest.py` - Shared fixtures and configuration
- `test_atomic_swaps.py` - Atomic swap scenarios
- `test_cli_commands.py` - CLI command testing
- `test_destructive_longrunning.py` - Stress tests

---

## Documentation (docs/)

### User Guides (docs/user-guides/)
- `QUICKSTART.md` - 5-minute getting started guide
- `TESTNET_GUIDE.md` - Testnet usage guide
- `wallet-setup.md` - Wallet configuration
- `mining.md` - Mining instructions
- `mobile_quickstart.md` - Mobile development
- `lightweight_node_guide.md` - IoT/Raspberry Pi
- `light_client_mode.md` - SPV client mode

### API Documentation (docs/api/)
- `rest-api.md` - REST API reference
- `sdk.md` - SDK usage guides
- `wallet_signing.md` - Transaction signing

### Advanced Topics (docs/advanced/)
- `atomic-swaps.md` - Cross-chain trading
- `htlc-contracts.md` - HTLC implementation

### Operations (docs/ops/)
- `backup_restore.md` - Backup procedures
- `api_key_rotation.md` - Security operations
- `utxo_audit.md` - UTXO set auditing

### Architecture (docs/architecture/)
- System design documentation
- Component interaction diagrams

---

## Scripts (scripts/)

**Setup Scripts**:
- `setup_wizard.py` - Interactive node setup
- `setup-crypto-project.sh` - Project initialization

**CI/CD Scripts** (`scripts/ci/`):
- `run_p2p_checks.sh` - P2P security validation
- `install_with_constraints.sh` - Dependency installation

**Utility Scripts**:
- Node management
- Testing utilities
- Deployment helpers

---

## Deployment (deploy/)

**Docker Configurations**:
- Multi-stage Dockerfiles
- Docker Compose setups
- Container orchestration

**Kubernetes** (k8s/):
- StatefulSet manifests
- Service definitions
- ConfigMaps and Secrets
- Ingress rules

---

## Monitoring (monitoring/)

**Prometheus**:
- Metrics collection configuration
- Alert rules

**Grafana**:
- Pre-built dashboards
- Visualization configs

---

## Explorer (explorer/)

**Backend** (`explorer/backend/`):
- Flask API server
- Database models
- Indexing service

**Frontend**:
- Web UI for blockchain exploration
- Real-time block updates
- Transaction search

---

## Configuration Files

**Root Level**:
- `pyproject.toml` - Python project configuration
- `pytest.ini` - Test configuration
- `requirements.txt` - Python dependencies
- `constraints.txt` - Dependency version pins
- `.env.example` - Environment variable template
- `Makefile` - Build and test targets

**Code Quality**:
- `.pylintrc` - Pylint configuration
- `mypy.ini` - Type checking configuration
- `.pre-commit-config.yaml` - Git hooks
- `.bandit` - Security scanning config

---

## Key Entry Points

**Running the Node**:
```bash
python -m xai.core.node          # Main node
python src/xai/START_TESTNET.sh  # Testnet script
```

**CLI Tools**:
```bash
xai                              # Main CLI
xai-wallet                       # Wallet CLI
xai-node                         # Node management
```

**Testing**:
```bash
pytest                           # Run tests
make ci                          # Full CI pipeline
```

---

*Last Updated: January 2025 | XAI Version: 0.2.0*
