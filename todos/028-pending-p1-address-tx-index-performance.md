# O(n²) Transaction History - Missing Address Index

---
status: pending
priority: p1
issue_id: 028
tags: [performance, scalability, database, indexing, code-review]
dependencies: [007]
---

## Problem Statement

The `get_transaction_history_window()` method performs a nested loop: O(n blocks) × O(m transactions per block), loading each block from disk sequentially. This is an O(n²) operation for address history queries that becomes unusable at scale.

## Findings

### Location
**File:** `src/xai/core/blockchain.py` (Lines 889-933)

### Evidence

```python
# CURRENT IMPLEMENTATION (O(n²))
for idx in range(len(self.chain)):  # O(n blocks)
    block_obj = self.storage.load_block_from_disk(idx)  # Disk I/O for each block
    for tx in block_obj.transactions:  # O(m transactions)
        if tx.sender != address and tx.recipient != address:
            continue
        # Collect matching transactions
```

### Performance Impact

| Blocks | Transactions | Query Time | Status |
|--------|-------------|------------|--------|
| 1,000 | 10,000 | ~1 second | Slow |
| 10,000 | 100,000 | ~30 seconds | Unusable |
| 100,000 | 1,000,000 | ~5 minutes | BROKEN |
| 1,000,000 | 10,000,000 | ~1 hour | CRITICAL |

### Impact

- **API Timeouts**: `/history/<address>` endpoint times out
- **Explorer Broken**: Block explorer cannot show address history
- **Wallet Unusable**: Wallet balance queries take forever
- **DoS Vector**: Attacker queries expensive addresses to DoS node

## Proposed Solutions

### Option A: SQLite Address Index (Recommended)
**Effort:** Medium | **Risk:** Low

```python
import sqlite3
from typing import List, Tuple

class AddressTransactionIndex:
    """O(log n) address transaction lookups using SQLite index."""

    def __init__(self, db_path: str):
        self.db = sqlite3.connect(db_path, check_same_thread=False)
        self._init_schema()

    def _init_schema(self) -> None:
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS address_txs (
                address TEXT NOT NULL,
                block_index INTEGER NOT NULL,
                tx_index INTEGER NOT NULL,
                txid TEXT NOT NULL,
                is_sender BOOLEAN NOT NULL,
                amount INTEGER NOT NULL,
                timestamp REAL NOT NULL,
                PRIMARY KEY (address, block_index, tx_index)
            )
        """)
        self.db.execute(
            "CREATE INDEX IF NOT EXISTS idx_address ON address_txs(address)"
        )
        self.db.execute(
            "CREATE INDEX IF NOT EXISTS idx_txid ON address_txs(txid)"
        )
        self.db.commit()

    def index_transaction(
        self,
        tx: Transaction,
        block_index: int,
        tx_index: int,
        timestamp: float
    ) -> None:
        """Index a transaction for both sender and recipient."""
        entries = []

        if tx.sender:
            entries.append((
                tx.sender, block_index, tx_index, tx.txid,
                True, -tx.amount, timestamp
            ))

        if tx.recipient:
            entries.append((
                tx.recipient, block_index, tx_index, tx.txid,
                False, tx.amount, timestamp
            ))

        self.db.executemany(
            """INSERT OR REPLACE INTO address_txs
               (address, block_index, tx_index, txid, is_sender, amount, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            entries
        )

    def get_transactions(
        self,
        address: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Tuple]:
        """O(log n) lookup instead of O(n²) scan."""
        cursor = self.db.execute(
            """SELECT block_index, tx_index, txid, is_sender, amount, timestamp
               FROM address_txs
               WHERE address = ?
               ORDER BY block_index DESC, tx_index DESC
               LIMIT ? OFFSET ?""",
            (address, limit, offset)
        )
        return cursor.fetchall()

    def get_balance_changes(self, address: str) -> int:
        """Calculate net balance from indexed transactions."""
        cursor = self.db.execute(
            "SELECT SUM(amount) FROM address_txs WHERE address = ?",
            (address,)
        )
        result = cursor.fetchone()[0]
        return result or 0
```

### Option B: In-Memory Index with LevelDB Persistence
**Effort:** Medium | **Risk:** Low

```python
import plyvel
from collections import defaultdict

class AddressIndex:
    """In-memory index backed by LevelDB for persistence."""

    def __init__(self, db_path: str):
        self.db = plyvel.DB(db_path, create_if_missing=True)
        self.memory_index: Dict[str, List[TxRef]] = defaultdict(list)
        self._load_from_disk()

    def _load_from_disk(self) -> None:
        """Load index into memory on startup."""
        for key, value in self.db:
            if key.startswith(b"addr:"):
                address = key[5:].decode()
                self.memory_index[address] = msgpack.unpackb(value)

    def get_transactions(self, address: str, limit: int = 100) -> List[TxRef]:
        """O(1) lookup from memory."""
        txs = self.memory_index.get(address, [])
        return txs[:limit]  # Already sorted by block height DESC
```

### Option C: Streaming API with Pagination
**Effort:** Small | **Risk:** Low

Add streaming/pagination to existing method as temporary fix:

```python
def get_transaction_history_paginated(
    self,
    address: str,
    start_block: int = 0,
    limit: int = 100
) -> Generator[Transaction, None, None]:
    """Paginated history query - still O(n) but bounded."""
    count = 0
    for idx in range(start_block, len(self.chain)):
        if count >= limit:
            break
        block = self.storage.load_block_from_disk(idx)
        for tx in block.transactions:
            if tx.sender == address or tx.recipient == address:
                yield tx
                count += 1
                if count >= limit:
                    break
```

## Recommended Action

Implement Option A (SQLite index) - it's the industry standard approach for blockchain explorers.

## Technical Details

**Integration Points:**
1. Index new transactions in `add_block()`
2. Rebuild index on reorg via `replace_chain()`
3. API endpoints use index instead of chain scan
4. Separate index DB file in data directory

**Migration:**
```bash
# Build index from existing chain
xai-node --rebuild-address-index
```

## Acceptance Criteria

- [ ] SQLite address index implemented
- [ ] Index updated on new blocks
- [ ] Index rebuilt on chain reorg
- [ ] Query time < 100ms for any address
- [ ] API endpoint uses index
- [ ] Pagination support for large histories
- [ ] Index rebuild tool for existing chains

## Work Log

| Date | Action | Result |
|------|--------|--------|
| 2025-12-07 | Issue identified by performance-oracle agent | Critical scalability blocker |
| 2025-12-05 | Related issue 007 (block indexing) identified | Part of indexing work |

## Resources

- [Ethereum Address Index Design](https://ethereum.org/en/developers/docs/apis/json-rpc/)
- [Bitcoin Core txindex](https://bitcoin.org/en/full-node#other-linux-distributions)
