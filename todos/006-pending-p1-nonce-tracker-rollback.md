# Nonce Tracker State Inconsistency After Failed Block Addition

---
status: pending
priority: p1
issue_id: 006
tags: [data-integrity, consensus, nonce, code-review]
dependencies: [004]
---

## Problem Statement

In `mine_pending_transactions()`, if block addition fails after nonce increments, nonces are not rolled back. This can cause permanent account lockout where users' transactions are rejected.

## Findings

### Location
**File:** `src/xai/core/blockchain.py` (Lines 2535-2566)

### Evidence

```python
# Line 2535-2540: Nonces are incremented immediately
for tx in new_block.transactions:
    if tx.sender != "COINBASE":
        self.utxo_manager.process_transaction_inputs(tx)
        self.nonce_tracker.increment_nonce(tx.sender, tx.nonce)  # <- Committed
    self.utxo_manager.process_transaction_outputs(tx)

# If later operations fail (e.g., storage.save_state_to_disk at line 2566)
# nonces remain incremented but block isn't added
```

### Attack Scenario

1. Block is mined with transactions from Alice (nonce 5->6)
2. Nonce tracker increments Alice's nonce to 6
3. Disk write fails (line 2566)
4. Block is lost but nonce is at 6
5. Alice's next transaction (nonce 6) is rejected as duplicate
6. Alice must use nonce 7, skipping 6 - causing permanent nonce desync

### Impact

- Account lockout - users cannot submit transactions
- Transactions permanently rejected
- Manual intervention required to fix nonces
- User funds effectively frozen

## Proposed Solutions

### Option A: Deferred Nonce Increment (Recommended)
**Effort:** Small | **Risk:** Low

```python
def mine_pending_transactions(self, miner_address: str) -> Optional[Block]:
    # ... create block ...

    # Track nonce changes but don't commit yet
    nonce_changes = []
    for tx in new_block.transactions:
        if tx.sender != "COINBASE":
            nonce_changes.append((tx.sender, tx.nonce))

    # Try to persist block
    try:
        self.storage.save_block(new_block)
        self.storage.save_state_to_disk(...)

        # Only commit nonces after successful persistence
        for sender, nonce in nonce_changes:
            self.nonce_tracker.increment_nonce(sender, nonce)

        return new_block

    except Exception as e:
        self.logger.error(f"Block persistence failed, nonces not updated: {e}")
        return None
```

### Option B: Nonce Tracker with Rollback
**Effort:** Medium | **Risk:** Low

```python
class NonceTracker:
    def increment_nonce(self, address: str, nonce: int) -> str:
        """Returns transaction ID for potential rollback"""
        tx_id = f"{address}:{nonce}:{time.time()}"
        self._pending_increments[tx_id] = (address, nonce)
        self._nonces[address] = nonce + 1
        return tx_id

    def commit(self, tx_ids: List[str]):
        """Finalize pending increments"""
        for tx_id in tx_ids:
            del self._pending_increments[tx_id]

    def rollback(self, tx_ids: List[str]):
        """Revert pending increments"""
        for tx_id in tx_ids:
            if tx_id in self._pending_increments:
                address, nonce = self._pending_increments[tx_id]
                self._nonces[address] = nonce
                del self._pending_increments[tx_id]
```

## Recommended Action

Implement Option A immediately. This is a **user-facing critical bug**.

## Technical Details

**Affected Components:**
- Blockchain mining (`blockchain.py`)
- Nonce tracker
- State persistence

**Database Changes:** None

## Acceptance Criteria

- [ ] Nonces only increment after successful block persistence
- [ ] Failed block addition leaves nonces unchanged
- [ ] Unit test: block persistence failure preserves nonces
- [ ] Integration test: recovery after disk failure
- [ ] No user account lockouts possible

## Work Log

| Date | Action | Result |
|------|--------|--------|
| 2025-12-05 | Issue identified by data-integrity-guardian agent | Critical vulnerability |

## Resources

- Related: Issue 004 (Missing atomicity in add_block)
- [Nonce Management Best Practices](https://ethereum.org/developers/docs/transactions)
