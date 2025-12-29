"""
Unit tests for xai.core.validation module.

Tests cover:
- Address validation (XAI/TXAI prefixes, special addresses)
- Amount validation (range, precision, overflow protection)
- Fee validation
- Positive integer validation
"""

import pytest
from decimal import Decimal
import math

from xai.core.consensus.validation import (
    validate_address,
    validate_amount,
    validate_fee,
    validate_positive_integer,
    MAX_SUPPLY,
    MIN_AMOUNT,
    MAX_TRANSACTION_AMOUNT,
    MAX_FEE,
    VALID_PREFIXES,
    SPECIAL_ADDRESSES,
)


class TestValidateAddress:
    """Tests for validate_address function."""

    def test_valid_xai_address(self):
        """Valid XAI address with 40 hex chars."""
        addr = "XAI" + "0" * 40
        assert validate_address(addr) == addr

    def test_valid_txai_address(self):
        """Valid TXAI (testnet) address."""
        addr = "TXAI" + "a" * 40
        # Now returns checksummed version
        result = validate_address(addr)
        assert result.startswith("TXAI")
        assert len(result) == 44

    def test_valid_mixed_case_hex(self):
        """Address with mixed case hex characters."""
        addr = "XAI" + "AaBbCcDdEe" * 4
        assert validate_address(addr) == addr

    def test_special_address_coinbase(self):
        """COINBASE special address."""
        assert validate_address("COINBASE") == "COINBASE"

    def test_special_address_xaitradefee(self):
        """XAITRADEFEE special address."""
        assert validate_address("XAITRADEFEE") == "XAITRADEFEE"

    def test_special_address_governance(self):
        """GOVERNANCE special address."""
        assert validate_address("GOVERNANCE") == "GOVERNANCE"

    def test_special_address_staking(self):
        """STAKING special address."""
        assert validate_address("STAKING") == "STAKING"

    def test_special_address_disallowed(self):
        """Special addresses rejected when allow_special=False."""
        with pytest.raises(ValueError, match="prefix"):
            validate_address("COINBASE", allow_special=False)

    def test_empty_address_raises(self):
        """Empty address raises ValueError."""
        with pytest.raises(ValueError, match="non-empty"):
            validate_address("")

    def test_none_address_raises(self):
        """None address raises ValueError."""
        with pytest.raises(ValueError):
            validate_address(None)

    def test_whitespace_only_raises(self):
        """Whitespace-only address raises ValueError."""
        with pytest.raises(ValueError, match="empty"):
            validate_address("   ")

    def test_invalid_prefix_raises(self):
        """Invalid prefix raises ValueError."""
        with pytest.raises(ValueError, match="prefix"):
            validate_address("BTC" + "0" * 40)

    def test_invalid_hex_chars_raises(self):
        """Non-hex characters raise ValueError."""
        with pytest.raises(ValueError, match="hexadecimal"):
            validate_address("XAI" + "G" * 40)  # G is not hex

    def test_address_too_short(self):
        """Address shorter than minimum raises ValueError."""
        with pytest.raises(ValueError):
            validate_address("XAI" + "0" * 10)

    def test_address_strips_whitespace(self):
        """Whitespace is stripped from address."""
        addr = "XAI" + "0" * 40
        assert validate_address(f"  {addr}  ") == addr

    def test_legacy_format_22_chars(self):
        """Legacy format with 22 hex chars."""
        addr = "XAI" + "0" * 22
        assert validate_address(addr) == addr

    def test_legacy_format_60_chars(self):
        """Legacy format with 60 hex chars."""
        addr = "XAI" + "0" * 60
        assert validate_address(addr) == addr


