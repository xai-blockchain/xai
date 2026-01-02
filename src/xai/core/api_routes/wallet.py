from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

from typing import TYPE_CHECKING, Any

from flask import jsonify

if TYPE_CHECKING:
    from xai.core.node_api import NodeAPIRoutes

def register_wallet_routes(routes: "NodeAPIRoutes") -> None:
    app = routes.app
    blockchain = routes.blockchain

    @app.route("/balance/<address>", methods=["GET"])
    def get_balance(address: str) -> dict[str, Any]:
        """Get balance for a blockchain address.

        Retrieves the current balance for the specified address by summing
        all transaction outputs minus inputs.

        Path Parameters:
            address (str): The blockchain address to query

        Returns:
            dict containing:
                - address (str): The queried address
                - balance (float): Current balance in XAI tokens
        """
        balance = blockchain.get_balance(address)
        return jsonify({"address": address, "balance": balance})

    @app.route("/address/<address>/nonce", methods=["GET"])
    def get_address_nonce(address: str) -> tuple[dict[str, Any], int]:
        """Get nonce information for an address.

        Returns confirmed nonce, next available nonce, and pending nonce for
        the specified address. Used for transaction ordering and replay protection.

        Path Parameters:
            address (str): The blockchain address to query

        Returns:
            Tuple containing (response_dict, http_status_code) where:
                - response_dict: Contains confirmed_nonce, next_nonce, pending_nonce
                - http_status_code: 200 on success, 503 if nonce tracker unavailable

        Raises:
            ServiceUnavailable: If nonce tracker is not available (503).
            ValueError: If nonce lookup fails (500).
            RuntimeError: If nonce tracker operation fails (500).
        """
        tracker = getattr(blockchain, "nonce_tracker", None)
        if tracker is None:
            return routes._error_response(
                "Nonce tracker unavailable",
                status=503,
                code="nonce_tracker_unavailable",
            )

        try:
            confirmed = tracker.get_nonce(address)
            next_nonce = tracker.get_next_nonce(address)
        except (ValueError, RuntimeError, KeyError, AttributeError) as exc:
            logger.error(
                "Nonce lookup failed",
                extra={
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "address": address,
                    "function": "nonce_lookup"
                },
                exc_info=True
            )
            return routes._handle_exception(exc, "nonce_lookup")

        pending_nonce = next_nonce - 1 if next_nonce - 1 > confirmed else None
        return (
            jsonify(
                {
                    "address": address,
                    "confirmed_nonce": max(confirmed, -1),
                    "next_nonce": next_nonce,
                    "pending_nonce": pending_nonce,
                }
            ),
            200,
        )

    @app.route("/history/<address>", methods=["GET"])
    def get_history(address: str) -> dict[str, Any]:
        """Get transaction history for an address.

        Returns paginated transaction history for the specified address,
        including all transactions where the address is sender or recipient.

        Path Parameters:
            address (str): The blockchain address to query

        Query Parameters:
            limit (int, optional): Maximum transactions to return (default: 50, max: 500)
            offset (int, optional): Number of transactions to skip (default: 0)

        Returns:
            dict containing:
                - address (str): The queried address
                - transaction_count (int): Total number of transactions for this address
                - limit (int): Applied limit
                - offset (int): Applied offset
                - transactions (list): List of transaction objects

        Raises:
            ValueError: If pagination parameters are invalid (400).
        """
        try:
            limit, offset = routes._get_pagination_params(default_limit=50, max_limit=500)
        except (ValueError, RuntimeError) as exc:
            return routes._error_response(
                str(exc),
                status=400,
                code="invalid_pagination",
                event_type="api.invalid_paging",
            )

        try:
            window, total = blockchain.get_transaction_history_window(address, limit, offset)
        except ValueError as exc:
            logger.warning(
                "ValueError in get_history",
                extra={
                    "error_type": "ValueError",
                    "error": str(exc),
                    "function": "get_history"
                }
            )
            return routes._error_response(
                str(exc),
                status=400,
                code="invalid_pagination",
                event_type="api.invalid_paging",
            )

        return jsonify(
            {
                "address": address,
                "transaction_count": total,
                "limit": limit,
                "offset": offset,
                "transactions": window,
            }
        )
