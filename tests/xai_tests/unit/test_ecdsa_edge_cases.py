"""
ECDSA edge case tests for signature verification.

Tests edge cases that could lead to security vulnerabilities:
- Malformed signatures (wrong length, invalid format)
- Boundary conditions (zero, max values)
- Key format validation
- Signature malleability checks
"""

import pytest
from xai.core.security.crypto_utils import (
    generate_secp256k1_keypair_hex,
    sign_message_hex,
    verify_signature_hex,
    derive_public_key_hex,
    load_public_key_from_hex,
    load_private_key_from_hex,
    deterministic_keypair_from_seed,
    compressed_public_key_from_private,
)


class TestECDSASignatureEdgeCases:
    """Test ECDSA signature verification edge cases."""

    def test_signature_too_short_rejected(self):
        """Signatures shorter than 64 bytes (128 hex chars) must be rejected."""
        priv, pub = generate_secp256k1_keypair_hex()
        message = b"test message"
        sig = sign_message_hex(priv, message)
        # Truncate signature
        truncated = sig[:120]  # 60 bytes instead of 64
        assert verify_signature_hex(pub, message, truncated) is False

    def test_signature_too_long_rejected(self):
        """Signatures longer than 64 bytes must be rejected."""
        priv, pub = generate_secp256k1_keypair_hex()
        message = b"test message"
        sig = sign_message_hex(priv, message)
        # Extend signature
        extended = sig + "0000"  # 66 bytes
        assert verify_signature_hex(pub, message, extended) is False

    def test_signature_invalid_hex_rejected(self):
        """Non-hex characters in signature must be rejected."""
        priv, pub = generate_secp256k1_keypair_hex()
        message = b"test message"
        # Invalid hex
        invalid_sig = "zz" * 64
        with pytest.raises(ValueError):
            verify_signature_hex(pub, message, invalid_sig)

    def test_empty_signature_rejected(self):
        """Empty signature must be rejected."""
        priv, pub = generate_secp256k1_keypair_hex()
        message = b"test message"
        assert verify_signature_hex(pub, message, "") is False

    def test_all_zeros_signature_rejected(self):
        """All-zeros signature (r=0, s=0) must be rejected."""
        priv, pub = generate_secp256k1_keypair_hex()
        message = b"test message"
        zero_sig = "00" * 64
        assert verify_signature_hex(pub, message, zero_sig) is False

    def test_signature_r_zero_rejected(self):
        """Signature with r=0 must be rejected (invalid point)."""
        priv, pub = generate_secp256k1_keypair_hex()
        message = b"test message"
        sig = sign_message_hex(priv, message)
        # Replace r with zeros (first 32 bytes)
        bad_sig = "00" * 32 + sig[64:]
        assert verify_signature_hex(pub, message, bad_sig) is False

    def test_signature_s_zero_rejected(self):
        """Signature with s=0 must be rejected."""
        priv, pub = generate_secp256k1_keypair_hex()
        message = b"test message"
        sig = sign_message_hex(priv, message)
        # Replace s with zeros (last 32 bytes)
        bad_sig = sig[:64] + "00" * 32
        assert verify_signature_hex(pub, message, bad_sig) is False

    def test_wrong_message_signature_rejected(self):
        """Signature for different message must be rejected."""
        priv, pub = generate_secp256k1_keypair_hex()
        message1 = b"original message"
        message2 = b"different message"
        sig = sign_message_hex(priv, message1)
        assert verify_signature_hex(pub, message2, sig) is False

    def test_wrong_key_signature_rejected(self):
        """Signature verified with wrong public key must be rejected."""
        priv1, pub1 = generate_secp256k1_keypair_hex()
        priv2, pub2 = generate_secp256k1_keypair_hex()
        message = b"test message"
        sig = sign_message_hex(priv1, message)
        assert verify_signature_hex(pub2, message, sig) is False

    def test_flipped_bit_signature_rejected(self):
        """Signature with single bit flipped must be rejected."""
        priv, pub = generate_secp256k1_keypair_hex()
        message = b"test message"
        sig = sign_message_hex(priv, message)
        # Flip a bit in the middle of the signature
        sig_bytes = bytearray(bytes.fromhex(sig))
        sig_bytes[32] ^= 0x01  # Flip bit in middle
        flipped_sig = sig_bytes.hex()
        assert verify_signature_hex(pub, message, flipped_sig) is False

    def test_empty_message_signature_valid(self):
        """Signing and verifying empty message should work."""
        priv, pub = generate_secp256k1_keypair_hex()
        message = b""
        sig = sign_message_hex(priv, message)
        assert verify_signature_hex(pub, message, sig) is True

    def test_large_message_signature_valid(self):
        """Signing and verifying large messages should work."""
        priv, pub = generate_secp256k1_keypair_hex()
        message = b"x" * 1_000_000  # 1MB message
        sig = sign_message_hex(priv, message)
        assert verify_signature_hex(pub, message, sig) is True


