"""
Base utilities for API Blueprints

Provides common dependencies and helper functions shared across blueprints.
"""

from __future__ import annotations

import logging
import time
from contextlib import nullcontext
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from flask import g, jsonify, request

from xai.core.security_validation import SecurityValidator, log_security_event

if TYPE_CHECKING:
    from xai.network.peer_manager import PeerManager

logger = logging.getLogger(__name__)


def get_api_context() -> Dict[str, Any]:
    """Get the API context containing node, blockchain, and other dependencies.

    The context is stored in Flask's g object during request setup.
    """
    return g.get("api_context", {})


def get_node() -> Any:
    """Get the blockchain node instance from context."""
    ctx = get_api_context()
    return ctx.get("node")


def get_blockchain() -> Any:
    """Get the blockchain instance from context."""
    ctx = get_api_context()
    return ctx.get("blockchain")


def get_peer_manager() -> Optional[Any]:
    """Get the peer manager instance from context."""
    ctx = get_api_context()
    return ctx.get("peer_manager")


def get_api_auth() -> Optional[Any]:
    """Get the API auth manager from context."""
    ctx = get_api_context()
    return ctx.get("api_auth")


def get_error_registry() -> Optional[Any]:
    """Get the error handler registry from context."""
    ctx = get_api_context()
    return ctx.get("error_registry")


def get_spending_limits() -> Optional[Any]:
    """Get the spending limits manager from context."""
    ctx = get_api_context()
    return ctx.get("spending_limits")


def log_event(
    event_type: str,
    payload: Optional[Dict[str, Any]] = None,
    severity: str = "INFO"
) -> None:
    """Log API security events with sanitized payloads."""
    sanitized = SecurityValidator.sanitize_for_logging(payload or {})
    log_security_event(event_type, {"details": sanitized}, severity=severity)


def success_response(payload: Dict[str, Any], status: int = 200) -> Tuple[Any, int]:
    """Return a success payload with consistent structure."""
    body = {"success": True, **payload}
    return jsonify(body), status


def error_response(
    message: str,
    status: int = 400,
    code: str = "bad_request",
    context: Optional[Dict[str, Any]] = None,
    event_type: str = "node_api_error",
) -> Tuple[Any, int]:
    """Return a sanitized error response and emit a security log."""
    severity = "ERROR" if status >= 500 else "WARNING"
    details = {"code": code, "status": status, **(context or {})}
    log_event(event_type, details, severity=severity)
    return jsonify({"success": False, "error": message, "code": code}), status


def handle_exception(error: Exception, context_str: str, status: int = 500) -> Tuple[Any, int]:
    """Route unexpected exceptions with sanitized output."""
    error_registry = get_error_registry()
    blockchain = get_blockchain()

    if error_registry:
        handled, handler_message = error_registry.handle_error(error, context_str, blockchain)
    else:
        handled, handler_message = False, str(error)

    details = {"context": context_str, "error": str(error), "handled": handled}
    return error_response(
        handler_message if status < 500 and handler_message else "Internal server error",
        status=status,
        code="internal_error",
        context=details,
        event_type="node_api_exception",
    )


def format_timestamp(timestamp: Optional[float]) -> Optional[str]:
    """Return RFC3339-ish string for telemetry fields."""
    if timestamp is None:
        return None
    try:
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(float(timestamp)))
    except (ValueError, TypeError, OverflowError):
        return None


def require_api_auth() -> Optional[Tuple[Any, int]]:
    """Check if API authentication is required and valid.

    Returns None if auth passes, or an error response tuple if it fails.
    """
    api_auth = get_api_auth()
    if not api_auth or not api_auth.is_enabled():
        return None
    allowed, reason = api_auth.authorize(request)
    if allowed:
        return None
    return error_response(
        "API key required",
        status=401,
        code="unauthorized",
        context={"reason": reason or ""},
        event_type="api_auth_failure",
    )


def require_admin_auth() -> Optional[Tuple[Any, int]]:
    """Check if admin authentication is required and valid.

    Returns None if auth passes, or an error response tuple if it fails.
    """
    api_auth = get_api_auth()
    if not api_auth:
        return error_response(
            "API authentication not configured",
            status=500,
            code="config_error",
        )
    allowed, reason = api_auth.authorize_admin(request)
    if allowed:
        return None
    return error_response(
        reason or "Admin token invalid",
        status=401,
        code="admin_unauthorized",
        event_type="api_admin_auth_failure",
    )


class PaginationError(ValueError):
    """Raised when pagination parameters are invalid."""
    pass


