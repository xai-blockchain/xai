# Consolidate 129 Duplicate Validation Functions

---
status: pending
priority: p2
issue_id: 019
tags: [code-quality, duplication, maintainability, code-review]
dependencies: []
---

## Problem Statement

The codebase has ~129 validation/sanitization functions spread across multiple files, with significant duplication. The same `validate_address` logic appears in 20+ locations.

## Findings

### Duplicate Patterns

`validate_address` appears in:
- `InputSanitizer.validate_address()` (node_api.py)
- `Transaction._validate_address()` (transaction.py)
- `SecurityValidator.validate_address()` (security_validation.py)
- `ERC20._validate_address()` (contracts/erc20.py)
- Plus 20+ other locations

### Impact

- Fix bugs in 20+ places instead of 1
- Inconsistent validation rules
- ~500+ lines of duplicate code
- Testing overhead

## Proposed Solutions

### Option A: Centralized Validation Module (Recommended)
**Effort:** Medium | **Risk:** Low

```python
# src/xai/core/validation.py
"""Centralized validation utilities - single source of truth"""

def validate_address(address: str) -> str:
    """Validate and normalize XAI address"""
    if not address or not isinstance(address, str):
        raise ValueError("Address must be non-empty string")
    address = address.strip()
    if not address.startswith(('xai1', '0x')):
        raise ValueError("Invalid address prefix")
    if len(address) < 40:
        raise ValueError("Address too short")
    return address

def validate_amount(amount: float, *, allow_zero: bool = False) -> Decimal:
    """Validate transaction amount"""
    if not isinstance(amount, (int, float, Decimal)):
        raise ValueError("Amount must be numeric")
    amount = Decimal(str(amount))
    if amount < 0:
        raise ValueError("Amount cannot be negative")
    if not allow_zero and amount == 0:
        raise ValueError("Amount cannot be zero")
    return amount
```

Then replace all duplicates:
```python
# Before (in 20+ files)
def _validate_address(self, addr):
    # duplicate logic

# After
from xai.core.validation import validate_address
```

## Acceptance Criteria

- [ ] Single validation module created
- [ ] All duplicates replaced with imports
- [ ] Consistent validation behavior across codebase
- [ ] ~500 lines removed

## Resources

- [DRY Principle](https://en.wikipedia.org/wiki/Don%27t_repeat_yourself)
