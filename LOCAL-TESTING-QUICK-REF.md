# Local Testing Quick Reference

Fast reference for common testing commands and workflows.

---

## Quick Commands

### Run All Tests
```bash
pytest                                    # Exclude slow tests (default)
pytest -m ""                              # Include all tests
pytest -v                                 # Verbose output
```

### Test by Category
```bash
pytest -m unit                            # Unit tests only
pytest -m integration                     # Integration tests
pytest -m security                        # Security tests
pytest -m performance                     # Performance tests
pytest -m "not slow"                      # Exclude slow tests
```

### Coverage Reports
```bash
pytest --cov=src                          # Basic coverage
pytest --cov=src --cov-report=html        # HTML report
pytest --cov=src --cov-fail-under=80      # Fail if <80%
open htmlcov/index.html                   # View report
```

### Specific Tests
```bash
pytest tests/xai_tests/test_blockchain.py              # Single file
pytest tests/xai_tests/test_blockchain.py::test_name   # Single test
pytest -k "wallet"                                      # Match pattern
pytest tests/xai_tests/unit/                           # Directory
```

---

## CI Workflows

### Pre-Commit (Fast)
```bash
make quick                                # Quick validation (1-2 min)
pytest -m "unit and not slow" --maxfail=1 # Stop on first failure
```

### Full CI (Before Push)
```bash
make ci                                   # Complete CI pipeline
./local-ci.ps1                            # Windows PowerShell
```

### P2P Security
```bash
make test-p2p-security                    # P2P tests
make p2p-hardening-check                  # Static checks
make ci-p2p                               # Combined
```

---

## Common Patterns

### Test with Output
```bash
pytest -v -s                              # Show print statements
pytest --log-cli-level=DEBUG              # Show debug logs
pytest --tb=short                         # Short traceback
```

### Parallel Execution
```bash
pytest -n auto                            # Auto-detect CPUs
pytest -n 4                               # Use 4 workers
```

### Stop Early
```bash
pytest --maxfail=1                        # Stop on first failure
pytest -x                                 # Same as above
```

### Rerun Failed
```bash
pytest --lf                               # Last failed
pytest --ff                               # Failed first, then rest
```

---

## Coverage Targets

| Module | Minimum | Target |
|--------|---------|--------|
| Overall | 80% | 85% |
| blockchain.py | 90% | 95% |
| transaction.py | 90% | 95% |
| wallet.py | 90% | 95% |
| validation.py | 90% | 95% |

---

## Test Markers Reference

```python
@pytest.mark.unit              # Fast unit test
@pytest.mark.integration       # Integration test
@pytest.mark.security          # Security validation
@pytest.mark.performance       # Performance benchmark
@pytest.mark.slow              # Slow test (>5s)
@pytest.mark.destructive       # Modifies data
@pytest.mark.atomic_swaps      # Atomic swap test
```

---

## Troubleshooting

### Port Already in Use
```bash
pkill -f xai-node              # Kill existing nodes
lsof -i :12001                 # Check port usage
```

### Tests Hang
```bash
pytest --timeout=300           # 5-minute timeout per test
pytest -x                      # Stop on first hang
```

### Coverage Missing Files
```bash
pytest --cov=src --cov-report=term-missing   # Show missing lines
```

### Clean Test Environment
```bash
rm -rf test_data_*             # Remove test data
rm -rf .pytest_cache           # Clear cache
rm -rf htmlcov/                # Remove old coverage
```

---

## Pre-Commit Hooks

### Install
```bash
pip install pre-commit
pre-commit install
```

### Run Manually
```bash
pre-commit run --all-files     # All hooks
pre-commit run black           # Just black
pre-commit run pylint          # Just pylint
```

---

## Test Data

### Test Addresses (Testnet)
```
TXAI1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa  # Test wallet 1
TXAI1recipient123...                    # Test wallet 2
```

### Test Private Keys
**WARNING**: Never use in production!
```
5KYZdUEo39z3FPrtuX2QbbwGnNP5zTd7yyr2SC1j299sBCnWjss
```

---

## Useful Aliases

Add to `~/.bashrc` or `~/.zshrc`:

```bash
alias pt='pytest'
alias ptv='pytest -v'
alias ptc='pytest --cov=src --cov-report=html'
alias ptu='pytest -m unit'
alias pti='pytest -m integration'
alias pts='pytest -m security'
alias ptf='pytest --lf'  # Re-run failed
```

---

## Quick Reference Card

```
Test Everything:        pytest
Unit Tests:             pytest -m unit
Coverage:               pytest --cov=src
Specific File:          pytest path/to/test_file.py
Pattern Match:          pytest -k "pattern"
Stop on Fail:           pytest -x
Verbose:                pytest -v
Last Failed:            pytest --lf
Full CI:                make ci
Quick Check:            make quick
```

---

*Last Updated: January 2025 | XAI Version: 0.2.0*