class TestECDSAKeyEdgeCases:
    """Test ECDSA key handling edge cases."""

    def test_public_key_too_short_rejected(self):
        """Public key shorter than 64 bytes must be rejected."""
        short_key = "00" * 32  # Only 32 bytes
        with pytest.raises(ValueError, match="64 bytes"):
            load_public_key_from_hex(short_key)

    def test_public_key_too_long_rejected(self):
        """Public key longer than 64 bytes must be rejected."""
        long_key = "00" * 128  # 128 bytes
        with pytest.raises(ValueError, match="64 bytes"):
            load_public_key_from_hex(long_key)

    def test_public_key_invalid_point_rejected(self):
        """Public key not on curve must be rejected."""
        # All zeros is not a valid point on secp256k1
        invalid_key = "00" * 64
        with pytest.raises(Exception):  # May raise various crypto errors
            load_public_key_from_hex(invalid_key)

    def test_private_key_zero_normalized(self):
        """Private key of 0 should be normalized to 1."""
        zero_key = "00" * 32
        private_key = load_private_key_from_hex(zero_key)
        # Should not crash; value is normalized to 1
        assert private_key.private_numbers().private_value == 1

    def test_private_key_exceeds_curve_order_normalized(self):
        """Private key exceeding curve order should be normalized."""
        # secp256k1 curve order: FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
        # Use a value slightly higher
        big_key = "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
        private_key = load_private_key_from_hex(big_key)
        # Should be normalized to value within curve order
        assert private_key.private_numbers().private_value < int(
            "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141", 16
        )

    def test_deterministic_keypair_short_seed_padded(self):
        """Short seeds should be zero-padded to 32 bytes."""
        short_seed = b"short"
        priv1, pub1 = deterministic_keypair_from_seed(short_seed)
        # Same short seed padded should give same result
        padded_seed = short_seed.ljust(32, b"\x00")
        priv2, pub2 = deterministic_keypair_from_seed(padded_seed)
        assert priv1 == priv2
        assert pub1 == pub2

    def test_deterministic_keypair_reproducible(self):
        """Same seed must always produce same keypair."""
        seed = b"reproducibility-test-seed-32byte"
        results = [deterministic_keypair_from_seed(seed) for _ in range(10)]
        assert all(r == results[0] for r in results)

    def test_compressed_public_key_format(self):
        """Compressed public key should be 33 bytes (66 hex chars)."""
        priv, pub = generate_secp256k1_keypair_hex()
        compressed = compressed_public_key_from_private(priv)
        assert len(compressed) == 66  # 33 bytes
        # First byte should be 02 or 03 (compressed format)
        assert compressed[:2] in ("02", "03")

    def test_derived_public_key_matches(self):
        """derive_public_key_hex should match keypair generation."""
        priv, pub = generate_secp256k1_keypair_hex()
        derived = derive_public_key_hex(priv)
        assert derived == pub


class TestECDSASignatureMalleability:
    """Test signature malleability resistance.

    In ECDSA, (r, s) and (r, n-s) are both valid signatures for the same
    message. Implementations should normalize to low-S to prevent
    transaction malleability attacks.
    """

    def test_high_s_signature_verification(self):
        """High-S signatures should be rejected to prevent malleability."""
        priv, pub = generate_secp256k1_keypair_hex()
        message = b"malleability test"
        sig = sign_message_hex(priv, message)

        # Get r and s values
        r = int(sig[:64], 16)
        s = int(sig[64:], 16)
        curve_order = int(
            "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141", 16
        )

        # Create high-S version: s' = n - s
        high_s = curve_order - s
        high_s_sig = sig[:64] + high_s.to_bytes(32, "big").hex()

        # Only low-S signature should verify
        assert verify_signature_hex(pub, message, sig) is True
        assert verify_signature_hex(pub, message, high_s_sig) is False

    def test_signature_different_for_different_messages(self):
        """Same key signing different messages produces different signatures."""
        priv, pub = generate_secp256k1_keypair_hex()
        sig1 = sign_message_hex(priv, b"message 1")
        sig2 = sign_message_hex(priv, b"message 2")
        assert sig1 != sig2


class TestECDSAWithTransaction:
    """Test ECDSA with transaction-like messages."""

    def test_sign_verify_json_transaction(self):
        """Sign and verify JSON transaction payload."""
        import json

        priv, pub = generate_secp256k1_keypair_hex()
        tx = {
            "sender": "XAI123",
            "recipient": "XAI456",
            "amount": 100.0,
            "fee": 0.1,
            "nonce": 42,
        }
        message = json.dumps(tx, sort_keys=True).encode()
        sig = sign_message_hex(priv, message)
        assert verify_signature_hex(pub, message, sig) is True

    def test_sign_verify_hash_message(self):
        """Sign and verify a hash value (common pattern)."""
        import hashlib

        priv, pub = generate_secp256k1_keypair_hex()
        data = b"some transaction data"
        hash_msg = hashlib.sha256(data).hexdigest().encode()
        sig = sign_message_hex(priv, hash_msg)
        assert verify_signature_hex(pub, hash_msg, sig) is True
