from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Tuple, Optional, Any

from flask import jsonify, request

from xai.core.request_validator_middleware import validate_request
from xai.core.input_validation_schemas import (
    RecoverySetupInput,
    RecoveryRequestInput,
    RecoveryVoteInput,
    RecoveryCancelInput,
    RecoveryExecuteInput,
)

if TYPE_CHECKING:
    from xai.core.node_api import NodeAPIRoutes


def register_recovery_routes(routes: "NodeAPIRoutes") -> None:
    """Register social recovery endpoints."""
    app = routes.app
    node = routes.node

    @app.route("/recovery/setup", methods=["POST"])
    @validate_request(routes.request_validator, RecoverySetupInput)
    def setup_recovery() -> Tuple[Dict[str, Any], int]:
        auth_error = routes._require_api_auth()
        if auth_error:
            return auth_error

        model: Optional[RecoverySetupInput] = getattr(request, "validated_model", None)
        if model is None:
            return routes._error_response(
                "Invalid recovery payload",
                status=400,
                code="invalid_payload",
            )

        try:
            result = node.recovery_manager.setup_guardians(
                owner_address=model.owner_address,
                guardian_addresses=model.guardians,
                threshold=model.threshold,
                signature=model.signature,
            )
            return routes._success_response(result if isinstance(result, dict) else {"result": result})
        except ValueError as exc:
            return routes._error_response(str(exc), status=400, code="recovery_invalid")
        except (RuntimeError, TypeError, KeyError) as exc:
            return routes._handle_exception(exc, "recovery_setup")

    @app.route("/recovery/request", methods=["POST"])
    @validate_request(routes.request_validator, RecoveryRequestInput)
    def request_recovery() -> Tuple[Dict[str, Any], int]:
        auth_error = routes._require_api_auth()
        if auth_error:
            return auth_error

        model: Optional[RecoveryRequestInput] = getattr(request, "validated_model", None)
        if model is None:
            return routes._error_response("Invalid recovery payload", status=400, code="invalid_payload")

        try:
            result = node.recovery_manager.initiate_recovery(
                owner_address=model.owner_address,
                new_address=model.new_address,
                guardian_address=model.guardian_address,
                signature=model.signature,
            )
            return routes._success_response(result if isinstance(result, dict) else {"result": result})
        except ValueError as exc:
            return routes._error_response(str(exc), status=400, code="recovery_invalid")
        except (RuntimeError, TypeError, KeyError) as exc:
            return routes._handle_exception(exc, "recovery_request")

    @app.route("/recovery/vote", methods=["POST"])
    @validate_request(routes.request_validator, RecoveryVoteInput)
    def vote_recovery() -> Tuple[Dict[str, Any], int]:
        auth_error = routes._require_api_auth()
        if auth_error:
            return auth_error
        model: Optional[RecoveryVoteInput] = getattr(request, "validated_model", None)
        if model is None:
            return routes._error_response("Invalid recovery payload", status=400, code="invalid_payload")

        try:
            result = node.recovery_manager.vote_recovery(
                request_id=model.request_id,
                guardian_address=model.guardian_address,
                signature=model.signature,
            )
            return routes._success_response(result if isinstance(result, dict) else {"result": result})
        except ValueError as exc:
            return routes._error_response(str(exc), status=400, code="recovery_invalid")
        except (RuntimeError, TypeError, KeyError) as exc:
            return routes._handle_exception(exc, "recovery_vote")

    @app.route("/recovery/status/<address>", methods=["GET"])
    def get_recovery_status(address: str) -> Tuple[Dict[str, Any], int]:
        try:
            status = node.recovery_manager.get_recovery_status(address)
            return jsonify({"success": True, "address": address, "status": status}), 200
        except ValueError as exc:
            return routes._error_response(str(exc), status=400, code="recovery_invalid")
        except (RuntimeError, TypeError, KeyError) as exc:
            return routes._handle_exception(exc, "recovery_get_status")

    @app.route("/recovery/cancel", methods=["POST"])
    @validate_request(routes.request_validator, RecoveryCancelInput)
    def cancel_recovery() -> Tuple[Dict[str, Any], int]:
        auth_error = routes._require_api_auth()
        if auth_error:
            return auth_error
        model: Optional[RecoveryCancelInput] = getattr(request, "validated_model", None)
        if model is None:
            return routes._error_response("Invalid recovery payload", status=400, code="invalid_payload")

        try:
            result = node.recovery_manager.cancel_recovery(
                request_id=model.request_id,
                owner_address=model.owner_address,
                signature=model.signature,
            )
            return routes._success_response(result if isinstance(result, dict) else {"result": result})
        except ValueError as exc:
            return routes._error_response(str(exc), status=400, code="recovery_invalid")
        except (RuntimeError, TypeError, KeyError) as exc:
            return routes._handle_exception(exc, "recovery_cancel")

    @app.route("/recovery/execute", methods=["POST"])
    @validate_request(routes.request_validator, RecoveryExecuteInput)
    def execute_recovery() -> Tuple[Dict[str, Any], int]:
        auth_error = routes._require_api_auth()
        if auth_error:
            return auth_error
        model: Optional[RecoveryExecuteInput] = getattr(request, "validated_model", None)
        if model is None:
            return routes._error_response("Invalid recovery payload", status=400, code="invalid_payload")

        try:
            result = node.recovery_manager.execute_recovery(
                request_id=model.request_id, executor_address=model.executor_address
            )
            return routes._success_response(result if isinstance(result, dict) else {"result": result})
        except ValueError as exc:
            return routes._error_response(str(exc), status=400, code="recovery_invalid")
        except (RuntimeError, TypeError, KeyError) as exc:
            return routes._handle_exception(exc, "recovery_execute")

    @app.route("/recovery/config/<address>", methods=["GET"])
    def get_recovery_config(address: str) -> Tuple[Dict[str, Any], int]:
        try:
            config = node.recovery_manager.get_recovery_config(address)
            if config:
                return jsonify({"success": True, "address": address, "config": config}), 200
            return (
                jsonify({"success": False, "message": "No recovery configuration found"}),
                404,
            )
        except ValueError as exc:
            return routes._error_response(str(exc), status=400, code="recovery_invalid")
        except (RuntimeError, TypeError, KeyError) as exc:
            return routes._handle_exception(exc, "recovery_get_config")

    @app.route("/recovery/guardian/<address>", methods=["GET"])
    def get_guardian_duties(address: str) -> Tuple[Dict[str, Any], int]:
        try:
            duties = node.recovery_manager.get_guardian_duties(address)
            return jsonify({"success": True, "duties": duties}), 200
        except ValueError as exc:
            return routes._error_response(str(exc), status=400, code="recovery_invalid")
        except (RuntimeError, TypeError, KeyError) as exc:
            return routes._handle_exception(exc, "recovery_get_guardian_duties")

    @app.route("/recovery/requests", methods=["GET"])
    def get_recovery_requests() -> Tuple[Dict[str, Any], int]:
        try:
            status_filter = request.args.get("status")
            requests_list = node.recovery_manager.get_all_requests(status=status_filter)
            return (
                jsonify({"success": True, "count": len(requests_list), "requests": requests_list}),
                200,
            )
        except ValueError as exc:
            return routes._error_response(str(exc), status=400, code="recovery_invalid")
        except (RuntimeError, TypeError, KeyError) as exc:
            return routes._handle_exception(exc, "recovery_get_requests")

    @app.route("/recovery/stats", methods=["GET"])
    def get_recovery_stats() -> Tuple[Dict[str, Any], int]:
        try:
            stats = node.recovery_manager.get_stats()
            return jsonify({"success": True, "stats": stats}), 200
        except ValueError as exc:
            return routes._error_response(str(exc), status=400, code="recovery_invalid")
        except (RuntimeError, TypeError, KeyError) as exc:
            return routes._handle_exception(exc, "recovery_get_stats")
