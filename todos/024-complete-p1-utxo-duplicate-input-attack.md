# UTXO Duplicate Input Attack - Inflation Vulnerability

---
status: complete
priority: p1
issue_id: 024
tags: [security, consensus, utxo, inflation, code-review]
dependencies: []
completed_date: 2025-12-07
---

## Problem Statement

The `process_transaction_inputs()` method in UTXO manager marks UTXOs as spent but does not check if they're already marked spent in the SAME transaction (duplicate inputs). An attacker can reference the same UTXO multiple times in inputs array to inflate transaction value.

## Findings

### Location
**File:** `src/xai/core/utxo_manager.py` (Lines 225-254)

### Evidence

```python
# Lines 239-250
for input_utxo_ref in transaction.inputs:
    txid = input_utxo_ref["txid"]
    vout = input_utxo_ref["vout"]
    # No check for duplicate (txid, vout) in this transaction's inputs!
    if not self.mark_utxo_spent(transaction.sender, txid, vout):
        return False  # Only fails if UTXO doesn't exist, not if duplicate
```

### Attack Example

```python
tx = Transaction(
    sender="attacker",
    inputs=[
        {"txid": "abc123", "vout": 0},  # Valid UTXO worth 100 XAI
        {"txid": "abc123", "vout": 0},  # DUPLICATE - should be rejected
        {"txid": "abc123", "vout": 0},  # DUPLICATE - should be rejected
    ],
    outputs=[{"address": "attacker", "amount": 300}]  # Spent 100, got 300
)
```

### Impact

- **Inflation Attack**: Create coins out of thin air
- **Supply Violation**: Exceed max supply of 121M XAI
- **Economic Collapse**: Unlimited money printing capability
- **Consensus Failure**: Nodes disagree on valid state

## Proposed Solutions

### Option A: Set-Based Duplicate Detection (Recommended)
**Effort:** Small | **Risk:** Low

```python
def process_transaction_inputs(self, transaction: Transaction) -> bool:
    """Process transaction inputs with duplicate detection."""

    # FIRST: Check for duplicate inputs within this transaction
    seen_inputs: Set[Tuple[str, int]] = set()
    for input_ref in transaction.inputs:
        utxo_key = (input_ref["txid"], input_ref["vout"])
        if utxo_key in seen_inputs:
            logger.security(
                "Duplicate UTXO input detected",
                extra={
                    "event": "utxo.duplicate_input_attack",
                    "txid": transaction.txid,
                    "duplicate_utxo": utxo_key,
                    "sender": transaction.sender
                }
            )
            raise UTXOValidationError(f"Duplicate input detected: {utxo_key}")
        seen_inputs.add(utxo_key)

    # THEN: Process each unique input
    for input_ref in transaction.inputs:
        if not self.mark_utxo_spent(transaction.sender, input_ref["txid"], input_ref["vout"]):
            return False

    return True
```

### Option B: Transaction Validation Layer
**Effort:** Medium | **Risk:** Low

Add validation at transaction creation time:

```python
class Transaction:
    def __init__(self, ..., inputs: List[Dict], ...):
        # Validate unique inputs
        input_keys = [(i["txid"], i["vout"]) for i in inputs]
        if len(input_keys) != len(set(input_keys)):
            raise TransactionValidationError("Duplicate inputs not allowed")

        self.inputs = inputs
```

## Recommended Action

Implement Option A immediately - this is a **CRITICAL** inflation vulnerability.

## Technical Details

**Affected Components:**
- UTXO manager
- Transaction validation
- Block validation
- Mempool validation

**Database Changes:** None

## Acceptance Criteria

- [x] Duplicate inputs detected and rejected
- [x] Security logging for attack attempts
- [x] Unit test with duplicate inputs (must fail)
- [ ] Fuzz test with random input combinations (future enhancement)
- [ ] Integration test verifying supply conservation (future enhancement)

## Work Log

| Date | Action | Result |
|------|--------|--------|
| 2025-12-07 | Issue identified by data-integrity-guardian agent | Critical inflation vulnerability |
| 2025-12-07 | Implemented duplicate input detection in process_transaction_inputs() | Fixed vulnerability using set-based detection |
| 2025-12-07 | Added security logging for attack attempts | Security events logged with CRITICAL severity |
| 2025-12-07 | Updated test to verify rejection of duplicate inputs | Test passes - duplicates properly rejected |
| 2025-12-07 | Verified all UTXO manager tests still pass | 53 tests pass, no regressions |

## Resources

- [Bitcoin CVE-2018-17144](https://bitcoincore.org/en/2018/09/20/notice/) - Similar inflation bug in Bitcoin
- [UTXO Model Security](https://en.bitcoin.it/wiki/Transaction)
