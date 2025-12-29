"""
Test cryptographic utilities for secp256k1 key management and signatures.

Tests cover:
- Key generation and derivation
- Public key extraction
- Signing and verification
- Canonical signature handling
- Edge cases and security-relevant scenarios
"""

from __future__ import annotations

import secrets

import pytest

from xai.core.security.crypto_utils import (
    _CURVE_ORDER,
    _normalize_private_value,
    _private_key_to_hex,
    _public_key_to_hex,
    canonicalize_signature_components,
    compressed_public_key_from_private,
    derive_public_key_hex,
    deterministic_keypair_from_seed,
    generate_secp256k1_keypair_hex,
    is_canonical_signature,
    load_private_key_from_hex,
    load_public_key_from_hex,
    sign_message_hex,
    verify_signature_hex,
)


class TestKeyGeneration:
    """Tests for key generation functions."""

    def test_generate_keypair_returns_valid_hex(self):
        """Generated keypair should be valid hex strings of correct length."""
        private_hex, public_hex = generate_secp256k1_keypair_hex()

        assert len(private_hex) == 64, "Private key should be 64 hex characters (32 bytes)"
        assert len(public_hex) == 128, "Public key should be 128 hex characters (64 bytes)"

        # Should be valid hex
        bytes.fromhex(private_hex)
        bytes.fromhex(public_hex)

    def test_generate_keypair_uniqueness(self):
        """Each call should generate unique keys."""
        keypairs = [generate_secp256k1_keypair_hex() for _ in range(10)]
        private_keys = [kp[0] for kp in keypairs]
        public_keys = [kp[1] for kp in keypairs]

        assert len(set(private_keys)) == 10, "Private keys should be unique"
        assert len(set(public_keys)) == 10, "Public keys should be unique"

    def test_deterministic_keypair_from_seed(self):
        """Same seed should produce same keypair."""
        seed = b"test_seed_for_deterministic_key_"
        private1, public1 = deterministic_keypair_from_seed(seed)
        private2, public2 = deterministic_keypair_from_seed(seed)

        assert private1 == private2, "Same seed should produce same private key"
        assert public1 == public2, "Same seed should produce same public key"

    def test_deterministic_keypair_different_seeds(self):
        """Different seeds should produce different keypairs."""
        seed1 = b"seed_one_for_testing____________"
        seed2 = b"seed_two_for_testing____________"

        private1, public1 = deterministic_keypair_from_seed(seed1)
        private2, public2 = deterministic_keypair_from_seed(seed2)

        assert private1 != private2, "Different seeds should produce different private keys"
        assert public1 != public2, "Different seeds should produce different public keys"

    def test_deterministic_keypair_short_seed_padded(self):
        """Short seeds should be padded and work correctly."""
        short_seed = b"short"
        private_hex, public_hex = deterministic_keypair_from_seed(short_seed)

        assert len(private_hex) == 64
        assert len(public_hex) == 128

        # Same short seed should still be deterministic
        private2, public2 = deterministic_keypair_from_seed(short_seed)
        assert private_hex == private2
        assert public_hex == public2


class TestKeyLoading:
    """Tests for loading keys from hex strings."""

    def test_load_private_key_roundtrip(self):
        """Loading a private key and extracting hex should match original."""
        private_hex, _ = generate_secp256k1_keypair_hex()
        private_key = load_private_key_from_hex(private_hex)
        recovered_hex = _private_key_to_hex(private_key)

        assert private_hex == recovered_hex

    def test_load_public_key_roundtrip(self):
        """Loading a public key and extracting hex should match original."""
        _, public_hex = generate_secp256k1_keypair_hex()
        public_key = load_public_key_from_hex(public_hex)
        recovered_hex = _public_key_to_hex(public_key)

        assert public_hex == recovered_hex

    def test_load_public_key_invalid_length(self):
        """Loading public key with wrong length should raise ValueError."""
        short_hex = "abcd" * 10  # 40 chars instead of 128

        with pytest.raises(ValueError, match="64 bytes"):
            load_public_key_from_hex(short_hex)

    def test_load_public_key_invalid_hex(self):
        """Loading public key with invalid hex should raise ValueError."""
        invalid_hex = "zzzz" * 32

        with pytest.raises(ValueError):
            load_public_key_from_hex(invalid_hex)

    def test_derive_public_key_from_private(self):
        """Derived public key should match original."""
        private_hex, expected_public = generate_secp256k1_keypair_hex()
        derived_public = derive_public_key_hex(private_hex)

        assert derived_public == expected_public


class TestPrivateKeyNormalization:
    """Tests for private key value normalization."""

    def test_normalize_zero_becomes_one(self):
        """Zero private value should normalize to 1 (not valid for EC)."""
        normalized = _normalize_private_value(0)
        assert normalized == 1

    def test_normalize_value_within_range(self):
        """Values within curve order should remain unchanged."""
        test_value = 12345678901234567890
        normalized = _normalize_private_value(test_value)
        assert normalized == test_value

    def test_normalize_value_at_curve_order(self):
        """Value at curve order should normalize to 1 (order mod order = 0 -> 1)."""
        normalized = _normalize_private_value(_CURVE_ORDER)
        assert normalized == 1

    def test_normalize_value_above_curve_order(self):
        """Values above curve order should be reduced modulo order."""
        above_order = _CURVE_ORDER + 100
        normalized = _normalize_private_value(above_order)
        assert normalized == 100


