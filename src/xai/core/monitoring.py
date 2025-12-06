"""
XAI Blockchain - Monitoring and Metrics System

Comprehensive monitoring with:
- Prometheus-compatible metrics
- Health check endpoints
- Performance monitoring
- Alert system
- Real-time metrics collection
"""

import time
import threading
import psutil
import os
import json
import logging
from typing import Dict, Any, List, Optional, Callable, Tuple
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from enum import Enum
from xai.core.config import Config
from xai.core.security_validation import SecurityEventRouter

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Metric types"""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


class AlertLevel(Enum):
    """Alert severity levels"""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class Metric:
    """Base metric class"""

    def __init__(
        self, name: str, description: str, metric_type: MetricType, labels: Dict[str, str] = None
    ):
        """
        Initialize metric

        Args:
            name: Metric name
            description: Metric description
            metric_type: Type of metric
            labels: Optional labels for the metric
        """
        self.name = name
        self.description = description
        self.metric_type = metric_type
        if isinstance(labels, dict):
            self.labels = labels
        elif isinstance(labels, (list, tuple, set)):
            self.labels = {str(label): "" for label in labels}
        else:
            self.labels = {}
        self.value = 0
        self.timestamp = time.time()

    def to_prometheus(self) -> str:
        """Convert metric to Prometheus format"""
        label_str = ",".join([f'{k}="{v}"' for k, v in self.labels.items()])
        label_part = f"{{{label_str}}}" if label_str else ""

        lines = [
            f"# HELP {self.name} {self.description}",
            f"# TYPE {self.name} {self.metric_type.value}",
            f"{self.name}{label_part} {self.value}",
        ]
        return "\n".join(lines)


class Counter(Metric):
    """Counter metric - monotonically increasing value"""

    def __init__(self, name: str, description: str, labels: Dict[str, str] = None):
        super().__init__(name, description, MetricType.COUNTER, labels)

    def inc(self, amount: float = 1.0):
        """Increment counter"""
        self.value += amount
        self.timestamp = time.time()

    def reset(self):
        """Reset counter to zero"""
        self.value = 0
        self.timestamp = time.time()


class Gauge(Metric):
    """Gauge metric - can go up or down"""

    def __init__(self, name: str, description: str, labels: Dict[str, str] = None):
        super().__init__(name, description, MetricType.GAUGE, labels)

    def set(self, value: float):
        """Set gauge value"""
        self.value = value
        self.timestamp = time.time()

    def inc(self, amount: float = 1.0):
        """Increment gauge"""
        self.value += amount
        self.timestamp = time.time()

    def dec(self, amount: float = 1.0):
        """Decrement gauge"""
        self.value -= amount
        self.timestamp = time.time()


class Histogram(Metric):
    """Histogram metric - tracks distribution of values"""

    def __init__(
        self,
        name: str,
        description: str,
        buckets: List[float] = None,
        labels: Dict[str, str] = None,
    ):
        super().__init__(name, description, MetricType.HISTOGRAM, labels)
        self.buckets = buckets or [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
        self.bucket_counts = defaultdict(int)
        self.sum = 0
        self.count = 0

        # Optional per-label series (keyed by sorted label tuples)
        self._labeled_series: Dict[Tuple[Tuple[str, str], ...], Dict[str, Any]] = {}

    def observe(self, value: float, labels: Optional[Dict[str, Any]] = None):
        """Observe a value, optionally tracking per-label buckets."""

        def _record(target_buckets: Dict[float, int], series: Dict[str, Any]) -> None:
            for bucket in self.buckets:
                if value <= bucket:
                    target_buckets[bucket] += 1
            series["sum"] += value
            series["count"] += 1

        if labels:
            key = tuple(sorted((str(k), str(v)) for k, v in labels.items()))
            series = self._labeled_series.setdefault(
                key,
                {
                    "bucket_counts": defaultdict(int),
                    "sum": 0.0,
                    "count": 0,
                    "labels": {**self.labels, **{str(k): str(v) for k, v in labels.items()}},
                },
            )
            _record(series["bucket_counts"], series)
            series["timestamp"] = time.time()
        else:
            base_series = {"sum": self.sum, "count": self.count}
            _record(self.bucket_counts, base_series)
            self.sum = base_series["sum"]
            self.count = base_series["count"]
            self.timestamp = time.time()

    def to_prometheus(self) -> str:
        """Convert histogram to Prometheus format"""
        lines = [f"# HELP {self.name} {self.description}", f"# TYPE {self.name} histogram"]

        def _emit_series(label_map: Dict[str, Any], bucket_counts: Dict[float, int], count: int, total_sum: float) -> None:
            normalized_labels = {str(k): str(v) for k, v in label_map.items() if v != ""}
            label_str = ",".join([f'{k}="{v}"' for k, v in normalized_labels.items()])
            base_labels = f"{{{label_str}}}" if label_str else ""
            for bucket in sorted(self.buckets):
                bucket_label_entries = dict(normalized_labels)
                bucket_label_entries["le"] = str(bucket)
                bucket_label_str = ",".join([f'{k}="{v}"' for k, v in bucket_label_entries.items()])
                lines.append(f"{self.name}_bucket{{{bucket_label_str}}} {bucket_counts.get(bucket, 0)}")
            inf_label_entries = dict(normalized_labels)
            inf_label_entries["le"] = "+Inf"
            inf_label_str = ",".join([f'{k}="{v}"' for k, v in inf_label_entries.items()])
            lines.append(f"{self.name}_bucket{{{inf_label_str}}} {count}")
            lines.append(f"{self.name}_sum{base_labels} {total_sum}")
            lines.append(f"{self.name}_count{base_labels} {count}")

        _emit_series(self.labels, self.bucket_counts, self.count, self.sum)
        for series in self._labeled_series.values():
            _emit_series(series["labels"], series["bucket_counts"], series["count"], series["sum"])

        return "\n".join(lines)


class Alert:
    """Alert representation"""

    def __init__(
        self,
        name: str,
        message: str,
        level: AlertLevel,
        metric_name: str = None,
        threshold: float = None,
        current_value: float = None,
    ):
        """
        Initialize alert

        Args:
            name: Alert name
            message: Alert message
            level: Alert severity level
            metric_name: Associated metric name
            threshold: Threshold value that triggered alert
            current_value: Current metric value
        """
        self.name = name
        self.message = message
        self.level = level
        self.metric_name = metric_name
        self.threshold = threshold
        self.current_value = current_value
        self.timestamp = datetime.now(timezone.utc)
        self.active = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary"""
        return {
            "name": self.name,
            "message": self.message,
            "level": self.level.value,
            "metric_name": self.metric_name,
            "threshold": self.threshold,
            "current_value": self.current_value,
            "timestamp": self.timestamp.isoformat(),
            "active": self.active,
        }


