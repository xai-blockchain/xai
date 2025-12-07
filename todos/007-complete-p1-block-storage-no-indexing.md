# Blockchain Storage: No Block Indexing - O(n) Lookups

---
status: pending
priority: p1
issue_id: 007
tags: [performance, storage, scalability, code-review]
dependencies: []
---

## Problem Statement

The `load_block_from_disk()` and `load_chain_from_disk()` methods perform **full sequential scans** of all block files, parsing every JSON line to find a specific block. This creates O(n) time complexity for block lookups where n = chain height.

## Findings

### Location
**File:** `src/xai/core/blockchain_storage.py` (Lines 195-258, 264-328)

### Evidence

```python
# Lines 209-258: Linear scan through ALL blocks
for block_file in block_files:
    with open(os.path.join(self.blocks_dir, block_file), "r") as f:
        for line in f:  # CRITICAL: Reads every block
            block_data = json.loads(line)
            if block_data["header"]["index"] == block_index:  # Only check after parsing
```

### Performance Impact at Scale

| Chain Height | Avg Query Time | Impact |
|-------------|----------------|--------|
| 10,000 | ~1s | Noticeable lag |
| 100,000 | ~10s | Request timeouts |
| 1,000,000 | ~100s | Unusable |

- At 1ms per JSON parse: 100 seconds to fetch latest block at 100k height
- API queries (`/block/<index>`) will timeout under load
- Sync from peers becomes impossibly slow

## Proposed Solutions

### Option A: SQLite Block Index (Recommended)
**Effort:** Medium | **Risk:** Low

```python
# src/xai/core/block_index.py
import sqlite3

class BlockIndex:
    def __init__(self, db_path: str):
        self.conn = sqlite3.connect(db_path)
        self._init_schema()

    def _init_schema(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS block_index (
                block_index INTEGER PRIMARY KEY,
                block_hash TEXT UNIQUE,
                file_path TEXT,
                file_offset INTEGER,
                timestamp REAL
            )
        """)
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_hash ON block_index(block_hash)")

    def index_block(self, block_index: int, block_hash: str, file_path: str, offset: int):
        self.conn.execute(
            "INSERT OR REPLACE INTO block_index VALUES (?, ?, ?, ?, ?)",
            (block_index, block_hash, file_path, offset, time.time())
        )

    def get_block_location(self, block_index: int) -> Optional[Tuple[str, int]]:
        row = self.conn.execute(
            "SELECT file_path, file_offset FROM block_index WHERE block_index = ?",
            (block_index,)
        ).fetchone()
        return row if row else None

    def get_by_hash(self, block_hash: str) -> Optional[Tuple[str, int]]:
        row = self.conn.execute(
            "SELECT file_path, file_offset FROM block_index WHERE block_hash = ?",
            (block_hash,)
        ).fetchone()
        return row if row else None
```

### Option B: File-Per-Block Storage
**Effort:** Large | **Risk:** Medium

Store each block in separate file:
```
blocks/
  000000.json
  000001.json
  ...
  099999.json
```

Direct file access: `blocks/{block_index:06d}.json`

### Option C: LRU Cache + Index
**Effort:** Small | **Risk:** Low

Add LRU cache for recent blocks + simple index file:

```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_block_cached(self, block_index: int) -> Optional[Block]:
    return self._load_block_from_index(block_index)
```

## Recommended Action

Implement Option A (SQLite index) + Option C (LRU cache). This provides:
- O(1) lookups via index
- Memory efficiency via LRU cache
- Backward compatibility with existing storage

## Technical Details

**Affected Components:**
- Block storage (`blockchain_storage.py`)
- Block retrieval APIs
- Chain sync
- Explorer backend

**Database Changes:** New SQLite database for block index

## Acceptance Criteria

- [ ] Block lookup is O(1) via index
- [ ] LRU cache for 1000 most recent blocks
- [ ] Index survives restart (persisted to disk)
- [ ] Migration script for existing chains
- [ ] Benchmark: <10ms block lookup at any height

## Work Log

| Date | Action | Result |
|------|--------|--------|
| 2025-12-05 | Issue identified by performance-oracle agent | Critical bottleneck |

## Resources

- [LevelDB](https://github.com/google/leveldb) - Alternative to SQLite
- [RocksDB](https://rocksdb.org/) - High-performance option
