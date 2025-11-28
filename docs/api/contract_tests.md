# API & P2P Contract Tests

## P2P Handshake Contracts
- `X-Node-Version` required; unknown versions rejected.
- `X-Node-Features` validated against supported set.
- Signature headers required; timestamp skew enforced.
- Tests: `tests/xai_tests/unit/test_p2p_version_negotiation.py`.

## Security Event Contracts
- SecurityEventRouter metrics increment for `p2p.*` events.
- Webhook sink only forwards severities WARNING+.
- Tests: `tests/xai_tests/unit/test_p2p_security_probes.py`, `tests/xai_tests/unit/test_security_webhook_sink.py`.

## Trust Store Rotation Contracts
- Rotation tool merges new + existing, optional drop of old.
- Tests: `tests/tools/test_trust_store_rotate.py`.

## Determinism Contracts
- Genesis load produces deterministic tip/UTXO digest across clean data dirs.
- Transaction hash deterministic for identical inputs.
- Tests: `tests/xai_tests/unit/test_blockchain_determinism.py`, `tests/xai_tests/unit/test_transaction_determinism.py`.
