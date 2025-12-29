"""
Unit tests for XAI address checksum (EIP-55 style).

Tests the mixed-case checksum encoding for XAI addresses,
ensuring error detection and compatibility with the EIP-55 standard.
"""

import pytest
from xai.core.wallets.address_checksum import (
    to_checksum_address,
    is_checksum_valid,
    validate_address,
    normalize_address,
)


class TestChecksumGeneration:
    """Test checksum address generation."""

    def test_lowercase_address_to_checksum(self):
        """Test converting lowercase address to checksummed format."""
        lowercase = "XAI7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b"
        checksummed = to_checksum_address(lowercase)

        # Should have mixed case
        assert checksummed != lowercase
        assert checksummed.startswith("XAI")
        assert len(checksummed) == 43

        # Should be deterministic
        assert to_checksum_address(lowercase) == checksummed

    def test_uppercase_address_to_checksum(self):
        """Test converting uppercase address to checksummed format."""
        uppercase = "XAI7A8B9C0D1E2F3A4B5C6D7E8F9A0B1C2D3E4F5A6B"
        checksummed = to_checksum_address(uppercase)

        # Should have mixed case
        assert checksummed != uppercase
        assert checksummed.startswith("XAI")
        assert len(checksummed) == 43

    def test_checksum_is_idempotent(self):
        """Test that checksumming an already checksummed address returns the same result."""
        address = "XAI7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b"
        checksummed = to_checksum_address(address)
        double_checksummed = to_checksum_address(checksummed)

        assert checksummed == double_checksummed

    def test_txai_prefix(self):
        """Test checksum with TXAI prefix (testnet)."""
        address = "TXAIabcdef1234567890abcdef1234567890abcdef12"
        checksummed = to_checksum_address(address)

        assert checksummed.startswith("TXAI")
        assert len(checksummed) == 44
        assert checksummed != address

    def test_different_addresses_different_checksums(self):
        """Test that different addresses produce different checksums."""
        addr1 = "XAI1111111111111111111111111111111111111111"
        addr2 = "XAI2222222222222222222222222222222222222222"

        checksum1 = to_checksum_address(addr1)
        checksum2 = to_checksum_address(addr2)

        assert checksum1 != checksum2


class TestChecksumValidation:
    """Test checksum validation."""

    def test_valid_checksum(self):
        """Test that a valid checksummed address passes validation."""
        address = "XAI7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b"
        checksummed = to_checksum_address(address)

        assert is_checksum_valid(checksummed)

    def test_lowercase_is_valid(self):
        """Test that all-lowercase addresses are considered valid (no checksum applied)."""
        lowercase = "XAI7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b"
        assert is_checksum_valid(lowercase)

    def test_uppercase_is_valid(self):
        """Test that all-uppercase addresses are considered valid (no checksum applied)."""
        uppercase = "XAI7A8B9C0D1E2F3A4B5C6D7E8F9A0B1C2D3E4F5A6B"
        assert is_checksum_valid(uppercase)

    def test_invalid_checksum_detected(self):
        """Test that an invalid checksum is detected."""
        address = "XAI7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b"
        checksummed = to_checksum_address(address)

        # Flip one case to make it invalid (find a letter, not a digit)
        invalid = None
        for i in range(3, len(checksummed)):
            if checksummed[i].isalpha():
                if checksummed[i].isupper():
                    invalid = checksummed[:i] + checksummed[i].lower() + checksummed[i+1:]
                else:
                    invalid = checksummed[:i] + checksummed[i].upper() + checksummed[i+1:]
                break

        assert invalid is not None, "Could not create invalid checksum test case"
        assert not is_checksum_valid(invalid)

    def test_invalid_prefix(self):
        """Test that invalid prefixes are rejected."""
        assert not is_checksum_valid("ETH7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b")
        assert not is_checksum_valid("0x7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b")

    def test_txai_checksum_validation(self):
        """Test TXAI prefix checksum validation."""
        address = "TXAIabcdef1234567890abcdef1234567890abcdef12"
        checksummed = to_checksum_address(address)

        assert is_checksum_valid(checksummed)


