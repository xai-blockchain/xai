# XAI Module Reference Index

High-level map of core modules and responsibilities.

## Core
- `src/xai/core/blockchain.py` – Orchestrates block/tx lifecycle, consensus hooks, storage integration.
- `src/xai/core/blockchain_components/` – Block, mempool, mining, validation mixins.
- `src/xai/core/transaction.py` – Transaction model, signing/verification, metadata.
- `src/xai/core/transaction_validator.py` – Admission checks, signature validation, nonce/fee rules.
- `src/xai/core/validation.py` – Input validation (amounts, addresses, hex), `AddressFormatValidator`.
- `src/xai/core/crypto_utils.py` – Key gen, signing, verification (secp256k1, low-S enforcement).

## Networking & P2P
- `src/xai/core/node_p2p.py` – P2P server, peer handshake, gossip.
- `src/xai/network/peer_manager.py` – Peer tracking, reputation, anti-replay.
- `src/xai/core/security/p2p_security.py` – Message signing, rate limits, abuse detection.

## API & Auth
- `src/xai/core/node_api.py` – Route registrar, request guards, admin scope checks.
- `src/xai/core/api_routes/` – Modular Flask route handlers (transactions, mining, admin, recovery, etc.).
- `src/xai/core/api_auth.py` – API key storage, scope-aware authorization, admin tokens.
- `src/xai/core/jwt_auth_manager.py` – JWT issuance/validation with roles.

## Wallets
- `src/xai/wallet/wallet.py` – Wallet model, encryption, derivation.
- `src/xai/wallet/multisig_wallet.py` – M-of-N multisig flows.
- `src/xai/wallet/cli.py` – Wallet CLI (hardware, signing, verification).

## Security
- `src/xai/security/tss_production.py` – Shamir shares + threshold signatures.
- `src/xai/security/circuit_breaker.py` – Circuit breaker primitive.
- `src/xai/blockchain/emergency_pause.py` – Persistent pause manager with circuit breaker integration.
- `src/xai/core/security_middleware.py` – Session/IP binding, rate limiting, CSRF, headers.
- `src/xai/core/security_validation.py` – Sanitization and validation wrappers.

## Monitoring
- `src/xai/core/prometheus_metrics.py` – Metric definitions and updates.
- `monitoring/` – Prometheus alerts, Grafana dashboards, runbooks.

## DeFi & EVM
- `src/xai/core/defi/` – Staking, oracle, circuit breakers, access control.
- `src/xai/core/vm/` – VM/executor, EVM interpreter/opcodes.
