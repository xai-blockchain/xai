"""
Chunked state synchronization for bandwidth-constrained clients.

Enables mobile devices to sync state in small chunks with resume capability.
Designed for:
- Slow/unreliable connections (mobile 3G/4G)
- High-latency networks
- Background sync with interruption tolerance
- Parallel chunk downloads

Features:
- 1MB default chunk size (configurable)
- SHA-256 checksum per chunk
- Resume from last successful chunk
- HTTP Range header support
- Compression (gzip) optional
- Priority chunks (account balances first)
"""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from xai.core.checkpoint_payload import CheckpointPayload
from xai.core.structured_logger import get_structured_logger


class ChunkPriority(Enum):
    """Priority levels for chunk download ordering."""
    CRITICAL = 0   # Account balances, UTXO set
    HIGH = 1       # Recent blocks, contract state
    MEDIUM = 2     # Historical blocks
    LOW = 3        # Archive data, logs

@dataclass
class SyncChunk:
    """
    Represents a single chunk of state data.

    Attributes:
        chunk_id: Unique identifier for the snapshot this chunk belongs to
        chunk_index: Zero-based index of this chunk in the sequence
        total_chunks: Total number of chunks in the snapshot
        data: Raw chunk data (uncompressed)
        checksum: SHA-256 checksum of the data
        compressed: Whether data is gzip-compressed
        priority: Download priority for this chunk
        size_bytes: Size of data in bytes
    """
    chunk_id: str
    chunk_index: int
    total_chunks: int
    data: bytes
    checksum: str
    compressed: bool = False
    priority: ChunkPriority = ChunkPriority.MEDIUM
    size_bytes: int = 0

    def __post_init__(self):
        if self.size_bytes == 0:
            self.size_bytes = len(self.data)

    def verify_checksum(self) -> bool:
        """Verify chunk data matches checksum (on uncompressed data)."""
        # If compressed, decompress first before checking
        data_to_check = self.decompress() if self.compressed else self.data
        computed = hashlib.sha256(data_to_check).hexdigest()
        return computed == self.checksum

    def compress(self) -> bytes:
        """Compress chunk data with gzip."""
        if self.compressed:
            return self.data
        return gzip.compress(self.data)

    def decompress(self) -> bytes:
        """Decompress chunk data if compressed."""
        if not self.compressed:
            return self.data
        return gzip.decompress(self.data)

    def to_dict(self) -> dict[str, Any]:
        """Serialize chunk metadata (without data)."""
        return {
            "chunk_id": self.chunk_id,
            "chunk_index": self.chunk_index,
            "total_chunks": self.total_chunks,
            "checksum": self.checksum,
            "compressed": self.compressed,
            "priority": self.priority.value,
            "size_bytes": self.size_bytes,
        }