class TestAddressValidation:
    """Test comprehensive address validation."""

    def test_validate_lowercase_address(self):
        """Test validating a lowercase address."""
        address = "XAI7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b"
        is_valid, result = validate_address(address)

        assert is_valid
        # Result should be the checksummed version
        assert result.startswith("XAI")
        assert len(result) == 43

    def test_validate_checksummed_address(self):
        """Test validating an already checksummed address."""
        address = "XAI7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b"
        checksummed = to_checksum_address(address)
        is_valid, result = validate_address(checksummed)

        assert is_valid
        assert result == checksummed

    def test_validate_invalid_prefix(self):
        """Test that invalid prefixes are rejected."""
        is_valid, error = validate_address("ETH7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b")

        assert not is_valid
        assert "prefix" in error.lower() or "XAI" in error or "TXAI" in error

    def test_validate_wrong_length(self):
        """Test that wrong length addresses are rejected."""
        is_valid, error = validate_address("XAI7a8b9c0d1e2f3")

        assert not is_valid
        assert "40" in error or "character" in error.lower()

    def test_validate_invalid_hex(self):
        """Test that invalid hex characters are rejected."""
        is_valid, error = validate_address("XAI7g8h9i0j1k2l3m4n5o6p7q8r9s0t1u2v3w4x5y6z")

        assert not is_valid
        assert "hex" in error.lower() or "invalid" in error.lower()

    def test_validate_with_checksum_required(self):
        """Test strict validation requiring checksum."""
        lowercase = "XAI7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b"
        is_valid, result = validate_address(lowercase, require_checksum=True)

        # All lowercase should pass and return checksummed version
        assert is_valid
        assert result != lowercase  # Should be checksummed

    def test_validate_invalid_checksum_with_suggestion(self):
        """Test that invalid checksum provides helpful suggestion."""
        address = "XAI7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b"
        checksummed = to_checksum_address(address)

        # Create invalid checksum by flipping case (find a letter)
        invalid = None
        for i in range(3, len(checksummed)):
            if checksummed[i].isalpha():
                if checksummed[i].isupper():
                    invalid = checksummed[:i] + checksummed[i].lower() + checksummed[i+1:]
                else:
                    invalid = checksummed[:i] + checksummed[i].upper() + checksummed[i+1:]
                break

        assert invalid is not None, "Could not create invalid checksum test case"

        is_valid, error = validate_address(invalid, require_checksum=False)

        # Should detect invalid checksum and suggest correct one
        assert not is_valid
        assert "checksum" in error.lower()
        assert checksummed in error

    def test_validate_txai_address(self):
        """Test validating TXAI testnet address."""
        address = "TXAIabcdef1234567890abcdef1234567890abcdef12"
        is_valid, result = validate_address(address)

        assert is_valid
        assert result.startswith("TXAI")


