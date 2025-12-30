"""
Tests for path traversal prevention in blockchain storage.

These tests verify that the BlockchainStorage class properly prevents
path traversal attacks when processing filenames from stored data.
"""

import json
import os
import tempfile
import pytest
from xai.core.chain.blockchain_storage import BlockchainStorage, PathTraversalError


class TestPathTraversalPrevention:
    """Test path traversal prevention in BlockchainStorage."""

    @pytest.fixture
    def storage(self, tmp_path):
        """Create a BlockchainStorage instance with temporary directory."""
        storage = BlockchainStorage(str(tmp_path), enable_index=False)
        return storage

    def test_validate_safe_path_accepts_valid_filename(self, storage):
        """Valid filenames should be accepted."""
        result = storage._validate_safe_path(storage.data_dir, "test.json")
        assert result.endswith("test.json")
        assert os.path.dirname(result) == os.path.normpath(storage.data_dir)

    def test_validate_safe_path_accepts_subdirectory(self, storage):
        """Valid subdirectory paths should be accepted."""
        result = storage._validate_safe_path(storage.data_dir, "blocks/block_0.json")
        assert "blocks" in result
        assert result.endswith("block_0.json")

    def test_validate_safe_path_rejects_parent_traversal(self, storage):
        """Paths with ../ should be rejected."""
        with pytest.raises(PathTraversalError):
            storage._validate_safe_path(storage.data_dir, "../etc/passwd")

    def test_validate_safe_path_rejects_deep_traversal(self, storage):
        """Deep path traversal attempts should be rejected."""
        with pytest.raises(PathTraversalError):
            storage._validate_safe_path(storage.data_dir, "../../../../../../etc/passwd")

    def test_validate_safe_path_rejects_mixed_traversal(self, storage):
        """Mixed valid and traversal paths should be rejected."""
        with pytest.raises(PathTraversalError):
            storage._validate_safe_path(storage.data_dir, "blocks/../../../etc/passwd")

    def test_validate_safe_path_rejects_absolute_path(self, storage):
        """Absolute paths outside base should be rejected."""
        with pytest.raises(PathTraversalError):
            storage._validate_safe_path(storage.data_dir, "/etc/passwd")

    def test_verify_integrity_rejects_traversal_in_checksum(self, storage):
        """verify_integrity should return False on path traversal attempt."""
        # Create a malicious checksum file with path traversal
        checksum_file = os.path.join(storage.data_dir, "checksum.json")
        malicious_checksums = {
            "../../../etc/passwd": "abc123",
            "valid_file.json": "def456"
        }

        with open(checksum_file, "w") as f:
            json.dump(malicious_checksums, f)

        # verify_integrity should return False (integrity failure)
        result = storage.verify_integrity()
        assert result is False

    def test_verify_integrity_accepts_valid_checksums(self, storage):
        """verify_integrity should work with valid file paths."""
        # Create a valid file
        valid_file = os.path.join(storage.data_dir, "test_file.json")
        with open(valid_file, "w") as f:
            f.write('{"test": "data"}')

        # Calculate checksum
        checksum = storage._calculate_checksum(valid_file)

        # Create valid checksum file
        checksum_file = os.path.join(storage.data_dir, "checksum.json")
        with open(checksum_file, "w") as f:
            json.dump({"test_file.json": checksum}, f)

        # verify_integrity should pass
        result = storage.verify_integrity()
        assert result is True

    def test_validate_safe_path_handles_encoded_traversal(self, storage):
        """URL-encoded paths are treated as literal filenames (not decoded)."""
        # Python's os.path doesn't URL-decode, so %2F is literal characters
        # This is safe - the path stays within base_dir with a weird filename
        result = storage._validate_safe_path(storage.data_dir, "..%2F..%2Fetc%2Fpasswd")
        assert os.path.basename(result) == "..%2F..%2Fetc%2Fpasswd"

    def test_validate_safe_path_handles_backslash_on_unix(self, storage):
        """Backslash traversal should be handled properly on Unix."""
        # On Unix, backslashes are valid in filenames but shouldn't allow traversal
        # This test ensures consistency
        result = storage._validate_safe_path(storage.data_dir, "test\\file.json")
        assert result is not None  # Should accept as literal backslash in filename


class TestPathTraversalLogging:
    """Test that path traversal attempts are logged appropriately."""

    @pytest.fixture
    def storage(self, tmp_path):
        """Create a BlockchainStorage instance with temporary directory."""
        return BlockchainStorage(str(tmp_path), enable_index=False)

    def test_traversal_attempt_raises_with_message(self, storage):
        """PathTraversalError should have descriptive message."""
        with pytest.raises(PathTraversalError) as exc_info:
            storage._validate_safe_path(storage.data_dir, "../secret")

        assert "path traversal" in str(exc_info.value).lower()
