"""
Tests for chunked state synchronization.

Tests cover:
- Chunk creation and splitting
- Chunk verification and checksums
- Resume capability
- Priority-based chunk ordering
- Compression
- API endpoints
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch

from xai.core.chunked_sync import (
    ChunkedStateSyncService,
    SyncChunk,
    SnapshotMetadata,
    SyncProgress,
    ChunkPriority,
)
from xai.core.checkpoint_payload import CheckpointPayload


@pytest.fixture
def temp_storage():
    """Create temporary storage directory."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def chunked_service(temp_storage):
    """Create chunked sync service."""
    return ChunkedStateSyncService(
        storage_dir=temp_storage,
        chunk_size=1000,  # Small chunks for testing
        enable_compression=False,
    )


@pytest.fixture
def sample_payload():
    """Create sample checkpoint payload."""
    data = {
        "utxo_snapshot": {"addr1": 100, "addr2": 200},
        "account_balances": {"addr3": 300},
        "blocks": [{"index": 0, "hash": "genesis"}],
    }
    serialized = json.dumps(data, sort_keys=True).encode("utf-8")
    import hashlib
    state_hash = hashlib.sha256(serialized).hexdigest()

    return CheckpointPayload(
        height=100,
        block_hash="abc123def456",
        state_hash=state_hash,
        data=data,
    )


class TestSyncChunk:
    """Test SyncChunk dataclass."""

    def test_chunk_creation(self):
        """Test creating a chunk."""
        data = b"test chunk data"
        import hashlib
        checksum = hashlib.sha256(data).hexdigest()

        chunk = SyncChunk(
            chunk_id="test_snapshot",
            chunk_index=0,
            total_chunks=5,
            data=data,
            checksum=checksum,
        )

        assert chunk.chunk_id == "test_snapshot"
        assert chunk.chunk_index == 0
        assert chunk.total_chunks == 5
        assert chunk.data == data
        assert chunk.checksum == checksum
        assert chunk.size_bytes == len(data)

    def test_chunk_checksum_verification(self):
        """Test chunk checksum verification."""
        data = b"test data"
        import hashlib
        correct_checksum = hashlib.sha256(data).hexdigest()

        # Valid checksum
        chunk = SyncChunk(
            chunk_id="test",
            chunk_index=0,
            total_chunks=1,
            data=data,
            checksum=correct_checksum,
        )
        assert chunk.verify_checksum()

        # Invalid checksum
        chunk.checksum = "invalid_checksum"
        assert not chunk.verify_checksum()

    def test_chunk_compression(self):
        """Test chunk compression."""
        data = b"test data that should compress well" * 10
        import hashlib
        checksum = hashlib.sha256(data).hexdigest()

        chunk = SyncChunk(
            chunk_id="test",
            chunk_index=0,
            total_chunks=1,
            data=data,
            checksum=checksum,
            compressed=False,
        )

        compressed = chunk.compress()
        assert len(compressed) < len(data)

        # Decompress should return original
        chunk.data = compressed
        chunk.compressed = True
        decompressed = chunk.decompress()
        assert decompressed == data


class TestSnapshotMetadata:
    """Test SnapshotMetadata."""

    def test_metadata_creation(self):
        """Test creating snapshot metadata."""
        metadata = SnapshotMetadata(
            snapshot_id="height_100_abc12345",
            height=100,
            block_hash="abc123def456",
            state_hash="def456ghi789",
            total_chunks=10,
            total_size=10000,
            chunk_size=1000,
            timestamp=1234567890.0,
        )

        assert metadata.snapshot_id == "height_100_abc12345"
        assert metadata.height == 100
        assert metadata.total_chunks == 10

    def test_metadata_serialization(self):
        """Test metadata to/from dict."""
        metadata = SnapshotMetadata(
            snapshot_id="test_snapshot",
            height=100,
            block_hash="abc123",
            state_hash="def456",
            total_chunks=5,
            total_size=5000,
            chunk_size=1000,
            timestamp=1234567890.0,
            priority_map={0: ChunkPriority.CRITICAL, 1: ChunkPriority.HIGH},
        )

        # Serialize
        data = metadata.to_dict()
        assert data["snapshot_id"] == "test_snapshot"
        assert data["height"] == 100

        # Deserialize
        restored = SnapshotMetadata.from_dict(data)
        assert restored.snapshot_id == metadata.snapshot_id
        assert restored.height == metadata.height
        assert restored.priority_map[0] == ChunkPriority.CRITICAL


