"""
Unit tests for wallet encryption migration
Tests migration from weak SHA256 encryption to secure PBKDF2
"""

import pytest
import json
import tempfile
import os
import base64
import hashlib
from cryptography.fernet import Fernet

from xai.core.wallet import Wallet


class TestWalletMigration:
    """Test wallet encryption migration functionality"""

    def test_needs_migration_legacy_wallet(self):
        """Test detection of legacy wallet format"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            # Create legacy wallet format (version 1.0 or no version)
            legacy_data = {
                "address": "XAI123",
                "public_key": "test_public_key",
                "private_key": "test_private_key"
            }
            json.dump(legacy_data, f)
            legacy_file = f.name

        try:
            # Should detect migration needed
            assert Wallet.needs_migration(legacy_file) is True
        finally:
            os.unlink(legacy_file)

    def test_needs_migration_v2_wallet(self):
        """Test that v2.0 wallets don't need migration"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            # Create v2.0 wallet format
            v2_data = {
                "version": "2.0",
                "data": {
                    "address": "XAI123",
                    "public_key": "test_public_key"
                }
            }
            json.dump(v2_data, f)
            v2_file = f.name

        try:
            # Should NOT detect migration needed
            assert Wallet.needs_migration(v2_file) is False
        finally:
            os.unlink(v2_file)

    def test_needs_migration_old_encrypted_format(self):
        """Test detection of old encrypted format without payload"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            # Old encrypted format (encrypted:true but no "payload")
            old_encrypted = {
                "version": "1.0",
                "encrypted": True,
                "data": "encrypted_blob_here"
            }
            json.dump(old_encrypted, f)
            old_file = f.name

        try:
            # Should detect migration needed
            assert Wallet.needs_migration(old_file) is True
        finally:
            os.unlink(old_file)

    def test_migrate_wallet_encryption_success(self):
        """Test successful wallet migration from legacy to secure encryption"""
        wallet = Wallet()
        password = "TestPassword123"

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            # Create a legacy encrypted wallet file manually
            wallet_data = {
                "private_key": wallet.private_key,
                "public_key": wallet.public_key,
                "address": wallet.address
            }
            wallet_json = json.dumps(wallet_data)

            # Use legacy weak encryption (SHA256 only)
            key = base64.urlsafe_b64encode(hashlib.sha256(password.encode()).digest())
            fernet = Fernet(key)
            encrypted_data = fernet.encrypt(wallet_json.encode()).decode()

            # Create legacy file structure (no HMAC wrapper)
            legacy_file_data = {
                "encrypted": True,
                "data": encrypted_data
            }
            json.dump(legacy_file_data, f)
            legacy_file = f.name

        try:
            # Verify it needs migration
            assert Wallet.needs_migration(legacy_file) is True

            # Perform migration
            result = wallet.migrate_wallet_encryption(legacy_file, password)

            # Migration should succeed
            assert result is True

            # File should no longer need migration
            assert Wallet.needs_migration(legacy_file) is False

            # Should be able to load with same password
            migrated_wallet = Wallet.load_from_file(legacy_file, password)

            # Verify data integrity
            assert migrated_wallet.private_key == wallet.private_key
            assert migrated_wallet.public_key == wallet.public_key
            assert migrated_wallet.address == wallet.address

            # Verify backup was created
            backup_files = [f for f in os.listdir(os.path.dirname(legacy_file))
                            if f.startswith(os.path.basename(legacy_file)) and '.backup.' in f]
            assert len(backup_files) >= 1

        finally:
            # Cleanup
            if os.path.exists(legacy_file):
                os.unlink(legacy_file)
            # Cleanup backup files
            for backup in backup_files:
                backup_path = os.path.join(os.path.dirname(legacy_file), backup)
                if os.path.exists(backup_path):
                    os.unlink(backup_path)

    def test_migrate_already_secure_wallet(self):
        """Test that migrating an already-secure wallet returns True (no-op)"""
        wallet = Wallet()
        password = "TestPassword123"

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_file = f.name

        try:
            # Save with secure encryption (v2.0 format)
            wallet.save_to_file(temp_file, password)

            # Verify it doesn't need migration
            assert Wallet.needs_migration(temp_file) is False

            # Attempt migration
            result = wallet.migrate_wallet_encryption(temp_file, password)

            # Should succeed (no-op)
            assert result is True

        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)

    def test_load_legacy_wallet_emits_warning(self, caplog):
        """Test that loading legacy wallet emits critical warning"""
        wallet = Wallet()
        password = "TestPassword123"

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            # Create legacy encrypted wallet
            wallet_data = {
                "private_key": wallet.private_key,
                "public_key": wallet.public_key,
                "address": wallet.address
            }
            wallet_json = json.dumps(wallet_data)

            # Use legacy weak encryption
            key = base64.urlsafe_b64encode(hashlib.sha256(password.encode()).digest())
            fernet = Fernet(key)
            encrypted_data = fernet.encrypt(wallet_json.encode()).decode()

            legacy_file_data = {
                "encrypted": True,
                "data": encrypted_data
            }
            json.dump(legacy_file_data, f)
            legacy_file = f.name

        try:
            # Load legacy wallet
            with caplog.at_level("WARNING"):
                loaded_wallet = Wallet.load_from_file(legacy_file, password)

            # Verify wallet loaded correctly
            assert loaded_wallet.private_key == wallet.private_key

            # Verify warning was logged
            assert any("legacy encryption" in record.message.lower() for record in caplog.records)

        finally:
            if os.path.exists(legacy_file):
                os.unlink(legacy_file)

    def test_secure_encryption_uses_pbkdf2(self):
        """Test that new wallet encryption uses PBKDF2 with proper parameters"""
        wallet = Wallet()
        password = "TestPassword123"

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_file = f.name

        try:
            # Save with secure encryption
            wallet.save_to_file(temp_file, password)

            # Read file and verify structure
            with open(temp_file, 'r') as f:
                file_data = json.load(f)

            # Verify v2.0 format
            assert file_data.get("version") == "2.0"

            # Verify it has encrypted payload with salt and nonce
            data = file_data.get("data", {})
            assert data.get("encrypted") is True
            assert "payload" in data

            payload = data["payload"]
            assert "salt" in payload
            assert "nonce" in payload
            assert "ciphertext" in payload

            # Verify salt is 16+ bytes
            salt = base64.b64decode(payload["salt"])
            assert len(salt) >= 16

            # Verify nonce exists
            nonce = base64.b64decode(payload["nonce"])
            assert len(nonce) >= 12

        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)

    def test_backward_compatibility_loading(self):
        """Test that legacy wallets can still be loaded (backward compatibility)"""
        wallet = Wallet()
        password = "TestPassword123"

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            # Create legacy encrypted wallet
            wallet_data = {
                "private_key": wallet.private_key,
                "public_key": wallet.public_key,
                "address": wallet.address
            }
            wallet_json = json.dumps(wallet_data)

            # Use legacy weak encryption
            key = base64.urlsafe_b64encode(hashlib.sha256(password.encode()).digest())
            fernet = Fernet(key)
            encrypted_data = fernet.encrypt(wallet_json.encode()).decode()

            legacy_file_data = {
                "encrypted": True,
                "data": encrypted_data
            }
            json.dump(legacy_file_data, f)
            legacy_file = f.name

        try:
            # Should be able to load legacy wallet
            loaded_wallet = Wallet.load_from_file(legacy_file, password)

            # Verify wallet data is correct
            assert loaded_wallet.private_key == wallet.private_key
            assert loaded_wallet.public_key == wallet.public_key
            assert loaded_wallet.address == wallet.address

        finally:
            if os.path.exists(legacy_file):
                os.unlink(legacy_file)
