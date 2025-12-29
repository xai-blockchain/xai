"""Admin emergency controls and circuit breaker routes.

This module provides REST API endpoints for emergency operations including
pausing/unpausing node operations and circuit breaker management.

Endpoints:
- GET /admin/emergency/status - Get emergency pause and circuit breaker status
- POST /admin/emergency/pause - Manually pause node operations
- POST /admin/emergency/unpause - Manually unpause node operations
- POST /admin/emergency/circuit-breaker/trip - Force-open circuit breaker
- POST /admin/emergency/circuit-breaker/reset - Reset circuit breaker
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from flask import request

from xai.core.security.api_rate_limiting import rate_limit_admin
from xai.core.config import Config

if TYPE_CHECKING:
    from xai.core.node_api import NodeAPIRoutes

logger = logging.getLogger(__name__)


def register_admin_emergency_routes(routes: "NodeAPIRoutes") -> None:
    """Register admin emergency control endpoints.

    All routes require admin/operator authentication via _require_control_role().
    """
    app = routes.app

    @app.route("/admin/emergency/status", methods=["GET"])
    @rate_limit_admin  # Very strict limits for admin operations
    def get_emergency_status() -> tuple[dict[str, Any], int]:
        """Return emergency pause and circuit breaker status (admin only)."""
        auth_error = routes._require_control_role({"admin", "operator", "auditor"})
        if auth_error:
            return auth_error

        limiter = routes._get_admin_rate_limiter()
        identifier = f"admin-emergency-status:{request.remote_addr or 'unknown'}"
        allowed, error = limiter.check_rate_limit(identifier, "/admin/emergency/status")
        if not allowed:
            return routes._error_response(
                error or "Rate limit exceeded",
                status=429,
                code="rate_limited",
                context={"identifier": identifier},
            )

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
    @rate_limit_admin  # Very strict limits for admin operations
    def pause_operations() -> tuple[dict[str, Any], int]:
        """Manually pause node operations (admin only)."""
        auth_error = routes._require_control_role({"admin", "operator"})
        if auth_error:
            return auth_error

        limiter = routes._get_admin_rate_limiter()
        identifier = f"admin-emergency-pause:{request.remote_addr or 'unknown'}"
        allowed, error = limiter.check_rate_limit(identifier, "/admin/emergency/pause")
        if not allowed:
            return routes._error_response(
                error or "Rate limit exceeded",
                status=429,
                code="rate_limited",
                context={"identifier": identifier},
            )

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
    @rate_limit_admin  # Very strict limits for admin operations
    def unpause_operations() -> tuple[dict[str, Any], int]:
        """Manually unpause node operations (admin only)."""
        auth_error = routes._require_control_role({"admin", "operator"})
        if auth_error:
            return auth_error

        limiter = routes._get_admin_rate_limiter()
        identifier = f"admin-emergency-unpause:{request.remote_addr or 'unknown'}"
        allowed, error = limiter.check_rate_limit(identifier, "/admin/emergency/unpause")
        if not allowed:
            return routes._error_response(
                error or "Rate limit exceeded",
                status=429,
                code="rate_limited",
                context={"identifier": identifier},
            )

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
    @rate_limit_admin  # Very strict limits for admin operations
    def trip_circuit_breaker() -> tuple[dict[str, Any], int]:
        """Force-open the global circuit breaker and auto-pause operations."""
        auth_error = routes._require_control_role({"admin"})
        if auth_error:
            return auth_error

        limiter = routes._get_admin_rate_limiter()
        identifier = f"admin-circuit-breaker-trip:{request.remote_addr or 'unknown'}"
        allowed, error = limiter.check_rate_limit(identifier, "/admin/emergency/circuit-breaker/trip")
        if not allowed:
            return routes._error_response(
                error or "Rate limit exceeded",
                status=429,
                code="rate_limited",
                context={"identifier": identifier},
            )

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
    @rate_limit_admin  # Very strict limits for admin operations
    def reset_circuit_breaker() -> tuple[dict[str, Any], int]:
        """Reset the global circuit breaker and clear automated pauses (admin only)."""
        auth_error = routes._require_control_role({"admin"})
        if auth_error:
            return auth_error

        limiter = routes._get_admin_rate_limiter()
        identifier = f"admin-circuit-breaker-reset:{request.remote_addr or 'unknown'}"
        allowed, error = limiter.check_rate_limit(identifier, "/admin/emergency/circuit-breaker/reset")
        if not allowed:
            return routes._error_response(
                error or "Rate limit exceeded",
                status=429,
                code="rate_limited",
                context={"identifier": identifier},
            )

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
