"""
SafeMath - Overflow Protection for DeFi Calculations.

Provides checked arithmetic operations to prevent integer overflow vulnerabilities
in financial calculations. Implements bounds checking similar to Solidity's SafeMath.

Security considerations:
- All operations check for overflow/underflow before executing
- Maximum values defined for different contexts (supply, debt, collateral)
- Explicit error messages for debugging
- Follows OpenZeppelin SafeMath patterns

Usage:
    from .safe_math import SafeMath, MAX_SUPPLY, MAX_DEBT

    # Safe addition
    result = SafeMath.safe_add(a, b, MAX_SUPPLY, "total_supplied")

    # Safe multiplication
    result = SafeMath.safe_mul(a, b)

    # Fixed-point multiplication
    result = SafeMath.wad_mul(a, b)
"""

from __future__ import annotations

from typing import Final, Optional
from ..vm.exceptions import VMExecutionError


# ==================== Constants ====================

# Maximum safe values for different contexts
# Based on realistic economic bounds for a blockchain ecosystem
MAX_SUPPLY: Final[int] = 121_000_000 * 10**18  # Max supply in smallest units (18 decimals)
MAX_DEBT: Final[int] = 121_000_000 * 10**18    # Max debt in smallest units
MAX_COLLATERAL: Final[int] = 10**36             # Max collateral value (larger for price * amount)
MAX_PRICE: Final[int] = 10**30                   # Max price (prevents overflow in value calculations)
MAX_UINT256: Final[int] = 2**256 - 1             # Standard EVM uint256 max
MAX_UINT128: Final[int] = 2**128 - 1             # For intermediate calculations

# Fixed-point precision constants
WAD: Final[int] = 10**18   # 18 decimal precision for amounts
RAY: Final[int] = 10**27   # 27 decimal precision for rates/indices
Q96: Final[int] = 2**96    # For sqrt price representation (Uniswap V3)
Q128: Final[int] = 2**128  # For extended precision

BASIS_POINTS: Final[int] = 10000  # 100% in basis points


