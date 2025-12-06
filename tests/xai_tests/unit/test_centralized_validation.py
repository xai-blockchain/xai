"""
Unit tests for centralized validation module.

Tests the centralized validation functions in xai.core.validation
to ensure they work correctly and provide a single source of truth.
"""

import pytest
from decimal import Decimal

from xai.core.validation import (
    validate_address,
    validate_amount,
    validate_fee,
    validate_positive_integer,
    validate_string,
    validate_hex_string,
)


class TestValidateAddress:
    """Test address validation."""

    def test_valid_mainnet_address(self):
        """Test valid mainnet address with XAI prefix."""
        address = "XAI" + "0" * 40
        result = validate_address(address)
        assert result == address

    def test_valid_testnet_address(self):
        """Test valid testnet address with TXAI prefix."""
        address = "TXAI" + "a" * 40
        result = validate_address(address)
        assert result == address

    def test_special_addresses(self):
        """Test special addresses are allowed."""
        assert validate_address("COINBASE") == "COINBASE"
        assert validate_address("XAITRADEFEE") == "XAITRADEFEE"
        assert validate_address("TXAITRADEFEE") == "TXAITRADEFEE"

    def test_special_addresses_can_be_disallowed(self):
        """Test special addresses can be disabled."""
        with pytest.raises(ValueError, match="Invalid address prefix"):
            validate_address("COINBASE", allow_special=False)

    def test_invalid_prefix(self):
        """Test invalid address prefix is rejected."""
        with pytest.raises(ValueError, match="Invalid address prefix"):
            validate_address("INVALID" + "0" * 40)

    def test_empty_address(self):
        """Test empty address is rejected."""
        with pytest.raises(ValueError, match="non-empty string|cannot be empty"):
            validate_address("")

    def test_non_string_address(self):
        """Test non-string address is rejected."""
        with pytest.raises(ValueError, match="must be a non-empty string"):
            validate_address(123)

    def test_legacy_format_address(self):
        """Test legacy format addresses are accepted."""
        # Legacy format: 22-60 hex chars after prefix
        address = "XAI" + "a" * 30
        result = validate_address(address)
        assert result == address


class TestValidateAmount:
    """Test amount validation."""

    def test_valid_amount(self):
        """Test valid amount."""
        assert validate_amount(10.5) == 10.5
        assert validate_amount(100) == 100.0
        assert validate_amount(Decimal("50.25")) == 50.25

    def test_zero_amount_rejected_by_default(self):
        """Test zero amount is rejected by default."""
        with pytest.raises(ValueError, match="cannot be zero"):
            validate_amount(0)

    def test_zero_amount_allowed_when_specified(self):
        """Test zero amount can be allowed."""
        assert validate_amount(0, allow_zero=True) == 0.0

    def test_negative_amount(self):
        """Test negative amount is rejected."""
        with pytest.raises(ValueError, match="cannot be negative"):
            validate_amount(-10)

    def test_nan_amount(self):
        """Test NaN amount is rejected."""
        with pytest.raises(ValueError, match="cannot be NaN"):
            validate_amount(float('nan'))

    def test_infinite_amount(self):
        """Test infinite amount is rejected."""
        with pytest.raises(ValueError, match="cannot be infinite"):
            validate_amount(float('inf'))

    def test_amount_exceeds_max(self):
        """Test amount exceeding maximum is rejected."""
        with pytest.raises(ValueError, match="exceeds maximum"):
            validate_amount(200_000_000)  # More than MAX_SUPPLY

    def test_amount_below_min(self):
        """Test amount below minimum is rejected."""
        with pytest.raises(ValueError, match="too small"):
            validate_amount(0.000000001)  # Less than MIN_AMOUNT

    def test_custom_min_max(self):
        """Test custom min/max values."""
        assert validate_amount(50, min_value=10, max_value=100) == 50.0
        with pytest.raises(ValueError, match="too small"):
            validate_amount(5, min_value=10)
        with pytest.raises(ValueError, match="exceeds maximum"):
            validate_amount(150, max_value=100)

    def test_precision_rounding(self):
        """Test precision is limited to 8 decimal places."""
        # Amount with more than 8 decimal places should be rounded
        result = validate_amount(10.123456789)
        assert result == 10.12345679  # Rounded to 8 decimals

    def test_non_numeric_amount(self):
        """Test non-numeric amount is rejected."""
        with pytest.raises(ValueError, match="must be numeric"):
            validate_amount("not a number")


class TestValidateFee:
    """Test fee validation."""

    def test_valid_fee(self):
        """Test valid fee."""
        assert validate_fee(0.24) == 0.24

    def test_zero_fee_allowed(self):
        """Test zero fee is allowed."""
        assert validate_fee(0) == 0.0

    def test_negative_fee(self):
        """Test negative fee is rejected."""
        with pytest.raises(ValueError, match="cannot be negative"):
            validate_fee(-1)

    def test_excessive_fee(self):
        """Test excessive fee is rejected."""
        with pytest.raises(ValueError, match="exceeds maximum"):
            validate_fee(2000)  # More than MAX_FEE


