from __future__ import annotations

"""
XAI API Blueprints

Flask Blueprints for organizing the node API into logical domain modules.
Extracted from the monolithic node_api.py as part of god class refactoring.

Usage:
    from xai.core.api_blueprints import register_blueprints
    register_blueprints(app, node, blockchain, peer_manager, api_auth, ...)
"""

import logging
from typing import TYPE_CHECKING, Any

from flask import Flask, g, redirect, request

from xai.core.api_blueprints.admin_bp import admin_bp
from xai.core.api_blueprints.blockchain_bp import blockchain_bp
from xai.core.api_blueprints.core_bp import core_bp
from xai.core.api_blueprints.exchange_bp import exchange_bp
from xai.core.api_blueprints.mining_bp import mining_bp
from xai.core.api_blueprints.payment_bp import payment_bp
from xai.core.api_blueprints.wallet_bp import wallet_bp

if TYPE_CHECKING:
    from xai.core.api_auth import APIAuthManager, APIKeyStore
    from xai.core.error_handlers import ErrorHandlerRegistry
    from xai.network.peer_manager import PeerManager
    from xai.wallet.spending_limits import SpendingLimitManager

__all__ = [
    "core_bp",
    "blockchain_bp",
    "wallet_bp",
    "mining_bp",
    "exchange_bp",
    "admin_bp",
    "payment_bp",
    "register_blueprints",
    "register_legacy_redirects",
    "ALL_BLUEPRINTS",
]

logger = logging.getLogger(__name__)

ALL_BLUEPRINTS = [
    core_bp,
    blockchain_bp,
    wallet_bp,
    mining_bp,
    # exchange_bp has url_prefix="/exchange", register separately
    # admin_bp has url_prefix="/admin", register separately
]

def register_blueprints(
    app: Flask,
    node: Any,
    blockchain: Any,
    peer_manager: "PeerManager" | None = None,
    api_auth: "APIAuthManager" | None = None,
    api_key_store: "APIKeyStore" | None = None,
    error_registry: "ErrorHandlerRegistry" | None = None,
    spending_limits: "SpendingLimitManager" | None = None,
) -> None:
    """
    Register all API blueprints with the Flask app.

    This function sets up:
    1. A before_request handler to inject context into Flask's g object
    2. All domain-specific blueprints

    Args:
        app: Flask application instance
        node: BlockchainNode instance
        blockchain: Blockchain instance
        peer_manager: PeerManager for P2P networking
        api_auth: APIAuthManager for authentication
        api_key_store: APIKeyStore for key management
        error_registry: ErrorHandlerRegistry for error handling
        spending_limits: SpendingLimitManager for transaction limits
    """
    # Store context that blueprints need
    api_context = {
        "node": node,
        "blockchain": blockchain,
        "peer_manager": peer_manager,
        "api_auth": api_auth,
        "api_key_store": api_key_store,
        "error_registry": error_registry,
        "spending_limits": spending_limits,
    }

    @app.before_request
    def inject_api_context() -> None:
        """Inject API context into Flask's g object for blueprint access."""
        g.api_context = api_context

    # Register blueprints without url_prefix (they define their own)
    for bp in ALL_BLUEPRINTS:
        app.register_blueprint(bp)

    # Register blueprints with url_prefix
    app.register_blueprint(exchange_bp)  # has url_prefix="/exchange"
    app.register_blueprint(admin_bp)  # has url_prefix="/admin"
    app.register_blueprint(payment_bp)  # has url_prefix="/payment"


def register_legacy_redirects(app: Flask) -> None:
    """
    Register HTTP 301 redirects from old unversioned routes to new /api/v1/ routes.

    This maintains backward compatibility while encouraging migration to versioned API.
    Redirects include deprecation warnings in response headers.

    Args:
        app: Flask application instance
    """
    # Define legacy routes that should redirect to /api/v1/
    legacy_patterns = [
        "/blocks",
        "/blocks/<path:subpath>",
        "/block/<path:subpath>",
        "/transactions",
        "/transaction/<path:subpath>",
        "/wallet/<path:subpath>",
        "/balance/<path:subpath>",
        "/send",
        "/mine",
        "/peers",
        "/stats",
        "/health",
        "/mempool",
        "/mempool/<path:subpath>",
        "/exchange/<path:subpath>",
        "/admin/<path:subpath>",
    ]

    def create_redirect_handler(pattern: str):
        """Factory to create redirect handlers for each pattern."""
        def redirect_handler(**kwargs):
            # Build new URL with /api/v1/ prefix
            old_path = request.path
            new_path = f"/api/v1{old_path}"

            # Preserve query string
            if request.query_string:
                new_path = f"{new_path}?{request.query_string.decode('utf-8')}"

            # Log deprecation warning
            logger.warning(
                "Deprecated API endpoint accessed (will be removed in future version)",
                extra={
                    "event": "api.deprecated_endpoint",
                    "old_path": old_path,
                    "new_path": new_path,
                    "remote_addr": request.remote_addr,
                }
            )

            # Create redirect response with deprecation headers
            response = redirect(new_path, code=301)
            response.headers["Deprecation"] = "true"
            response.headers["X-API-Deprecated"] = "Use /api/v1/ prefix for all API calls"
            response.headers["Link"] = '</api/v1>; rel="successor-version"'
            return response

        # Set a unique name for each redirect handler
        redirect_handler.__name__ = f"legacy_redirect_{pattern.replace('/', '_').replace('<', '').replace('>', '')}"
        return redirect_handler

    # Register redirect routes
    for pattern in legacy_patterns:
        handler = create_redirect_handler(pattern)
        # Use the same methods as the original endpoint would accept
        app.add_url_rule(pattern, view_func=handler, methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
