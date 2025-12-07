# Blockchain Storage: No Compression for Old Blocks

---
status: pending
priority: p3
issue_id: 020
tags: [performance, storage, scalability, code-review]
dependencies: [007]
---

## Problem Statement

Blocks are stored as uncompressed JSON, wasting ~70% of disk space. At scale, this creates significant storage costs.

## Findings

### Location
**File:** `src/xai/core/blockchain_storage.py` (Lines 86-103)

### Evidence

```python
# Line 100: No compression
f.write(json.dumps(block.to_dict()) + "\n")
```

### Storage Impact

| Chain Height | Uncompressed | Compressed (gzip) | Savings |
|-------------|--------------|-------------------|---------|
| 100,000 | ~5GB | ~1.5GB | 70% |
| 1,000,000 | ~50GB | ~15GB | 70% |

## Proposed Solution

```python
import gzip

def save_block_to_disk(self, block: Block):
    # Compress blocks older than recent window
    if block.index < self._get_latest_index() - 1000:
        data = gzip.compress(json.dumps(block.to_dict()).encode())
        with open(f"blocks/{block.index}.json.gz", "wb") as f:
            f.write(data)
    else:
        # Recent blocks uncompressed for fast access
        with open(f"blocks/{block.index}.json", "w") as f:
            f.write(json.dumps(block.to_dict()))
```

## Acceptance Criteria

- [ ] Old blocks compressed with gzip
- [ ] Recent blocks remain uncompressed
- [ ] Transparent decompression on read
- [ ] 70% storage reduction

## Resources

- [Python gzip module](https://docs.python.org/3/library/gzip.html)
