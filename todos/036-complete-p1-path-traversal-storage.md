---
status: complete
priority: p1
issue_id: "036"
tags: [security, critical, storage, path-traversal]
dependencies: []
---

# Path Traversal Vulnerability in Blockchain Storage

## Problem Statement

The `verify_integrity()` method in blockchain_storage.py uses `os.path.join(self.data_dir, filename)` where `filename` comes from stored checksums. If an attacker corrupts the checksum file, they could inject paths like `../../../etc/passwd` to read or verify existence of arbitrary files.

**Why it matters:** Could allow attackers to probe filesystem structure or verify existence of sensitive files outside the blockchain data directory.

## Findings

**Location:** `/home/hudson/blockchain-projects/xai/src/xai/core/chain/blockchain_storage.py:487`

**Evidence:**
```python
# Line 487 - VULNERABLE
for filename, stored_checksum in stored_checksums.items():
    filepath = os.path.join(self.data_dir, filename)  # filename from untrusted source
```

**Attack Vector:**
If checksum.json is corrupted/manipulated:
```json
{"../../../etc/passwd": "abc123", "blocks/blocks_0.json": "def456"}
```

## Proposed Solutions

### Option 1: Path Normalization and Validation (Recommended)
```python
for filename, stored_checksum in stored_checksums.items():
    safe_path = os.path.normpath(os.path.join(self.data_dir, filename))
    if not safe_path.startswith(os.path.normpath(self.data_dir)):
        logger.error("Path traversal attempt detected", extra={"filename": filename})
        return False
    filepath = safe_path
```
- **Pros:** Simple, effective, no external dependencies
- **Cons:** None
- **Effort:** Small (1 hour)
- **Risk:** Low

### Option 2: Allowlist Approach
- Only allow filenames matching specific patterns (blocks/*.json, state/*.json)
- **Pros:** More restrictive
- **Cons:** May break future features
- **Effort:** Small (2 hours)
- **Risk:** Low

## Recommended Action

Implement Option 1 immediately. Add security logging for attempted path traversal.

## Technical Details

**Affected files:**
- `src/xai/core/chain/blockchain_storage.py`

**Components:** Blockchain storage, integrity verification

## Acceptance Criteria

- [ ] All filenames validated before path construction
- [ ] Path traversal attempts logged as security events
- [ ] Unit test for path traversal prevention
- [ ] Existing functionality unchanged

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2025-12-30 | Identified during security audit | Never trust filenames from stored/external data |

## Resources

- [OWASP Path Traversal](https://owasp.org/www-community/attacks/Path_Traversal)
