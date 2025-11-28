"""
Unit tests for XAI Wallet functionality

Tests wallet creation, key generation, signing, and file operations
"""

import pytest
import sys
import os
import json
import tempfile
from pathlib import Path

# Add core directory to path

from xai.core.wallet import Wallet


class TestWalletCreation:
    """Test wallet creation and initialization"""

    def test_create_new_wallet(self):
        """Test creating a new wallet generates keys"""
        wallet = Wallet()

        assert wallet.private_key is not None
        assert wallet.public_key is not None
        assert wallet.address is not None

    def test_private_key_length(self):
        """Test private key has correct length"""
        wallet = Wallet()

        # ECDSA SECP256k1 private key is 32 bytes = 64 hex chars
        assert len(wallet.private_key) == 64

    def test_public_key_length(self):
        """Test public key has correct length"""
        wallet = Wallet()

        # ECDSA SECP256k1 public key is 64 bytes = 128 hex chars
        assert len(wallet.public_key) == 128

    def test_address_format(self):
        """Test address has correct XAI format"""
        wallet = Wallet()

        assert wallet.address.startswith("XAI")
        assert len(wallet.address) == 43  # XAI + 40 chars

    def test_unique_wallets(self):
        """Test each wallet is unique"""
        wallet1 = Wallet()
        wallet2 = Wallet()

        assert wallet1.private_key != wallet2.private_key
        assert wallet1.public_key != wallet2.public_key
        assert wallet1.address != wallet2.address


class TestWalletLoading:
    """Test loading wallet from existing private key"""

    def test_load_from_private_key(self):
        """Test loading wallet from existing private key"""
        # Create wallet and save keys
        wallet1 = Wallet()
        private_key = wallet1.private_key

        # Load wallet from same private key
        wallet2 = Wallet(private_key=private_key)

        assert wallet2.private_key == wallet1.private_key
        assert wallet2.public_key == wallet1.public_key
        assert wallet2.address == wallet1.address

    def test_derive_public_key(self):
        """Test public key derivation from private key"""
        wallet1 = Wallet()
        private_key = wallet1.private_key

        wallet2 = Wallet(private_key=private_key)

        # Public key should be derived correctly
        assert wallet2.public_key == wallet1.public_key

    def test_derive_address(self):
        """Test address derivation from public key"""
        wallet1 = Wallet()
        private_key = wallet1.private_key

        wallet2 = Wallet(private_key=private_key)

        # Address should be same
        assert wallet2.address == wallet1.address


class TestMessageSigning:
    """Test message signing and verification"""

    def test_sign_message(self):
        """Test signing a message"""
        wallet = Wallet()
        message = "Hello, XAI Blockchain!"

        signature = wallet.sign_message(message)

        assert signature is not None
        assert len(signature) > 0

    def test_verify_valid_signature(self):
        """Test verification of valid signature"""
        wallet = Wallet()
        message = "Test message"

        signature = wallet.sign_message(message)
        is_valid = wallet.verify_signature(message, signature, wallet.public_key)

        assert is_valid

    def test_reject_invalid_signature(self):
        """Test rejection of invalid signature"""
        wallet = Wallet()
        message = "Test message"

        signature = wallet.sign_message(message)

        # Try to verify with wrong message
        is_valid = wallet.verify_signature("Wrong message", signature, wallet.public_key)

        assert not is_valid

    def test_reject_wrong_signer(self):
        """Test rejection of signature from wrong wallet"""
        wallet1 = Wallet()
        wallet2 = Wallet()
        message = "Test message"

        signature = wallet1.sign_message(message)

        # Try to verify with wallet2's public key
        is_valid = wallet2.verify_signature(message, signature, wallet2.public_key)

        assert not is_valid

    def test_signature_uniqueness(self):
        """Test different messages produce different signatures"""
        wallet = Wallet()

        sig1 = wallet.sign_message("Message 1")
        sig2 = wallet.sign_message("Message 2")

        assert sig1 != sig2


