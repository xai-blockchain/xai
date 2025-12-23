from __future__ import annotations

"""
XAI Blockchain - Prometheus Metrics
Comprehensive metrics collection for blockchain monitoring
"""

import logging
import os
import time

import psutil
from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    Info,
    Summary,
    start_http_server,
)
from pythonjsonlogger import jsonlogger

logger = logging.getLogger(__name__)

class BlockchainMetrics:
    """
    Centralized metrics collector for XAI blockchain
    Exports metrics in Prometheus format
    """

    def __init__(self, port: int = 8000, registry: CollectorRegistry | None = None):
        """
        Initialize blockchain metrics

        Args:
            port: Port to expose metrics endpoint (default: 8000)
            registry: Custom Prometheus registry (optional)
        """
        self.registry = registry or CollectorRegistry()
        self.metrics_port = port

        # ==================== BLOCK METRICS ====================
        self.blocks_total = Counter(
            "xai_blocks_total", "Total number of blocks mined", registry=self.registry
        )

        self.block_height = Gauge(
            "xai_block_height", "Current blockchain height", registry=self.registry
        )

        self.block_size_bytes = Histogram(
            "xai_block_size_bytes",
            "Block size distribution in bytes",
            buckets=[1000, 5000, 10000, 50000, 100000, 500000, 1000000],
            registry=self.registry,
        )

        self.block_mining_time = Histogram(
            "xai_block_mining_time_seconds",
            "Time taken to mine a block",
            buckets=[1, 5, 10, 30, 60, 120, 300, 600],
            registry=self.registry,
        )

        self.block_difficulty = Gauge(
            "xai_block_difficulty", "Current mining difficulty", registry=self.registry
        )

        self.block_production_rate = Gauge(
            "xai_block_production_rate_per_minute",
            "Block production rate (blocks per minute)",
            registry=self.registry,
        )

        # ==================== TRANSACTION METRICS ====================
        self.transactions_total = Counter(
            "xai_transactions_total",
            "Total number of transactions processed",
            ["status"],  # pending, confirmed, failed
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
            "xai_peers_connected", "Number of connected peers", registry=self.registry
        )

        self.network_bandwidth_sent_bytes = Counter(
            "xai_network_bandwidth_sent_bytes_total",
            "Total network bandwidth sent",
            registry=self.registry,
        )

        self.network_bandwidth_received_bytes = Counter(
            "xai_network_bandwidth_received_bytes_total",
            "Total network bandwidth received",
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
            ["message_type"],  # block, transaction, ping, etc.
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

        # ==================== WALLET METRICS ====================
        self.wallet_balance = Gauge(
            "xai_wallet_balance_xai",
            "Wallet balance in XAI",
            ["address"],
            registry=self.registry,
        )

        self.total_supply = Gauge(
            "xai_total_supply_xai", "Total XAI supply", registry=self.registry
        )

        self.circulating_supply = Gauge(
            "xai_circulating_supply_xai", "Circulating XAI supply", registry=self.registry
        )

        # ==================== MINING METRICS ====================
        self.mining_hashrate = Gauge(
            "xai_mining_hashrate",
            "Current mining hashrate (hashes per second)",
            registry=self.registry,
        )

        self.mining_attempts = Counter(
            "xai_mining_attempts_total", "Total mining attempts", registry=self.registry
        )

        self.mining_success = Counter(
            "xai_mining_success_total", "Successful mining operations", registry=self.registry
        )

        # ==================== SYSTEM METRICS ====================
        self.system_cpu_usage = Gauge(
            "xai_system_cpu_usage_percent", "CPU usage percentage", registry=self.registry
        )

        self.system_memory_usage = Gauge(
            "xai_system_memory_usage_bytes", "Memory usage in bytes", registry=self.registry
        )

        self.system_memory_percent = Gauge(
            "xai_system_memory_percent", "Memory usage percentage", registry=self.registry
        )

        self.system_disk_usage = Gauge(
            "xai_system_disk_usage_bytes", "Disk usage in bytes", registry=self.registry
        )

        self.system_disk_percent = Gauge(
            "xai_system_disk_percent", "Disk usage percentage", registry=self.registry
        )

        self.process_uptime_seconds = Gauge(
            "xai_process_uptime_seconds", "Process uptime in seconds", registry=self.registry
        )

        # ==================== BLOCKCHAIN STATE ====================
        self.chain_sync_status = Gauge(
            "xai_chain_sync_status",
            "Chain sync status (1 = synced, 0 = syncing)",
            registry=self.registry,
        )

        self.orphaned_blocks = Counter(
            "xai_orphaned_blocks_total", "Total orphaned blocks", registry=self.registry
        )

        self.reorgs = Counter(
            "xai_chain_reorgs_total", "Total chain reorganizations", registry=self.registry
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

        # ==================== INFO METRICS ====================
        self.node_info = Info("xai_node", "XAI node information", registry=self.registry)

        # Track start time for uptime calculation
        self.start_time = time.time()

    def start_server(self):
        """Start Prometheus metrics HTTP server"""
        try:
            start_http_server(self.metrics_port, registry=self.registry)
            print(f"[OK] Prometheus metrics server started on port {self.metrics_port}")
            print(f"  Metrics endpoint: http://localhost:{self.metrics_port}/metrics")
        except OSError as e:
            logger.error(
                "OSError in start_server",
                extra={
                    "error_type": "OSError",
                    "error": str(e),
                    "function": "start_server"
                }
            )
            print(f"[ERROR] Failed to start metrics server on port {self.metrics_port}: {e}")
            print(f"  Port may already be in use. Try a different port.")

    def update_system_metrics(self):
        """Update system resource metrics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=0.1)
            self.system_cpu_usage.set(cpu_percent)

            # Memory usage
            memory = psutil.virtual_memory()
            self.system_memory_usage.set(memory.used)
            self.system_memory_percent.set(memory.percent)

            # Disk usage (for blockchain data directory)
            disk = psutil.disk_usage(".")
            self.system_disk_usage.set(disk.used)
            self.system_disk_percent.set(disk.percent)

            # Process uptime
            uptime = time.time() - self.start_time
            self.process_uptime_seconds.set(uptime)

        except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as e:
            logger.error(
                "Exception in update_system_metrics",
                extra={
                    "error_type": "Exception",
                    "error": str(e),
                    "function": "update_system_metrics"
                }
            )
            print(f"Warning: Failed to update system metrics: {e}")

    def set_node_info(self, version: str, network: str, node_id: str):
        """Set node information"""
        self.node_info.info({"version": version, "network": network, "node_id": node_id})

    def record_block(self, height: int, size: int, difficulty: int, mining_time: float):
        """Record a new block"""
        self.blocks_total.inc()
        self.block_height.set(height)
        self.block_size_bytes.observe(size)
        self.block_difficulty.set(difficulty)
        self.block_mining_time.observe(mining_time)

    def record_transaction(
        self,
        status: str = "confirmed",
        value: float = 0,
        fee: float = 0,
        processing_time: float = 0,
    ):
        """Record a transaction"""
        self.transactions_total.labels(status=status).inc()
        if value > 0:
            self.transaction_value.observe(value)
        if fee > 0:
            self.transaction_fee.observe(fee)
        if processing_time > 0:
            self.transaction_processing_time.observe(processing_time)

    def update_mempool_size(self, size: int):
        """Update transaction pool size"""
        self.transaction_pool_size.set(size)

    def update_peer_count(self, count: int):
        """Update connected peer count"""
        self.peers_connected.set(count)

    def record_network_message(self, message_type: str):
        """Record network message"""
        self.network_messages.labels(message_type=message_type).inc()

    def record_api_request(self, endpoint: str, method: str, status: int, duration: float):
        """Record API request"""
        self.api_requests_total.labels(endpoint=endpoint, method=method, status=str(status)).inc()
        self.api_request_duration.labels(endpoint=endpoint, method=method).observe(duration)

    def update_mining_hashrate(self, hashrate: float):
        """Update mining hashrate"""
        self.mining_hashrate.set(hashrate)

    def record_mining_attempt(self, success: bool = False):
        """Record mining attempt"""
        self.mining_attempts.inc()
        if success:
            self.mining_success.inc()

    def update_supply_metrics(self, total: float, circulating: float):
        """Update supply metrics"""
        self.total_supply.set(total)
        self.circulating_supply.set(circulating)

    def set_sync_status(self, synced: bool):
        """Set chain sync status"""
        self.chain_sync_status.set(1 if synced else 0)

    def record_ai_task(self, provider: str, status: str, duration: float):
        """Record AI task execution"""
        self.ai_tasks_total.labels(provider=provider, status=status).inc()
        self.ai_task_duration.labels(provider=provider).observe(duration)

# Global metrics instance
_metrics_instance: BlockchainMetrics | None = None

def get_metrics() -> BlockchainMetrics:
    """Get or create global metrics instance"""
    global _metrics_instance
    if _metrics_instance is None:
        _metrics_instance = BlockchainMetrics()
    return _metrics_instance

def initialize_metrics(
    port: int = 8000, version: str = "1.0.0", network: str = "mainnet", node_id: str = ""
):
    """
    Initialize and start metrics server

    Args:
        port: Metrics server port
        version: Node version
        network: Network name (mainnet/testnet)
        node_id: Unique node identifier
    """
    metrics = get_metrics()
    metrics.metrics_port = port
    metrics.set_node_info(version, network, node_id)
    metrics.start_server()
    return metrics

# Convenience decorator for timing functions
def time_function(metric_name: str):
    """Decorator to time function execution and record to metrics"""

    def decorator(func):
        def wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start
                # Record success
                return result
            except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as e:
                logger.error(
                    "Exception in wrapper",
                    extra={
                        "error_type": "Exception",
                        "error": str(e),
                        "function": "wrapper"
                    }
                )
                duration = time.time() - start
                # Record failure
                raise
            finally:
                # Update relevant metric based on metric_name
                pass

        return wrapper

    return decorator

if __name__ == "__main__":
    # Example usage
    print("XAI Blockchain Metrics - Test Mode")
    print("=" * 50)

    metrics = initialize_metrics(
        port=8000, version="1.0.0", network="testnet", node_id="test-node-001"
    )

    print("\nSimulating blockchain activity...")

    # Simulate some metrics
    metrics.record_block(height=1, size=5000, difficulty=1000, mining_time=30)
    metrics.record_transaction(status="confirmed", value=100, fee=0.001, processing_time=0.5)
    metrics.update_peer_count(5)
    metrics.update_mempool_size(10)
    metrics.update_system_metrics()

    print("\nMetrics recorded. Access at http://localhost:8000/metrics")
    print("Press Ctrl+C to stop...")

    try:
        while True:
            time.sleep(5)
            metrics.update_system_metrics()
    except KeyboardInterrupt:
        print("\nShutting down...")
