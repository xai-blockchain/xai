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
from typing import TYPE_CHECKING, Dict, Tuple, Any

from flask import request

from xai.core.rate_limiter import get_rate_limiter
from xai.core.monitoring import MetricsCollector

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
        auth_error = routes._require_admin_auth()
        if auth_error:
            return auth_error

        metadata = api_auth.list_key_metadata()
        return routes._success_response(metadata)

    @app.route("/admin/api-keys", methods=["POST"])
    def create_api_key() -> Tuple[Dict[str, Any], int]:
        """Create a new API key (admin only)."""
        auth_error = routes._require_admin_auth()
        if auth_error:
            return auth_error

        payload = request.get_json(silent=True) or {}
        label = str(payload.get("label", "")).strip()
        scope = str(payload.get("scope", "user")).strip().lower() or "user"

        if scope not in {"user", "admin"}:
            return routes._error_response("Invalid scope", status=400, code="invalid_payload")

        try:
            api_key, key_id = api_auth.issue_key(label=label, scope=scope)
            routes._log_event(
                "api_key_issued",
                {"key_id": key_id, "label": label, "scope": scope},
                severity="INFO"
            )
            return routes._success_response(
                {"api_key": api_key, "key_id": key_id, "scope": scope},
                status=201
            )
        except ValueError as exc:
            return routes._error_response(str(exc), status=500, code="admin_error")

    @app.route("/admin/api-keys/<key_id>", methods=["DELETE"])
    def delete_api_key(key_id: str) -> Tuple[Dict[str, Any], int]:
        """Revoke an API key (admin only)."""
        auth_error = routes._require_admin_auth()
        if auth_error:
            return auth_error

        try:
            if api_auth.revoke_key(key_id):
                routes._log_event("api_key_revoked", {"key_id": key_id}, severity="WARNING")
                return routes._success_response({"revoked": True})
        except ValueError as exc:
            return routes._error_response(str(exc), status=500, code="admin_error")

        return routes._error_response("API key not found", status=404, code="not_found")

    @app.route("/admin/api-key-events", methods=["GET"])
    def list_api_key_events() -> Tuple[Dict[str, Any], int]:
        """List API key events with pagination (admin only)."""
        auth_error = routes._require_admin_auth()
        if auth_error:
            return auth_error

        limit = request.args.get("limit", default=100, type=int)
        events = api_key_store.get_events(limit=limit)
        return routes._success_response({"events": events})

    @app.route("/admin/withdrawals/telemetry", methods=["GET"])
    def get_withdrawal_telemetry() -> Tuple[Dict[str, Any], int]:
        """Get withdrawal telemetry metrics (admin only)."""
        auth_error = routes._require_admin_auth()
        if auth_error:
            return auth_error

        limiter = get_rate_limiter()
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
        auth_error = routes._require_admin_auth()
        if auth_error:
            return auth_error

        limiter = get_rate_limiter()
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
        auth_error = routes._require_admin_auth()
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
            return routes._success_response(
                {"address": address, "limit": limit},
                status=201
            )
        except Exception as exc:
            return routes._error_response(str(exc), status=500, code="admin_error")
