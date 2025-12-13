from __future__ import annotations

import logging
logger = logging.getLogger(__name__)


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
        """Set up social recovery guardians for an account (admin only).

        Configures trusted guardians who can collectively help recover access
        to an account if the owner loses their keys. Requires threshold number
        of guardian signatures to execute recovery.

        This endpoint requires API authentication.

        Request Body (RecoverySetupInput):
            {
                "owner_address": "account owner address",
                "guardians": ["guardian1_addr", "guardian2_addr", ...],
                "threshold": int (minimum guardian votes needed),
                "signature": "owner signature authorizing setup"
            }

        Returns:
            Tuple containing (response_dict, http_status_code) where:
                - response_dict: Setup confirmation
                - http_status_code: 200 on success, 400/401/500 on error

        Raises:
            AuthenticationError: If API key is missing or invalid (401).
            ValidationError: If recovery setup data is invalid (400).
            ValueError: If guardian setup fails (400).
        """
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
            logger.warning(
                "ValueError in setup_recovery",
                error_type="ValueError",
                error=str(exc),
                function="setup_recovery",
            )
            return routes._error_response(str(exc), status=400, code="recovery_invalid")
        except (RuntimeError, TypeError, KeyError) as exc:
            return routes._handle_exception(exc, "recovery_setup")

    @app.route("/recovery/request", methods=["POST"])
    @validate_request(routes.request_validator, RecoveryRequestInput)
    def request_recovery() -> Tuple[Dict[str, Any], int]:
        """Initiate account recovery process (admin only).

        Starts a recovery request to transfer account control to a new address.
        Requires guardian to initiate and threshold number of guardians to approve.

        This endpoint requires API authentication.

        Request Body (RecoveryRequestInput):
            {
                "owner_address": "original account address",
                "new_address": "new address to transfer control to",
                "guardian_address": "guardian initiating request",
                "signature": "guardian signature"
            }

        Returns:
            Tuple containing (response_dict, http_status_code) where:
                - response_dict: Recovery request ID and status
                - http_status_code: 200 on success, 400/401/500 on error

        Raises:
            AuthenticationError: If API key is missing or invalid (401).
            ValidationError: If recovery request data is invalid (400).
            ValueError: If recovery initiation fails (400).
        """
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
            logger.warning(
                "ValueError in request_recovery",
                error_type="ValueError",
                error=str(exc),
                function="request_recovery",
            )
            return routes._error_response(str(exc), status=400, code="recovery_invalid")
        except (RuntimeError, TypeError, KeyError) as exc:
            return routes._handle_exception(exc, "recovery_request")

    @app.route("/recovery/vote", methods=["POST"])
    @validate_request(routes.request_validator, RecoveryVoteInput)
    def vote_recovery() -> Tuple[Dict[str, Any], int]:
        """Vote to approve a recovery request (admin only).

        Guardian casts vote to approve account recovery. When threshold is reached,
        recovery can be executed to transfer account control.

        This endpoint requires API authentication.

        Request Body (RecoveryVoteInput):
            {
                "request_id": "recovery request identifier",
                "guardian_address": "guardian voting address",
                "signature": "guardian signature"
            }

        Returns:
            Tuple containing (response_dict, http_status_code) where:
                - response_dict: Vote confirmation and current vote count
                - http_status_code: 200 on success, 400/401/500 on error

        Raises:
            AuthenticationError: If API key is missing or invalid (401).
            ValidationError: If vote data is invalid (400).
            ValueError: If guardian already voted or not authorized (400).
        """
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
            logger.warning(
                "ValueError in vote_recovery",
                error_type="ValueError",
                error=str(exc),
                function="vote_recovery",
            )
            return routes._error_response(str(exc), status=400, code="recovery_invalid")
        except (RuntimeError, TypeError, KeyError) as exc:
            return routes._handle_exception(exc, "recovery_vote")

    @app.route("/recovery/status/<address>", methods=["GET"])
    def get_recovery_status(address: str) -> Tuple[Dict[str, Any], int]:
        """Get recovery status for an account.

        Returns current recovery status including active requests, guardian votes,
        and whether recovery is configured for the account.

        Path Parameters:
            address (str): The account address to query

        Returns:
            Tuple containing (response_dict, http_status_code) where:
                - response_dict: Contains success flag, address, and status object
                - http_status_code: 200 on success, 400/500 on error

        Raises:
            ValueError: If address is invalid (400).
        """
        try:
            status = node.recovery_manager.get_recovery_status(address)
            return jsonify({"success": True, "address": address, "status": status}), 200
        except ValueError as exc:
            logger.warning(
                "ValueError in get_recovery_status",
                error_type="ValueError",
                error=str(exc),
                function="get_recovery_status",
            )
            return routes._error_response(str(exc), status=400, code="recovery_invalid")
        except (RuntimeError, TypeError, KeyError) as exc:
            return routes._handle_exception(exc, "recovery_get_status")

    @app.route("/recovery/cancel", methods=["POST"])
    @validate_request(routes.request_validator, RecoveryCancelInput)
    def cancel_recovery() -> Tuple[Dict[str, Any], int]:
        """Cancel an active recovery request (admin only).

        Allows account owner to cancel recovery request if they regain access
        before guardians complete the recovery process.

        This endpoint requires API authentication.

        Request Body (RecoveryCancelInput):
            {
                "request_id": "recovery request identifier",
                "owner_address": "account owner address",
                "signature": "owner signature"
            }

        Returns:
            Tuple containing (response_dict, http_status_code) where:
                - response_dict: Cancellation confirmation
                - http_status_code: 200 on success, 400/401/500 on error

        Raises:
            AuthenticationError: If API key is missing or invalid (401).
            ValidationError: If cancel data is invalid (400).
            ValueError: If request doesn't exist or not authorized (400).
        """
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
            logger.warning(
                "ValueError in cancel_recovery",
                error_type="ValueError",
                error=str(exc),
                function="cancel_recovery",
            )
            return routes._error_response(str(exc), status=400, code="recovery_invalid")
        except (RuntimeError, TypeError, KeyError) as exc:
            return routes._handle_exception(exc, "recovery_cancel")

    @app.route("/recovery/execute", methods=["POST"])
    @validate_request(routes.request_validator, RecoveryExecuteInput)
    def execute_recovery() -> Tuple[Dict[str, Any], int]:
        """Execute approved recovery to transfer account control (admin only).

        Finalizes recovery process when threshold guardian votes are reached,
        transferring account control to the new address specified in request.

        This endpoint requires API authentication.

        Request Body (RecoveryExecuteInput):
            {
                "request_id": "recovery request identifier",
                "executor_address": "address executing recovery (any guardian)"
            }

        Returns:
            Tuple containing (response_dict, http_status_code) where:
                - response_dict: Execution confirmation with new address
                - http_status_code: 200 on success, 400/401/500 on error

        Raises:
            AuthenticationError: If API key is missing or invalid (401).
            ValidationError: If execute data is invalid (400).
            ValueError: If threshold not met or execution fails (400).
        """
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
            logger.warning(
                "ValueError in execute_recovery",
                error_type="ValueError",
                error=str(exc),
                function="execute_recovery",
            )
            return routes._error_response(str(exc), status=400, code="recovery_invalid")
        except (RuntimeError, TypeError, KeyError) as exc:
            return routes._handle_exception(exc, "recovery_execute")

    @app.route("/recovery/config/<address>", methods=["GET"])
    def get_recovery_config(address: str) -> Tuple[Dict[str, Any], int]:
        """Get recovery configuration for an account.

        Returns guardian list, threshold settings, and recovery configuration
        details for the specified account.

        Path Parameters:
            address (str): The account address to query

        Returns:
            Tuple containing (response_dict, http_status_code) where:
                - response_dict: Contains success flag, address, and config object
                - http_status_code: 200 on success, 404 if no config, 400/500 on error

        Raises:
            NotFound: If account has no recovery configuration (404).
            ValueError: If address is invalid (400).
        """
        try:
            config = node.recovery_manager.get_recovery_config(address)
            if config:
                return jsonify({"success": True, "address": address, "config": config}), 200
            return (
                jsonify({"success": False, "message": "No recovery configuration found"}),
                404,
            )
        except ValueError as exc:
            logger.warning(
                "ValueError in get_recovery_config",
                error_type="ValueError",
                error=str(exc),
                function="get_recovery_config",
            )
            return routes._error_response(str(exc), status=400, code="recovery_invalid")
        except (RuntimeError, TypeError, KeyError) as exc:
            return routes._handle_exception(exc, "recovery_get_config")

    @app.route("/recovery/guardian/<address>", methods=["GET"])
    def get_guardian_duties(address: str) -> Tuple[Dict[str, Any], int]:
        """Get guardian duties and pending recovery requests.

        Returns all accounts where this address is a guardian and any pending
        recovery requests requiring this guardian's vote.

        Path Parameters:
            address (str): The guardian address to query

        Returns:
            Tuple containing (response_dict, http_status_code) where:
                - response_dict: Contains success flag and duties object
                - http_status_code: 200 on success, 400/500 on error

        Raises:
            ValueError: If address is invalid (400).
        """
        try:
            duties = node.recovery_manager.get_guardian_duties(address)
            return jsonify({"success": True, "duties": duties}), 200
        except ValueError as exc:
            logger.warning(
                "ValueError in get_guardian_duties",
                error_type="ValueError",
                error=str(exc),
                function="get_guardian_duties",
            )
            return routes._error_response(str(exc), status=400, code="recovery_invalid")
        except (RuntimeError, TypeError, KeyError) as exc:
            return routes._handle_exception(exc, "recovery_get_guardian_duties")

    @app.route("/recovery/requests", methods=["GET"])
    def get_recovery_requests() -> Tuple[Dict[str, Any], int]:
        """Get all recovery requests, optionally filtered by status.

        Returns list of recovery requests with optional status filtering
        (pending, approved, executed, cancelled).

        Query Parameters:
            status (str, optional): Filter by status - "pending", "approved",
                                   "executed", or "cancelled"

        Returns:
            Tuple containing (response_dict, http_status_code) where:
                - response_dict: Contains success flag, count, and requests list
                - http_status_code: 200 on success, 400/500 on error

        Raises:
            ValueError: If status filter is invalid (400).
        """
        try:
            status_filter = request.args.get("status")
            requests_list = node.recovery_manager.get_all_requests(status=status_filter)
            return (
                jsonify({"success": True, "count": len(requests_list), "requests": requests_list}),
                200,
            )
        except ValueError as exc:
            logger.warning(
                "ValueError in get_recovery_requests",
                error_type="ValueError",
                error=str(exc),
                function="get_recovery_requests",
            )
            return routes._error_response(str(exc), status=400, code="recovery_invalid")
        except (RuntimeError, TypeError, KeyError) as exc:
            return routes._handle_exception(exc, "recovery_get_requests")

    @app.route("/recovery/stats", methods=["GET"])
    def get_recovery_stats() -> Tuple[Dict[str, Any], int]:
        """Get system-wide social recovery statistics.

        Returns aggregate statistics about recovery system including total
        accounts with recovery configured, active requests, and success rate.

        Returns:
            Tuple containing (response_dict, http_status_code) where:
                - response_dict: Contains success flag and stats object
                - http_status_code: 200 on success, 400/500 on error

        Raises:
            ValueError: If stats retrieval fails (400).
        """
        try:
            stats = node.recovery_manager.get_stats()
            return jsonify({"success": True, "stats": stats}), 200
        except ValueError as exc:
            logger.warning(
                "ValueError in get_recovery_stats",
                error_type="ValueError",
                error=str(exc),
                function="get_recovery_stats",
            )
            return routes._error_response(str(exc), status=400, code="recovery_invalid")
        except (RuntimeError, TypeError, KeyError) as exc:
            return routes._handle_exception(exc, "recovery_get_stats")