@dataclass
class SnapshotMetadata:
    """
    Metadata for a complete state snapshot split into chunks.

    Attributes:
        snapshot_id: Unique identifier for this snapshot
        height: Block height at which snapshot was taken
        block_hash: Hash of the block at this height
        state_hash: Root hash of the state at this height
        total_chunks: Number of chunks in this snapshot
        total_size: Total size of all chunks in bytes
        chunk_size: Size of each chunk in bytes (last may be smaller)
        timestamp: When snapshot was created
        compression_enabled: Whether chunks are compressed
        priority_map: Mapping of chunk indices to priorities
    """
    snapshot_id: str
    height: int
    block_hash: str
    state_hash: str
    total_chunks: int
    total_size: int
    chunk_size: int
    timestamp: float
    compression_enabled: bool = False
    priority_map: dict[int, ChunkPriority] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize metadata to JSON-compatible dict."""
        return {
            "snapshot_id": self.snapshot_id,
            "height": self.height,
            "block_hash": self.block_hash,
            "state_hash": self.state_hash,
            "total_chunks": self.total_chunks,
            "total_size": self.total_size,
            "chunk_size": self.chunk_size,
            "timestamp": self.timestamp,
            "compression_enabled": self.compression_enabled,
            "priority_map": {
                str(k): v.value for k, v in self.priority_map.items()
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SnapshotMetadata":
        """Deserialize metadata from dict."""
        priority_map = {
            int(k): ChunkPriority(v)
            for k, v in data.get("priority_map", {}).items()
        }
        return cls(
            snapshot_id=data["snapshot_id"],
            height=data["height"],
            block_hash=data["block_hash"],
            state_hash=data["state_hash"],
            total_chunks=data["total_chunks"],
            total_size=data["total_size"],
            chunk_size=data["chunk_size"],
            timestamp=data["timestamp"],
            compression_enabled=data.get("compression_enabled", False),
            priority_map=priority_map,
        )

@dataclass
class SyncProgress:
    """
    Tracks download progress for resumable sync.

    Attributes:
        snapshot_id: ID of snapshot being downloaded
        downloaded_chunks: Set of chunk indices successfully downloaded
        failed_chunks: Set of chunk indices that failed to download
        total_chunks: Total number of chunks
        started_at: Timestamp when download started
        last_chunk_at: Timestamp of last successful chunk download
    """
    snapshot_id: str
    downloaded_chunks: set[int] = field(default_factory=set)
    failed_chunks: set[int] = field(default_factory=set)
    total_chunks: int = 0
    started_at: float = 0.0
    last_chunk_at: float = 0.0

    def __post_init__(self):
        if self.started_at == 0.0:
            self.started_at = time.time()

    @property
    def progress_percent(self) -> float:
        """Calculate download progress percentage."""
        if self.total_chunks == 0:
            return 0.0
        return (len(self.downloaded_chunks) / self.total_chunks) * 100.0

    @property
    def is_complete(self) -> bool:
        """Check if all chunks have been downloaded."""
        return len(self.downloaded_chunks) == self.total_chunks

    @property
    def remaining_chunks(self) -> list[int]:
        """Get list of chunks still needed."""
        all_chunks = set(range(self.total_chunks))
        return sorted(all_chunks - self.downloaded_chunks)

    def mark_downloaded(self, chunk_index: int) -> None:
        """Mark a chunk as successfully downloaded."""
        self.downloaded_chunks.add(chunk_index)
        self.failed_chunks.discard(chunk_index)
        self.last_chunk_at = time.time()

    def mark_failed(self, chunk_index: int) -> None:
        """Mark a chunk download as failed."""
        self.failed_chunks.add(chunk_index)

    def to_dict(self) -> dict[str, Any]:
        """Serialize progress to JSON-compatible dict."""
        return {
            "snapshot_id": self.snapshot_id,
            "downloaded_chunks": list(self.downloaded_chunks),
            "failed_chunks": list(self.failed_chunks),
            "total_chunks": self.total_chunks,
            "started_at": self.started_at,
            "last_chunk_at": self.last_chunk_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SyncProgress":
        """Deserialize progress from dict."""
        return cls(
            snapshot_id=data["snapshot_id"],
            downloaded_chunks=set(data.get("downloaded_chunks", [])),
            failed_chunks=set(data.get("failed_chunks", [])),
            total_chunks=data.get("total_chunks", 0),
            started_at=data.get("started_at", 0.0),
            last_chunk_at=data.get("last_chunk_at", 0.0),
        )

class ChunkedStateSyncService:
    """
    Service for creating and downloading chunked state snapshots.

    Supports:
    - Creating snapshots split into chunks
    - Downloading chunks with resume capability
    - Verifying and applying complete snapshots
    - Priority-based chunk ordering
    - Compression
    """

    DEFAULT_CHUNK_SIZE = 1_000_000  # 1MB

    def __init__(
        self,
        storage_dir: str,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        enable_compression: bool = True,
    ):
        """
        Initialize chunked sync service.

        Args:
            storage_dir: Directory for storing chunks and metadata
            chunk_size: Size of each chunk in bytes
            enable_compression: Whether to compress chunks
        """
        self.storage_dir = Path(storage_dir)
        self.chunk_size = chunk_size
        self.enable_compression = enable_compression
        self.logger = get_structured_logger()

        # Ensure storage directory exists
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.snapshots_dir = self.storage_dir / "snapshots"
        self.snapshots_dir.mkdir(exist_ok=True)
        self.progress_dir = self.storage_dir / "progress"
        self.progress_dir.mkdir(exist_ok=True)

    def create_state_snapshot_chunks(
        self,
        height: int,
        payload: CheckpointPayload,
        priority_keys: list[str] | None = None,
    ) -> tuple[SnapshotMetadata, list[SyncChunk]]:
        """
        Split a checkpoint payload into resumable chunks.

        Args:
            height: Block height for this snapshot
            payload: Checkpoint payload containing state data
            priority_keys: List of data keys to prioritize (downloaded first)

        Returns:
            Tuple of (metadata, list of chunks)
        """
        snapshot_id = self._generate_snapshot_id(height, payload.block_hash)

        self.logger.info(
            "Creating chunked snapshot",
            snapshot_id=snapshot_id,
            height=height,
            block_hash=payload.block_hash,
        )

        # Serialize payload data
        serialized = json.dumps(payload.to_dict(), sort_keys=True).encode("utf-8")
        total_size = len(serialized)

        # Create chunks directly from serialized data
        chunks: list[SyncChunk] = []
        priority_map: dict[int, ChunkPriority] = {}

        chunk_index = 0
        offset = 0

        while offset < len(serialized):
            chunk_data = serialized[offset : offset + self.chunk_size]

            # Calculate checksum on uncompressed data
            checksum = hashlib.sha256(chunk_data).hexdigest()

            # Store original size before compression
            original_size = len(chunk_data)

            # Compress if enabled
            compressed = False
            if self.enable_compression:
                chunk_data = gzip.compress(chunk_data)
                compressed = True

            chunk = SyncChunk(
                chunk_id=snapshot_id,
                chunk_index=chunk_index,
                total_chunks=0,  # Will be set later
                data=chunk_data,
                checksum=checksum,
                compressed=compressed,
                priority=ChunkPriority.MEDIUM,
                size_bytes=original_size,
            )

            chunks.append(chunk)
            priority_map[chunk_index] = ChunkPriority.MEDIUM
            chunk_index += 1
            offset += self.chunk_size

        # Update total_chunks in all chunks
        total_chunks = len(chunks)
        for chunk in chunks:
            chunk.total_chunks = total_chunks

        # Create metadata
        metadata = SnapshotMetadata(
            snapshot_id=snapshot_id,
            height=height,
            block_hash=payload.block_hash,
            state_hash=payload.state_hash,
            total_chunks=total_chunks,
            total_size=total_size,
            chunk_size=self.chunk_size,
            timestamp=time.time(),
            compression_enabled=self.enable_compression,
            priority_map=priority_map,
        )

        # Save to disk
        self._save_snapshot(metadata, chunks)

        self.logger.info(
            "Snapshot created",
            snapshot_id=snapshot_id,
            total_chunks=total_chunks,
            total_size_mb=total_size / 1_000_000,
            compressed=self.enable_compression,
        )

        return metadata, chunks

    def get_snapshot_metadata(self, snapshot_id: str) -> SnapshotMetadata | None:
        """
        Get metadata for a snapshot.

        Args:
            snapshot_id: ID of the snapshot

        Returns:
            Snapshot metadata or None if not found
        """
        metadata_path = self.snapshots_dir / snapshot_id / "metadata.json"
        if not metadata_path.exists():
            return None

        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return SnapshotMetadata.from_dict(data)
        except (OSError, IOError, json.JSONDecodeError, ValueError, KeyError) as e:
            self.logger.error(
                "Failed to load snapshot metadata",
                extra={
                    "snapshot_id": snapshot_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                }
            )
            return None

    def get_latest_snapshot_id(self) -> str | None:
        """
        Get the ID of the most recent snapshot.

        Returns:
            Snapshot ID or None if no snapshots exist
        """
        if not self.snapshots_dir.exists():
            return None

        # Find all snapshot directories
        snapshots = [
            d.name for d in self.snapshots_dir.iterdir()
            if d.is_dir() and (d / "metadata.json").exists()
        ]

        if not snapshots:
            return None

        # Parse heights from IDs and return highest
        # Format: height_<height>_<hash>
        snapshot_heights = []
        for sid in snapshots:
            try:
                parts = sid.split("_")
                if len(parts) >= 2:
                    height = int(parts[1])
                    snapshot_heights.append((height, sid))
            except (ValueError, IndexError):
                continue

        if not snapshot_heights:
            return None

        return max(snapshot_heights, key=lambda x: x[0])[1]

    def get_chunk(
        self,
        snapshot_id: str,
        chunk_index: int,
    ) -> SyncChunk | None:
        """
        Get a specific chunk for download.

        Args:
            snapshot_id: ID of the snapshot
            chunk_index: Index of the chunk to retrieve

        Returns:
            Chunk data or None if not found
        """
        chunk_path = self.snapshots_dir / snapshot_id / f"chunk_{chunk_index:06d}.bin"
        meta_path = self.snapshots_dir / snapshot_id / f"chunk_{chunk_index:06d}.json"

        if not chunk_path.exists() or not meta_path.exists():
            self.logger.warning(
                "Chunk not found",
                snapshot_id=snapshot_id,
                chunk_index=chunk_index,
            )
            return None

        try:
            # Load chunk metadata
            with open(meta_path, "r", encoding="utf-8") as f:
                meta_data = json.load(f)

            # Load chunk data
            with open(chunk_path, "rb") as f:
                chunk_data = f.read()

            chunk = SyncChunk(
                chunk_id=meta_data["chunk_id"],
                chunk_index=meta_data["chunk_index"],
                total_chunks=meta_data["total_chunks"],
                data=chunk_data,
                checksum=meta_data["checksum"],
                compressed=meta_data.get("compressed", False),
                priority=ChunkPriority(meta_data.get("priority", ChunkPriority.MEDIUM.value)),
                size_bytes=meta_data.get("size_bytes", len(chunk_data)),
            )

            return chunk

        except (OSError, IOError, json.JSONDecodeError, ValueError, KeyError) as e:
            self.logger.error(
                "Failed to load chunk",
                extra={
                    "snapshot_id": snapshot_id,
                    "chunk_index": chunk_index,
                    "error": str(e),
                    "error_type": type(e).__name__,
                }
            )
            return None

    def verify_and_apply_chunks(
        self,
        chunks: list[SyncChunk],
        expected_state_hash: str,
    ) -> tuple[bool, CheckpointPayload | None]:
        """
        Verify checksums and reconstruct state from chunks.

        Args:
            chunks: List of downloaded chunks
            expected_state_hash: Expected state hash for verification

        Returns:
            Tuple of (success, reconstructed payload)
        """
        if not chunks:
            self.logger.error("No chunks provided for verification")
            return False, None

        snapshot_id = chunks[0].chunk_id
        total_chunks = chunks[0].total_chunks

        self.logger.info(
            "Verifying chunks",
            snapshot_id=snapshot_id,
            chunk_count=len(chunks),
            total_expected=total_chunks,
        )

        # Verify we have all chunks
        if len(chunks) != total_chunks:
            self.logger.error(
                "Incomplete chunk set",
                extra={
                    "snapshot_id": snapshot_id,
                    "received": len(chunks),
                    "expected": total_chunks,
                }
            )
            return False, None

        # Sort chunks by index
        chunks.sort(key=lambda c: c.chunk_index)

        # Verify each chunk's checksum
        for chunk in chunks:
            if not chunk.verify_checksum():
                self.logger.error(
                    "Chunk checksum verification failed",
                    extra={
                        "snapshot_id": snapshot_id,
                        "chunk_index": chunk.chunk_index,
                    }
                )
                return False, None

        # Reconstruct data
        try:
            data_parts = []
            for chunk in chunks:
                # Decompress if needed
                if chunk.compressed:
                    data_parts.append(chunk.decompress())
                else:
                    data_parts.append(chunk.data)

            # Combine all chunks
            full_data = b"".join(data_parts)

            # Parse as JSON
            payload_dict = json.loads(full_data)

            # Reconstruct checkpoint payload
            payload = CheckpointPayload(
                height=payload_dict["height"],
                block_hash=payload_dict["block_hash"],
                state_hash=payload_dict["state_hash"],
                data=payload_dict.get("data", {}),
                work=payload_dict.get("work"),
                signature=payload_dict.get("signature"),
                pubkey=payload_dict.get("pubkey"),
            )

            # Verify state hash
            if payload.state_hash != expected_state_hash:
                self.logger.error(
                    "State hash mismatch",
                    extra={
                        "snapshot_id": snapshot_id,
                        "expected": expected_state_hash,
                        "actual": payload.state_hash,
                    }
                )
                return False, None

            # Verify payload integrity
            if not payload.verify_integrity():
                self.logger.error(
                    "Payload integrity check failed",
                    snapshot_id=snapshot_id,
                )
                return False, None

            self.logger.info(
                "Chunks verified successfully",
                snapshot_id=snapshot_id,
                height=payload.height,
            )

            return True, payload

        except (json.JSONDecodeError, ValueError, KeyError, TypeError, OSError, IOError) as e:
            self.logger.error(
                "Failed to reconstruct payload from chunks",
                extra={
                    "snapshot_id": snapshot_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                }
            )
            return False, None

    def get_sync_progress(self, snapshot_id: str) -> SyncProgress | None:
        """
        Get download progress for a snapshot.

        Args:
            snapshot_id: ID of the snapshot

        Returns:
            Sync progress or None if not found
        """
        progress_path = self.progress_dir / f"{snapshot_id}.json"
        if not progress_path.exists():
            return None

        try:
            with open(progress_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return SyncProgress.from_dict(data)
        except (OSError, IOError, json.JSONDecodeError, ValueError, KeyError) as e:
            self.logger.error(
                "Failed to load sync progress",
                extra={
                    "snapshot_id": snapshot_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                }
            )
            return None

    def save_sync_progress(self, progress: SyncProgress) -> bool:
        """
        Save download progress for resume capability.

        Args:
            progress: Sync progress to save

        Returns:
            True if saved successfully
        """
        progress_path = self.progress_dir / f"{progress.snapshot_id}.json"

        try:
            with open(progress_path, "w", encoding="utf-8") as f:
                json.dump(progress.to_dict(), f, indent=2)
            return True
        except (OSError, IOError) as e:
            self.logger.error(
                "Failed to save sync progress",
                extra={
                    "snapshot_id": progress.snapshot_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                }
            )
            return False

    def delete_progress(self, snapshot_id: str) -> bool:
        """
        Delete progress file after successful sync.

        Args:
            snapshot_id: ID of the snapshot

        Returns:
            True if deleted successfully
        """
        progress_path = self.progress_dir / f"{snapshot_id}.json"
        if progress_path.exists():
            try:
                progress_path.unlink()
                return True
            except OSError as e:
                self.logger.error(
                    "Failed to delete progress file",
                    extra={
                        "snapshot_id": snapshot_id,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    }
                )
                return False
        return True

    def _generate_snapshot_id(self, height: int, block_hash: str) -> str:
        """Generate unique snapshot ID."""
        # Format: height_<height>_<first 8 chars of hash>
        return f"height_{height}_{block_hash[:8]}"

    def _split_by_priority(
        self,
        payload_dict: dict[str, Any],
        priority_keys: list[str],
    ) -> tuple[bytes, bytes]:
        """
        Split payload data into priority and regular sections.

        Args:
            payload_dict: Full payload dictionary
            priority_keys: Keys to extract for priority download

        Returns:
            Tuple of (priority_data_bytes, regular_data_bytes)
        """
        priority_data = {}
        regular_data = payload_dict.copy()

        # Extract priority keys
        data_section = regular_data.get("data", {})
        priority_section = {}

        for key in priority_keys:
            if key in data_section:
                priority_section[key] = data_section.pop(key)

        if priority_section:
            priority_data["data"] = priority_section
            regular_data["data"] = data_section

        # Serialize both sections
        priority_bytes = json.dumps(priority_data, sort_keys=True).encode("utf-8") if priority_data else b""
        regular_bytes = json.dumps(regular_data, sort_keys=True).encode("utf-8")

        return priority_bytes, regular_bytes

    def _save_snapshot(
        self,
        metadata: SnapshotMetadata,
        chunks: list[SyncChunk],
    ) -> None:
        """
        Save snapshot metadata and chunks to disk.

        Args:
            metadata: Snapshot metadata
            chunks: List of chunks to save
        """
        snapshot_dir = self.snapshots_dir / metadata.snapshot_id
        snapshot_dir.mkdir(parents=True, exist_ok=True)

        # Save metadata
        metadata_path = snapshot_dir / "metadata.json"
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata.to_dict(), f, indent=2)

        # Save each chunk
        for chunk in chunks:
            chunk_path = snapshot_dir / f"chunk_{chunk.chunk_index:06d}.bin"
            meta_path = snapshot_dir / f"chunk_{chunk.chunk_index:06d}.json"

            # Save chunk data
            with open(chunk_path, "wb") as f:
                f.write(chunk.data)

            # Save chunk metadata
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(chunk.to_dict(), f, indent=2)
