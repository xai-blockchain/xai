"""
Unit tests for EncryptedAPIKeyStore with Fernet encryption and migration.

Tests cover:
- Encrypted key storage and retrieval
- Legacy hashed key backward compatibility
- Key rotation with encryption
- Migration from hashed to encrypted keys
- Multi-version key support
- Security features (constant-time comparison, no plaintext logging)
"""

import os
import time
from pathlib import Path

import pytest

from xai.core.encrypted_api_key_store import EncryptedAPIKeyStore
from xai.core.api_key_encryption import APIKeyEncryptionManager


class TestEncryptedAPIKeyStore:
    """Test suite for EncryptedAPIKeyStore."""

    def test_issue_encrypted_key(self, tmp_path: Path) -> None:
        """Issue a new encrypted API key and verify storage."""
        store = EncryptedAPIKeyStore(str(tmp_path / "keys.json"), enable_encryption=True)

        assert store.encryption_enabled is True

        plaintext, key_id = store.issue_key(label="test-key", scope="user")

        assert plaintext is not None
        assert key_id is not None
        assert key_id in store.list_keys()

        metadata = store.get_key_metadata(key_id)
        assert metadata is not None
        assert metadata["storage_type"] == "encrypted"
        assert metadata["label"] == "test-key"
        assert metadata["scope"] == "user"
        assert "encrypted_key" not in metadata  # Should be excluded from public metadata

    def test_issue_hashed_key_when_encryption_disabled(self, tmp_path: Path) -> None:
        """Issue hashed key when encryption is disabled."""
        store = EncryptedAPIKeyStore(str(tmp_path / "keys.json"), enable_encryption=False)

        assert store.encryption_enabled is False

        plaintext, key_id = store.issue_key(label="legacy-key", scope="admin")

        metadata = store.get_key_metadata(key_id)
        assert metadata is not None
        assert metadata["storage_type"] == "hashed"
        assert metadata["scope"] == "admin"

    def test_validate_encrypted_key(self, tmp_path: Path) -> None:
        """Validate encrypted API key using constant-time comparison."""
        store = EncryptedAPIKeyStore(str(tmp_path / "keys.json"))

        plaintext, key_id = store.issue_key(label="validate-test")

        # Validate correct key
        is_valid, found_key_id, metadata = store.validate_key(plaintext)
        assert is_valid is True
        assert found_key_id == key_id
        assert metadata is not None
        assert metadata["label"] == "validate-test"

        # Validate wrong key
        is_valid, found_key_id, metadata = store.validate_key("wrong-key")
        assert is_valid is False
        assert found_key_id is None
        assert metadata is None

    def test_validate_legacy_hashed_key(self, tmp_path: Path) -> None:
        """Validate legacy hashed key for backward compatibility."""
        store = EncryptedAPIKeyStore(str(tmp_path / "keys.json"), enable_encryption=False)

        plaintext, key_id = store.issue_key(label="legacy")

        # Validate hashed key
        is_valid, found_key_id, metadata = store.validate_key(plaintext)
        assert is_valid is True
        assert found_key_id == key_id

    def test_rotate_encrypted_key(self, tmp_path: Path) -> None:
        """Rotate an encrypted key and verify old key is revoked."""
        store = EncryptedAPIKeyStore(str(tmp_path / "keys.json"))

        old_plain, old_key_id = store.issue_key(label="rotate-test", scope="user")

        # Rotate key
        new_plain, new_key_id = store.rotate_key(old_key_id, label="rotated-key", scope="admin")

        # Old key should be revoked
        assert old_key_id not in store.list_keys()
        is_valid, _, _ = store.validate_key(old_plain)
        assert is_valid is False

        # New key should work
        assert new_key_id in store.list_keys()
        is_valid, found_id, metadata = store.validate_key(new_plain)
        assert is_valid is True
        assert found_id == new_key_id
        assert metadata["label"] == "rotated-key"
        assert metadata["scope"] == "admin"

    def test_revoke_key(self, tmp_path: Path) -> None:
        """Revoke an API key and verify it cannot be validated."""
        store = EncryptedAPIKeyStore(str(tmp_path / "keys.json"))

        plaintext, key_id = store.issue_key(label="revoke-test")

        # Revoke key
        result = store.revoke_key(key_id)
        assert result is True

        # Key should not be found
        assert key_id not in store.list_keys()
        is_valid, _, _ = store.validate_key(plaintext)
        assert is_valid is False

        # Revoking again should return False
        result = store.revoke_key(key_id)
        assert result is False

    def test_migrate_hashed_to_encrypted(self, tmp_path: Path) -> None:
        """Migrate a legacy hashed key to encrypted storage."""
        store = EncryptedAPIKeyStore(str(tmp_path / "keys.json"), enable_encryption=False)

        # Issue hashed key
        plaintext, old_key_id = store.issue_key(label="to-migrate", scope="user")

        metadata_before = store.get_key_metadata(old_key_id)
        assert metadata_before["storage_type"] == "hashed"

        # Enable encryption
        store._encryption_mgr = APIKeyEncryptionManager(enable_encryption=True)

        # Migrate key
        success, new_key_id = store.migrate_to_encrypted(plaintext)

        assert success is True
        assert new_key_id is not None
        assert old_key_id not in store.list_keys()  # Old key removed
        assert new_key_id in store.list_keys()  # New key added

        # Verify new key metadata
        metadata_after = store.get_key_metadata(new_key_id)
        assert metadata_after is not None
        assert metadata_after["storage_type"] == "encrypted"
        assert metadata_after["label"] == "to-migrate"
        assert metadata_after["scope"] == "user"
        assert metadata_after["migrated_from"] == old_key_id

        # Validate migrated key
        is_valid, found_id, _ = store.validate_key(plaintext)
        assert is_valid is True
        assert found_id == new_key_id

    def test_migrate_nonexistent_key(self, tmp_path: Path) -> None:
        """Attempt to migrate a non-existent key."""
        store = EncryptedAPIKeyStore(str(tmp_path / "keys.json"))

        success, error = store.migrate_to_encrypted("nonexistent-key")
        assert success is False
        assert error == "Key not found"

    def test_key_expiration(self, tmp_path: Path) -> None:
        """Test key expiration handling."""
        store = EncryptedAPIKeyStore(str(tmp_path / "keys.json"))

        # Issue key with 1-second TTL
        plaintext, key_id = store.issue_key(label="expiring", ttl_seconds=1)

        # Key should be valid initially
        is_valid, _, _ = store.validate_key(plaintext)
        assert is_valid is True

        # Wait for expiration
        time.sleep(1.5)

        # Key should be expired
        is_valid, found_id, metadata = store.validate_key(plaintext)
        assert is_valid is False  # Expired keys return False
        assert found_id == key_id  # But we know which key it was
        assert metadata is not None

        # Verify metadata shows expiration
        metadata = store.get_key_metadata(key_id)
        assert metadata["expired"] is True

    def test_permanent_keys(self, tmp_path: Path) -> None:
        """Test permanent (non-expiring) keys."""
        store = EncryptedAPIKeyStore(str(tmp_path / "keys.json"), allow_permanent=True)

        plaintext, key_id = store.issue_key(label="permanent", permanent=True)

        metadata = store.get_key_metadata(key_id)
        assert metadata["permanent"] is True
        assert metadata["expires_at"] is None
        assert metadata["expired"] is False

        # Validate key
        is_valid, _, _ = store.validate_key(plaintext)
        assert is_valid is True

    def test_permanent_keys_disabled(self, tmp_path: Path) -> None:
        """Test that permanent keys can be disabled."""
        store = EncryptedAPIKeyStore(str(tmp_path / "keys.json"), allow_permanent=False)

        with pytest.raises(ValueError, match="Permanent API keys are disabled"):
            store.issue_key(label="permanent", permanent=True)

    def test_persistence(self, tmp_path: Path) -> None:
        """Test that keys persist across store instances with same encryption key."""
        store_path = str(tmp_path / "keys.json")

        # Generate encryption key to use for both stores
        from xai.core.api_key_encryption import APIKeyEncryptionManager

        encryption_key = APIKeyEncryptionManager.generate_key()

        # Create store and issue key
        store1 = EncryptedAPIKeyStore(store_path, encryption_key=encryption_key)
        plaintext, key_id = store1.issue_key(label="persist-test", scope="admin")

        # Create new store instance with same encryption key (reload from disk)
        store2 = EncryptedAPIKeyStore(store_path, encryption_key=encryption_key)

        # Key should exist
        assert key_id in store2.list_keys()

        # Validate key
        is_valid, found_id, metadata = store2.validate_key(plaintext)
        assert is_valid is True
        assert found_id == key_id
        assert metadata["label"] == "persist-test"
        assert metadata["scope"] == "admin"

    def test_audit_log(self, tmp_path: Path) -> None:
        """Test audit logging for key operations."""
        store = EncryptedAPIKeyStore(str(tmp_path / "keys.json"))

        # Issue key
        _, key_id1 = store.issue_key(label="audit-test")

        # Rotate key
        _, key_id2 = store.rotate_key(key_id1, label="rotated")

        # Revoke key
        store.revoke_key(key_id2)

        # Check audit log
        events = store.get_events()

        assert len(events) >= 3

        issue_events = [e for e in events if e["action"] == "issue"]
        rotate_events = [e for e in events if e["action"] == "rotate"]
        revoke_events = [e for e in events if e["action"] == "revoke"]

        assert len(issue_events) >= 1
        assert len(rotate_events) >= 1
        assert len(revoke_events) >= 1

        # Verify rotate event has metadata
        rotate_event = rotate_events[0]
        assert "replaced" in rotate_event
        assert rotate_event["replaced"] == key_id1

    def test_statistics(self, tmp_path: Path) -> None:
        """Test key storage statistics."""
        store = EncryptedAPIKeyStore(str(tmp_path / "keys.json"))

        # Issue encrypted keys
        store.issue_key(label="key1", scope="user")
        store.issue_key(label="key2", scope="admin")

        # Issue hashed key
        store.issue_key(label="key3", scope="user", use_encryption=False)

        # Issue expired key
        store.issue_key(label="key4", ttl_seconds=1)
        time.sleep(1.5)

        stats = store.get_statistics()

        assert stats["total_keys"] == 4
        assert stats["encrypted_keys"] == 3
        assert stats["hashed_keys"] == 1
        assert stats["expired_keys"] == 1
        assert stats["active_keys"] == 3

        assert stats["by_scope"]["user"] == 3
        assert stats["by_scope"]["admin"] == 1

    def test_list_keys_excludes_encrypted_data(self, tmp_path: Path) -> None:
        """Verify list_keys() does not expose encrypted_key field."""
        store = EncryptedAPIKeyStore(str(tmp_path / "keys.json"))

        _, key_id = store.issue_key(label="security-test")

        keys = store.list_keys()
        metadata = keys[key_id]

        assert "encrypted_key" not in metadata
        assert "label" in metadata
        assert "scope" in metadata

    def test_bootstrap_with_specific_key(self, tmp_path: Path) -> None:
        """Test issuing a key with specific plaintext (bootstrap scenario)."""
        store = EncryptedAPIKeyStore(str(tmp_path / "keys.json"))

        specific_key = "bootstrap-secret-key-12345"

        plaintext, key_id = store.issue_key(
            label="bootstrap",
            scope="admin",
            plaintext=specific_key,
        )

        assert plaintext == specific_key

        # Validate bootstrap key
        is_valid, found_id, metadata = store.validate_key(specific_key)
        assert is_valid is True
        assert found_id == key_id
        assert metadata["scope"] == "admin"

    def test_ttl_limits(self, tmp_path: Path) -> None:
        """Test TTL is clamped to max_ttl_days."""
        store = EncryptedAPIKeyStore(
            str(tmp_path / "keys.json"),
            default_ttl_days=90,
            max_ttl_days=180,
        )

        # Request 1 year TTL, should be clamped to 180 days
        _, key_id = store.issue_key(label="ttl-test", ttl_seconds=365 * 86400)

        metadata = store.get_key_metadata(key_id)
        created = metadata["created"]
        expires_at = metadata["expires_at"]

        # TTL should be clamped to 180 days
        ttl = expires_at - created
        assert ttl <= 180 * 86400 + 1  # Allow 1 second tolerance

    def test_encryption_with_custom_key(self, tmp_path: Path) -> None:
        """Test encryption with a custom Fernet key."""
        # Generate custom key
        from xai.core.api_key_encryption import APIKeyEncryptionManager

        custom_key = APIKeyEncryptionManager.generate_key()

        store = EncryptedAPIKeyStore(
            str(tmp_path / "keys.json"),
            encryption_key=custom_key,
        )

        plaintext, key_id = store.issue_key(label="custom-key-test")

        # Validate key
        is_valid, _, _ = store.validate_key(plaintext)
        assert is_valid is True

        # Verify persistence with custom key
        store2 = EncryptedAPIKeyStore(
            str(tmp_path / "keys.json"),
            encryption_key=custom_key,
        )

        is_valid, _, _ = store2.validate_key(plaintext)
        assert is_valid is True


