# Fuzzing and Property-Based Testing

This directory contains fuzzing and property-based tests for the XAI Blockchain project.

## Overview

Fuzzing and property-based testing complement traditional example-based testing by:

1. **Discovering Edge Cases**: Automatically finding inputs that cause failures
2. **Testing Properties**: Verifying invariants that should always hold
3. **Improving Coverage**: Reaching code paths that might be missed
4. **Security Testing**: Finding vulnerabilities through randomized inputs

## Test Files

### example_fuzz_test.py

Demonstrates fuzzing techniques for:
- API endpoint fuzzing
- Transaction fuzzing
- Input validation fuzzing
- Network protocol fuzzing

**Run with:**
```bash
pytest tests/fuzzing/example_fuzz_test.py -v
```

### example_property_test.py

Demonstrates property-based testing for:
- Cryptographic properties (determinism, collision resistance)
- Transaction properties (balance conservation, validation)
- Blockchain properties (consensus, immutability)
- Arithmetic properties (overflow protection)
- Stateful testing (wallet state machine)

**Run with:**
```bash
pytest tests/fuzzing/example_property_test.py -v
```

## Property-Based Testing Concepts

### Properties vs Examples

**Example-Based Test:**
```python
def test_transfer():
    wallet = Wallet(balance=100)
    wallet.transfer(30)
    assert wallet.balance == 70
```

**Property-Based Test:**
```python
@given(st.integers(min_value=0), st.integers(min_value=0))
def test_transfer_never_negative(initial_balance, amount):
    wallet = Wallet(balance=initial_balance)
    if amount > initial_balance:
        with pytest.raises(InsufficientBalance):
            wallet.transfer(amount)
    else:
        wallet.transfer(amount)
        assert wallet.balance >= 0  # Property: never negative
```

### Key Properties to Test

**Cryptographic**:
- Determinism: Same input → Same output
- Reversibility: Encrypt → Decrypt = Original
- Collision Resistance: Different inputs → Different hashes

**Transactions**:
- Balance Conservation: Total before = Total after
- Non-negative: Balances never go negative
- Validation: Invalid transactions rejected

**Blockchain**:
- Chain Integrity: Valid chain stays valid
- Consensus: All honest nodes agree
- Immutability: Past blocks don't change

**Arithmetic**:
- No Overflow: Operations don't overflow
- Precision: Decimal precision maintained
- Commutative: a + b = b + a

## Hypothesis Strategies

Hypothesis provides strategies for generating test data:

```python
from hypothesis import strategies as st

# Basic types
st.integers(min_value=0, max_value=100)
st.text(min_size=1, max_size=100)
st.binary(min_size=1, max_size=1000)
st.booleans()

# Collections
st.lists(st.integers(), min_size=1, max_size=10)
st.dictionaries(keys=st.text(), values=st.integers())

# Custom strategies
@st.composite
def blockchain_address(draw):
    return '0x' + ''.join(draw(st.lists(
        st.sampled_from('0123456789abcdef'),
        min_size=40,
        max_size=40
    )))
```

## Stateful Testing

For testing sequences of operations:

```python
from hypothesis.stateful import RuleBasedStateMachine, rule, invariant

class WalletStateMachine(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()
        self.balance = 0

    @rule(amount=st.integers(min_value=1, max_value=1000))
    def deposit(self, amount):
        self.balance += amount

    @invariant()
    def balance_non_negative(self):
        assert self.balance >= 0
```

## Best Practices

### 1. Use Meaningful Properties

**Good:**
```python
@given(st.lists(st.integers(min_value=0)))
def test_sum_never_negative(numbers):
    assert sum(numbers) >= 0
```

**Bad:**
```python
@given(st.integers())
def test_something(x):
    assert True  # Not testing anything meaningful
```

### 2. Use assume() for Constraints

```python
@given(st.integers(), st.integers())
def test_division(a, b):
    assume(b != 0)  # Skip test if b is 0
    result = a / b
    assert result * b == a
```

### 3. Add Examples for Edge Cases

```python
@given(st.integers())
@example(0)  # Test specific edge case
@example(-1)
@example(2**31 - 1)
def test_function(value):
    # Test implementation
    pass
```

### 4. Configure Settings

```python
from hypothesis import settings

@given(st.integers())
@settings(max_examples=1000, deadline=None)
def test_expensive_operation(value):
    # More examples, no deadline
    pass
```

## Running Fuzzing Tests

### Run All Fuzzing Tests
```bash
pytest tests/fuzzing/ -v
```

### Run with Coverage
```bash
pytest tests/fuzzing/ --cov=src/xai --cov-report=html
```

### Run Specific Test Class
```bash
pytest tests/fuzzing/example_fuzz_test.py::TestAPIFuzzing -v
```

### Run with More Examples
```bash
pytest tests/fuzzing/ -v --hypothesis-show-statistics
```

### Run with Hypothesis Profile
```bash
# In pytest.ini or conftest.py
from hypothesis import settings
settings.register_profile("ci", max_examples=1000)
settings.register_profile("dev", max_examples=100)

# Run with profile
pytest tests/fuzzing/ --hypothesis-profile=ci
```

## Debugging Failing Tests

### 1. Reproduce Failures

Hypothesis automatically finds minimal failing examples:

```
Falsifying example: test_transaction_validation(
    sender='0x00',
    receiver='0x00',
    amount=-1
)
```

### 2. Use Print Debugging

```python
@given(st.integers())
def test_something(value):
    print(f"Testing with value: {value}")  # Will show for failures
    assert value >= 0
```

### 3. Use Hypothesis Database

Hypothesis stores failing examples in `.hypothesis/` directory.
To clear and start fresh:

```bash
rm -rf .hypothesis/
```

## Integration with CI/CD

### GitHub Actions Example

```yaml
- name: Run Fuzzing Tests
  run: |
    pytest tests/fuzzing/ -v --hypothesis-profile=ci
```

### Continuous Fuzzing

For long-running fuzzing:

```bash
# Run fuzzing overnight
pytest tests/fuzzing/ --hypothesis-profile=thorough --maxfail=1
```

## Further Reading

- [Hypothesis Documentation](https://hypothesis.readthedocs.io/)
- [Property-Based Testing Guide](https://hypothesis.works/articles/)
- [Fuzzing Best Practices](https://owasp.org/www-community/Fuzzing)

## Contributing

When adding new fuzzing tests:

1. Identify properties to test
2. Create appropriate strategies
3. Add meaningful examples
4. Document the property being tested
5. Configure appropriate settings

## License

Same as XAI Blockchain project.
