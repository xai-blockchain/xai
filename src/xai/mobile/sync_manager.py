"""
Mobile Sync Manager

Provides mobile-optimized state synchronization with:
- Priority-based chunk downloading
- Bandwidth throttling
- Background sync support
- Pause/resume capability
- Disk space checking
- Network condition adaptation
"""

from __future__ import annotations

import asyncio
import os
import shutil
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from threading import Lock
from typing import Any, Callable

from xai.core.checkpoint_payload import CheckpointPayload
from xai.core.chunked_sync import (
    ChunkedStateSyncService,
    ChunkPriority,
    SyncChunk,
    SyncProgress,
)
from xai.core.structured_logger import get_structured_logger

class SyncState(Enum):
    """State of the sync operation."""
    IDLE = "idle"
    CHECKING_DISK = "checking_disk"
    DOWNLOADING = "downloading"
    PAUSED = "paused"
    VERIFYING = "verifying"
    APPLYING = "applying"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class NetworkCondition:
    """
    Network condition information.

    Attributes:
        bandwidth_limit: Maximum bandwidth in bytes/second (0 = unlimited)
        connection_type: Type of connection (wifi, cellular, etc.)
        is_metered: Whether connection is metered
        signal_strength: Signal strength (0-100)
    """
    bandwidth_limit: int = 0
    connection_type: str = "unknown"
    is_metered: bool = False
    signal_strength: int = 100

    def get_recommended_chunk_size(self) -> int:
        """
        Get recommended chunk size based on network conditions.

        Returns:
            Recommended chunk size in bytes
        """
        if self.connection_type == "wifi" and not self.is_metered:
            return 5_000_000  # 5MB for WiFi
        elif self.connection_type == "4g":
            return 2_000_000  # 2MB for 4G
        elif self.connection_type == "3g":
            return 512_000    # 512KB for 3G
        else:
            return 1_000_000  # 1MB default

@dataclass
class SyncStatistics:
    """
    Statistics for sync operation.

    Attributes:
        bytes_downloaded: Total bytes downloaded
        chunks_downloaded: Number of chunks downloaded
        chunks_failed: Number of chunks that failed
        average_speed: Average download speed (bytes/second)
        elapsed_time: Elapsed time in seconds
        estimated_time_remaining: Estimated time remaining (seconds)
    """
    bytes_downloaded: int = 0
    chunks_downloaded: int = 0
    chunks_failed: int = 0
    average_speed: float = 0.0
    elapsed_time: float = 0.0
    estimated_time_remaining: float = 0.0

class BandwidthThrottle:
    """
    Bandwidth throttling for download rate limiting.

    Uses token bucket algorithm for smooth rate limiting.
    """

    def __init__(self, bytes_per_second: int = 0):
        """
        Initialize bandwidth throttle.

        Args:
            bytes_per_second: Maximum bytes per second (0 = unlimited)
        """
        self.bytes_per_second = bytes_per_second
        self.tokens = 0.0
        self.last_update = time.time()
        self.lock = Lock()

    def set_limit(self, bytes_per_second: int) -> None:
        """
        Set bandwidth limit.

        Args:
            bytes_per_second: Maximum bytes per second (0 = unlimited)
        """
        with self.lock:
            self.bytes_per_second = bytes_per_second

    def throttle(self, byte_count: int) -> None:
        """
        Throttle based on byte count.

        Blocks until enough tokens are available.

        Args:
            byte_count: Number of bytes being transferred
        """
        if self.bytes_per_second == 0:
            return  # No limit

        with self.lock:
            now = time.time()
            elapsed = now - self.last_update
            self.last_update = now

            # Add tokens based on elapsed time
            self.tokens += elapsed * self.bytes_per_second
            self.tokens = min(self.tokens, self.bytes_per_second * 2)  # Max 2 seconds burst

            # Wait if not enough tokens
            if byte_count > self.tokens:
                wait_time = (byte_count - self.tokens) / self.bytes_per_second
                time.sleep(wait_time)
                self.tokens = 0
            else:
                self.tokens -= byte_count

