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
        auth_error = routes._require_api_auth()
        if auth_error:
            return auth_error

        model: Optional[MiningRegisterInput] = getattr(request, "validated_model", None)
        if model is None:
            return routes._error_response("Invalid miner payload", status=400, code="invalid_payload")

        try:
            result = node.bonus_manager.register_miner(model.address)
            return routes._success_response(result if isinstance(result, dict) else {"result": result})
        except Exception as exc:
            return routes._handle_exception(exc, "register_miner")

    @app.route("/mining/achievements/<address>", methods=["GET"])
    def get_achievements(address: str) -> Tuple[Dict[str, Any], int]:
        blocks_mined = request.args.get("blocks_mined", default=0, type=int)
        streak_days = request.args.get("streak_days", default=0, type=int)

        try:
            result = node.bonus_manager.check_achievements(address, blocks_mined, streak_days)
            return jsonify(result), 200
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    @app.route("/mining/claim-bonus", methods=["POST"])
    @validate_request(routes.request_validator, MiningBonusClaimInput)
    def claim_bonus() -> Tuple[Dict[str, Any], int]:
        auth_error = routes._require_api_auth()
        if auth_error:
            return auth_error

        model: Optional[MiningBonusClaimInput] = getattr(request, "validated_model", None)
        if model is None:
            return routes._error_response("Invalid bonus payload", status=400, code="invalid_payload")

        try:
            result = node.bonus_manager.claim_bonus(model.address, model.bonus_type)
            return routes._success_response(result if isinstance(result, dict) else {"result": result})
        except Exception as exc:
            return routes._handle_exception(exc, "claim_bonus")

    @app.route("/mining/referral/create", methods=["POST"])
    @validate_request(routes.request_validator, ReferralCreateInput)
    def create_referral_code() -> Tuple[Dict[str, Any], int]:
        auth_error = routes._require_api_auth()
        if auth_error:
            return auth_error

        model: Optional[ReferralCreateInput] = getattr(request, "validated_model", None)
        if model is None:
            return routes._error_response("Invalid referral payload", status=400, code="invalid_payload")

        try:
            result = node.bonus_manager.create_referral_code(model.address)
            return routes._success_response(result if isinstance(result, dict) else {"result": result})
        except Exception as exc:
            return routes._handle_exception(exc, "create_referral_code")

    @app.route("/mining/referral/use", methods=["POST"])
    @validate_request(routes.request_validator, ReferralUseInput)
    def use_referral_code() -> Tuple[Dict[str, Any], int]:
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
        except Exception as exc:
            return routes._handle_exception(exc, "use_referral_code")

    @app.route("/mining/user-bonuses/<address>", methods=["GET"])
    def get_user_bonuses(address: str) -> Tuple[Dict[str, Any], int]:
        try:
            result = node.bonus_manager.get_user_bonuses(address)
            return jsonify(result), 200
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    @app.route("/mining/leaderboard", methods=["GET"])
    def get_bonus_leaderboard() -> Tuple[Dict[str, Any], int]:
        limit = request.args.get("limit", default=10, type=int)

        try:
            leaderboard = node.bonus_manager.get_leaderboard(limit)
            return jsonify({"success": True, "limit": limit, "leaderboard": leaderboard}), 200
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    @app.route("/mining/leaderboard/unified", methods=["GET"])
    def get_unified_leaderboard() -> Tuple[Dict[str, Any], int]:
        limit = request.args.get("limit", default=10, type=int)
        metric = request.args.get("metric", default="composite", type=str)

        try:
            leaderboard = node.bonus_manager.get_unified_leaderboard(metric, limit)
            return jsonify(
                {"success": True, "limit": limit, "metric": metric, "leaderboard": leaderboard}
            ), 200
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    @app.route("/mining/stats", methods=["GET"])
    def get_mining_bonus_stats() -> Tuple[Dict[str, Any], int]:
        try:
            stats = node.bonus_manager.get_stats()
            return jsonify({"success": True, "stats": stats}), 200
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500
