"""
Comprehensive unit tests for BlockchainWAL (Write-Ahead Log)

Tests the Write-Ahead Log functionality for chain reorganization crash recovery.
The WAL is a critical infrastructure component ensuring blockchain state consistency.

Test coverage includes:
- WAL initialization and setup
- write_reorg_wal() for starting a reorg
- commit_reorg_wal() for completing successful reorgs
- rollback_reorg_wal() for reverting failed reorgs
- recover_from_incomplete_reorg() for crash recovery
- Edge cases: corrupted files, concurrent access, permission errors
- Error handling paths for all operations
"""

from __future__ import annotations

import json
import os
import stat
import tempfile
import threading
import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, Mock, patch, mock_open

import pytest

from xai.core.chain.blockchain_wal import BlockchainWAL


class MockLogger:
    """Mock logger for testing without file system logging."""

    def __init__(self):
        self.info_calls = []
        self.warning_calls = []
        self.error_calls = []
        self.debug_calls = []

    def info(self, msg, *args, **kwargs):
        self.info_calls.append((msg, args, kwargs))

    def warning(self, msg, *args, **kwargs):
        self.warning_calls.append((msg, args, kwargs))

    def error(self, msg, *args, **kwargs):
        self.error_calls.append((msg, args, kwargs))

    def debug(self, msg, *args, **kwargs):
        self.debug_calls.append((msg, args, kwargs))