class SafeMath:
    """
    SafeMath provides checked arithmetic operations to prevent overflow vulnerabilities.

    All operations throw VMExecutionError on overflow/underflow, preventing
    silent failures that could lead to accounting errors.
    """

    # ==================== Basic Checked Arithmetic ====================

    @staticmethod
    def safe_add(a: int, b: int, max_value: int, name: str = "value") -> int:
        """
        Add two integers with overflow protection.

        Args:
            a: First operand
            b: Second operand
            max_value: Maximum allowed result
            name: Variable name for error messages

        Returns:
            a + b

        Raises:
            VMExecutionError: If result would overflow or underflow
        """
        if a < 0:
            raise VMExecutionError(f"{name}: negative operand a={a}")
        if b < 0:
            raise VMExecutionError(f"{name}: negative operand b={b}")

        result = a + b

        if result > max_value:
            raise VMExecutionError(
                f"{name} overflow: {a} + {b} = {result} exceeds max {max_value}"
            )

        return result

    @staticmethod
    def safe_sub(a: int, b: int, name: str = "value") -> int:
        """
        Subtract two integers with underflow protection.

        Args:
            a: Minuend
            b: Subtrahend
            name: Variable name for error messages

        Returns:
            a - b

        Raises:
            VMExecutionError: If result would be negative
        """
        if a < 0:
            raise VMExecutionError(f"{name}: negative operand a={a}")
        if b < 0:
            raise VMExecutionError(f"{name}: negative operand b={b}")
        if b > a:
            raise VMExecutionError(
                f"{name} underflow: {a} - {b} would be negative"
            )

        return a - b

    @staticmethod
    def safe_mul(a: int, b: int, max_value: int = MAX_UINT256, name: str = "value") -> int:
        """
        Multiply two integers with overflow protection.

        Args:
            a: First factor
            b: Second factor
            max_value: Maximum allowed result
            name: Variable name for error messages

        Returns:
            a * b

        Raises:
            VMExecutionError: If result would overflow
        """
        if a < 0:
            raise VMExecutionError(f"{name}: negative operand a={a}")
        if b < 0:
            raise VMExecutionError(f"{name}: negative operand b={b}")

        if a == 0 or b == 0:
            return 0

        result = a * b

        # Check for overflow by verifying division
        if result // a != b:
            raise VMExecutionError(
                f"{name} multiplication overflow: {a} * {b}"
            )

        if result > max_value:
            raise VMExecutionError(
                f"{name} overflow: {a} * {b} = {result} exceeds max {max_value}"
            )

        return result

    @staticmethod
    def safe_div(a: int, b: int, name: str = "value") -> int:
        """
        Divide two integers with zero check.

        Args:
            a: Dividend
            b: Divisor
            name: Variable name for error messages

        Returns:
            a // b (integer division)

        Raises:
            VMExecutionError: If divisor is zero
        """
        if b == 0:
            raise VMExecutionError(f"{name} division by zero")
        if a < 0:
            raise VMExecutionError(f"{name}: negative dividend a={a}")
        if b < 0:
            raise VMExecutionError(f"{name}: negative divisor b={b}")

        return a // b

    # ==================== Fixed-Point Arithmetic ====================

    @staticmethod
    def wad_mul(a: int, b: int, round_up: bool = False) -> int:
        """
        Multiply two WAD (18 decimal) fixed-point values.

        Args:
            a: First value in WAD precision
            b: Second value in WAD precision
            round_up: If True, round up; if False, round down

        Returns:
            Product in WAD precision

        Raises:
            VMExecutionError: If result would overflow
        """
        if a < 0 or b < 0:
            raise VMExecutionError(f"wad_mul: negative operands a={a}, b={b}")

        result = SafeMath.safe_mul(a, b, MAX_UINT256, "wad_mul")

        if round_up:
            # Add (WAD - 1) before division to round up
            return (result + WAD - 1) // WAD
        else:
            return result // WAD

    @staticmethod
    def wad_div(a: int, b: int, round_up: bool = False) -> int:
        """
        Divide two values returning WAD precision result.

        Args:
            a: Dividend
            b: Divisor
            round_up: If True, round up; if False, round down

        Returns:
            (a * WAD) / b

        Raises:
            VMExecutionError: If divisor is zero or overflow
        """
        if b == 0:
            raise VMExecutionError("wad_div: division by zero")
        if a < 0 or b < 0:
            raise VMExecutionError(f"wad_div: negative operands a={a}, b={b}")

        numerator = SafeMath.safe_mul(a, WAD, MAX_UINT256, "wad_div")

        if round_up:
            return (numerator + b - 1) // b
        else:
            return numerator // b

    @staticmethod
    def ray_mul(a: int, b: int) -> int:
        """
        Multiply two RAY (27 decimal) fixed-point values.

        Args:
            a: First value in RAY precision
            b: Second value in RAY precision

        Returns:
            Product in RAY precision

        Raises:
            VMExecutionError: If result would overflow
        """
        if a < 0 or b < 0:
            raise VMExecutionError(f"ray_mul: negative operands a={a}, b={b}")

        result = SafeMath.safe_mul(a, b, MAX_UINT256, "ray_mul")

        # Round half up
        half_ray = RAY // 2
        return (result + half_ray) // RAY

    @staticmethod
    def ray_div(a: int, b: int) -> int:
        """
        Divide two values returning RAY precision result.

        Args:
            a: Dividend
            b: Divisor

        Returns:
            (a * RAY) / b

        Raises:
            VMExecutionError: If divisor is zero or overflow
        """
        if b == 0:
            raise VMExecutionError("ray_div: division by zero")
        if a < 0 or b < 0:
            raise VMExecutionError(f"ray_div: negative operands a={a}, b={b}")

        numerator = SafeMath.safe_mul(a, RAY, MAX_UINT256, "ray_div")

        # Round half up
        half_b = b // 2
        return (numerator + half_b) // b

    # ==================== Percentage Calculations ====================

    @staticmethod
    def percentage(amount: int, percentage_bp: int) -> int:
        """
        Calculate percentage of an amount (basis points).

        Args:
            amount: Base amount
            percentage_bp: Percentage in basis points (e.g., 5000 = 50%)

        Returns:
            (amount * percentage_bp) / BASIS_POINTS

        Raises:
            VMExecutionError: If overflow or invalid inputs
        """
        if amount < 0:
            raise VMExecutionError(f"percentage: negative amount {amount}")
        if percentage_bp < 0:
            raise VMExecutionError(f"percentage: negative percentage {percentage_bp}")
        if percentage_bp > BASIS_POINTS:
            raise VMExecutionError(
                f"percentage: percentage {percentage_bp} exceeds 100% ({BASIS_POINTS} bp)"
            )

        result = SafeMath.safe_mul(amount, percentage_bp, MAX_UINT256, "percentage")
        return result // BASIS_POINTS

    # ==================== Bounds Validation ====================

    @staticmethod
    def require_non_negative(value: int, name: str = "value") -> None:
        """
        Require value is non-negative.

        Args:
            value: Value to check
            name: Variable name for error messages

        Raises:
            VMExecutionError: If value is negative
        """
        if value < 0:
            raise VMExecutionError(f"{name} must be non-negative, got {value}")

    @staticmethod
    def require_positive(value: int, name: str = "value") -> None:
        """
        Require value is positive.

        Args:
            value: Value to check
            name: Variable name for error messages

        Raises:
            VMExecutionError: If value is not positive
        """
        if value <= 0:
            raise VMExecutionError(f"{name} must be positive, got {value}")

    @staticmethod
    def require_in_range(
        value: int,
        min_value: int,
        max_value: int,
        name: str = "value"
    ) -> None:
        """
        Require value is within specified range.

        Args:
            value: Value to check
            min_value: Minimum allowed value (inclusive)
            max_value: Maximum allowed value (inclusive)
            name: Variable name for error messages

        Raises:
            VMExecutionError: If value is out of range
        """
        if value < min_value or value > max_value:
            raise VMExecutionError(
                f"{name} must be in range [{min_value}, {max_value}], got {value}"
            )

    @staticmethod
    def require_lte(a: int, b: int, name_a: str = "a", name_b: str = "b") -> None:
        """
        Require a <= b.

        Args:
            a: First value
            b: Second value
            name_a: Name of first value for error messages
            name_b: Name of second value for error messages

        Raises:
            VMExecutionError: If a > b
        """
        if a > b:
            raise VMExecutionError(f"{name_a} ({a}) must be <= {name_b} ({b})")

    @staticmethod
    def require_gte(a: int, b: int, name_a: str = "a", name_b: str = "b") -> None:
        """
        Require a >= b.

        Args:
            a: First value
            b: Second value
            name_a: Name of first value for error messages
            name_b: Name of second value for error messages

        Raises:
            VMExecutionError: If a < b
        """
        if a < b:
            raise VMExecutionError(f"{name_a} ({a}) must be >= {name_b} ({b})")


