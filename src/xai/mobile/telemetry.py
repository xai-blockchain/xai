"""
Mobile Telemetry Collection

Tracks mobile-specific performance metrics for optimization:
- Bandwidth usage (bytes sent/received per operation)
- Battery impact estimation
- Sync duration and efficiency
- API call latency from mobile
- Memory and storage usage
- Aggregated statistics for insights
"""

from __future__ import annotations

import time
import json
import hashlib
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from collections import defaultdict
from threading import Lock

logger = logging.getLogger(__name__)


@dataclass
class TelemetryEvent:
    """Individual telemetry event from mobile client"""

    event_type: str  # 'sync', 'api_call', 'transaction', 'storage', 'memory'
    timestamp: float
    client_id: str  # Anonymous device identifier

    # Bandwidth metrics (bytes)
    bytes_sent: int = 0
    bytes_received: int = 0

    # Performance metrics
    duration_ms: float = 0  # Operation duration
    latency_ms: float = 0   # Network latency

    # Battery metrics
    battery_level_start: Optional[float] = None  # 0-100
    battery_level_end: Optional[float] = None

    # Resource metrics
    memory_mb: Optional[float] = None
    storage_mb: Optional[float] = None

    # Connectivity
    connection_type: Optional[str] = None  # 'wifi', 'cellular', 'offline'
    signal_strength: Optional[int] = None  # 0-5 bars

    # Operation-specific metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TelemetryEvent:
        """Create from dictionary"""
        # Handle metadata separately
        metadata = data.pop('metadata', {})
        event = cls(**data)
        event.metadata = metadata
        return event

    def battery_drain(self) -> Optional[float]:
        """Calculate battery drain percentage"""
        if self.battery_level_start is not None and self.battery_level_end is not None:
            return self.battery_level_start - self.battery_level_end
        return None

    def total_bytes(self) -> int:
        """Total bytes transferred"""
        return self.bytes_sent + self.bytes_received

    def bytes_per_second(self) -> float:
        """Calculate throughput in bytes/second"""
        if self.duration_ms > 0:
            return (self.total_bytes() * 1000) / self.duration_ms
        return 0.0


@dataclass
class AggregatedStats:
    """Aggregated telemetry statistics for a time window"""

    start_time: float
    end_time: float
    event_count: int

    # Bandwidth totals
    total_bytes_sent: int = 0
    total_bytes_received: int = 0

    # Performance averages
    avg_duration_ms: float = 0
    avg_latency_ms: float = 0

    # Battery impact
    total_battery_drain: float = 0
    avg_battery_drain_per_event: float = 0

    # Resource usage
    avg_memory_mb: float = 0
    avg_storage_mb: float = 0

    # Connection breakdown
    connection_types: Dict[str, int] = field(default_factory=dict)

    # Event type breakdown
    event_types: Dict[str, int] = field(default_factory=dict)

    # Performance percentiles
    latency_p50: float = 0
    latency_p95: float = 0
    latency_p99: float = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return asdict(self)


