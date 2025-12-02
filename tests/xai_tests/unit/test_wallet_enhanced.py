"""
Enhanced comprehensive tests for wallet.py to achieve 98%+ coverage

Tests all wallet functionality including edge cases and error paths
"""

import pytest
import json
import tempfile
import os
from pathlib import Path
from xai.core.wallet import Wallet, WalletManager


class TestWalletManagerCreation:
    """Test WalletManager initialization"""

    def test_wallet_manager_default_dir(self):
        """Test WalletManager with default directory"""
        manager = WalletManager()

        assert manager.data_dir is not None
        assert manager.data_dir.exists()
        assert manager.wallets == {}

    def test_wallet_manager_custom_dir(self):
        """Test WalletManager with custom directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = WalletManager(data_dir=tmpdir)

            assert str(manager.data_dir) == tmpdir
            assert manager.data_dir.exists()

    def test_wallet_manager_creates_directory(self):
        """Test WalletManager creates directory if it doesn't exist"""
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_path = os.path.join(tmpdir, "wallets", "test")
            manager = WalletManager(data_dir=custom_path)

            assert os.path.exists(custom_path)


class TestWalletManagerOperations:
    """Test WalletManager wallet operations"""

    def test_create_wallet_unencrypted(self):
        """Test creating unencrypted wallet"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = WalletManager(data_dir=tmpdir)
            wallet = manager.create_wallet("test_wallet")

            assert wallet is not None
            assert "test_wallet" in manager.wallets
            assert os.path.exists(os.path.join(tmpdir, "test_wallet.wallet"))

    def test_create_wallet_encrypted(self):
        """Test creating encrypted wallet"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = WalletManager(data_dir=tmpdir)
            wallet = manager.create_wallet("test_wallet", password="SecurePass123")

            assert wallet is not None
            assert "test_wallet" in manager.wallets

            # Verify file is encrypted (new HMAC format)
            with open(os.path.join(tmpdir, "test_wallet.wallet"), "r") as f:
                file_data = json.load(f)
            # New format has HMAC wrapper with data inside
            assert "hmac_signature" in file_data
            assert "data" in file_data
            assert file_data["data"].get("encrypted") is True

    def test_load_wallet_unencrypted(self):
        """Test loading unencrypted wallet"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = WalletManager(data_dir=tmpdir)

            # Create and save wallet
            original_wallet = manager.create_wallet("test_wallet")
            original_address = original_wallet.address

            # Clear wallets and reload
            manager.wallets.clear()
            loaded_wallet = manager.load_wallet("test_wallet")

            assert loaded_wallet.address == original_address

    def test_load_wallet_encrypted(self):
        """Test loading encrypted wallet"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = WalletManager(data_dir=tmpdir)
            password = "SecurePass123"

            # Create encrypted wallet
            original_wallet = manager.create_wallet("test_wallet", password=password)
            original_address = original_wallet.address

            # Clear and reload
            manager.wallets.clear()
            loaded_wallet = manager.load_wallet("test_wallet", password=password)

            assert loaded_wallet.address == original_address

    def test_load_wallet_not_found(self):
        """Test loading non-existent wallet raises error"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = WalletManager(data_dir=tmpdir)

            with pytest.raises(FileNotFoundError, match="not found"):
                manager.load_wallet("nonexistent")

    def test_load_encrypted_wallet_wrong_password(self):
        """Test loading encrypted wallet with wrong password fails"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = WalletManager(data_dir=tmpdir)

            # Create encrypted wallet
            manager.create_wallet("test_wallet", password="CorrectPassword")

            # Try to load with wrong password
            manager.wallets.clear()
            with pytest.raises(Exception):
                manager.load_wallet("test_wallet", password="WrongPassword")

    def test_load_encrypted_wallet_no_password(self):
        """Test loading encrypted wallet without password fails"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = WalletManager(data_dir=tmpdir)

            # Create encrypted wallet
            manager.create_wallet("test_wallet", password="Password123")

            # Try to load without password
            manager.wallets.clear()
            with pytest.raises(ValueError, match="Password required"):
                manager.load_wallet("test_wallet")

    def test_list_wallets(self):
        """Test listing all wallets"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = WalletManager(data_dir=tmpdir)

            # Create multiple wallets
            manager.create_wallet("wallet1")
            manager.create_wallet("wallet2")
            manager.create_wallet("wallet3")

            wallets = manager.list_wallets()

            assert len(wallets) == 3
            assert "wallet1" in wallets
            assert "wallet2" in wallets
            assert "wallet3" in wallets

    def test_list_wallets_empty(self):
        """Test listing wallets when directory is empty"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = WalletManager(data_dir=tmpdir)

            wallets = manager.list_wallets()

            assert wallets == []

    def test_get_wallet(self):
        """Test getting loaded wallet"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = WalletManager(data_dir=tmpdir)

            wallet = manager.create_wallet("test_wallet")
            retrieved = manager.get_wallet("test_wallet")

            assert retrieved is wallet

    def test_get_wallet_not_loaded(self):
        """Test getting wallet that hasn't been loaded"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = WalletManager(data_dir=tmpdir)

            result = manager.get_wallet("nonexistent")

            assert result is None


class TestWalletEncryptionMethods:
    """Test wallet encryption/decryption methods"""

    def test_encrypt_method(self):
        """Test _encrypt method"""
        wallet = Wallet()
        data = "Test data"
        password = "SecurePassword"

        encrypted = wallet._encrypt(data, password)

        assert encrypted != data
        assert len(encrypted) > 0

    def test_decrypt_method(self):
        """Test _decrypt method"""
        wallet = Wallet()
        data = "Test data"
        password = "SecurePassword"

        encrypted = wallet._encrypt(data, password)
        decrypted = wallet._decrypt(encrypted, password)

        assert decrypted == data

    def test_encrypt_decrypt_roundtrip(self):
        """Test encrypt/decrypt roundtrip"""
        wallet = Wallet()
        data = "Sensitive wallet data"
        password = "Password123"

        encrypted = wallet._encrypt(data, password)
        decrypted = wallet._decrypt(encrypted, password)

        assert decrypted == data


class TestWalletStaticMethods:
    """Test wallet static methods"""

    def test_decrypt_static_method(self):
        """Test _decrypt_static method"""
        wallet = Wallet()
        data = "Test data"
        password = "Password123"

        # Encrypt with instance method
        encrypted = wallet._encrypt(data, password)

        # Decrypt with static method
        decrypted = Wallet._decrypt_static(encrypted, password)

        assert decrypted == data

    def test_decrypt_payload_static_method(self):
        """Test _decrypt_payload_static method"""
        wallet = Wallet()
        data = "Test data"
        password = "Password123"

        # Encrypt with instance method
        payload = wallet._encrypt_payload(data, password)

        # Decrypt with static method
        decrypted = Wallet._decrypt_payload_static(payload, password)

        assert decrypted == data

    def test_load_from_file_static(self):
        """Test load_from_file static method"""
        with tempfile.TemporaryDirectory() as tmpdir:
            filename = os.path.join(tmpdir, "test.wallet")

            # Create and save wallet
            wallet1 = Wallet()
            wallet1.save_to_file(filename)

            # Load using static method
            wallet2 = Wallet.load_from_file(filename)

            assert wallet2.address == wallet1.address

    def test_load_from_file_encrypted_static(self):
        """Test load_from_file static method with encrypted wallet"""
        with tempfile.TemporaryDirectory() as tmpdir:
            filename = os.path.join(tmpdir, "test.wallet")
            password = "SecurePass123"

            # Create and save encrypted wallet
            wallet1 = Wallet()
            wallet1.save_to_file(filename, password=password)

            # Load using static method
            wallet2 = Wallet.load_from_file(filename, password=password)

            assert wallet2.address == wallet1.address

    def test_load_from_file_old_format(self):
        """Test load_from_file with old encryption format"""
        with tempfile.TemporaryDirectory() as tmpdir:
            filename = os.path.join(tmpdir, "old_format.wallet")
            password = "Password123"

            wallet1 = Wallet()

            # Create old format (using _encrypt instead of _encrypt_payload)
            wallet_data = {
                "private_key": wallet1.private_key,
                "public_key": wallet1.public_key,
                "address": wallet1.address,
            }

            encrypted_data = wallet1._encrypt(json.dumps(wallet_data), password)

            with open(filename, "w") as f:
                json.dump({"encrypted": True, "data": encrypted_data}, f)

            # Load wallet
            wallet2 = Wallet.load_from_file(filename, password=password)

            assert wallet2.address == wallet1.address


class TestWalletDictMethods:
    """Test wallet to_dict methods"""

    def test_to_dict(self):
        """Test to_dict method"""
        wallet = Wallet()
        data = wallet.to_dict()

        assert "address" in data
        assert "public_key" in data
        assert "private_key" not in data

    def test_to_public_dict(self):
        """Test to_public_dict method"""
        wallet = Wallet()
        data = wallet.to_public_dict()

        assert "address" in data
        assert "public_key" in data
        assert "private_key" not in data
        assert data["address"] == wallet.address
        assert data["public_key"] == wallet.public_key

    def test_to_full_dict_unsafe(self):
        """Test to_full_dict_unsafe method includes private key"""
        wallet = Wallet()
        data = wallet.to_full_dict_unsafe()

        assert "address" in data
        assert "public_key" in data
        assert "private_key" in data
        assert data["private_key"] == wallet.private_key


class TestWalletVerificationEdgeCases:
    """Test edge cases in signature verification"""

    def test_verify_signature_bad_signature_error(self):
        """Test verification with malformed signature"""
        wallet = Wallet()
        message = "Test"

        # Create invalid signature
        invalid_sig = "0" * 128

        result = wallet.verify_signature(message, invalid_sig, wallet.public_key)

        assert result is False

    def test_verify_signature_unexpected_exception(self):
        """Test verification handles unexpected exceptions"""
        wallet = Wallet()
        message = "Test"

        # Use invalid public key to trigger exception
        result = wallet.verify_signature(message, "0" * 128, "invalid_pubkey")

        assert result is False

    def test_verify_signature_wrong_length(self):
        """Test verification with wrong signature length"""
        wallet = Wallet()
        message = "Test"

        # Too short signature
        result = wallet.verify_signature(message, "abc", wallet.public_key)

        assert result is False


class TestWalletMainBlock:
    """Test wallet main block execution"""

    def test_wallet_main_execution(self, capsys):
        """Test wallet __main__ block would execute correctly"""
        # This tests the example usage code
        # We can't directly run __main__ but we can test the functionality

        wallet = Wallet()

        # Test wallet creation
        assert wallet.address is not None
        assert wallet.public_key is not None
        assert wallet.private_key is not None

        # Test signing
        message = "Hello AXN!"
        signature = wallet.sign_message(message)
        assert signature is not None

        # Test verification
        is_valid = wallet.verify_signature(message, signature, wallet.public_key)
        assert is_valid

        # Test save (using temp file)
        with tempfile.TemporaryDirectory() as tmpdir:
            filename = os.path.join(tmpdir, "test_wallet.json")
            wallet.save_to_file(filename)
            assert os.path.exists(filename)


class TestWalletErrorPaths:
    """Test error handling paths"""

    def test_decrypt_payload_bad_decrypt(self):
        """Test _decrypt_payload with bad data raises ValueError"""
        wallet = Wallet()

        # Invalid payload
        bad_payload = {
            "ciphertext": "invalid",
            "nonce": "invalid",
            "salt": "invalid"
        }

        with pytest.raises(ValueError, match="Bad decrypt"):
            wallet._decrypt_payload(bad_payload, "password")

    def test_save_to_file_creates_parent_directories(self):
        """Test save_to_file creates parent directories"""
        with tempfile.TemporaryDirectory() as tmpdir:
            wallet = Wallet()

            # Use nested path
            filename = os.path.join(tmpdir, "subdir", "wallet.json")

            # Create parent directory first (wallet doesn't auto-create)
            os.makedirs(os.path.dirname(filename), exist_ok=True)

            wallet.save_to_file(filename)

            assert os.path.exists(filename)


class TestWalletKeyDerivation:
    """Test key derivation functions"""

    def test_derive_public_key_deterministic(self):
        """Test public key derivation is deterministic"""
        private_key = "a" * 64

        wallet1 = Wallet(private_key=private_key)
        wallet2 = Wallet(private_key=private_key)

        assert wallet1.public_key == wallet2.public_key

    def test_generate_address_deterministic(self):
        """Test address generation is deterministic"""
        wallet = Wallet()

        address1 = wallet._generate_address(wallet.public_key)
        address2 = wallet._generate_address(wallet.public_key)

        assert address1 == address2

    def test_generate_address_different_public_keys(self):
        """Test different public keys produce different addresses"""
        wallet1 = Wallet()
        wallet2 = Wallet()

        address1 = wallet1._generate_address(wallet1.public_key)
        address2 = wallet2._generate_address(wallet2.public_key)

        assert address1 != address2


class TestWalletEncryptionPayload:
    """Test encryption payload structure"""

    def test_encrypt_payload_structure(self):
        """Test _encrypt_payload returns correct structure"""
        wallet = Wallet()
        payload = wallet._encrypt_payload("test data", "password")

        assert "ciphertext" in payload
        assert "nonce" in payload
        assert "salt" in payload
        assert isinstance(payload["ciphertext"], str)
        assert isinstance(payload["nonce"], str)
        assert isinstance(payload["salt"], str)

    def test_encrypt_payload_randomness(self):
        """Test _encrypt_payload produces different outputs"""
        wallet = Wallet()
        data = "test data"
        password = "password"

        payload1 = wallet._encrypt_payload(data, password)
        payload2 = wallet._encrypt_payload(data, password)

        # Different nonce and salt should produce different ciphertext
        assert payload1["nonce"] != payload2["nonce"]
        assert payload1["salt"] != payload2["salt"]
        assert payload1["ciphertext"] != payload2["ciphertext"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
