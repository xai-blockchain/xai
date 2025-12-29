"""
Tests for Mobile Sync Manager.

Tests cover:
- Priority-based chunk downloading
- Bandwidth throttling
- Pause/resume capability
- Disk space checking
- Network condition adaptation
- Statistics tracking
"""

import pytest
import tempfile
import shutil
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from xai.mobile.sync_manager import (
    MobileSyncManager,
    SyncState,
    NetworkCondition,
    SyncStatistics,
    BandwidthThrottle,
)
from xai.core.p2p.chunked_sync import (
    ChunkedStateSyncService,
    SyncChunk,
    SnapshotMetadata,
    SyncProgress,
    ChunkPriority,
)
from xai.core.consensus.checkpoint_payload import CheckpointPayload


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
        chunk_size=1000,
        enable_compression=False,
    )


@pytest.fixture
def sync_manager(chunked_service, temp_storage):
    """Create mobile sync manager."""
    return MobileSyncManager(
        chunked_service=chunked_service,
        storage_dir=temp_storage,
        min_free_space_mb=10,
        enable_background_sync=True,
    )


@pytest.fixture
def sample_payload():
    """Create sample checkpoint payload."""
    import json
    import hashlib

    data = {
        "utxo_snapshot": {"addr1": 100, "addr2": 200},
        "account_balances": {"addr3": 300},
    }
    serialized = json.dumps(data, sort_keys=True).encode("utf-8")
    state_hash = hashlib.sha256(serialized).hexdigest()

    return CheckpointPayload(
        height=100,
        block_hash="abc123def456",
        state_hash=state_hash,
        data=data,
    )


class TestNetworkCondition:
    """Test NetworkCondition class."""

    def test_default_network_condition(self):
        """Test default network condition."""
        condition = NetworkCondition()
        assert condition.bandwidth_limit == 0
        assert condition.connection_type == "unknown"
        assert not condition.is_metered
        assert condition.signal_strength == 100

    def test_wifi_chunk_size(self):
        """Test recommended chunk size for WiFi."""
        condition = NetworkCondition(connection_type="wifi", is_metered=False)
        assert condition.get_recommended_chunk_size() == 5_000_000

    def test_4g_chunk_size(self):
        """Test recommended chunk size for 4G."""
        condition = NetworkCondition(connection_type="4g")
        assert condition.get_recommended_chunk_size() == 2_000_000

    def test_3g_chunk_size(self):
        """Test recommended chunk size for 3G."""
        condition = NetworkCondition(connection_type="3g")
        assert condition.get_recommended_chunk_size() == 512_000

    def test_default_chunk_size(self):
        """Test default recommended chunk size."""
        condition = NetworkCondition(connection_type="unknown")
        assert condition.get_recommended_chunk_size() == 1_000_000


class TestBandwidthThrottle:
    """Test BandwidthThrottle class."""

    def test_throttle_unlimited(self):
        """Test throttling with no limit."""
        throttle = BandwidthThrottle(bytes_per_second=0)
        start = time.time()
        throttle.throttle(1_000_000)
        elapsed = time.time() - start
        assert elapsed < 0.1  # Should be nearly instant

    def test_throttle_limited(self):
        """Test throttling with limit."""
        throttle = BandwidthThrottle(bytes_per_second=100_000)  # 100KB/s
        start = time.time()
        throttle.throttle(200_000)  # 200KB
        elapsed = time.time() - start
        assert elapsed >= 1.8  # Should take at least ~2 seconds

    def test_set_limit(self):
        """Test changing bandwidth limit."""
        throttle = BandwidthThrottle(bytes_per_second=0)
        throttle.set_limit(100_000)
        assert throttle.bytes_per_second == 100_000


