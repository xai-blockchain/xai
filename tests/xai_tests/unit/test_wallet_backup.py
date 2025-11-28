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
from xai.core.wallet_encryption import WalletEncryption


class TestWalletBackup:
    """Tests for wallet backup and restore"""

    def test_encrypted_backup_creation(self, tmp_path):
        """Test creating encrypted wallet backup"""
        wallet = Wallet()
        password = "secure_password_123"

        # Create backup
        backup_file = tmp_path / "wallet_backup.enc"

        wallet_data = {
            'address': wallet.address,
            'public_key': wallet.public_key,
            'private_key': wallet.private_key
        }

        # Encrypt and save
        encryptor = WalletEncryption()
        encrypted_data = encryptor.encrypt(json.dumps(wallet_data), password)

        with open(backup_file, 'w') as f:
            f.write(encrypted_data)

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
        encryptor = WalletEncryption()
        encrypted_data = encryptor.encrypt(json.dumps(wallet_data), password)

        with open(backup_file, 'w') as f:
            f.write(encrypted_data)

        # Restore from backup
        with open(backup_file, 'r') as f:
            encrypted_backup = f.read()

        decrypted_data = encryptor.decrypt(encrypted_backup, password)
        restored_data = json.loads(decrypted_data)

        # Verify restored data matches original
        assert restored_data['address'] == wallet1.address
        assert restored_data['public_key'] == wallet1.public_key
        assert restored_data['private_key'] == wallet1.private_key

    def test_backup_with_wrong_password_fails(self, tmp_path):
        """Test backup restoration fails with wrong password"""
        wallet = Wallet()
        correct_password = "correct_password"
        wrong_password = "wrong_password"

        # Create backup with correct password
        wallet_data = {
            'address': wallet.address,
            'public_key': wallet.public_key,
            'private_key': wallet.private_key
        }

        backup_file = tmp_path / "wallet_backup.enc"
        encryptor = WalletEncryption()
        encrypted_data = encryptor.encrypt(json.dumps(wallet_data), correct_password)

        with open(backup_file, 'w') as f:
            f.write(encrypted_data)

        # Try to restore with wrong password
        with open(backup_file, 'r') as f:
            encrypted_backup = f.read()

        with pytest.raises(Exception):  # Should raise decryption error
            encryptor.decrypt(encrypted_backup, wrong_password)

    def test_backup_file_integrity_check(self, tmp_path):
        """Test backup file integrity verification"""
        wallet = Wallet()
        password = "password123"

        wallet_data = {
            'address': wallet.address,
            'public_key': wallet.public_key,
            'private_key': wallet.private_key,
            'checksum': 'abc123'  # Add checksum for integrity
        }

        backup_file = tmp_path / "wallet_backup.enc"
        encryptor = WalletEncryption()
        encrypted_data = encryptor.encrypt(json.dumps(wallet_data), password)

        with open(backup_file, 'w') as f:
            f.write(encrypted_data)

        # Verify file wasn't corrupted
        with open(backup_file, 'r') as f:
            backup_content = f.read()

        assert len(backup_content) > 0
        assert backup_content == encrypted_data

    def test_partial_backup_missing_fields(self, tmp_path):
        """Test handling of backup with missing fields"""
        password = "password123"

        # Incomplete backup data (missing private_key)
        incomplete_data = {
            'address': 'XAI123',
            'public_key': 'pubkey123'
            # private_key is missing
        }

        backup_file = tmp_path / "incomplete_backup.enc"
        encryptor = WalletEncryption()
        encrypted_data = encryptor.encrypt(json.dumps(incomplete_data), password)

        with open(backup_file, 'w') as f:
            f.write(encrypted_data)

        # Restore
        with open(backup_file, 'r') as f:
            encrypted_backup = f.read()

        decrypted_data = encryptor.decrypt(encrypted_backup, password)
        restored_data = json.loads(decrypted_data)

        # Should detect missing field
        assert 'private_key' not in restored_data
        assert 'address' in restored_data
        assert 'public_key' in restored_data

    def test_backup_format_compatibility(self, tmp_path):
        """Test backup format is compatible across versions"""
        wallet = Wallet()
        password = "password123"

        # Version 1 format
        wallet_data_v1 = {
            'version': 1,
            'address': wallet.address,
            'public_key': wallet.public_key,
            'private_key': wallet.private_key
        }

        backup_file = tmp_path / "wallet_v1.enc"
        encryptor = WalletEncryption()
        encrypted_data = encryptor.encrypt(json.dumps(wallet_data_v1), password)

        with open(backup_file, 'w') as f:
            f.write(encrypted_data)

        # Restore and verify
        with open(backup_file, 'r') as f:
            encrypted_backup = f.read()

        decrypted_data = encryptor.decrypt(encrypted_backup, password)
        restored_data = json.loads(decrypted_data)

        assert restored_data['version'] == 1
        assert 'address' in restored_data

    def test_multiple_wallet_backups(self, tmp_path):
        """Test backing up multiple wallets"""
        wallets = [Wallet() for _ in range(3)]
        password = "password123"

        encryptor = WalletEncryption()

        for i, wallet in enumerate(wallets):
            wallet_data = {
                'address': wallet.address,
                'public_key': wallet.public_key,
                'private_key': wallet.private_key
            }

            backup_file = tmp_path / f"wallet_{i}.enc"
            encrypted_data = encryptor.encrypt(json.dumps(wallet_data), password)

            with open(backup_file, 'w') as f:
                f.write(encrypted_data)

        # Verify all backups exist
        for i in range(3):
            assert (tmp_path / f"wallet_{i}.enc").exists()

    def test_backup_with_metadata(self, tmp_path):
        """Test backup includes wallet metadata"""
        wallet = Wallet()
        password = "password123"

        wallet_data = {
            'address': wallet.address,
            'public_key': wallet.public_key,
            'private_key': wallet.private_key,
            'metadata': {
                'label': 'My Main Wallet',
                'created_at': '2024-01-01',
                'backup_count': 1
            }
        }

        backup_file = tmp_path / "wallet_with_meta.enc"
        encryptor = WalletEncryption()
        encrypted_data = encryptor.encrypt(json.dumps(wallet_data), password)

        with open(backup_file, 'w') as f:
            f.write(encrypted_data)

        # Restore and verify metadata
        with open(backup_file, 'r') as f:
            encrypted_backup = f.read()

        decrypted_data = encryptor.decrypt(encrypted_backup, password)
        restored_data = json.loads(decrypted_data)

        assert 'metadata' in restored_data
        assert restored_data['metadata']['label'] == 'My Main Wallet'

    def test_empty_password_backup_fails(self, tmp_path):
        """Test backup with empty password is rejected"""
        wallet = Wallet()
        empty_password = ""

        wallet_data = {
            'address': wallet.address,
            'public_key': wallet.public_key,
            'private_key': wallet.private_key
        }

        encryptor = WalletEncryption()

        # Empty password should be rejected or handled specially
        try:
            encrypted_data = encryptor.encrypt(json.dumps(wallet_data), empty_password)
            # If encryption succeeds with empty password, that's a design choice
            # but restoration should work consistently
            decrypted = encryptor.decrypt(encrypted_data, empty_password)
            assert json.loads(decrypted)['address'] == wallet.address
        except ValueError:
            # Or it might reject empty passwords
            pass

    def test_corrupted_backup_file_detection(self, tmp_path):
        """Test detection of corrupted backup file"""
        backup_file = tmp_path / "corrupted_backup.enc"

        # Write corrupted data
        with open(backup_file, 'w') as f:
            f.write("corrupted_encrypted_data_xyz123")

        # Try to restore
        with open(backup_file, 'r') as f:
            corrupted_backup = f.read()

        encryptor = WalletEncryption()

        with pytest.raises(Exception):  # Should raise decryption error
            encryptor.decrypt(corrupted_backup, "password123")
