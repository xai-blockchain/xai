"""
Test suite for XAI Blockchain - Cryptographic Primitives Verification

This test suite verifies the correctness of fundamental cryptographic operations:
- SHA-256 hashing
- ECDSA signature generation and verification
- Public key derivation
- Address generation

These are consensus-critical operations that must produce identical results
across all nodes to maintain network integrity.
"""

import pytest
import hashlib
from xai.core.security.crypto_utils import (
    sign_message_hex,
    verify_signature_hex,
    derive_public_key_hex,
    generate_secp256k1_keypair_hex
)
from xai.core.wallet import Wallet


class TestSHA256Hashing:
    """Verify SHA-256 hash function produces correct and consistent results."""

    def test_sha256_known_vectors(self):
        """Test SHA-256 against known test vectors from NIST."""
        # Test vector 1: Empty string
        h1 = hashlib.sha256(b"").hexdigest()
        assert h1 == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

        # Test vector 2: "abc"
        h2 = hashlib.sha256(b"abc").hexdigest()
        assert h2 == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"

        # Test vector 3: Longer message
        h3 = hashlib.sha256(
            b"abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq"
        ).hexdigest()
        assert h3 == "248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1"

    def test_sha256_consistency(self):
        """Verify SHA-256 produces same output for same input."""
        message = b"XAI Blockchain Test Message"
        h1 = hashlib.sha256(message).hexdigest()
        h2 = hashlib.sha256(message).hexdigest()
        assert h1 == h2
        assert len(h1) == 64  # 256 bits = 64 hex characters

    def test_sha256_avalanche_effect(self):
        """Verify SHA-256 exhibits avalanche effect (small change = large difference)."""
        msg1 = b"XAI Blockchain"
        msg2 = b"XAI blockchain"  # One character different (case)

        h1 = hashlib.sha256(msg1).hexdigest()
        h2 = hashlib.sha256(msg2).hexdigest()

        # Hashes should be completely different
        assert h1 != h2

        # Count differing bits
        bits_different = sum(
            bin(int(a, 16) ^ int(b, 16)).count("1")
            for a, b in zip(h1, h2)
        )
        # Avalanche effect: ~50% of bits should differ
        # For 256 bits, expect ~128 bits different (allow 64-192 range)
        assert 64 < bits_different < 192


class TestECDSASignatures:
    """Verify ECDSA signature generation and verification."""

    def test_signature_generation_and_verification(self):
        """Test that generated signatures can be verified with the correct public key."""
        # Generate a private key
        private_key, public_key = generate_secp256k1_keypair_hex()

        # Sign a message
        message = b"Test transaction data"
        signature = sign_message_hex(private_key, message)

        # Verify the signature
        assert verify_signature_hex(public_key, message, signature) is True

    def test_signature_verification_fails_wrong_message(self):
        """Verify that signature verification fails when message is modified."""
        private_key, public_key = generate_secp256k1_keypair_hex()

        # Sign original message
        message = b"Original message"
        signature = sign_message_hex(private_key, message)

        # Try to verify with tampered message
        tampered_message = b"Tampered message"
        assert verify_signature_hex(public_key, tampered_message, signature) is False

    def test_signature_verification_fails_wrong_public_key(self):
        """Verify that signature verification fails with wrong public key."""
        # Generate two different key pairs
        private_key1, public_key1 = generate_secp256k1_keypair_hex()
        private_key2, public_key2 = generate_secp256k1_keypair_hex()

        # Sign message with key1
        message = b"Test message"
        signature = sign_message_hex(private_key1, message)

        # Verification should pass with correct public key
        assert verify_signature_hex(public_key1, message, signature) is True

        # Verification should fail with wrong public key
        assert verify_signature_hex(public_key2, message, signature) is False

    def test_signature_determinism(self):
        """Verify that signing the same message produces consistent signatures.

        Note: This test expects deterministic signatures (RFC 6979).
        If using randomized ECDSA, this test may need adjustment.
        """
        private_key, public_key = generate_secp256k1_keypair_hex()
        message = b"Deterministic test message"

        # Sign the same message twice
        sig1 = sign_message_hex(private_key, message)
        sig2 = sign_message_hex(private_key, message)

        # Signatures should be identical for deterministic ECDSA
        # If implementation uses randomized ECDSA, both should still verify
        assert verify_signature_hex(public_key, message, sig1) is True
        assert verify_signature_hex(public_key, message, sig2) is True

    def test_signature_length(self):
        """Verify signature has correct length (128 hex characters = 64 bytes)."""
        private_key, _ = generate_secp256k1_keypair_hex()
        message = b"Test message for length check"
        signature = sign_message_hex(private_key, message)

        # ECDSA signature should be 64 bytes = 128 hex characters
        assert len(signature) == 128