class TestMobileSyncManager:
    """Test MobileSyncManager class."""

    def test_manager_creation(self, sync_manager, temp_storage):
        """Test creating sync manager."""
        assert sync_manager.storage_dir == Path(temp_storage)
        assert sync_manager.min_free_space_mb == 10
        assert sync_manager.enable_background_sync
        assert sync_manager.state == SyncState.IDLE

    def test_set_network_condition(self, sync_manager):
        """Test setting network condition."""
        condition = NetworkCondition(
            bandwidth_limit=100_000,
            connection_type="4g",
            is_metered=True,
            signal_strength=80,
        )

        sync_manager.set_network_condition(condition)
        assert sync_manager.network_condition.bandwidth_limit == 100_000
        assert sync_manager.network_condition.connection_type == "4g"
        assert sync_manager.network_condition.is_metered
        assert sync_manager.bandwidth_throttle.bytes_per_second == 100_000

    def test_check_disk_space_sufficient(self, sync_manager):
        """Test disk space check with sufficient space."""
        # Should succeed with reasonable requirement
        result = sync_manager.check_disk_space(1_000_000)  # 1MB
        assert result

    def test_check_disk_space_insufficient(self, sync_manager):
        """Test disk space check with insufficient space."""
        # Should fail with unrealistic requirement
        result = sync_manager.check_disk_space(1_000_000_000_000_000)  # 1PB
        assert not result

    def test_priority_ordered_chunks(self, sync_manager):
        """Test priority ordering of chunks."""
        remaining = [0, 1, 2, 3, 4]
        priority_map = {
            0: ChunkPriority.CRITICAL,
            1: ChunkPriority.HIGH,
            2: ChunkPriority.MEDIUM,
            3: ChunkPriority.LOW,
            4: ChunkPriority.MEDIUM,
        }

        ordered = sync_manager.get_priority_ordered_chunks(remaining, priority_map)
        # Should be ordered by priority (0=highest)
        assert ordered[0] == 0  # CRITICAL
        assert ordered[1] == 1  # HIGH
        assert ordered[2] in [2, 4]  # MEDIUM
        assert ordered[-1] == 3  # LOW

    def test_pause_resume_sync(self, sync_manager):
        """Test pausing and resuming sync."""
        # Set state to downloading
        sync_manager.state = SyncState.DOWNLOADING

        # Pause
        sync_manager.pause_sync()
        assert sync_manager.state == SyncState.PAUSED
        assert sync_manager.is_paused()

        # Resume
        sync_manager.resume_sync()
        assert sync_manager.state == SyncState.DOWNLOADING
        assert not sync_manager.is_paused()

    def test_get_sync_state(self, sync_manager):
        """Test getting sync state."""
        state = sync_manager.get_sync_state()
        assert "state" in state
        assert "paused" in state
        assert "network_condition" in state
        assert "statistics" in state
        assert state["state"] == SyncState.IDLE.value

    def test_progress_callback(self, sync_manager):
        """Test progress callback."""
        callback_data = []

        def callback(data):
            callback_data.append(data)

        sync_manager.set_progress_callback(callback)
        sync_manager._update_state(SyncState.DOWNLOADING)

        assert len(callback_data) > 0
        assert callback_data[0]["state"] == SyncState.DOWNLOADING.value

    def test_sync_snapshot_no_metadata(self, sync_manager):
        """Test sync fails with no metadata."""
        def mock_fetcher(snapshot_id, chunk_index):
            return None

        result = sync_manager.sync_snapshot("invalid_snapshot", mock_fetcher)
        assert result is None
        assert sync_manager.state == SyncState.FAILED

    def test_sync_snapshot_insufficient_disk_space(
        self,
        sync_manager,
        chunked_service,
        sample_payload,
    ):
        """Test sync fails with insufficient disk space."""
        # Create a snapshot
        metadata, chunks = chunked_service.create_state_snapshot_chunks(
            height=100,
            payload=sample_payload,
        )

        # Set unrealistic disk space requirement
        sync_manager.min_free_space_mb = 1_000_000  # 1TB

        def mock_fetcher(snapshot_id, chunk_index):
            return chunked_service.get_chunk(snapshot_id, chunk_index)

        result = sync_manager.sync_snapshot(metadata.snapshot_id, mock_fetcher)
        assert result is None
        assert sync_manager.state == SyncState.FAILED

    def test_sync_snapshot_success(
        self,
        sync_manager,
        chunked_service,
        sample_payload,
    ):
        """Test successful snapshot sync."""
        # Create a snapshot
        metadata, chunks = chunked_service.create_state_snapshot_chunks(
            height=100,
            payload=sample_payload,
        )

        def mock_fetcher(snapshot_id, chunk_index):
            return chunked_service.get_chunk(snapshot_id, chunk_index)

        result = sync_manager.sync_snapshot(metadata.snapshot_id, mock_fetcher)
        assert result is not None
        assert result.height == sample_payload.height
        assert result.block_hash == sample_payload.block_hash
        assert sync_manager.state == SyncState.COMPLETED

    def test_sync_snapshot_with_pause_resume(
        self,
        sync_manager,
        chunked_service,
        sample_payload,
    ):
        """Test sync with pause/resume."""
        # Create a snapshot with multiple chunks
        metadata, chunks = chunked_service.create_state_snapshot_chunks(
            height=100,
            payload=sample_payload,
        )

        call_count = [0]
        pause_at = 2

        def mock_fetcher(snapshot_id, chunk_index):
            call_count[0] += 1
            if call_count[0] == pause_at:
                # Pause after 2nd chunk
                sync_manager.pause_sync()
                # Resume after short delay
                import threading
                threading.Timer(0.5, sync_manager.resume_sync).start()
            return chunked_service.get_chunk(snapshot_id, chunk_index)

        result = sync_manager.sync_snapshot(metadata.snapshot_id, mock_fetcher)
        assert result is not None
        assert sync_manager.state == SyncState.COMPLETED

    def test_sync_snapshot_with_failed_chunk(
        self,
        sync_manager,
        chunked_service,
        sample_payload,
    ):
        """Test sync continues after failed chunk."""
        # Create a snapshot
        metadata, chunks = chunked_service.create_state_snapshot_chunks(
            height=100,
            payload=sample_payload,
        )

        def mock_fetcher(snapshot_id, chunk_index):
            # Fail on first chunk
            if chunk_index == 0:
                return None
            return chunked_service.get_chunk(snapshot_id, chunk_index)

        result = sync_manager.sync_snapshot(metadata.snapshot_id, mock_fetcher)
        # Should fail because first chunk is missing
        assert result is None
        assert sync_manager.statistics.chunks_failed > 0

    def test_download_chunk_with_throttle(
        self,
        sync_manager,
        chunked_service,
        sample_payload,
    ):
        """Test chunk download with bandwidth throttling."""
        # Create a snapshot
        metadata, chunks = chunked_service.create_state_snapshot_chunks(
            height=100,
            payload=sample_payload,
        )

        # Set bandwidth limit
        sync_manager.bandwidth_throttle.set_limit(50_000)  # 50KB/s

        def mock_fetcher(snapshot_id, chunk_index):
            return chunked_service.get_chunk(snapshot_id, chunk_index)

        # Download first chunk
        chunk = sync_manager._download_chunk_with_throttle(
            metadata.snapshot_id,
            0,
            mock_fetcher,
        )

        assert chunk is not None
        assert chunk.chunk_index == 0

    def test_statistics_update(
        self,
        sync_manager,
        chunked_service,
        sample_payload,
    ):
        """Test statistics are updated during sync."""
        # Create a snapshot
        metadata, chunks = chunked_service.create_state_snapshot_chunks(
            height=100,
            payload=sample_payload,
        )

        def mock_fetcher(snapshot_id, chunk_index):
            return chunked_service.get_chunk(snapshot_id, chunk_index)

        # Track progress updates
        progress_updates = []

        def callback(data):
            progress_updates.append(data)

        sync_manager.set_progress_callback(callback)

        result = sync_manager.sync_snapshot(metadata.snapshot_id, mock_fetcher)
        assert result is not None

        # Check statistics were updated
        assert sync_manager.statistics.bytes_downloaded > 0
        assert sync_manager.statistics.chunks_downloaded > 0
        assert sync_manager.statistics.average_speed > 0
        assert sync_manager.statistics.elapsed_time > 0

        # Check progress callbacks were called
        assert len(progress_updates) > 0


class TestSyncStatistics:
    """Test SyncStatistics dataclass."""

    def test_statistics_creation(self):
        """Test creating statistics."""
        stats = SyncStatistics(
            bytes_downloaded=1_000_000,
            chunks_downloaded=10,
            chunks_failed=1,
            average_speed=100_000.0,
            elapsed_time=10.0,
            estimated_time_remaining=5.0,
        )

        assert stats.bytes_downloaded == 1_000_000
        assert stats.chunks_downloaded == 10
        assert stats.chunks_failed == 1
        assert stats.average_speed == 100_000.0


class TestSyncState:
    """Test SyncState enum."""

    def test_sync_states(self):
        """Test all sync states are defined."""
        assert SyncState.IDLE.value == "idle"
        assert SyncState.CHECKING_DISK.value == "checking_disk"
        assert SyncState.DOWNLOADING.value == "downloading"
        assert SyncState.PAUSED.value == "paused"
        assert SyncState.VERIFYING.value == "verifying"
        assert SyncState.APPLYING.value == "applying"
        assert SyncState.COMPLETED.value == "completed"
        assert SyncState.FAILED.value == "failed"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