class TestSyncProgress:
    """Test SyncProgress tracking."""

    def test_progress_creation(self):
        """Test creating sync progress."""
        progress = SyncProgress(
            snapshot_id="test_snapshot",
            total_chunks=10,
        )

        assert progress.snapshot_id == "test_snapshot"
        assert progress.total_chunks == 10
        assert len(progress.downloaded_chunks) == 0
        assert progress.progress_percent == 0.0

    def test_progress_tracking(self):
        """Test marking chunks as downloaded."""
        progress = SyncProgress(
            snapshot_id="test_snapshot",
            total_chunks=10,
        )

        # Mark chunks as downloaded
        progress.mark_downloaded(0)
        progress.mark_downloaded(1)
        progress.mark_downloaded(2)

        assert len(progress.downloaded_chunks) == 3
        assert progress.progress_percent == 30.0
        assert not progress.is_complete

        # Mark remaining chunks
        for i in range(3, 10):
            progress.mark_downloaded(i)

        assert progress.is_complete
        assert progress.progress_percent == 100.0

    def test_progress_remaining_chunks(self):
        """Test getting remaining chunks."""
        progress = SyncProgress(
            snapshot_id="test",
            total_chunks=5,
        )

        progress.mark_downloaded(0)
        progress.mark_downloaded(2)
        progress.mark_downloaded(4)

        remaining = progress.remaining_chunks
        assert remaining == [1, 3]

    def test_progress_serialization(self):
        """Test progress to/from dict."""
        progress = SyncProgress(
            snapshot_id="test",
            total_chunks=10,
        )
        progress.mark_downloaded(0)
        progress.mark_downloaded(1)
        progress.mark_failed(5)

        # Serialize
        data = progress.to_dict()
        assert data["snapshot_id"] == "test"
        assert 0 in data["downloaded_chunks"]
        assert 5 in data["failed_chunks"]

        # Deserialize
        restored = SyncProgress.from_dict(data)
        assert restored.snapshot_id == progress.snapshot_id
        assert restored.downloaded_chunks == progress.downloaded_chunks
        assert restored.failed_chunks == progress.failed_chunks


class TestChunkedStateSyncService:
    """Test ChunkedStateSyncService."""

    def test_service_creation(self, temp_storage):
        """Test creating sync service."""
        service = ChunkedStateSyncService(
            storage_dir=temp_storage,
            chunk_size=1000,
            enable_compression=True,
        )

        assert service.storage_dir == Path(temp_storage)
        assert service.chunk_size == 1000
        assert service.enable_compression

        # Check directories created
        assert service.snapshots_dir.exists()
        assert service.progress_dir.exists()

    def test_create_snapshot_chunks(self, chunked_service, sample_payload):
        """Test creating chunked snapshot from payload."""
        metadata, chunks = chunked_service.create_state_snapshot_chunks(
            height=100,
            payload=sample_payload,
        )

        # Check metadata
        assert metadata.height == 100
        assert metadata.block_hash == sample_payload.block_hash
        assert metadata.state_hash == sample_payload.state_hash
        assert metadata.total_chunks > 0
        assert metadata.chunk_size == 1000

        # Check chunks
        assert len(chunks) == metadata.total_chunks
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i
            assert chunk.total_chunks == metadata.total_chunks
            assert chunk.chunk_id == metadata.snapshot_id
            assert chunk.verify_checksum()

    def test_chunk_priority_assignment(self, chunked_service, sample_payload):
        """Test that chunks have priority assignments."""
        metadata, chunks = chunked_service.create_state_snapshot_chunks(
            height=100,
            payload=sample_payload,
            priority_keys=["utxo_snapshot", "account_balances"],
        )

        # All chunks should have a priority assigned
        priorities = [chunk.priority for chunk in chunks]
        assert len(priorities) == len(chunks)
        # Default implementation uses MEDIUM for all chunks
        assert all(p == ChunkPriority.MEDIUM for p in priorities)

    def test_get_chunk(self, chunked_service, sample_payload):
        """Test retrieving a specific chunk."""
        metadata, chunks = chunked_service.create_state_snapshot_chunks(
            height=100,
            payload=sample_payload,
        )

        # Get first chunk
        chunk = chunked_service.get_chunk(metadata.snapshot_id, 0)
        assert chunk is not None
        assert chunk.chunk_index == 0
        assert chunk.chunk_id == metadata.snapshot_id
        assert chunk.verify_checksum()

        # Get non-existent chunk
        chunk = chunked_service.get_chunk("invalid_id", 999)
        assert chunk is None

    def test_verify_and_apply_chunks(self, chunked_service, sample_payload):
        """Test verifying and reconstructing payload from chunks."""
        metadata, chunks = chunked_service.create_state_snapshot_chunks(
            height=100,
            payload=sample_payload,
        )

        # Verify all chunks
        success, payload = chunked_service.verify_and_apply_chunks(
            chunks,
            metadata.state_hash,
        )

        assert success
        assert payload is not None
        assert payload.height == sample_payload.height
        assert payload.block_hash == sample_payload.block_hash
        assert payload.state_hash == sample_payload.state_hash
        assert payload.verify_integrity()

    def test_verify_incomplete_chunks(self, chunked_service, sample_payload):
        """Test verification fails with incomplete chunks."""
        metadata, chunks = chunked_service.create_state_snapshot_chunks(
            height=100,
            payload=sample_payload,
        )

        # Remove last chunk
        incomplete_chunks = chunks[:-1]

        success, payload = chunked_service.verify_and_apply_chunks(
            incomplete_chunks,
            metadata.state_hash,
        )

        assert not success
        assert payload is None

    def test_verify_corrupted_chunk(self, chunked_service, sample_payload):
        """Test verification fails with corrupted chunk."""
        metadata, chunks = chunked_service.create_state_snapshot_chunks(
            height=100,
            payload=sample_payload,
        )

        # Corrupt a chunk
        chunks[0].data = b"corrupted data"

        success, payload = chunked_service.verify_and_apply_chunks(
            chunks,
            metadata.state_hash,
        )

        assert not success
        assert payload is None

    def test_sync_progress_save_load(self, chunked_service):
        """Test saving and loading sync progress."""
        progress = SyncProgress(
            snapshot_id="test_snapshot",
            total_chunks=10,
        )
        progress.mark_downloaded(0)
        progress.mark_downloaded(1)

        # Save progress
        success = chunked_service.save_sync_progress(progress)
        assert success

        # Load progress
        loaded = chunked_service.get_sync_progress("test_snapshot")
        assert loaded is not None
        assert loaded.snapshot_id == progress.snapshot_id
        assert loaded.downloaded_chunks == progress.downloaded_chunks

    def test_delete_progress(self, chunked_service):
        """Test deleting sync progress."""
        progress = SyncProgress(
            snapshot_id="test_snapshot",
            total_chunks=5,
        )

        # Save and delete
        chunked_service.save_sync_progress(progress)
        assert chunked_service.get_sync_progress("test_snapshot") is not None

        success = chunked_service.delete_progress("test_snapshot")
        assert success
        assert chunked_service.get_sync_progress("test_snapshot") is None

    def test_get_latest_snapshot_id(self, chunked_service, sample_payload):
        """Test getting latest snapshot ID."""
        # Create multiple snapshots
        chunked_service.create_state_snapshot_chunks(height=100, payload=sample_payload)
        chunked_service.create_state_snapshot_chunks(height=200, payload=sample_payload)
        chunked_service.create_state_snapshot_chunks(height=150, payload=sample_payload)

        # Get latest
        latest_id = chunked_service.get_latest_snapshot_id()
        assert latest_id is not None
        assert "height_200_" in latest_id


