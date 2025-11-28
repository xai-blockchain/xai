# Test Suite Quick Action Guide
## Immediate Actions for Test Improvement

---

## QUICK START: Fix Failing Tests Today

### Step 1: Run Tests Locally (5 minutes)
```bash
cd C:\Users\decri\GitClones\Crypto

# Run only failing tests
pytest tests/ -k "test_reject_zero_amount or test_reject_dust_transaction or test_bridge_queues_proposal" -v

# Or run with coverage for specific module
pytest tests/xai_tests/test_transaction_validator.py --cov=src/xai/core/transaction_validator --cov-report=term -v
```

### Step 2: Fix Quick Wins (< 2 hours total)

#### Fix #1: Security Validation (15 min)
**File**: `C:\Users\decri\GitClones\Crypto\tests\xai_tests\security\test_input_validation.py`
**Test**: `test_reject_zero_amount`
**Location**: Line ~50-60

**Likely Issue**: Amount validation logic
**Quick Fix**:
1. Check transaction validator accepts zero amounts when it shouldn't
2. Add/fix validation: `if amount <= 0: raise ValueError`
3. Run test: `pytest tests/xai_tests/security/test_input_validation.py::TestAmountValidation::test_reject_zero_amount -v`

#### Fix #2: Dust Protection (15 min)
**File**: `C:\Users\decri\GitClones\Crypto\tests\xai_tests\unit\test_security.py`
**Test**: `test_reject_dust_transaction`

**Likely Issue**: Dust threshold not enforced
**Quick Fix**:
1. Check `blockchain.py` or `transaction_validator.py` for dust limits
2. Ensure transactions below threshold are rejected
3. Run test: `pytest tests/xai_tests/unit/test_security.py::TestDustProtection::test_reject_dust_transaction -v`

#### Fix #3: AI Bridge (20 min)
**File**: `C:\Users\decri\GitClones\Crypto\tests\xai_tests\test_ai_bridge.py`
**Test**: `test_bridge_queues_proposal_and_records_metrics`

**Likely Issue**: Metrics recording or queue management
**Quick Fix**:
1. Review AI bridge implementation
2. Ensure metrics are properly recorded
3. Run test: `pytest tests/xai_tests/test_ai_bridge.py::test_bridge_queues_proposal_and_records_metrics -v`

---

## CRITICAL FIXES: Transaction Validation (2-3 hours)

### Location: `tests\xai_tests\test_transaction_validator.py`

All 5 transaction validator tests are failing. Common root cause likely.

### Debug Strategy:
```bash
# Run all transaction validator tests with verbose output
pytest tests/xai_tests/test_transaction_validator.py -v -s --tb=long

# This will show exact assertion failures
```

### Common Issues:
1. **Transaction type checking**: Update for new transaction types (TIME_CAPSULE, GOVERNANCE_VOTE)
2. **Balance validation**: UTXO tracking might have changed
3. **Coinbase validation**: Special handling for mining rewards

### Fix Checklist:
- [ ] Update transaction type enum/validation
- [ ] Fix balance checking logic
- [ ] Add coinbase transaction exemption from balance check
- [ ] Handle time-locked transactions
- [ ] Handle governance vote transactions

---

## TOKEN/SUPPLY FIXES: XAI Token (1.5 hours)

### Location: `tests\xai_tests\test_xai_token.py`

Three tests failing related to minting and vesting.

### Tests:
1. `test_mint_tokens_exceed_cap` - Supply cap enforcement
2. `test_mint_tokens_zero_or_negative_amount` - Input validation
3. `test_create_vesting_schedule_insufficient_balance` - Balance checking

### Quick Debug:
```bash
pytest tests/xai_tests/test_xai_token.py::TestXAIToken -v --tb=short
```

