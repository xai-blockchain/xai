from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Tuple, Any

from flask import jsonify

if TYPE_CHECKING:
    from xai.core.node_api import NodeAPIRoutes


def register_wallet_routes(routes: "NodeAPIRoutes") -> None:
    app = routes.app
    blockchain = routes.blockchain

    @app.route("/balance/<address>", methods=["GET"])
    def get_balance(address: str) -> Dict[str, Any]:
        balance = blockchain.get_balance(address)
        return jsonify({"address": address, "balance": balance})

    @app.route("/address/<address>/nonce", methods=["GET"])
    def get_address_nonce(address: str) -> Tuple[Dict[str, Any], int]:
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
        except (ValueError, RuntimeError) as exc:
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
    def get_history(address: str) -> Dict[str, Any]:
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
