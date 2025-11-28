# Error Handling Tests - Quick Reference Guide

## Overview

Three comprehensive test files created to boost coverage from 14-22% to 70%+ for all error handling modules.

---

## Test Files Summary

### 1. test_error_handlers_comprehensive.py (897 lines, 89 tests)

**Target Module:** `src/xai/core/error_handlers.py`

**Test Classes:**
- `TestCircuitState` - 3 tests
- `TestCircuitBreaker` - 21 tests
- `TestRetryStrategy` - 13 tests
- `TestErrorHandler` - 3 tests
- `TestNetworkErrorHandler` - 8 tests
- `TestValidationErrorHandler` - 7 tests
- `TestStorageErrorHandler` - 6 tests
- `TestErrorHandlerRegistry` - 14 tests
- `TestErrorLogger` - 18 tests
- `TestIntegration` - 3 tests

**Key Coverage:**
- Circuit breaker states and transitions
- Exponential backoff retry logic
- Error classification and routing
- Error logging and statistics
- Handler registration and dispatch

**Expected Coverage:** 85%+

---

### 2. test_error_recovery_comprehensive.py (801 lines, 60 tests)

**Target Module:** `src/xai/core/error_recovery.py`

**Test Classes:**
- `TestErrorRecoveryManager` - 45 tests
- `TestCreateRecoveryManager` - 3 tests
- `TestErrorRecoveryIntegration` - 12 tests

**Key Coverage:**
- Recovery manager initialization
- Operation wrapping with circuit breakers
- Corruption detection and recovery
- Network partition handling
- Graceful shutdown procedures
- Checkpoint creation
- Health monitoring
- State transitions

**Expected Coverage:** 82%+

---

### 3. test_error_detection_comprehensive.py (1048 lines, 82 tests)

**Target Module:** `src/xai/core/error_detection.py`

**Test Classes:**
- `TestErrorSeverity` - 2 tests
- `TestRecoveryState` - 2 tests
- `TestErrorDetector` - 28 tests
- `TestCorruptionDetector` - 20 tests
- `TestHealthMonitor` - 30 tests
- `TestIntegration` - 5 tests

**Key Coverage:**
- Error severity classification
- Error pattern detection
- Corruption detection (hash, chain, UTXO, supply, transactions)
- Health scoring and trending
- Metric tracking

**Expected Coverage:** 90%+

---

## Quick Test Execution

### Run Individual Test Files

```bash
# Test error handlers
pytest tests/xai_tests/unit/test_error_handlers_comprehensive.py -v

# Test error recovery
pytest tests/xai_tests/unit/test_error_recovery_comprehensive.py -v

# Test error detection
pytest tests/xai_tests/unit/test_error_detection_comprehensive.py -v
```

### Run All Error Handling Tests

```bash
pytest tests/xai_tests/unit/test_error_*_comprehensive.py -v
```

### Run with Coverage Reports

```bash
# Individual module coverage
pytest tests/xai_tests/unit/test_error_handlers_comprehensive.py \
  --cov=src/xai/core/error_handlers \
  --cov-report=term-missing \
  --cov-report=html:coverage_html/error_handlers

pytest tests/xai_tests/unit/test_error_recovery_comprehensive.py \
  --cov=src/xai/core/error_recovery \
  --cov-report=term-missing \
  --cov-report=html:coverage_html/error_recovery

pytest tests/xai_tests/unit/test_error_detection_comprehensive.py \
  --cov=src/xai/core/error_detection \
  --cov-report=term-missing \
  --cov-report=html:coverage_html/error_detection

# Combined coverage report
pytest tests/xai_tests/unit/test_error_*_comprehensive.py \
  --cov=src/xai/core/error_handlers \
  --cov=src/xai/core/error_recovery \
  --cov=src/xai/core/error_detection \
  --cov-report=term-missing \
  --cov-report=html:coverage_html/error_handling
```

### Run Specific Test Classes

```bash
# Circuit breaker tests only
pytest tests/xai_tests/unit/test_error_handlers_comprehensive.py::TestCircuitBreaker -v

# Corruption detector tests only
pytest tests/xai_tests/unit/test_error_detection_comprehensive.py::TestCorruptionDetector -v

# Recovery manager tests only
pytest tests/xai_tests/unit/test_error_recovery_comprehensive.py::TestErrorRecoveryManager -v
```

### Run Specific Tests

```bash
# Test circuit breaker state transitions
pytest tests/xai_tests/unit/test_error_handlers_comprehensive.py::TestCircuitBreaker::test_half_open_state_transition -v

# Test corruption detection
pytest tests/xai_tests/unit/test_error_detection_comprehensive.py::TestCorruptionDetector::test_detect_corruption_broken_chain -v

# Test graceful shutdown
pytest tests/xai_tests/unit/test_error_recovery_comprehensive.py::TestErrorRecoveryManager::test_graceful_shutdown -v
```

---

## Test Structure

### Common Test Pattern

```python
class TestClassName:
    """Test class for ClassName functionality"""

    @pytest.fixture
    def instance(self):
        """Create instance for testing"""
        return ClassName()

    def test_method_name_scenario(self, instance):
        """Test specific scenario for method"""
        # Arrange
        setup_data = ...

        # Act
        result = instance.method(setup_data)

        # Assert
        assert result == expected_value
```

### Mock Objects Used

```python
# Blockchain mock
class MockBlockchain:
    def __init__(self):
        self.chain = []
        self.pending_transactions = []
        self.utxo_set = {}

# Block mock
class MockBlock:
    def __init__(self, index, previous_hash):
        self.index = index
        self.previous_hash = previous_hash
        self.hash = f"block_{index}_hash"

# Transaction mock
class MockTransaction:
    def __init__(self, sender, recipient, amount, fee):
        self.sender = sender
        self.recipient = recipient
        self.amount = amount
        self.fee = fee
```

