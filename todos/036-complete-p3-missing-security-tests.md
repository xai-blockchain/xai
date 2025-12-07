# Missing Security-Specific Test Coverage

---
status: pending
priority: p3
issue_id: 036
tags: [testing, security, coverage, code-review]
dependencies: []
---

## Problem Statement

Security-critical modules lack explicit security tests. While functional tests exist, there are no dedicated tests for attack vectors, edge cases, and security invariants that would be expected in a production blockchain.

## Findings

### Locations
**Files Needing Security Tests:**
- `src/xai/core/wallet.py` - No key derivation tests
- `src/xai/core/defi/flash_loans.py` - No reentrancy tests
- `src/xai/core/defi/oracle.py` - No manipulation tests
- `src/xai/core/utxo_manager.py` - No double-spend tests
- `src/xai/core/transaction.py` - No malleability tests

### Evidence

```python
# Current test coverage focuses on happy path
def test_transfer_success():
    wallet.transfer(recipient, amount)
    assert wallet.balance == expected

# Missing security tests like:
# - test_transfer_prevents_double_spend
# - test_signature_malleability_rejected
# - test_replay_attack_prevented
# - test_overflow_in_amount_rejected
```

### Impact

- **Undetected Vulnerabilities**: Security bugs ship to production
- **Regression Risk**: Fixes may be undone without tests
- **Audit Readiness**: Auditors expect security test suites
- **Confidence**: Can't verify security properties hold

## Proposed Solutions

### Option A: Security Test Suite (Recommended)
**Effort:** Medium | **Risk:** Low

```python
# tests/security/test_double_spend.py
import pytest
from xai.core.blockchain import Blockchain
from xai.core.transaction import Transaction

class TestDoubleSpendPrevention:
    """Test suite for double-spend attack prevention."""

    def test_same_utxo_cannot_be_spent_twice(self, blockchain):
        """Verify UTXO can only be spent once."""
        tx1 = create_transaction(utxo_id="utxo_001", recipient="alice")
        tx2 = create_transaction(utxo_id="utxo_001", recipient="bob")

        assert blockchain.add_transaction(tx1) == True
        assert blockchain.add_transaction(tx2) == False  # Must reject

    def test_double_spend_in_same_block(self, blockchain):
        """Double spend within single block rejected."""
        block = create_block_with_transactions([
            create_transaction(utxo_id="utxo_001", recipient="alice"),
            create_transaction(utxo_id="utxo_001", recipient="bob"),
        ])

        assert blockchain.validate_block(block) == False

    def test_race_condition_double_spend(self, blockchain):
        """Concurrent transactions cannot double spend."""
        import threading

        results = []
        utxo_id = "utxo_race"

        def attempt_spend(recipient):
            tx = create_transaction(utxo_id=utxo_id, recipient=recipient)
            result = blockchain.add_transaction(tx)
            results.append(result)

        threads = [
            threading.Thread(target=attempt_spend, args=(f"recipient_{i}",))
            for i in range(10)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Exactly one should succeed
        assert results.count(True) == 1


# tests/security/test_signature_security.py
class TestSignatureSecurity:
    """Test signature verification security."""

    def test_signature_malleability_rejected(self, wallet):
        """Malleable signatures must be rejected."""
        tx = wallet.create_transaction(recipient="bob", amount=100)
        original_sig = tx.signature

        # Attempt signature malleation
        malleable_sig = mutate_signature(original_sig)
        tx.signature = malleable_sig

        assert wallet.verify_signature(tx) == False

    def test_wrong_private_key_rejected(self, wallet):
        """Transaction signed with wrong key rejected."""
        tx = create_unsigned_transaction(sender=wallet.address)
        wrong_wallet = create_wallet()  # Different keys
        tx.signature = wrong_wallet.sign(tx.hash)

        assert wallet.verify_signature(tx) == False

    def test_empty_signature_rejected(self):
        """Empty signature must be rejected."""
        tx = create_transaction()
        tx.signature = b""

        assert verify_transaction(tx) == False


# tests/security/test_overflow.py
class TestOverflowPrevention:
    """Test integer overflow prevention."""

    def test_amount_overflow_rejected(self):
        """Amount exceeding max rejected."""
        MAX_SUPPLY = 21_000_000 * 10**18

        with pytest.raises(ValueError):
            create_transaction(amount=MAX_SUPPLY + 1)

    def test_balance_overflow_prevented(self, blockchain):
        """Balance calculation cannot overflow."""
        # Give address near-max balance
        address = "overflow_test"
        blockchain.set_balance(address, MAX_INT - 100)

        # Attempt to credit more than fits
        tx = create_credit_transaction(address, amount=200)

        assert blockchain.process_transaction(tx) == False


# tests/security/test_reentrancy.py
class TestReentrancyPrevention:
    """Test reentrancy attack prevention."""

    def test_flash_loan_callback_reentrancy(self, flash_loan_pool):
        """Flash loan callback cannot reenter."""
        class MaliciousCallback:
            def __init__(self, pool):
                self.pool = pool

            def on_flash_loan(self, amount):
                # Attempt reentrancy
                self.pool.flash_loan(amount, self)

        attacker = MaliciousCallback(flash_loan_pool)

        with pytest.raises(ReentrancyError):
            flash_loan_pool.flash_loan(1000, attacker)
```