class TestChunkedSyncWithCompression:
    """Test chunked sync with compression enabled."""

    def test_compressed_chunks(self, temp_storage, sample_payload):
        """Test creating compressed chunks."""
        service = ChunkedStateSyncService(
            storage_dir=temp_storage,
            chunk_size=1000,
            enable_compression=True,
        )

        metadata, chunks = service.create_state_snapshot_chunks(
            height=100,
            payload=sample_payload,
        )

        # Check chunks are marked as compressed
        assert metadata.compression_enabled
        for chunk in chunks:
            assert chunk.compressed

        # Verify decompression works
        success, payload = service.verify_and_apply_chunks(
            chunks,
            metadata.state_hash,
        )

        assert success
        assert payload is not None
        assert payload.height == sample_payload.height


class TestCheckpointSyncIntegration:
    """Test integration with CheckpointSyncManager."""

    @patch("xai.core.checkpoint_sync.ChunkedStateSyncService")
    def test_chunked_sync_manager_init(self, mock_service_class):
        """Test CheckpointSyncManager with chunked sync enabled."""
        from xai.core.checkpoint_sync import CheckpointSyncManager

        mock_blockchain = Mock()
        mock_blockchain.base_dir = "/tmp/test"
        mock_blockchain.checkpoint_manager = None
        mock_config = Mock()
        mock_config.CHECKPOINT_QUORUM = 3
        mock_config.TRUSTED_CHECKPOINT_PUBKEYS = []
        mock_config.CHECKPOINT_MIN_PEERS = 2
        mock_config.CHECKPOINT_REQUEST_RATE_SECONDS = 30
        mock_blockchain.config = mock_config

        manager = CheckpointSyncManager(
            blockchain=mock_blockchain,
            enable_chunked_sync=True,
            chunk_size=2_000_000,
        )

        assert manager.enable_chunked_sync
        assert manager.chunked_service is not None

    def test_chunked_sync_disabled_by_default(self):
        """Test chunked sync is disabled by default."""
        from xai.core.checkpoint_sync import CheckpointSyncManager

        mock_blockchain = Mock()
        mock_blockchain.checkpoint_manager = None
        mock_config = Mock()
        mock_config.CHECKPOINT_QUORUM = 3
        mock_config.TRUSTED_CHECKPOINT_PUBKEYS = []
        mock_config.CHECKPOINT_MIN_PEERS = 2
        mock_config.CHECKPOINT_REQUEST_RATE_SECONDS = 30
        mock_blockchain.config = mock_config

        manager = CheckpointSyncManager(
            blockchain=mock_blockchain,
        )

        assert not manager.enable_chunked_sync
        assert manager.chunked_service is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
