"""
XAI Performance Dashboard - Real-Time Monitoring

Flask Blueprint providing:
- Real-time TPS (transactions per second) monitoring
- Block time / latency tracking
- Mempool size visualization
- Network peer count
- Recent blocks with timing
- Historical charts (last hour/day)

Integrates with existing MetricsCollector and blockchain get_stats().
"""

from __future__ import annotations

import logging
import os
import time
from collections import deque
from datetime import datetime, timezone
from threading import Lock
from typing import TYPE_CHECKING, Any

from flask import Blueprint, g, jsonify, render_template, request

if TYPE_CHECKING:
    from xai.core.blockchain import Blockchain

logger = logging.getLogger(__name__)


# Local helper functions to avoid circular import with api_blueprints
def get_api_context() -> dict[str, Any]:
    """Get the API context containing node, blockchain, and other dependencies."""
    return g.get("api_context", {})


def get_node() -> Any:
    """Get the blockchain node instance from context."""
    return get_api_context().get("node")


def get_blockchain() -> Any:
    """Get the blockchain instance from context."""
    return get_api_context().get("blockchain")


def success_response(payload: dict[str, Any], status: int = 200) -> tuple[Any, int]:
    """Return a success payload with consistent structure."""
    body = {"success": True, **payload}
    return jsonify(body), status


def error_response(
    message: str,
    status: int = 400,
    code: str = "bad_request",
) -> tuple[Any, int]:
    """Return a sanitized error response."""
    return jsonify({"success": False, "error": message, "code": code}), status

# Performance metrics history (in-memory, thread-safe)
_metrics_lock = Lock()
_tps_history: deque[dict[str, Any]] = deque(maxlen=3600)  # 1 hour at 1/sec
_block_history: deque[dict[str, Any]] = deque(maxlen=1440)  # Last 1440 blocks
_last_block_count: int = 0
_last_tx_count: int = 0
_last_sample_time: float = 0.0

# Create Blueprint
performance_bp = Blueprint(
    "performance",
    __name__,
    url_prefix="/dashboard",
    template_folder="templates",
)


def _calculate_tps(blockchain: "Blockchain") -> dict[str, Any]:
    """Calculate current TPS and update history."""
    global _last_block_count, _last_tx_count, _last_sample_time

    now = time.time()
    stats = blockchain.get_stats()
    current_height = stats.get("chain_height", 0)
    pending_count = stats.get("pending_transactions_count", 0)

    # Calculate cumulative tx count from chain
    cumulative_tx = getattr(blockchain, "_cumulative_tx_count", 0)
    if cumulative_tx == 0:
        # Fallback: estimate from block count
        cumulative_tx = current_height * 5  # rough estimate

    with _metrics_lock:
        elapsed = now - _last_sample_time if _last_sample_time > 0 else 1.0
        elapsed = max(elapsed, 0.001)

        # TPS calculation
        if _last_tx_count > 0:
            tx_delta = max(0, cumulative_tx - _last_tx_count)
            tps = tx_delta / elapsed
        else:
            tps = 0.0

        # Block rate calculation
        block_delta = max(0, current_height - _last_block_count)
        blocks_per_minute = (block_delta / elapsed) * 60 if elapsed > 0 else 0

        _last_block_count = current_height
        _last_tx_count = cumulative_tx
        _last_sample_time = now

        # Store in history
        sample = {
            "timestamp": now,
            "tps": round(tps, 3),
            "blocks_per_minute": round(blocks_per_minute, 2),
            "pending_count": pending_count,
            "height": current_height,
        }
        _tps_history.append(sample)

    return sample


