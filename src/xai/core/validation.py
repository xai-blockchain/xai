"""
XAI Blockchain - Centralized Validation Utilities

Single source of truth for all validation functions.
Consolidates duplicate validation logic across the codebase.

This module provides:
- Address validation (XAI/TXAI prefixes, hex format)
- Amount validation (range, precision, overflow protection)
- Transaction data validation
- General input sanitization

All validation functions raise ValueError with clear error messages.
"""

from typing import Any, Optional
from decimal import Decimal
import re

from xai.core.security_validation import SecurityValidator, ValidationError


# Constants
MAX_SUPPLY = 121_000_000.0
MIN_AMOUNT = 0.00000001  # 1 satoshi equivalent
MAX_TRANSACTION_AMOUNT = MAX_SUPPLY
MAX_FEE = 1000.0

# Address validation
VALID_PREFIXES = ("XAI", "TXAI")
SPECIAL_ADDRESSES = ("COINBASE", "XAITRADEFEE", "TXAITRADEFEE")
MIN_ADDRESS_LENGTH = 40
MAX_ADDRESS_LENGTH = 100


def validate_address(address: str, *, allow_special: bool = True) -> str:
    """
    Validate and normalize XAI blockchain address.

    XAI addresses follow the format:
    - Mainnet: XAI + 40 hex characters (e.g., XAI1234567890abcdef...)
    - Testnet: TXAI + 40 hex characters (e.g., TXAI1234567890abcdef...)
    - Special: COINBASE, XAITRADEFEE, TXAITRADEFEE (if allow_special=True)

    Args:
        address: Address to validate
        allow_special: Whether to allow special addresses (COINBASE, etc.)

    Returns:
        Validated and normalized address

    Raises:
        ValueError: If address is invalid

    Examples:
        >>> validate_address("XAI" + "0" * 40)
        'XAI0000000000000000000000000000000000000000'
        >>> validate_address("COINBASE")
        'COINBASE'
        >>> validate_address("invalid")
        ValueError: Invalid address format
    """
    if not address or not isinstance(address, str):
        raise ValueError("Address must be a non-empty string")

    address = address.strip()

    if not address:
        raise ValueError("Address cannot be empty")

    # Special addresses
    if allow_special and address in SPECIAL_ADDRESSES:
        return address

    # Standard XAI/TXAI addresses: prefix + 40 hex chars (strict)
    if re.fullmatch(r'(XAI|TXAI)[A-Fa-f0-9]{40}', address):
        return address

    # Legacy format: prefix + variable hex (22-60 chars) for backward compatibility
    if re.fullmatch(r'(XAI|TXAI)[A-Fa-f0-9]{22,60}', address):
        return address

    # Check if prefix is missing
    if not address.startswith(VALID_PREFIXES):
        raise ValueError(
            f"Invalid address prefix: must start with {' or '.join(VALID_PREFIXES)}"
        )

    # Check length
    if len(address) < MIN_ADDRESS_LENGTH:
        raise ValueError(
            f"Address too short: minimum {MIN_ADDRESS_LENGTH} characters"
        )

    if len(address) > MAX_ADDRESS_LENGTH:
        raise ValueError(
            f"Address too long: maximum {MAX_ADDRESS_LENGTH} characters"
        )

    raise ValueError(
        "Invalid address format: must be XAI/TXAI prefix followed by hex characters"
    )


def validate_amount(
    amount: Any,
    *,
    allow_zero: bool = False,
    min_value: Optional[float] = None,
    max_value: Optional[float] = None
) -> float:
    """
    Validate transaction amount.

    Validates that amount is:
    - A valid numeric type
    - Not NaN or infinite
    - Non-negative
    - Within specified bounds
    - Has acceptable precision (max 8 decimal places)

    Args:
        amount: Amount to validate
        allow_zero: Whether to allow zero amounts (default False)
        min_value: Minimum allowed value (default MIN_AMOUNT if not allow_zero)
        max_value: Maximum allowed value (default MAX_TRANSACTION_AMOUNT)

    Returns:
        Validated amount as float, rounded to 8 decimal places

    Raises:
        ValueError: If amount is invalid

    Examples:
        >>> validate_amount(10.5)
        10.5
        >>> validate_amount(0)
        ValueError: Amount cannot be zero
        >>> validate_amount(0, allow_zero=True)
        0.0
        >>> validate_amount(-5)
        ValueError: Amount cannot be negative
    """
    # Type check and conversion
    if not isinstance(amount, (int, float, Decimal)):
        raise ValueError("Amount must be numeric (int, float, or Decimal)")

    try:
        amount_decimal = Decimal(str(amount))
    except (ValueError, TypeError, ArithmeticError) as e:
        raise ValueError(f"Invalid amount value: {e}") from e

    # Check for NaN
    if amount != amount:  # NaN check
        raise ValueError("Amount cannot be NaN")

    # Check for infinity
    try:
        if amount_decimal.is_infinite():
            raise ValueError("Amount cannot be infinite")
    except AttributeError:
        # Fallback for non-Decimal types
        if amount == float('inf') or amount == float('-inf'):
            raise ValueError("Amount cannot be infinite")

    amount_float = float(amount_decimal)

    # Non-negative check
    if amount_float < 0:
        raise ValueError("Amount cannot be negative")

    # Zero check
    if not allow_zero and amount_float == 0:
        raise ValueError("Amount cannot be zero")

    # Minimum value check
    effective_min = min_value if min_value is not None else (0 if allow_zero else MIN_AMOUNT)
    if amount_float < effective_min:
        raise ValueError(
            f"Amount too small: {amount_float} < minimum {effective_min}"
        )

    # Maximum value check
    effective_max = max_value if max_value is not None else MAX_TRANSACTION_AMOUNT
    if amount_float > effective_max:
        raise ValueError(
            f"Amount exceeds maximum: {amount_float} > {effective_max}"
        )

    # Precision check (max 8 decimal places)
    rounded = round(amount_float, 8)
    if abs(amount_float - rounded) > 1e-10:  # Allow tiny floating point errors
        amount_float = rounded

    return amount_float