from xai.core.blockchain_interface import BlockchainDataProvider


class _LazyBlockchainProvider:
    """
    Adapter that fetches fresh blockchain stats on every call, whether provided
    a full Blockchain or a lightweight data provider.
    """

    def __init__(self, source: Any):
        self._source = source

    def get_stats(self) -> Dict[str, Any]:
        """Return up-to-date blockchain stats."""
        if hasattr(self._source, "get_blockchain_data_provider"):
            try:
                provider = self._source.get_blockchain_data_provider()
                if provider:
                    return provider.get_stats()
            except (AttributeError, TypeError) as e:
                # Fall back to direct get_stats if provider snapshot fails
                logger.debug(f"Blockchain data provider snapshot unavailable: {e}")

        if hasattr(self._source, "get_stats") and callable(self._source.get_stats):
            return self._source.get_stats()

        raise AttributeError("Blockchain provider does not expose get_stats()")

class MetricsCollector:
    """
    Main metrics collection system

    Tracks:
    - Blockchain metrics (blocks, transactions)
    - Network metrics (peers, messages)
    - System metrics (CPU, memory)
    - Performance metrics (mining, validation)
    """

    def __init__(self, blockchain_data_provider=None, update_interval: int = 5, blockchain=None):
        """
        Initialize metrics collector

        Args:
            blockchain_data_provider: Object conforming to BlockchainDataProvider interface
            update_interval: Interval in seconds to update system metrics
            blockchain: Backward-compatible arg for callers passing a Blockchain directly
        """
        provider = blockchain_data_provider or blockchain
        resolved_provider, blockchain_ref = self._resolve_blockchain_provider(provider)
        self.blockchain_data_provider = resolved_provider
        # Backward-compat attribute used in some integration paths
        self.blockchain = blockchain_ref
        self.update_interval = update_interval

        # Metrics registry
        self.metrics: Dict[str, Metric] = {}

        # Alert system
        self.alerts: List[Alert] = []
        self.alert_rules = []
        self.max_alerts = 100
        self._last_mempool_rejected_invalid = 0
        self._last_mempool_rejected_banned = 0
        self._last_active_bans_alert_value = 0
        self._mempool_alert_invalid_delta = getattr(Config, "MEMPOOL_ALERT_INVALID_DELTA", 50)
        self._mempool_alert_ban_delta = getattr(Config, "MEMPOOL_ALERT_BAN_DELTA", 10)
        self._mempool_alert_active_bans = getattr(Config, "MEMPOOL_ALERT_ACTIVE_BANS", 1)

        # Initialize metrics
        self._initialize_metrics()

        # Start background monitoring
        self.monitoring_active = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()

        # Performance tracking
        self.block_times = deque(maxlen=100)
        self.tx_processing_times = deque(maxlen=1000)
        self.recent_security_events = deque(maxlen=100)
        self.withdrawal_events = deque()
        self.recent_withdrawal_events = deque(maxlen=50)
        default_log_path = os.environ.get("XAI_WITHDRAWAL_EVENT_LOG", "monitoring/withdrawals_events.jsonl").strip()
        self.withdrawal_event_log_path = default_log_path or None

        MetricsCollector._instance = self

    def _initialize_metrics(self):
        """Initialize all metrics"""

        # Blockchain metrics
        self.register_counter("xai_blocks_mined_total", "Total number of blocks mined")
        self.register_counter(
            "xai_transactions_processed_total", "Total number of transactions processed"
        )
        self.register_gauge("xai_chain_height", "Current blockchain height")
        self.register_gauge("xai_difficulty", "Current mining difficulty")
        self.register_gauge("xai_pending_transactions", "Number of pending transactions in mempool")
        self.register_gauge("xai_total_supply", "Total XAI in circulation")
        self.register_histogram(
            "xai_block_timestamp_median_drift_seconds",
            "Difference between block timestamp and rolling median time past",
            buckets=[
                -1200,
                -600,
                -300,
                -120,
                -60,
                -30,
                -10,
                -1,
                0,
                1,
                10,
                30,
                60,
                120,
                300,
                600,
                1200,
            ],
        )
        self.register_histogram(
            "xai_block_timestamp_wall_clock_drift_seconds",
            "Difference between block timestamp and system clock",
            buckets=[-7200, -3600, -1200, -600, -300, -120, -60, -30, -10, 0, 10, 30, 60, 120, 300, 600, 1200, 3600, 7200],
        )
        self.register_gauge(
            "xai_block_timestamp_history_entries",
            "Number of timestamp drift samples stored in memory",
        )

        # Network metrics
        self.register_gauge("xai_peers_connected", "Number of connected peers")
        self.register_counter("xai_p2p_messages_received_total", "Total P2P messages received")
        self.register_counter("xai_p2p_messages_sent_total", "Total P2P messages sent")
        self.register_counter("xai_blocks_received_total", "Total blocks received from network")
        self.register_counter("xai_blocks_propagated_total", "Total blocks propagated to network")

        # Performance metrics
        self.register_histogram(
            "xai_block_mining_duration_seconds",
            "Time taken to mine a block",
            buckets=[1, 5, 10, 30, 60, 120, 300, 600],
        )
        self.register_histogram(
            "xai_block_propagation_duration_seconds",
            "Time taken for block to propagate",
            buckets=[0.1, 0.5, 1, 2, 5, 10],
        )
        self.register_histogram(
            "xai_transaction_validation_duration_seconds",
            "Time taken to validate a transaction",
            buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0],
        )
        self.register_gauge("xai_mempool_size_bytes", "Size of transaction mempool in bytes")
        self.register_counter(
            "xai_mempool_rejected_invalid_total",
            "Total transactions rejected as invalid at mempool admission",
        )
        self.register_counter(
            "xai_mempool_rejected_banned_total",
            "Total transactions rejected due to sender ban",
        )
        self.register_counter(
            "xai_mempool_rejected_low_fee_total",
            "Total transactions rejected due to low fee rate or full mempool",
        )
        self.register_counter(
            "xai_mempool_rejected_sender_cap_total",
            "Total transactions rejected due to per-sender cap",
        )
        self.register_counter(
            "xai_mempool_evicted_low_fee_total",
            "Total transactions evicted for low fee rate when mempool full",
        )
        self.register_counter(
            "xai_mempool_expired_total",
            "Total transactions expired out of mempool",
        )
        self.register_counter(
            "xai_send_rejections_stale_timestamp_total",
            "Total /send requests rejected due to stale timestamps",
        )
        self.register_counter(
            "xai_send_rejections_future_timestamp_total",
            "Total /send requests rejected due to future timestamps",
        )
        self.register_counter(
            "xai_send_rejections_txid_mismatch_total",
            "Total /send requests rejected due to TXID mismatch",
        )
        self.register_gauge(
            "xai_mempool_active_bans",
            "Number of senders currently rate-limited/banned from mempool",
        )
        self.register_gauge("xai_mining_rate_blocks_per_second", "Blocks mined per second")
        self.register_gauge("xai_orphan_blocks", "Number of orphan blocks")
        self.register_gauge("xai_orphan_transactions", "Number of orphan transactions")

        # System metrics
        self.register_gauge("xai_node_cpu_usage_percent", "Node CPU usage percentage")
        self.register_gauge("xai_node_memory_usage_bytes", "Node memory usage in bytes")
        self.register_gauge("xai_node_memory_usage_percent", "Node memory usage percentage")
        self.register_gauge("xai_node_disk_usage_bytes", "Node disk usage in bytes")
        self.register_gauge("xai_node_uptime_seconds", "Node uptime in seconds")

        # API metrics
        self.register_counter("xai_api_requests_total", "Total API requests received")
        self.register_counter("xai_api_errors_total", "Total API errors")
        self.register_histogram(
            "xai_api_request_duration_seconds",
            "API request duration",
            buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
        )
        self.register_histogram(
            "xai_api_endpoint_latency_seconds",
            "API endpoint latency",
            buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
            labels=["endpoint"],
        )

        # Faucet metrics
        self.register_counter(
            "xai_faucet_claims_total", "Total faucet claims processed successfully"
        )
        self.register_counter("xai_faucet_errors_total", "Total faucet claim errors recorded")

        # Security metrics
        self.register_counter("xai_security_events_total", "Total security events recorded")
        self.register_counter(
            "xai_security_events_warning_total", "Security warnings recorded"
        )
        self.register_counter(
            "xai_security_events_critical_total", "Security critical alerts recorded"
        )

        # Withdrawal metrics
        self.register_counter(
            "xai_withdrawals_daily_total", "Daily withdrawal transactions recorded"
        )
        self.register_gauge(
            "xai_withdrawals_rate_per_minute",
            "Rolling one-minute window of approved withdrawals",
        )
        self.register_counter(
            "xai_withdrawals_time_locked_total", "Time-locked withdrawal requests"
        )
        self.register_gauge(
            "xai_withdrawals_time_locked_backlog", "Number of pending time-locked withdrawals"
        )
        self.register_counter(
            "xai_withdrawal_processor_completed_total",
            "Total withdrawals completed by the exchange withdrawal processor",
        )
        self.register_counter(
            "xai_withdrawal_processor_flagged_total",
            "Total withdrawals flagged for manual review by the processor",
        )
        self.register_counter(
            "xai_withdrawal_processor_failed_total",
            "Total withdrawals rejected by the processor",
        )
        self.register_gauge(
            "xai_withdrawal_pending_queue", "Current pending exchange withdrawal queue depth"
        )
        # Crypto deposit metrics
        self.register_counter(
            "xai_crypto_deposit_events_total",
            "Total crypto deposit events processed by the monitor",
        )
        self.register_counter(
            "xai_crypto_deposit_credited_total",
            "Total crypto deposits credited to exchange wallets",
        )
        self.register_gauge(
            "xai_crypto_deposit_pending_events",
            "Number of crypto deposits awaiting confirmations",
        )
        self.register_counter(
            "xai_crypto_deposit_errors_total",
            "Total crypto deposit monitoring errors",
        )

        # Consensus metrics
        self.register_counter("xai_consensus_forks_total", "Total number of chain forks detected")
        self.register_counter("xai_consensus_reorgs_total", "Total number of chain reorganizations")
        self.register_gauge("xai_consensus_finalized_height", "Height of last finalized block")
        self.register_counter("xai_p2p_nonce_replay_total", "Total P2P messages rejected due to nonce replay")
        self.register_counter("xai_p2p_rate_limited_total", "Total P2P messages dropped due to rate limits")
        self.register_counter("xai_p2p_invalid_signature_total", "Total P2P messages rejected for invalid or stale signatures")
        self.register_counter("xai_p2p_quic_errors_total", "Total QUIC transport errors detected")
        self.register_counter("xai_p2p_quic_timeouts_total", "Total QUIC dial/send timeouts detected")

        # Start time for uptime calculation
        self.start_time = time.time()

    @classmethod
    def instance(
        cls,
        blockchain_data_provider: Optional[Any] = None,
        blockchain: Optional[Any] = None,
        update_interval: int = 5,
    ) -> "MetricsCollector":
        """
        Return or create the singleton MetricsCollector, optionally injecting
        a blockchain reference for compatibility with integration paths.
        """
        if not hasattr(cls, "_instance") or cls._instance is None:
            cls._instance = cls(
                blockchain_data_provider=blockchain_data_provider or blockchain,
                update_interval=update_interval,
            )
        elif blockchain_data_provider or blockchain:
            cls._instance.attach_blockchain(blockchain_data_provider or blockchain)
        return cls._instance

    def register_counter(
        self, name: str, description: str, labels: Dict[str, str] = None
    ) -> Counter:
        """Register a counter metric"""
        counter = Counter(name, description, labels)
        self.metrics[name] = counter
        return counter

    def register_gauge(self, name: str, description: str, labels: Dict[str, str] = None) -> Gauge:
        """Register a gauge metric"""
        gauge = Gauge(name, description, labels)
        self.metrics[name] = gauge
        return gauge

    def register_histogram(
        self,
        name: str,
        description: str,
        buckets: List[float] = None,
        labels: Dict[str, str] = None,
    ) -> Histogram:
        """Register a histogram metric"""
        histogram = Histogram(name, description, buckets, labels)
        self.metrics[name] = histogram
        return histogram

    def get_metric(self, name: str) -> Optional[Metric]:
        """Get metric by name"""
        return self.metrics.get(name)

    def _set_metric_if_present(self, name: str, value: Any) -> None:
        metric = self.metrics.get(name)
        if metric is None or value is None:
            return
        try:
            if isinstance(metric, Gauge):
                metric.set(value)
            elif isinstance(metric, Counter):
                # Counters are monotonic; set only forward
                if value >= metric.value:
                    metric.value = value
                    metric.timestamp = time.time()
            else:
                metric.value = value
                metric.timestamp = time.time()
        except (TypeError, ValueError, AttributeError) as e:
            # Metric update failed - log but don't break monitoring
            logger.debug(f"Failed to set metric {name}: {e}")

    def record_send_rejection(self, reason: str) -> None:
        """Increment /send rejection counters by reason."""
        name = {
            "stale_timestamp": "xai_send_rejections_stale_timestamp_total",
            "future_timestamp": "xai_send_rejections_future_timestamp_total",
            "txid_mismatch": "xai_send_rejections_txid_mismatch_total",
        }.get(reason)
        if not name:
            return
        metric = self.metrics.get(name)
        if isinstance(metric, Counter):
            metric.inc()

    def _process_mempool_alert_state(self, stats: Dict[str, Any]) -> None:
        """
        Derive alert conditions from mempool rejection/ban metrics.
        """
        invalid_total = stats.get("mempool_rejected_invalid_total")
        if invalid_total is not None:
            delta_invalid = max(0, invalid_total - self._last_mempool_rejected_invalid)
            if delta_invalid >= self._mempool_alert_invalid_delta:
                self._fire_alert(
                    "mempool.invalid_rejections_surge",
                    f"Detected {delta_invalid} invalid mempool rejections in the last interval",
                    AlertLevel.WARNING,
                )
            self._last_mempool_rejected_invalid = invalid_total

        banned_total = stats.get("mempool_rejected_banned_total")
        if banned_total is not None:
            delta_banned = max(0, banned_total - self._last_mempool_rejected_banned)
            if delta_banned >= self._mempool_alert_ban_delta:
                self._fire_alert(
                    "mempool.banned_senders_surge",
                    f"Detected {delta_banned} submissions from banned senders in the last interval",
                    AlertLevel.WARNING,
                )
            self._last_mempool_rejected_banned = banned_total

        active_bans = stats.get("mempool_active_bans")
        if active_bans is not None:
            if (
                active_bans >= self._mempool_alert_active_bans
                and active_bans != self._last_active_bans_alert_value
            ):
                self._fire_alert(
                    "mempool.active_bans",
                    f"{active_bans} senders currently rate-limited from mempool",
                    AlertLevel.WARNING,
                )
            self._last_active_bans_alert_value = active_bans

    def _resolve_blockchain_provider(self, provider: Optional[Any]) -> tuple[Optional[Any], Optional[Any]]:
        """
        Normalize blockchain provider inputs and keep a reference to the original
        blockchain (when available) to satisfy callers expecting a .blockchain attribute.
        """
        if provider is None:
            return None, None

        if hasattr(provider, "get_blockchain_data_provider") or hasattr(provider, "get_stats"):
            return _LazyBlockchainProvider(provider), provider

        if isinstance(provider, BlockchainDataProvider):
            return provider, provider

        if hasattr(provider, "get_stats"):
            return provider, provider

        return None, None

    def attach_blockchain(self, provider: Any) -> None:
        """
        Attach or swap the blockchain provider post-initialization.
        """
        resolved, original = self._resolve_blockchain_provider(provider)
        self.blockchain_data_provider = resolved
        self.blockchain = original

    def _monitor_loop(self):
        """Background monitoring loop"""
        while self.monitoring_active:
            try:
                self._update_system_metrics()
                if self.blockchain_data_provider:
                    self._update_blockchain_metrics()
                self._check_alert_rules()
                time.sleep(self.update_interval)
            except Exception as exc:  # pragma: no cover - defensive
                logger.error(
                    "Error in monitoring loop: %s",
                    exc,
                    extra={"event": "monitoring.loop_error"},
                    exc_info=True,
                )

    def _update_system_metrics(self):
        """Update system resource metrics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            self.get_metric("xai_node_cpu_usage_percent").set(cpu_percent)

            # Memory usage
            memory = psutil.virtual_memory()
            self.get_metric("xai_node_memory_usage_bytes").set(memory.used)
            self.get_metric("xai_node_memory_usage_percent").set(memory.percent)

            # Disk usage
            disk = psutil.disk_usage("/")
            self.get_metric("xai_node_disk_usage_bytes").set(disk.used)

            # Uptime
            uptime = time.time() - self.start_time
            self.get_metric("xai_node_uptime_seconds").set(uptime)

        except Exception as exc:
            logger.error(
                "Error updating system metrics: %s",
                exc,
                extra={"event": "monitoring.system_metrics_failed"},
                exc_info=True,
            )

    def _update_blockchain_metrics(self):
        """Update blockchain-specific metrics"""
        if not self.blockchain_data_provider:
            return

        try:
            stats = self.blockchain_data_provider.get_stats()

            # Chain height
            self.get_metric("xai_chain_height").set(stats["chain_height"])

            # Difficulty
            self.get_metric("xai_difficulty").set(stats["difficulty"])

            # Pending transactions
            self.get_metric("xai_pending_transactions").set(stats["pending_transactions_count"])
            
            # Mempool size
            self.get_metric("xai_mempool_size_bytes").set(stats["mempool_size_bytes"])
            self._set_metric_if_present(
                "xai_mempool_rejected_invalid_total",
                stats.get("mempool_rejected_invalid_total"),
            )
            self._set_metric_if_present(
                "xai_mempool_rejected_banned_total",
                stats.get("mempool_rejected_banned_total"),
            )
            self._set_metric_if_present(
                "xai_mempool_rejected_low_fee_total",
                stats.get("mempool_rejected_low_fee_total"),
            )
            self._set_metric_if_present(
                "xai_mempool_rejected_sender_cap_total",
                stats.get("mempool_rejected_sender_cap_total"),
            )
            self._set_metric_if_present(
                "xai_mempool_evicted_low_fee_total",
                stats.get("mempool_evicted_low_fee_total"),
            )
            self._set_metric_if_present(
                "xai_mempool_expired_total",
                stats.get("mempool_expired_total"),
            )
            self._set_metric_if_present(
                "xai_mempool_active_bans",
                stats.get("mempool_active_bans"),
            )
            self._process_mempool_alert_state(stats)

            # Orphan blocks
            self.get_metric("xai_orphan_blocks").set(stats["orphan_blocks_count"])

            # Orphan transactions
            self.get_metric("xai_orphan_transactions").set(stats["orphan_transactions_count"])

            # Total supply
            self.get_metric("xai_total_supply").set(stats["total_circulating_supply"])

        except Exception as exc:
            logger.error(
                "Error updating blockchain metrics: %s",
                exc,
                extra={"event": "monitoring.blockchain_metrics_failed"},
                exc_info=True,
            )

    def record_block_mined(self, block_index: int, mining_time: float = None):
        """Record block mining event"""
        self.get_metric("xai_blocks_mined_total").inc()
        self.get_metric("xai_chain_height").set(block_index)

        if mining_time:
            self.get_metric("xai_block_mining_duration_seconds").observe(mining_time)
            self.block_times.append(mining_time)

    def record_transaction_processed(self, processing_time: float = None):
        """Record transaction processing"""
        self.get_metric("xai_transactions_processed_total").inc()

        if processing_time:
            self.get_metric("xai_transaction_validation_duration_seconds").observe(processing_time)
            self.tx_processing_times.append(processing_time)

    def record_peer_connected(self, peer_count: int):
        """Record peer connection"""
        self.get_metric("xai_peers_connected").set(peer_count)

    def record_p2p_message(self, direction: str):
        """Record P2P message sent or received"""
        if direction == "sent":
            self.get_metric("xai_p2p_messages_sent_total").inc()
        else:
            self.get_metric("xai_p2p_messages_received_total").inc()

    def record_block_propagation(self, propagation_time: float):
        """Record block propagation time"""
        self.get_metric("xai_block_propagation_duration_seconds").observe(propagation_time)
        self.get_metric("xai_blocks_propagated_total").inc()

    def record_api_request(self, endpoint: str, duration: float, error: bool = False):
        """Record API request"""
        self.get_metric("xai_api_requests_total").inc()
        self.get_metric("xai_api_request_duration_seconds").observe(duration)

        if error:
            self.get_metric("xai_api_errors_total").inc()

    def record_faucet_result(self, success: bool):
        """Record faucet outcome for monitoring dashboards."""
        metric_name = "xai_faucet_claims_total" if success else "xai_faucet_errors_total"
        metric = self.get_metric(metric_name)
        if metric:
            metric.inc()

    def record_withdrawal(
        self, user_address: str, amount: float, timestamp: Optional[int] = None
    ) -> int:
        """Record an approved withdrawal and return the rolling per-minute rate."""
        counter = self.get_metric("xai_withdrawals_daily_total")
        if counter:
            counter.inc()

        now = float(timestamp if timestamp is not None else time.time())
        rate = self._record_withdrawal_rate_event(now)
        self._append_withdrawal_event(user_address, amount, now, rate)
        return rate

    def record_time_locked_request(self, pending_backlog: int):
        """Record a new time-locked withdrawal and refresh backlog gauges."""
        counter = self.get_metric("xai_withdrawals_time_locked_total")
        if counter:
            counter.inc()
        self.update_time_locked_backlog(pending_backlog)

    def update_time_locked_backlog(self, pending_backlog: int):
        """Set the gauge for pending time-locked withdrawals."""
        gauge = self.get_metric("xai_withdrawals_time_locked_backlog")
        if gauge:
            gauge.set(pending_backlog)

    def record_withdrawal_processor_stats(self, stats: Dict[str, Any], queue_depth: int) -> None:
        """Record counters and gauges emitted by the withdrawal processor."""
        if not stats:
            return
        completed = self.get_metric("xai_withdrawal_processor_completed_total")
        flagged = self.get_metric("xai_withdrawal_processor_flagged_total")
        failed = self.get_metric("xai_withdrawal_processor_failed_total")
        if completed:
            completed.inc(float(stats.get("completed", 0)))
        if flagged:
            flagged.inc(float(stats.get("flagged", 0)))
        if failed:
            failed.inc(float(stats.get("failed", 0)))
        queue_gauge = self.get_metric("xai_withdrawal_pending_queue")
        if queue_gauge:
            queue_gauge.set(queue_depth)

    def record_crypto_deposit_stats(self, stats: Dict[str, Any]) -> None:
        """Ingest crypto deposit monitor statistics into metrics."""
        if not stats:
            return
        processed = float(stats.get("processed", 0) or 0)
        credited = float(stats.get("credited", 0) or 0)
        pending = float(stats.get("pending", 0) or 0)
        errors = float(stats.get("errors", 0) or 0)

        events_counter = self.get_metric("xai_crypto_deposit_events_total")
        credited_counter = self.get_metric("xai_crypto_deposit_credited_total")
        pending_gauge = self.get_metric("xai_crypto_deposit_pending_events")
        errors_counter = self.get_metric("xai_crypto_deposit_errors_total")

        if events_counter and processed:
            events_counter.inc(processed)
        if credited_counter and credited:
            credited_counter.inc(credited)
        if pending_gauge is not None:
            pending_gauge.set(pending)
        if errors_counter and errors:
            errors_counter.inc(errors)

    def record_security_event(
        self, event_type: str, severity: str, payload: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record security events for alerting/metrics."""
        total = self.get_metric("xai_security_events_total")
        if total:
            total.inc()

        severity_normalized = (severity or "INFO").upper()
        if severity_normalized in {"WARNING", "WARN"}:
            metric = self.get_metric("xai_security_events_warning_total")
            if metric:
                metric.inc()
        elif severity_normalized in {"ERROR", "CRITICAL"}:
            metric = self.get_metric("xai_security_events_critical_total")
            if metric:
                metric.inc()

        if event_type.startswith("p2p.replay"):
            metric = self.get_metric("xai_p2p_nonce_replay_total")
            if metric:
                metric.inc()
        if event_type.startswith("p2p.rate_limited"):
            metric = self.get_metric("xai_p2p_rate_limited_total")
            if metric:
                metric.inc()
        if event_type.startswith("p2p.invalid_signature"):
            metric = self.get_metric("xai_p2p_invalid_signature_total")
            if metric:
                metric.inc()

        self.recent_security_events.appendleft(
            {
                "event_type": event_type,
                "severity": severity_normalized,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "details": payload or {},
            }
        )

        if severity_normalized in {"WARNING", "WARN", "ERROR", "CRITICAL"}:
            level = AlertLevel.WARNING if severity_normalized in {"WARNING", "WARN"} else AlertLevel.CRITICAL
            message = f"Security event {event_type} ({severity_normalized})"
            self._fire_alert(f"security.{event_type}", message, level)

    def _record_withdrawal_rate_event(self, timestamp: float) -> int:
        """Track withdrawals per minute for rate dashboards."""
        self.withdrawal_events.append(timestamp)
        cutoff = timestamp - 60
        while self.withdrawal_events and self.withdrawal_events[0] < cutoff:
            self.withdrawal_events.popleft()

        gauge = self.get_metric("xai_withdrawals_rate_per_minute")
        if gauge:
            gauge.set(len(self.withdrawal_events))
        return len(self.withdrawal_events)

    def _append_withdrawal_event(
        self, user_address: str, amount: float, timestamp: float, rate_per_minute: int
    ) -> None:
        event = {
            "timestamp": timestamp,
            "user": user_address,
            "amount": amount,
            "rate_per_minute": rate_per_minute,
        }
        self.recent_withdrawal_events.appendleft(event)

        if not self.withdrawal_event_log_path:
            return
        try:
            directory = os.path.dirname(self.withdrawal_event_log_path)
            if directory:
                os.makedirs(directory, exist_ok=True)
            with open(self.withdrawal_event_log_path, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(event))
                handle.write("\n")
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning(
                "Failed to append withdrawal event log: %s",
                exc,
                extra={"event": "monitoring.withdrawal_log_failed"},
            )

    def get_recent_withdrawals(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Return the most recent withdrawal events for alert context."""
        return list(list(self.recent_withdrawal_events)[:limit])

    def add_alert_rule(
        self, name: str, condition: Callable[[], bool], message: str, level: AlertLevel
    ):
        """
        Add alert rule

        Args:
            name: Alert name
            condition: Function that returns True if alert should fire
            message: Alert message
            level: Alert severity level
        """
        self.alert_rules.append(
            {"name": name, "condition": condition, "message": message, "level": level}
        )

    def _check_alert_rules(self):
        """Check all alert rules and fire alerts if needed"""
        for rule in self.alert_rules:
            try:
                if rule["condition"]():
                    self._fire_alert(rule["name"], rule["message"], rule["level"])
            except Exception as exc:
                logger.error(
                    "Error checking alert rule %s: %s",
                    rule.get("name", "<unknown>"),
                    exc,
                    extra={"event": "monitoring.alert_rule_error"},
                    exc_info=True,
                )

    def _fire_alert(self, name: str, message: str, level: AlertLevel):
        """Fire an alert"""
        alert = Alert(name, message, level)
        self.alerts.append(alert)

        # Keep only recent alerts
        if len(self.alerts) > self.max_alerts:
            self.alerts = self.alerts[-self.max_alerts :]

        # Log alert
        log_level = logging.WARNING if level != AlertLevel.INFO else logging.INFO
        if level == AlertLevel.CRITICAL:
            log_level = logging.CRITICAL
        logger.log(
            log_level,
            "%s: %s",
            name,
            message,
            extra={"event": "monitoring.alert", "alert_name": name, "severity": level.value},
        )
        try:
            SecurityEventRouter.dispatch(
                f"alert.{name}",
                {"message": message, "level": level.value},
                level.value.upper(),
            )
        except (AttributeError, RuntimeError, TypeError) as e:
            # Avoid alert-path failures breaking monitoring
            logger.debug(f"Failed to dispatch alert event: {e}")

    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get active alerts"""
        return [alert.to_dict() for alert in self.alerts if alert.active]

    def clear_alert(self, alert_name: str):
        """Clear alert by name"""
        for alert in self.alerts:
            if alert.name == alert_name:
                alert.active = False

    def export_prometheus(self) -> str:
        """
        Export all metrics in Prometheus format

        Returns:
            String in Prometheus exposition format
        """
        output = []
        for metric in self.metrics.values():
            output.append(metric.to_prometheus())
            output.append("")  # Empty line between metrics

        return "\n".join(output)

    def get_health_status(self) -> Dict[str, Any]:
        """
        Get health check status

        Returns:
            Health status dictionary
        """
        status = {
            "status": "healthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            "uptime_seconds": time.time() - self.start_time,
            "checks": {},
        }

        # Check system resources
        cpu_percent = self.get_metric("xai_node_cpu_usage_percent").value
        memory_percent = self.get_metric("xai_node_memory_usage_percent").value

        status["checks"]["cpu"] = {
            "status": "healthy" if cpu_percent < 90 else "degraded",
            "usage_percent": cpu_percent,
        }

        status["checks"]["memory"] = {
            "status": "healthy" if memory_percent < 90 else "degraded",
            "usage_percent": memory_percent,
        }

        # Check blockchain
        if self.blockchain:
            pending = self.get_metric("xai_pending_transactions").value
            status["checks"]["mempool"] = {
                "status": "healthy" if pending < 10000 else "degraded",
                "pending_transactions": pending,
            }

            chain_height = self.get_metric("xai_chain_height").value
            status["checks"]["blockchain"] = {"status": "healthy", "chain_height": chain_height}

        # Overall status
        if any(check["status"] == "degraded" for check in status["checks"].values()):
            status["status"] = "degraded"

        # Add active alerts
        active_alerts = self.get_active_alerts()
        if active_alerts:
            status["alerts"] = active_alerts
            if any(alert["level"] == "critical" for alert in active_alerts):
                status["status"] = "unhealthy"

        return status

    def get_stats(self) -> Dict[str, Any]:
        """Get monitoring statistics"""
        stats = {
            "metrics_count": len(self.metrics),
            "alerts_count": len([a for a in self.alerts if a.active]),
            "uptime_seconds": time.time() - self.start_time,
        }

        # Add metric values
        stats["metrics"] = {}
        for name, metric in self.metrics.items():
            if isinstance(metric, (Counter, Gauge)):
                stats["metrics"][name] = metric.value
            elif isinstance(metric, Histogram):
                stats["metrics"][name] = {
                    "count": metric.count,
                    "sum": metric.sum,
                    "avg": metric.sum / metric.count if metric.count > 0 else 0,
                }

        # Performance stats
        if self.block_times:
            stats["performance"] = {
                "avg_block_time": sum(self.block_times) / len(self.block_times),
                "avg_tx_processing_time": (
                    sum(self.tx_processing_times) / len(self.tx_processing_times)
                    if self.tx_processing_times
                    else 0
                ),
            }

        return stats

    def shutdown(self):
        """Shutdown monitoring system"""
        self.monitoring_active = False
        if self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)


