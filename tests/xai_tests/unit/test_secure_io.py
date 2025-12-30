"""
Tests for secure I/O utilities.

Verifies that file operations use proper permissions to prevent
data leakage on multi-user systems.
"""

import json
import os
import stat
import tempfile
import pytest

from xai.utils.secure_io import (
    secure_write_file,
    secure_write_json,
    secure_create_directory,
    secure_atomic_write,
    secure_atomic_write_json,
    SECURE_FILE_MODE,
    SECURE_DIR_MODE,
)


class TestSecureWriteFile:
    """Test secure_write_file function."""

    def test_creates_file_with_secure_permissions(self, tmp_path):
        """Files should be created with 0o600 permissions."""
        test_file = tmp_path / "test.txt"
        secure_write_file(str(test_file), "test content")

        mode = os.stat(test_file).st_mode & 0o777
        assert mode == SECURE_FILE_MODE

    def test_writes_string_content(self, tmp_path):
        """String content should be written correctly."""
        test_file = tmp_path / "test.txt"
        content = "Hello, World!"
        secure_write_file(str(test_file), content)

        assert test_file.read_text() == content

    def test_writes_bytes_content(self, tmp_path):
        """Bytes content should be written correctly."""
        test_file = tmp_path / "test.bin"
        content = b"\x00\x01\x02\x03"
        secure_write_file(str(test_file), content)

        assert test_file.read_bytes() == content

    def test_overwrites_existing_file(self, tmp_path):
        """Should overwrite existing files with secure permissions."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("old content")
        os.chmod(test_file, 0o644)  # Insecure permissions

        secure_write_file(str(test_file), "new content")

        assert test_file.read_text() == "new content"
        mode = os.stat(test_file).st_mode & 0o777
        assert mode == SECURE_FILE_MODE

    def test_rejects_invalid_content_type(self, tmp_path):
        """Should reject non-string, non-bytes content."""
        test_file = tmp_path / "test.txt"
        with pytest.raises(TypeError):
            secure_write_file(str(test_file), 12345)


class TestSecureWriteJson:
    """Test secure_write_json function."""

    def test_creates_file_with_secure_permissions(self, tmp_path):
        """JSON files should be created with 0o600 permissions."""
        test_file = tmp_path / "test.json"
        secure_write_json(str(test_file), {"key": "value"})

        mode = os.stat(test_file).st_mode & 0o777
        assert mode == SECURE_FILE_MODE

    def test_writes_valid_json(self, tmp_path):
        """JSON should be valid and readable."""
        test_file = tmp_path / "test.json"
        data = {"name": "test", "value": 42, "nested": {"a": 1}}
        secure_write_json(str(test_file), data)

        with open(test_file) as f:
            loaded = json.load(f)
        assert loaded == data


class TestSecureCreateDirectory:
    """Test secure_create_directory function."""

    def test_creates_directory_with_secure_permissions(self, tmp_path):
        """Directories should be created with 0o700 permissions."""
        test_dir = tmp_path / "secure_dir"
        secure_create_directory(str(test_dir))

        mode = os.stat(test_dir).st_mode & 0o777
        assert mode == SECURE_DIR_MODE

    def test_creates_nested_directories(self, tmp_path):
        """Should create parent directories as needed."""
        test_dir = tmp_path / "a" / "b" / "c"
        secure_create_directory(str(test_dir))

        assert test_dir.is_dir()


class TestSecureAtomicWrite:
    """Test secure_atomic_write function."""

    def test_creates_file_with_secure_permissions(self, tmp_path):
        """Atomic writes should use secure permissions."""
        test_file = tmp_path / "test.txt"
        secure_atomic_write(str(test_file), "test content")

        mode = os.stat(test_file).st_mode & 0o777
        assert mode == SECURE_FILE_MODE

    def test_atomic_write_is_all_or_nothing(self, tmp_path):
        """If write fails, original content should remain."""
        test_file = tmp_path / "test.txt"
        original_content = "original"
        test_file.write_text(original_content)

        # This should fail because we're passing invalid content type
        with pytest.raises(TypeError):
            secure_atomic_write(str(test_file), {"invalid": "type"})

        # Original content should still be there
        assert test_file.read_text() == original_content

    def test_creates_parent_directories(self, tmp_path):
        """Should create parent directories if needed."""
        test_file = tmp_path / "subdir" / "test.txt"
        secure_atomic_write(str(test_file), "content")

        assert test_file.exists()
        assert test_file.read_text() == "content"


class TestSecureAtomicWriteJson:
    """Test secure_atomic_write_json function."""

    def test_creates_file_with_secure_permissions(self, tmp_path):
        """Atomic JSON writes should use secure permissions."""
        test_file = tmp_path / "test.json"
        secure_atomic_write_json(str(test_file), {"key": "value"})

        mode = os.stat(test_file).st_mode & 0o777
        assert mode == SECURE_FILE_MODE

    def test_writes_valid_json(self, tmp_path):
        """JSON should be valid and readable."""
        test_file = tmp_path / "test.json"
        data = {"test": [1, 2, 3]}
        secure_atomic_write_json(str(test_file), data)

        with open(test_file) as f:
            loaded = json.load(f)
        assert loaded == data


class TestPermissionConstants:
    """Test permission constants."""

    def test_secure_file_mode_is_owner_only(self):
        """SECURE_FILE_MODE should be owner read/write only."""
        assert SECURE_FILE_MODE == 0o600

    def test_secure_dir_mode_is_owner_only(self):
        """SECURE_DIR_MODE should be owner read/write/execute only."""
        assert SECURE_DIR_MODE == 0o700
