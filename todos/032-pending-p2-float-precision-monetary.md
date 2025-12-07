# Float Precision in Monetary Calculations

---
status: pending
priority: p2
issue_id: 032
tags: [precision, monetary, data-integrity, defi, code-review]
dependencies: []
---

## Problem Statement

Multiple DeFi and financial modules use Python floats for monetary calculations, which causes precision loss and potential fund discrepancies. Blockchain financial systems require exact arithmetic using Decimal or integer representation.

## Findings

### Locations
**Files:**
- `src/xai/core/defi/lending.py` - Interest calculations
- `src/xai/core/defi/concentrated_liquidity.py` - Liquidity math
- `src/xai/core/trading.py` - Price calculations
- `src/xai/core/transaction.py` - Amount handling

### Evidence

```python
# Examples of float usage in financial calculations

# Interest calculation with floats
interest = principal * rate * time  # Float multiplication

# Price calculation
price = amount_out / amount_in  # Float division

# Fee calculation
fee = amount * 0.003  # Float percentage
```

### Impact

- **Precision Loss**: Accumulated rounding errors over many transactions
- **Fund Discrepancy**: Pool balances may not match sum of deposits
- **Arbitrage Risk**: Precision differences exploitable for profit
- **Audit Failures**: Non-deterministic calculations across nodes

## Proposed Solutions

### Option A: Decimal Module (Recommended)
**Effort:** Medium | **Risk:** Low

```python
from decimal import Decimal, ROUND_DOWN, getcontext

# Set precision for blockchain operations
getcontext().prec = 28

class MonetaryAmount:
    """Fixed-precision monetary amount."""

    PRECISION = 18  # Like Ethereum wei

    def __init__(self, value: str | int | Decimal):
        if isinstance(value, float):
            raise TypeError("Float not allowed for monetary values")
        self.value = Decimal(str(value))

    def __add__(self, other: "MonetaryAmount") -> "MonetaryAmount":
        return MonetaryAmount(self.value + other.value)

    def __mul__(self, other: "MonetaryAmount") -> "MonetaryAmount":
        # Round down to prevent inflation
        result = self.value * other.value
        return MonetaryAmount(result.quantize(
            Decimal(f"1e-{self.PRECISION}"),
            rounding=ROUND_DOWN
        ))

    def to_wei(self) -> int:
        """Convert to integer representation."""
        return int(self.value * Decimal(10 ** self.PRECISION))

    @classmethod
    def from_wei(cls, wei: int) -> "MonetaryAmount":
        """Create from integer representation."""
        return cls(Decimal(wei) / Decimal(10 ** cls.PRECISION))
```

### Option B: Integer-Only Arithmetic
**Effort:** Medium | **Risk:** Low

```python
class TokenAmount:
    """Integer-based token amount (smallest unit)."""

    def __init__(self, amount: int, decimals: int = 18):
        if not isinstance(amount, int):
            raise TypeError("Amount must be integer")
        self.amount = amount
        self.decimals = decimals

    def __add__(self, other: "TokenAmount") -> "TokenAmount":
        assert self.decimals == other.decimals
        return TokenAmount(self.amount + other.amount, self.decimals)

    def mul_ratio(self, numerator: int, denominator: int) -> "TokenAmount":
        """Multiply by ratio without intermediate floats."""
        # amount * numerator // denominator (round down)
        return TokenAmount(
            self.amount * numerator // denominator,
            self.decimals
        )

    def display(self) -> str:
        """Human-readable format."""
        whole = self.amount // (10 ** self.decimals)
        frac = self.amount % (10 ** self.decimals)
        return f"{whole}.{str(frac).zfill(self.decimals)}"
```

## Recommended Action

Implement Option A (Decimal) for new code, Option B for performance-critical paths.

## Technical Details

**Affected Components:**
- Interest rate calculations
- Swap price calculations
- Fee calculations
- Balance tracking
- Liquidity math

**Migration Strategy:**
1. Create MonetaryAmount class
2. Add type checks to reject floats
3. Update calculations one module at a time
4. Add invariant tests for precision

## Acceptance Criteria

- [ ] MonetaryAmount or TokenAmount class implemented
- [ ] Float usage banned in monetary calculations
- [ ] All DeFi calculations use exact arithmetic
- [ ] Type checker configured to flag float in amounts
- [ ] Invariant tests: sum(deposits) == pool.balance
- [ ] Cross-node determinism tests pass

## Work Log

| Date | Action | Result |
|------|--------|--------|
| 2025-12-07 | Issue identified by data-integrity-guardian agent | Financial precision risk |

## Resources

- [Python Decimal Module](https://docs.python.org/3/library/decimal.html)
- [Solidity Fixed Point Math](https://docs.openzeppelin.com/contracts/4.x/utilities#math)
