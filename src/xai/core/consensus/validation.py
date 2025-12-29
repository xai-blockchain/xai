from __future__ import annotations

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

import re
from decimal import ROUND_DOWN, Decimal, InvalidOperation, getcontext
from typing import Any

from xai.core.wallets.address_checksum import is_checksum_valid, normalize_address, to_checksum_address
from xai.core.wallets.address_checksum import validate_address as validate_checksum
from xai.core.security.security_validation import SecurityValidator, ValidationError

# Set global decimal precision for blockchain operations
getcontext().prec = 28

# Constants
MAX_SUPPLY = 121_000_000.0
MIN_AMOUNT = 0.00000001  # 1 satoshi equivalent
MAX_TRANSACTION_AMOUNT = MAX_SUPPLY
MAX_FEE = 1000.0

# Address validation
VALID_PREFIXES = ("XAI", "TXAI")
SPECIAL_ADDRESSES = ("COINBASE", "XAITRADEFEE", "TXAITRADEFEE", "GOVERNANCE", "STAKING", "TIMECAPSULE")
MIN_ADDRESS_LENGTH = 40
MAX_ADDRESS_LENGTH = 100

class AddressFormatValidator:
    """
    Dedicated XAI address validator with network-aware prefix enforcement.

    Provides strict validation with options to allow legacy formats and special
    system addresses while guarding against malformed or spoofed prefixes.
    """

    def __init__(
        self,
        *,
        allowed_prefixes: Iterable[str] = VALID_PREFIXES,
        expected_prefix: str | None = None,
        allow_special: bool = True,
        allow_legacy: bool = True,
    ) -> None:
        self.allowed_prefixes = tuple(allowed_prefixes)
        self.expected_prefix = expected_prefix
        self.allow_special = allow_special
        self.allow_legacy = allow_legacy

    def _require_prefix(self, address: str) -> str:
        for candidate in sorted(self.allowed_prefixes, key=len, reverse=True):
            if address.startswith(candidate):
                if self.expected_prefix and not address.startswith(self.expected_prefix):
                    raise ValueError(f"Address must use network prefix {self.expected_prefix}")
                return candidate
        raise ValueError(f"Invalid address prefix: must start with {' or '.join(self.allowed_prefixes)}")

    def _validate_hex_body(self, body: str) -> None:
        if not body:
            raise ValueError("Address body missing after prefix")
        if not re.fullmatch(r"[A-Fa-f0-9]+", body):
            raise ValueError("Address body must be hexadecimal")

    def validate(self, address: str, require_checksum: bool = False) -> str:
        """
        Validate and normalize an address. Returns the normalized address.

        Args:
            address: Address to validate
            require_checksum: If True, require valid EIP-55 checksum
        """
        if not address or not isinstance(address, str):
            raise ValueError("Address must be a non-empty string")

        normalized = address.strip()
        if not normalized:
            raise ValueError("Address cannot be empty")

        if self.allow_special and normalized in SPECIAL_ADDRESSES:
            return normalized

        prefix = self._require_prefix(normalized)
        prefix_len = len(prefix)
        body = normalized[prefix_len:]
        self._validate_hex_body(body)

        body_len = len(body)
        if body_len + prefix_len > MAX_ADDRESS_LENGTH:
            raise ValueError(f"Address too long: maximum {MAX_ADDRESS_LENGTH} characters")

        if not self.allow_legacy and body_len != 40:
            raise ValueError("Address must be prefix + 40 hex characters")

        if self.allow_legacy and 22 <= body_len <= 60:
            return normalized
        if body_len == 40:
            # For 40-character hex addresses, optionally validate/apply checksum
            if require_checksum or (body != body.lower() and body != body.upper()):
                # Mixed case present or checksum required - validate it
                is_valid, result = validate_checksum(normalized, require_checksum=require_checksum)
                if not is_valid:
                    raise ValueError(result)
                return result
            return normalized

        raise ValueError("Invalid address format: must be prefix + hex payload")

    def is_valid(self, address: str) -> bool:
        """Return True if address is valid, False otherwise."""
        try:
            self.validate(address)
            return True
        except ValueError:
            return False

def validate_address(address: str, *, allow_special: bool = True, require_checksum: bool = False, apply_checksum: bool = True) -> str:
    """
    Validate and normalize XAI blockchain address.

    Args:
        address: Address to validate
        allow_special: Allow special system addresses (COINBASE, etc.)
        require_checksum: Require valid EIP-55 checksum (strict mode)
        apply_checksum: Return checksummed format (recommended)

    Returns:
        Validated and optionally checksummed address

    See AddressFormatValidator for detailed rules.
    """
    validator = AddressFormatValidator(allow_special=allow_special)
    validated = validator.validate(address, require_checksum=require_checksum)

    # Apply checksum to standard addresses if requested
    if apply_checksum and validated not in SPECIAL_ADDRESSES:
        try:
            validated = normalize_address(validated)
        except ValueError:
            # If checksum fails, return original validated address
            pass

    return validated

