"""Admin monitoring and operational control routes.

This module provides REST API endpoints for monitoring and controlling
node operations including mining status, peer management, and configuration.

Endpoints:
- GET /admin/mining/status - Get mining status
- POST /admin/mining/enable - Enable mining
- POST /admin/mining/disable - Disable mining
- GET /admin/peers - Get detailed peer snapshot
- POST /admin/peers/disconnect - Disconnect a peer
- POST /admin/peers/ban - Ban a peer/IP
- POST /admin/peers/unban - Remove peer/IP from ban list
- POST /admin/config/reload - Reload runtime configuration
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from flask import request

from xai.core.config import Config, ConfigurationError, reload_runtime
from xai.network.peer_manager import PeerManager

if TYPE_CHECKING:
    from xai.core.node_api import NodeAPIRoutes

logger = logging.getLogger(__name__)


def register_admin_monitoring_routes(routes: "NodeAPIRoutes") -> None:
    """Register admin monitoring and operational control endpoints.

    All routes require admin/operator authentication via _require_control_role().
    """
    app = routes.app
    node = routes.node

    def _require_peer_manager() -> PeerManager | None:
        manager = getattr(node, "peer_manager", None)
        required = ("disconnect_peer", "ban_peer", "unban_peer")
        if manager and all(hasattr(manager, attr) for attr in required):
            return manager
        return None

    @app.route("/admin/mining/status", methods=["GET"])
    def admin_mining_status() -> tuple[dict[str, Any], int]:
        """Return node mining status and pause context (admin/operator/auditor)."""
        auth_error = routes._require_control_role({"admin", "operator", "auditor"})
        if auth_error:
            return auth_error

        pause_manager = getattr(routes, "emergency_pause_manager", None)
        pause_status: dict[str, Any] = {}
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
    def admin_enable_mining() -> tuple[dict[str, Any], int]:
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
    def admin_disable_mining() -> tuple[dict[str, Any], int]:
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

    @app.route("/admin/peers", methods=["GET"])
    def admin_peer_status() -> tuple[dict[str, Any], int]:
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
    def admin_peer_disconnect() -> tuple[dict[str, Any], int]:
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
    def admin_peer_ban() -> tuple[dict[str, Any], int]:
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
    def admin_peer_unban() -> tuple[dict[str, Any], int]:
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
    def admin_config_reload() -> tuple[dict[str, Any], int]:
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
