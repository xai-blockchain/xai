"""Tests for blockchain_persistence.py - comprehensive storage and recovery testing."""

import json
import os
import time

import pytest

from xai.core.chain.blockchain_persistence import BlockchainStorage, BlockchainStorageConfig


class TestBlockchainStorageBasic:
    """Basic save/load operations."""

    def test_save_and_load_round_trip_creates_checkpoint(self, tmp_path):
        storage = BlockchainStorage(data_dir=tmp_path.as_posix())
        data = {"chain": [1] * BlockchainStorageConfig.CHECKPOINT_INTERVAL}

        success, msg = storage.save_to_disk(data)
        assert success
        assert "checksum" in msg

        checkpoints = list((tmp_path / "checkpoints").glob("checkpoint_*.json"))
        assert checkpoints, "checkpoint should be created at interval height"

        loaded_success, loaded_data, _ = storage.load_from_disk()
        assert loaded_success
        assert loaded_data == data

    def test_save_without_backup(self, tmp_path):
        storage = BlockchainStorage(data_dir=tmp_path.as_posix())
        data = {"chain": [1, 2, 3]}

        success, msg = storage.save_to_disk(data, create_backup=False)
        assert success
        assert "saved successfully" in msg

        backups = list((tmp_path / "backups").glob("blockchain_backup_*.json"))
        assert len(backups) == 0

    def test_load_when_file_not_exists(self, tmp_path):
        storage = BlockchainStorage(data_dir=tmp_path.as_posix())

        success, data, msg = storage.load_from_disk()
        assert not success
        assert data is None
        assert "No blockchain file found" in msg

    def test_simple_save_load(self, tmp_path):
        storage = BlockchainStorage(data_dir=tmp_path.as_posix())
        data = {"chain": [{"block": 1}, {"block": 2}], "utxo": {}}

        success, _ = storage.save_to_disk(data, create_backup=False)
        assert success

        loaded_success, loaded_data, _ = storage.load_from_disk()
        assert loaded_success
        assert loaded_data == data


class TestChecksumOperations:
    """Checksum calculation and verification."""

    def test_calculate_checksum_deterministic(self, tmp_path):
        storage = BlockchainStorage(data_dir=tmp_path.as_posix())

        checksum1 = storage._calculate_checksum("test data")
        checksum2 = storage._calculate_checksum("test data")
        assert checksum1 == checksum2

    def test_calculate_checksum_different_data(self, tmp_path):
        storage = BlockchainStorage(data_dir=tmp_path.as_posix())

        checksum1 = storage._calculate_checksum("data1")
        checksum2 = storage._calculate_checksum("data2")
        assert checksum1 != checksum2

    def test_verify_checksum_valid(self, tmp_path):
        storage = BlockchainStorage(data_dir=tmp_path.as_posix())
        data = "test data"
        checksum = storage._calculate_checksum(data)

        assert storage._verify_checksum(data, checksum)

    def test_verify_checksum_invalid(self, tmp_path):
        storage = BlockchainStorage(data_dir=tmp_path.as_posix())

        assert not storage._verify_checksum("data", "wrongchecksum")


class TestRecovery:
    """Recovery from corrupted data."""

    def test_corrupted_main_file_recovers_from_backup(self, tmp_path):
        storage = BlockchainStorage(data_dir=tmp_path.as_posix())

        original = {"chain": [1, 2, 3]}
        updated = {"chain": [1, 2, 3, 4]}

        assert storage.save_to_disk(original)[0]
        assert storage.save_to_disk(updated, create_backup=True)[0]

        corrupted_package = {"metadata": {"checksum": "deadbeef"}, "blockchain": updated}
        (tmp_path / "blockchain.json").write_text(json.dumps(corrupted_package))

        success, recovered, msg = storage.load_from_disk()
        assert success
        assert recovered == original
        assert "Recovered" in msg

    def test_corrupted_json_triggers_recovery(self, tmp_path):
        storage = BlockchainStorage(data_dir=tmp_path.as_posix())
        data = {"chain": [1, 2]}

        assert storage.save_to_disk(data, create_backup=False)[0]
        assert storage.save_to_disk({"chain": [1, 2, 3]}, create_backup=True)[0]

        (tmp_path / "blockchain.json").write_text("{invalid json")

        success, recovered, msg = storage.load_from_disk()
        assert success
        assert recovered == data
        assert "Recovered" in msg

    def test_recovery_from_checkpoint(self, tmp_path):
        storage = BlockchainStorage(data_dir=tmp_path.as_posix())
        data = {"chain": [1] * BlockchainStorageConfig.CHECKPOINT_INTERVAL}

        assert storage.save_to_disk(data, create_backup=False)[0]

        backup_dir = tmp_path / "backups"
        for f in backup_dir.glob("*"):
            f.unlink()

        (tmp_path / "blockchain.json").write_text("{invalid}")

        success, recovered, msg = storage.load_from_disk()
        assert success
        assert recovered == data
        assert "checkpoint" in msg.lower() or "Recovered" in msg

    def test_recovery_fails_when_no_backup_or_checkpoint(self, tmp_path):
        storage = BlockchainStorage(data_dir=tmp_path.as_posix())
        data = {"chain": [1, 2]}

        assert storage.save_to_disk(data, create_backup=False)[0]

        (tmp_path / "blockchain.json").write_text("{invalid}")

        success, recovered, msg = storage.load_from_disk()
        assert not success
        assert recovered is None
        assert "failed" in msg.lower() or "Recovery" in msg