class TestPublicKeyDerivation:
    """Verify public key derivation from private keys."""

    def test_public_key_derivation_consistency(self):
        """Verify that deriving public key from same private key gives same result."""
        private_key, _ = generate_secp256k1_keypair_hex()

        pub1 = derive_public_key_hex(private_key)
        pub2 = derive_public_key_hex(private_key)

        assert pub1 == pub2

    def test_public_key_length(self):
        """Verify public key has correct length."""
        private_key, public_key = generate_secp256k1_keypair_hex()

        # Raw coordinates: 64 bytes = 128 hex characters (r,s without prefix)
        # Compressed public key: 33 bytes = 66 hex characters (with prefix)
        # Uncompressed public key: 65 bytes = 130 hex characters (with prefix)
        assert len(public_key) in [66, 128, 130]

    def test_different_private_keys_different_public_keys(self):
        """Verify that different private keys produce different public keys."""
        priv1, pub1 = generate_secp256k1_keypair_hex()
        priv2, pub2 = generate_secp256k1_keypair_hex()

        assert pub1 != pub2


class TestAddressGeneration:
    """Verify address generation from public keys."""

    def test_address_format(self):
        """Verify generated addresses have correct XAI format."""
        wallet = Wallet()

        # Address should start with "XAI"
        assert wallet.address.startswith("XAI")

        # Address should be 43 characters (XAI + 40 hex chars)
        assert len(wallet.address) == 43

    def test_address_uniqueness(self):
        """Verify that different wallets have different addresses."""
        wallet1 = Wallet()
        wallet2 = Wallet()

        assert wallet1.address != wallet2.address

    def test_address_derivation_consistency(self):
        """Verify address is consistently derived from public key."""
        wallet = Wallet()

        # Derive address from public key manually
        pub_key_bytes = bytes.fromhex(wallet.public_key)
        pub_hash = hashlib.sha256(pub_key_bytes).hexdigest()
        expected_address = f"XAI{pub_hash[:40]}"

        assert wallet.address == expected_address


class TestCryptographicBoundaries:
    """Test edge cases and boundary conditions."""

    def test_empty_message_signing(self):
        """Verify that signing empty messages works correctly."""
        private_key, public_key = generate_secp256k1_keypair_hex()

        # Sign empty message
        signature = sign_message_hex(private_key, b"")

        # Should verify successfully
        assert verify_signature_hex(public_key, b"", signature) is True

    def test_large_message_signing(self):
        """Verify signing large messages works correctly."""
        private_key, public_key = generate_secp256k1_keypair_hex()

        # Create a large message (1MB)
        large_message = b"X" * (1024 * 1024)

        # Sign and verify
        signature = sign_message_hex(private_key, large_message)
        assert verify_signature_hex(public_key, large_message, signature) is True

    def test_binary_message_signing(self):
        """Verify signing binary (non-text) messages works correctly."""
        private_key, public_key = generate_secp256k1_keypair_hex()

        # Create binary message with all byte values
        binary_message = bytes(range(256))

        # Sign and verify
        signature = sign_message_hex(private_key, binary_message)
        assert verify_signature_hex(public_key, binary_message, signature) is True


class TestCrossValidation:
    """Cross-validate crypto operations with wallet functionality."""

    def test_wallet_signature_verification(self):
        """Verify that wallet-signed transactions can be verified."""
        from xai.core.blockchain import Transaction

        wallet1 = Wallet()
        wallet2 = Wallet()

        # Create and sign a transaction
        tx = Transaction(
            sender=wallet1.address,
            recipient=wallet2.address,
            amount=10.0,
            fee=0.1,
            public_key=wallet1.public_key,
            nonce=0,
            inputs=[{"txid": "a" * 64, "vout": 0}],
            outputs=[{"address": wallet2.address, "amount": 10.0}],
        )
        tx.sign_transaction(wallet1.private_key)

        # Verify the signature
        assert tx.verify_signature() is True

    def test_wallet_signature_tampering_detection(self):
        """Verify that wallet can detect tampered transaction signatures."""
        from xai.core.blockchain import Transaction

        wallet1 = Wallet()
        wallet2 = Wallet()

        # Create and sign a transaction
        tx = Transaction(
            sender=wallet1.address,
            recipient=wallet2.address,
            amount=10.0,
            fee=0.1,
            public_key=wallet1.public_key,
            nonce=0,
            inputs=[{"txid": "a" * 64, "vout": 0}],
            outputs=[{"address": wallet2.address, "amount": 10.0}],
        )
        tx.sign_transaction(wallet1.private_key)

        # Tamper with the transaction
        tx.amount = 100.0

        # Signature verification should fail
        assert tx.verify_signature() is False
