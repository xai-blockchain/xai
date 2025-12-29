from __future__ import annotations

"""
XAI Blockchain API Extensions

Lightweight coordinator for API extension modules.

This module integrates:
1. Mining control (api_mining.py)
2. Governance & voting (api_governance.py)
3. Wallet & trading (api_wallet.py)
4. AI & Personal AI (api_ai.py)
5. WebSocket real-time updates (api_websocket.py)

These extend the base node API with functionality needed for:
- Browser mining plugins
- Desktop miners
- Node operator dashboards
- Trading interfaces
- AI-assisted operations
"""

import logging
from typing import Any

from xai.core.api.api_ai import AIAPIHandler
from xai.core.api.api_governance import GovernanceAPIHandler
from xai.core.api.api_mining import MiningAPIHandler
from xai.core.api.api_wallet import WalletAPIHandler
from xai.core.api.api_websocket import WebSocketAPIHandler
from xai.core.config import Config
from xai.security.module_attachment_guard import ModuleAttachmentError, ModuleAttachmentGuard

logger = logging.getLogger(__name__)
ATTACHMENT_SAFE = True

_ALLOWED_EXTENSION_MODULES = {
    "xai.core.api.api_mining",
    "xai.core.api.api_governance",
    "xai.core.api.api_wallet",
    "xai.core.api.api_ai",
    "xai.core.api.api_websocket",
}
_extension_guard = ModuleAttachmentGuard(_ALLOWED_EXTENSION_MODULES, require_attribute="ATTACHMENT_SAFE")

# Validate extension modules at import time to fail fast if tampered/shadowed
try:
    _extension_guard.require_all()
except ModuleAttachmentError as exc:  # pragma: no cover - defensive startup guard
    logger.critical(
        "API extension module validation failed: %s",
        exc,
        extra={"event": "api.extensions.validation_failed"}
    )
    raise

class APIExtensions:
    """
    Extended API endpoints coordinator.

    Delegates to specialized handlers for each API category.
    """

    def __init__(self, node: Any):
        """
        Initialize API extensions.

        Args:
            node: BlockchainNode instance
        """
        self.node = node
        self.app = node.app

        # Initialize trade peers for wallet API
        self.trade_peers: dict[str, float] = {}
        for peer in Config.WALLET_TRADE_PEERS:
            self._register_trade_peer(peer)

        # Initialize WebSocket handler first (needed by other handlers)
        api_auth = getattr(getattr(node, "api_routes", None), "api_auth", None)
        self.websocket_handler = WebSocketAPIHandler(node, self.app, api_auth=api_auth)

        # Initialize specialized API handlers
        self.mining_handler = MiningAPIHandler(node, self.app, self.websocket_handler.broadcast_ws)
        self.governance_handler = GovernanceAPIHandler(node, self.app)
        self.wallet_handler = WalletAPIHandler(
            node, self.app, self.websocket_handler.broadcast_ws, self.trade_peers
        )
        self.ai_handler = AIAPIHandler(node, self.app)

        # Start background tasks
        self.websocket_handler.start_background_tasks()

        logger.info("API Extensions initialized with modular handlers")

    def _register_trade_peer(self, host: str) -> None:
        """
        Register a trade peer.

        Args:
            host: Peer hostname
        """
        import time

        normalized = host.rstrip("/")
        if not normalized:
            return
        self.trade_peers[normalized] = time.time()
        logger.info(f"Registered wallet-trade peer {normalized}")

    # Expose WebSocket broadcast for backward compatibility
    def broadcast_ws(self, message: dict[str, Any]) -> None:
        """
        Broadcast message to WebSocket clients.

        Args:
            message: Message to broadcast
        """
        self.websocket_handler.broadcast_ws(message)

    # Expose mining stats for backward compatibility
    @property
    def mining_threads(self) -> dict[str, dict[str, Any]]:
        """Get mining threads dictionary."""
        return self.mining_handler.mining_threads

    @property
    def mining_stats(self) -> dict[str, dict[str, Any]]:
        """Get mining stats dictionary."""
        return self.mining_handler.mining_stats

# Integration with existing node
def extend_node_api(node: Any) -> APIExtensions:
    """
    Extend existing BlockchainNode with new API endpoints.

    Args:
        node: BlockchainNode instance

    Returns:
        APIExtensions instance
    """
    extensions = APIExtensions(node)
    logger.info("✅ API Extensions loaded:")
    logger.info("   - Mining control (/mining/start, /mining/stop, /mining/status)")
    logger.info("   - Governance API (/governance/*)")
    logger.info("   - Wallet API (/wallet/*, /wallet-trades/*)")
    logger.info("   - AI API (/personal-ai/*, /questioning/*)")
    logger.info("   - WebSocket API (/ws)")
    return extensions

# Usage in node.py:
# from xai.core.api.api_extensions import extend_node_api
# extensions = extend_node_api(node)