def validate_amount(
    amount: Any,
    *,
    allow_zero: bool = False,
    min_value: float | None = None,
    max_value: float | None = None
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
    max_value: int | None = None
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
    exact_length: int | None = None,
    min_length: int | None = None,
    max_length: int | None = None
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

class MonetaryAmount:
    """
    Fixed-precision monetary amount for blockchain financial calculations.

    Uses Decimal internally to avoid floating-point precision errors.
    All arithmetic rounds down to prevent inflation/fund creation.

    Precision: 8 decimal places (like Bitcoin satoshis).
    """

    PRECISION = 8  # Decimal places (1 XAI = 100_000_000 base units)
    _quantizer = Decimal(f"1e-{PRECISION}")

    def __init__(self, value: str | int | Decimal):
        """
        Create a MonetaryAmount from string, int, or Decimal.

        Args:
            value: Numeric value (float is explicitly forbidden)

        Raises:
            TypeError: If value is a float
            ValueError: If value is invalid or out of range
        """
        if isinstance(value, float):
            raise TypeError(
                "Float not allowed for monetary values due to precision loss. "
                "Use string or Decimal instead."
            )

        try:
            self._value = Decimal(str(value)).quantize(
                self._quantizer, rounding=ROUND_DOWN
            )
        except (InvalidOperation, ValueError) as e:
            raise ValueError(f"Invalid monetary value: {value}") from e

        if self._value < 0:
            raise ValueError(f"Monetary amount cannot be negative: {value}")
        if self._value > Decimal(str(MAX_SUPPLY)):
            raise ValueError(f"Amount exceeds max supply: {value}")

    @property
    def value(self) -> Decimal:
        """Return the underlying Decimal value."""
        return self._value

    def __add__(self, other: "MonetaryAmount") -> "MonetaryAmount":
        if not isinstance(other, MonetaryAmount):
            raise TypeError(f"Cannot add MonetaryAmount and {type(other)}")
        return MonetaryAmount(str(self._value + other._value))

    def __sub__(self, other: "MonetaryAmount") -> "MonetaryAmount":
        if not isinstance(other, MonetaryAmount):
            raise TypeError(f"Cannot subtract {type(other)} from MonetaryAmount")
        result = self._value - other._value
        if result < 0:
            raise ValueError("Subtraction would result in negative amount")
        return MonetaryAmount(str(result))

    def __mul__(self, other: "MonetaryAmount" | int | Decimal) -> "MonetaryAmount":
        if isinstance(other, MonetaryAmount):
            result = self._value * other._value
        elif isinstance(other, (int, Decimal)):
            result = self._value * Decimal(str(other))
        else:
            raise TypeError(f"Cannot multiply MonetaryAmount by {type(other)}")
        return MonetaryAmount(str(result.quantize(self._quantizer, rounding=ROUND_DOWN)))

    def __truediv__(self, other: "MonetaryAmount" | int | Decimal) -> "MonetaryAmount":
        if isinstance(other, MonetaryAmount):
            if other._value == 0:
                raise ZeroDivisionError("Cannot divide by zero")
            result = self._value / other._value
        elif isinstance(other, (int, Decimal)):
            if Decimal(str(other)) == 0:
                raise ZeroDivisionError("Cannot divide by zero")
            result = self._value / Decimal(str(other))
        else:
            raise TypeError(f"Cannot divide MonetaryAmount by {type(other)}")
        return MonetaryAmount(str(result.quantize(self._quantizer, rounding=ROUND_DOWN)))

    def __eq__(self, other: object) -> bool:
        if isinstance(other, MonetaryAmount):
            return self._value == other._value
        return False

    def __lt__(self, other: "MonetaryAmount") -> bool:
        return self._value < other._value

    def __le__(self, other: "MonetaryAmount") -> bool:
        return self._value <= other._value

    def __gt__(self, other: "MonetaryAmount") -> bool:
        return self._value > other._value

    def __ge__(self, other: "MonetaryAmount") -> bool:
        return self._value >= other._value

    def __repr__(self) -> str:
        return f"MonetaryAmount('{self._value}')"

    def __str__(self) -> str:
        return str(self._value)

    def to_base_units(self) -> int:
        """Convert to smallest unit (like satoshis/wei)."""
        return int(self._value * Decimal(10 ** self.PRECISION))

    @classmethod
    def from_base_units(cls, base_units: int) -> "MonetaryAmount":
        """Create from smallest unit representation."""
        if not isinstance(base_units, int):
            raise TypeError("Base units must be integer")
        return cls(str(Decimal(base_units) / Decimal(10 ** cls.PRECISION)))

    @classmethod
    def zero(cls) -> "MonetaryAmount":
        """Return a zero amount."""
        return cls("0")

# Backwards compatibility: expose SecurityValidator for advanced use cases
__all__ = [
    'AddressFormatValidator',
    'validate_address',
    'validate_amount',
    'validate_fee',
    'validate_positive_integer',
    'validate_string',
    'validate_hex_string',
    'SecurityValidator',
    'ValidationError',
    'MonetaryAmount',
    'normalize_address',
    'is_checksum_valid',
    'to_checksum_address',
]