def validate_fee(fee: Any) -> float:
    """
    Validate transaction fee.

    Fees follow similar rules to amounts but:
    - Zero fees are allowed
    - Maximum fee limit prevents excessive fees

    Args:
        fee: Fee to validate

    Returns:
        Validated fee as float

    Raises:
        ValueError: If fee is invalid

    Examples:
        >>> validate_fee(0.24)
        0.24
        >>> validate_fee(0)
        0.0
        >>> validate_fee(-1)
        ValueError: Fee cannot be negative
    """
    return validate_amount(fee, allow_zero=True, max_value=MAX_FEE)


def validate_positive_integer(
    value: Any,
    *,
    min_value: int = 0,
    max_value: Optional[int] = None
) -> int:
    """
    Validate positive integer value.

    Args:
        value: Value to validate
        min_value: Minimum allowed value (default 0)
        max_value: Maximum allowed value (default 2^63-1)

    Returns:
        Validated integer

    Raises:
        ValueError: If value is invalid
    """
    if not isinstance(value, int):
        try:
            value = int(value)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Value must be an integer: {e}") from e

    if value < min_value:
        raise ValueError(f"Value must be >= {min_value}")

    effective_max = max_value if max_value is not None else (2**63 - 1)
    if value > effective_max:
        raise ValueError(f"Value must be <= {effective_max}")

    return value


def validate_string(
    value: Any,
    *,
    max_length: int = 1000,
    allow_empty: bool = False
) -> str:
    """
    Validate and sanitize string input.

    Args:
        value: String to validate
        max_length: Maximum allowed length
        allow_empty: Whether to allow empty strings

    Returns:
        Sanitized string (whitespace stripped)

    Raises:
        ValueError: If string is invalid
    """
    if not isinstance(value, str):
        raise ValueError("Value must be a string")

    value = value.strip()

    if not allow_empty and not value:
        raise ValueError("Value cannot be empty")

    if len(value) > max_length:
        raise ValueError(f"Value too long: maximum {max_length} characters")

    # No control characters (except newlines, tabs, carriage returns)
    if any(ord(c) < 32 for c in value if c not in '\n\r\t'):
        raise ValueError("Value contains invalid control characters")

    return value


def validate_hex_string(
    value: Any,
    *,
    exact_length: Optional[int] = None,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None
) -> str:
    """
    Validate hexadecimal string.

    Args:
        value: Hex string to validate
        exact_length: Exact length required (optional)
        min_length: Minimum length (optional)
        max_length: Maximum length (optional)

    Returns:
        Validated hex string (lowercase)

    Raises:
        ValueError: If hex string is invalid
    """
    if not isinstance(value, str):
        raise ValueError("Hex string must be a string")

    value = value.strip().lower()

    if not re.match(r'^[0-9a-f]+$', value):
        raise ValueError("Value must contain only hexadecimal characters (0-9, a-f)")

    if exact_length is not None and len(value) != exact_length:
        raise ValueError(f"Hex string must be exactly {exact_length} characters")

    if min_length is not None and len(value) < min_length:
        raise ValueError(f"Hex string must be at least {min_length} characters")

    if max_length is not None and len(value) > max_length:
        raise ValueError(f"Hex string must be at most {max_length} characters")

    return value


# Backwards compatibility: expose SecurityValidator for advanced use cases
__all__ = [
    'validate_address',
    'validate_amount',
    'validate_fee',
    'validate_positive_integer',
    'validate_string',
    'validate_hex_string',
    'SecurityValidator',
    'ValidationError',
]