class MockBlockchain:
    """Mock Blockchain for testing BlockchainWAL in isolation."""

    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.reorg_wal_path = os.path.join(data_dir, "reorg.wal")
        self.logger = MockLogger()


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test data."""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    # Cleanup
    import shutil
    if os.path.exists(temp_path):
        shutil.rmtree(temp_path)


@pytest.fixture
def mock_blockchain(temp_dir):
    """Create a mock blockchain instance."""
    return MockBlockchain(temp_dir)


@pytest.fixture
def wal(mock_blockchain):
    """Create a BlockchainWAL instance for testing."""
    return BlockchainWAL(mock_blockchain)


class TestBlockchainWALInitialization:
    """Test BlockchainWAL initialization."""

    def test_init_stores_blockchain_reference(self, mock_blockchain):
        """WAL should store reference to blockchain."""
        wal = BlockchainWAL(mock_blockchain)
        assert wal.blockchain is mock_blockchain

    def test_init_with_none_blockchain(self):
        """WAL should handle None blockchain (edge case)."""
        wal = BlockchainWAL(None)
        assert wal.blockchain is None


class TestWriteReorgWAL:
    """Test write_reorg_wal() method."""

    def test_write_reorg_wal_basic(self, wal, mock_blockchain):
        """write_reorg_wal should create valid WAL entry."""
        entry = wal.write_reorg_wal(
            old_tip="a" * 64,
            new_tip="b" * 64,
            fork_point=100
        )

        assert entry["type"] == "REORG_BEGIN"
        assert entry["old_tip"] == "a" * 64
        assert entry["new_tip"] == "b" * 64
        assert entry["fork_point"] == 100
        assert entry["status"] == "in_progress"
        assert "timestamp" in entry
        assert entry["timestamp"] > 0

    def test_write_reorg_wal_persists_to_disk(self, wal, mock_blockchain):
        """write_reorg_wal should persist entry to disk."""
        wal.write_reorg_wal(
            old_tip="a" * 64,
            new_tip="b" * 64,
            fork_point=100
        )

        assert os.path.exists(mock_blockchain.reorg_wal_path)

        with open(mock_blockchain.reorg_wal_path, "r") as f:
            saved_entry = json.load(f)

        assert saved_entry["type"] == "REORG_BEGIN"
        assert saved_entry["status"] == "in_progress"

    def test_write_reorg_wal_with_none_values(self, wal, mock_blockchain):
        """write_reorg_wal should handle None values gracefully."""
        entry = wal.write_reorg_wal(
            old_tip=None,
            new_tip=None,
            fork_point=None
        )

        assert entry["old_tip"] is None
        assert entry["new_tip"] is None
        assert entry["fork_point"] is None

    def test_write_reorg_wal_overwrites_existing(self, wal, mock_blockchain):
        """write_reorg_wal should overwrite existing WAL file."""
        # Write first entry
        wal.write_reorg_wal(
            old_tip="a" * 64,
            new_tip="b" * 64,
            fork_point=100
        )

        # Write second entry
        wal.write_reorg_wal(
            old_tip="c" * 64,
            new_tip="d" * 64,
            fork_point=200
        )

        with open(mock_blockchain.reorg_wal_path, "r") as f:
            saved_entry = json.load(f)

        assert saved_entry["old_tip"] == "c" * 64
        assert saved_entry["fork_point"] == 200

    def test_write_reorg_wal_logs_success(self, wal, mock_blockchain):
        """write_reorg_wal should log on successful write."""
        wal.write_reorg_wal(
            old_tip="a" * 64,
            new_tip="b" * 64,
            fork_point=100
        )

        assert len(mock_blockchain.logger.info_calls) > 0
        # Check logged message contains relevant info
        info_call = mock_blockchain.logger.info_calls[0]
        assert "WAL" in info_call[0]

    def test_write_reorg_wal_handles_permission_error(self, wal, mock_blockchain):
        """write_reorg_wal should handle permission errors gracefully."""
        # Make directory read-only (Unix-like systems)
        if os.name != 'nt':  # Skip on Windows
            os.chmod(mock_blockchain.data_dir, stat.S_IRUSR | stat.S_IXUSR)

            try:
                entry = wal.write_reorg_wal(
                    old_tip="a" * 64,
                    new_tip="b" * 64,
                    fork_point=100
                )

                # Should still return entry
                assert entry["type"] == "REORG_BEGIN"
                # Should log error
                assert len(mock_blockchain.logger.error_calls) > 0
            finally:
                # Restore permissions for cleanup
                os.chmod(mock_blockchain.data_dir, stat.S_IRWXU)

    def test_write_reorg_wal_handles_invalid_path(self):
        """write_reorg_wal should handle invalid file paths."""
        mock_bc = Mock()
        mock_bc.reorg_wal_path = "/nonexistent/directory/reorg.wal"
        mock_bc.logger = MockLogger()

        wal = BlockchainWAL(mock_bc)
        entry = wal.write_reorg_wal(
            old_tip="a" * 64,
            new_tip="b" * 64,
            fork_point=100
        )

        # Should still return entry (logged error internally)
        assert entry["type"] == "REORG_BEGIN"
        assert len(mock_bc.logger.error_calls) > 0


class TestCommitReorgWAL:
    """Test commit_reorg_wal() method."""

    def test_commit_reorg_wal_updates_status(self, wal, mock_blockchain):
        """commit_reorg_wal should update entry status to committed."""
        entry = wal.write_reorg_wal(
            old_tip="a" * 64,
            new_tip="b" * 64,
            fork_point=100
        )

        wal.commit_reorg_wal(entry)

        assert entry["status"] == "committed"
        assert "commit_timestamp" in entry
        assert entry["commit_timestamp"] > 0

    def test_commit_reorg_wal_removes_wal_file(self, wal, mock_blockchain):
        """commit_reorg_wal should remove WAL file after successful commit."""
        entry = wal.write_reorg_wal(
            old_tip="a" * 64,
            new_tip="b" * 64,
            fork_point=100
        )

        wal.commit_reorg_wal(entry)

        # WAL file should be removed after commit
        assert not os.path.exists(mock_blockchain.reorg_wal_path)

    def test_commit_reorg_wal_logs_success(self, wal, mock_blockchain):
        """commit_reorg_wal should log successful commit."""
        entry = wal.write_reorg_wal(
            old_tip="a" * 64,
            new_tip="b" * 64,
            fork_point=100
        )

        initial_info_count = len(mock_blockchain.logger.info_calls)
        wal.commit_reorg_wal(entry)

        # Should have logged additional info
        assert len(mock_blockchain.logger.info_calls) > initial_info_count

    def test_commit_reorg_wal_with_empty_entry(self, wal, mock_blockchain):
        """commit_reorg_wal should handle empty entry dict."""
        entry = {}

        wal.commit_reorg_wal(entry)

        assert entry["status"] == "committed"
        assert "commit_timestamp" in entry

    def test_commit_reorg_wal_handles_file_removal_error(self, wal, mock_blockchain):
        """commit_reorg_wal should handle file removal errors gracefully."""
        entry = wal.write_reorg_wal(
            old_tip="a" * 64,
            new_tip="b" * 64,
            fork_point=100
        )

        # Remove WAL file before commit (simulate race condition)
        os.remove(mock_blockchain.reorg_wal_path)

        # Should not raise exception
        wal.commit_reorg_wal(entry)

        assert entry["status"] == "committed"

    def test_commit_reorg_wal_handles_write_error(self):
        """commit_reorg_wal should handle write errors."""
        mock_bc = Mock()
        mock_bc.reorg_wal_path = "/nonexistent/path/reorg.wal"
        mock_bc.logger = MockLogger()

        wal = BlockchainWAL(mock_bc)
        entry = {"status": "in_progress"}

        wal.commit_reorg_wal(entry)

        # Should log error but not crash
        assert len(mock_bc.logger.error_calls) > 0


class TestRollbackReorgWAL:
    """Test rollback_reorg_wal() method."""

    def test_rollback_reorg_wal_updates_status(self, wal, mock_blockchain):
        """rollback_reorg_wal should update entry status to rolled_back."""
        entry = wal.write_reorg_wal(
            old_tip="a" * 64,
            new_tip="b" * 64,
            fork_point=100
        )

        wal.rollback_reorg_wal(entry)

        assert entry["status"] == "rolled_back"
        assert "rollback_timestamp" in entry
        assert entry["rollback_timestamp"] > 0

    def test_rollback_reorg_wal_removes_wal_file(self, wal, mock_blockchain):
        """rollback_reorg_wal should remove WAL file after rollback."""
        entry = wal.write_reorg_wal(
            old_tip="a" * 64,
            new_tip="b" * 64,
            fork_point=100
        )

        wal.rollback_reorg_wal(entry)

        assert not os.path.exists(mock_blockchain.reorg_wal_path)

    def test_rollback_reorg_wal_logs_success(self, wal, mock_blockchain):
        """rollback_reorg_wal should log successful rollback."""
        entry = wal.write_reorg_wal(
            old_tip="a" * 64,
            new_tip="b" * 64,
            fork_point=100
        )

        initial_info_count = len(mock_blockchain.logger.info_calls)
        wal.rollback_reorg_wal(entry)

        assert len(mock_blockchain.logger.info_calls) > initial_info_count

    def test_rollback_reorg_wal_with_empty_entry(self, wal, mock_blockchain):
        """rollback_reorg_wal should handle empty entry dict."""
        entry = {}

        wal.rollback_reorg_wal(entry)

        assert entry["status"] == "rolled_back"

    def test_rollback_reorg_wal_handles_file_error(self):
        """rollback_reorg_wal should handle file errors gracefully."""
        mock_bc = Mock()
        mock_bc.reorg_wal_path = "/nonexistent/path/reorg.wal"
        mock_bc.logger = MockLogger()

        wal = BlockchainWAL(mock_bc)
        entry = {"status": "in_progress"}

        wal.rollback_reorg_wal(entry)

        assert len(mock_bc.logger.error_calls) > 0


class TestRecoverFromIncompleteReorg:
    """Test recover_from_incomplete_reorg() method."""

    def test_recover_no_wal_file(self, wal, mock_blockchain):
        """recover_from_incomplete_reorg should do nothing if no WAL file exists."""
        # No WAL file exists
        assert not os.path.exists(mock_blockchain.reorg_wal_path)

        # Should complete without error
        wal.recover_from_incomplete_reorg()

        # No warnings should be logged
        assert len(mock_blockchain.logger.warning_calls) == 0

    def test_recover_from_in_progress_reorg(self, wal, mock_blockchain):
        """recover_from_incomplete_reorg should detect and handle in_progress status."""
        # Create WAL file with in_progress status
        wal_entry = {
            "type": "REORG_BEGIN",
            "old_tip": "a" * 64,
            "new_tip": "b" * 64,
            "fork_point": 100,
            "timestamp": time.time(),
            "status": "in_progress"
        }

        with open(mock_blockchain.reorg_wal_path, "w") as f:
            json.dump(wal_entry, f)

        wal.recover_from_incomplete_reorg()

        # Should log warning about incomplete reorg
        assert len(mock_blockchain.logger.warning_calls) > 0

        # WAL file should be removed
        assert not os.path.exists(mock_blockchain.reorg_wal_path)

    def test_recover_removes_committed_wal(self, wal, mock_blockchain):
        """recover_from_incomplete_reorg should remove stale committed WAL."""
        wal_entry = {
            "type": "REORG_BEGIN",
            "status": "committed",
            "commit_timestamp": time.time()
        }

        with open(mock_blockchain.reorg_wal_path, "w") as f:
            json.dump(wal_entry, f)

        wal.recover_from_incomplete_reorg()

        # Should remove stale WAL file
        assert not os.path.exists(mock_blockchain.reorg_wal_path)

        # Should log debug message, not warning
        assert len(mock_blockchain.logger.warning_calls) == 0

    def test_recover_removes_rolled_back_wal(self, wal, mock_blockchain):
        """recover_from_incomplete_reorg should remove stale rolled_back WAL."""
        wal_entry = {
            "type": "REORG_BEGIN",
            "status": "rolled_back",
            "rollback_timestamp": time.time()
        }

        with open(mock_blockchain.reorg_wal_path, "w") as f:
            json.dump(wal_entry, f)

        wal.recover_from_incomplete_reorg()

        assert not os.path.exists(mock_blockchain.reorg_wal_path)

    def test_recover_handles_corrupted_json(self, wal, mock_blockchain):
        """recover_from_incomplete_reorg should handle corrupted JSON."""
        # Write corrupted JSON
        with open(mock_blockchain.reorg_wal_path, "w") as f:
            f.write("{invalid json content")

        wal.recover_from_incomplete_reorg()

        # Should log error
        assert len(mock_blockchain.logger.error_calls) > 0

    def test_recover_handles_empty_file(self, wal, mock_blockchain):
        """recover_from_incomplete_reorg should handle empty WAL file."""
        # Create empty file
        with open(mock_blockchain.reorg_wal_path, "w") as f:
            pass

        wal.recover_from_incomplete_reorg()

        # Should log error due to empty JSON
        assert len(mock_blockchain.logger.error_calls) > 0

    def test_recover_handles_missing_status_key(self, wal, mock_blockchain):
        """recover_from_incomplete_reorg should handle WAL entry missing status key."""
        wal_entry = {
            "type": "REORG_BEGIN",
            "old_tip": "a" * 64
            # No "status" key
        }

        with open(mock_blockchain.reorg_wal_path, "w") as f:
            json.dump(wal_entry, f)

        wal.recover_from_incomplete_reorg()

        # Should handle gracefully (status will be None, not "in_progress")
        # WAL should be removed as stale
        assert not os.path.exists(mock_blockchain.reorg_wal_path)

    def test_recover_handles_read_permission_error(self, wal, mock_blockchain):
        """recover_from_incomplete_reorg should handle read permission errors."""
        # Create WAL file
        wal_entry = {"status": "in_progress"}
        with open(mock_blockchain.reorg_wal_path, "w") as f:
            json.dump(wal_entry, f)

        if os.name != 'nt':  # Skip on Windows
            # Make file unreadable
            os.chmod(mock_blockchain.reorg_wal_path, 0)

            try:
                wal.recover_from_incomplete_reorg()
                # Should log error
                assert len(mock_blockchain.logger.error_calls) > 0
            finally:
                # Restore permissions for cleanup
                os.chmod(mock_blockchain.reorg_wal_path, stat.S_IRWXU)

    def test_recover_logs_detailed_info_for_incomplete_reorg(self, wal, mock_blockchain):
        """recover_from_incomplete_reorg should log detailed info for crashed reorg."""
        wal_entry = {
            "type": "REORG_BEGIN",
            "old_tip": "oldtip123" + "0" * 55,
            "new_tip": "newtip456" + "0" * 55,
            "fork_point": 999,
            "timestamp": 1234567890.0,
            "status": "in_progress"
        }

        with open(mock_blockchain.reorg_wal_path, "w") as f:
            json.dump(wal_entry, f)

        wal.recover_from_incomplete_reorg()

        # Warning should contain reorg details
        assert len(mock_blockchain.logger.warning_calls) > 0
        warning_call = mock_blockchain.logger.warning_calls[0]
        # The extra dict should contain the details
        assert "extra" in warning_call[2]
        extra = warning_call[2]["extra"]
        assert extra.get("fork_point") == 999


class TestCrashRecoveryScenarios:
    """Test realistic crash recovery scenarios."""

    def test_crash_before_reorg_applied(self, wal, mock_blockchain):
        """Simulate crash immediately after WAL write, before reorg."""
        # Simulate: WAL written, then crash
        entry = wal.write_reorg_wal(
            old_tip="a" * 64,
            new_tip="b" * 64,
            fork_point=100
        )

        # Verify WAL was written
        assert os.path.exists(mock_blockchain.reorg_wal_path)

        # On restart, recover
        wal.recover_from_incomplete_reorg()

        # WAL should be cleared for state rebuild
        assert not os.path.exists(mock_blockchain.reorg_wal_path)
        assert len(mock_blockchain.logger.warning_calls) > 0

    def test_crash_during_reorg_partially_applied(self, wal, mock_blockchain):
        """Simulate crash with reorg partially applied."""
        # Start reorg
        entry = wal.write_reorg_wal(
            old_tip="a" * 64,
            new_tip="b" * 64,
            fork_point=100
        )

        # Simulate partial reorg work (WAL still exists with in_progress)
        # Then crash...

        # On restart
        wal.recover_from_incomplete_reorg()

        # Should detect and handle
        assert not os.path.exists(mock_blockchain.reorg_wal_path)

    def test_successful_reorg_no_recovery_needed(self, wal, mock_blockchain):
        """Successful reorg should leave no WAL for recovery."""
        entry = wal.write_reorg_wal(
            old_tip="a" * 64,
            new_tip="b" * 64,
            fork_point=100
        )

        # Complete the reorg successfully
        wal.commit_reorg_wal(entry)

        # On restart, no recovery needed
        wal.recover_from_incomplete_reorg()

        # No warnings
        assert len(mock_blockchain.logger.warning_calls) == 0

    def test_failed_reorg_with_rollback_no_recovery_needed(self, wal, mock_blockchain):
        """Rolled back reorg should leave no WAL for recovery."""
        entry = wal.write_reorg_wal(
            old_tip="a" * 64,
            new_tip="b" * 64,
            fork_point=100
        )

        # Reorg failed, rollback
        wal.rollback_reorg_wal(entry)

        # On restart, no recovery needed
        wal.recover_from_incomplete_reorg()

        assert len(mock_blockchain.logger.warning_calls) == 0


class TestConcurrentAccess:
    """Test concurrent access scenarios."""

    def test_concurrent_write_operations(self, mock_blockchain):
        """Test multiple threads writing to WAL."""
        wal = BlockchainWAL(mock_blockchain)
        results = []
        errors = []

        def write_wal(thread_id):
            try:
                entry = wal.write_reorg_wal(
                    old_tip=f"{thread_id}" + "0" * 63,
                    new_tip=f"{thread_id}" + "1" * 63,
                    fork_point=thread_id
                )
                results.append(entry)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=write_wal, args=(i,)) for i in range(5)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All writes should succeed (last one wins)
        assert len(errors) == 0
        assert len(results) == 5

        # File should exist with valid content
        with open(mock_blockchain.reorg_wal_path, "r") as f:
            final_entry = json.load(f)
        assert final_entry["type"] == "REORG_BEGIN"


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_wal_with_unicode_in_hashes(self, wal, mock_blockchain):
        """WAL should handle standard hex hashes only."""
        # Standard hex hashes (no unicode issues)
        entry = wal.write_reorg_wal(
            old_tip="abcdef1234567890" * 4,
            new_tip="fedcba0987654321" * 4,
            fork_point=0
        )

        assert entry is not None

    def test_wal_with_large_fork_point(self, wal, mock_blockchain):
        """WAL should handle very large fork point values."""
        entry = wal.write_reorg_wal(
            old_tip="a" * 64,
            new_tip="b" * 64,
            fork_point=2**31 - 1  # Max 32-bit signed int
        )

        assert entry["fork_point"] == 2**31 - 1

        # Verify it persists correctly
        with open(mock_blockchain.reorg_wal_path, "r") as f:
            saved_entry = json.load(f)
        assert saved_entry["fork_point"] == 2**31 - 1

    def test_wal_with_zero_fork_point(self, wal, mock_blockchain):
        """WAL should handle fork point of 0 (fork at genesis)."""
        entry = wal.write_reorg_wal(
            old_tip="a" * 64,
            new_tip="b" * 64,
            fork_point=0
        )

        assert entry["fork_point"] == 0

    def test_wal_with_negative_fork_point(self, wal, mock_blockchain):
        """WAL should handle negative fork point (edge case)."""
        # This shouldn't happen in practice, but WAL shouldn't crash
        entry = wal.write_reorg_wal(
            old_tip="a" * 64,
            new_tip="b" * 64,
            fork_point=-1
        )

        assert entry["fork_point"] == -1

    def test_rapid_write_commit_cycles(self, wal, mock_blockchain):
        """Test rapid write/commit cycles."""
        for i in range(10):
            entry = wal.write_reorg_wal(
                old_tip=f"{i:064x}",
                new_tip=f"{i+100:064x}",
                fork_point=i
            )
            wal.commit_reorg_wal(entry)

        # WAL file should not exist after final commit
        assert not os.path.exists(mock_blockchain.reorg_wal_path)

    def test_write_with_special_timestamp(self, wal, mock_blockchain):
        """WAL should handle edge case timestamps."""
        with patch('time.time', return_value=0.0):
            entry = wal.write_reorg_wal(
                old_tip="a" * 64,
                new_tip="b" * 64,
                fork_point=100
            )
            assert entry["timestamp"] == 0.0

    def test_commit_without_prior_write(self, wal, mock_blockchain):
        """commit_reorg_wal should work even without prior write_reorg_wal."""
        entry = {
            "type": "REORG_BEGIN",
            "old_tip": "a" * 64,
            "new_tip": "b" * 64,
            "fork_point": 100,
            "status": "in_progress"
        }

        # Directly commit (no WAL file exists)
        wal.commit_reorg_wal(entry)

        assert entry["status"] == "committed"

    def test_rollback_without_prior_write(self, wal, mock_blockchain):
        """rollback_reorg_wal should work even without prior write_reorg_wal."""
        entry = {
            "type": "REORG_BEGIN",
            "status": "in_progress"
        }

        wal.rollback_reorg_wal(entry)

        assert entry["status"] == "rolled_back"


class TestFsyncBehavior:
    """Test that WAL properly syncs to disk."""

    def test_write_uses_fsync(self, mock_blockchain):
        """write_reorg_wal should call fsync for durability."""
        wal = BlockchainWAL(mock_blockchain)

        with patch('os.fsync') as mock_fsync:
            wal.write_reorg_wal(
                old_tip="a" * 64,
                new_tip="b" * 64,
                fork_point=100
            )

            # fsync should have been called
            assert mock_fsync.called

    def test_commit_uses_fsync(self, mock_blockchain):
        """commit_reorg_wal should call fsync for durability."""
        wal = BlockchainWAL(mock_blockchain)

        entry = wal.write_reorg_wal(
            old_tip="a" * 64,
            new_tip="b" * 64,
            fork_point=100
        )

        with patch('os.fsync') as mock_fsync:
            wal.commit_reorg_wal(entry)
            # fsync should have been called during commit write
            assert mock_fsync.called

    def test_rollback_uses_fsync(self, mock_blockchain):
        """rollback_reorg_wal should call fsync for durability."""
        wal = BlockchainWAL(mock_blockchain)

        entry = wal.write_reorg_wal(
            old_tip="a" * 64,
            new_tip="b" * 64,
            fork_point=100
        )

        with patch('os.fsync') as mock_fsync:
            wal.rollback_reorg_wal(entry)
            # fsync should have been called during rollback write
            assert mock_fsync.called


class TestWALIntegrity:
    """Test WAL data integrity."""

    def test_wal_json_formatting(self, wal, mock_blockchain):
        """WAL file should be valid, readable JSON."""
        entry = wal.write_reorg_wal(
            old_tip="a" * 64,
            new_tip="b" * 64,
            fork_point=100
        )

        with open(mock_blockchain.reorg_wal_path, "r") as f:
            content = f.read()

        # Should be valid JSON
        parsed = json.loads(content)
        assert isinstance(parsed, dict)

        # Should be indented for readability
        assert "\n" in content  # Indented JSON has newlines

    def test_wal_contains_all_required_fields(self, wal, mock_blockchain):
        """WAL entry should contain all required fields."""
        entry = wal.write_reorg_wal(
            old_tip="a" * 64,
            new_tip="b" * 64,
            fork_point=100
        )

        required_fields = ["type", "old_tip", "new_tip", "fork_point", "timestamp", "status"]
        for field in required_fields:
            assert field in entry, f"Missing required field: {field}"

    def test_wal_timestamp_is_recent(self, wal, mock_blockchain):
        """WAL timestamp should be recent (within 1 second)."""
        before = time.time()
        entry = wal.write_reorg_wal(
            old_tip="a" * 64,
            new_tip="b" * 64,
            fork_point=100
        )
        after = time.time()

        assert before <= entry["timestamp"] <= after


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
