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
from typing import Dict, Any, List, Optional, Callable
from collections import defaultdict, deque
from datetime import datetime, timedelta
from enum import Enum


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
        self.labels = labels or {}
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

    def observe(self, value: float):
        """Observe a value"""
        self.sum += value
        self.count += 1

        for bucket in self.buckets:
            if value <= bucket:
                self.bucket_counts[bucket] += 1

        self.timestamp = time.time()

    def to_prometheus(self) -> str:
        """Convert histogram to Prometheus format"""
        label_str = ",".join([f'{k}="{v}"' for k, v in self.labels.items()])
        base_labels = f"{{{label_str}}}" if label_str else ""

        lines = [f"# HELP {self.name} {self.description}", f"# TYPE {self.name} histogram"]

        # Bucket counts
        for bucket in sorted(self.buckets):
            count = self.bucket_counts.get(bucket, 0)
            bucket_labels = f'le="{bucket}"'
            if label_str:
                bucket_labels = f"{label_str},{bucket_labels}"
            lines.append(f"{self.name}_bucket{{{bucket_labels}}} {count}")

        # +Inf bucket
        inf_labels = f'le="+Inf"'
        if label_str:
            inf_labels = f"{label_str},{inf_labels}"
        lines.append(f"{self.name}_bucket{{{inf_labels}}} {self.count}")

        # Sum and count
        lines.append(f"{self.name}_sum{base_labels} {self.sum}")
        lines.append(f"{self.name}_count{base_labels} {self.count}")

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
        self.timestamp = datetime.utcnow()
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


class MetricsCollector:
    """
    Main metrics collection system

    Tracks:
    - Blockchain metrics (blocks, transactions)
    - Network metrics (peers, messages)
    - System metrics (CPU, memory)
    - Performance metrics (mining, validation)
    """

    def __init__(self, blockchain=None, update_interval: int = 5):
        """
        Initialize metrics collector

        Args:
            blockchain: Blockchain instance to monitor
            update_interval: Interval in seconds to update system metrics
        """
        self.blockchain = blockchain
        self.update_interval = update_interval

        # Metrics registry
        self.metrics: Dict[str, Metric] = {}

        # Alert system
        self.alerts: List[Alert] = []
        self.alert_rules = []
        self.max_alerts = 100

        # Initialize metrics
        self._initialize_metrics()

        # Start background monitoring
        self.monitoring_active = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()

        # Performance tracking
        self.block_times = deque(maxlen=100)
        self.tx_processing_times = deque(maxlen=1000)

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

        # Consensus metrics
        self.register_counter("xai_consensus_forks_total", "Total number of chain forks detected")
        self.register_counter("xai_consensus_reorgs_total", "Total number of chain reorganizations")
        self.register_gauge("xai_consensus_finalized_height", "Height of last finalized block")

        # Start time for uptime calculation
        self.start_time = time.time()

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

    def _monitor_loop(self):
        """Background monitoring loop"""
        while self.monitoring_active:
            try:
                self._update_system_metrics()
                if self.blockchain:
                    self._update_blockchain_metrics()
                self._check_alert_rules()
                time.sleep(self.update_interval)
            except Exception as e:
                print(f"Error in monitoring loop: {e}")

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

        except Exception as e:
            print(f"Error updating system metrics: {e}")

    def _update_blockchain_metrics(self):
        """Update blockchain-specific metrics"""
        try:
            # Chain height
            chain_height = len(self.blockchain.chain)
            self.get_metric("xai_chain_height").set(chain_height)

            # Difficulty
            self.get_metric("xai_difficulty").set(self.blockchain.difficulty)

            # Pending transactions
            pending = len(self.blockchain.pending_transactions)
            self.get_metric("xai_pending_transactions").set(pending)

            # Total supply
            total_supply = (
                self.blockchain.get_total_circulating_supply()
                if hasattr(self.blockchain, "get_total_circulating_supply")
                else 0
            )
            self.get_metric("xai_total_supply").set(total_supply)

        except Exception as e:
            print(f"Error updating blockchain metrics: {e}")

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
            except Exception as e:
                print(f"Error checking alert rule {rule['name']}: {e}")

    def _fire_alert(self, name: str, message: str, level: AlertLevel):
        """Fire an alert"""
        alert = Alert(name, message, level)
        self.alerts.append(alert)

        # Keep only recent alerts
        if len(self.alerts) > self.max_alerts:
            self.alerts = self.alerts[-self.max_alerts :]

        # Log alert
        print(f"[ALERT {level.value.upper()}] {name}: {message}")

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
            "timestamp": datetime.utcnow().isoformat(),
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
    print("Testing Metrics Collector...")
    print("=" * 70)

    # Create collector
    collector = MetricsCollector(update_interval=2)

    # Simulate some activity
    print("\nSimulating blockchain activity...")

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
    print("\nHealth Status:")
    health = collector.get_health_status()
    import json

    print(json.dumps(health, indent=2))

    # Export Prometheus metrics
    print("\n" + "=" * 70)
    print("Prometheus Metrics Export (sample):")
    print("=" * 70)
    prom_output = collector.export_prometheus()
    # Print first 1000 chars
    print(prom_output[:1000])
    print("\n... (truncated)")

    # Get stats
    print("\n" + "=" * 70)
    print("Monitoring Statistics:")
    print("=" * 70)
    stats = collector.get_stats()
    print(json.dumps(stats, indent=2, default=str))

    # Shutdown
    print("\nShutting down...")
    collector.shutdown()
    print("Done!")