class TestWalletFileOperations:
    """Test saving and loading wallet files"""

    def test_save_wallet_unencrypted(self):
        """Test saving wallet to file without encryption"""
        wallet = Wallet()

        with tempfile.TemporaryDirectory() as tmpdir:
            filename = os.path.join(tmpdir, "test_wallet.json")
            wallet.save_to_file(filename)

            assert os.path.exists(filename)

            # Verify file contents
            with open(filename, "r") as f:
                data = json.load(f)

            assert data["private_key"] == wallet.private_key
            assert data["public_key"] == wallet.public_key
            assert data["address"] == wallet.address

    def test_load_wallet_from_file(self):
        """Test loading wallet from saved file"""
        wallet1 = Wallet()

        with tempfile.TemporaryDirectory() as tmpdir:
            filename = os.path.join(tmpdir, "test_wallet.json")
            wallet1.save_to_file(filename)

            # Load wallet from file
            with open(filename, "r") as f:
                data = json.load(f)

            wallet2 = Wallet(private_key=data["private_key"])

            assert wallet2.private_key == wallet1.private_key
            assert wallet2.address == wallet1.address

    def test_save_wallet_encrypted(self):
        """Test saving wallet with password encryption"""
        wallet = Wallet()
        password = "SecurePassword123"

        with tempfile.TemporaryDirectory() as tmpdir:
            filename = os.path.join(tmpdir, "encrypted_wallet.json")
            wallet.save_to_file(filename, password=password)

            assert os.path.exists(filename)

            # Verify file contains encrypted payload
            with open(filename, "r", encoding="utf-8") as f:
                data = json.load(f)

            assert data.get("encrypted") is True
            payload = data.get("payload") or data.get("data")
            assert payload and isinstance(payload, dict)
            assert payload.get("ciphertext")
            assert payload.get("nonce")
            assert payload.get("salt")


class TestAddressGeneration:
    """Test XAI address generation"""

    def test_address_from_public_key(self):
        """Test address is consistently generated from public key"""
        wallet = Wallet()

        # Generate address again
        address2 = wallet._generate_address(wallet.public_key)

        assert address2 == wallet.address

    def test_address_prefix(self):
        """Test all addresses start with XAI"""
        for _ in range(10):
            wallet = Wallet()
            assert wallet.address.startswith("XAI")

    def test_address_hex_characters(self):
        """Test address contains valid hex characters"""
        wallet = Wallet()

        # Remove XAI prefix
        address_hex = wallet.address[3:]

        # Should be valid hex
        assert all(c in "0123456789abcdef" for c in address_hex)


class TestKeyPairGeneration:
    """Test ECDSA key pair generation"""

    def test_generate_keypair(self):
        """Test keypair generation"""
        wallet = Wallet()

        private_key, public_key = wallet._generate_keypair()

        assert len(private_key) == 64  # 32 bytes hex
        assert len(public_key) == 128  # 64 bytes hex

    def test_keypair_validity(self):
        """Test generated keypair is valid"""
        wallet = Wallet()

        # Should be able to sign and verify
        message = "Test"
        signature = wallet.sign_message(message)
        is_valid = wallet.verify_signature(message, signature, wallet.public_key)

        assert is_valid

    def test_public_key_from_private(self):
        """Test public key can be derived from private"""
        wallet1 = Wallet()

        # Derive public key from private
        public_key = wallet1._derive_public_key(wallet1.private_key)

        assert public_key == wallet1.public_key


class TestEncryptionDecryption:
    """Test wallet encryption/decryption"""

    def test_encrypt_data(self):
        """Test data encryption"""
        wallet = Wallet()
        data = "Sensitive data"
        password = "StrongPassword"

        payload = wallet._encrypt_payload(data, password)

        assert isinstance(payload, dict)
        assert {"ciphertext", "nonce", "salt"}.issubset(set(payload.keys()))
        assert payload["ciphertext"]

    def test_decrypt_data(self):
        """Test data decryption"""
        wallet = Wallet()
        data = "Sensitive data"
        password = "StrongPassword"

        payload = wallet._encrypt_payload(data, password)
        decrypted = wallet._decrypt_payload(payload, password)

        assert decrypted == data

    def test_wrong_password_decryption(self):
        """Test decryption with wrong password fails"""
        wallet = Wallet()
        data = "Sensitive data"
        password1 = "Password1"
        password2 = "Password2"

        payload = wallet._encrypt_payload(data, password1)

        with pytest.raises(Exception):
            wallet._decrypt_payload(payload, password2)

    def test_encryption_consistency(self):
        """Test encryption produces consistent output"""
        wallet = Wallet()
        data = "Test data"
        password = "Password"

        payload1 = wallet._encrypt_payload(data, password)
        payload2 = wallet._encrypt_payload(data, password)

        assert payload1 != payload2


class TestWalletSecurity:
    """Test wallet security features"""

    def test_private_key_randomness(self):
        """Test private keys are sufficiently random"""
        keys = set()

        for _ in range(100):
            wallet = Wallet()
            keys.add(wallet.private_key)

        # All keys should be unique
        assert len(keys) == 100

    def test_address_collision_resistance(self):
        """Test address collision resistance"""
        addresses = set()

        for _ in range(100):
            wallet = Wallet()
            addresses.add(wallet.address)

        # All addresses should be unique
        assert len(addresses) == 100

    def test_signature_non_malleability(self):
        """Test signatures cannot be easily manipulated"""
        wallet = Wallet()
        message = "Important transaction"

        sig1 = wallet.sign_message(message)

        # Slightly modify signature
        modified_sig = sig1[:-2] + "00"

        # Modified signature should not verify
        is_valid = wallet.verify_signature(message, modified_sig, wallet.public_key)

        assert not is_valid


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
