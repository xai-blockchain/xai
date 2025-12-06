# Race Condition in Chain Reorganization with Pending Transactions

---
status: pending
priority: p1
issue_id: 003
tags: [data-integrity, consensus, blockchain, code-review]
dependencies: []
---

## Problem Statement

During `replace_chain()`, pending transactions in the mempool are not validated against the new chain state after reorganization. This creates a window where transactions valid in the old chain may become invalid (double-spends) in the new chain.

## Findings

### Location
**File:** `src/xai/core/blockchain.py` (Lines 3304-3349)

### Evidence

```python
# Line 3330: Nonce tracker is rebuilt from new chain
self._rebuild_nonce_tracker(materialized_chain)

# But pending_transactions are NOT re-validated against new UTXO state
# Line 3336-3341: State is saved but pending txs aren't checked
self.storage.save_state_to_disk(
    self.utxo_manager,
    self.pending_transactions,  # <- Stale transactions from old chain
    self.contracts,
    self.contract_receipts,
)
```

### Attack Scenario

1. Alice has UTXO from block 100 in current chain
2. Transaction TX1 spending that UTXO is in mempool
3. Chain reorg happens, new chain doesn't have block 100
4. TX1 is still in mempool but references non-existent UTXO
5. Next mined block includes TX1, creating invalid state
6. When block is broadcast, other nodes reject it, causing fork

### Impact

- Byzantine state divergence
- Network splits
- Potential double-spend exploitation
- Consensus failure

## Proposed Solutions

### Option A: Mempool Revalidation After Reorg (Recommended)
**Effort:** Medium | **Risk:** Low

```python
def replace_chain(self, new_chain: List[Block]) -> bool:
    # ... existing validation ...

    # After rebuilding state
    self._rebuild_nonce_tracker(materialized_chain)

    # NEW: Revalidate all pending transactions
    valid_pending = []
    for tx in self.pending_transactions:
        try:
            if self.transaction_validator.validate_transaction(tx):
                valid_pending.append(tx)
            else:
                self.logger.warning(f"Evicting invalid tx {tx.txid} after reorg")
        except Exception as e:
            self.logger.warning(f"Tx {tx.txid} failed revalidation: {e}")

    self.pending_transactions = valid_pending

    # Now save state
    self.storage.save_state_to_disk(...)
```

### Option B: Snapshot and Restore Pattern
**Effort:** Large | **Risk:** Medium

Create full state snapshots before reorg, restore on any failure:

```python
def replace_chain(self, new_chain: List[Block]) -> bool:
    snapshot = self._create_full_snapshot()
    try:
        # ... reorg logic ...
        self._revalidate_mempool()
    except Exception:
        self._restore_snapshot(snapshot)
        raise
```

## Recommended Action

Implement Option A immediately. This is a **consensus-critical bug**.

## Technical Details

**Affected Components:**
- Blockchain core (`blockchain.py`)
- Mempool management
- UTXO manager
- Nonce tracker

**Database Changes:** None

## Acceptance Criteria

- [ ] `replace_chain()` revalidates all pending transactions
- [ ] Invalid transactions evicted with logging
- [ ] Unit test: reorg with conflicting mempool transactions
- [ ] Integration test: multi-node reorg scenario
- [ ] No state divergence after reorg

## Work Log

| Date | Action | Result |
|------|--------|--------|
| 2025-12-05 | Issue identified by data-integrity-guardian agent | Critical vulnerability |

## Resources

- [Bitcoin Reorg Handling](https://en.bitcoin.it/wiki/Chain_Reorganization)
- Related: Issue 004 (Missing atomicity in add_block)
