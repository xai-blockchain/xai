---
status: complete
priority: p2
issue_id: "040"
tags: [security, medium, consensus, double-spend]
dependencies: []
---

# Pending UTXO Timeout May Enable Brief Double-Spend Window

## Problem Statement

The `_pending_timeout` is set to 300 seconds (5 minutes). If a transaction is added to the mempool, its UTXOs are locked for 5 minutes. If the network is slow or the transaction is stuck, the lock expires and those UTXOs become available again while the original transaction may still be propagating.

**Why it matters:** An attacker could potentially craft a timing attack where they submit a transaction, wait for the lock to expire, then submit a conflicting transaction.

## Findings

**Location:** `/home/hudson/blockchain-projects/xai/src/xai/core/transactions/utxo_manager.py:90`

## Proposed Solutions

### Option 1: Transaction-Lifecycle-Based Locks (Recommended)
- UTXOs unlocked only when transaction is rejected, included in block, or evicted from mempool
- **Pros:** Eliminates timing attack window
- **Cons:** More complex state management
- **Effort:** Medium (1-2 days)
- **Risk:** Low

### Option 2: Extend Timeout
- Increase timeout to 30+ minutes
- **Pros:** Simple
- **Cons:** Doesn't fully eliminate the issue
- **Effort:** Small (1 hour)
- **Risk:** Medium

## Recommended Action

Implement Option 1 - tie UTXO locks to transaction lifecycle.

## Acceptance Criteria

- [ ] UTXO locks tied to transaction state, not fixed timeout
- [ ] Locks released only on explicit rejection/inclusion/eviction
- [ ] Unit tests for lock lifecycle

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2025-12-30 | Identified during security audit | Fixed timeouts create attack windows |
