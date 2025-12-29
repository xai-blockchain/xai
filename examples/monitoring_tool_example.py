#!/usr/bin/env python3
"""
XAI Blockchain Monitoring Tool Example

A real-time monitoring tool demonstrating:
- Blockchain status tracking
- Network health monitoring
- Mempool statistics
- Performance metrics collection
- Alerting on anomalies

Usage:
    python monitoring_tool_example.py --node-url http://localhost:12001
    python monitoring_tool_example.py --node-url http://localhost:12001 --json
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@dataclass
class BlockchainMetrics:
    """Blockchain state metrics."""
    height: int = 0
    latest_hash: str = ""
    difficulty: int = 0
    total_transactions: int = 0
    timestamp: float = 0.0


@dataclass
class NetworkMetrics:
    """Network health metrics."""
    peer_count: int = 0
    inbound_peers: int = 0
    outbound_peers: int = 0
    sync_status: str = "unknown"
    sync_progress: float = 0.0


@dataclass
class MempoolMetrics:
    """Mempool statistics."""
    size: int = 0
    bytes: int = 0
    pending_fees: float = 0.0
    oldest_tx_age: int = 0  # seconds


@dataclass
class PerformanceMetrics:
    """Performance metrics."""
    avg_block_time: float = 0.0
    tps: float = 0.0  # transactions per second
    mining_hashrate: float = 0.0


@dataclass
class HealthStatus:
    """Overall node health status."""
    healthy: bool = True
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class MonitoringSnapshot:
    """Complete monitoring snapshot."""
    timestamp: str
    blockchain: BlockchainMetrics
    network: NetworkMetrics
    mempool: MempoolMetrics
    performance: PerformanceMetrics
    health: HealthStatus


class XAIMonitor:
    """XAI blockchain monitoring client."""

    def __init__(self, node_url: str, timeout: float = 10.0):
        self.node_url = node_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self._last_block_height: int = 0
        self._last_block_time: float = 0.0
        self._tx_count_history: list[tuple[float, int]] = []

    def _get(self, endpoint: str) -> dict[str, Any]:
        """Make GET request to node."""
        try:
            resp = self.session.get(
                f"{self.node_url}/{endpoint.lstrip('/')}",
                timeout=self.timeout,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            logger.error("Request failed for %s: %s", endpoint, e)
            raise

    def get_blockchain_metrics(self) -> BlockchainMetrics:
        """Fetch blockchain state metrics."""
        try:
            info = self._get("/info")
            return BlockchainMetrics(
                height=info.get("chain_length", 0),
                latest_hash=info.get("latest_block_hash", ""),
                difficulty=info.get("difficulty", 0),
                total_transactions=info.get("total_transactions", 0),
                timestamp=info.get("latest_block_timestamp", 0.0),
            )
        except Exception:
            return BlockchainMetrics()

    def get_network_metrics(self) -> NetworkMetrics:
        """Fetch network health metrics."""
        try:
            # Get peer info
            peers = self._get("/peers")
            peer_list = peers.get("peers", [])
            peer_count = len(peer_list)
            inbound = sum(1 for p in peer_list if p.get("direction") == "inbound")
            outbound = peer_count - inbound

            # Get sync status
            sync_info = self._get("/sync/status")
            sync_status = sync_info.get("status", "unknown")
            sync_progress = sync_info.get("progress", 0.0)

            return NetworkMetrics(
                peer_count=peer_count,
                inbound_peers=inbound,
                outbound_peers=outbound,
                sync_status=sync_status,
                sync_progress=sync_progress,
            )
        except Exception:
            return NetworkMetrics()

    def get_mempool_metrics(self) -> MempoolMetrics:
        """Fetch mempool statistics."""
        try:
            stats = self._get("/mempool/stats")
            return MempoolMetrics(
                size=stats.get("size", 0),
                bytes=stats.get("bytes", 0),
                pending_fees=stats.get("total_fees", 0.0),
                oldest_tx_age=stats.get("oldest_tx_age_seconds", 0),
            )
        except Exception:
            return MempoolMetrics()

    def get_performance_metrics(self, blockchain: BlockchainMetrics) -> PerformanceMetrics:
        """Calculate performance metrics."""
        now = time.time()

        # Calculate average block time
        avg_block_time = 0.0
        if self._last_block_time > 0 and blockchain.height > self._last_block_height:
            blocks_delta = blockchain.height - self._last_block_height
            time_delta = now - self._last_block_time
            if blocks_delta > 0:
                avg_block_time = time_delta / blocks_delta

        # Update history
        self._last_block_height = blockchain.height
        self._last_block_time = now

        # Calculate TPS
        self._tx_count_history.append((now, blockchain.total_transactions))
        # Keep last 5 minutes
        cutoff = now - 300
        self._tx_count_history = [
            (t, c) for t, c in self._tx_count_history if t > cutoff
        ]

        tps = 0.0
        if len(self._tx_count_history) >= 2:
            oldest_time, oldest_count = self._tx_count_history[0]
            newest_time, newest_count = self._tx_count_history[-1]
            time_span = newest_time - oldest_time
            if time_span > 0:
                tps = (newest_count - oldest_count) / time_span

        # Get mining hashrate
        try:
            mining = self._get("/mining/status")
            hashrate = mining.get("hashrate", 0.0)
        except Exception:
            hashrate = 0.0

        return PerformanceMetrics(
            avg_block_time=avg_block_time,
            tps=tps,
            mining_hashrate=hashrate,
        )

    def check_health(
        self,
        blockchain: BlockchainMetrics,
        network: NetworkMetrics,
        mempool: MempoolMetrics,
    ) -> HealthStatus:
        """Evaluate overall node health."""
        issues: list[str] = []
        warnings: list[str] = []

        # Check peer count
        if network.peer_count == 0:
            issues.append("No peers connected")
        elif network.peer_count < 3:
            warnings.append(f"Low peer count: {network.peer_count}")

        # Check sync status
        if network.sync_status == "syncing" and network.sync_progress < 99:
            warnings.append(f"Syncing: {network.sync_progress:.1f}% complete")

        # Check mempool
        if mempool.size > 5000:
            warnings.append(f"Large mempool: {mempool.size} transactions")
        if mempool.oldest_tx_age > 3600:
            warnings.append(f"Stale mempool transactions (oldest: {mempool.oldest_tx_age}s)")

        # Check block age
        if blockchain.timestamp > 0:
            block_age = time.time() - blockchain.timestamp
            if block_age > 600:  # 10 minutes
                issues.append(f"No new blocks for {int(block_age)}s")
            elif block_age > 300:  # 5 minutes
                warnings.append(f"Block age: {int(block_age)}s")

        return HealthStatus(
            healthy=len(issues) == 0,
            issues=issues,
            warnings=warnings,
        )

    def collect_snapshot(self) -> MonitoringSnapshot:
        """Collect complete monitoring snapshot."""
        blockchain = self.get_blockchain_metrics()
        network = self.get_network_metrics()
        mempool = self.get_mempool_metrics()
        performance = self.get_performance_metrics(blockchain)
        health = self.check_health(blockchain, network, mempool)

        return MonitoringSnapshot(
            timestamp=datetime.now(timezone.utc).isoformat(),
            blockchain=blockchain,
            network=network,
            mempool=mempool,
            performance=performance,
            health=health,
        )


def format_human_readable(snapshot: MonitoringSnapshot) -> str:
    """Format snapshot for human-readable output."""
    lines = [
        "=" * 60,
        f"XAI Blockchain Monitor - {snapshot.timestamp}",
        "=" * 60,
        "",
        "BLOCKCHAIN STATUS:",
        f"  Height:       {snapshot.blockchain.height:,}",
        f"  Difficulty:   {snapshot.blockchain.difficulty}",
        f"  Transactions: {snapshot.blockchain.total_transactions:,}",
        f"  Latest Hash:  {snapshot.blockchain.latest_hash[:16]}...",
        "",
        "NETWORK STATUS:",
        f"  Peers:     {snapshot.network.peer_count} (in: {snapshot.network.inbound_peers}, out: {snapshot.network.outbound_peers})",
        f"  Sync:      {snapshot.network.sync_status} ({snapshot.network.sync_progress:.1f}%)",
        "",
        "MEMPOOL:",
        f"  Size:      {snapshot.mempool.size} transactions",
        f"  Fees:      {snapshot.mempool.pending_fees:.8f} XAI",
        "",
        "PERFORMANCE:",
        f"  Block Time: {snapshot.performance.avg_block_time:.1f}s",
        f"  TPS:        {snapshot.performance.tps:.2f}",
        f"  Hashrate:   {snapshot.performance.mining_hashrate:.2f} H/s",
        "",
    ]

    # Health status
    if snapshot.health.healthy:
        lines.append("HEALTH: ✓ Healthy")
    else:
        lines.append("HEALTH: ✗ Issues Detected")

    for issue in snapshot.health.issues:
        lines.append(f"  [ERROR] {issue}")
    for warning in snapshot.health.warnings:
        lines.append(f"  [WARN]  {warning}")

    lines.append("")
    return "\n".join(lines)


def run_monitor(
    node_url: str,
    interval: int = 30,
    output_json: bool = False,
) -> None:
    """Run monitoring loop."""
    monitor = XAIMonitor(node_url)
    logger.info("Starting XAI monitor for %s", node_url)
    logger.info("Update interval: %ds", interval)

    try:
        while True:
            try:
                snapshot = monitor.collect_snapshot()

                if output_json:
                    # Output as JSON
                    data = asdict(snapshot)
                    print(json.dumps(data, indent=2, default=str))
                else:
                    # Output human-readable
                    print(format_human_readable(snapshot))

                # Log health issues
                if not snapshot.health.healthy:
                    for issue in snapshot.health.issues:
                        logger.error("Health issue: %s", issue)
                for warning in snapshot.health.warnings:
                    logger.warning("Health warning: %s", warning)

            except requests.RequestException as e:
                logger.error("Failed to collect metrics: %s", e)
            except Exception as e:
                logger.exception("Unexpected error: %s", e)

            time.sleep(interval)

    except KeyboardInterrupt:
        logger.info("Monitoring stopped by user")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="XAI Blockchain Monitoring Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Human-readable output
    python monitoring_tool_example.py --node-url http://localhost:12001

    # JSON output for processing
    python monitoring_tool_example.py --node-url http://localhost:12001 --json

    # Custom interval
    python monitoring_tool_example.py --node-url http://localhost:12001 --interval 60
        """,
    )
    parser.add_argument(
        "--node-url",
        default="http://localhost:12001",
        help="XAI node URL (default: http://localhost:12001)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=30,
        help="Update interval in seconds (default: 30)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="output_json",
        help="Output as JSON instead of human-readable",
    )

    args = parser.parse_args()
    run_monitor(args.node_url, args.interval, args.output_json)


if __name__ == "__main__":
    main()
