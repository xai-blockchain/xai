# XAI Blockchain Test Suite

## Overview

Comprehensive test suite for the XAI blockchain, covering core functionality, wallet operations, token burning, and security features.

## Test Coverage

### Core Blockchain Tests (`test_blockchain.py`)
✅ Blockchain initialization
✅ Genesis block creation
✅ Block mining and proof-of-work
✅ Transaction creation and signing
✅ Transaction validation
✅ Balance tracking (UTXO)
✅ Chain validation
✅ 121M supply cap enforcement
✅ Halving schedule (12 XAI → 6 → 3...)
✅ UTC timestamp verification
✅ Multiple block mining

### Wallet Tests (`test_wallet.py`)
✅ Wallet creation and initialization
✅ Unique key generation
✅ Address format validation (XAI/TXAI prefix)
✅ Private key length (64 hex chars)
✅ Public key length (128 hex chars)
✅ Transaction signing
✅ Signature verification
✅ Receiving XAI
✅ Sending XAI
✅ Security (cannot forge signatures)
✅ Immutability (cannot modify signed transactions)
✅ Wallet data serialization

### Token Burning Tests (`test_token_burning.py`)
✅ Engine initialization
✅ Service pricing
✅ Service consumption
✅ 50/50 burn/miner distribution
✅ USD-pegged dynamic pricing
✅ Burn statistics tracking
✅ Multiple burns tracking
✅ Service usage breakdown
✅ Anonymous tracking (no personal data)
✅ UTC timestamps
✅ Burn history retrieval
✅ No treasury allocation (dev funded separately)

## Installation

### Install Test Dependencies

```bash
cd tests
pip install -r requirements_test.txt
```

Or install individually:
```bash
pip install pytest pytest-cov pytest-timeout pytest-mock
```

## Running Tests

### Run All Tests

```bash
# From project root
pytest tests/

# Or from tests directory
cd tests
pytest
```

### Run Specific Test File

```bash
pytest tests/test_blockchain.py
pytest tests/test_wallet.py
pytest tests/test_token_burning.py
```

### Run Specific Test Class

```bash
pytest tests/test_blockchain.py::TestBlockchainCore
pytest tests/test_wallet.py::TestWalletCreation
```

### Run Specific Test Function

```bash
pytest tests/test_blockchain.py::TestBlockchainCore::test_blockchain_initialization
```

### Run with Coverage Report

```bash
pytest tests/ --cov=core --cov-report=html
```

This generates a coverage report in `htmlcov/index.html`.

### Run with Verbose Output

```bash
pytest tests/ -v
```

### Run Faster (Parallel Execution)

```bash
pip install pytest-xdist
pytest tests/ -n auto
```

## Test Organization

```
tests/
├── README.md                   # This file
├── pytest.ini                  # Pytest configuration
├── requirements_test.txt       # Test dependencies
├── test_blockchain.py          # Core blockchain tests
├── test_wallet.py              # Wallet tests
└── test_token_burning.py       # Token burning tests
```

## Writing New Tests

### Test File Naming

- Test files must start with `test_`
- Example: `test_new_feature.py`

### Test Class Naming

- Test classes must start with `Test`
- Example: `class TestNewFeature:`

### Test Function Naming

- Test functions must start with `test_`
- Example: `def test_new_functionality():`

### Example Test

```python
import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

from blockchain import Blockchain

class TestNewFeature:
    """Test new feature"""

    def test_feature_works(self):
        """Test that new feature works correctly"""
        bc = Blockchain()

        # Your test logic here
        assert True, "Feature should work"
```

## Test Markers

Use markers to categorize tests:

```python
@pytest.mark.blockchain
def test_blockchain_feature():
    pass

@pytest.mark.security
def test_security_feature():
    pass

@pytest.mark.slow
def test_slow_operation():
    pass
```

Run tests by marker:
```bash
pytest -m blockchain
pytest -m security
pytest -m "not slow"
```

## Continuous Integration

### Pre-Commit Testing

Before committing, run:
```bash
pytest tests/ -v
```

All tests must pass before committing!

### Coverage Requirements

Maintain at least 80% code coverage:
```bash
pytest tests/ --cov=core --cov-report=term-missing
```

## Common Test Patterns

### Testing Blockchain Operations

```python
def test_blockchain_operation():
    bc = Blockchain()
    wallet = Wallet()

    # Mine a block
    block = bc.mine_pending_transactions(wallet.address)

    # Verify
    assert block.index > 0
    assert bc.get_balance(wallet.address) > 0
```

### Testing Transactions

```python
def test_transaction():
    wallet1 = Wallet()
    wallet2 = Wallet()

    tx = Transaction(wallet1.address, wallet2.address, 10.0, 0.24)
    tx.sign_transaction(wallet1.private_key)

    assert tx.verify_signature()
```

### Testing Token Burning

```python
def test_burning():
    engine = TokenBurningEngine()

    result = engine.consume_service(
        wallet_address="XAI123...",
        service_type=ServiceType.AI_QUERY_SIMPLE
    )

    assert result['success'] == True
    assert result['burned_xai'] > 0
```

## Troubleshooting

### Import Errors

If you get import errors:
```python
# Add this at top of test file
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))
```

### Test Discovery Issues

Make sure:
- Test files start with `test_`
- Test functions start with `test_`
- You're running pytest from correct directory

### Slow Tests

Some blockchain tests may be slow due to mining. Use markers:
```python
@pytest.mark.slow
def test_mine_many_blocks():
    pass
```

Skip slow tests:
```bash
pytest -m "not slow"
```

## Test Results

### Success Output

```
========================= test session starts =========================
tests/test_blockchain.py ............                          [ 40%]
tests/test_wallet.py ........                                  [ 66%]
tests/test_token_burning.py ..........                         [100%]

========================= 30 passed in 2.34s ==========================
```

### Failure Output

```
FAILED tests/test_blockchain.py::TestBlockchainCore::test_supply_cap
    AssertionError: Max supply should be 121M
    assert 120000000.0 == 121000000.0
```

## Adding Tests for New Features

When adding new features:

1. **Create test file**: `tests/test_new_feature.py`
2. **Write tests first** (TDD approach)
3. **Implement feature** until tests pass
4. **Run all tests** to ensure no regressions
5. **Check coverage**: `pytest --cov`
6. **Document** what you tested

## Security Testing

### Test Security Features

```python
def test_cannot_forge_signature():
    """Ensure signatures cannot be forged"""
    wallet1 = Wallet()
    wallet2 = Wallet()

    tx = Transaction(wallet1.address, "XAI...", 10.0)
    tx.sign_transaction(wallet2.private_key)  # Wrong wallet

    assert not tx.verify_signature()
```

### Test Anonymity

```python
def test_no_personal_data():
    """Ensure no personal data is stored"""
    engine = TokenBurningEngine()
    result = engine.consume_service(...)

    assert 'ip_address' not in result
    assert 'user_name' not in result
```

## Next Steps

After implementing basic tests:

1. ✅ Add integration tests
2. ✅ Add performance tests
3. ✅ Add security audit tests
4. ✅ Set up CI/CD pipeline
5. ✅ Implement automated testing

## References

- [Pytest Documentation](https://docs.pytest.org/)
- [Python Testing Best Practices](https://docs.python-guide.org/writing/tests/)

---

**Last Updated:** 2025-11-09 (UTC)
