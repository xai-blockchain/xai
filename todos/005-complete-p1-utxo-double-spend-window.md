# UTXO Double-Spend Window in Mempool Validation

---
status: pending
priority: p1
issue_id: 005
tags: [data-integrity, security, mempool, code-review]
dependencies: []
---

## Problem Statement

Double-spend detection in `add_transaction()` only checks against pending transactions, not against UTXOs already spent in confirmed blocks. There's a TOCTOU (Time-of-Check-Time-of-Use) race between validation and mempool insertion.

## Findings

### Location
**File:** `src/xai/core/blockchain.py` (Lines 2135-2186)

### Evidence

```python
# Line 2135: Validation checks UTXO availability
is_valid = self.transaction_validator.validate_transaction(transaction)

# Gap here - no lock held across validation and insertion

# Line 2170-2186: Double-spend check ONLY against mempool
for pending_tx in self.pending_transactions:
    if pending_tx.tx_type != "coinbase" and pending_tx.inputs:
        for pending_input in pending_tx.inputs:
            # Only checks mempool, not confirmed blocks
```

The UTXO manager uses RLock (thread-safe), but blockchain doesn't hold the lock across the validation->insertion sequence.

### Attack Scenario

1. Thread A: Validates TX1 spending UTXO_X (passes - UTXO exists)
2. Thread B: TX2 also spending UTXO_X gets validated (passes)
3. Thread A: Adds TX1 to mempool
4. Thread B: Adds TX2 to mempool (double-spend not detected)
5. Both transactions get into the same block or consecutive blocks
6. Second transaction fails validation during block mining but may cause state inconsistency

### Impact

- Mempool pollution with invalid transactions
- Potential double-spend if race is exploited
- Block mining failures
- Network consensus issues

## Proposed Solutions

### Option A: Atomic Validation-Insertion Lock (Recommended)
**Effort:** Small | **Risk:** Low

```python
def add_transaction(self, transaction: Transaction) -> bool:
    with self._mempool_lock:  # Hold lock across entire operation
        # Validate UTXO availability
        is_valid = self.transaction_validator.validate_transaction(transaction)
        if not is_valid:
            return False

        # Check mempool double-spends
        if self._check_mempool_double_spend(transaction):
            return False

        # Add to mempool (still under lock)
        self.pending_transactions.append(transaction)
        return True
```

### Option B: Optimistic Concurrency with Retry
**Effort:** Medium | **Risk:** Medium

```python
def add_transaction(self, transaction: Transaction, max_retries=3) -> bool:
    for attempt in range(max_retries):
        # Get UTXO version
        utxo_version = self.utxo_manager.get_version()

        # Validate
        if not self.transaction_validator.validate_transaction(transaction):
            return False

        with self._mempool_lock:
            # Check version hasn't changed
            if self.utxo_manager.get_version() != utxo_version:
                continue  # Retry

            # Safe to add
            self.pending_transactions.append(transaction)
            return True

    return False  # Max retries exceeded
```

## Recommended Action

Implement Option A immediately. This is a **security-critical bug**.

## Technical Details

**Affected Components:**
- Blockchain core (`blockchain.py`)
- Transaction validator
- Mempool management
- UTXO manager

**Database Changes:** None

## Acceptance Criteria

- [ ] Atomic lock covers validation through insertion
- [ ] No double-spend possible via race condition
- [ ] Unit test: concurrent transaction submission
- [ ] Stress test: high-volume parallel submissions
- [ ] Security audit confirms no TOCTOU vulnerabilities

## Work Log

| Date | Action | Result |
|------|--------|--------|
| 2025-12-05 | Issue identified by data-integrity-guardian agent | Critical vulnerability |

## Resources

- [CWE-367: TOCTOU Race Condition](https://cwe.mitre.org/data/definitions/367.html)
- [Double-Spend Attack](https://en.bitcoin.it/wiki/Double-spending)