### Likely Fixes:
```python
# In src/xai/core/xai_token.py

# Fix 1: Enforce supply cap
def mint_tokens(self, amount):
    if self.total_supply + amount > self.max_supply:
        raise ValueError("Would exceed maximum supply")
    # ... rest of logic

# Fix 2: Validate amount
def mint_tokens(self, amount):
    if amount <= 0:
        raise ValueError("Amount must be positive")
    # ... rest of logic

# Fix 3: Check balance for vesting
def create_vesting_schedule(self, amount):
    if self.get_balance(self.address) < amount:
        raise ValueError("Insufficient balance for vesting")
    # ... rest of logic
```

---

## NETWORK CONSENSUS FIXES: Deeper Investigation (4-6 hours)

### These require more investigation:

#### Test 1: `test_reject_invalid_chain`
**File**: `tests\xai_tests\integration\test_network.py`
**Line**: ~130-150
**Issue**: Chain validation not rejecting invalid chains
**Debug**:
```bash
pytest tests/xai_tests/integration/test_network.py::TestChainConsensus::test_reject_invalid_chain -v -s
```

#### Test 2: `test_transaction_broadcast`
**Issue**: P2P message propagation
**Debug**:
```bash
pytest tests/xai_tests/integration/test_network.py::TestTransactionPropagation::test_transaction_broadcast -v -s
```

#### Test 3: `test_block_validation_prevents_corruption`
**Issue**: Block validation or corruption detection

#### Test 4: `test_transaction_announcement`
**Issue**: Network messaging

### Investigation Steps:
1. Run each test individually with full output
2. Check network/P2P module changes
3. Review blockchain validation logic
4. Check for recent refactoring that broke integration

---

## COVERAGE IMPROVEMENT: Daily Goals

### Week 1: Core Modules
**Goal**: Increase coverage from 17% to 35%

#### Monday: blockchain.py (78% → 90%)
```bash
# Check current coverage
pytest tests/ --cov=src/xai/core/blockchain --cov-report=html --cov-report=term-missing

# Review missing lines in htmlcov/blockchain_py.html
# Write ~40 new tests for uncovered code
```

**Focus Areas**:
- Edge cases in block validation
- Error handling paths
- Complex chain reorganization scenarios

#### Tuesday: wallet.py (87% → 95%)
```bash
pytest tests/ --cov=src/xai/core/wallet --cov-report=term-missing
```

**Focus Areas**:
- Key generation edge cases
- Transaction signing variations
- Balance calculation edge cases

#### Wednesday: transaction_validator.py (77% → 95%)
**Focus Areas**:
- All transaction types
- Validation error paths
- Edge cases (max values, special addresses)

#### Thursday: node_api.py (21% → 60%)
**Focus Areas**:
- All API endpoints
- Error responses
- Input validation

#### Friday: node.py (26% → 60%)
**Focus Areas**:
- Node lifecycle
- P2P communication
- State management

---

## TESTING BEST PRACTICES

### Writing New Tests

#### Template for Unit Tests:
```python
import pytest
from src.xai.core.module import ClassToTest

class TestClassName:
    @pytest.fixture
    def instance(self):
        """Create test instance"""
        return ClassToTest()

    def test_normal_operation(self, instance):
        """Test happy path"""
        result = instance.method(valid_input)
        assert result == expected_output

    def test_edge_case(self, instance):
        """Test edge cases"""
        result = instance.method(edge_case_input)
        assert result == edge_case_output

    def test_error_handling(self, instance):
        """Test error cases"""
        with pytest.raises(ValueError):
            instance.method(invalid_input)
```

#### Template for Integration Tests:
```python
import pytest
from src.xai.core.blockchain import Blockchain
from src.xai.core.wallet import Wallet

class TestFeatureIntegration:
    @pytest.fixture
    def setup(self):
        """Setup test environment"""
        blockchain = Blockchain()
        wallet = Wallet()
        return blockchain, wallet

    def test_end_to_end_scenario(self, setup):
        """Test complete workflow"""
        blockchain, wallet = setup
        # Create transaction
        # Mine block
        # Verify state
        assert blockchain.get_balance(wallet.address) == expected_balance
```

### Running Tests Efficiently

