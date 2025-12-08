"""
Admin API Blueprint

Handles admin-only endpoints: API key management, withdrawal telemetry, spend limits.
Extracted from node_api.py as part of god class refactoring.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Tuple

from flask import Blueprint, jsonify, request

from xai.core.api_blueprints.base import (
    error_response,
    get_api_context,
    get_node,
    log_event,
    require_admin_auth,
    success_response,
)
from xai.core.monitoring import MetricsCollector
from xai.core.rate_limiter import get_rate_limiter

logger = logging.getLogger(__name__)

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/api-keys", methods=["GET"])
def list_api_keys() -> Tuple[Dict[str, Any], int]:
    """List all API keys (admin only)."""
    ctx = get_api_context()
    api_auth = ctx.get("api_auth")

    auth_error = require_admin_auth()
    if auth_error:
        return auth_error

    metadata = api_auth.list_key_metadata()
    return success_response(metadata)


@admin_bp.route("/api-keys", methods=["POST"])
def create_api_key() -> Tuple[Dict[str, Any], int]:
    """Create a new API key (admin only)."""
    ctx = get_api_context()
    api_auth = ctx.get("api_auth")

    auth_error = require_admin_auth()
    if auth_error:
        return auth_error

    payload = request.get_json(silent=True) or {}
    label = str(payload.get("label", "")).strip()
    scope = str(payload.get("scope", "user")).strip().lower() or "user"
    if scope not in {"user", "admin"}:
        return error_response("Invalid scope", status=400, code="invalid_payload")

    try:
        api_key, key_id = api_auth.issue_key(label=label, scope=scope)
        log_event(
            "api_key_issued", {"key_id": key_id, "label": label, "scope": scope}, severity="INFO"
        )
        return success_response(
            {"api_key": api_key, "key_id": key_id, "scope": scope}, status=201
        )
    except ValueError as exc:
        return error_response(str(exc), status=500, code="admin_error")


@admin_bp.route("/api-keys/<key_id>", methods=["DELETE"])
def delete_api_key(key_id: str) -> Tuple[Dict[str, Any], int]:
    """Delete an API key (admin only)."""
    ctx = get_api_context()
    api_auth = ctx.get("api_auth")

    auth_error = require_admin_auth()
    if auth_error:
        return auth_error

    try:
        if api_auth.revoke_key(key_id):
            log_event("api_key_revoked", {"key_id": key_id}, severity="WARNING")
            return success_response({"revoked": True})
    except ValueError as exc:
        return error_response(str(exc), status=500, code="admin_error")

    return error_response("API key not found", status=404, code="not_found")


@admin_bp.route("/api-key-events", methods=["GET"])
def list_api_key_events() -> Tuple[Dict[str, Any], int]:
    """List API key events (admin only)."""
    ctx = get_api_context()
    api_key_store = ctx.get("api_key_store")

    auth_error = require_admin_auth()
    if auth_error:
        return auth_error

    limit = request.args.get("limit", default=100, type=int)
    events = api_key_store.get_events(limit=limit)
    return success_response({"events": events})


@admin_bp.route("/withdrawals/telemetry", methods=["GET"])
def get_withdrawal_telemetry() -> Tuple[Dict[str, Any], int]:
    """Get withdrawal telemetry data (admin only)."""
    node = get_node()

    auth_error = require_admin_auth()
    if auth_error:
        return auth_error

    limiter = get_rate_limiter()
    identifier = f"admin-telemetry:{request.remote_addr or 'unknown'}"
    allowed, rate_error = limiter.check_rate_limit(identifier, "/admin/withdrawals/telemetry")
    if not allowed:
        return error_response(
            rate_error or "Rate limit exceeded",
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
    log_event(
        "admin_withdrawals_telemetry_access",
        {
            "rate_per_minute": payload["rate_per_minute"],
            "time_locked_backlog": payload["time_locked_backlog"],
            "events_served": len(events),
        },
        severity="INFO",
    )
    return success_response(payload)


@admin_bp.route("/withdrawals/status", methods=["GET"])
def get_withdrawal_status_snapshot() -> Tuple[Dict[str, Any], int]:
    """Get withdrawal status snapshot (admin only)."""
    node = get_node()

    auth_error = require_admin_auth()
    if auth_error:
        return auth_error

    limiter = get_rate_limiter()
    identifier = f"admin-withdrawal-status:{request.remote_addr or 'unknown'}"
    allowed, rate_error = limiter.check_rate_limit(identifier, "/admin/withdrawals/status")
    if not allowed:
        return error_response(
            rate_error or "Rate limit exceeded",
            status=429,
            code="rate_limited",
            context={"identifier": identifier},
        )

    manager = getattr(node, "exchange_wallet_manager", None)
    if not manager:
        return error_response(
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
            return error_response(
                "Invalid status filter",
                status=400,
                code="invalid_status",
                context={"invalid": sorted(invalid)},
            )
        target_statuses = requested or valid_statuses
    else:
        target_statuses = valid_statuses

    withdrawals = {
        status: manager.get_withdrawals_by_status(status, limit) for status in sorted(target_statuses)
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
    log_event(
        "admin_withdrawals_status_access",
        {
            "queue_depth": payload["queue_depth"],
            "statuses": sorted(list(target_statuses)),
            "limit": limit,
        },
        severity="INFO",
    )
    return success_response(payload)


@admin_bp.route("/spend-limit", methods=["POST"])
def set_spend_limit() -> Tuple[Dict[str, Any], int]:
    """Set per-address daily spending limit (admin only)."""
    ctx = get_api_context()
    spending_limits = ctx.get("spending_limits")

    auth_error = require_admin_auth()
    if auth_error:
        return auth_error

    payload = request.get_json(silent=True) or {}
    address = str(payload.get("address", "")).strip()
    try:
        limit_val = float(payload.get("limit"))
    except (TypeError, ValueError):
        return error_response("Invalid limit", status=400, code="invalid_payload")

    if not address or limit_val <= 0:
        return error_response("Invalid address or limit", status=400, code="invalid_payload")

    try:
        spending_limits.set_limit(address, limit_val)
        log_event(
            "spend_limit_set",
            {"address": address, "limit": limit_val},
            severity="INFO",
        )
        return success_response({"address": address, "limit": limit_val})
    except Exception as exc:
        return error_response(str(exc), status=500, code="admin_error")
