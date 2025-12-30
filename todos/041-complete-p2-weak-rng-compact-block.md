---
status: complete
priority: p2
issue_id: "041"
tags: [security, medium, cryptography, random]
dependencies: []
---

# Weak Random Number Generator in Compact Block

## Problem Statement

The compact block implementation uses `random.getrandbits(64)` for short txid nonce generation instead of the cryptographically secure `secrets.randbits(64)`.

**Why it matters:** Non-cryptographic RNG could be predictable, potentially enabling txid collision attacks.

## Findings

**Location:** `/home/hudson/blockchain-projects/xai/src/xai/core/p2p/compact_block.py:114`

## Proposed Solutions

### Option 1: Use secrets module (Recommended)
```python
import secrets
nonce = secrets.randbits(64)
```
- **Pros:** Cryptographically secure
- **Cons:** None
- **Effort:** Small (15 minutes)
- **Risk:** None

## Recommended Action

Replace `random.getrandbits(64)` with `secrets.randbits(64)`.

## Acceptance Criteria

- [ ] All cryptographic random generation uses `secrets` module
- [ ] Codebase audit for other weak RNG usage

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2025-12-30 | Identified during security audit | Always use secrets for crypto |