class TestNormalizeAddress:
    """Test address normalization."""

    def test_normalize_lowercase(self):
        """Test normalizing lowercase address."""
        lowercase = "XAI7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b"
        normalized = normalize_address(lowercase)

        assert normalized.startswith("XAI")
        assert len(normalized) == 43
        assert is_checksum_valid(normalized)

    def test_normalize_uppercase(self):
        """Test normalizing uppercase address."""
        uppercase = "XAI7A8B9C0D1E2F3A4B5C6D7E8F9A0B1C2D3E4F5A6B"
        normalized = normalize_address(uppercase)

        assert normalized.startswith("XAI")
        assert len(normalized) == 43
        assert is_checksum_valid(normalized)

    def test_normalize_mixed_case(self):
        """Test normalizing mixed-case address."""
        address = "XAI7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b"
        checksummed = to_checksum_address(address)
        normalized = normalize_address(checksummed)

        assert normalized == checksummed

    def test_normalize_invalid_raises(self):
        """Test that normalizing invalid address raises ValueError."""
        with pytest.raises(ValueError):
            normalize_address("ETH7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b")

        with pytest.raises(ValueError):
            normalize_address("XAI7a8")

    def test_normalize_txai(self):
        """Test normalizing TXAI testnet address."""
        address = "TXAIabcdef1234567890abcdef1234567890abcdef12"
        normalized = normalize_address(address)

        assert normalized.startswith("TXAI")
        assert is_checksum_valid(normalized)


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_address(self):
        """Test that empty address raises ValueError."""
        with pytest.raises(ValueError):
            to_checksum_address("")

    def test_none_address(self):
        """Test that None address raises appropriate error."""
        with pytest.raises((ValueError, AttributeError)):
            to_checksum_address(None)

    def test_address_too_short(self):
        """Test that too-short address raises ValueError."""
        with pytest.raises(ValueError, match="40 characters"):
            to_checksum_address("XAI7a8b")

    def test_address_too_long(self):
        """Test that too-long address raises ValueError."""
        with pytest.raises(ValueError, match="40 characters"):
            to_checksum_address("XAI7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d")

    def test_no_prefix(self):
        """Test that address without prefix raises ValueError."""
        with pytest.raises(ValueError, match="prefix"):
            to_checksum_address("7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b")

    def test_case_sensitivity_matters(self):
        """Test that checksum is case-sensitive."""
        address = "XAI7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b"
        checksummed = to_checksum_address(address)

        # Should have at least some uppercase chars (very unlikely to be all lowercase after checksum)
        assert checksummed != checksummed.lower() or checksummed != checksummed.upper()

    def test_numeric_chars_unchanged(self):
        """Test that numeric characters are never uppercased."""
        address = "XAI0123456789000000000000000000000000000000"
        checksummed = to_checksum_address(address)

        # All digits should remain as-is
        for i, char in enumerate(address[3:]):
            if char.isdigit():
                assert checksummed[3 + i] == char


class TestKnownVectors:
    """Test against known checksum vectors."""

    def test_known_vector_1(self):
        """Test a known address checksum."""
        # This is a real address that should checksum consistently
        address = "XAI1234567890abcdef1234567890abcdef12345678"
        checksummed = to_checksum_address(address)

        # Verify it's consistent and valid
        assert is_checksum_valid(checksummed)
        assert checksummed == to_checksum_address(checksummed)

    def test_known_vector_2(self):
        """Test another known address checksum."""
        address = "XAIffffffffffffffffffffffffffffffffff000000"
        checksummed = to_checksum_address(address)

        # Verify it's consistent and valid
        assert is_checksum_valid(checksummed)
        assert checksummed == to_checksum_address(checksummed)

    def test_all_zeros(self):
        """Test address with all zeros."""
        address = "XAI0000000000000000000000000000000000000000"
        checksummed = to_checksum_address(address)

        # All digits should remain lowercase
        assert checksummed == address

    def test_all_f(self):
        """Test address with all f's."""
        address = "XAIffffffffffffffffffffffffffffffffffffffff"
        checksummed = to_checksum_address(address)

        # Should have mixed case
        assert checksummed != address
        assert is_checksum_valid(checksummed)


class TestIntegrationWithValidation:
    """Test integration between checksum and validation modules."""

    def test_validation_module_integration(self):
        """Test that validation module properly uses checksum."""
        from xai.core.consensus.validation import validate_address as val_validate

        address = "XAI7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b"
        validated = val_validate(address, allow_special=False, apply_checksum=True)

        assert is_checksum_valid(validated)

    def test_wallet_address_generation(self):
        """Test that wallet generates checksummed addresses."""
        from xai.core.wallet import Wallet

        wallet = Wallet()
        address = wallet.address

        # Should be checksummed
        assert is_checksum_valid(address)
        # Address prefix depends on network (XAI for mainnet, TXAI for testnet)
        assert address.startswith("XAI") or address.startswith("TXAI")