class TestEncryptionManager:
    """Test suite for APIKeyEncryptionManager."""

    def test_generate_key(self) -> None:
        """Test Fernet key generation."""
        key = APIKeyEncryptionManager.generate_key()
        assert key is not None
        assert isinstance(key, str)
        assert len(key) > 0

        # Should be valid Fernet key
        mgr = APIKeyEncryptionManager(encryption_key=key)
        assert mgr.is_enabled() is True

    def test_derive_key_from_secret(self) -> None:
        """Test key derivation from secret."""
        secret = "my-secret-passphrase"

        key1 = APIKeyEncryptionManager.derive_key_from_secret(secret)
        key2 = APIKeyEncryptionManager.derive_key_from_secret(secret)

        # Same secret should produce same key
        assert key1 == key2

        # Different secret should produce different key
        key3 = APIKeyEncryptionManager.derive_key_from_secret("different-secret")
        assert key3 != key1

    def test_encrypt_decrypt(self) -> None:
        """Test basic encryption and decryption."""
        mgr = APIKeyEncryptionManager()

        plaintext = "my-secret-api-key-12345"

        encrypted = mgr.encrypt(plaintext)
        assert encrypted is not None
        assert plaintext not in encrypted  # Plaintext should not appear in ciphertext

        decrypted = mgr.decrypt(encrypted)
        assert decrypted == plaintext

    def test_versioned_encryption(self) -> None:
        """Test encryption with version prefix."""
        mgr = APIKeyEncryptionManager()

        plaintext = "test-key"
        encrypted = mgr.encrypt(plaintext)

        # Should have version prefix
        assert ":" in encrypted
        version_str, _ = encrypted.split(":", 1)
        assert version_str.isdigit()
        assert int(version_str) == 1

    def test_multi_version_decryption(self) -> None:
        """Test decryption with multiple key versions."""
        # Create manager with current key
        key1 = APIKeyEncryptionManager.generate_key()
        mgr1 = APIKeyEncryptionManager(encryption_key=key1)

        plaintext = "multi-version-test"
        encrypted_v1 = mgr1.encrypt(plaintext)

        # Simulate rotation: set old key as v2, new key as v1
        os.environ["XAI_API_KEY_ENCRYPTION_KEY"] = APIKeyEncryptionManager.generate_key()
        os.environ["XAI_API_KEY_ENCRYPTION_KEY_V2"] = key1

        # Create new manager with rotated keys
        mgr2 = APIKeyEncryptionManager()

        # Should still decrypt v1 encrypted data
        decrypted = mgr2.decrypt(encrypted_v1)
        assert decrypted == plaintext

        # Clean up env
        os.environ.pop("XAI_API_KEY_ENCRYPTION_KEY_V2", None)

    def test_re_encrypt(self) -> None:
        """Test re-encryption for key rotation."""
        mgr = APIKeyEncryptionManager()

        plaintext = "re-encrypt-test"
        encrypted_v1 = mgr.encrypt(plaintext, version=1)

        # Re-encrypt (same version for this test)
        encrypted_v1_again = mgr.re_encrypt(encrypted_v1, target_version=1)
        assert encrypted_v1_again is not None

        # Decrypt should still work
        decrypted = mgr.decrypt(encrypted_v1_again)
        assert decrypted == plaintext

    def test_constant_time_compare(self) -> None:
        """Test constant-time string comparison."""
        mgr = APIKeyEncryptionManager()

        # Equal strings
        assert mgr.constant_time_compare("test", "test") is True

        # Different strings
        assert mgr.constant_time_compare("test", "TEST") is False
        assert mgr.constant_time_compare("test", "tess") is False
        assert mgr.constant_time_compare("short", "longer") is False

    def test_invalid_decryption(self) -> None:
        """Test decryption with invalid ciphertext."""
        mgr = APIKeyEncryptionManager()

        # Invalid ciphertext
        decrypted = mgr.decrypt("invalid-ciphertext")
        assert decrypted is None

        # Tampered ciphertext
        plaintext = "test"
        encrypted = mgr.encrypt(plaintext)
        tampered = encrypted[:-5] + "XXXXX"  # Modify end
        decrypted = mgr.decrypt(tampered)
        assert decrypted is None


