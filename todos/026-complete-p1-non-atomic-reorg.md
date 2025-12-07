# Non-Atomic Chain Reorganization - State Corruption Risk

---
status: pending
priority: p1
issue_id: 026
tags: [data-integrity, consensus, reorg, atomicity, code-review]
dependencies: [003, 004]
---

## Problem Statement

The `replace_chain()` method performs multi-step state modifications (UTXO set clear, chain rebuild, governance rebuild, nonce rebuild) without proper atomic guarantees. If any step fails after clearing the UTXO set, the rollback may not restore all dependent state correctly.

## Findings

### Location
**File:** `src/xai/core/blockchain.py` (Lines 3278-3489)

### Evidence

```python
# Lines 3387-3408
self.utxo_manager.clear()  # Point of no return - state is destroyed

# Multiple rebuild operations that can fail independently
for block in materialized_chain:
    # If this fails, UTXO state is corrupted
    if not self.utxo_manager.process_transaction_inputs(tx):
        raise Exception(...)

if self.smart_contract_manager:
    self._rebuild_contract_state()  # Can fail independently

self._rebuild_governance_state_from_chain()  # Can fail independently
self._rebuild_nonce_tracker(materialized_chain)  # Can fail independently
```

### Failure Scenarios

1. **UTXO Rebuild Failure**: UTXO cleared, partial rebuild = lost coins
2. **Contract State Failure**: UTXO rebuilt, contracts not = inconsistent DeFi state
3. **Governance Failure**: Chain/UTXO ok, governance broken = voting corruption
4. **Crash During Reorg**: Power loss mid-reorg = unrecoverable corruption

### Impact

- **Data Loss**: Coins permanently lost from failed rebuilds
- **Double-Spend**: UTXO and nonce trackers desynchronized
- **State Divergence**: Different subsystems have different chain views
- **Unrecoverable Node**: Node requires manual intervention to recover

## Proposed Solutions

### Option A: Two-Phase Commit Protocol (Recommended)
**Effort:** Large | **Risk:** Medium

```python
class ReorgTransaction:
    """Atomic chain reorganization with two-phase commit."""

    def __init__(self, blockchain: Blockchain, new_chain: List[Block]):
        self.blockchain = blockchain
        self.new_chain = new_chain
        self.snapshots: Dict[str, Any] = {}
        self.committed = False

    def prepare(self) -> bool:
        """Phase 1: Prepare - snapshot all state."""
        try:
            self.snapshots = {
                "utxo": self.blockchain.utxo_manager.snapshot(),
                "nonce": self.blockchain.nonce_tracker.snapshot(),
                "chain": list(self.blockchain.chain),
                "contracts": self.blockchain.smart_contract_manager.snapshot()
                    if self.blockchain.smart_contract_manager else None,
                "governance": self.blockchain.governance_executor.snapshot()
                    if self.blockchain.governance_executor else None,
                "finality": self.blockchain.finality_manager.snapshot()
                    if self.blockchain.finality_manager else None,
            }
            return True
        except Exception as e:
            logger.error(f"Reorg prepare failed: {e}")
            return False

    def execute(self) -> bool:
        """Phase 2: Execute - apply changes atomically."""
        if not self.snapshots:
            raise RuntimeError("Must call prepare() before execute()")

        try:
            # Clear and rebuild all state
            self.blockchain.utxo_manager.clear()
            self._rebuild_utxo()

            self.blockchain.nonce_tracker.clear()
            self._rebuild_nonces()

            if self.blockchain.smart_contract_manager:
                self._rebuild_contracts()

            if self.blockchain.governance_executor:
                self._rebuild_governance()

            # All succeeded - mark committed
            self.committed = True
            return True

        except Exception as e:
            logger.error(f"Reorg execute failed: {e}")
            self.rollback()
            raise

    def rollback(self) -> None:
        """Rollback to pre-reorg state."""
        if self.committed:
            raise RuntimeError("Cannot rollback committed transaction")

        logger.warning("Rolling back failed reorganization")

        # Restore all state from snapshots
        self.blockchain.utxo_manager.restore(self.snapshots["utxo"])
        self.blockchain.nonce_tracker.restore(self.snapshots["nonce"])
        self.blockchain.chain = self.snapshots["chain"]

        if self.snapshots["contracts"]:
            self.blockchain.smart_contract_manager.restore(self.snapshots["contracts"])

        if self.snapshots["governance"]:
            self.blockchain.governance_executor.restore(self.snapshots["governance"])

        if self.snapshots["finality"]:
            self.blockchain.finality_manager.restore(self.snapshots["finality"])

        logger.info("Rollback completed successfully")
```

### Option B: Write-Ahead Log (WAL)
**Effort:** Large | **Risk:** Low

Implement WAL for crash recovery:

```python
class ReorgWAL:
    """Write-ahead log for crash-safe reorganizations."""

    def __init__(self, wal_path: str):
        self.wal_path = wal_path

    def begin_reorg(self, old_tip: str, new_tip: str) -> int:
        """Log reorg start."""
        entry = {
            "type": "REORG_BEGIN",
            "old_tip": old_tip,
            "new_tip": new_tip,
            "timestamp": time.time()
        }
        return self._append_entry(entry)

    def log_state_snapshot(self, component: str, snapshot: bytes) -> None:
        """Log state snapshot before modification."""
        entry = {
            "type": "STATE_SNAPSHOT",
            "component": component,
            "snapshot": snapshot.hex()
        }
        self._append_entry(entry)

    def commit_reorg(self, seq: int) -> None:
        """Mark reorg as committed."""
        entry = {"type": "REORG_COMMIT", "seq": seq}
        self._append_entry(entry)
        self._fsync()

    def recover_on_startup(self) -> None:
        """Recover from incomplete reorg on node startup."""
        incomplete = self._find_incomplete_reorg()
        if incomplete:
            logger.warning(f"Recovering from incomplete reorg: {incomplete}")
            self._rollback_from_wal(incomplete)
```

## Recommended Action

Implement Option A (two-phase commit) with Option B (WAL) for crash recovery. This addresses both runtime failures and crash scenarios.

## Technical Details

**Affected Components:**
- Chain reorganization logic
- UTXO manager
- Nonce tracker
- Smart contract manager
- Governance executor
- Finality manager

**Database Changes:** Add WAL file for reorg operations

## Acceptance Criteria

- [ ] All state managers support snapshot/restore
- [ ] Two-phase commit for reorg operations
- [ ] WAL for crash recovery
- [ ] Startup recovery from incomplete reorg
- [ ] Unit tests for each failure scenario
- [ ] Integration test: kill node during reorg, verify recovery

## Work Log

| Date | Action | Result |
|------|--------|--------|
| 2025-12-07 | Issue identified by data-integrity-guardian agent | Critical data integrity risk |
| 2025-12-05 | Related issues 003, 004 previously identified | Builds on earlier findings |

## Resources

- [Two-Phase Commit Protocol](https://en.wikipedia.org/wiki/Two-phase_commit_protocol)
- [Write-Ahead Logging](https://en.wikipedia.org/wiki/Write-ahead_logging)
- Bitcoin Core reorg handling
