from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Tuple, Optional, Any

from flask import jsonify, request

from xai.core.request_validator_middleware import validate_request
from xai.core.input_validation_schemas import (
    MiningRegisterInput,
    MiningBonusClaimInput,
    ReferralCreateInput,
    ReferralUseInput,
)

if TYPE_CHECKING:
    from xai.core.node_api import NodeAPIRoutes


def register_mining_bonus_routes(routes: "NodeAPIRoutes") -> None:
    """Register mining bonus, referral, and leaderboard endpoints."""
    app = routes.app
    node = routes.node

    @app.route("/mining/register", methods=["POST"])
    @validate_request(routes.request_validator, MiningRegisterInput)
    def register_miner() -> Tuple[Dict[str, Any], int]:
        """Register a miner for bonus programs (admin only).

        Enrolls a miner address in the bonus tracking system to enable
        achievement tracking, referrals, and bonus claims.

        This endpoint requires API authentication.

        Request Body (MiningRegisterInput):
            {
                "address": "miner address"
            }

        Returns:
            Tuple containing (response_dict, http_status_code) where:
                - response_dict: Registration confirmation
                - http_status_code: 200 on success, 400/401/500 on error

        Raises:
            AuthenticationError: If API key is missing or invalid (401).
            ValidationError: If address is invalid (400).
            ValueError: If registration fails (400).
        """
        auth_error = routes._require_api_auth()
        if auth_error:
            return auth_error

        model: Optional[MiningRegisterInput] = getattr(request, "validated_model", None)
        if model is None:
            return routes._error_response("Invalid miner payload", status=400, code="invalid_payload")

        try:
            result = node.bonus_manager.register_miner(model.address)
            return routes._success_response(result if isinstance(result, dict) else {"result": result})
        except ValueError as exc:
            return routes._error_response(str(exc), status=400, code="mining_invalid")
        except (RuntimeError, KeyError, TypeError) as exc:
            return routes._handle_exception(exc, "register_miner")

    @app.route("/mining/achievements/<address>", methods=["GET"])
    def get_achievements(address: str) -> Tuple[Dict[str, Any], int]:
        """Get mining achievements for an address.

        Checks which achievements the miner has unlocked based on blocks mined
        and streak days, returning achievement details and unlock status.

        Path Parameters:
            address (str): The miner's blockchain address

        Query Parameters:
            blocks_mined (int, optional): Total blocks mined (default: 0)
            streak_days (int, optional): Current streak in days (default: 0)

        Returns:
            Tuple containing (response_dict, http_status_code) where:
                - response_dict: Achievement data with unlock status
                - http_status_code: 200 on success, 400/500 on error

        Raises:
            ValueError: If address is invalid (400).
        """
        blocks_mined = request.args.get("blocks_mined", default=0, type=int)
        streak_days = request.args.get("streak_days", default=0, type=int)

        try:
            result = node.bonus_manager.check_achievements(address, blocks_mined, streak_days)
            return jsonify(result), 200
        except ValueError as exc:
            return routes._error_response(str(exc), status=400, code="mining_invalid")
        except (RuntimeError, KeyError, TypeError) as exc:
            return routes._handle_exception(exc, "get_achievements")

    @app.route("/mining/claim-bonus", methods=["POST"])
    @validate_request(routes.request_validator, MiningBonusClaimInput)
    def claim_bonus() -> Tuple[Dict[str, Any], int]:
        """Claim an earned mining bonus (admin only).

        Claims a specific bonus type that the miner has earned through
        achievements, referrals, or other bonus programs.

        This endpoint requires API authentication.

        Request Body (MiningBonusClaimInput):
            {
                "address": "miner address",
                "bonus_type": "achievement" | "referral" | "streak"
            }

        Returns:
            Tuple containing (response_dict, http_status_code) where:
                - response_dict: Claim confirmation with bonus amount
                - http_status_code: 200 on success, 400/401/500 on error

        Raises:
            AuthenticationError: If API key is missing or invalid (401).
            ValidationError: If claim data is invalid (400).
            ValueError: If bonus not available or claim fails (400).
        """
        auth_error = routes._require_api_auth()
        if auth_error:
            return auth_error

        model: Optional[MiningBonusClaimInput] = getattr(request, "validated_model", None)
        if model is None:
            return routes._error_response("Invalid bonus payload", status=400, code="invalid_payload")

        try:
            result = node.bonus_manager.claim_bonus(model.address, model.bonus_type)
            return routes._success_response(result if isinstance(result, dict) else {"result": result})
        except ValueError as exc:
            return routes._error_response(str(exc), status=400, code="mining_invalid")
        except (RuntimeError, KeyError, TypeError) as exc:
            return routes._handle_exception(exc, "claim_bonus")

    @app.route("/mining/referral/create", methods=["POST"])
    @validate_request(routes.request_validator, ReferralCreateInput)
    def create_referral_code() -> Tuple[Dict[str, Any], int]:
        """Create a referral code for a miner (admin only).

        Generates a unique referral code that can be shared with new miners
        to earn referral bonuses when they join and mine.

        This endpoint requires API authentication.

        Request Body (ReferralCreateInput):
            {
                "address": "referrer address"
            }

        Returns:
            Tuple containing (response_dict, http_status_code) where:
                - response_dict: Contains generated referral code
                - http_status_code: 200 on success, 400/401/500 on error

        Raises:
            AuthenticationError: If API key is missing or invalid (401).
            ValidationError: If address is invalid (400).
            ValueError: If code creation fails (400).
        """
        auth_error = routes._require_api_auth()
        if auth_error:
            return auth_error

        model: Optional[ReferralCreateInput] = getattr(request, "validated_model", None)
        if model is None:
            return routes._error_response("Invalid referral payload", status=400, code="invalid_payload")

        try:
            result = node.bonus_manager.create_referral_code(model.address)
            return routes._success_response(result if isinstance(result, dict) else {"result": result})
        except ValueError as exc:
            return routes._error_response(str(exc), status=400, code="referral_invalid")
        except (RuntimeError, KeyError, TypeError) as exc:
            return routes._handle_exception(exc, "create_referral_code")

    @app.route("/mining/referral/use", methods=["POST"])
    @validate_request(routes.request_validator, ReferralUseInput)
    def use_referral_code() -> Tuple[Dict[str, Any], int]:
        """Apply a referral code for a new miner (admin only).

        Registers a referral relationship between new miner and referrer,
        enabling both parties to earn referral bonuses.

        This endpoint requires API authentication.

        Request Body (ReferralUseInput):
            {
                "new_address": "new miner address",
                "referral_code": "code from referrer",
                "metadata": {} (optional)
            }

        Returns:
            Tuple containing (response_dict, http_status_code) where:
                - response_dict: Confirmation with referral details
                - http_status_code: 200 on success, 400/401/500 on error

        Raises:
            AuthenticationError: If API key is missing or invalid (401).
            ValidationError: If referral data is invalid (400).
            ValueError: If code is invalid or already used (400).
        """
        auth_error = routes._require_api_auth()
        if auth_error:
            return auth_error

        model: Optional[ReferralUseInput] = getattr(request, "validated_model", None)
        if model is None:
            return routes._error_response("Invalid referral payload", status=400, code="invalid_payload")

        try:
            result = node.bonus_manager.use_referral_code(
                model.new_address,
                model.referral_code,
                metadata=getattr(model, "metadata", None),
            )
            return routes._success_response(result if isinstance(result, dict) else {"result": result})
        except ValueError as exc:
            return routes._error_response(str(exc), status=400, code="referral_invalid")
        except (RuntimeError, KeyError, TypeError) as exc:
            return routes._handle_exception(exc, "use_referral_code")

    @app.route("/mining/user-bonuses/<address>", methods=["GET"])
    def get_user_bonuses(address: str) -> Tuple[Dict[str, Any], int]:
        """Get all bonuses for a specific miner.

        Returns complete bonus status including earned bonuses, claimed bonuses,
        pending bonuses, and total bonus amount for the miner.

        Path Parameters:
            address (str): The miner's blockchain address

        Returns:
            Tuple containing (response_dict, http_status_code) where:
                - response_dict: Complete bonus information
                - http_status_code: 200 on success, 400/500 on error

        Raises:
            ValueError: If address is invalid (400).
        """
        try:
            result = node.bonus_manager.get_user_bonuses(address)
            return jsonify(result), 200
        except ValueError as exc:
            return routes._error_response(str(exc), status=400, code="mining_invalid")
        except (RuntimeError, KeyError, TypeError) as exc:
            return routes._handle_exception(exc, "get_user_bonuses")

    @app.route("/mining/leaderboard", methods=["GET"])
    def get_bonus_leaderboard() -> Tuple[Dict[str, Any], int]:
        """Get mining bonus leaderboard.

        Returns ranked list of miners by total bonuses earned.

        Query Parameters:
            limit (int, optional): Maximum entries to return (default: 10)

        Returns:
            Tuple containing (response_dict, http_status_code) where:
                - response_dict: Contains success flag, limit, and leaderboard list
                - http_status_code: 200 on success, 400/500 on error

        Raises:
            ValueError: If limit is invalid (400).
        """
        limit = request.args.get("limit", default=10, type=int)

        try:
            leaderboard = node.bonus_manager.get_leaderboard(limit)
            return jsonify({"success": True, "limit": limit, "leaderboard": leaderboard}), 200
        except ValueError as exc:
            return routes._error_response(str(exc), status=400, code="mining_invalid")
        except (RuntimeError, KeyError, TypeError) as exc:
            return routes._handle_exception(exc, "get_bonus_leaderboard")

    @app.route("/mining/leaderboard/unified", methods=["GET"])
    def get_unified_leaderboard() -> Tuple[Dict[str, Any], int]:
        """Get unified leaderboard across all mining metrics.

        Returns ranked miners based on selected metric combining blocks mined,
        bonuses earned, streaks, and other achievements.

        Query Parameters:
            limit (int, optional): Maximum entries to return (default: 10)
            metric (str, optional): Ranking metric - "composite", "blocks", or "bonuses"
                                   (default: "composite")

        Returns:
            Tuple containing (response_dict, http_status_code) where:
                - response_dict: Contains success flag, metric, limit, and leaderboard
                - http_status_code: 200 on success, 400/500 on error

        Raises:
            ValueError: If limit or metric is invalid (400).
        """
        limit = request.args.get("limit", default=10, type=int)
        metric = request.args.get("metric", default="composite", type=str)

        try:
            leaderboard = node.bonus_manager.get_unified_leaderboard(metric, limit)
            return jsonify(
                {"success": True, "limit": limit, "metric": metric, "leaderboard": leaderboard}
            ), 200
        except ValueError as exc:
            return routes._error_response(str(exc), status=400, code="mining_invalid")
        except (RuntimeError, KeyError, TypeError) as exc:
            return routes._handle_exception(exc, "get_unified_leaderboard")

    @app.route("/mining/stats", methods=["GET"])
    def get_mining_bonus_stats() -> Tuple[Dict[str, Any], int]:
        """Get system-wide mining bonus statistics.

        Returns aggregate statistics about the mining bonus program including
        total bonuses issued, active miners, and program participation metrics.

        Returns:
            Tuple containing (response_dict, http_status_code) where:
                - response_dict: Contains success flag and stats object
                - http_status_code: 200 on success, 400/500 on error

        Raises:
            ValueError: If stats retrieval fails (400).
        """
        try:
            stats = node.bonus_manager.get_stats()
            return jsonify({"success": True, "stats": stats}), 200
        except ValueError as exc:
            return routes._error_response(str(exc), status=400, code="mining_invalid")
        except (RuntimeError, KeyError, TypeError) as exc:
            return routes._handle_exception(exc, "get_mining_bonus_stats")
