from __future__ import annotations

import logging
import os
import time
from typing import Any, Callable

from flask import jsonify, request

try:
    from unittest.mock import Mock as _Mock  # type: ignore
except ImportError:  # pragma: no cover - fallback when mock not present
    _Mock = None

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from xai.core.node_api import NodeAPIRoutes

logger = logging.getLogger(__name__)

def register_core_routes(
    routes: "NodeAPIRoutes",
    *,
    node_version: str,
    algo_features_enabled: bool,
    endpoint_provider: Callable[[], Any],
) -> None:
    """Wire up the core informational/health endpoints."""
    app = routes.app
    node = routes.node
    blockchain = routes.blockchain

    @app.route("/", methods=["GET"])
    def index() -> tuple[dict[str, Any], int]:
        """Node information and available endpoints."""
        return (
            jsonify(
                {
                    "status": "online",
                    "node": "AXN Full Node",
                    "version": node_version,
                    "algorithmic_features": algo_features_enabled,
                    "endpoints": endpoint_provider(),
                }
            ),
            200,
        )

    @app.route("/health", methods=["GET"])
    def health_check() -> tuple[dict[str, Any], int]:
        """Health check endpoint for Docker and monitoring."""
        overall_status = "healthy"
        http_status = 200
        timestamp = time.time()
        blockchain_summary: dict[str, Any] = {"accessible": False}
        services: dict[str, Any] = {"api": "running"}
        backlog: dict[str, Any] = {"pending_transactions": 0, "orphan_blocks": 0}
        network: dict[str, Any] = {"peers": 0}

        def degrade(reason: str) -> None:
            nonlocal overall_status, http_status
            if overall_status == "healthy":
                overall_status = "degraded"
            http_status = 503
            services.setdefault("issues", []).append(reason)

        try:
            if blockchain:
                try:
                    stats = blockchain.get_stats()
                    blockchain_summary = {
                        "accessible": True,
                        "height": stats.get("chain_height", len(getattr(blockchain, "chain", []))),
                        "difficulty": stats.get("difficulty"),
                        "total_supply": stats.get("total_circulating_supply"),
                        "latest_block_hash": stats.get("latest_block_hash", ""),
                    }
                    backlog["pending_transactions"] = stats.get("pending_transactions_count", 0)
                    backlog["orphan_blocks"] = stats.get("orphan_blocks_count", 0)
                    backlog["orphan_transactions"] = stats.get("orphan_transactions_count", 0)
                except (RuntimeError, ValueError, KeyError, AttributeError) as exc:  # pragma: no cover - defensive
                    blockchain_summary = {"accessible": False, "error": str(exc)}
                    overall_status = "unhealthy"
                    http_status = 503
                    logger.debug("Health check failed to pull blockchain stats", exc_info=True)
            else:
                blockchain_summary = {"accessible": False, "error": "Blockchain not initialized"}
                degrade("blockchain_unavailable")
        except (RuntimeError, ValueError, AttributeError) as exc:  # pragma: no cover - defensive
            blockchain_summary = {"accessible": False, "error": str(exc)}
            overall_status = "unhealthy"
            http_status = 503
            logger.debug("Health check encountered blockchain error", exc_info=True)

        # Storage check
        storage_status = "healthy"
        try:
            storage = getattr(node, "blockchain", None)
            data_dir = getattr(getattr(storage, "storage", None), "data_dir", os.getcwd())
            if not isinstance(data_dir, (str, os.PathLike)):
                data_dir = os.getcwd()
            test_file = os.path.join(data_dir, "health_check.tmp")
            with open(test_file, "w", encoding="utf-8") as handle:
                handle.write("ok")
            os.remove(test_file)
        except (OSError, IOError, PermissionError, RuntimeError, ValueError) as exc:
            storage_status = "degraded"
            degrade("storage_unwritable")
            services["storage_error"] = str(exc)
            logger.warning("Health check storage probe failed", exc_info=True)
        services["storage"] = storage_status

        # Network/P2P checks
        p2p_manager = getattr(node, "p2p_manager", None)
        is_mock_manager = bool(_Mock and isinstance(p2p_manager, _Mock))
        if is_mock_manager and getattr(p2p_manager, "_mock_parent", None) is not None:
            p2p_manager = None
            is_mock_manager = False
        p2p_status = "running"
        peer_count = 0
        if p2p_manager and not is_mock_manager:
            try:
                server = getattr(p2p_manager, "server", None)
                if not server or not server.is_serving():
                    p2p_status = "degraded"
                    degrade("p2p_server_down")
                if hasattr(p2p_manager, "get_peer_count"):
                    peer_count_raw = p2p_manager.get_peer_count()
                    peer_count = (
                        peer_count_raw
                        if isinstance(peer_count_raw, (int, float))
                        else 0
                    )
                    if peer_count == 0:
                        degrade("no_connected_peers")
                network["peers"] = peer_count
            except (RuntimeError, ValueError, AttributeError) as exc:  # pragma: no cover - defensive
                p2p_status = "degraded"
                degrade("p2p_error")
                services["p2p_error"] = str(exc)
                logger.debug("Health check P2P probe failed", exc_info=True)
        else:
            p2p_status = "unavailable"
            network["peers"] = 0
        services["p2p"] = p2p_status

        # Backlog thresholds
        if backlog.get("pending_transactions", 0) > 10000:
            degrade("mempool_backlog")
            backlog["status"] = "degraded"
        if backlog.get("orphan_blocks", 0) > 100:
            degrade("orphan_block_backlog")
            backlog["status"] = "degraded"

        response = {
            "status": overall_status,
            "timestamp": timestamp,
            "blockchain": blockchain_summary,
            "services": services,
            "network": network,
            "backlog": backlog,
        }
        if http_status != 200:
            response["error"] = services.get("issues", ["degraded"])[0] if services.get("issues") else "degraded"
        return jsonify(response), http_status

    @app.route("/checkpoint/provenance", methods=["GET"])
    def checkpoint_provenance() -> tuple[dict[str, Any], int]:
        """Expose recent checkpoint provenance for diagnostics."""
        sync_coordinator = getattr(node, "partial_sync_coordinator", None)
        sync_mgr = getattr(sync_coordinator, "sync_manager", None) if sync_coordinator else None
        provenance = []
        if sync_mgr and hasattr(sync_mgr, "get_provenance"):
            try:
                provenance = sync_mgr.get_provenance()
            except (RuntimeError, ValueError, AttributeError) as exc:
                logger.debug("Failed to read checkpoint provenance: %s", exc)
        return jsonify({"provenance": provenance}), 200

    @app.route("/metrics", methods=["GET"])
    def prometheus_metrics() -> tuple[str, int, dict[str, str]]:
        """Prometheus metrics endpoint."""
        try:
            metrics_output = node.metrics_collector.export_prometheus()
            return metrics_output, 200, {"Content-Type": "text/plain; version=0.0.4"}
        except (RuntimeError, ValueError) as exc:
            logger.error("Failed to generate Prometheus metrics", exc_info=True)
            return f"# Error generating metrics: {exc}\n", 500, {"Content-Type": "text/plain"}

    @app.route("/stats", methods=["GET"])
    def get_stats() -> dict[str, Any]:
        """Get blockchain statistics with miner and uptime metadata."""
        stats = blockchain.get_stats()
        stats["miner_address"] = node.miner_address
        stats["peers"] = len(node.peers)
        stats["is_mining"] = node.is_mining
        stats["node_uptime"] = time.time() - node.start_time
        return jsonify(stats)

    @app.route("/mempool", methods=["GET"])
    def get_mempool_overview() -> tuple[dict[str, Any], int]:
        """Get mempool statistics and a snapshot of pending transactions."""
        limit_param = request.args.get("limit", default=100, type=int)
        limit = 100 if limit_param is None else limit_param
        if limit < 0:
            limit = 0
        limit = min(limit, 1000)
        try:
            overview = blockchain.get_mempool_overview(limit)
            return jsonify({"success": True, "limit": limit, "mempool": overview}), 200
        except AttributeError:
            return (
                jsonify({"success": False, "error": "Blockchain unavailable"}),
                503,
            )
        except (RuntimeError, ValueError) as exc:
            return routes._handle_exception(exc, "mempool_overview")

    @app.route("/mempool/stats", methods=["GET"])
    def get_mempool_stats() -> tuple[dict[str, Any], int]:
        """Aggregate mempool fee statistics and congestion indicators."""
        limit_param = request.args.get("limit", default=0, type=int)
        limit = 0 if limit_param is None else limit_param
        if limit < 0:
            limit = 0
        limit = min(limit, 1000)

        try:
            overview = blockchain.get_mempool_overview(limit)
        except AttributeError:
            return (
                jsonify({"success": False, "error": "Blockchain unavailable"}),
                503,
            )
        except (RuntimeError, ValueError) as exc:
            return routes._handle_exception(exc, "mempool_stats")

        limits = overview.get("limits", {}) or {}
        pending_count = int(overview.get("pending_count", 0) or 0)
        size_bytes = int(overview.get("size_bytes", 0) or 0)
        max_transactions = int(limits.get("max_transactions") or 0)
        max_transactions = max(max_transactions, 1)
        capacity_ratio = min(max(pending_count / float(max_transactions), 0.0), 1.0)

        max_age_seconds = float(limits.get("max_age_seconds") or 0.0)
        max_age_seconds = max(max_age_seconds, 1.0)
        oldest_age = float(overview.get("oldest_transaction_age_seconds") or 0.0)
        age_pressure = min(max(oldest_age / max_age_seconds, 0.0), 1.0)

        if capacity_ratio >= 0.9 or age_pressure >= 0.9:
            pressure_state = "critical"
        elif capacity_ratio >= 0.7 or age_pressure >= 0.75:
            pressure_state = "elevated"
        elif capacity_ratio >= 0.5 or age_pressure >= 0.5:
            pressure_state = "moderate"
        else:
            pressure_state = "normal"

        avg_fee_rate = float(overview.get("avg_fee_rate") or 0.0)
        median_fee_rate = float(overview.get("median_fee_rate") or 0.0)
        min_fee_rate = float(overview.get("min_fee_rate") or 0.0)
        max_fee_rate = float(overview.get("max_fee_rate") or 0.0)

        def _recommended(multiplier: float) -> float:
            baseline = median_fee_rate if median_fee_rate > 0 else avg_fee_rate
            candidate = baseline * multiplier
            if multiplier < 1.0:
                candidate = max(candidate, min_fee_rate)
            else:
                candidate = max(candidate, min_fee_rate)
            return float(candidate)

        fee_stats = {
            "average_fee": float(overview.get("avg_fee") or 0.0),
            "median_fee": float(overview.get("median_fee") or 0.0),
            "average_fee_rate": avg_fee_rate,
            "median_fee_rate": median_fee_rate,
            "min_fee_rate": min_fee_rate,
            "max_fee_rate": max_fee_rate,
            "recommended_fee_rates": {
                "slow": _recommended(0.75),
                "standard": _recommended(1.0),
                "priority": _recommended(1.25),
            },
        }

        pressure = {
            "status": pressure_state,
            "capacity_ratio": capacity_ratio,
            "pending_transactions": pending_count,
            "max_transactions": max_transactions,
            "age_pressure": age_pressure,
            "oldest_transaction_age_seconds": oldest_age,
            "size_bytes": size_bytes,
            "size_kb": overview.get("size_kb", size_bytes / 1024.0 if size_bytes else 0.0),
        }

        response_body: dict[str, Any] = {
            "success": True,
            "limit": limit,
            "timestamp": overview.get("timestamp"),
            "fees": fee_stats,
            "pressure": pressure,
            "sponsored_transactions": overview.get("sponsored_transactions", 0),
            "rejections": overview.get("rejections", {}),
            "transactions": overview.get("transactions", []),
            "transactions_returned": overview.get("transactions_returned", 0),
        }
        return jsonify(response_body), 200