class TestBackupManagement:
    """Backup creation, listing, and cleanup."""

    def test_list_backups_empty(self, tmp_path):
        storage = BlockchainStorage(data_dir=tmp_path.as_posix())
        backups = storage.list_backups()
        assert backups == []

    def test_list_backups_with_data(self, tmp_path):
        storage = BlockchainStorage(data_dir=tmp_path.as_posix())

        assert storage.save_to_disk({"chain": [1]})[0]
        assert storage.save_to_disk({"chain": [1, 2]}, create_backup=True)[0]

        backups = storage.list_backups()
        assert len(backups) == 1
        assert "filename" in backups[0]
        assert "timestamp" in backups[0]

    def test_cleanup_old_backups(self, tmp_path):
        storage = BlockchainStorage(data_dir=tmp_path.as_posix())

        for i in range(BlockchainStorageConfig.MAX_BACKUPS + 3):
            backup_file = tmp_path / "backups" / f"blockchain_backup_2024010{i:02d}_120000.json"
            backup_file.write_text(json.dumps({"test": i}))
            time.sleep(0.01)

        storage._cleanup_old_backups()

        remaining = list((tmp_path / "backups").glob("blockchain_backup_*.json"))
        assert len(remaining) == BlockchainStorageConfig.MAX_BACKUPS

    def test_restore_from_backup(self, tmp_path):
        storage = BlockchainStorage(data_dir=tmp_path.as_posix())
        data = {"chain": [1, 2, 3]}

        assert storage.save_to_disk(data)[0]
        assert storage.save_to_disk({"chain": [1, 2, 3, 4]}, create_backup=True)[0]

        backups = storage.list_backups()
        assert len(backups) >= 1

        success, restored, msg = storage.restore_from_backup(backups[0]["filename"])
        assert success
        assert restored == data

    def test_restore_from_nonexistent_backup(self, tmp_path):
        storage = BlockchainStorage(data_dir=tmp_path.as_posix())

        success, data, msg = storage.restore_from_backup("nonexistent.json")
        assert not success
        assert data is None
        assert "not found" in msg


class TestCheckpointManagement:
    """Checkpoint creation and listing."""

    def test_list_checkpoints_empty(self, tmp_path):
        storage = BlockchainStorage(data_dir=tmp_path.as_posix())
        checkpoints = storage.list_checkpoints()
        assert checkpoints == []

    def test_list_checkpoints_with_data(self, tmp_path):
        storage = BlockchainStorage(data_dir=tmp_path.as_posix())
        data = {"chain": [1] * BlockchainStorageConfig.CHECKPOINT_INTERVAL}

        assert storage.save_to_disk(data)[0]

        checkpoints = storage.list_checkpoints()
        assert len(checkpoints) >= 1
        assert checkpoints[0]["block_height"] == BlockchainStorageConfig.CHECKPOINT_INTERVAL


class TestMetadataAndIntegrity:
    """Metadata access and integrity verification."""

    def test_get_metadata_when_no_file(self, tmp_path):
        storage = BlockchainStorage(data_dir=tmp_path.as_posix())
        metadata = storage.get_metadata()
        assert metadata is None

    def test_get_metadata_after_save(self, tmp_path):
        storage = BlockchainStorage(data_dir=tmp_path.as_posix())
        data = {"chain": [1, 2, 3]}

        assert storage.save_to_disk(data)[0]

        metadata = storage.get_metadata()
        assert metadata is not None
        assert "checksum" in metadata
        assert "block_height" in metadata
        assert metadata["block_height"] == 3

    def test_verify_integrity_valid(self, tmp_path):
        storage = BlockchainStorage(data_dir=tmp_path.as_posix())
        data = {"chain": [1, 2, 3]}

        assert storage.save_to_disk(data)[0]

        valid, msg = storage.verify_integrity()
        assert valid
        assert "verified" in msg.lower()

    def test_verify_integrity_no_file(self, tmp_path):
        storage = BlockchainStorage(data_dir=tmp_path.as_posix())

        valid, msg = storage.verify_integrity()
        assert not valid
        assert "not found" in msg

    def test_verify_integrity_corrupted(self, tmp_path):
        storage = BlockchainStorage(data_dir=tmp_path.as_posix())
        data = {"chain": [1, 2, 3]}

        assert storage.save_to_disk(data)[0]

        corrupted = {"metadata": {"checksum": "bad"}, "blockchain": data}
        (tmp_path / "blockchain.json").write_text(json.dumps(corrupted))

        valid, msg = storage.verify_integrity()
        assert not valid
        assert "failed" in msg.lower()


class TestAtomicWrite:
    """Atomic write operations."""

    def test_atomic_write_creates_no_temp_file(self, tmp_path):
        storage = BlockchainStorage(data_dir=tmp_path.as_posix())
        data = {"chain": [1, 2]}

        assert storage.save_to_disk(data)[0]

        temp_files = list(tmp_path.glob("*.tmp"))
        assert len(temp_files) == 0

    def test_directories_created_on_init(self, tmp_path):
        data_dir = tmp_path / "newdir"
        storage = BlockchainStorage(data_dir=data_dir.as_posix())

        assert data_dir.exists()
        assert (data_dir / "backups").exists()
        assert (data_dir / "checkpoints").exists()