---

## Key Test Scenarios

### Circuit Breaker Tests

1. **State Transitions**
   - CLOSED → OPEN (after threshold failures)
   - OPEN → HALF_OPEN (after timeout)
   - HALF_OPEN → CLOSED (after success threshold)
   - HALF_OPEN → OPEN (on failure)

2. **Edge Cases**
   - Calls rejected when OPEN
   - Timeout calculation
   - Success/failure counting

### Retry Strategy Tests

1. **Retry Logic**
   - Success on first try
   - Success after retries
   - All retries exhausted

2. **Backoff Behavior**
   - Exponential delay calculation
   - Max delay capping
   - Retry count verification

### Error Detection Tests

1. **Severity Classification**
   - CRITICAL: MemoryError, SystemExit, IOError
   - HIGH: Blockchain/transaction errors
   - MEDIUM: Network errors, general errors

2. **Pattern Detection**
   - Threshold-based pattern identification
   - Suggestion generation
   - Statistics aggregation

### Corruption Detection Tests

1. **Integrity Checks**
   - Hash integrity
   - Chain continuity
   - UTXO consistency
   - Supply validation
   - Transaction validity

2. **Error Detection**
   - Hash mismatches
   - Broken chain links
   - Negative amounts
   - Invalid signatures

### Health Monitoring Tests

1. **Metric Tracking**
   - Block time
   - Mempool size
   - Peer count
   - Error count

2. **Score Calculation**
   - Perfect health (100)
   - Penalties (old blocks, full mempool, no peers, errors)
   - Minimum floor (0)

3. **Trend Analysis**
   - Improving
   - Declining
   - Stable

---

## Coverage Goals by Module

| Module | Current | Target | New Tests | Expected |
|--------|---------|--------|-----------|----------|
| error_handlers.py | 22% | 70%+ | 89 | 85%+ |
| error_recovery.py | 18% | 70%+ | 60 | 82%+ |
| error_detection.py | 14% | 70%+ | 82 | 90%+ |
| **Average** | **18%** | **70%+** | **231** | **86%+** |

---

## Test Maintenance

### Adding New Tests

1. Identify untested code from coverage report
2. Create test method with descriptive name
3. Use appropriate fixtures
4. Mock external dependencies
5. Test both success and failure paths
6. Add edge case tests

### Updating Tests

When error handling modules change:

1. Review modified code
2. Update affected test cases
3. Add tests for new functionality
4. Update mock objects if needed
5. Run full test suite
6. Verify coverage maintained

### Debugging Failed Tests

```bash
# Run with verbose output
pytest tests/xai_tests/unit/test_error_handlers_comprehensive.py -vv

# Run with debugging
pytest tests/xai_tests/unit/test_error_handlers_comprehensive.py --pdb

# Run with print statements visible
pytest tests/xai_tests/unit/test_error_handlers_comprehensive.py -s

# Show local variables on failure
pytest tests/xai_tests/unit/test_error_handlers_comprehensive.py -l
```

---

## Common Issues and Solutions

### Issue: Import Errors

**Problem:** `ModuleNotFoundError: No module named 'xai'`

**Solution:**
```bash
# Ensure PYTHONPATH is set
export PYTHONPATH=$PYTHONPATH:$(pwd)/src

# Or install in editable mode
pip install -e .
```

### Issue: Mock Object Attribute Errors

**Problem:** `AttributeError: Mock object has no attribute 'method'`

**Solution:**
```python
# Configure mock with expected attributes
mock_obj = Mock()
mock_obj.method = Mock(return_value=expected_value)

# Or use spec
mock_obj = Mock(spec=RealClass)
```

### Issue: Time-Dependent Test Failures

**Problem:** Tests fail intermittently due to timing

**Solution:**
```python
# Use shorter timeouts in tests
circuit_breaker = CircuitBreaker(timeout=0.1)

# Use time.sleep() carefully
time.sleep(0.11)  # Slightly longer than timeout

# Or use freezegun for time control
from freezegun import freeze_time
```

---

## File Locations

- **Test Files:** `C:\Users\decri\GitClones\Crypto\tests\xai_tests\unit\`
  - test_error_handlers_comprehensive.py
  - test_error_recovery_comprehensive.py
  - test_error_detection_comprehensive.py

- **Source Files:** `C:\Users\decri\GitClones\Crypto\src\xai\core\`
  - error_handlers.py
  - error_recovery.py
  - error_detection.py
  - recovery_strategies.py (dependency)

---

## Next Steps

1. **Run Tests:**
   ```bash
   pytest tests/xai_tests/unit/test_error_*_comprehensive.py -v
   ```

2. **Generate Coverage Report:**
   ```bash
   pytest tests/xai_tests/unit/test_error_*_comprehensive.py \
     --cov=src/xai/core/error_handlers \
     --cov=src/xai/core/error_recovery \
     --cov=src/xai/core/error_detection \
     --cov-report=html
   ```

3. **View Coverage:**
   ```bash
   open coverage_html/index.html  # or open in browser
   ```

4. **Identify Remaining Gaps:**
   - Review coverage report
   - Add tests for uncovered lines
   - Target 70%+ coverage

5. **Integrate into CI/CD:**
   - Add to GitHub Actions workflow
   - Set minimum coverage threshold
   - Generate coverage badges

---

## Additional Resources

- **Coverage Report:** `ERROR_HANDLING_TEST_COVERAGE_REPORT.md`
- **pytest Documentation:** https://docs.pytest.org/
- **Mock Documentation:** https://docs.python.org/3/library/unittest.mock.html
- **Coverage.py Documentation:** https://coverage.readthedocs.io/