def get_pagination_params(
    default_limit: int = 50,
    max_limit: int = 500,
    default_offset: int = 0,
) -> Tuple[int, int]:
    """Normalize pagination query params and enforce sane limits."""
    limit = request.args.get("limit", default=default_limit, type=int)
    offset = request.args.get("offset", default=default_offset, type=int)
    if limit is None or offset is None:
        raise PaginationError("limit and offset must be integers")
    if limit <= 0:
        raise PaginationError("limit must be greater than zero")
    if limit > max_limit:
        raise PaginationError(f"limit cannot exceed {max_limit}")
    if offset < 0:
        raise PaginationError("offset cannot be negative")
    return limit, offset


def build_peer_diversity_stats(manager: "PeerManager") -> Dict[str, Any]:
    """Snapshot peer diversity counters under lock for consistent reporting."""
    diversity_lock = getattr(manager, "_diversity_lock", None)
    context = diversity_lock if hasattr(diversity_lock, "__enter__") else nullcontext()
    with context:
        prefix_counts = dict(getattr(manager, "prefix_counts", {}))
        asn_counts = dict(getattr(manager, "asn_counts", {}))
        country_counts = dict(getattr(manager, "country_counts", {}))
        unknown_geo = int(getattr(manager, "unknown_geo_peers", 0))

    return {
        "prefix_counts": prefix_counts,
        "asn_counts": asn_counts,
        "country_counts": country_counts,
        "unknown_geo_peers": unknown_geo,
        "unique_prefixes": len(prefix_counts),
        "unique_asns": len(asn_counts),
        "unique_countries": len(country_counts),
        "thresholds": {
            "min_unique_prefixes": getattr(manager, "min_unique_prefixes", None),
            "min_unique_asns": getattr(manager, "min_unique_asns", None),
            "min_unique_countries": getattr(manager, "min_unique_countries", None),
            "max_unknown_geo": getattr(manager, "max_unknown_geo", None),
        },
    }


def build_peer_snapshot() -> Dict[str, Any]:
    """Assemble detailed peer metadata for verbose peer queries."""
    from xai.network.peer_manager import PeerManager

    manager = get_peer_manager()
    if not isinstance(manager, PeerManager):
        return {"connections": [], "diversity": {}, "limits": {}, "connected_total": 0}

    now = time.time()
    connected = getattr(manager, "connected_peers", {}) or {}
    seen_nonces = getattr(manager, "seen_nonces", {}) or {}
    trusted_set = {peer.lower() for peer in getattr(manager, "trusted_peers", set())}
    banned_set = {peer.lower() for peer in getattr(manager, "banned_peers", set())}

    connections: List[Dict[str, Any]] = []
    for peer_id, info in list(connected.items()):
        connected_at = float(info.get("connected_at", now) or now)
        last_seen = info.get("last_seen")
        ip_address = (info.get("ip_address") or "").lower()
        geo = info.get("geo") or {}
        nonce_window = seen_nonces.get(peer_id, [])
        reputation = None
        if getattr(manager, "reputation", None):
            reputation = round(manager.reputation.get_score(peer_id), 4)

        connections.append(
            {
                "peer_id": peer_id,
                "ip_address": info.get("ip_address"),
                "connected_at": connected_at,
                "connected_at_iso": format_timestamp(connected_at),
                "uptime_seconds": max(0.0, now - connected_at),
                "last_seen": last_seen,
                "last_seen_iso": format_timestamp(last_seen) if last_seen else None,
                "geo": geo,
                "reputation": reputation,
                "nonce_window": len(nonce_window),
                "trusted": ip_address in trusted_set,
                "banned": ip_address in banned_set,
            }
        )

    connections.sort(key=lambda entry: entry.get("connected_at") or 0.0, reverse=True)
    diversity = build_peer_diversity_stats(manager)
    limits = {
        "max_connections_per_ip": getattr(manager, "max_connections_per_ip", None),
        "max_per_prefix": getattr(manager, "max_per_prefix", None),
        "max_per_asn": getattr(manager, "max_per_asn", None),
        "max_per_country": getattr(manager, "max_per_country", None),
        "max_unknown_geo": getattr(manager, "max_unknown_geo", None),
        "require_client_cert": getattr(manager, "require_client_cert", False),
    }
    discovery = getattr(getattr(manager, "discovery", None), "discovered_peers", [])

    return {
        "connections": connections,
        "connected_total": len(connections),
        "diversity": diversity,
        "limits": limits,
        "trusted_peers": sorted(trusted_set),
        "banned_peers": sorted(banned_set),
        "discovered": discovery[:50] if isinstance(discovery, list) else [],
    }