class MobileTelemetryCollector:
    """
    Collects and aggregates mobile telemetry data.

    Provides insights into:
    - Bandwidth efficiency per operation type
    - Battery impact patterns
    - API latency distribution
    - Memory/storage trends
    - Network quality impact on performance
    """

    def __init__(self, storage_path: Optional[str] = None, max_events: int = 10000):
        """
        Initialize telemetry collector.

        Args:
            storage_path: Optional path to persist telemetry data
            max_events: Maximum events to keep in memory
        """
        self.storage_path = storage_path
        self.max_events = max_events

        # Event storage
        self._events: List[TelemetryEvent] = []
        self._lock = Lock()

        # Aggregated statistics cache
        self._cached_stats: Dict[str, AggregatedStats] = {}
        self._cache_lock = Lock()

        # Event counters by type
        self._event_counters: Dict[str, int] = defaultdict(int)

        logger.info(f"MobileTelemetryCollector initialized (max_events={max_events})")

    def record_event(self, event: TelemetryEvent) -> bool:
        """
        Record a telemetry event.

        Args:
            event: Telemetry event to record

        Returns:
            True if recorded successfully
        """
        try:
            with self._lock:
                self._events.append(event)
                self._event_counters[event.event_type] += 1

                # Prune old events if limit exceeded
                if len(self._events) > self.max_events:
                    overflow = len(self._events) - self.max_events
                    self._events = self._events[overflow:]
                    logger.debug(f"Pruned {overflow} old telemetry events")

                # Invalidate cached stats
                with self._cache_lock:
                    self._cached_stats.clear()

            return True

        except Exception as e:
            logger.error(f"Failed to record telemetry event: {e}")
            return False

    def record_sync_event(
        self,
        client_id: str,
        bytes_sent: int,
        bytes_received: int,
        duration_ms: float,
        connection_type: str,
        blocks_synced: int = 0,
        battery_start: Optional[float] = None,
        battery_end: Optional[float] = None
    ) -> None:
        """
        Record a sync operation event.

        Args:
            client_id: Anonymous device identifier
            bytes_sent: Bytes sent during sync
            bytes_received: Bytes received during sync
            duration_ms: Sync duration in milliseconds
            connection_type: Connection type (wifi/cellular/offline)
            blocks_synced: Number of blocks synchronized
            battery_start: Battery level at start (0-100)
            battery_end: Battery level at end (0-100)
        """
        event = TelemetryEvent(
            event_type='sync',
            timestamp=time.time(),
            client_id=client_id,
            bytes_sent=bytes_sent,
            bytes_received=bytes_received,
            duration_ms=duration_ms,
            connection_type=connection_type,
            battery_level_start=battery_start,
            battery_level_end=battery_end,
            metadata={'blocks_synced': blocks_synced}
        )
        self.record_event(event)

    def record_api_call(
        self,
        client_id: str,
        endpoint: str,
        method: str,
        bytes_sent: int,
        bytes_received: int,
        latency_ms: float,
        duration_ms: float,
        connection_type: str,
        status_code: int = 200
    ) -> None:
        """
        Record an API call event.

        Args:
            client_id: Anonymous device identifier
            endpoint: API endpoint path
            method: HTTP method (GET/POST/etc)
            bytes_sent: Request size in bytes
            bytes_received: Response size in bytes
            latency_ms: Network latency
            duration_ms: Total request duration
            connection_type: Connection type
            status_code: HTTP status code
        """
        event = TelemetryEvent(
            event_type='api_call',
            timestamp=time.time(),
            client_id=client_id,
            bytes_sent=bytes_sent,
            bytes_received=bytes_received,
            latency_ms=latency_ms,
            duration_ms=duration_ms,
            connection_type=connection_type,
            metadata={
                'endpoint': endpoint,
                'method': method,
                'status_code': status_code
            }
        )
        self.record_event(event)

    def record_transaction(
        self,
        client_id: str,
        tx_size_bytes: int,
        broadcast_latency_ms: float,
        connection_type: str,
        success: bool = True
    ) -> None:
        """
        Record a transaction broadcast event.

        Args:
            client_id: Anonymous device identifier
            tx_size_bytes: Transaction size in bytes
            broadcast_latency_ms: Time to broadcast transaction
            connection_type: Connection type
            success: Whether broadcast succeeded
        """
        event = TelemetryEvent(
            event_type='transaction',
            timestamp=time.time(),
            client_id=client_id,
            bytes_sent=tx_size_bytes,
            latency_ms=broadcast_latency_ms,
            duration_ms=broadcast_latency_ms,
            connection_type=connection_type,
            metadata={'success': success}
        )
        self.record_event(event)

    def record_resource_snapshot(
        self,
        client_id: str,
        memory_mb: float,
        storage_mb: float,
        connection_type: str
    ) -> None:
        """
        Record a resource usage snapshot.

        Args:
            client_id: Anonymous device identifier
            memory_mb: Memory usage in MB
            storage_mb: Storage usage in MB
            connection_type: Current connection type
        """
        event = TelemetryEvent(
            event_type='resource_snapshot',
            timestamp=time.time(),
            client_id=client_id,
            memory_mb=memory_mb,
            storage_mb=storage_mb,
            connection_type=connection_type
        )
        self.record_event(event)

    def get_stats(
        self,
        time_window_hours: Optional[int] = None,
        event_type: Optional[str] = None,
        connection_type: Optional[str] = None
    ) -> AggregatedStats:
        """
        Get aggregated statistics with optional filters.

        Args:
            time_window_hours: Only include events from last N hours
            event_type: Filter by event type
            connection_type: Filter by connection type

        Returns:
            Aggregated statistics
        """
        # Generate cache key
        cache_key = f"{time_window_hours}_{event_type}_{connection_type}"

        with self._cache_lock:
            if cache_key in self._cached_stats:
                return self._cached_stats[cache_key]

        # Filter events
        with self._lock:
            events = list(self._events)

        if time_window_hours:
            cutoff = time.time() - (time_window_hours * 3600)
            events = [e for e in events if e.timestamp >= cutoff]

        if event_type:
            events = [e for e in events if e.event_type == event_type]

        if connection_type:
            events = [e for e in events if e.connection_type == connection_type]

        if not events:
            return AggregatedStats(
                start_time=time.time(),
                end_time=time.time(),
                event_count=0
            )

        # Calculate aggregated statistics
        stats = self._calculate_stats(events)

        # Cache results
        with self._cache_lock:
            self._cached_stats[cache_key] = stats

        return stats

    def _calculate_stats(self, events: List[TelemetryEvent]) -> AggregatedStats:
        """Calculate aggregated statistics from event list"""

        total_bytes_sent = sum(e.bytes_sent for e in events)
        total_bytes_received = sum(e.bytes_received for e in events)

        # Duration averages
        durations = [e.duration_ms for e in events if e.duration_ms > 0]
        avg_duration = sum(durations) / len(durations) if durations else 0

        # Latency averages and percentiles
        latencies = [e.latency_ms for e in events if e.latency_ms > 0]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0

        sorted_latencies = sorted(latencies) if latencies else [0]
        latency_p50 = sorted_latencies[int(len(sorted_latencies) * 0.50)] if sorted_latencies else 0
        latency_p95 = sorted_latencies[int(len(sorted_latencies) * 0.95)] if sorted_latencies else 0
        latency_p99 = sorted_latencies[int(len(sorted_latencies) * 0.99)] if sorted_latencies else 0

        # Battery drain
        battery_drains = [e.battery_drain() for e in events if e.battery_drain() is not None]
        total_battery_drain = sum(battery_drains) if battery_drains else 0
        avg_battery_drain = total_battery_drain / len(battery_drains) if battery_drains else 0

        # Memory and storage
        memory_values = [e.memory_mb for e in events if e.memory_mb is not None]
        avg_memory = sum(memory_values) / len(memory_values) if memory_values else 0

        storage_values = [e.storage_mb for e in events if e.storage_mb is not None]
        avg_storage = sum(storage_values) / len(storage_values) if storage_values else 0

        # Connection type breakdown
        connection_types: Dict[str, int] = defaultdict(int)
        for e in events:
            if e.connection_type:
                connection_types[e.connection_type] += 1

        # Event type breakdown
        event_types: Dict[str, int] = defaultdict(int)
        for e in events:
            event_types[e.event_type] += 1

        return AggregatedStats(
            start_time=min(e.timestamp for e in events),
            end_time=max(e.timestamp for e in events),
            event_count=len(events),
            total_bytes_sent=total_bytes_sent,
            total_bytes_received=total_bytes_received,
            avg_duration_ms=avg_duration,
            avg_latency_ms=avg_latency,
            total_battery_drain=total_battery_drain,
            avg_battery_drain_per_event=avg_battery_drain,
            avg_memory_mb=avg_memory,
            avg_storage_mb=avg_storage,
            connection_types=dict(connection_types),
            event_types=dict(event_types),
            latency_p50=latency_p50,
            latency_p95=latency_p95,
            latency_p99=latency_p99
        )

    def get_bandwidth_by_operation(self) -> Dict[str, Dict[str, int]]:
        """
        Get bandwidth usage breakdown by operation type.

        Returns:
            Dict mapping event_type to {bytes_sent, bytes_received, total}
        """
        breakdown: Dict[str, Dict[str, int]] = defaultdict(
            lambda: {'bytes_sent': 0, 'bytes_received': 0, 'total': 0}
        )

        with self._lock:
            for event in self._events:
                breakdown[event.event_type]['bytes_sent'] += event.bytes_sent
                breakdown[event.event_type]['bytes_received'] += event.bytes_received
                breakdown[event.event_type]['total'] += event.total_bytes()

        return dict(breakdown)

    def get_battery_impact_by_operation(self) -> Dict[str, Dict[str, float]]:
        """
        Get battery impact breakdown by operation type.

        Returns:
            Dict mapping event_type to {total_drain, avg_drain, event_count}
        """
        breakdown: Dict[str, List[float]] = defaultdict(list)

        with self._lock:
            for event in self._events:
                drain = event.battery_drain()
                if drain is not None:
                    breakdown[event.event_type].append(drain)

        result = {}
        for event_type, drains in breakdown.items():
            result[event_type] = {
                'total_drain': sum(drains),
                'avg_drain': sum(drains) / len(drains) if drains else 0,
                'event_count': len(drains)
            }

        return result

    def get_performance_trends(
        self,
        hours: int = 24,
        bucket_size_minutes: int = 60
    ) -> List[Dict[str, Any]]:
        """
        Get performance trends over time.

        Args:
            hours: Number of hours to analyze
            bucket_size_minutes: Time bucket size in minutes

        Returns:
            List of time buckets with aggregated metrics
        """
        cutoff = time.time() - (hours * 3600)
        bucket_size_seconds = bucket_size_minutes * 60

        with self._lock:
            events = [e for e in self._events if e.timestamp >= cutoff]

        if not events:
            return []

        # Group events into time buckets
        buckets: Dict[int, List[TelemetryEvent]] = defaultdict(list)
        for event in events:
            bucket_id = int(event.timestamp / bucket_size_seconds)
            buckets[bucket_id].append(event)

        # Calculate stats for each bucket
        trends = []
        for bucket_id in sorted(buckets.keys()):
            bucket_events = buckets[bucket_id]
            stats = self._calculate_stats(bucket_events)

            trends.append({
                'timestamp': bucket_id * bucket_size_seconds,
                'event_count': len(bucket_events),
                'avg_latency_ms': stats.avg_latency_ms,
                'total_bytes': stats.total_bytes_sent + stats.total_bytes_received,
                'avg_battery_drain': stats.avg_battery_drain_per_event
            })

        return trends

    def clear_events(self) -> int:
        """
        Clear all stored events.

        Returns:
            Number of events cleared
        """
        with self._lock:
            count = len(self._events)
            self._events.clear()
            self._event_counters.clear()

        with self._cache_lock:
            self._cached_stats.clear()

        logger.info(f"Cleared {count} telemetry events")
        return count

    def export_events(self, max_events: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Export events as dictionaries.

        Args:
            max_events: Maximum number of recent events to export

        Returns:
            List of event dictionaries
        """
        with self._lock:
            events = self._events[-max_events:] if max_events else self._events
            return [e.to_dict() for e in events]

    def get_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive telemetry summary.

        Returns:
            Summary dictionary with all key metrics
        """
        overall_stats = self.get_stats()
        bandwidth_by_op = self.get_bandwidth_by_operation()
        battery_by_op = self.get_battery_impact_by_operation()

        return {
            'overall': overall_stats.to_dict(),
            'bandwidth_by_operation': bandwidth_by_op,
            'battery_by_operation': battery_by_op,
            'total_events': len(self._events),
            'event_type_counts': dict(self._event_counters),
            'collection_period': {
                'start': overall_stats.start_time,
                'end': overall_stats.end_time,
                'duration_hours': (overall_stats.end_time - overall_stats.start_time) / 3600
            }
        }
