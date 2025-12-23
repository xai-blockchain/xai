# XAI Blockchain Testing Guide

Complete guide to testing the XAI blockchain implementation.

---

## Test Organization

### Test Structure

```
tests/
├── xai_tests/          # Main test suite
│   ├── unit/           # Unit tests (fast, isolated)
│   ├── integration/    # Multi-component tests
│   ├── security/       # Security validation tests
│   ├── performance/    # Benchmarking and stress tests
│   ├── consensus/      # Consensus algorithm tests
│   ├── contracts/      # Smart contract tests
│   └── fuzzing/        # Fuzzing and property-based tests
├── api/                # API endpoint tests
├── e2e/                # End-to-end scenarios
├── chaos/              # Chaos engineering tests
└── testnet/            # Testnet-specific tests
```

### Test Markers

Tests are categorized using pytest markers:

- `@pytest.mark.unit` - Fast, isolated component tests
- `@pytest.mark.integration` - Multi-component interaction tests
- `@pytest.mark.security` - Security validation and attack vectors
- `@pytest.mark.performance` - Benchmarking and stress tests
- `@pytest.mark.slow` - Long-running tests (excluded by default)
- `@pytest.mark.destructive` - Tests that modify/corrupt data
- `@pytest.mark.atomic_swaps` - Atomic swap scenarios

---

## Running Tests

### Quick Test Commands

```bash
# Run all tests (excluding slow tests)
pytest

# Run with coverage report
pytest --cov=src --cov-report=html

# Run specific test category
pytest -m unit              # Unit tests only
pytest -m integration       # Integration tests only
pytest -m security          # Security tests only

# Run specific test file
pytest tests/xai_tests/test_blockchain.py -v

# Run tests matching pattern
pytest -k "test_wallet" -v
```

### Full CI Pipeline

```bash
# RECOMMENDED: Run before every commit
make ci

# Quick validation (1-2 minutes)
make quick

# Windows PowerShell
.\local-ci.ps1          # Full CI
.\local-ci.ps1 -Quick   # Quick validation
```

### Specialized Test Suites

```bash
# P2P security tests
make test-p2p-security

# P2P hardening check (static analysis)
make p2p-hardening-check

# Combined P2P checks
make ci-p2p
```

---

## Test Categories

### Unit Tests (tests/xai_tests/unit/)

Fast, isolated tests for individual components:

```bash
pytest tests/xai_tests/unit/ -v
```

**Coverage areas:**
- Blockchain core logic
- Transaction validation
- Wallet operations
- Cryptographic primitives
- UTXO management

### Integration Tests (tests/xai_tests/integration/)

Multi-component interaction tests:

```bash
pytest tests/xai_tests/integration/ -v
```

**Coverage areas:**
- API endpoint integration
- P2P networking
- Consensus mechanisms
- Block propagation
- State synchronization

### Security Tests (tests/xai_tests/security/)

Security validation and attack simulation:

```bash
pytest -m security
```

**Coverage areas:**
- Signature verification
- Nonce replay protection
- Input validation
- Access control
- Rate limiting

### Performance Tests (tests/xai_tests/performance/)

Benchmarking and stress testing:

```bash
pytest -m performance
```

**Coverage areas:**
- Transaction throughput
- Block validation speed
- Memory usage
- Network latency
- Database performance

---

## Coverage Requirements

### Minimum Coverage Thresholds

- **Overall**: 80% line coverage
- **Critical modules**: 90%+ coverage required
  - `src/xai/core/blockchain.py`
  - `src/xai/core/transaction.py`
  - `src/xai/core/wallet.py`
  - `src/xai/core/validation.py`
  - `src/xai/security/`

### Generate Coverage Report

```bash
# HTML report
pytest --cov=src/xai --cov-report=html
open htmlcov/index.html

# Terminal report
pytest --cov=src/xai --cov-report=term-missing

# Fail if coverage below 80%
pytest --cov=src/xai --cov-fail-under=80
```

---

## Writing Tests

### Test Structure Template

```python
import pytest
from xai.core.blockchain import Blockchain

class TestBlockchain:
    """Test suite for blockchain core functionality."""

    @pytest.fixture
    def blockchain(self):
        """Create a fresh blockchain instance for testing."""
        return Blockchain(test_mode=True)

    @pytest.mark.unit
    def test_genesis_block(self, blockchain):
        """Test genesis block creation."""
        assert blockchain.get_height() == 0
        genesis = blockchain.get_block(0)
        assert genesis.index == 0
        assert genesis.previous_hash == "0"

    @pytest.mark.security
    def test_invalid_signature_rejected(self, blockchain):
        """Test that transactions with invalid signatures are rejected."""
        tx = create_invalid_transaction()
        with pytest.raises(ValidationError):
            blockchain.add_transaction(tx)
```

### Best Practices

1. **Use fixtures** for test data and setup
2. **Mark tests appropriately** with pytest markers
3. **Test both success and failure cases**
4. **Mock external dependencies** (network, filesystem)
5. **Keep tests isolated** - no shared state
6. **Use descriptive test names** - explain what is being tested

---

## Testing Workflows

### Pre-Commit Testing

```bash
# Run pre-commit hooks
pre-commit run --all-files

# Quick test suite
pytest -m "unit and not slow" --maxfail=1
```

### Pull Request Testing

```bash
# Full test suite with coverage
make ci

# Ensure coverage threshold
pytest --cov=src/xai --cov-fail-under=80

# Security audit
bandit -r src/
```

### Release Testing

```bash
# All tests including slow tests
pytest -m ""

# Performance regression tests
pytest -m performance --benchmark-only

# Chaos engineering tests
pytest tests/chaos/ -v
```

---

## Troubleshooting

### Common Issues

**Tests fail with "Address already in use"**
- Kill existing node processes: `pkill -f xai-node`
- Use different test ports in configuration

**Tests hang indefinitely**
- Check for deadlocks in P2P networking code
- Increase timeouts for slow CI environments
- Use `pytest --timeout=300` to enforce time limits

**Coverage report missing files**
- Ensure all source files are imported during tests
- Check coverage configuration in `pyproject.toml`
- Run: `pytest --cov=src --cov-report=term-missing`

---

## Additional Resources

- **Integration Testing Guide**: `tests/INTEGRATION_TESTING_GUIDE.md`
- **CI Scripts**: `scripts/ci/`
- **Test Utilities**: `tests/conftest.py`
- **Coverage Dashboard**: `htmlcov/index.html` (after running tests)

---

*Last Updated: January 2025 | XAI Version: 0.2.0*
