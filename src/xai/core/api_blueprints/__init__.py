"""
XAI API Blueprints

Flask Blueprints for organizing the node API into logical domain modules.
Extracted from the monolithic node_api.py as part of god class refactoring.

Usage:
    from xai.core.api_blueprints import register_blueprints
    register_blueprints(app, node, blockchain, peer_manager, api_auth, ...)
"""

from typing import TYPE_CHECKING, Any, Optional

from flask import Flask, g

from xai.core.api_blueprints.core_bp import core_bp
from xai.core.api_blueprints.blockchain_bp import blockchain_bp
from xai.core.api_blueprints.wallet_bp import wallet_bp
from xai.core.api_blueprints.mining_bp import mining_bp
from xai.core.api_blueprints.exchange_bp import exchange_bp
from xai.core.api_blueprints.admin_bp import admin_bp

if TYPE_CHECKING:
    from xai.network.peer_manager import PeerManager
    from xai.core.api_auth import APIAuthManager, APIKeyStore
    from xai.core.error_handlers import ErrorHandlerRegistry
    from xai.wallet.spending_limits import SpendingLimitManager

__all__ = [
    "core_bp",
    "blockchain_bp",
    "wallet_bp",
    "mining_bp",
    "exchange_bp",
    "admin_bp",
    "register_blueprints",
    "ALL_BLUEPRINTS",
]

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
    peer_manager: Optional["PeerManager"] = None,
    api_auth: Optional["APIAuthManager"] = None,
    api_key_store: Optional["APIKeyStore"] = None,
    error_registry: Optional["ErrorHandlerRegistry"] = None,
    spending_limits: Optional["SpendingLimitManager"] = None,
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
    def inject_api_context():
        """Inject API context into Flask's g object for blueprint access."""
        g.api_context = api_context

    # Register blueprints without url_prefix
    for bp in ALL_BLUEPRINTS:
        app.register_blueprint(bp)

    # Register blueprints with url_prefix
    app.register_blueprint(exchange_bp)  # has url_prefix="/exchange"
    app.register_blueprint(admin_bp)  # has url_prefix="/admin"
