---
status: complete
priority: p1
issue_id: "037"
tags: [security, critical, storage, permissions]
dependencies: []
---

# No Explicit File Permissions on Sensitive Storage Files

## Problem Statement

Sensitive storage files (wallet keys, UTXO data, checkpoints) are created with default umask permissions. On multi-user systems, other users could potentially read blockchain data including wallet information.

**Why it matters:** Private data exposure on shared systems. Potential access to wallet data by unauthorized local users.

## Findings

**Locations:**
- `src/xai/core/chain/blockchain_storage.py` - All atomic writes
- `src/xai/core/chain/blockchain_wal.py` - WAL file creation
- `src/xai/core/consensus/checkpoints.py` - Checkpoint files
- `src/xai/core/transactions/utxo_store.py` - LevelDB store

**Evidence:**
```python
# Current (insecure - uses umask)
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(payload, f, indent=2)
```

## Proposed Solutions

### Option 1: Explicit File Permissions with os.open() (Recommended)
```python
import os
fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, "w", encoding="utf-8") as f:
    json.dump(payload, f, indent=2)
```
- **Pros:** Secure, atomic creation with correct permissions
- **Cons:** More verbose code
- **Effort:** Medium (4-6 hours)
- **Risk:** Low

### Option 2: Create Utility Function
```python
def secure_write(path, content, mode=0o600):
    """Write content to file with explicit permissions."""
    ...
```
- **Pros:** Reusable, consistent
- **Cons:** Requires updating all write sites
- **Effort:** Medium (1 day)
- **Risk:** Low

## Recommended Action

Implement Option 2 - create a secure_write utility and use it across all sensitive file operations.

## Technical Details

**Affected files:**
- `src/xai/core/chain/blockchain_storage.py`
- `src/xai/core/chain/blockchain_wal.py`
- `src/xai/core/consensus/checkpoints.py`
- `src/xai/core/transactions/utxo_store.py`

**Components:** All storage components

## Acceptance Criteria

- [ ] All sensitive files created with 0o600 permissions
- [ ] Directories created with 0o700 permissions
- [ ] Utility function for secure writes
- [ ] Unit tests verify correct permissions

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2025-12-30 | Identified during security audit | Default umask can expose sensitive data |

## Resources

- [Linux File Permissions](https://linux.die.net/man/2/open)
