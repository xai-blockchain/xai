"""
Comprehensive tests for wallet backup and restore functionality

Tests encrypted backups, password protection, file integrity,
partial backup handling, and format compatibility.
"""

import pytest
import json
import os
from unittest.mock import Mock, patch, mock_open

from xai.core.wallet import Wallet
from xai.core.wallet_encryption import WalletEncryption, save_encrypted_wallet, load_encrypted_wallet


class TestWalletBackup:
    """Tests for wallet backup and restore using WalletEncryption API"""

    def test_encrypted_backup_creation(self, tmp_path):
        """Test creating encrypted wallet backup"""
        wallet = Wallet()
        password = "secure_password_123"  # At least 8 chars required

        # Create backup using the proper WalletEncryption API
        backup_file = tmp_path / "wallet_backup.enc"

        wallet_data = {
            'address': wallet.address,
            'public_key': wallet.public_key,
            'private_key': wallet.private_key
        }

        # Use the static encrypt_wallet method
        encrypted_data = WalletEncryption.encrypt_wallet(wallet_data, password)

        with open(backup_file, 'w') as f:
            json.dump(encrypted_data, f)

        # Verify file exists and has content
        assert backup_file.exists()
        assert backup_file.stat().st_size > 0

    def test_encrypted_restore(self, tmp_path):
        """Test restoring wallet from encrypted backup"""
        wallet1 = Wallet()
        password = "secure_password_123"

        # Create backup
        wallet_data = {
            'address': wallet1.address,
            'public_key': wallet1.public_key,
            'private_key': wallet1.private_key
        }

        backup_file = tmp_path / "wallet_backup.enc"
        encrypted_data = WalletEncryption.encrypt_wallet(wallet_data, password)

        with open(backup_file, 'w') as f:
            json.dump(encrypted_data, f)

        # Restore from backup
        with open(backup_file, 'r') as f:
            encrypted_backup = json.load(f)

        restored_data = WalletEncryption.decrypt_wallet(encrypted_backup, password)

        # Verify restored data matches original
        assert restored_data['address'] == wallet1.address
        assert restored_data['public_key'] == wallet1.public_key
        assert restored_data['private_key'] == wallet1.private_key

    def test_backup_with_wrong_password_fails(self, tmp_path):
        """Test backup restoration fails with wrong password"""
        wallet = Wallet()
        correct_password = "correct_password_123"
        wrong_password = "wrong_password_abc"

        # Create backup with correct password
        wallet_data = {
            'address': wallet.address,
            'public_key': wallet.public_key,
            'private_key': wallet.private_key
        }

        backup_file = tmp_path / "wallet_backup.enc"
        encrypted_data = WalletEncryption.encrypt_wallet(wallet_data, correct_password)

        with open(backup_file, 'w') as f:
            json.dump(encrypted_data, f)

        # Try to restore with wrong password
        with open(backup_file, 'r') as f:
            encrypted_backup = json.load(f)

        with pytest.raises(ValueError, match="Incorrect password"):
            WalletEncryption.decrypt_wallet(encrypted_backup, wrong_password)

    def test_backup_file_integrity_check(self, tmp_path):
        """Test backup file integrity verification"""
        wallet = Wallet()
        password = "password12345678"  # At least 8 chars

        wallet_data = {
            'address': wallet.address,
            'public_key': wallet.public_key,
            'private_key': wallet.private_key,
        }

        backup_file = tmp_path / "wallet_backup.enc"
        encrypted_data = WalletEncryption.encrypt_wallet(wallet_data, password)

        with open(backup_file, 'w') as f:
            json.dump(encrypted_data, f)

        # Verify file wasn't corrupted by reading it back
        with open(backup_file, 'r') as f:
            backup_content = json.load(f)

        assert backup_content.get("encrypted") is True
        assert "encrypted_private_key" in backup_content
        assert "salt" in backup_content

    def test_partial_backup_missing_fields(self, tmp_path):
        """Test handling of wallet with missing private_key raises error"""
        password = "password12345678"

        # Incomplete backup data (missing private_key)
        incomplete_data = {
            'address': 'XAI123abc456def789',
            'public_key': 'pubkey123'
            # private_key is missing
        }

        # encrypt_wallet should raise an error for missing private_key
        with pytest.raises(ValueError, match="private_key"):
            WalletEncryption.encrypt_wallet(incomplete_data, password)

    def test_backup_format_compatibility(self, tmp_path):
        """Test backup format is compatible and includes version info"""
        wallet = Wallet()
        password = "password12345678"

        wallet_data = {
            'address': wallet.address,
            'public_key': wallet.public_key,
            'private_key': wallet.private_key
        }

        backup_file = tmp_path / "wallet_v1.enc"
        encrypted_data = WalletEncryption.encrypt_wallet(wallet_data, password)

        # Verify format includes versioning
        assert "encryption_version" in encrypted_data
        assert encrypted_data.get("encrypted") is True

        with open(backup_file, 'w') as f:
            json.dump(encrypted_data, f)

        # Restore and verify
        with open(backup_file, 'r') as f:
            encrypted_backup = json.load(f)

        restored_data = WalletEncryption.decrypt_wallet(encrypted_backup, password)
        assert 'address' in restored_data
        assert 'private_key' in restored_data

    def test_multiple_wallet_backups(self, tmp_path):
        """Test backing up multiple wallets"""
        wallets = [Wallet() for _ in range(3)]
        password = "password12345678"

        for i, wallet in enumerate(wallets):
            wallet_data = {
                'address': wallet.address,
                'public_key': wallet.public_key,
                'private_key': wallet.private_key
            }

            backup_file = tmp_path / f"wallet_{i}.enc"
            encrypted_data = WalletEncryption.encrypt_wallet(wallet_data, password)

            with open(backup_file, 'w') as f:
                json.dump(encrypted_data, f)

        # Verify all backups exist
        for i in range(3):
            assert (tmp_path / f"wallet_{i}.enc").exists()

    def test_backup_with_metadata(self, tmp_path):
        """Test backup includes wallet metadata via optional fields"""
        wallet = Wallet()
        password = "password12345678"

        wallet_data = {
            'address': wallet.address,
            'public_key': wallet.public_key,
            'private_key': wallet.private_key,
            'initial_balance': 100.0,
            'tier': 'premium'
        }

        backup_file = tmp_path / "wallet_with_meta.enc"
        encrypted_data = WalletEncryption.encrypt_wallet(wallet_data, password)

        with open(backup_file, 'w') as f:
            json.dump(encrypted_data, f)

        # Restore and verify metadata
        with open(backup_file, 'r') as f:
            encrypted_backup = json.load(f)

        restored_data = WalletEncryption.decrypt_wallet(encrypted_backup, password)

        assert 'initial_balance' in restored_data
        assert restored_data['initial_balance'] == 100.0
        assert restored_data['tier'] == 'premium'

    def test_empty_password_backup_fails(self, tmp_path):
        """Test backup with empty password is rejected"""
        wallet = Wallet()
        empty_password = ""

        wallet_data = {
            'address': wallet.address,
            'public_key': wallet.public_key,
            'private_key': wallet.private_key
        }

        # Empty password should be rejected (min 8 characters required)
        with pytest.raises(ValueError, match="at least 8 characters"):
            WalletEncryption.encrypt_wallet(wallet_data, empty_password)

    def test_short_password_backup_fails(self, tmp_path):
        """Test backup with short password is rejected"""
        wallet = Wallet()
        short_password = "short"  # Less than 8 characters

        wallet_data = {
            'address': wallet.address,
            'public_key': wallet.public_key,
            'private_key': wallet.private_key
        }

        # Short password should be rejected
        with pytest.raises(ValueError, match="at least 8 characters"):
            WalletEncryption.encrypt_wallet(wallet_data, short_password)

    def test_corrupted_backup_file_detection(self, tmp_path):
        """Test detection of corrupted backup file"""
        backup_file = tmp_path / "corrupted_backup.enc"

        # Write corrupted data (not a valid encrypted wallet)
        corrupted_data = {
            "encrypted": True,
            "encrypted_private_key": "not_valid_base64!!!",
            "salt": "also_not_valid!!!"
        }
        with open(backup_file, 'w') as f:
            json.dump(corrupted_data, f)

        # Try to restore
        with open(backup_file, 'r') as f:
            corrupted_backup = json.load(f)

        with pytest.raises(Exception):  # Should raise decryption error
            WalletEncryption.decrypt_wallet(corrupted_backup, "password12345678")

    def test_change_password(self, tmp_path):
        """Test changing wallet encryption password"""
        wallet = Wallet()
        old_password = "old_password_123"
        new_password = "new_password_456"

        wallet_data = {
            'address': wallet.address,
            'public_key': wallet.public_key,
            'private_key': wallet.private_key
        }

        # Encrypt with old password
        encrypted_data = WalletEncryption.encrypt_wallet(wallet_data, old_password)

        # Change password
        re_encrypted = WalletEncryption.change_password(encrypted_data, old_password, new_password)

        # Old password should no longer work
        with pytest.raises(ValueError, match="Incorrect password"):
            WalletEncryption.decrypt_wallet(re_encrypted, old_password)

        # New password should work
        decrypted = WalletEncryption.decrypt_wallet(re_encrypted, new_password)
        assert decrypted['address'] == wallet.address
        assert decrypted['private_key'] == wallet.private_key

    def test_is_encrypted_check(self):
        """Test checking if wallet data is encrypted"""
        wallet = Wallet()
        password = "password12345678"

        wallet_data = {
            'address': wallet.address,
            'public_key': wallet.public_key,
            'private_key': wallet.private_key
        }

        # Unencrypted data
        assert WalletEncryption.is_encrypted(wallet_data) is False

        # Encrypted data
        encrypted = WalletEncryption.encrypt_wallet(wallet_data, password)
        assert WalletEncryption.is_encrypted(encrypted) is True

    def test_save_and_load_encrypted_wallet(self, tmp_path):
        """Test save_encrypted_wallet and load_encrypted_wallet helper functions"""
        wallet = Wallet()
        password = "password12345678"
        filename = str(tmp_path / "wallet.enc")

        wallet_data = {
            'address': wallet.address,
            'public_key': wallet.public_key,
            'private_key': wallet.private_key
        }

        # Save
        save_encrypted_wallet(wallet_data, password, filename)
        assert os.path.exists(filename)

        # Load
        loaded = load_encrypted_wallet(filename, password)
        assert loaded['address'] == wallet.address
        assert loaded['private_key'] == wallet.private_key
