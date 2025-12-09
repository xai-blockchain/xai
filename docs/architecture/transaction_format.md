# Transaction Format (Placeholder)

Intended contents:
- Canonical serialization, fields (sender/recipient/amount/fee/nonce/tx_type/inputs/outputs/metadata)
- Signature/txid calculation and domain separation
- RBF/nonce rules, replay protection, timestamp requirements

See `src/xai/core/transaction.py` and validator tests (`tests_xai_tests/unit/test_transaction_validator.py`, `test_vm_tx_processor.py`, `test_mempool_mixin.py`).***
