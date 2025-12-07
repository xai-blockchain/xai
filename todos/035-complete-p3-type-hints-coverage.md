# Incomplete Type Hints Coverage

---
status: pending
priority: p3
issue_id: 035
tags: [type-safety, maintainability, code-quality, code-review]
dependencies: []
---

## Problem Statement

Many modules have incomplete or missing type hints, reducing IDE support, catching fewer bugs at development time, and making the codebase harder to understand and maintain.

## Findings

### Locations
**Files with Poor Type Coverage:**
- `src/xai/core/blockchain.py` - Mixed type hints
- `src/xai/core/trading.py` - Missing return types
- `src/xai/network/peer_manager.py` - Incomplete parameter types
- `src/xai/core/defi/*.py` - Inconsistent coverage

### Evidence

```python
# Missing type hints
def process_transaction(self, tx):  # No types
    result = self.validate(tx)  # Unknown return type
    return result

# Partial type hints (incomplete)
def calculate_fee(self, amount: float):  # Missing return type
    return amount * self.fee_rate

# Using Any excessively
def handle_message(self, msg: Any) -> Any:  # Defeats purpose of typing
    pass
```

### Impact

- **Bug Detection**: Misses type errors at dev time
- **IDE Support**: Poor autocomplete and navigation
- **Documentation**: Types serve as documentation
- **Refactoring Risk**: Easier to introduce bugs

## Proposed Solutions

### Option A: Strict Type Checking (Recommended)
**Effort:** Medium | **Risk:** Low

```python
# Configure mypy in pyproject.toml
[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_ignores = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
disallow_untyped_decorators = true
no_implicit_optional = true
warn_redundant_casts = true

# Per-module overrides for gradual adoption
[[tool.mypy.overrides]]
module = "xai.core.*"
disallow_untyped_defs = true

[[tool.mypy.overrides]]
module = "xai.network.*"
disallow_untyped_defs = true
```

### Option B: Type Stub Files
**Effort:** Small | **Risk:** Low

Create `.pyi` stub files for critical modules:

```python
# blockchain.pyi
from typing import List, Optional, Dict

class Block:
    index: int
    timestamp: float
    transactions: List[Transaction]
    previous_hash: str
    hash: str
    nonce: int

class Blockchain:
    chain: List[Block]

    def add_block(self, block: Block) -> bool: ...
    def get_block(self, index: int) -> Optional[Block]: ...
    def validate_chain(self) -> bool: ...
```

### Option C: Runtime Type Checking
**Effort:** Small | **Risk:** Low

Add runtime validation for critical functions:

```python
from typing import get_type_hints
from functools import wraps

def enforce_types(func):
    """Decorator to enforce type hints at runtime."""
    hints = get_type_hints(func)

    @wraps(func)
    def wrapper(*args, **kwargs):
        # Validate argument types
        for name, value in kwargs.items():
            if name in hints:
                expected = hints[name]
                if not isinstance(value, expected):
                    raise TypeError(
                        f"{name} must be {expected}, got {type(value)}"
                    )
        return func(*args, **kwargs)
    return wrapper


@enforce_types
def transfer(sender: str, recipient: str, amount: int) -> bool:
    # Runtime type checking enabled
    pass
```

## Recommended Action

Implement Option A with gradual rollout. Start with core modules.

## Technical Details

**Priority Order for Type Hints:**
1. `src/xai/core/transaction.py` - Critical for safety
2. `src/xai/core/blockchain.py` - Core logic
3. `src/xai/core/wallet.py` - Security-sensitive
4. `src/xai/core/defi/*.py` - Financial calculations
5. `src/xai/network/*.py` - External interfaces

**Common Type Patterns:**
```python
from typing import (
    List, Dict, Optional, Union, Tuple,
    TypeVar, Generic, Protocol, Callable
)
from typing_extensions import TypedDict

# Custom types for domain
Address = str  # Could be NewType for stricter checking
TxId = str
BlockHash = str
Amount = int  # Wei-like smallest unit

class TransactionData(TypedDict):
    sender: Address
    recipient: Address
    amount: Amount
    nonce: int
    signature: bytes
```

## Acceptance Criteria

- [ ] mypy configured in pyproject.toml
- [ ] Core modules pass mypy strict
- [ ] CI runs mypy checks
- [ ] No `Any` in public APIs
- [ ] Type coverage > 80%
- [ ] Custom types for domain concepts

## Work Log

| Date | Action | Result |
|------|--------|--------|
| 2025-12-07 | Issue identified by python-reviewer agent | Code quality issue |

## Resources

- [Python Type Hints](https://docs.python.org/3/library/typing.html)
- [mypy Documentation](https://mypy.readthedocs.io/)
- [PEP 484](https://peps.python.org/pep-0484/)