class TestSignatureOperations:
    """Tests for signing and verification."""

    def test_sign_and_verify_simple_message(self):
        """Signing and verifying a simple message should work."""
        private_hex, public_hex = generate_secp256k1_keypair_hex()
        message = b"Hello, blockchain!"

        signature = sign_message_hex(private_hex, message)
        assert len(signature) == 128, "Signature should be 128 hex chars (64 bytes)"

        is_valid = verify_signature_hex(public_hex, message, signature)
        assert is_valid is True

    def test_verify_fails_with_wrong_message(self):
        """Verification should fail with modified message."""
        private_hex, public_hex = generate_secp256k1_keypair_hex()
        message = b"Original message"
        wrong_message = b"Modified message"

        signature = sign_message_hex(private_hex, message)
        is_valid = verify_signature_hex(public_hex, wrong_message, signature)

        assert is_valid is False

    def test_verify_fails_with_wrong_public_key(self):
        """Verification should fail with wrong public key."""
        private1, public1 = generate_secp256k1_keypair_hex()
        _, public2 = generate_secp256k1_keypair_hex()
        message = b"Test message"

        signature = sign_message_hex(private1, message)
        is_valid = verify_signature_hex(public2, message, signature)

        assert is_valid is False

    def test_verify_fails_with_tampered_signature(self):
        """Verification should fail with tampered signature."""
        private_hex, public_hex = generate_secp256k1_keypair_hex()
        message = b"Secure message"

        signature = sign_message_hex(private_hex, message)

        # Tamper with the signature (flip a bit)
        sig_bytes = bytes.fromhex(signature)
        tampered_bytes = bytes([sig_bytes[0] ^ 0x01]) + sig_bytes[1:]
        tampered_sig = tampered_bytes.hex()

        is_valid = verify_signature_hex(public_hex, message, tampered_sig)
        assert is_valid is False

    def test_verify_empty_message(self):
        """Should be able to sign and verify empty message."""
        private_hex, public_hex = generate_secp256k1_keypair_hex()
        message = b""

        signature = sign_message_hex(private_hex, message)
        is_valid = verify_signature_hex(public_hex, message, signature)

        assert is_valid is True

    def test_verify_large_message(self):
        """Should handle large messages (internally hashed)."""
        private_hex, public_hex = generate_secp256k1_keypair_hex()
        message = secrets.token_bytes(10000)  # 10KB random data

        signature = sign_message_hex(private_hex, message)
        is_valid = verify_signature_hex(public_hex, message, signature)

        assert is_valid is True

    def test_verify_invalid_signature_length(self):
        """Verification should return False for wrong signature length."""
        _, public_hex = generate_secp256k1_keypair_hex()
        message = b"test"
        short_signature = "abcd" * 16  # 64 chars instead of 128

        is_valid = verify_signature_hex(public_hex, message, short_signature)
        assert is_valid is False

    def test_verify_invalid_hex_signature_raises(self):
        """Verification with invalid hex raises ValueError."""
        _, public_hex = generate_secp256k1_keypair_hex()
        message = b"test"
        invalid_signature = "zz" * 64

        # Invalid hex raises ValueError (bytes.fromhex() fails)
        with pytest.raises(ValueError):
            verify_signature_hex(public_hex, message, invalid_signature)


