---
status: pending
priority: p2
issue_id: "042"
tags: [security, medium, storage, encryption]
dependencies: ["037"]
---

# No Encryption at Rest for Blockchain Storage

## Problem Statement

Block index (SQLite), UTXO store (LevelDB), WAL files, checkpoints, and backups store data in plaintext. Checkpoints contain full UTXO snapshots exposing all address balances.

**Why it matters:** Disk compromise exposes complete blockchain state and all address balances.

## Findings

**Locations:**
- `src/xai/core/chain/block_index.py` - SQLite unencrypted
- `src/xai/core/transactions/utxo_store.py` - LevelDB unencrypted
- `src/xai/core/chain/blockchain_wal.py` - WAL files unencrypted
- `src/xai/core/consensus/checkpoints.py` - Checkpoints unencrypted

## Proposed Solutions

### Option 1: Full Disk Encryption (External)
- Recommend LUKS or similar for deployment
- **Pros:** Simple, no code changes
- **Cons:** Requires admin setup
- **Effort:** None (documentation)
- **Risk:** Low

### Option 2: Application-Level Encryption
- Encrypt all files with AES-GCM before writing
- Use SQLCipher for block_index.db
- **Pros:** Defense in depth
- **Cons:** Performance impact, key management
- **Effort:** High (1-2 weeks)
- **Risk:** Medium

## Recommended Action

Document full disk encryption requirement (Option 1) and plan Option 2 for future.

## Acceptance Criteria

- [ ] Documentation recommends full disk encryption
- [ ] Checkpoint UTXO data encrypted (high priority subset)

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2025-12-30 | Identified during security audit | Defense in depth requires multiple layers |
