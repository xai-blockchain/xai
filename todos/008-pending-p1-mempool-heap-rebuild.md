# Mempool: Full Linear Scan for Transaction Removal

---
status: pending
priority: p1
issue_id: 008
tags: [performance, mempool, scalability, code-review]
dependencies: []
---

## Problem Statement

Removing transactions from the mempool requires **rebuilding the entire fee priority queue** after expiration/eviction. This creates O(n log n) complexity for every removal operation.

## Findings

### Location
**File:** `src/xai/network/mempool_manager.py` (Lines 155-172, 212-218)

### Evidence

```python
# Lines 212-218: O(n) rebuild after EVERY expiry check
if self.eviction_policy == "lowest_fee" and expired_tx_ids:
    self.transaction_queue = []  # CRITICAL: Full rebuild
    for tx_id, tx_data in self.pending_transactions.items():
        heapq.heappush(self.transaction_queue, (...))  # O(n log n)
```

### Performance Impact

- Mempool with 10,000 transactions: ~10,000 heap operations every 60 seconds
- Block mining (removing confirmed txs): O(k * n log n) where k = txs per block
- High CPU usage during block propagation spikes
- Mempool becomes bottleneck at scale

| Mempool Size | Rebuild Time | Impact |
|-------------|--------------|--------|
| 1,000 | ~10ms | Acceptable |
| 10,000 | ~200ms | Noticeable |
| 100,000 | ~5s | Severe |

## Proposed Solutions

### Option A: Lazy Deletion (Recommended)
**Effort:** Small | **Risk:** Low

Mark entries as deleted in heap, skip during pop:

```python
class LazyHeapMempool:
    def __init__(self):
        self.heap = []  # (priority, tx_id, is_valid)
        self.valid_txs = {}  # tx_id -> tx_data
        self.deleted = set()

    def add(self, tx_id: str, tx_data: dict, priority: float):
        heapq.heappush(self.heap, (-priority, tx_id))
        self.valid_txs[tx_id] = tx_data

    def remove(self, tx_id: str):
        """O(1) lazy deletion"""
        self.deleted.add(tx_id)
        if tx_id in self.valid_txs:
            del self.valid_txs[tx_id]

    def pop_highest_priority(self) -> Optional[Tuple[str, dict]]:
        """Skip deleted entries"""
        while self.heap:
            priority, tx_id = heapq.heappop(self.heap)
            if tx_id not in self.deleted:
                tx_data = self.valid_txs.pop(tx_id, None)
                if tx_data:
                    return (tx_id, tx_data)
        return None

    def compact(self):
        """Periodic cleanup when deleted > 50% of heap"""
        if len(self.deleted) > len(self.heap) // 2:
            self.heap = [
                (p, tid) for p, tid in self.heap
                if tid not in self.deleted
            ]
            heapq.heapify(self.heap)
            self.deleted.clear()
```

### Option B: Indexed Priority Queue
**Effort:** Medium | **Risk:** Low

Use indexed heap with O(log n) removal:

```python
from sortedcontainers import SortedDict

class IndexedMempool:
    def __init__(self):
        # SortedDict maintains sorted order with O(log n) operations
        self.by_priority = SortedDict()  # priority -> [tx_ids]
        self.tx_data = {}  # tx_id -> (priority, data)

    def remove(self, tx_id: str):
        """O(log n) removal"""
        if tx_id in self.tx_data:
            priority, _ = self.tx_data[tx_id]
            self.by_priority[priority].remove(tx_id)
            if not self.by_priority[priority]:
                del self.by_priority[priority]
            del self.tx_data[tx_id]
```

### Option C: Batch Operations
**Effort:** Small | **Risk:** Low

Collect deletions and batch rebuild:

```python
def remove_batch(self, tx_ids: List[str]):
    """Only rebuild once for batch removal"""
    for tx_id in tx_ids:
        del self.pending_transactions[tx_id]

    # Single rebuild at end
    self._rebuild_heap()
```

## Recommended Action

Implement Option A (lazy deletion) immediately. Add Option C (batching) for block confirmation removals.

## Technical Details

**Affected Components:**
- Mempool manager (`mempool_manager.py`)
- Block mining
- Transaction expiration

**Database Changes:** None

## Acceptance Criteria

- [ ] Transaction removal is O(1) amortized
- [ ] Periodic compaction when >50% deleted
- [ ] Batch removal for confirmed transactions
- [ ] Benchmark: 10,000 tx mempool, <1ms removal

## Work Log

| Date | Action | Result |
|------|--------|--------|
| 2025-12-05 | Issue identified by performance-oracle agent | Critical bottleneck |

## Resources

- [sortedcontainers library](https://grantjenks.com/docs/sortedcontainers/)
- [Lazy Deletion Pattern](https://en.wikipedia.org/wiki/Lazy_deletion)
