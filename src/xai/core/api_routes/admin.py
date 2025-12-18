"""
Admin Routes Module

Handles all administrative API endpoints including:
- API key management (list, create, revoke)
- API key event logging
- Withdrawal telemetry and status monitoring
- Spending limit configuration

All routes require admin authentication.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Dict, Tuple, Any, Optional

from flask import request

from xai.core.config import Config, ConfigurationError, reload_runtime
from xai.performance.profiling import MemoryProfiler, CPUProfiler
from xai.core.rate_limiter import get_rate_limiter
from xai.core.monitoring import MetricsCollector
from xai.network.peer_manager import PeerManager

if TYPE_CHECKING:
    from xai.core.node_api import NodeAPIRoutes

logger = logging.getLogger(__name__)


def register_admin_routes(routes: "NodeAPIRoutes") -> None:
    """
    Register all admin-related endpoints.

    All routes require admin authentication via _require_admin_auth().

    Routes registered:
    - GET /admin/api-keys - List all API key metadata
    - POST /admin/api-keys - Create new API key
    - DELETE /admin/api-keys/<key_id> - Revoke an API key
    - GET /admin/api-key-events - List API key events with pagination
    - GET /admin/withdrawals/telemetry - Get withdrawal rate and backlog metrics
    - GET /admin/withdrawals/status - Get withdrawal queue status
    - POST /admin/spend-limit - Set per-address daily spending limit
    """
    app = routes.app
    api_auth = routes.api_auth
    api_key_store = routes.api_key_store
    node = routes.node
    spending_limits = routes.spending_limits

    @app.route("/admin/api-keys", methods=["GET"])
    def list_api_keys() -> Tuple[Dict[str, Any], int]:
        """List all API key metadata (admin only)."""
        auth_error = routes._require_control_role({"admin"})
        if auth_error:
            return auth_error

        metadata = api_auth.list_key_metadata()
        return routes._success_response(metadata)

    max_ttl_days = getattr(Config, "API_KEY_MAX_TTL_DAYS", 365)
    allow_permanent_keys = getattr(Config, "API_KEY_ALLOW_PERMANENT", False)

    def _normalize_ttl(payload: Dict[str, Any]) -> Tuple[Optional[int], Optional[Tuple[Dict[str, Any], int]]]:
        """Convert expires_in_days/hours payload fields into seconds."""
        ttl_seconds: Optional[int] = None
        if "expires_in_days" in payload:
            try:
                ttl_seconds = int(float(payload["expires_in_days"]) * 86400)
            except (TypeError, ValueError):
                return None, routes._error_response("Invalid expires_in_days", status=400, code="invalid_payload")
        elif "expires_in_hours" in payload:
            try:
                ttl_seconds = int(float(payload["expires_in_hours"]) * 3600)
            except (TypeError, ValueError):
                return None, routes._error_response("Invalid expires_in_hours", status=400, code="invalid_payload")

        if ttl_seconds is not None and ttl_seconds <= 0:
            return None, routes._error_response("TTL must be positive", status=400, code="invalid_payload")

        if ttl_seconds is not None:
            max_ttl_seconds = max(1, int(max_ttl_days * 86400))
            ttl_seconds = min(ttl_seconds, max_ttl_seconds)
        return ttl_seconds, None

    @app.route("/admin/api-keys", methods=["POST"])
    def create_api_key() -> Tuple[Dict[str, Any], int]:
        """Create a new API key (admin only)."""
        auth_error = routes._require_control_role({"admin"})
        if auth_error:
            return auth_error

        payload = request.get_json(silent=True) or {}
        label = str(payload.get("label", "")).strip()
        scope = str(payload.get("scope", "user")).strip().lower() or "user"
        permanent = bool(payload.get("permanent", False))
        ttl_seconds, ttl_error = _normalize_ttl(payload)
        if ttl_error:
            return ttl_error
        if permanent and not allow_permanent_keys:
            return routes._error_response(
                "Permanent API keys are disabled",
                status=400,
                code="permanent_keys_disabled",
            )

        if scope not in {"user", "operator", "auditor", "admin"}:
            return routes._error_response("Invalid scope", status=400, code="invalid_payload")

        try:
            api_key, key_id = api_auth.issue_key(label=label, scope=scope, ttl_seconds=ttl_seconds, permanent=permanent)
            metadata: Dict[str, Any] = {}
            if api_key_store:
                metadata = api_key_store.list_keys().get(key_id, {})
            routes._log_event(
                "api_key_issued",
                {
                    "key_id": key_id,
                    "label": label,
                    "scope": scope,
                    "expires_at": metadata.get("expires_at"),
                    "permanent": metadata.get("permanent", False),
                },
                severity="INFO",
            )
            return routes._success_response(
                {
                    "api_key": api_key,
                    "key_id": key_id,
                    "scope": scope,
                    "expires_at": metadata.get("expires_at"),
                    "permanent": metadata.get("permanent", False),
                },
                status=201,
            )
        except ValueError as exc:
            logger.warning(
                "ValueError in create_api_key",
                extra={
                    "error_type": "ValueError",
                    "error": str(exc),
                    "function": "create_api_key"
                }
            )
            return routes._error_response(str(exc), status=500, code="admin_error")

    @app.route("/admin/api-keys/<key_id>", methods=["DELETE"])
    def delete_api_key(key_id: str) -> Tuple[Dict[str, Any], int]:
        """Revoke an API key (admin only)."""
        auth_error = routes._require_control_role({"admin"})
        if auth_error:
            return auth_error

        try:
            if api_auth.revoke_key(key_id):
                routes._log_event("api_key_revoked", {"key_id": key_id}, severity="WARNING")
                return routes._success_response({"revoked": True})
        except ValueError as exc:
            logger.warning(
                "ValueError in delete_api_key",
                extra={
                    "error_type": "ValueError",
                    "error": str(exc),
                    "function": "delete_api_key"
                }
            )
            return routes._error_response(str(exc), status=500, code="admin_error")

        return routes._error_response("API key not found", status=404, code="not_found")

    @app.route("/admin/api-key-events", methods=["GET"])
    def list_api_key_events() -> Tuple[Dict[str, Any], int]:
        """List API key events with pagination (admin only)."""
        auth_error = routes._require_control_role({"admin", "auditor"})
        if auth_error:
            return auth_error

        limit = request.args.get("limit", default=100, type=int)
        events = api_key_store.get_events(limit=limit)
        return routes._success_response({"events": events})

    @app.route("/admin/withdrawals/telemetry", methods=["GET"])
    def get_withdrawal_telemetry() -> Tuple[Dict[str, Any], int]:
        """Get withdrawal telemetry metrics (admin only)."""
        auth_error = routes._require_control_role({"admin", "operator"})
        if auth_error:
            return auth_error

        limiter = routes._get_admin_rate_limiter()
        identifier = f"admin-telemetry:{request.remote_addr or 'unknown'}"
        allowed, error = limiter.check_rate_limit(identifier, "/admin/withdrawals/telemetry")
        if not allowed:
            return routes._error_response(
                error or "Rate limit exceeded",
                status=429,
                code="rate_limited",
                context={"identifier": identifier},
            )

        limit = request.args.get("limit", default=20, type=int) or 20
        limit = max(1, min(limit, 200))

        collector = getattr(node, "metrics_collector", None) or MetricsCollector.instance()
        events = collector.get_recent_withdrawals(limit=limit)
        rate_metric = collector.get_metric("xai_withdrawals_rate_per_minute")
        backlog_metric = collector.get_metric("xai_withdrawals_time_locked_backlog")

        payload = {
            "rate_per_minute": rate_metric.value if rate_metric else 0,
            "time_locked_backlog": backlog_metric.value if backlog_metric else 0,
            "recent_withdrawals": events,
            "log_path": getattr(collector, "withdrawal_event_log_path", None),
        }

        routes._log_event(
            "admin_withdrawals_telemetry_access",
            {
                "rate_per_minute": payload["rate_per_minute"],
                "time_locked_backlog": payload["time_locked_backlog"],
                "events_served": len(events),
            },
            severity="INFO",
        )

        return routes._success_response(payload)

    @app.route("/admin/withdrawals/status", methods=["GET"])
    def get_withdrawal_status_snapshot() -> Tuple[Dict[str, Any], int]:
        """Get withdrawal queue status snapshot (admin only)."""
        auth_error = routes._require_control_role({"admin", "operator", "auditor"})
        if auth_error:
            return auth_error

        limiter = routes._get_admin_rate_limiter()
        identifier = f"admin-withdrawal-status:{request.remote_addr or 'unknown'}"
        allowed, error = limiter.check_rate_limit(identifier, "/admin/withdrawals/status")
        if not allowed:
            return routes._error_response(
                error or "Rate limit exceeded",
                status=429,
                code="rate_limited",
                context={"identifier": identifier},
            )

        manager = getattr(node, "exchange_wallet_manager", None)
        if not manager:
            return routes._error_response(
                "Exchange wallet manager unavailable",
                status=503,
                code="service_unavailable",
            )

        limit = request.args.get("limit", default=25, type=int) or 25
        limit = max(1, min(limit, 200))

        status_param = request.args.get("status", default="")
        valid_statuses = {"pending", "completed", "failed", "flagged"}

        if status_param:
            requested = {item.strip().lower() for item in status_param.split(",") if item.strip()}
            invalid = requested - valid_statuses
            if invalid:
                return routes._error_response(
                    "Invalid status filter",
                    status=400,
                    code="invalid_status",
                    context={"invalid": sorted(invalid)},
                )
            target_statuses = requested or valid_statuses
        else:
            target_statuses = valid_statuses

        withdrawals = {
            status: manager.get_withdrawals_by_status(status, limit)
            for status in sorted(target_statuses)
        }
        counts = manager.get_withdrawal_counts()

        processor_stats = None
        if hasattr(node, "get_withdrawal_processor_stats"):
            processor_stats = node.get_withdrawal_processor_stats()

        payload = {
            "counts": counts,
            "queue_depth": counts.get("pending", 0),
            "latest_processor_run": processor_stats,
            "withdrawals": withdrawals,
        }

        routes._log_event(
            "admin_withdrawals_status_access",
            {
                "queue_depth": payload["queue_depth"],
                "statuses": sorted(list(target_statuses)),
                "limit": limit,
            },
            severity="INFO",
        )

        return routes._success_response(payload)

    @app.route("/admin/spend-limit", methods=["POST"])
    def set_spend_limit() -> Tuple[Dict[str, Any], int]:
        """Set per-address daily spending limit (admin only)."""
        auth_error = routes._require_control_role({"admin"})
        if auth_error:
            return auth_error

        payload = request.get_json(silent=True) or {}
        address = str(payload.get("address", "")).strip()

        try:
            limit = float(payload.get("limit"))
        except (TypeError, ValueError) as e:
            logger.debug("Invalid limit value in spending limit request", error=str(e))
            return routes._error_response("Invalid limit", status=400, code="invalid_payload")

        if not address or limit <= 0:
            return routes._error_response(
                "Invalid address or limit",
                status=400,
                code="invalid_payload"
            )

        try:
            spending_limits.set_limit(address, limit)
            routes._log_event(
                "spend_limit_set",
                {"address": address, "limit": limit},
                severity="INFO",
            )
            return routes._success_response(
                {"address": address, "limit": limit},
                status=201
            )
        except (OSError, IOError) as exc:
            logger.error(
                "Storage error setting spend limit: %s",
                str(exc),
                extra={
                    "event": "api.spend_limit_storage_error",
                    "address": address,
                    "limit": limit,
                },
                exc_info=True,
            )
            return routes._error_response("Failed to persist spending limit", status=500, code="storage_error")
        except RuntimeError as exc:
            logger.error(
                "Runtime error setting spend limit: %s",
                str(exc),
                extra={
                    "event": "api.spend_limit_runtime_error",
                    "address": address,
                    "limit": limit,
                },
                exc_info=True,
            )
            return routes._error_response(str(exc), status=500, code="admin_error")

    @app.route("/admin/emergency/status", methods=["GET"])
    def get_emergency_status() -> Tuple[Dict[str, Any], int]:
        """Return emergency pause and circuit breaker status (admin only)."""
        auth_error = routes._require_control_role({"admin", "operator", "auditor"})
        if auth_error:
            return auth_error

        pause_manager = getattr(routes, "emergency_pause_manager", None)
        circuit_breaker = getattr(routes, "emergency_circuit_breaker", None)
        if not pause_manager or not circuit_breaker:
            return routes._error_response(
                "Emergency controls unavailable",
                status=503,
                code="service_unavailable",
            )

        status = pause_manager.get_status()
        status["circuit_breaker"] = circuit_breaker.snapshot()
        return routes._success_response(status)

    @app.route("/admin/emergency/pause", methods=["POST"])
    def pause_operations() -> Tuple[Dict[str, Any], int]:
        """Manually pause node operations (admin only)."""
        auth_error = routes._require_control_role({"admin", "operator"})
        if auth_error:
            return auth_error

        pause_manager = getattr(routes, "emergency_pause_manager", None)
        if not pause_manager:
            return routes._error_response(
                "Emergency controls unavailable",
                status=503,
                code="service_unavailable",
            )

        payload = request.get_json(silent=True) or {}
        reason = str(payload.get("reason") or "Manual emergency pause").strip()
        try:
            pause_manager.pause_operations(Config.EMERGENCY_PAUSER_ADDRESS, reason=reason)
            routes._log_event(
                "admin_emergency_pause",
                {"reason": reason},
                severity="CRITICAL",
            )
            return routes._success_response({"paused": True, "reason": reason})
        except PermissionError as exc:
            return routes._error_response(
                str(exc),
                status=403,
                code="forbidden",
            )

    @app.route("/admin/emergency/unpause", methods=["POST"])
    def unpause_operations() -> Tuple[Dict[str, Any], int]:
        """Manually unpause node operations (admin only)."""
        auth_error = routes._require_control_role({"admin", "operator"})
        if auth_error:
            return auth_error

        pause_manager = getattr(routes, "emergency_pause_manager", None)
        if not pause_manager:
            return routes._error_response(
                "Emergency controls unavailable",
                status=503,
                code="service_unavailable",
            )

        payload = request.get_json(silent=True) or {}
        reason = str(payload.get("reason") or "Manual unpause").strip()
        try:
            pause_manager.unpause_operations(Config.EMERGENCY_PAUSER_ADDRESS, reason=reason)
            routes._log_event(
                "admin_emergency_unpause",
                {"reason": reason},
                severity="WARNING",
            )
            return routes._success_response({"paused": False, "reason": reason})
        except PermissionError as exc:
            return routes._error_response(
                str(exc),
                status=403,
                code="forbidden",
            )

    @app.route("/admin/emergency/circuit-breaker/trip", methods=["POST"])
    def trip_circuit_breaker() -> Tuple[Dict[str, Any], int]:
        """Force-open the global circuit breaker and auto-pause operations."""
        auth_error = routes._require_control_role({"admin"})
        if auth_error:
            return auth_error

        breaker = getattr(routes, "emergency_circuit_breaker", None)
        pause_manager = getattr(routes, "emergency_pause_manager", None)
        if not breaker or not pause_manager:
            return routes._error_response(
                "Emergency controls unavailable",
                status=503,
                code="service_unavailable",
            )

        breaker.force_open()
        pause_manager.check_and_auto_pause()
        routes._log_event(
            "admin_circuit_breaker_trip",
            {"state": breaker.state.value},
            severity="CRITICAL",
        )
        return routes._success_response({"state": breaker.state.value, "paused": pause_manager.is_paused()})

    @app.route("/admin/emergency/circuit-breaker/reset", methods=["POST"])
    def reset_circuit_breaker() -> Tuple[Dict[str, Any], int]:
        """Reset the global circuit breaker and clear automated pauses (admin only)."""
        auth_error = routes._require_control_role({"admin"})
        if auth_error:
            return auth_error

        breaker = getattr(routes, "emergency_circuit_breaker", None)
        pause_manager = getattr(routes, "emergency_pause_manager", None)
        if not breaker or not pause_manager:
            return routes._error_response(
                "Emergency controls unavailable",
                status=503,
                code="service_unavailable",
            )

        breaker.reset()
        pause_manager.unpause_operations(
            caller_address=Config.EMERGENCY_PAUSER_ADDRESS,
            reason="Manual circuit breaker reset",
        )
        routes._log_event(
            "admin_circuit_breaker_reset",
            {"state": breaker.state.value},
            severity="INFO",
        )
        return routes._success_response({"state": breaker.state.value, "paused": pause_manager.is_paused()})

    @app.route("/admin/mining/status", methods=["GET"])
    def admin_mining_status() -> Tuple[Dict[str, Any], int]:
        """Return node mining status and pause context (admin/operator/auditor)."""
        auth_error = routes._require_control_role({"admin", "operator", "auditor"})
        if auth_error:
            return auth_error

        pause_manager = getattr(routes, "emergency_pause_manager", None)
        pause_status: Dict[str, Any] = {}
        if pause_manager and pause_manager.is_paused():
            pause_status = pause_manager.get_status()

        payload = {
            "is_mining": bool(node.is_mining),
            "miner_address": getattr(node, "miner_address", None),
            "paused": bool(pause_status.get("is_paused")),
            "pause_reason": pause_status.get("reason"),
            "paused_by": pause_status.get("paused_by"),
            "paused_timestamp": pause_status.get("paused_timestamp"),
        }
        return routes._success_response(payload)

    @app.route("/admin/mining/enable", methods=["POST"])
    def admin_enable_mining() -> Tuple[Dict[str, Any], int]:
        """Enable node auto-mining (admin/operator)."""
        auth_error = routes._require_control_role({"admin", "operator"})
        if auth_error:
            return auth_error

        paused = routes._reject_if_paused("admin_enable_mining")
        if paused:
            return paused

        if node.is_mining:
            return routes._success_response(
                {"started": False, "message": "Mining already active", "is_mining": True}
            )

        try:
            node.start_mining()
            routes._log_event(
                "admin_mining_enable",
                {"miner_address": getattr(node, "miner_address", None)},
                severity="WARNING",
            )
            return routes._success_response(
                {"started": True, "message": "Mining enabled", "is_mining": True}
            )
        except Exception as exc:  # pylint: disable=broad-except
            return routes._handle_exception(exc, "admin_enable_mining")

    @app.route("/admin/mining/disable", methods=["POST"])
    def admin_disable_mining() -> Tuple[Dict[str, Any], int]:
        """Disable auto-mining (admin/operator)."""
        auth_error = routes._require_control_role({"admin", "operator"})
        if auth_error:
            return auth_error

        if not node.is_mining:
            return routes._success_response(
                {"stopped": False, "message": "Mining already stopped", "is_mining": False}
            )

        try:
            node.stop_mining()
            routes._log_event(
                "admin_mining_disable",
                {"miner_address": getattr(node, "miner_address", None)},
                severity="INFO",
            )
            return routes._success_response(
                {"stopped": True, "message": "Mining disabled", "is_mining": False}
            )
        except Exception as exc:  # pylint: disable=broad-except
            return routes._handle_exception(exc, "admin_disable_mining")

    def _require_peer_manager() -> PeerManager | None:
        manager = getattr(node, "peer_manager", None)
        required = ("disconnect_peer", "ban_peer", "unban_peer")
        if manager and all(hasattr(manager, attr) for attr in required):
            return manager
        return None

    def _memory_profiler() -> MemoryProfiler:
        profiler = getattr(routes, "memory_profiler", None)
        if not isinstance(profiler, MemoryProfiler):
            profiler = MemoryProfiler()
            routes.memory_profiler = profiler
        return profiler

    def _cpu_profiler() -> CPUProfiler:
        profiler = getattr(routes, "cpu_profiler", None)
        if not isinstance(profiler, CPUProfiler):
            profiler = CPUProfiler()
            routes.cpu_profiler = profiler
        return profiler

    @app.route("/admin/peers", methods=["GET"])
    def admin_peer_status() -> Tuple[Dict[str, Any], int]:
        """Return detailed peer snapshot (admin/operator/auditor)."""
        auth_error = routes._require_control_role({"admin", "operator", "auditor"})
        if auth_error:
            return auth_error

        snapshot = routes._build_peer_snapshot()
        manager = _require_peer_manager()
        snapshot.update(
            {
                "ban_counts": getattr(manager, "ban_counts", {}),
                "banned_until": getattr(manager, "banned_until", {}),
            }
        )
        return routes._success_response(snapshot)

    @app.route("/admin/peers/disconnect", methods=["POST"])
    def admin_peer_disconnect() -> Tuple[Dict[str, Any], int]:
        """Disconnect a peer immediately (admin/operator)."""
        auth_error = routes._require_control_role({"admin", "operator"})
        if auth_error:
            return auth_error

        manager = _require_peer_manager()
        if not manager:
            return routes._error_response(
                "Peer manager unavailable",
                status=503,
                code="service_unavailable",
            )

        payload = request.get_json(silent=True) or {}
        peer_id = str(payload.get("peer_id") or "").strip()
        if not peer_id:
            return routes._error_response("peer_id required", status=400, code="invalid_payload")

        manager.disconnect_peer(peer_id)
        routes._log_event(
            "admin_peer_disconnect",
            {"peer_id": peer_id},
            severity="WARNING",
        )
        return routes._success_response({"disconnected": True, "peer_id": peer_id})

    @app.route("/admin/peers/ban", methods=["POST"])
    def admin_peer_ban() -> Tuple[Dict[str, Any], int]:
        """Ban a peer/IP and drop active connections (admin/operator)."""
        auth_error = routes._require_control_role({"admin", "operator"})
        if auth_error:
            return auth_error

        manager = _require_peer_manager()
        if not manager:
            return routes._error_response(
                "Peer manager unavailable",
                status=503,
                code="service_unavailable",
            )

        payload = request.get_json(silent=True) or {}
        peer_id = str(payload.get("peer_id") or payload.get("ip_address") or "").strip()
        reason = str(payload.get("reason") or "Manual ban").strip()
        if not peer_id:
            return routes._error_response("peer_id required", status=400, code="invalid_payload")

        try:
            manager.ban_peer(peer_id)
            routes._log_event(
                "admin_peer_ban",
                {"peer_id": peer_id, "reason": reason},
                severity="CRITICAL",
            )
            return routes._success_response({"banned": True, "peer_id": peer_id, "reason": reason})
        except Exception as exc:  # pylint: disable=broad-except
            return routes._handle_exception(exc, "admin_peer_ban")

    @app.route("/admin/peers/unban", methods=["POST"])
    def admin_peer_unban() -> Tuple[Dict[str, Any], int]:
        """Remove a peer/IP from the ban list (admin/operator)."""
        auth_error = routes._require_control_role({"admin", "operator"})
        if auth_error:
            return auth_error

        manager = _require_peer_manager()
        if not manager:
            return routes._error_response(
                "Peer manager unavailable",
                status=503,
                code="service_unavailable",
            )

        payload = request.get_json(silent=True) or {}
        peer_id = str(payload.get("peer_id") or payload.get("ip_address") or "").strip()
        if not peer_id:
            return routes._error_response("peer_id required", status=400, code="invalid_payload")

        try:
            manager.unban_peer(peer_id)
            routes._log_event(
                "admin_peer_unban",
                {"peer_id": peer_id},
                severity="INFO",
            )
            return routes._success_response({"unbanned": True, "peer_id": peer_id})
        except Exception as exc:  # pylint: disable=broad-except
            return routes._handle_exception(exc, "admin_peer_unban")

    @app.route("/admin/config/reload", methods=["POST"])
    def admin_config_reload() -> Tuple[Dict[str, Any], int]:
        """Reload runtime configuration from environment (admin only)."""
        auth_error = routes._require_control_role({"admin"})
        if auth_error:
            return auth_error

        payload = request.get_json(silent=True) or {}
        overrides = payload.get("overrides")
        if overrides is not None and not isinstance(overrides, dict):
            return routes._error_response(
                "overrides must be an object",
                status=400,
                code="invalid_payload",
            )

        try:
            result = reload_runtime(overrides=overrides)
        except ConfigurationError as exc:
            return routes._error_response(str(exc), status=400, code="invalid_payload")

        routes._body_size_limit = max(1, int(getattr(Config, "API_MAX_JSON_BYTES", routes._body_size_limit)))
        routes.app.config["MAX_CONTENT_LENGTH"] = routes._body_size_limit

        changed_fields = list(result.get("changed", {}).keys())
        routes._log_event(
            "admin_config_reload",
            {"overrides": list((overrides or {}).keys()), "changed": changed_fields},
            severity="INFO",
        )
        return routes._success_response(result)

    @app.route("/admin/profiling/status", methods=["GET"])
    def admin_profiling_status() -> Tuple[Dict[str, Any], int]:
        """Return profiling subsystem status (admin/operator)."""
        auth_error = routes._require_control_role({"admin", "operator"})
        if auth_error:
            return auth_error

        memory = _memory_profiler()
        cpu = _cpu_profiler()
        memory_stats = memory.get_memory_stats() if memory.is_profiling else {}
        cpu_hotspots = cpu.get_hotspots(top_n=5) if cpu.profiler else []
        payload = {
            "memory": {
                "running": memory.is_profiling,
                "snapshot_count": len(memory.snapshots),
                "stats": memory_stats,
            },
            "cpu": {
                "running": cpu.is_profiling,
                "has_profiler": cpu.profiler is not None,
                "hotspots": cpu_hotspots,
            },
        }
        return routes._success_response(payload)

    @app.route("/admin/profiling/memory/start", methods=["POST"])
    def admin_memory_start() -> Tuple[Dict[str, Any], int]:
        auth_error = routes._require_control_role({"admin"})
        if auth_error:
            return auth_error
        profiler = _memory_profiler()
        if profiler.is_profiling:
            return routes._success_response({"started": False, "message": "Memory profiler already running"})
        profiler.start()
        routes._log_event("admin_memory_profiler_start", {"snapshots": len(profiler.snapshots)}, severity="INFO")
        return routes._success_response({"started": True})

    @app.route("/admin/profiling/memory/stop", methods=["POST"])
    def admin_memory_stop() -> Tuple[Dict[str, Any], int]:
        auth_error = routes._require_control_role({"admin"})
        if auth_error:
            return auth_error
        profiler = _memory_profiler()
        if not profiler.is_profiling:
            return routes._success_response({"stopped": False, "message": "Memory profiler not running"})
        profiler.stop()
        routes._log_event("admin_memory_profiler_stop", {"snapshots": len(profiler.snapshots)}, severity="INFO")
        return routes._success_response({"stopped": True})

    @app.route("/admin/profiling/memory/snapshot", methods=["POST"])
    def admin_memory_snapshot() -> Tuple[Dict[str, Any], int]:
        auth_error = routes._require_control_role({"admin", "operator"})
        if auth_error:
            return auth_error

        profiler = _memory_profiler()
        if not profiler.is_profiling:
            return routes._error_response("Memory profiler not running", status=400, code="profiler_inactive")

        payload = request.get_json(silent=True) or {}
        top_n = int(payload.get("top_n") or 10)
        snapshot = profiler.take_snapshot(top_n=top_n)
        return routes._success_response(
            {
                "timestamp": snapshot.timestamp,
                "current_mb": snapshot.current_mb,
                "peak_mb": snapshot.peak_mb,
                "top_allocations": snapshot.top_allocations,
                "snapshot_count": len(profiler.snapshots),
            }
        )

    @app.route("/admin/profiling/cpu/start", methods=["POST"])
    def admin_cpu_start() -> Tuple[Dict[str, Any], int]:
        auth_error = routes._require_control_role({"admin"})
        if auth_error:
            return auth_error

        profiler = _cpu_profiler()
        if profiler.is_profiling:
            return routes._success_response({"started": False, "message": "CPU profiler already running"})
        profiler.start()
        routes._log_event("admin_cpu_profiler_start", {}, severity="INFO")
        return routes._success_response({"started": True})

    @app.route("/admin/profiling/cpu/stop", methods=["POST"])
    def admin_cpu_stop() -> Tuple[Dict[str, Any], int]:
        auth_error = routes._require_control_role({"admin"})
        if auth_error:
            return auth_error

        profiler = _cpu_profiler()
        if not profiler.is_profiling:
            return routes._success_response({"stopped": False, "message": "CPU profiler not running"})
        profiler.stop()
        summary = profiler.get_stats(top_n=20)
        routes._log_event("admin_cpu_profiler_stop", {"summary_length": len(summary)}, severity="INFO")
        return routes._success_response({"stopped": True, "summary": summary})

    @app.route("/admin/profiling/cpu/hotspots", methods=["GET"])
    def admin_cpu_hotspots() -> Tuple[Dict[str, Any], int]:
        auth_error = routes._require_control_role({"admin", "operator"})
        if auth_error:
            return auth_error

        profiler = _cpu_profiler()
        top_n = int(request.args.get("top", 10))
        hotspots = profiler.get_hotspots(top_n=top_n)
        return routes._success_response({"hotspots": hotspots, "running": profiler.is_profiling})
