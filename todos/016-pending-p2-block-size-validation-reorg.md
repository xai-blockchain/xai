# Block Size Validation Bypass in Reorganization

---
status: pending
priority: p2
issue_id: 016
tags: [data-integrity, consensus, security, code-review]
dependencies: []
---

## Problem Statement

When validating candidate chains in `replace_chain()`, block size limits are not enforced. Only `_validate_chain_structure()` is called which checks hashes/PoW but not size limits.

## Findings

### Location
**File:** `src/xai/core/blockchain.py` (Lines 3300-3320)

### Evidence

```python
# Line 3300-3302: Only structural validation
if not self._validate_chain_structure(materialized_chain):
    return False

# _validate_chain_structure (line 3360) doesn't check:
# - MAX_BLOCK_SIZE_BYTES
# - MAX_TRANSACTIONS_PER_BLOCK
# - Transaction size limits

# Compare to add_block() which does check (line 2689):
if not self._block_within_size_limits(block, context="inbound_block"):
    return False
```

### Attack Scenario

1. Attacker creates fork with oversized blocks (e.g., 10MB)
2. Fork has more cumulative work than main chain
3. `replace_chain()` accepts fork without size checks
4. Node now has 10MB blocks in chain
5. When broadcasting, other nodes reject oversized blocks
6. Permanent chain divergence from network

### Impact

- Network consensus failure
- DoS via memory exhaustion
- Chain splits

## Proposed Solutions

### Option A: Add Size Validation to replace_chain() (Recommended)
**Effort:** Small | **Risk:** Low

```python
def _validate_chain_structure(self, chain: List[Block]) -> bool:
    # ... existing validation ...

    # ADD: Block size validation
    for block in chain:
        if not self._block_within_size_limits(block, context="chain_replacement"):
            self.logger.warning(f"Block {block.index} exceeds size limits")
            return False

    return True
```

## Acceptance Criteria

- [ ] `replace_chain()` validates block sizes
- [ ] Oversized blocks rejected during reorg
- [ ] Unit test: reorg with oversized blocks fails
- [ ] No chain divergence possible via size bypass

## Resources

- Related: Issue 003 (Chain reorg race condition)