# Example usage and testing
if __name__ == "__main__":
    logger.info("Testing Metrics Collector...")
    logger.info("=" * 70)

    # Create collector
    collector = MetricsCollector(update_interval=2)

    # Simulate some activity
    logger.info("Simulating blockchain activity...")

    for i in range(5):
        collector.record_block_mined(i + 1, mining_time=2.5)
        collector.record_transaction_processed(processing_time=0.05)
        collector.record_peer_connected(peer_count=3 + i)
        time.sleep(1)

    # Add alert rule
    def high_cpu_check():
        cpu = collector.get_metric("xai_node_cpu_usage_percent").value
        return cpu > 80

    collector.add_alert_rule(
        "high_cpu", high_cpu_check, "CPU usage is above 80%", AlertLevel.WARNING
    )

    # Get health status
    logger.info("Health Status:")
    health = collector.get_health_status()
    import json

    logger.info(json.dumps(health, indent=2))

    # Export Prometheus metrics
    logger.info("=" * 70)
    logger.info("Prometheus Metrics Export (sample):")
    logger.info("=" * 70)
    prom_output = collector.export_prometheus()
    # Print first 1000 chars
    logger.info("%s", prom_output[:1000])
    logger.info("... (truncated)")

    # Get stats
    logger.info("=" * 70)
    logger.info("Monitoring Statistics:")
    logger.info("=" * 70)
    stats = collector.get_stats()
    logger.info(json.dumps(stats, indent=2, default=str))

    # Shutdown
    logger.info("Shutting down...")
    collector.shutdown()
    logger.info("Done!")