# ==================== Invariant Assertions ====================

def assert_supply_debt_invariant(total_supplied: int, total_borrowed: int) -> None:
    """
    Assert fundamental lending invariant: total_supplied >= total_borrowed.

    This invariant must ALWAYS hold in a lending protocol. If it doesn't,
    the protocol is insolvent.

    Args:
        total_supplied: Total supplied liquidity
        total_borrowed: Total borrowed amount

    Raises:
        VMExecutionError: If invariant is violated
    """
    if total_supplied < total_borrowed:
        raise VMExecutionError(
            f"CRITICAL: Lending invariant violated! "
            f"total_supplied ({total_supplied}) < total_borrowed ({total_borrowed}). "
            f"Protocol is insolvent."
        )


def assert_utilization_in_bounds(total_supplied: int, total_borrowed: int) -> None:
    """
    Assert utilization is within valid range [0, 1].

    Args:
        total_supplied: Total supplied liquidity
        total_borrowed: Total borrowed amount

    Raises:
        VMExecutionError: If utilization is invalid
    """
    if total_supplied == 0:
        if total_borrowed != 0:
            raise VMExecutionError(
                f"CRITICAL: total_borrowed ({total_borrowed}) > 0 "
                f"but total_supplied is 0"
            )
        return

    # Utilization should be in [0, 1]
    if total_borrowed > total_supplied:
        raise VMExecutionError(
            f"CRITICAL: total_borrowed ({total_borrowed}) > "
            f"total_supplied ({total_supplied})"
        )


def assert_health_factor_valid(health_factor: int, ray: int = RAY) -> None:
    """
    Assert health factor is within valid range.

    Args:
        health_factor: Health factor in RAY precision
        ray: RAY constant value

    Raises:
        VMExecutionError: If health factor is invalid
    """
    if health_factor < 0:
        raise VMExecutionError(
            f"CRITICAL: Invalid health factor {health_factor} < 0"
        )

    # Health factor > 10^10 (10 million) is unrealistic
    max_reasonable_health_factor = ray * 10_000_000
    if health_factor > max_reasonable_health_factor:
        raise VMExecutionError(
            f"CRITICAL: Unrealistic health factor {health_factor} > {max_reasonable_health_factor}"
        )
