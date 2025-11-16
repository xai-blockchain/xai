# Testing Guide

## Running Tests

### Quick Start

```bash
# Run all tests
pytest

# Run specific test categories
pytest -m unit           # Unit tests only
pytest -m integration    # Integration tests only
pytest -m performance    # Performance tests only
pytest -m security       # Security tests only

# Run tests with coverage
pytest --cov=src/aixn --cov-report=html

# Run tests in parallel
pytest -n auto
```

### Test Organization

```
tests/
├── aixn_tests/
│   ├── unit/              # Unit tests
│   ├── integration/       # Integration tests
│   ├── performance/       # Performance benchmarks
│   ├── security/          # Security tests
│   └── stubs/             # Test stubs and mocks
```

### Test Markers

- `@pytest.mark.unit` - Fast, isolated unit tests
- `@pytest.mark.integration` - Tests requiring multiple components
- `@pytest.mark.performance` - Performance benchmarks
- `@pytest.mark.security` - Security-focused tests
- `@pytest.mark.slow` - Long-running tests (skipped by default)

### Writing Tests

```python
import pytest
from aixn.core.blockchain import Blockchain

@pytest.mark.unit
def test_blockchain_initialization():
    """Test blockchain initialization"""
    bc = Blockchain()
    assert len(bc.chain) == 1
    assert bc.chain[0].index == 0

@pytest.mark.integration
def test_transaction_flow():
    """Test complete transaction flow"""
    bc = Blockchain()
    # ... test implementation
```

### CI/CD Integration

Tests run automatically on:
- Push to main/develop branches
- Pull requests
- Daily at 2 AM UTC

Coverage reports are uploaded to Codecov automatically.

## Test Requirements

All code changes should:
- Have corresponding tests
- Maintain >80% code coverage
- Pass all existing tests
- Follow testing best practices

## Debugging Tests

```bash
# Run with verbose output
pytest -v

# Show print statements
pytest -s

# Stop on first failure
pytest -x

# Run last failed tests
pytest --lf

# Run specific test
pytest tests/aixn_tests/test_blockchain.py::TestBlockchainCore::test_genesis_block
```

## Performance Testing

```bash
# Run benchmarks
pytest -m performance --benchmark-only

# Compare benchmarks
pytest -m performance --benchmark-compare
```

## Security Testing

```bash
# Run security tests
pytest -m security

# Run with Bandit
bandit -r src/

# Run with Safety
safety check
```