class TestValidatePositiveInteger:
    """Test positive integer validation."""

    def test_valid_integer(self):
        """Test valid integer."""
        assert validate_positive_integer(42) == 42
        assert validate_positive_integer(0) == 0

    def test_negative_integer(self):
        """Test negative integer is rejected."""
        with pytest.raises(ValueError, match="must be >= 0"):
            validate_positive_integer(-1)

    def test_custom_min_value(self):
        """Test custom minimum value."""
        assert validate_positive_integer(10, min_value=5) == 10
        with pytest.raises(ValueError, match="must be >= 5"):
            validate_positive_integer(3, min_value=5)

    def test_custom_max_value(self):
        """Test custom maximum value."""
        assert validate_positive_integer(50, max_value=100) == 50
        with pytest.raises(ValueError, match="must be <= 100"):
            validate_positive_integer(150, max_value=100)

    def test_string_conversion(self):
        """Test string to integer conversion."""
        assert validate_positive_integer("42") == 42

    def test_invalid_string(self):
        """Test invalid string is rejected."""
        with pytest.raises(ValueError, match="must be an integer"):
            validate_positive_integer("not a number")


class TestValidateString:
    """Test string validation."""

    def test_valid_string(self):
        """Test valid string."""
        assert validate_string("hello") == "hello"

    def test_whitespace_stripped(self):
        """Test whitespace is stripped."""
        assert validate_string("  hello  ") == "hello"

    def test_empty_string_rejected_by_default(self):
        """Test empty string is rejected by default."""
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_string("")
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_string("   ")

    def test_empty_string_allowed_when_specified(self):
        """Test empty string can be allowed."""
        assert validate_string("", allow_empty=True) == ""

    def test_max_length(self):
        """Test maximum length enforcement."""
        assert validate_string("short", max_length=10) == "short"
        with pytest.raises(ValueError, match="too long"):
            validate_string("x" * 1001, max_length=1000)

    def test_control_characters_rejected(self):
        """Test control characters are rejected."""
        with pytest.raises(ValueError, match="invalid control characters"):
            validate_string("hello\x00world")

    def test_newlines_tabs_allowed(self):
        """Test newlines and tabs are allowed."""
        assert validate_string("hello\nworld") == "hello\nworld"
        assert validate_string("hello\tworld") == "hello\tworld"

    def test_non_string(self):
        """Test non-string is rejected."""
        with pytest.raises(ValueError, match="must be a string"):
            validate_string(123)


class TestValidateHexString:
    """Test hex string validation."""

    def test_valid_hex_string(self):
        """Test valid hex string."""
        assert validate_hex_string("abc123") == "abc123"
        assert validate_hex_string("ABCDEF") == "abcdef"  # Converted to lowercase

    def test_exact_length(self):
        """Test exact length requirement."""
        assert validate_hex_string("ab" * 32, exact_length=64) == "ab" * 32
        with pytest.raises(ValueError, match="must be exactly 64 characters"):
            validate_hex_string("ab" * 30, exact_length=64)

    def test_min_max_length(self):
        """Test min/max length requirements."""
        assert validate_hex_string("abc", min_length=2, max_length=5) == "abc"
        with pytest.raises(ValueError, match="at least 5"):
            validate_hex_string("abc", min_length=5)
        with pytest.raises(ValueError, match="at most 5"):
            validate_hex_string("abcdef", max_length=5)

    def test_invalid_hex_characters(self):
        """Test invalid hex characters are rejected."""
        with pytest.raises(ValueError, match="only hexadecimal characters"):
            validate_hex_string("xyz123")

    def test_non_string(self):
        """Test non-string is rejected."""
        with pytest.raises(ValueError, match="must be a string"):
            validate_hex_string(123)


class TestBackwardsCompatibility:
    """Test backwards compatibility with SecurityValidator."""

    def test_can_import_security_validator(self):
        """Test SecurityValidator can still be imported."""
        from xai.core.validation import SecurityValidator, ValidationError
        assert SecurityValidator is not None
        assert ValidationError is not None

    def test_security_validator_methods(self):
        """Test SecurityValidator methods still work."""
        from xai.core.validation import SecurityValidator
        validator = SecurityValidator()

        # Test validate_address
        addr = validator.validate_address("XAI" + "0" * 40)
        assert addr == "XAI" + "0" * 40

        # Test validate_amount
        amt = validator.validate_amount(10.5)
        assert amt == 10.5

        # Test validate_fee
        fee = validator.validate_fee(0.24)
        assert fee == 0.24
