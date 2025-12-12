from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Callable, Optional, Tuple, Dict, Any

from flask import jsonify, request

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from xai.core.node_api import NodeAPIRoutes


def register_mining_routes(
    routes: "NodeAPIRoutes",
    *,
    advanced_rate_limiter_getter: Optional[Callable[[], Any]] = None,
) -> None:
    """Expose mining control endpoints."""
    app = routes.app
    blockchain = routes.blockchain
    node = routes.node

    def _get_mining_limiter():
        if not callable(advanced_rate_limiter_getter):
            raise RuntimeError("advanced rate limiter unavailable")
        limiter = advanced_rate_limiter_getter()
        if limiter is None:
            raise RuntimeError("advanced rate limiter unavailable")
        return limiter

    @app.route("/mine", methods=["POST"])
    def mine_block() -> Tuple[Dict[str, Any], int]:
        """Mine a single block with pending transactions.

        Mines one block containing pending transactions and broadcasts it to the
        network. Includes rate limiting to prevent mining abuse.

        This endpoint requires API authentication.

        Returns:
            Tuple containing (response_dict, http_status_code) where:
                - response_dict: Contains mined block data, success flag, and reward
                - http_status_code: 200 on success, 400/429/503 on error

        Raises:
            AuthenticationError: If API key is missing or invalid (401).
            RateLimitError: If mining rate limit exceeded (429).
            ValueError: If no pending transactions to mine (400).
            RuntimeError: If rate limiter is unavailable (503).
        """
        auth_error = routes._require_api_auth()
        if auth_error:
            return auth_error

        try:
            limiter = _get_mining_limiter()
            allowed, error = limiter.check_rate_limit("/mine")
            if not allowed:
                return routes._error_response(
                    error or "Rate limit exceeded",
                    status=429,
                    code="rate_limited",
                )
        except (ImportError, AttributeError, RuntimeError) as exc:
            logger.error(
                "Rate limiter unavailable for /mine: %s",
                type(exc).__name__,
                extra={
                    "event": "api.rate_limiter_error",
                    "endpoint": "/mine",
                    "client": request.remote_addr or "unknown",
                },
                exc_info=True,
            )
            return routes._error_response(
                "Rate limiting unavailable. Please retry later.",
                status=503,
                code="rate_limiter_unavailable",
            )

        if not blockchain.pending_transactions:
            return jsonify({"error": "No pending transactions to mine"}), 400

        try:
            block = blockchain.mine_pending_transactions(node.miner_address)
            node.broadcast_block(block)
            return (
                jsonify(
                    {
                        "success": True,
                        "block": block.to_dict(),
                        "message": f"Block {block.index} mined successfully",
                        "reward": blockchain.block_reward,
                    }
                ),
                200,
            )
        except (ValueError, RuntimeError) as exc:
            return routes._handle_exception(exc, "mine_block")

    @app.route("/auto-mine/start", methods=["POST"])
    def start_auto_mining() -> Dict[str, str]:
        """Start automatic continuous mining.

        Enables auto-mining mode where the node continuously mines blocks
        whenever pending transactions are available.

        This endpoint requires API authentication.

        Returns:
            Dict containing status message indicating mining started or already active.

        Raises:
            AuthenticationError: If API key is missing or invalid (401).
        """
        auth_error = routes._require_api_auth()
        if auth_error:
            return auth_error
        if node.is_mining:
            return jsonify({"message": "Mining already active"})

        node.start_mining()
        return jsonify({"message": "Auto-mining started"})

    @app.route("/auto-mine/stop", methods=["POST"])
    def stop_auto_mining() -> Dict[str, str]:
        """Stop automatic continuous mining.

        Disables auto-mining mode, halting continuous block mining.
        Does not affect manual mining via /mine endpoint.

        This endpoint requires API authentication.

        Returns:
            Dict containing status message indicating mining stopped or wasn't active.

        Raises:
            AuthenticationError: If API key is missing or invalid (401).
        """
        auth_error = routes._require_api_auth()
        if auth_error:
            return auth_error
        if not node.is_mining:
            return jsonify({"message": "Mining not active"})

        node.stop_mining()
        return jsonify({"message": "Auto-mining stopped"})