def _get_block_times(blockchain: "Blockchain", count: int = 20) -> list[dict[str, Any]]:
    """Get recent block timing information."""
    chain = getattr(blockchain, "chain", [])
    if not chain:
        return []

    results = []
    start_idx = max(0, len(chain) - count)

    for i in range(start_idx, len(chain)):
        block = chain[i]
        block_time = 0.0
        if i > 0:
            prev_block = chain[i - 1]
            prev_ts = getattr(prev_block, "timestamp", 0)
            curr_ts = getattr(block, "timestamp", 0)
            block_time = curr_ts - prev_ts if curr_ts > prev_ts else 0

        tx_count = 0
        if hasattr(block, "transactions"):
            tx_count = len(block.transactions)
        elif hasattr(block, "transaction_count"):
            tx_count = block.transaction_count

        results.append({
            "index": getattr(block, "index", i),
            "hash": str(getattr(block, "hash", ""))[:16] + "...",
            "timestamp": getattr(block, "timestamp", 0),
            "block_time": round(block_time, 2),
            "tx_count": tx_count,
        })

    return results[-count:]


def _get_historical_metrics(hours: int = 1) -> dict[str, Any]:
    """Get historical TPS and block metrics for charts."""
    with _metrics_lock:
        now = time.time()
        cutoff = now - (hours * 3600)

        # Filter history by time range
        filtered = [s for s in _tps_history if s["timestamp"] >= cutoff]

        if not filtered:
            return {
                "tps_avg": 0.0,
                "tps_max": 0.0,
                "tps_min": 0.0,
                "samples": [],
                "period_hours": hours,
            }

        tps_values = [s["tps"] for s in filtered]

        # Downsample for chart (max 120 points)
        step = max(1, len(filtered) // 120)
        sampled = filtered[::step]

        return {
            "tps_avg": round(sum(tps_values) / len(tps_values), 3),
            "tps_max": round(max(tps_values), 3),
            "tps_min": round(min(tps_values), 3),
            "samples": [
                {
                    "timestamp": s["timestamp"],
                    "tps": s["tps"],
                    "pending": s["pending_count"],
                }
                for s in sampled
            ],
            "period_hours": hours,
        }


# ==================== Routes ====================


@performance_bp.route("/")
def dashboard_home():
    """Render the main performance dashboard HTML page."""
    return render_template("performance.html")


@performance_bp.route("/api/metrics/current", methods=["GET"])
def get_current_metrics():
    """Get current real-time metrics snapshot."""
    blockchain = get_blockchain()
    node = get_node()

    if not blockchain:
        return error_response("Blockchain not initialized", status=503)

    try:
        # Get blockchain stats
        stats = blockchain.get_stats()
        tps_data = _calculate_tps(blockchain)

        # Get peer count
        peer_count = 0
        p2p_manager = getattr(node, "p2p_manager", None)
        if p2p_manager and hasattr(p2p_manager, "get_peer_count"):
            try:
                peer_count = p2p_manager.get_peer_count()
            except (RuntimeError, AttributeError):
                pass

        # Get mempool info
        mempool_size_bytes = stats.get("mempool_size_bytes", 0)
        mempool_size_kb = round(mempool_size_bytes / 1024, 2)
        pending_tx_count = stats.get("pending_transactions_count", 0)

        # Get mining status
        is_mining = getattr(node, "is_mining", False)

        # Calculate average block time from recent blocks
        recent_blocks = _get_block_times(blockchain, 10)
        avg_block_time = 0.0
        if recent_blocks:
            block_times = [b["block_time"] for b in recent_blocks if b["block_time"] > 0]
            if block_times:
                avg_block_time = round(sum(block_times) / len(block_times), 2)

        return success_response({
            "current": {
                "tps": tps_data["tps"],
                "blocks_per_minute": tps_data["blocks_per_minute"],
                "chain_height": stats.get("chain_height", 0),
                "difficulty": stats.get("difficulty", 0),
                "avg_block_time": avg_block_time,
                "peer_count": peer_count,
                "mempool": {
                    "pending_count": pending_tx_count,
                    "size_kb": mempool_size_kb,
                    "size_bytes": mempool_size_bytes,
                },
                "is_mining": is_mining,
                "latest_block_hash": stats.get("latest_block_hash", "")[:16] + "...",
            },
            "timestamp": time.time(),
            "timestamp_iso": datetime.now(timezone.utc).isoformat(),
        })
    except (RuntimeError, ValueError, KeyError, AttributeError) as exc:
        logger.error("Failed to get current metrics: %s", exc, exc_info=True)
        return error_response(f"Metrics unavailable: {type(exc).__name__}", status=500)


@performance_bp.route("/api/metrics/blocks", methods=["GET"])
def get_recent_blocks():
    """Get recent blocks with timing information."""
    blockchain = get_blockchain()
    if not blockchain:
        return error_response("Blockchain not initialized", status=503)

    try:
        count = request.args.get("count", default=20, type=int)
        count = min(max(1, count), 100)  # Clamp to 1-100

        blocks = _get_block_times(blockchain, count)
        return success_response({
            "blocks": blocks,
            "count": len(blocks),
        })
    except (RuntimeError, ValueError, KeyError, AttributeError) as exc:
        logger.error("Failed to get block times: %s", exc, exc_info=True)
        return error_response(f"Block data unavailable: {type(exc).__name__}", status=500)


@performance_bp.route("/api/metrics/history", methods=["GET"])
def get_metrics_history():
    """Get historical metrics for charts."""
    blockchain = get_blockchain()
    if not blockchain:
        return error_response("Blockchain not initialized", status=503)

    try:
        hours = request.args.get("hours", default=1, type=int)
        hours = min(max(1, hours), 24)  # Clamp to 1-24 hours

        history = _get_historical_metrics(hours)
        return success_response({
            "history": history,
        })
    except (RuntimeError, ValueError, KeyError, AttributeError) as exc:
        logger.error("Failed to get history: %s", exc, exc_info=True)
        return error_response(f"History unavailable: {type(exc).__name__}", status=500)


@performance_bp.route("/api/metrics/summary", methods=["GET"])
def get_metrics_summary():
    """Get a full summary for dashboard initialization."""
    blockchain = get_blockchain()
    node = get_node()

    if not blockchain:
        return error_response("Blockchain not initialized", status=503)

    try:
        # Combine all metrics
        stats = blockchain.get_stats()
        tps_data = _calculate_tps(blockchain)
        recent_blocks = _get_block_times(blockchain, 10)
        history_1h = _get_historical_metrics(1)

        # Peer count
        peer_count = 0
        p2p_manager = getattr(node, "p2p_manager", None)
        if p2p_manager and hasattr(p2p_manager, "get_peer_count"):
            try:
                peer_count = p2p_manager.get_peer_count()
            except (RuntimeError, AttributeError):
                pass

        # Node uptime
        start_time = getattr(node, "start_time", 0)
        uptime_seconds = time.time() - start_time if start_time > 0 else 0

        return success_response({
            "chain": {
                "height": stats.get("chain_height", 0),
                "difficulty": stats.get("difficulty", 0),
                "total_supply": stats.get("total_circulating_supply", 0),
                "latest_block_hash": stats.get("latest_block_hash", ""),
            },
            "performance": {
                "tps": tps_data["tps"],
                "blocks_per_minute": tps_data["blocks_per_minute"],
                "tps_avg_1h": history_1h["tps_avg"],
                "tps_max_1h": history_1h["tps_max"],
            },
            "mempool": {
                "pending_count": stats.get("pending_transactions_count", 0),
                "size_bytes": stats.get("mempool_size_bytes", 0),
                "orphan_tx_count": stats.get("orphan_transactions_count", 0),
            },
            "network": {
                "peer_count": peer_count,
                "orphan_blocks": stats.get("orphan_blocks_count", 0),
            },
            "node": {
                "is_mining": getattr(node, "is_mining", False),
                "uptime_seconds": round(uptime_seconds, 0),
            },
            "recent_blocks": recent_blocks,
            "history": history_1h["samples"][-30:],  # Last 30 samples for sparkline
            "timestamp": time.time(),
        })
    except (RuntimeError, ValueError, KeyError, AttributeError) as exc:
        logger.error("Failed to get summary: %s", exc, exc_info=True)
        return error_response(f"Summary unavailable: {type(exc).__name__}", status=500)
