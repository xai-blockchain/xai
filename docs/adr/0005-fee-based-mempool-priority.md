# ADR-0005: Fee-Based Mempool Priority Queue

**Status:** Accepted
**Date:** 2025-12-28

## Context
Transactions need fair ordering based on fee rate (fee-per-byte), not absolute fee. Large transactions with high fees shouldn't crowd out smaller high-fee-rate transactions.

## Decision
Implemented in `blockchain_components/mempool_mixin.py`:

```python
def _prioritize_transactions(self, transactions, max_count=None):
    # 1. Group by sender, sort by nonce (validity)
    # 2. Sort all by fee rate (descending)
    # 3. Topological sort for UTXO dependencies
```

Uses Python's `list.sort()` (Timsort, O(n log n)) with topological sort via Kahn's algorithm.

## Consequences
**Positive:**
- Fair fee market
- Maintains nonce ordering per sender
- Handles intra-block UTXO dependencies

**Alternatives Considered:**
- Heap-based priority queue: marginal benefit for typical mempool sizes (<10k)
- Skip list: complexity not justified

**Performance:** O(n log n) sorting dominates; acceptable for mempool sizes up to 100k transactions.
