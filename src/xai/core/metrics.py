"""
XAI Blockchain - Enhanced Metrics and Monitoring Module

Comprehensive metrics collection and exporting for production monitoring:
- Prometheus metrics export in standard format
- Structured JSON logging for log aggregation
- System resource monitoring
- Blockchain-specific metrics
- Performance monitoring with histograms and summaries
- Alert-ready metrics for critical conditions

This module provides the core monitoring infrastructure for the XAI blockchain,
supporting both real-time dashboards and long-term trend analysis.
"""

from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    Summary,
    Info,
    CollectorRegistry,
    generate_latest,
    REGISTRY,
)
import time
import psutil
import os
import json
import logging
import threading
from typing import Optional, Dict, Any, List
from datetime import datetime
from pythonjsonlogger import jsonlogger
from pathlib import Path


# ==================== STRUCTURED LOGGING SETUP ====================

class StructuredLogger:
    """Structured logging for JSON format output and log aggregation"""

    def __init__(self, name: str, log_file: Optional[str] = None):
        """
        Initialize structured logger.

        Args:
            name: Logger name
            log_file: Optional log file path for JSON logs
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)

        # Remove existing handlers to avoid duplicates
        self.logger.handlers = []

        # JSON formatter for structured logs
        json_formatter = jsonlogger.JsonFormatter(
            fmt="%(timestamp)s %(level)s %(name)s %(message)s"
        )

        # Console handler with JSON format
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(json_formatter)
        self.logger.addHandler(console_handler)

        # File handler with JSON format (if specified)
        if log_file:
            try:
                log_path = Path(log_file)
                log_path.parent.mkdir(parents=True, exist_ok=True)
                file_handler = logging.FileHandler(log_file)
                file_handler.setFormatter(json_formatter)
                self.logger.addHandler(file_handler)
            except Exception as e:
                print(f"Warning: Could not create file log handler: {e}")

    def log(
        self,
        level: str,
        message: str,
        **extra_fields: Any
    ) -> None:
        """
        Log a structured message with additional fields.

        Args:
            level: Log level (info, warning, error, debug)
            message: Log message
            **extra_fields: Additional fields to include in JSON
        """
        extra_fields["timestamp"] = datetime.utcnow().isoformat()
        extra_fields["message"] = message

        if level == "info":
            self.logger.info(message, extra=extra_fields)
        elif level == "warning":
            self.logger.warning(message, extra=extra_fields)
        elif level == "error":
            self.logger.error(message, extra=extra_fields)
        elif level == "debug":
            self.logger.debug(message, extra=extra_fields)
        elif level == "critical":
            self.logger.critical(message, extra=extra_fields)

    def info(self, message: str, **extra_fields: Any) -> None:
        """Log info level message"""
        self.log("info", message, **extra_fields)

    def warning(self, message: str, **extra_fields: Any) -> None:
        """Log warning level message"""
        self.log("warning", message, **extra_fields)

    def error(self, message: str, **extra_fields: Any) -> None:
        """Log error level message"""
        self.log("error", message, **extra_fields)

    def debug(self, message: str, **extra_fields: Any) -> None:
        """Log debug level message"""
        self.log("debug", message, **extra_fields)

    def critical(self, message: str, **extra_fields: Any) -> None:
        """Log critical level message"""
        self.log("critical", message, **extra_fields)


# ==================== PROMETHEUS METRICS ====================

class BlockchainMetrics:
    """
    Centralized metrics collector for XAI blockchain.
    Exports metrics in Prometheus format for time-series monitoring.

    Supports:
    - Counters: For monotonically increasing values
    - Gauges: For current values that can go up/down
    - Histograms: For distribution of values over time
    - Summaries: For observations across time windows
    - Info: For metadata about the node
    """

    def __init__(
        self,
        port: int = 8000,
        registry: Optional[CollectorRegistry] = None,
        log_file: Optional[str] = None,
    ):
        """
        Initialize blockchain metrics.

        Args:
            port: Port to expose metrics endpoint
            registry: Custom Prometheus registry (optional)
            log_file: Path to structured JSON log file
        """
        self.registry = registry or REGISTRY
        self.metrics_port = port
        self.logger = StructuredLogger("xai.metrics", log_file)
        self.start_time = time.time()

        # Lock for thread-safe operations
        self._lock = threading.Lock()

        # ==================== BLOCK METRICS ====================
        self.blocks_total = Counter(
            "xai_blocks_total",
            "Total number of blocks mined",
            registry=self.registry,
        )

        self.block_height = Gauge(
            "xai_block_height",
            "Current blockchain height",
            registry=self.registry,
        )

        self.block_size_bytes = Histogram(
            "xai_block_size_bytes",
            "Block size distribution in bytes",
            buckets=[1000, 5000, 10000, 50000, 100000, 500000, 1000000, 5000000],
            registry=self.registry,
        )

        self.block_mining_time = Histogram(
            "xai_block_mining_time_seconds",
            "Time taken to mine a block",
            buckets=[1, 5, 10, 30, 60, 120, 300, 600, 1800],
            registry=self.registry,
        )

        self.block_difficulty = Gauge(
            "xai_block_difficulty",
            "Current mining difficulty",
            registry=self.registry,
        )

        self.block_production_rate = Gauge(
            "xai_block_production_rate_per_minute",
            "Block production rate (blocks per minute)",
            registry=self.registry,
        )

        self.block_validation_time = Histogram(
            "xai_block_validation_time_seconds",
            "Time to validate a block",
            buckets=[0.001, 0.01, 0.05, 0.1, 0.5, 1, 5],
            registry=self.registry,
        )

        # ==================== TRANSACTION METRICS ====================
        self.transactions_total = Counter(
            "xai_transactions_total",
            "Total number of transactions processed",
            ["status"],
            registry=self.registry,
        )

        self.transaction_pool_size = Gauge(
            "xai_transaction_pool_size",
            "Current number of transactions in mempool",
            registry=self.registry,
        )

        self.transaction_throughput = Gauge(
            "xai_transaction_throughput_per_second",
            "Transactions processed per second",
            registry=self.registry,
        )

        self.transaction_value = Histogram(
            "xai_transaction_value_xai",
            "Transaction value distribution in XAI",
            buckets=[0.1, 1, 10, 100, 1000, 10000, 100000],
            registry=self.registry,
        )

        self.transaction_fee = Histogram(
            "xai_transaction_fee_xai",
            "Transaction fee distribution in XAI",
            buckets=[0.0001, 0.001, 0.01, 0.1, 1, 10],
            registry=self.registry,
        )

        self.transaction_processing_time = Histogram(
            "xai_transaction_processing_time_seconds",
            "Transaction processing time",
            buckets=[0.001, 0.01, 0.1, 0.5, 1, 5, 10],
            registry=self.registry,
        )

        # ==================== NETWORK METRICS ====================
        self.peers_connected = Gauge(
            "xai_peers_connected",
            "Number of connected peers",
            registry=self.registry,
        )

        self.peers_active = Gauge(
            "xai_peers_active",
            "Number of active peers (recently communicated)",
            registry=self.registry,
        )

        self.network_bandwidth_sent_bytes = Counter(
            "xai_network_bandwidth_sent_bytes_total",
            "Total network bandwidth sent in bytes",
            registry=self.registry,
        )

        self.network_bandwidth_received_bytes = Counter(
            "xai_network_bandwidth_received_bytes_total",
            "Total network bandwidth received in bytes",
            registry=self.registry,
        )

        self.network_latency = Histogram(
            "xai_network_latency_seconds",
            "Network latency to peers",
            buckets=[0.01, 0.05, 0.1, 0.5, 1, 2, 5],
            registry=self.registry,
        )

        self.network_messages = Counter(
            "xai_network_messages_total",
            "Network messages by type",
            ["message_type"],
            registry=self.registry,
        )

        self.network_errors = Counter(
            "xai_network_errors_total",
            "Network errors by type",
            ["error_type"],
            registry=self.registry,
        )

        # ==================== API METRICS ====================
        self.api_requests_total = Counter(
            "xai_api_requests_total",
            "Total API requests",
            ["endpoint", "method", "status"],
            registry=self.registry,
        )

        self.api_request_duration = Histogram(
            "xai_api_request_duration_seconds",
            "API request duration",
            ["endpoint", "method"],
            buckets=[0.001, 0.01, 0.05, 0.1, 0.5, 1, 2, 5],
            registry=self.registry,
        )

        self.api_active_connections = Gauge(
            "xai_api_active_connections",
            "Number of active API connections",
            registry=self.registry,
        )

        self.api_errors = Counter(
            "xai_api_errors_total",
            "API errors by endpoint",
            ["endpoint", "error_type"],
            registry=self.registry,
        )

        # ==================== WALLET METRICS ====================
        self.wallet_balance = Gauge(
            "xai_wallet_balance_xai",
            "Wallet balance in XAI",
            ["address"],
            registry=self.registry,
        )

        self.total_supply = Gauge(
            "xai_total_supply_xai",
            "Total XAI supply",
            registry=self.registry,
        )

        self.circulating_supply = Gauge(
            "xai_circulating_supply_xai",
            "Circulating XAI supply",
            registry=self.registry,
        )

        self.wallet_transactions = Counter(
            "xai_wallet_transactions_total",
            "Transactions by wallet address",
            ["address", "type"],
            registry=self.registry,
        )

        # ==================== MINING METRICS ====================
        self.mining_hashrate = Gauge(
            "xai_mining_hashrate",
            "Current mining hashrate (hashes per second)",
            registry=self.registry,
        )

        self.mining_attempts = Counter(
            "xai_mining_attempts_total",
            "Total mining attempts",
            registry=self.registry,
        )

        self.mining_success = Counter(
            "xai_mining_success_total",
            "Successful mining operations",
            registry=self.registry,
        )

        self.mining_difficulty = Gauge(
            "xai_mining_difficulty",
            "Mining difficulty adjustment metric",
            registry=self.registry,
        )

        self.mining_blocks_found = Counter(
            "xai_mining_blocks_found_total",
            "Blocks found by this node",
            registry=self.registry,
        )

        # ==================== SYSTEM METRICS ====================
        self.system_cpu_usage = Gauge(
            "xai_system_cpu_usage_percent",
            "CPU usage percentage",
            registry=self.registry,
        )

        self.system_memory_usage = Gauge(
            "xai_system_memory_usage_bytes",
            "Memory usage in bytes",
            registry=self.registry,
        )

        self.system_memory_percent = Gauge(
            "xai_system_memory_percent",
            "Memory usage percentage",
            registry=self.registry,
        )

        self.system_disk_usage = Gauge(
            "xai_system_disk_usage_bytes",
            "Disk usage in bytes",
            registry=self.registry,
        )

        self.system_disk_percent = Gauge(
            "xai_system_disk_percent",
            "Disk usage percentage",
            registry=self.registry,
        )

        self.process_uptime_seconds = Gauge(
            "xai_process_uptime_seconds",
            "Process uptime in seconds",
            registry=self.registry,
        )

        self.process_num_threads = Gauge(
            "xai_process_num_threads",
            "Number of threads in process",
            registry=self.registry,
        )

        # ==================== BLOCKCHAIN STATE ====================
        self.chain_sync_status = Gauge(
            "xai_chain_sync_status",
            "Chain sync status (1 = synced, 0 = syncing)",
            registry=self.registry,
        )

        self.chain_height = Gauge(
            "xai_chain_height",
            "Current chain height (alias for block_height)",
            registry=self.registry,
        )

        self.chain_sync_percentage = Gauge(
            "xai_chain_sync_percentage",
            "Chain sync progress percentage",
            registry=self.registry,
        )

        self.orphaned_blocks = Counter(
            "xai_orphaned_blocks_total",
            "Total orphaned blocks",
            registry=self.registry,
        )

        self.reorgs = Counter(
            "xai_chain_reorgs_total",
            "Total chain reorganizations",
            registry=self.registry,
        )

        self.reorg_depth = Histogram(
            "xai_chain_reorg_depth",
            "Depth of chain reorganizations",
            buckets=[1, 2, 5, 10, 20, 50],
            registry=self.registry,
        )

        # ==================== VALIDATION METRICS ====================
        self.validation_failures = Counter(
            "xai_validation_failures_total",
            "Validation failures by type",
            ["validation_type"],
            registry=self.registry,
        )

        self.validation_errors = Counter(
            "xai_validation_errors_total",
            "Validation errors by category",
            ["error_category"],
            registry=self.registry,
        )

        # ==================== AI METRICS ====================
        self.ai_tasks_total = Counter(
            "xai_ai_tasks_total",
            "Total AI tasks executed",
            ["provider", "status"],
            registry=self.registry,
        )

        self.ai_task_duration = Histogram(
            "xai_ai_task_duration_seconds",
            "AI task execution time",
            ["provider"],
            buckets=[0.1, 0.5, 1, 5, 10, 30, 60],
            registry=self.registry,
        )

        self.ai_task_cost = Counter(
            "xai_ai_task_cost_total",
            "Total AI task cost",
            ["provider"],
            registry=self.registry,
        )

        # ==================== INFO METRICS ====================
        self.node_info = Info(
            "xai_node",
            "XAI node information",
            registry=self.registry,
        )

        self.logger.info("BlockchainMetrics initialized", port=port)

    def export_prometheus(self) -> str:
        """
        Export metrics in Prometheus text format.

        Returns:
            Prometheus format metrics string
        """
        return generate_latest(self.registry).decode("utf-8")

    def update_system_metrics(self) -> None:
        """Update system resource metrics"""
        with self._lock:
            try:
                # CPU usage
                cpu_percent = psutil.cpu_percent(interval=0.1)
                self.system_cpu_usage.set(cpu_percent)

                # Memory usage
                memory = psutil.virtual_memory()
                self.system_memory_usage.set(memory.used)
                self.system_memory_percent.set(memory.percent)

                # Disk usage
                disk = psutil.disk_usage(".")
                self.system_disk_usage.set(disk.used)
                self.system_disk_percent.set(disk.percent)

                # Process uptime
                uptime = time.time() - self.start_time
                self.process_uptime_seconds.set(uptime)

                # Thread count
                try:
                    process = psutil.Process(os.getpid())
                    self.process_num_threads.set(process.num_threads())
                except (AttributeError, psutil.NoSuchProcess) as e:
                    # Expected when process terminates or psutil is unavailable
                    self.logger.debug(
                        "Failed to get thread count",
                        extra={"error": str(e), "event": "metrics.thread_count_unavailable"}
                    )

                # Alert on high resource usage
                if cpu_percent > 80:
                    self.logger.warning(
                        "High CPU usage",
                        cpu_percent=cpu_percent,
                    )
                if memory.percent > 85:
                    self.logger.warning(
                        "High memory usage",
                        memory_percent=memory.percent,
                    )

            except Exception as e:
                self.logger.error("Failed to update system metrics", error=str(e))

    def set_node_info(self, version: str, network: str, node_id: str) -> None:
        """Set node information"""
        with self._lock:
            self.node_info.info(
                {
                    "version": version,
                    "network": network,
                    "node_id": node_id,
                }
            )

    def record_block(
        self,
        height: int,
        size: int,
        difficulty: int,
        mining_time: float,
        validation_time: float = 0,
    ) -> None:
        """Record a new block"""
        with self._lock:
            self.blocks_total.inc()
            self.block_height.set(height)
            self.chain_height.set(height)
            self.block_size_bytes.observe(size)
            self.block_difficulty.set(difficulty)
            self.block_mining_time.observe(mining_time)
            if validation_time > 0:
                self.block_validation_time.observe(validation_time)

            self.logger.debug(
                "Block recorded",
                height=height,
                size=size,
                mining_time=mining_time,
                validation_time=validation_time,
            )

    def record_transaction(
        self,
        status: str = "confirmed",
        value: float = 0,
        fee: float = 0,
        processing_time: float = 0,
    ) -> None:
        """Record a transaction"""
        with self._lock:
            self.transactions_total.labels(status=status).inc()
            if value > 0:
                self.transaction_value.observe(value)
            if fee > 0:
                self.transaction_fee.observe(fee)
            if processing_time > 0:
                self.transaction_processing_time.observe(processing_time)

            self.logger.debug(
                "Transaction recorded",
                status=status,
                value=value,
                fee=fee,
                processing_time=processing_time,
            )

    def update_mempool_size(self, size: int) -> None:
        """Update transaction pool size"""
        with self._lock:
            self.transaction_pool_size.set(size)

    def update_peer_count(self, count: int, active: int = 0) -> None:
        """Update connected peer count"""
        with self._lock:
            self.peers_connected.set(count)
            if active > 0:
                self.peers_active.set(active)

            # Alert if peer count is low
            if count < 2:
                self.logger.warning("Low peer count", peers=count)

    def record_network_message(self, message_type: str) -> None:
        """Record network message"""
        with self._lock:
            self.network_messages.labels(message_type=message_type).inc()

    def record_network_error(self, error_type: str) -> None:
        """Record network error"""
        with self._lock:
            self.network_errors.labels(error_type=error_type).inc()
            self.logger.warning("Network error", error_type=error_type)

    def record_api_request(
        self,
        endpoint: str,
        method: str,
        status: int,
        duration: float,
    ) -> None:
        """Record API request"""
        with self._lock:
            self.api_requests_total.labels(
                endpoint=endpoint,
                method=method,
                status=str(status),
            ).inc()
            self.api_request_duration.labels(
                endpoint=endpoint,
                method=method,
            ).observe(duration)

    def record_api_error(self, endpoint: str, error_type: str) -> None:
        """Record API error"""
        with self._lock:
            self.api_errors.labels(endpoint=endpoint, error_type=error_type).inc()
            self.logger.error("API error", endpoint=endpoint, error_type=error_type)

    def update_mining_hashrate(self, hashrate: float) -> None:
        """Update mining hashrate"""
        with self._lock:
            self.mining_hashrate.set(hashrate)

    def record_mining_attempt(self, success: bool = False) -> None:
        """Record mining attempt"""
        with self._lock:
            self.mining_attempts.inc()
            if success:
                self.mining_success.inc()
                self.mining_blocks_found.inc()

    def update_supply_metrics(self, total: float, circulating: float) -> None:
        """Update supply metrics"""
        with self._lock:
            self.total_supply.set(total)
            self.circulating_supply.set(circulating)

    def set_sync_status(self, synced: bool, percentage: float = 100.0) -> None:
        """Set chain sync status"""
        with self._lock:
            self.chain_sync_status.set(1 if synced else 0)
            self.chain_sync_percentage.set(percentage)

    def record_validation_failure(self, validation_type: str) -> None:
        """Record validation failure"""
        with self._lock:
            self.validation_failures.labels(validation_type=validation_type).inc()
            self.logger.warning(
                "Validation failure",
                validation_type=validation_type,
            )

    def record_validation_error(self, error_category: str) -> None:
        """Record validation error"""
        with self._lock:
            self.validation_errors.labels(error_category=error_category).inc()
            self.logger.error("Validation error", error_category=error_category)

    def record_reorg(self, depth: int) -> None:
        """Record chain reorganization"""
        with self._lock:
            self.reorgs.inc()
            self.reorg_depth.observe(depth)
            self.logger.warning("Chain reorganization", depth=depth)

    def record_ai_task(
        self,
        provider: str,
        status: str,
        duration: float,
        cost: float = 0,
    ) -> None:
        """Record AI task execution"""
        with self._lock:
            self.ai_tasks_total.labels(provider=provider, status=status).inc()
            self.ai_task_duration.labels(provider=provider).observe(duration)
            if cost > 0:
                self.ai_task_cost.labels(provider=provider).inc(cost)

            self.logger.debug(
                "AI task recorded",
                provider=provider,
                status=status,
                duration=duration,
                cost=cost,
            )

    def record_wallet_transaction(
        self,
        address: str,
        tx_type: str,
    ) -> None:
        """Record wallet transaction"""
        with self._lock:
            self.wallet_transactions.labels(address=address, type=tx_type).inc()

    def update_wallet_balance(self, address: str, balance: float) -> None:
        """Update wallet balance"""
        with self._lock:
            self.wallet_balance.labels(address=address).set(balance)


# ==================== GLOBAL METRICS INSTANCE ====================

_metrics_instance: Optional[BlockchainMetrics] = None
_metrics_lock = threading.Lock()


def get_metrics() -> BlockchainMetrics:
    """Get or create global metrics instance"""
    global _metrics_instance
    if _metrics_instance is None:
        with _metrics_lock:
            if _metrics_instance is None:
                _metrics_instance = BlockchainMetrics()
    return _metrics_instance


def initialize_metrics(
    port: int = 8000,
    version: str = "1.0.0",
    network: str = "mainnet",
    node_id: str = "",
    log_file: Optional[str] = None,
) -> BlockchainMetrics:
    """
    Initialize and configure metrics system.

    Args:
        port: Metrics server port
        version: Node version
        network: Network name (mainnet/testnet)
        node_id: Unique node identifier
        log_file: Path to structured JSON log file

    Returns:
        BlockchainMetrics instance
    """
    global _metrics_instance
    with _metrics_lock:
        if _metrics_instance is None:
            _metrics_instance = BlockchainMetrics(port=port, log_file=log_file)
        _metrics_instance.metrics_port = port
        _metrics_instance.set_node_info(version, network, node_id)
    return _metrics_instance


if __name__ == "__main__":
    # Example usage
    print("XAI Blockchain Metrics - Test Mode")
    print("=" * 50)

    # Security fix: Use environment variable or secure default instead of hardcoded /tmp
    import tempfile
    from pathlib import Path
    log_dir = os.getenv("XAI_LOG_DIR", os.path.join(Path.home(), ".xai", "logs"))
    Path(log_dir).mkdir(parents=True, exist_ok=True)

    metrics = initialize_metrics(
        port=8000,
        version="1.0.0",
        network="testnet",
        node_id="test-node-001",
        log_file=os.path.join(log_dir, "xai-metrics.json"),
    )

    print("\nSimulating blockchain activity...")

    # Simulate some metrics
    metrics.record_block(height=1, size=5000, difficulty=1000, mining_time=30)
    metrics.record_transaction(status="confirmed", value=100, fee=0.001, processing_time=0.5)
    metrics.update_peer_count(5, 3)
    metrics.update_mempool_size(10)
    metrics.update_system_metrics()

    print("\nMetrics recorded.")
    print("\nSample Prometheus output:")
    print("-" * 50)
    output = metrics.export_prometheus()
    # Print first 50 lines
    for line in output.split("\n")[:50]:
        print(line)

    print("\n... (more metrics available)")
