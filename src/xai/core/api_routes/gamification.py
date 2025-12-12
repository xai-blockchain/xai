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
        """Get recent airdrop winners.

        Returns list of recent airdrop events with winner addresses and amounts.

        Query Parameters:
            limit (int, optional): Maximum airdrops to return (default: 10)

        Returns:
            Dict containing:
                - success (bool): Always True
                - airdrops (list): Recent airdrop events
        """
        limit = request.args.get("limit", default=10, type=int)
        recent_airdrops = blockchain.airdrop_manager.get_recent_airdrops(limit)
        return jsonify({"success": True, "airdrops": recent_airdrops})

    @app.route("/airdrop/user/<address>", methods=["GET"])
    def get_user_airdrops(address: str) -> Dict[str, Any]:
        """Get airdrop history for a specific user.

        Returns complete airdrop history including total airdrops received
        and total amount claimed.

        Path Parameters:
            address (str): The blockchain address to query

        Returns:
            Dict containing:
                - success (bool): Always True
                - address (str): The queried address
                - total_airdrops (int): Number of airdrops received
                - total_received (float): Total amount received from airdrops
                - history (list): List of airdrop events
        """
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
        """Get mining streak leaderboard.

        Returns top miners ranked by their current or longest mining streaks.

        Query Parameters:
            limit (int, optional): Maximum entries to return (default: 10)
            sort_by (str, optional): Sort field - "current_streak" or "longest_streak"
                                    (default: "current_streak")

        Returns:
            Dict containing:
                - success (bool): Always True
                - leaderboard (list): Ranked list of miners with streak stats
        """
        limit = request.args.get("limit", default=10, type=int)
        sort_by = request.args.get("sort_by", default="current_streak")
        leaderboard = blockchain.streak_tracker.get_leaderboard(limit, sort_by)
        return jsonify({"success": True, "leaderboard": leaderboard})

    @app.route("/mining/streak/<address>", methods=["GET"])
    def get_miner_streak(address: str) -> Tuple[Dict[str, Any], int]:
        """Get mining streak statistics for a specific miner.

        Returns current streak, longest streak, and other mining statistics
        for the specified address.

        Path Parameters:
            address (str): The miner's blockchain address

        Returns:
            Tuple containing (response_dict, http_status_code) where:
                - response_dict: Contains success flag, address, and stats object
                - http_status_code: 200 on success, 404 if no mining history

        Raises:
            NotFound: If address has no mining history (404).
        """
        stats = blockchain.streak_tracker.get_miner_stats(address)
        if not stats:
            return (
                jsonify({"success": False, "error": "No mining history found for this address"}),
                404,
            )
        return jsonify({"success": True, "address": address, "stats": stats}), 200

    @app.route("/treasure/active", methods=["GET"])
    def get_active_treasures() -> Dict[str, Any]:
        """Get all active treasure hunts.

        Returns list of treasure hunts that are currently claimable,
        excluding already claimed treasures.

        Returns:
            Dict containing:
                - success (bool): Always True
                - count (int): Number of active treasures
                - treasures (list): List of active treasure hunt objects
        """
        treasures = blockchain.treasure_manager.get_active_treasures()
        return jsonify({"success": True, "count": len(treasures), "treasures": treasures})

    @app.route("/treasure/create", methods=["POST"])
    @validate_request(routes.request_validator, TreasureCreateInput)
    def create_treasure() -> Tuple[Dict[str, Any], int]:
        """Create a new treasure hunt (admin only).

        Creates a treasure hunt with a puzzle that users can solve to claim rewards.

        This endpoint requires API authentication.

        Request Body (TreasureCreateInput):
            {
                "creator": "address",
                "amount": float,
                "puzzle_type": "hash" | "math" | "riddle",
                "puzzle_data": object,
                "hint": "optional hint text"
            }

        Returns:
            Tuple containing (response_dict, http_status_code) where:
                - response_dict: Contains treasure_id and success message
                - http_status_code: 200 on success, 400/401/500 on error

        Raises:
            AuthenticationError: If API key is missing or invalid (401).
            ValidationError: If treasure data is invalid (400).
            ValueError: If treasure creation fails (500).
            RuntimeError: If treasure manager operation fails (500).
        """
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
        except (ValueError, RuntimeError) as exc:
            return routes._handle_exception(exc, "create_treasure")

    @app.route("/treasure/claim", methods=["POST"])
    @validate_request(routes.request_validator, TreasureClaimInput)
    def claim_treasure() -> Tuple[Dict[str, Any], int]:
        """Claim a treasure hunt by solving its puzzle.

        Attempts to claim a treasure by providing the solution to its puzzle.
        If successful, creates a COINBASE transaction crediting the reward.

        This endpoint requires API authentication.

        Request Body (TreasureClaimInput):
            {
                "treasure_id": "string",
                "claimer": "address",
                "solution": "puzzle solution"
            }

        Returns:
            Tuple containing (response_dict, http_status_code) where:
                - response_dict: Contains amount and success message or error
                - http_status_code: 200 on success, 400/401/500 on error

        Raises:
            AuthenticationError: If API key is missing or invalid (401).
            ValidationError: If claim data is invalid (400).
            ValueError: If solution is incorrect or claim fails (400).
            RuntimeError: If treasure manager operation fails (500).
        """
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

        except (ValueError, RuntimeError) as exc:
            return routes._handle_exception(exc, "claim_treasure")

    @app.route("/treasure/details/<treasure_id>", methods=["GET"])
    def get_treasure_details(treasure_id: str) -> Tuple[Dict[str, Any], int]:
        """Get detailed information about a specific treasure hunt.

        Returns complete details including creator, amount, puzzle type,
        hint, and claim status.

        Path Parameters:
            treasure_id (str): The unique treasure hunt identifier

        Returns:
            Tuple containing (response_dict, http_status_code) where:
                - response_dict: Contains success flag and treasure object
                - http_status_code: 200 on success, 404 if not found

        Raises:
            NotFound: If treasure_id does not exist (404).
        """
        treasure = blockchain.treasure_manager.get_treasure_details(treasure_id)
        if not treasure:
            return jsonify({"error": "Treasure not found"}), 404
        return jsonify({"success": True, "treasure": treasure}), 200

    @app.route("/timecapsule/pending", methods=["GET"])
    def get_pending_timecapsules() -> Dict[str, Any]:
        """Get pending time capsule transactions.

        Returns list of time-locked transactions that have not yet matured
        and can't be claimed yet.

        Returns:
            Dict containing:
                - success (bool): Always True
                - count (int): Number of pending capsules
                - capsules (list): List of pending time capsule objects
        """
        capsules = blockchain.timecapsule_manager.get_pending_capsules()
        return jsonify({"success": True, "count": len(capsules), "capsules": capsules})

    @app.route("/timecapsule/<address>", methods=["GET"])
    def get_user_timecapsules(address: str) -> Dict[str, Any]:
        """Get time capsule transactions for a specific user.

        Returns both sent and received time capsules for the specified address,
        including pending and claimed capsules.

        Path Parameters:
            address (str): The blockchain address to query

        Returns:
            Dict containing:
                - success (bool): Always True
                - address (str): The queried address
                - sent (list): Time capsules sent by this address
                - received (list): Time capsules this address can claim
        """
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
        """Get system-wide fee refund statistics.

        Returns aggregate statistics about fee refunds including total refunds
        processed, total amount refunded, and average refund amount.

        Returns:
            Dict containing:
                - success (bool): Always True
                - stats (object): Refund statistics object
        """
        stats = blockchain.fee_refund_calculator.get_refund_stats()
        return jsonify({"success": True, "stats": stats})

    @app.route("/refunds/<address>", methods=["GET"])
    def get_user_refunds(address: str) -> Dict[str, Any]:
        """Get fee refund history for a specific user.

        Returns complete refund history including total refunds received
        and total amount refunded for the specified address.

        Path Parameters:
            address (str): The blockchain address to query

        Returns:
            Dict containing:
                - success (bool): Always True
                - address (str): The queried address
                - total_refunds (int): Number of refunds received
                - total_refunded (float): Total amount refunded
                - history (list): List of refund events
        """
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
