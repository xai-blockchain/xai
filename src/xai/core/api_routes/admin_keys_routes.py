"""Admin API key management routes.

This module provides REST API endpoints for managing API keys,
including listing, creating, and revoking keys, as well as
viewing API key events.

Endpoints:
- GET /admin/api-keys - List all API key metadata
- POST /admin/api-keys - Create new API key
- DELETE /admin/api-keys/<key_id> - Revoke an API key
- GET /admin/api-key-events - List API key events with pagination
- POST /admin/spend-limit - Set per-address daily spending limit
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from flask import request

from xai.core.config import Config

if TYPE_CHECKING:
    from xai.core.node_api import NodeAPIRoutes

logger = logging.getLogger(__name__)


def register_admin_keys_routes(routes: "NodeAPIRoutes") -> None:
    """Register admin API key management endpoints.

    All routes require admin authentication via _require_control_role().
    """
    app = routes.app
    api_auth = routes.api_auth
    api_key_store = routes.api_key_store
    spending_limits = routes.spending_limits

    @app.route("/admin/api-keys", methods=["GET"])
    def list_api_keys() -> tuple[dict[str, Any], int]:
        """List all API key metadata (admin only)."""
        auth_error = routes._require_control_role({"admin"})
        if auth_error:
            return auth_error

        metadata = api_auth.list_key_metadata()
        return routes._success_response(metadata)

    max_ttl_days = getattr(Config, "API_KEY_MAX_TTL_DAYS", 365)
    allow_permanent_keys = getattr(Config, "API_KEY_ALLOW_PERMANENT", False)

    def _normalize_ttl(payload: dict[str, Any]) -> tuple[int | None, tuple[dict[str, Any], int] | None]:
        """Convert expires_in_days/hours payload fields into seconds."""
        ttl_seconds: int | None = None
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
    def create_api_key() -> tuple[dict[str, Any], int]:
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
            metadata: dict[str, Any] = {}
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
    def delete_api_key(key_id: str) -> tuple[dict[str, Any], int]:
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
    def list_api_key_events() -> tuple[dict[str, Any], int]:
        """List API key events with pagination (admin only)."""
        auth_error = routes._require_control_role({"admin", "auditor"})
        if auth_error:
            return auth_error

        limit = request.args.get("limit", default=100, type=int)
        events = api_key_store.get_events(limit=limit)
        return routes._success_response({"events": events})

    @app.route("/admin/spend-limit", methods=["POST"])
    def set_spend_limit() -> tuple[dict[str, Any], int]:
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

    @app.route("/admin/withdrawals/telemetry", methods=["GET"])
    def get_withdrawal_telemetry() -> tuple[dict[str, Any], int]:
        """Get withdrawal telemetry metrics (admin only)."""
        auth_error = routes._require_control_role({"admin", "operator"})
        if auth_error:
            return auth_error

        from xai.core.monitoring import MetricsCollector

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

        node = routes.node
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
    def get_withdrawal_status_snapshot() -> tuple[dict[str, Any], int]:
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

        node = routes.node
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
