from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Tuple, Optional, Any

from flask import jsonify, request

from xai.core.request_validator_middleware import validate_request
from xai.core.input_validation_schemas import TreasureCreateInput, TreasureClaimInput

if TYPE_CHECKING:
    from xai.core.node_api import NodeAPIRoutes


def register_gamification_routes(routes: "NodeAPIRoutes") -> None:
    """Register gamification endpoints (airdrops, streaks, treasure, refunds)."""
    app = routes.app
    blockchain = routes.blockchain
    node = routes.node

    @app.route("/airdrop/winners", methods=["GET"])
    def get_airdrop_winners() -> Dict[str, Any]:
        limit = request.args.get("limit", default=10, type=int)
        recent_airdrops = blockchain.airdrop_manager.get_recent_airdrops(limit)
        return jsonify({"success": True, "airdrops": recent_airdrops})

    @app.route("/airdrop/user/<address>", methods=["GET"])
    def get_user_airdrops(address: str) -> Dict[str, Any]:
        history = blockchain.airdrop_manager.get_user_airdrop_history(address)
        total_received = sum(a["amount"] for a in history)
        return jsonify(
            {
                "success": True,
                "address": address,
                "total_airdrops": len(history),
                "total_received": total_received,
                "history": history,
            }
        )

    @app.route("/mining/streaks", methods=["GET"])
    def get_mining_streaks() -> Dict[str, Any]:
        limit = request.args.get("limit", default=10, type=int)
        sort_by = request.args.get("sort_by", default="current_streak")
        leaderboard = blockchain.streak_tracker.get_leaderboard(limit, sort_by)
        return jsonify({"success": True, "leaderboard": leaderboard})

    @app.route("/mining/streak/<address>", methods=["GET"])
    def get_miner_streak(address: str) -> Tuple[Dict[str, Any], int]:
        stats = blockchain.streak_tracker.get_miner_stats(address)
        if not stats:
            return (
                jsonify({"success": False, "error": "No mining history found for this address"}),
                404,
            )
        return jsonify({"success": True, "address": address, "stats": stats}), 200

    @app.route("/treasure/active", methods=["GET"])
    def get_active_treasures() -> Dict[str, Any]:
        treasures = blockchain.treasure_manager.get_active_treasures()
        return jsonify({"success": True, "count": len(treasures), "treasures": treasures})

    @app.route("/treasure/create", methods=["POST"])
    @validate_request(routes.request_validator, TreasureCreateInput)
    def create_treasure() -> Tuple[Dict[str, Any], int]:
        auth_error = routes._require_api_auth()
        if auth_error:
            return auth_error

        model: Optional[TreasureCreateInput] = getattr(request, "validated_model", None)
        if model is None:
            return routes._error_response("Invalid treasure payload", status=400, code="invalid_payload")

        try:
            treasure_id = blockchain.treasure_manager.create_treasure_hunt(
                creator_address=model.creator,
                amount=float(model.amount),
                puzzle_type=model.puzzle_type,
                puzzle_data=model.puzzle_data,
                hint=model.hint or "",
            )
            return routes._success_response(
                {
                    "treasure_id": treasure_id,
                    "message": "Treasure hunt created successfully",
                }
            )
        except Exception as exc:
            return routes._handle_exception(exc, "create_treasure")

    @app.route("/treasure/claim", methods=["POST"])
    @validate_request(routes.request_validator, TreasureClaimInput)
    def claim_treasure() -> Tuple[Dict[str, Any], int]:
        auth_error = routes._require_api_auth()
        if auth_error:
            return auth_error

        model: Optional[TreasureClaimInput] = getattr(request, "validated_model", None)
        if model is None:
            return routes._error_response("Invalid treasure payload", status=400, code="invalid_payload")

        try:
            from xai.core.blockchain import Transaction

            success, amount = blockchain.treasure_manager.claim_treasure(
                treasure_id=model.treasure_id,
                claimer_address=model.claimer,
                solution=model.solution,
            )

            if success:
                treasure_tx = Transaction("COINBASE", model.claimer, amount, tx_type="treasure")
                treasure_tx.txid = treasure_tx.calculate_hash()
                blockchain.pending_transactions.append(treasure_tx)

                return routes._success_response(
                    {
                        "amount": amount,
                        "message": "Treasure claimed successfully!",
                    }
                )
            return routes._error_response(
                "Incorrect solution",
                status=400,
                code="invalid_solution",
            )

        except Exception as exc:
            return routes._handle_exception(exc, "claim_treasure")

    @app.route("/treasure/details/<treasure_id>", methods=["GET"])
    def get_treasure_details(treasure_id: str) -> Tuple[Dict[str, Any], int]:
        treasure = blockchain.treasure_manager.get_treasure_details(treasure_id)
        if not treasure:
            return jsonify({"error": "Treasure not found"}), 404
        return jsonify({"success": True, "treasure": treasure}), 200

    @app.route("/timecapsule/pending", methods=["GET"])
    def get_pending_timecapsules() -> Dict[str, Any]:
        capsules = blockchain.timecapsule_manager.get_pending_capsules()
        return jsonify({"success": True, "count": len(capsules), "capsules": capsules})

    @app.route("/timecapsule/<address>", methods=["GET"])
    def get_user_timecapsules(address: str) -> Dict[str, Any]:
        capsules = blockchain.timecapsule_manager.get_user_capsules(address)
        return jsonify(
            {
                "success": True,
                "address": address,
                "sent": capsules["sent"],
                "received": capsules["received"],
            }
        )

    @app.route("/refunds/stats", methods=["GET"])
    def get_refund_stats() -> Dict[str, Any]:
        stats = blockchain.fee_refund_calculator.get_refund_stats()
        return jsonify({"success": True, "stats": stats})

    @app.route("/refunds/<address>", methods=["GET"])
    def get_user_refunds(address: str) -> Dict[str, Any]:
        history = blockchain.fee_refund_calculator.get_user_refund_history(address)
        total_refunded = sum(r["amount"] for r in history)
        return jsonify(
            {
                "success": True,
                "address": address,
                "total_refunds": len(history),
                "total_refunded": total_refunded,
                "history": history,
            }
        )