class TestCanonicalSignatures:
    """Tests for canonical (low-S) signature handling."""

    def test_signature_is_canonicalized(self):
        """Signatures produced by sign_message_hex should be canonical."""
        private_hex, public_hex = generate_secp256k1_keypair_hex()

        # Generate multiple signatures to test canonicalization
        for i in range(10):
            message = f"Test message {i}".encode()
            signature = sign_message_hex(private_hex, message)

            # Extract r and s
            sig_bytes = bytes.fromhex(signature)
            r = int.from_bytes(sig_bytes[:32], "big")
            s = int.from_bytes(sig_bytes[32:], "big")

            assert is_canonical_signature(r, s), f"Signature {i} should be canonical"

    def test_is_canonical_signature_valid_range(self):
        """is_canonical_signature should return True for valid low-S signatures."""
        r = _CURVE_ORDER // 4  # Valid r
        s = _CURVE_ORDER // 4  # Low S (less than order/2)

        assert is_canonical_signature(r, s) is True

    def test_is_canonical_signature_high_s(self):
        """is_canonical_signature should return False for high-S signatures."""
        r = _CURVE_ORDER // 4
        s = _CURVE_ORDER - 100  # High S (greater than order/2)

        assert is_canonical_signature(r, s) is False

    def test_is_canonical_signature_out_of_range(self):
        """is_canonical_signature should return False for out-of-range values."""
        # r = 0 is invalid
        assert is_canonical_signature(0, _CURVE_ORDER // 4) is False

        # s = 0 is invalid
        assert is_canonical_signature(_CURVE_ORDER // 4, 0) is False

        # r >= order is invalid
        assert is_canonical_signature(_CURVE_ORDER, _CURVE_ORDER // 4) is False

    def test_canonicalize_high_s_signature(self):
        """canonicalize_signature_components should convert high-S to low-S."""
        r = _CURVE_ORDER // 4
        high_s = _CURVE_ORDER - 100  # High S

        canon_r, canon_s = canonicalize_signature_components(r, high_s)

        assert canon_r == r, "R should remain unchanged"
        assert canon_s == 100, "S should be converted to low-S"
        assert is_canonical_signature(canon_r, canon_s) is True

    def test_canonicalize_already_canonical(self):
        """canonicalize_signature_components should not modify already canonical signatures."""
        r = _CURVE_ORDER // 4
        low_s = 100

        canon_r, canon_s = canonicalize_signature_components(r, low_s)

        assert canon_r == r
        assert canon_s == low_s

    def test_canonicalize_invalid_r_raises(self):
        """canonicalize_signature_components should raise for invalid r."""
        with pytest.raises(ValueError, match="r component out of range"):
            canonicalize_signature_components(0, _CURVE_ORDER // 4)

        with pytest.raises(ValueError, match="r component out of range"):
            canonicalize_signature_components(_CURVE_ORDER, _CURVE_ORDER // 4)

    def test_canonicalize_invalid_s_raises(self):
        """canonicalize_signature_components should raise for invalid s."""
        with pytest.raises(ValueError, match="s component out of range"):
            canonicalize_signature_components(_CURVE_ORDER // 4, 0)

        with pytest.raises(ValueError, match="s component out of range"):
            canonicalize_signature_components(_CURVE_ORDER // 4, _CURVE_ORDER)

    def test_verify_rejects_non_canonical_signature(self):
        """verify_signature_hex should reject non-canonical signatures."""
        private_hex, public_hex = generate_secp256k1_keypair_hex()
        message = b"Test"

        # Get a valid signature first
        signature = sign_message_hex(private_hex, message)
        sig_bytes = bytes.fromhex(signature)
        r = int.from_bytes(sig_bytes[:32], "big")
        s = int.from_bytes(sig_bytes[32:], "big")

        # Create high-S version (non-canonical)
        high_s = _CURVE_ORDER - s
        high_s_sig = (r.to_bytes(32, "big") + high_s.to_bytes(32, "big")).hex()

        # Should reject non-canonical
        assert verify_signature_hex(public_hex, message, high_s_sig) is False


class TestCompressedPublicKey:
    """Tests for compressed public key generation."""

    def test_compressed_public_key_length(self):
        """Compressed public key should be 33 bytes (66 hex chars)."""
        private_hex, _ = generate_secp256k1_keypair_hex()
        compressed = compressed_public_key_from_private(private_hex)

        assert len(compressed) == 66, "Compressed key should be 66 hex chars"

    def test_compressed_public_key_prefix(self):
        """Compressed public key should start with 02 or 03."""
        private_hex, _ = generate_secp256k1_keypair_hex()
        compressed = compressed_public_key_from_private(private_hex)

        assert compressed[:2] in ("02", "03"), "Should have valid compression prefix"

    def test_compressed_key_deterministic(self):
        """Same private key should produce same compressed public key."""
        private_hex, _ = generate_secp256k1_keypair_hex()

        compressed1 = compressed_public_key_from_private(private_hex)
        compressed2 = compressed_public_key_from_private(private_hex)

        assert compressed1 == compressed2


class TestSecurityCases:
    """Security-focused test cases."""

    def test_signature_malleability_protection(self):
        """Verification should reject malleable (high-S) signatures."""
        private_hex, public_hex = generate_secp256k1_keypair_hex()
        message = b"Security test"

        signature = sign_message_hex(private_hex, message)
        sig_bytes = bytes.fromhex(signature)
        r = int.from_bytes(sig_bytes[:32], "big")
        s = int.from_bytes(sig_bytes[32:], "big")

        # Create malleable signature
        malleable_s = _CURVE_ORDER - s
        malleable_sig = (r.to_bytes(32, "big") + malleable_s.to_bytes(32, "big")).hex()

        # Original should verify
        assert verify_signature_hex(public_hex, message, signature) is True

        # Malleable should NOT verify (protects against transaction malleability)
        assert verify_signature_hex(public_hex, message, malleable_sig) is False

    def test_different_messages_different_signatures(self):
        """Different messages should produce different signatures."""
        private_hex, _ = generate_secp256k1_keypair_hex()

        sig1 = sign_message_hex(private_hex, b"Message 1")
        sig2 = sign_message_hex(private_hex, b"Message 2")

        assert sig1 != sig2

    def test_weak_private_key_normalized(self):
        """Very small private keys should still work after normalization."""
        # Use a small value that's still valid
        small_key = "0000000000000000000000000000000000000000000000000000000000000001"
        public_hex = derive_public_key_hex(small_key)

        # Should produce valid public key
        assert len(public_hex) == 128

        # Should be able to sign and verify
        message = b"test"
        signature = sign_message_hex(small_key, message)
        assert verify_signature_hex(public_hex, message, signature) is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
