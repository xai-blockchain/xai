"""
Unit tests for Flask secret key manager.

Tests cover:
- Secret key persistence and retrieval
- Environment variable override
- File permissions
- Error handling
- Key rotation
"""

import os
import tempfile
import stat
from pathlib import Path
import pytest
from xai.core.security.flask_secret_manager import FlaskSecretManager, get_flask_secret_key


class TestFlaskSecretManager:
    """Test Flask secret key manager functionality."""

    def test_generate_secret_key(self, tmp_path):
        """Test secret key generation."""
        manager = FlaskSecretManager(data_dir=str(tmp_path))
        secret_key = manager.get_secret_key()

        # Should be 64 character hex string (32 bytes)
        assert len(secret_key) == 64
        assert all(c in '0123456789abcdef' for c in secret_key.lower())

    def test_secret_key_persistence(self, tmp_path):
        """Test that secret key is persisted to file."""
        manager = FlaskSecretManager(data_dir=str(tmp_path))
        secret_key1 = manager.get_secret_key()

        # Create new manager instance
        manager2 = FlaskSecretManager(data_dir=str(tmp_path))
        secret_key2 = manager2.get_secret_key()

        # Should load the same key
        assert secret_key1 == secret_key2

    def test_secret_key_file_permissions(self, tmp_path):
        """Test that secret key file has secure permissions (0600)."""
        manager = FlaskSecretManager(data_dir=str(tmp_path))
        manager.get_secret_key()

        secret_file = tmp_path / ".secret_key"
        assert secret_file.exists()

        # Check permissions (owner read/write only)
        file_mode = stat.S_IMODE(os.stat(secret_file).st_mode)
        assert file_mode == 0o600

    def test_environment_variable_override(self, tmp_path, monkeypatch):
        """Test that XAI_SECRET_KEY environment variable takes precedence."""
        env_key = "a" * 64
        monkeypatch.setenv("XAI_SECRET_KEY", env_key)

        manager = FlaskSecretManager(data_dir=str(tmp_path))
        secret_key = manager.get_secret_key()

        assert secret_key == env_key

        # File should not be created when env var is set
        secret_file = tmp_path / ".secret_key"
        assert not secret_file.exists()

    def test_flask_secret_key_fallback(self, tmp_path, monkeypatch):
        """Test that FLASK_SECRET_KEY works as fallback."""
        env_key = "b" * 64
        monkeypatch.setenv("FLASK_SECRET_KEY", env_key)

        manager = FlaskSecretManager(data_dir=str(tmp_path))
        secret_key = manager.get_secret_key()

        assert secret_key == env_key

        # File should not be created when env var is set
        secret_file = tmp_path / ".secret_key"
        assert not secret_file.exists()

    def test_xai_secret_key_precedence(self, tmp_path, monkeypatch):
        """Test that XAI_SECRET_KEY takes precedence over FLASK_SECRET_KEY."""
        xai_key = "c" * 64
        flask_key = "d" * 64
        monkeypatch.setenv("XAI_SECRET_KEY", xai_key)
        monkeypatch.setenv("FLASK_SECRET_KEY", flask_key)

        manager = FlaskSecretManager(data_dir=str(tmp_path))
        secret_key = manager.get_secret_key()

        # Should use XAI_SECRET_KEY, not FLASK_SECRET_KEY
        assert secret_key == xai_key
        assert secret_key != flask_key

    def test_corrupted_secret_file(self, tmp_path):
        """Test handling of corrupted secret key file."""
        secret_file = tmp_path / ".secret_key"
        secret_file.write_text("")  # Empty file

        manager = FlaskSecretManager(data_dir=str(tmp_path))
        secret_key = manager.get_secret_key()

        # Should generate new key and overwrite corrupted file
        assert len(secret_key) == 64
        assert secret_file.read_text().strip() == secret_key

    def test_short_secret_key(self, tmp_path):
        """Test handling of too-short secret key in file."""
        secret_file = tmp_path / ".secret_key"
        secret_file.write_text("abc123")  # Too short

        manager = FlaskSecretManager(data_dir=str(tmp_path))
        secret_key = manager.get_secret_key()

        # Should generate new key
        assert len(secret_key) == 64
        assert secret_key != "abc123"

    def test_key_rotation(self, tmp_path):
        """Test secret key rotation."""
        manager = FlaskSecretManager(data_dir=str(tmp_path))
        old_key = manager.get_secret_key()

        new_key = manager.rotate_secret_key()

        # Keys should be different
        assert old_key != new_key
        assert len(new_key) == 64

        # New key should be persisted
        manager2 = FlaskSecretManager(data_dir=str(tmp_path))
        loaded_key = manager2.get_secret_key()
        assert loaded_key == new_key

    def test_data_dir_creation(self):
        """Test that data directory is created if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            data_dir = Path(tmp_dir) / "subdir" / "xai"
            assert not data_dir.exists()

            manager = FlaskSecretManager(data_dir=str(data_dir))
            manager.get_secret_key()

            assert data_dir.exists()

    def test_default_data_dir(self, monkeypatch, tmp_path):
        """Test default data directory (~/.xai)."""
        # Mock home directory
        monkeypatch.setenv("HOME", str(tmp_path))

        manager = FlaskSecretManager()
        secret_key = manager.get_secret_key()

        expected_dir = tmp_path / ".xai"
        assert expected_dir.exists()
        assert (expected_dir / ".secret_key").exists()
        assert len(secret_key) == 64

    def test_get_flask_secret_key_convenience(self, tmp_path):
        """Test convenience function."""
        secret_key = get_flask_secret_key(data_dir=str(tmp_path))

        assert len(secret_key) == 64
        assert (tmp_path / ".secret_key").exists()

    def test_secret_key_uniqueness(self, tmp_path):
        """Test that different instances generate different keys."""
        dir1 = tmp_path / "instance1"
        dir2 = tmp_path / "instance2"

        key1 = get_flask_secret_key(data_dir=str(dir1))
        key2 = get_flask_secret_key(data_dir=str(dir2))

        # Different instances should have different keys
        assert key1 != key2

    def test_secret_key_format(self, tmp_path):
        """Test that generated secret keys are valid hex."""
        manager = FlaskSecretManager(data_dir=str(tmp_path))
        secret_key = manager.get_secret_key()

        # Should be valid hex
        try:
            bytes.fromhex(secret_key)
        except ValueError:
            pytest.fail("Secret key is not valid hex")

    def test_read_permission_error(self, tmp_path):
        """Test handling of permission errors when reading secret key."""
        manager = FlaskSecretManager(data_dir=str(tmp_path))
        manager.get_secret_key()

        secret_file = tmp_path / ".secret_key"

        # Make file unreadable
        os.chmod(secret_file, 0o000)

        try:
            # Should generate new key on permission error
            manager2 = FlaskSecretManager(data_dir=str(tmp_path))
            secret_key = manager2.get_secret_key()
            assert len(secret_key) == 64
        finally:
            # Restore permissions for cleanup
            os.chmod(secret_file, 0o600)

    def test_write_permission_error(self, tmp_path, monkeypatch, caplog):
        """Test handling of permission errors when writing secret key."""
        # Make directory read-only
        os.chmod(tmp_path, 0o500)

        try:
            manager = FlaskSecretManager(data_dir=str(tmp_path))
            secret_key = manager.get_secret_key()

            # Should still generate key even if can't persist
            assert len(secret_key) == 64

            # Should log error
            assert "Failed to persist secret key" in caplog.text
        finally:
            # Restore permissions for cleanup
            os.chmod(tmp_path, 0o700)

    def test_secret_key_not_logged(self, tmp_path, caplog):
        """Test that actual secret key value is never logged."""
        import logging
        caplog.set_level(logging.DEBUG)

        manager = FlaskSecretManager(data_dir=str(tmp_path))
        secret_key = manager.get_secret_key()

        # Ensure the actual key is not in any log message
        for record in caplog.records:
            assert secret_key not in record.message
            if hasattr(record, 'args') and record.args:
                assert secret_key not in str(record.args)

    def test_environment_variable_whitespace(self, tmp_path, monkeypatch):
        """Test that environment variable handles whitespace."""
        env_key = "a" * 64
        monkeypatch.setenv("XAI_SECRET_KEY", f"  {env_key}  ")

        manager = FlaskSecretManager(data_dir=str(tmp_path))
        secret_key = manager.get_secret_key()

        # Should use the env var as-is (including whitespace)
        assert secret_key == f"  {env_key}  "

    def test_concurrent_access(self, tmp_path):
        """Test that multiple managers can access the same secret key."""
        import threading

        results = []

        def get_key():
            manager = FlaskSecretManager(data_dir=str(tmp_path))
            results.append(manager.get_secret_key())

        # Create multiple threads accessing the secret key
        threads = [threading.Thread(target=get_key) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All threads should get the same key
        assert len(results) == 5
        assert all(key == results[0] for key in results)