class TestValidateAmount:
    """Tests for validate_amount function."""

    def test_valid_amount_integer(self):
        """Valid integer amount."""
        assert validate_amount(100) == 100.0

    def test_valid_amount_float(self):
        """Valid float amount."""
        assert validate_amount(10.5) == 10.5

    def test_valid_amount_decimal(self):
        """Valid Decimal amount."""
        assert validate_amount(Decimal("10.5")) == 10.5

    def test_zero_not_allowed_by_default(self):
        """Zero amount raises ValueError by default."""
        with pytest.raises(ValueError, match="zero"):
            validate_amount(0)

    def test_zero_allowed_when_specified(self):
        """Zero amount allowed with allow_zero=True."""
        assert validate_amount(0, allow_zero=True) == 0.0

    def test_negative_amount_raises(self):
        """Negative amount raises ValueError."""
        with pytest.raises(ValueError, match="negative"):
            validate_amount(-5)

    def test_nan_raises(self):
        """NaN raises ValueError."""
        with pytest.raises(ValueError, match="NaN"):
            validate_amount(float('nan'))

    def test_infinity_raises(self):
        """Infinity raises ValueError."""
        with pytest.raises(ValueError, match="infinite"):
            validate_amount(float('inf'))

    def test_negative_infinity_raises(self):
        """Negative infinity raises ValueError."""
        with pytest.raises(ValueError, match="infinite"):
            validate_amount(float('-inf'))

    def test_min_amount_enforced(self):
        """Amount below MIN_AMOUNT raises ValueError."""
        tiny = MIN_AMOUNT / 10
        with pytest.raises(ValueError, match="too small"):
            validate_amount(tiny)

    def test_max_amount_enforced(self):
        """Amount above MAX_TRANSACTION_AMOUNT raises ValueError."""
        huge = MAX_TRANSACTION_AMOUNT * 2
        with pytest.raises(ValueError, match="exceeds maximum"):
            validate_amount(huge)

    def test_custom_min_value(self):
        """Custom min_value enforced."""
        with pytest.raises(ValueError, match="too small"):
            validate_amount(5, min_value=10)

    def test_custom_max_value(self):
        """Custom max_value enforced."""
        with pytest.raises(ValueError, match="exceeds maximum"):
            validate_amount(100, max_value=50)

    def test_precision_rounded(self):
        """Amount rounded to 8 decimal places."""
        result = validate_amount(1.123456789123)
        assert result == pytest.approx(1.12345679, rel=1e-8)

    def test_non_numeric_raises(self):
        """Non-numeric type raises ValueError."""
        with pytest.raises(ValueError, match="numeric"):
            validate_amount("100")

    def test_string_numeric_raises(self):
        """String representation of number raises ValueError."""
        with pytest.raises(ValueError, match="numeric"):
            validate_amount("10.5")

    def test_max_supply_boundary(self):
        """Amount at MAX_SUPPLY boundary."""
        assert validate_amount(MAX_SUPPLY) == MAX_SUPPLY

    def test_small_valid_amount(self):
        """Smallest valid amount (MIN_AMOUNT)."""
        assert validate_amount(MIN_AMOUNT) == MIN_AMOUNT


class TestValidateFee:
    """Tests for validate_fee function."""

    def test_valid_fee(self):
        """Valid fee amount."""
        assert validate_fee(0.24) == 0.24

    def test_zero_fee_allowed(self):
        """Zero fee is allowed."""
        assert validate_fee(0) == 0.0

    def test_negative_fee_raises(self):
        """Negative fee raises ValueError."""
        with pytest.raises(ValueError, match="negative"):
            validate_fee(-1)

    def test_max_fee_enforced(self):
        """Fee above MAX_FEE raises ValueError."""
        with pytest.raises(ValueError, match="exceeds maximum"):
            validate_fee(MAX_FEE + 100)

    def test_fee_at_max(self):
        """Fee at exactly MAX_FEE is valid."""
        assert validate_fee(MAX_FEE) == MAX_FEE


class TestValidatePositiveInteger:
    """Tests for validate_positive_integer function."""

    def test_valid_positive_integer(self):
        """Valid positive integer."""
        assert validate_positive_integer(10) == 10

    def test_zero_allowed_by_default(self):
        """Zero is valid with default min_value=0."""
        assert validate_positive_integer(0) == 0

    def test_custom_min_value(self):
        """Custom min_value enforced."""
        with pytest.raises(ValueError):
            validate_positive_integer(5, min_value=10)

    def test_custom_max_value(self):
        """Custom max_value enforced."""
        with pytest.raises(ValueError):
            validate_positive_integer(100, max_value=50)

    def test_float_converted_to_int(self):
        """Float value converted to int (truncated)."""
        # Implementation converts floats to int
        assert validate_positive_integer(10.5) == 10
        assert validate_positive_integer(10.9) == 10

    def test_negative_raises(self):
        """Negative integer raises ValueError."""
        with pytest.raises(ValueError):
            validate_positive_integer(-5)

    def test_string_numeric_converted(self):
        """Numeric string converted to int."""
        # Implementation converts numeric strings to int
        assert validate_positive_integer("10") == 10

    def test_string_non_numeric_raises(self):
        """Non-numeric string raises ValueError."""
        with pytest.raises(ValueError):
            validate_positive_integer("abc")


class TestConstants:
    """Tests for validation constants."""

    def test_max_supply_value(self):
        """MAX_SUPPLY is correctly defined."""
        assert MAX_SUPPLY == 121_000_000.0

    def test_min_amount_value(self):
        """MIN_AMOUNT is correctly defined."""
        assert MIN_AMOUNT == 0.00000001

    def test_max_fee_value(self):
        """MAX_FEE is correctly defined."""
        assert MAX_FEE == 1000.0

    def test_valid_prefixes(self):
        """VALID_PREFIXES contains expected values."""
        assert "XAI" in VALID_PREFIXES
        assert "TXAI" in VALID_PREFIXES

    def test_special_addresses(self):
        """SPECIAL_ADDRESSES contains expected values."""
        expected = {"COINBASE", "XAITRADEFEE", "TXAITRADEFEE", "GOVERNANCE", "STAKING", "TIMECAPSULE"}
        assert set(SPECIAL_ADDRESSES) == expected
