# XAI Blockchain - Testing Framework

## Overview

Comprehensive testing framework for the XAI blockchain covering unit tests, integration tests, security tests, and performance tests.

## Test Suites

### 1. Unit Tests (BlockchainUnitTests)
Tests for individual components:
- ✓ Wallet creation and key generation
- ✓ Transaction signing and verification
- ✓ Block creation and hashing
- ✓ Blockchain initialization
- ✓ Transaction validation
- ✓ Balance calculation from UTXO set

### 2. Integration Tests (BlockchainIntegrationTests)
Tests for complete workflows:
- ✓ Full transaction flow (create, sign, submit, mine)
- ✓ Chain validation
- ✓ Supply cap enforcement
- ✓ Concurrent transaction handling

### 3. Security Tests (SecurityTests)
Tests for attack prevention:
- ✓ Double-spend prevention
- ✓ Invalid signature rejection
- ✓ Block size limit enforcement
- ✓ Dust attack prevention
- ✓ Reorganization depth limits

### 4. Performance Tests (PerformanceTests)
Stress and performance tests:
- ✓ Mining performance (< 60s for 10 transactions)
- ✓ Large transaction volume (50 transactions)
- ✓ Chain validation performance
- ✓ Balance query with 1000 UTXOs

## Running Tests

### Full Test Suite
```bash
cd C:\Users\decri\GitClones\Crypto\xai
python tests/test_framework.py
```

### Individual Component Tests
```bash
# Persistence tests
python core/test_blockchain_persistence.py

# Chain validation tests
python tests/test_chain_validator.py

# Peer discovery tests
python core/test_peer_discovery.py

# Config manager tests
python tests/test_config_manager.py
```

## Test Structure

```
tests/
├── test_framework.py           # Main test runner
├── test_chain_validator.py     # Chain validation tests
├── test_config_manager.py      # Configuration tests
└── README_TESTING.md           # This file

core/
├── test_blockchain_persistence.py  # Persistence tests
└── test_peer_discovery.py          # P2P discovery tests
```

## Expected Results

**Total Tests**: 20+ across all suites
- Unit tests: 6 tests
- Integration tests: 4 tests
- Security tests: 5 tests
- Performance tests: 4 tests

**Performance Benchmarks**:
- Mining 10 transactions: < 60 seconds
- Adding 50 transactions: < 5 seconds
- Validating chain: < 10 seconds
- Balance query (1000 UTXOs): < 0.1 seconds

## Test Coverage

### Core Blockchain
- [x] Genesis block creation
- [x] Block mining with PoW
- [x] Transaction validation
- [x] Signature verification
- [x] UTXO tracking
- [x] Balance calculation
- [x] Supply cap enforcement
- [x] Chain validation

### Security Features
- [x] Double-spend prevention
- [x] Invalid signature rejection
- [x] Block size limits
- [x] Transaction size limits
- [x] Dust attack prevention
- [x] Reorganization protection
- [x] Checkpointing
- [x] Supply validation

### Network Features
- [x] Peer discovery
- [x] Peer quality scoring
- [x] Bootstrap nodes
- [x] Peer diversity

### Persistence
- [x] Save blockchain to disk
- [x] Load blockchain from disk
- [x] Backup creation
- [x] Backup restoration
- [x] Corruption detection
- [x] Automatic recovery

### Advanced Features
- [x] Advanced consensus
- [x] Error recovery
- [x] Monitoring/metrics
- [x] Structured logging
- [x] Configuration management

## Troubleshooting

### Module Import Errors
If you encounter import errors, ensure you're running from the correct directory:
```bash
cd C:\Users\decri\GitClones\Crypto\xai
```

And that all dependencies are installed:
```bash
pip install -r requirements.txt
```

### Test Failures
Common causes:
1. **Genesis block mismatch**: Delete `data/blockchain.json` and retry
2. **Port conflicts**: Ensure no other nodes are running
3. **Permission errors**: Check write permissions in `data/` directory

## Continuous Integration

For CI/CD integration:
```bash
# Run all tests and exit with code 0 on success
python tests/test_framework.py
echo $?  # 0 = success, 1 = failure
```

## Test Reports

Tests generate detailed reports showing:
- Test name and status (✓ or ✗)
- Execution time
- Failure details (if any)
- Performance metrics

Example output:
```
======================================================================
UNIT TESTS - Core Components
======================================================================
  ✓ test_wallet_creation
  ✓ test_transaction_signing
  ✓ test_block_creation
  ✓ test_blockchain_initialization
  ✓ test_transaction_validation
  ✓ test_balance_calculation

======================================================================
TEST SUMMARY
======================================================================
Total tests:  20
Passed:       20 ✓
Failed:       0
Errors:       0
Duration:     45.32s
======================================================================

✓ ALL TESTS PASSED!
```

## Adding New Tests

To add new tests:

1. Create test method in appropriate class:
```python
@staticmethod
def test_new_feature():
    """Test description"""
    # Test code here
    assert condition, "Error message"
    return True
```

2. Test will be automatically discovered if:
   - Method name starts with `test_`
   - Method is static
   - Method returns `True` on success

## Best Practices

1. **Isolation**: Each test should be independent
2. **Cleanup**: Tests should not leave artifacts
3. **Speed**: Keep tests fast (< 1s each if possible)
4. **Clear assertions**: Use descriptive error messages
5. **Edge cases**: Test boundary conditions
6. **Security**: Always test attack scenarios

## Production Testing

Before deployment:
```bash
# Run full test suite
python tests/test_framework.py

# Run security-specific tests
python -m unittest tests.test_framework.SecurityTests

# Run performance benchmarks
python -m unittest tests.test_framework.PerformanceTests
```

## Future Enhancements

- [ ] Add code coverage reporting
- [ ] Add mutation testing
- [ ] Add fuzz testing
- [ ] Add property-based testing
- [ ] Add end-to-end network tests
- [ ] Add load testing with multiple nodes
- [ ] Add chaos engineering tests