class MobileSyncManager:
    """
    Mobile-optimized sync manager.

    Provides:
    - Priority-based chunk downloading
    - Bandwidth throttling
    - Background sync support
    - Pause/resume capability
    - Disk space checking
    """

    def __init__(
        self,
        chunked_service: ChunkedStateSyncService,
        storage_dir: str,
        min_free_space_mb: int = 100,
        enable_background_sync: bool = True,
    ):
        """
        Initialize mobile sync manager.

        Args:
            chunked_service: Chunked sync service instance
            storage_dir: Directory for storing sync data
            min_free_space_mb: Minimum free space required (MB)
            enable_background_sync: Enable background sync
        """
        self.chunked_service = chunked_service
        self.storage_dir = Path(storage_dir)
        self.min_free_space_mb = min_free_space_mb
        self.enable_background_sync = enable_background_sync
        self.logger = get_structured_logger()

        # State tracking
        self.state = SyncState.IDLE
        self.state_lock = Lock()
        self.paused = False

        # Network conditions
        self.network_condition = NetworkCondition()
        self.bandwidth_throttle = BandwidthThrottle()

        # Statistics
        self.statistics = SyncStatistics()
        self.start_time = 0.0

        # Progress callback
        self.progress_callback: Callable[[dict[str, Any]], None] | None = None

        # Ensure storage directory exists
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def set_network_condition(self, condition: NetworkCondition) -> None:
        """
        Set network condition information.

        Args:
            condition: Network condition details
        """
        self.network_condition = condition
        self.bandwidth_throttle.set_limit(condition.bandwidth_limit)

        self.logger.info(
            "Network condition updated",
            connection_type=condition.connection_type,
            bandwidth_limit=condition.bandwidth_limit,
            is_metered=condition.is_metered,
        )

    def set_progress_callback(self, callback: Callable[[dict[str, Any]], None]) -> None:
        """
        Set progress callback function.

        Args:
            callback: Function to call with progress updates
        """
        self.progress_callback = callback

    def check_disk_space(self, required_bytes: int) -> bool:
        """
        Check if enough disk space is available.

        Args:
            required_bytes: Required space in bytes

        Returns:
            True if enough space available
        """
        try:
            stat = shutil.disk_usage(self.storage_dir)
            free_mb = stat.free / (1024 * 1024)
            required_mb = required_bytes / (1024 * 1024)

            if free_mb < self.min_free_space_mb + required_mb:
                self.logger.warning(
                    "Insufficient disk space",
                    free_mb=round(free_mb, 2),
                    required_mb=round(required_mb, 2),
                    min_free_mb=self.min_free_space_mb,
                )
                return False

            return True

        except (OSError, IOError) as e:
            self.logger.error(
                "Failed to check disk space",
                error=str(e),
                error_type=type(e).__name__,
            )
            return False

    def get_priority_ordered_chunks(
        self,
        remaining_chunks: list[int],
        priority_map: dict[int, ChunkPriority],
    ) -> list[int]:
        """
        Order chunks by priority for download.

        Args:
            remaining_chunks: List of remaining chunk indices
            priority_map: Map of chunk index to priority

        Returns:
            List of chunk indices ordered by priority
        """
        def get_priority(chunk_idx: int) -> int:
            priority = priority_map.get(chunk_idx, ChunkPriority.MEDIUM)
            return priority.value

        return sorted(remaining_chunks, key=get_priority)

    def pause_sync(self) -> None:
        """Pause the sync operation."""
        with self.state_lock:
            if self.state == SyncState.DOWNLOADING:
                self.paused = True
                self.state = SyncState.PAUSED
                self.logger.info("Sync paused")

    def resume_sync(self) -> None:
        """Resume the sync operation."""
        with self.state_lock:
            if self.state == SyncState.PAUSED:
                self.paused = False
                self.state = SyncState.DOWNLOADING
                self.logger.info("Sync resumed")

    def is_paused(self) -> bool:
        """Check if sync is paused."""
        return self.paused

    def _update_state(self, new_state: SyncState) -> None:
        """
        Update sync state and notify callback.

        Args:
            new_state: New sync state
        """
        with self.state_lock:
            self.state = new_state

        if self.progress_callback:
            try:
                self.progress_callback({
                    "state": self.state.value,
                    "statistics": {
                        "bytes_downloaded": self.statistics.bytes_downloaded,
                        "chunks_downloaded": self.statistics.chunks_downloaded,
                        "chunks_failed": self.statistics.chunks_failed,
                        "average_speed": self.statistics.average_speed,
                        "elapsed_time": self.statistics.elapsed_time,
                        "estimated_time_remaining": self.statistics.estimated_time_remaining,
                    },
                })
            except (ValueError, TypeError, RuntimeError, OSError, IOError) as e:
                self.logger.debug(
                    "Progress callback failed",
                    error=str(e),
                    error_type=type(e).__name__,
                )

    def _update_statistics(
        self,
        progress: SyncProgress,
        metadata: Any,
    ) -> None:
        """
        Update sync statistics.

        Args:
            progress: Current sync progress
            metadata: Snapshot metadata
        """
        self.statistics.chunks_downloaded = len(progress.downloaded_chunks)
        self.statistics.chunks_failed = len(progress.failed_chunks)

        # Calculate elapsed time
        self.statistics.elapsed_time = time.time() - self.start_time

        # Calculate average speed
        if self.statistics.elapsed_time > 0:
            self.statistics.average_speed = (
                self.statistics.bytes_downloaded / self.statistics.elapsed_time
            )

        # Estimate time remaining
        remaining_bytes = metadata.total_size - self.statistics.bytes_downloaded
        if self.statistics.average_speed > 0:
            self.statistics.estimated_time_remaining = (
                remaining_bytes / self.statistics.average_speed
            )

    def sync_snapshot(
        self,
        snapshot_id: str,
        chunk_fetcher: Callable[[str, int], SyncChunk | None],
    ) -> CheckpointPayload | None:
        """
        Sync a snapshot with mobile optimizations.

        Args:
            snapshot_id: ID of snapshot to sync
            chunk_fetcher: Function to fetch chunks (e.g., from network)

        Returns:
            Reconstructed checkpoint payload or None if failed
        """
        try:
            # Get snapshot metadata
            metadata = self.chunked_service.get_snapshot_metadata(snapshot_id)
            if not metadata:
                self.logger.error("Snapshot metadata not found", snapshot_id=snapshot_id)
                self._update_state(SyncState.FAILED)
                return None

            # Check disk space
            self._update_state(SyncState.CHECKING_DISK)
            if not self.check_disk_space(metadata.total_size):
                self.logger.error(
                    "Insufficient disk space",
                    snapshot_id=snapshot_id,
                    required_mb=metadata.total_size / (1024 * 1024),
                )
                self._update_state(SyncState.FAILED)
                return None

            self.logger.info(
                "Starting snapshot sync",
                snapshot_id=snapshot_id,
                height=metadata.height,
                total_chunks=metadata.total_chunks,
                total_size_mb=metadata.total_size / (1024 * 1024),
            )

            # Get or create progress
            progress = self.chunked_service.get_sync_progress(snapshot_id)
            if not progress:
                progress = SyncProgress(
                    snapshot_id=snapshot_id,
                    total_chunks=metadata.total_chunks,
                )

            # Initialize statistics
            self.start_time = progress.started_at
            self.statistics = SyncStatistics()

            # Start downloading
            self._update_state(SyncState.DOWNLOADING)

            # Get priority-ordered chunks
            remaining = progress.remaining_chunks
            ordered_chunks = self.get_priority_ordered_chunks(
                remaining,
                metadata.priority_map,
            )

            # Download chunks
            chunks: list[SyncChunk] = []
            for chunk_index in range(metadata.total_chunks):
                # Check if paused
                while self.is_paused():
                    time.sleep(0.5)

                # Skip already downloaded chunks
                if chunk_index in progress.downloaded_chunks:
                    chunk = self.chunked_service.get_chunk(snapshot_id, chunk_index)
                    if chunk:
                        chunks.append(chunk)
                        self.statistics.bytes_downloaded += chunk.size_bytes
                    continue

                # Download chunk
                chunk = self._download_chunk_with_throttle(
                    snapshot_id,
                    chunk_index,
                    chunk_fetcher,
                )

                if not chunk:
                    progress.mark_failed(chunk_index)
                    self.statistics.chunks_failed += 1
                    self.logger.error(
                        "Failed to download chunk",
                        snapshot_id=snapshot_id,
                        chunk_index=chunk_index,
                    )
                    # Save progress and continue
                    self.chunked_service.save_sync_progress(progress)
                    continue

                # Verify chunk checksum
                if not chunk.verify_checksum():
                    progress.mark_failed(chunk_index)
                    self.statistics.chunks_failed += 1
                    self.logger.error(
                        "Chunk checksum verification failed",
                        snapshot_id=snapshot_id,
                        chunk_index=chunk_index,
                    )
                    self.chunked_service.save_sync_progress(progress)
                    continue

                # Mark as downloaded
                progress.mark_downloaded(chunk_index)
                chunks.append(chunk)
                self.statistics.bytes_downloaded += chunk.size_bytes

                # Update statistics and notify
                self._update_statistics(progress, metadata)
                self._update_state(SyncState.DOWNLOADING)

                # Save progress periodically
                if chunk_index % 10 == 0:
                    self.chunked_service.save_sync_progress(progress)

            # Check if all chunks downloaded
            if len(progress.downloaded_chunks) != metadata.total_chunks:
                self.logger.error(
                    "Incomplete chunk download",
                    snapshot_id=snapshot_id,
                    downloaded=len(progress.downloaded_chunks),
                    total=metadata.total_chunks,
                )
                self._update_state(SyncState.FAILED)
                return None

            # Save final progress
            self.chunked_service.save_sync_progress(progress)

            # Verify and apply chunks
            self._update_state(SyncState.VERIFYING)
            success, payload = self.chunked_service.verify_and_apply_chunks(
                chunks,
                metadata.state_hash,
            )

            if not success or not payload:
                self.logger.error(
                    "Failed to verify and reconstruct payload",
                    snapshot_id=snapshot_id,
                )
                self._update_state(SyncState.FAILED)
                return None

            # Cleanup progress file
            self.chunked_service.delete_progress(snapshot_id)

            self.logger.info(
                "Snapshot sync completed",
                snapshot_id=snapshot_id,
                height=payload.height,
                elapsed_time=self.statistics.elapsed_time,
            )

            self._update_state(SyncState.COMPLETED)
            return payload

        except (ValueError, KeyError, OSError, IOError, RuntimeError) as e:
            self.logger.error(
                "Sync failed with exception",
                snapshot_id=snapshot_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            self._update_state(SyncState.FAILED)
            return None

    def _download_chunk_with_throttle(
        self,
        snapshot_id: str,
        chunk_index: int,
        chunk_fetcher: Callable[[str, int], SyncChunk | None],
    ) -> SyncChunk | None:
        """
        Download a chunk with bandwidth throttling.

        Args:
            snapshot_id: ID of snapshot
            chunk_index: Index of chunk to download
            chunk_fetcher: Function to fetch chunk

        Returns:
            Downloaded chunk or None if failed
        """
        try:
            # Fetch chunk
            chunk = chunk_fetcher(snapshot_id, chunk_index)
            if not chunk:
                return None

            # Apply bandwidth throttle
            self.bandwidth_throttle.throttle(len(chunk.data))

            return chunk

        except (ValueError, OSError, IOError, RuntimeError) as e:
            self.logger.error(
                "Failed to download chunk",
                snapshot_id=snapshot_id,
                chunk_index=chunk_index,
                error=str(e),
                error_type=type(e).__name__,
            )
            return None

    def get_sync_state(self) -> dict[str, Any]:
        """
        Get current sync state and statistics.

        Returns:
            Dictionary with state and statistics
        """
        return {
            "state": self.state.value,
            "paused": self.paused,
            "network_condition": {
                "connection_type": self.network_condition.connection_type,
                "bandwidth_limit": self.network_condition.bandwidth_limit,
                "is_metered": self.network_condition.is_metered,
                "signal_strength": self.network_condition.signal_strength,
            },
            "statistics": {
                "bytes_downloaded": self.statistics.bytes_downloaded,
                "chunks_downloaded": self.statistics.chunks_downloaded,
                "chunks_failed": self.statistics.chunks_failed,
                "average_speed": self.statistics.average_speed,
                "elapsed_time": self.statistics.elapsed_time,
                "estimated_time_remaining": self.statistics.estimated_time_remaining,
            },
        }