class TestBackwardCompatibility:
    """Test backward compatibility between hashed and encrypted keys."""

    def test_mixed_key_types(self, tmp_path: Path) -> None:
        """Test store with both hashed and encrypted keys."""
        store = EncryptedAPIKeyStore(str(tmp_path / "keys.json"))

        # Issue hashed key
        hashed_plain, hashed_id = store.issue_key(label="hashed", use_encryption=False)

        # Issue encrypted key
        encrypted_plain, encrypted_id = store.issue_key(label="encrypted", use_encryption=True)

        # Both should validate
        is_valid, found_id, _ = store.validate_key(hashed_plain)
        assert is_valid is True
        assert found_id == hashed_id

        is_valid, found_id, _ = store.validate_key(encrypted_plain)
        assert is_valid is True
        assert found_id == encrypted_id

        # Check statistics
        stats = store.get_statistics()
        assert stats["hashed_keys"] == 1
        assert stats["encrypted_keys"] == 1

    def test_load_legacy_store(self, tmp_path: Path) -> None:
        """Test loading store created without encryption."""
        store_path = str(tmp_path / "keys.json")

        # Create legacy store (no encryption)
        legacy_store = EncryptedAPIKeyStore(store_path, enable_encryption=False)
        legacy_plain, legacy_id = legacy_store.issue_key(label="legacy", scope="admin")

        # Load with encryption-enabled store
        modern_store = EncryptedAPIKeyStore(store_path, enable_encryption=True)

        # Legacy key should still validate
        is_valid, found_id, metadata = modern_store.validate_key(legacy_plain)
        assert is_valid is True
        assert found_id == legacy_id
        assert metadata["storage_type"] == "hashed"

        # New keys should use encryption
        new_plain, new_id = modern_store.issue_key(label="modern")
        new_metadata = modern_store.get_key_metadata(new_id)
        assert new_metadata["storage_type"] == "encrypted"
