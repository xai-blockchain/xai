# Missing Atomicity in add_block() UTXO Updates

---
status: pending
priority: p1
issue_id: 004
tags: [data-integrity, consensus, blockchain, code-review]
dependencies: []
---

## Problem Statement

In `add_block()`, when a reorganization is triggered via `_handle_fork()`, there's no atomic rollback mechanism if the fork handling fails partway through. The code directly modifies UTXO state without creating a snapshot first.

## Findings

### Location
**File:** `src/xai/core/blockchain.py` (Lines 2630-2800)

### Evidence

```python
# Line 2750-2780: Block is added to chain without snapshot
# If _handle_fork() is called (line 2757), it can fail after partial UTXO updates
if block.header.index < len(self.chain):
    if not self._handle_fork(block):  # <- Can fail after mutations
        return False
```

Unlike `replace_chain()` which has snapshot/restore (line 3304-3349), `add_block()` lacks this protection.

### Attack Scenario

1. Node receives competing fork block at height 100
2. `add_block()` calls `_handle_fork()`
3. Fork processing begins, modifies UTXO set partially
4. Fork validation fails mid-way (e.g., invalid signature at block 102)
5. Function returns False but UTXO set is left in inconsistent state
6. No rollback occurs - UTXOs are corrupted

### Impact

- Permanent UTXO corruption requiring full blockchain resync
- Node becomes unusable
- Potential fund loss if corrupted state is used

## Proposed Solutions

### Option A: Snapshot Before Fork Handling (Recommended)
**Effort:** Medium | **Risk:** Low

```python
def add_block(self, block: Block) -> bool:
    # Create snapshot before any state modifications
    utxo_snapshot = self.utxo_manager.snapshot()
    nonce_snapshot = self.nonce_tracker.snapshot()

    try:
        if block.header.index < len(self.chain):
            if not self._handle_fork(block):
                # Restore on failure
                self.utxo_manager.restore(utxo_snapshot)
                self.nonce_tracker.restore(nonce_snapshot)
                return False

        # ... rest of add_block logic ...
        return True

    except Exception as e:
        # Restore on any exception
        self.utxo_manager.restore(utxo_snapshot)
        self.nonce_tracker.restore(nonce_snapshot)
        self.logger.error(f"add_block failed, state restored: {e}")
        return False
```

### Option B: Copy-on-Write State Manager
**Effort:** Large | **Risk:** Medium

Implement copy-on-write semantics for all state:

```python
class AtomicStateManager:
    def __init__(self, utxo_manager, nonce_tracker):
        self.utxo = utxo_manager
        self.nonces = nonce_tracker

    @contextmanager
    def atomic(self):
        snapshot = self._snapshot_all()
        try:
            yield
        except Exception:
            self._restore_all(snapshot)
            raise
```

## Recommended Action

Implement Option A immediately. This is a **data integrity critical bug**.

## Technical Details

**Affected Components:**
- Blockchain core (`blockchain.py`)
- UTXO manager
- Nonce tracker
- Fork handling

**Database Changes:** None (but need snapshot/restore methods)

## Acceptance Criteria

- [ ] `add_block()` creates state snapshots before modifications
- [ ] All failure paths restore snapshots
- [ ] Unit test: partial fork failure restores state
- [ ] Integration test: concurrent fork handling
- [ ] No UTXO corruption after failed block additions

## Work Log

| Date | Action | Result |
|------|--------|--------|
| 2025-12-05 | Issue identified by data-integrity-guardian agent | Critical vulnerability |

## Resources

- Related: Issue 003 (Race condition in chain reorg)
- [ACID Properties](https://en.wikipedia.org/wiki/ACID)