### Option B: Property-Based Security Testing
**Effort:** Medium | **Risk:** Low

```python
from hypothesis import given, strategies as st

class TestSecurityInvariants:
    """Property-based security testing."""

    @given(st.lists(st.integers(min_value=1, max_value=1000)))
    def test_total_supply_invariant(self, amounts):
        """Total supply never changes from transactions."""
        blockchain = Blockchain()
        initial_supply = blockchain.total_supply()

        for amount in amounts:
            tx = create_random_transfer(amount)
            blockchain.process_transaction(tx)

        assert blockchain.total_supply() == initial_supply

    @given(st.binary(min_size=1, max_size=1000))
    def test_invalid_signatures_rejected(self, random_bytes):
        """Random bytes never validate as signature."""
        tx = create_transaction()
        tx.signature = random_bytes

        assert verify_transaction(tx) == False
```

## Recommended Action

Implement Option A for explicit attack vector tests, add Option B for invariants.

## Technical Details

**Security Test Categories:**
1. **Double Spend** - UTXO reuse, race conditions
2. **Signature** - Malleability, forgery, replay
3. **Overflow** - Integer, balance, supply
4. **Reentrancy** - Callbacks, state modification
5. **Oracle** - Manipulation, staleness
6. **Access Control** - Authorization bypass
7. **DoS** - Resource exhaustion, gas limits

**Test File Structure:**
```
tests/
├── security/
│   ├── test_double_spend.py
│   ├── test_signature_security.py
│   ├── test_overflow.py
│   ├── test_reentrancy.py
│   ├── test_oracle_manipulation.py
│   ├── test_access_control.py
│   └── test_dos_prevention.py
├── invariants/
│   └── test_economic_invariants.py
└── fuzz/
    └── test_fuzz_transactions.py
```

## Acceptance Criteria

- [ ] Double-spend test suite
- [ ] Signature security tests
- [ ] Overflow prevention tests
- [ ] Reentrancy tests for DeFi
- [ ] Oracle manipulation tests
- [ ] Property-based invariant tests
- [ ] Fuzz testing for transaction parsing
- [ ] CI runs security tests on every PR

## Work Log

| Date | Action | Result |
|------|--------|--------|
| 2025-12-07 | Issue identified by python-reviewer agent | Testing gap |

## Resources

- [OWASP Testing Guide](https://owasp.org/www-project-web-security-testing-guide/)
- [Hypothesis Property Testing](https://hypothesis.readthedocs.io/)
- [Trail of Bits Testing](https://github.com/trailofbits/publications)
