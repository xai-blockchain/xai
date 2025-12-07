# Integer Overflow in DeFi Lending Calculations

---
status: pending
priority: p1
issue_id: 025
tags: [security, defi, overflow, lending, code-review]
dependencies: []
---

## Problem Statement

Multiple arithmetic operations on balances, debt, and collateral in the lending protocol use `+=`, `-=` without overflow protection. While Python's arbitrary precision integers prevent actual overflow, extremely large values can cause unexpected behavior and accounting errors.

## Findings

### Locations
**File:** `src/xai/core/defi/lending.py`
- Lines 282, 581, 824-825, 833, 994, 1009

### Evidence

```python
state.total_supplied += amount  # Line 282 - No bounds check
state.total_borrowed += amount  # Line 581 - No bounds check
total_collateral += value  # Line 824 - Can grow unbounded
weighted_ltv += value * config.ltv // self.BASIS_POINTS  # Line 825 - Large intermediate
total_debt += debt * self._get_price(asset)  # Line 833 - Multiplication overflow risk
```

### Attack Scenarios

1. **Supply Inflation**: Repeatedly supply until total_supplied exceeds realistic bounds
2. **Collateral Manipulation**: Create positions with astronomically large collateral values
3. **Debt Amplification**: Compound interest calculations with large principal
4. **Liquidation Gaming**: Manipulate health factors via extreme values

### Impact

- **Accounting Errors**: Protocol reports incorrect totals
- **Insolvency Risk**: Bad debt hidden by overflow behavior
- **Liquidation Failures**: Health factor calculations break down
- **Fund Loss**: Users unable to withdraw due to accounting bugs

## Proposed Solutions

### Option A: Explicit Bounds Checking (Recommended)
**Effort:** Medium | **Risk:** Low

```python
from decimal import Decimal, ROUND_DOWN
from typing import Final

class LendingPool:
    MAX_SUPPLY: Final[int] = 121_000_000 * 10**18  # Max supply in smallest units
    MAX_DEBT: Final[int] = 121_000_000 * 10**18
    MAX_COLLATERAL: Final[int] = 10**36  # Reasonable upper bound

    def _safe_add(self, current: int, amount: int, max_value: int, name: str) -> int:
        """Add with overflow protection."""
        result = current + amount
        if result > max_value:
            raise VMExecutionError(
                f"{name} overflow: {current} + {amount} = {result} exceeds {max_value}"
            )
        if result < 0:
            raise VMExecutionError(f"{name} underflow: result {result} is negative")
        return result

    def supply(self, caller: str, asset: str, amount: int) -> bool:
        # Validate amount
        if amount <= 0 or amount > self.MAX_SUPPLY:
            raise VMExecutionError(f"Invalid supply amount: {amount}")

        state = self._get_asset_state(asset)

        # Safe addition with bounds check
        state.total_supplied = self._safe_add(
            state.total_supplied, amount, self.MAX_SUPPLY, "total_supplied"
        )

        # ... rest of supply logic
```

### Option B: Decimal Arithmetic
**Effort:** Large | **Risk:** Medium

Use Python's Decimal for all financial calculations:

```python
from decimal import Decimal, getcontext

# Set precision for financial calculations
getcontext().prec = 38  # 38 significant figures

class LendingPool:
    def _calculate_health_factor(self, user: str) -> Decimal:
        total_collateral = Decimal(0)
        total_debt = Decimal(0)

        for asset, config in self.markets.items():
            position = self._get_position(user, asset)
            price = Decimal(self._get_price(asset))

            collateral_value = Decimal(position.collateral) * price / Decimal(10**18)
            debt_value = Decimal(position.debt) * price / Decimal(10**18)

            total_collateral += collateral_value * Decimal(config.ltv) / Decimal(10000)
            total_debt += debt_value

        if total_debt == 0:
            return Decimal("inf")

        return total_collateral / total_debt
```

### Option C: Invariant Assertions
**Effort:** Small | **Risk:** Low

Add runtime invariant checks:

```python
def _assert_invariants(self, state: AssetState) -> None:
    """Assert lending pool invariants hold."""
    assert state.total_supplied >= state.total_borrowed, "Supplied < Borrowed"
    assert state.total_supplied <= self.MAX_SUPPLY, "Supply overflow"
    assert state.total_borrowed >= 0, "Negative debt"

    # Utilization sanity check
    if state.total_supplied > 0:
        utilization = state.total_borrowed / state.total_supplied
        assert 0 <= utilization <= 1.0, f"Invalid utilization: {utilization}"
```

## Recommended Action

Implement Option A with Option C as defense-in-depth. All DeFi calculations MUST have explicit bounds.

## Technical Details

**Affected Components:**
- Lending pool
- Borrow/supply functions
- Health factor calculations
- Liquidation logic
- Interest accrual

**Database Changes:** None

## Acceptance Criteria

- [ ] All arithmetic operations have bounds checks
- [ ] MAX_SUPPLY and MAX_DEBT constants defined
- [ ] Invariant assertions after every state change
- [ ] Unit tests for boundary conditions
- [ ] Fuzz tests with extreme values
- [ ] Integration test: total_supplied >= total_borrowed always

## Work Log

| Date | Action | Result |
|------|--------|--------|
| 2025-12-07 | Issue identified by security-sentinel agent | Critical accounting vulnerability |

## Resources

- [Compound Finance Accounting](https://compound.finance/docs)
- [Aave Safety Module](https://docs.aave.com/developers/safety-module)
