"""
Mobile Network Optimizer

Adaptive optimization based on network conditions:
- Dynamic batch size adjustment based on connection quality
- WiFi vs cellular detection and optimization
- Low-bandwidth mode with compression
- Offline transaction queue
- Smart request batching and prioritization
"""

from __future__ import annotations

import gzip
import json
import logging
import time
from collections import deque
from dataclasses import asdict, dataclass, field
from enum import Enum
from threading import Lock
from typing import Any

logger = logging.getLogger(__name__)

class ConnectionType(Enum):
    """Network connection types"""
    WIFI = "wifi"
    CELLULAR = "cellular"
    OFFLINE = "offline"
    UNKNOWN = "unknown"

class BandwidthMode(Enum):
    """Bandwidth optimization modes"""
    FULL = "full"           # No restrictions
    OPTIMIZED = "optimized" # Moderate compression
    LOW = "low"             # Aggressive compression, reduced polling
    MINIMAL = "minimal"     # Only critical operations

@dataclass
class NetworkProfile:
    """Network connection profile with quality metrics"""

    connection_type: ConnectionType
    signal_strength: int  # 0-5 bars
    estimated_bandwidth_kbps: float
    latency_ms: float
    packet_loss_percent: float = 0.0
    is_metered: bool = False  # Is this a metered connection?

    def quality_score(self) -> float:
        """
        Calculate overall connection quality score (0-1).

        Higher is better. Considers bandwidth, latency, signal, packet loss.
        """
        # Normalize components (0-1 scale)
        bandwidth_score = min(self.estimated_bandwidth_kbps / 10000, 1.0)  # 10Mbps = max
        latency_score = max(0, 1.0 - (self.latency_ms / 1000))  # 1s latency = 0
        signal_score = self.signal_strength / 5.0
        packet_loss_score = max(0, 1.0 - (self.packet_loss_percent / 100))

        # Weighted average
        return (
            0.3 * bandwidth_score +
            0.3 * latency_score +
            0.2 * signal_score +
            0.2 * packet_loss_score
        )

    def recommended_mode(self) -> BandwidthMode:
        """Get recommended bandwidth mode for this connection"""
        if self.connection_type == ConnectionType.OFFLINE:
            return BandwidthMode.MINIMAL

        quality = self.quality_score()

        if quality >= 0.7 and self.connection_type == ConnectionType.WIFI:
            return BandwidthMode.FULL
        elif quality >= 0.5:
            return BandwidthMode.OPTIMIZED
        elif quality >= 0.3:
            return BandwidthMode.LOW
        else:
            return BandwidthMode.MINIMAL

    def recommended_batch_size(self, base_size: int = 50) -> int:
        """
        Get recommended batch size for sync operations.

        Args:
            base_size: Base batch size for optimal conditions

        Returns:
            Adjusted batch size
        """
        quality = self.quality_score()

        if quality >= 0.7:
            return base_size
        elif quality >= 0.5:
            return max(base_size // 2, 10)
        elif quality >= 0.3:
            return max(base_size // 4, 5)
        else:
            return max(base_size // 10, 1)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            'connection_type': self.connection_type.value,
            'signal_strength': self.signal_strength,
            'estimated_bandwidth_kbps': self.estimated_bandwidth_kbps,
            'latency_ms': self.latency_ms,
            'packet_loss_percent': self.packet_loss_percent,
            'is_metered': self.is_metered,
            'quality_score': self.quality_score(),
            'recommended_mode': self.recommended_mode().value
        }

@dataclass
class QueuedTransaction:
    """Transaction queued for offline submission"""

    tx_id: str
    tx_data: dict[str, Any]
    created_at: float
    priority: int = 0  # Higher = more urgent
    retries: int = 0
    last_retry_at: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> QueuedTransaction:
        """Create from dictionary"""
        return cls(**data)

class NetworkOptimizer:
    """
    Adaptive network optimizer for mobile clients.

    Features:
    - Connection quality detection and profiling
    - Automatic batch size adjustment
    - Compression for low-bandwidth scenarios
    - Offline transaction queue
    - Smart request prioritization
    """

    def __init__(
        self,
        enable_compression: bool = True,
        max_queue_size: int = 1000,
        compression_threshold_bytes: int = 1024
    ):
        """
        Initialize network optimizer.

        Args:
            enable_compression: Enable response compression
            max_queue_size: Maximum offline queue size
            compression_threshold_bytes: Minimum size for compression
        """
        self.enable_compression = enable_compression
        self.max_queue_size = max_queue_size
        self.compression_threshold = compression_threshold_bytes

        # Current network profile
        self._current_profile: NetworkProfile | None = None
        self._profile_lock = Lock()

        # Offline transaction queue
        self._tx_queue: deque[QueuedTransaction] = deque(maxlen=max_queue_size)
        self._queue_lock = Lock()

        # Performance history for adaptive learning
        self._latency_history: deque[float] = deque(maxlen=100)
        self._bandwidth_history: deque[float] = deque(maxlen=100)

        logger.info("NetworkOptimizer initialized")

    def update_network_profile(
        self,
        connection_type: str,
        signal_strength: int,
        latency_ms: float,
        estimated_bandwidth_kbps: float | None = None,
        packet_loss_percent: float = 0.0,
        is_metered: bool = False
    ) -> NetworkProfile:
        """
        Update current network profile.

        Args:
            connection_type: 'wifi', 'cellular', 'offline', 'unknown'
            signal_strength: Signal strength (0-5 bars)
            latency_ms: Current latency in milliseconds
            estimated_bandwidth_kbps: Estimated bandwidth in kbps
            packet_loss_percent: Packet loss percentage
            is_metered: Is connection metered?

        Returns:
            Updated network profile
        """
        # Parse connection type
        try:
            conn_type = ConnectionType(connection_type)
        except ValueError:
            conn_type = ConnectionType.UNKNOWN

        # Estimate bandwidth if not provided
        if estimated_bandwidth_kbps is None:
            estimated_bandwidth_kbps = self._estimate_bandwidth()

        # Update history
        self._latency_history.append(latency_ms)
        self._bandwidth_history.append(estimated_bandwidth_kbps)

        # Create profile
        profile = NetworkProfile(
            connection_type=conn_type,
            signal_strength=signal_strength,
            estimated_bandwidth_kbps=estimated_bandwidth_kbps,
            latency_ms=latency_ms,
            packet_loss_percent=packet_loss_percent,
            is_metered=is_metered
        )

        with self._profile_lock:
            self._current_profile = profile

        logger.debug(
            f"Network profile updated: {conn_type.value}, "
            f"quality={profile.quality_score():.2f}, "
            f"mode={profile.recommended_mode().value}"
        )

        return profile

    def get_current_profile(self) -> NetworkProfile | None:
        """Get current network profile"""
        with self._profile_lock:
            return self._current_profile

    def _estimate_bandwidth(self) -> float:
        """
        Estimate bandwidth based on recent history.

        Returns:
            Estimated bandwidth in kbps
        """
        if not self._bandwidth_history:
            return 1000.0  # Default 1 Mbps

        # Use median of recent measurements
        sorted_bw = sorted(self._bandwidth_history)
        return sorted_bw[len(sorted_bw) // 2]

    def get_recommended_batch_size(self, operation: str = "sync") -> int:
        """
        Get recommended batch size for operation.

        Args:
            operation: Operation type ('sync', 'transactions', 'blocks')

        Returns:
            Recommended batch size
        """
        base_sizes = {
            'sync': 50,
            'transactions': 100,
            'blocks': 20
        }

        base_size = base_sizes.get(operation, 50)

        profile = self.get_current_profile()
        if profile:
            return profile.recommended_batch_size(base_size)

        return base_size

    def get_bandwidth_mode(self) -> BandwidthMode:
        """
        Get current recommended bandwidth mode.

        Returns:
            Recommended bandwidth mode
        """
        profile = self.get_current_profile()
        if profile:
            return profile.recommended_mode()

        return BandwidthMode.OPTIMIZED

    def should_compress(self, data_size_bytes: int) -> bool:
        """
        Determine if data should be compressed.

        Args:
            data_size_bytes: Size of data to potentially compress

        Returns:
            True if compression is recommended
        """
        if not self.enable_compression:
            return False

        if data_size_bytes < self.compression_threshold:
            return False

        mode = self.get_bandwidth_mode()
        return mode in (BandwidthMode.LOW, BandwidthMode.MINIMAL, BandwidthMode.OPTIMIZED)

    def compress_response(self, data: dict[str, Any]) -> tuple[bytes, bool]:
        """
        Compress response data if beneficial.

        Args:
            data: Response data dictionary

        Returns:
            Tuple of (compressed_data, was_compressed)
        """
        json_data = json.dumps(data).encode('utf-8')

        if not self.should_compress(len(json_data)):
            return json_data, False

        try:
            compressed = gzip.compress(json_data, compresslevel=6)

            # Only use compression if it actually reduces size
            if len(compressed) < len(json_data) * 0.9:
                logger.debug(
                    f"Compressed response: {len(json_data)} -> {len(compressed)} bytes "
                    f"({(1 - len(compressed)/len(json_data))*100:.1f}% reduction)"
                )
                return compressed, True
            else:
                return json_data, False

        except Exception as e:
            logger.error(f"Compression failed: {e}")
            return json_data, False

    def decompress_request(self, data: bytes) -> dict[str, Any]:
        """
        Decompress request data.

        Args:
            data: Compressed data

        Returns:
            Decompressed dictionary

        Raises:
            ValueError: If decompression fails
        """
        try:
            decompressed = gzip.decompress(data)
            return json.loads(decompressed)
        except Exception as e:
            raise ValueError(f"Failed to decompress request: {e}")

    def queue_transaction(
        self,
        tx_id: str,
        tx_data: dict[str, Any],
        priority: int = 0
    ) -> bool:
        """
        Queue transaction for offline submission.

        Args:
            tx_id: Transaction identifier
            tx_data: Transaction data
            priority: Priority (higher = more urgent)

        Returns:
            True if queued successfully
        """
        tx = QueuedTransaction(
            tx_id=tx_id,
            tx_data=tx_data,
            created_at=time.time(),
            priority=priority
        )

        with self._queue_lock:
            # Check for duplicates
            if any(t.tx_id == tx_id for t in self._tx_queue):
                logger.warning(f"Transaction {tx_id} already in queue")
                return False

            # Add to queue (sorted by priority)
            self._tx_queue.append(tx)
            # Re-sort by priority (descending)
            sorted_queue = sorted(self._tx_queue, key=lambda t: t.priority, reverse=True)
            self._tx_queue.clear()
            self._tx_queue.extend(sorted_queue)

        logger.info(f"Queued transaction {tx_id} with priority {priority}")
        return True

    def get_queued_transactions(
        self,
        max_count: int | None = None
    ) -> list[QueuedTransaction]:
        """
        Get queued transactions for submission.

        Args:
            max_count: Maximum transactions to return

        Returns:
            List of queued transactions (highest priority first)
        """
        with self._queue_lock:
            if max_count:
                return list(self._tx_queue)[:max_count]
            return list(self._tx_queue)

    def remove_transaction(self, tx_id: str) -> bool:
        """
        Remove transaction from queue.

        Args:
            tx_id: Transaction identifier

        Returns:
            True if removed
        """
        with self._queue_lock:
            original_len = len(self._tx_queue)
            self._tx_queue = deque(
                [t for t in self._tx_queue if t.tx_id != tx_id],
                maxlen=self.max_queue_size
            )
            removed = len(self._tx_queue) < original_len

        if removed:
            logger.info(f"Removed transaction {tx_id} from queue")

        return removed

    def mark_retry(self, tx_id: str) -> None:
        """
        Mark transaction as retried.

        Args:
            tx_id: Transaction identifier
        """
        with self._queue_lock:
            for tx in self._tx_queue:
                if tx.tx_id == tx_id:
                    tx.retries += 1
                    tx.last_retry_at = time.time()
                    break

    def get_queue_status(self) -> dict[str, Any]:
        """
        Get offline queue status.

        Returns:
            Queue status dictionary
        """
        with self._queue_lock:
            total = len(self._tx_queue)
            by_priority = {}
            oldest = None
            newest = None

            if self._tx_queue:
                oldest = min(t.created_at for t in self._tx_queue)
                newest = max(t.created_at for t in self._tx_queue)

                for tx in self._tx_queue:
                    by_priority[tx.priority] = by_priority.get(tx.priority, 0) + 1

        return {
            'total_queued': total,
            'by_priority': by_priority,
            'oldest_timestamp': oldest,
            'newest_timestamp': newest,
            'queue_capacity': self.max_queue_size
        }

    def optimize_sync_params(self, base_params: dict[str, Any]) -> dict[str, Any]:
        """
        Optimize sync parameters based on network conditions.

        Args:
            base_params: Base sync parameters

        Returns:
            Optimized parameters
        """
        optimized = dict(base_params)
        profile = self.get_current_profile()

        if not profile:
            return optimized

        mode = profile.recommended_mode()

        # Adjust batch size
        if 'batch_size' in optimized:
            optimized['batch_size'] = profile.recommended_batch_size(
                optimized['batch_size']
            )

        # Adjust polling interval based on mode
        if mode == BandwidthMode.LOW or mode == BandwidthMode.MINIMAL:
            if 'poll_interval' in optimized:
                optimized['poll_interval'] = max(optimized['poll_interval'] * 2, 60)

        # Enable/disable optional data based on mode
        if mode == BandwidthMode.MINIMAL:
            optimized['include_full_blocks'] = False
            optimized['include_tx_details'] = False
        elif mode == BandwidthMode.LOW:
            optimized['include_full_blocks'] = False

        # Compression flag
        optimized['use_compression'] = mode in (
            BandwidthMode.LOW,
            BandwidthMode.MINIMAL,
            BandwidthMode.OPTIMIZED
        )

        return optimized

    def get_stats(self) -> dict[str, Any]:
        """
        Get optimizer statistics.

        Returns:
            Statistics dictionary
        """
        profile = self.get_current_profile()
        queue_status = self.get_queue_status()

        stats = {
            'current_profile': profile.to_dict() if profile else None,
            'bandwidth_mode': self.get_bandwidth_mode().value,
            'queue_status': queue_status,
            'compression_enabled': self.enable_compression
        }

        # Add performance history stats
        if self._latency_history:
            stats['latency_avg_ms'] = sum(self._latency_history) / len(self._latency_history)
            stats['latency_min_ms'] = min(self._latency_history)
            stats['latency_max_ms'] = max(self._latency_history)

        if self._bandwidth_history:
            stats['bandwidth_avg_kbps'] = sum(self._bandwidth_history) / len(self._bandwidth_history)
            stats['bandwidth_min_kbps'] = min(self._bandwidth_history)
            stats['bandwidth_max_kbps'] = max(self._bandwidth_history)

        return stats