```bash
# Run only fast tests (< 1 second each)
pytest tests/ -m "not slow" -v

# Run with parallel execution (requires pytest-xdist)
pytest tests/ -n auto

# Run with coverage and fail if below threshold
pytest tests/ --cov=src/xai --cov-fail-under=80

# Run specific test file
pytest tests/xai_tests/test_blockchain.py -v

# Run tests matching pattern
pytest tests/ -k "transaction" -v

# Stop on first failure (useful for debugging)
pytest tests/ -x

# Run last failed tests only
pytest tests/ --lf

# Run with detailed output for debugging
pytest tests/ -vv -s --tb=long
```

---

## PRIORITY MATRIX

### This Week (5-10 hours)
- [ ] Fix 9 quick-win tests (6 hours)
- [ ] Fix transaction validation tests (3 hours)
- [ ] Increase blockchain.py coverage to 85% (2 hours)

### Next Week (20-30 hours)
- [ ] Fix network consensus tests (6 hours)
- [ ] Increase core module coverage to 90% (15 hours)
- [ ] Start security module tests (10 hours)

### This Month (80-100 hours)
- [ ] Achieve 50% overall coverage
- [ ] Complete security module coverage
- [ ] Fix all integration test failures

---

## AUTOMATION SETUP

### Pre-commit Hook for Tests
```bash
#!/bin/bash
# Run fast tests before commit
pytest tests/ -m "not slow" --tb=short -q
if [ $? -ne 0 ]; then
    echo "Tests failed. Commit aborted."
    exit 1
fi
```

### CI/CD Integration
```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.13'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      - name: Run tests with coverage
        run: |
          pytest tests/ --cov=src/xai --cov-report=xml --cov-report=term
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

---

## USEFUL COMMANDS CHEAT SHEET

```bash
# Coverage commands
pytest --cov=src/xai --cov-report=html  # Generate HTML report
pytest --cov=src/xai --cov-report=term-missing  # Show missing lines
pytest --cov=src/xai --cov-report=json  # Generate JSON report

# Test selection
pytest -k "network"  # Run tests matching "network"
pytest tests/unit/  # Run only unit tests
pytest -m slow  # Run tests marked as slow
pytest --collect-only  # List all tests without running

# Output control
pytest -v  # Verbose output
pytest -q  # Quiet output
pytest -s  # Show print statements
pytest --tb=short  # Short traceback
pytest --tb=long  # Long traceback

# Performance
pytest -n 4  # Run with 4 parallel workers
pytest --durations=10  # Show 10 slowest tests
pytest --timeout=30  # Set 30 second timeout per test

# Debugging
pytest --pdb  # Drop into debugger on failure
pytest --trace  # Drop into debugger at start
pytest -x  # Stop on first failure
pytest --lf  # Run last failed
pytest --ff  # Run failed first, then others

# Coverage thresholds
pytest --cov=src/xai --cov-fail-under=80  # Fail if coverage < 80%
```

---

## TROUBLESHOOTING

### Issue: Tests timing out
**Solution**: Add timeout decorator
```python
import pytest

@pytest.mark.timeout(30)  # 30 second timeout
def test_long_running():
    # ... test code
```

### Issue: Tests are flaky
**Solution**: Add retries
```python
@pytest.mark.flaky(reruns=3)  # Retry up to 3 times
def test_network_operation():
    # ... test code
```

### Issue: Fixtures too slow
**Solution**: Use session or module scope
```python
@pytest.fixture(scope="session")  # Created once per test session
def expensive_fixture():
    # ... setup code
    yield resource
    # ... teardown code
```

### Issue: Import errors
**Solution**: Check PYTHONPATH
```bash
export PYTHONPATH="${PYTHONPATH}:${PWD}/src"
```

---

## GETTING HELP

### Documentation
- pytest docs: https://docs.pytest.org/
- coverage.py docs: https://coverage.readthedocs.io/
- Test patterns: https://docs.python-guide.org/writing/tests/

### Project Resources
- Test suite report: `TEST_SUITE_COMPREHENSIVE_REPORT.md`
- Coverage HTML: `htmlcov/index.html`
- Coverage JSON: `coverage.json`

---

**Last Updated**: November 19, 2025
**Next Update**: After fixing quick-win tests
