"""
Crypto Deposit Routes Module

Handles all cryptocurrency deposit-related endpoints including:
- Deposit address generation (BTC/ETH/USDT)
- User deposit address queries
- Pending deposit monitoring
- Deposit history
- System statistics

Integrates with the CryptoDepositManager for deposit tracking and confirmation.
"""

from __future__ import annotations

import logging
logger = logging.getLogger(__name__)


from typing import TYPE_CHECKING, Dict, Tuple, Optional, Any

from flask import jsonify, request

from xai.core.request_validator_middleware import validate_request
from xai.core.input_validation_schemas import CryptoDepositAddressInput

if TYPE_CHECKING:
    from xai.core.node_api import NodeAPIRoutes


def register_crypto_deposit_routes(routes: "NodeAPIRoutes") -> None:
    """Register all crypto deposit-related endpoints."""
    app = routes.app
    node = routes.node

    @app.route("/exchange/crypto/generate-address", methods=["POST"])
    @validate_request(routes.request_validator, CryptoDepositAddressInput)
    def generate_crypto_deposit_address() -> Tuple[Dict[str, Any], int]:
        """Generate unique deposit address for BTC/ETH/USDT.

        Creates a new deposit address for the specified cryptocurrency that will
        automatically credit the user's account when deposits are confirmed.

        This endpoint requires API authentication.

        Request Body (CryptoDepositAddressInput):
            {
                "user_address": "XAI address",
                "currency": "BTC" | "ETH" | "USDT"
            }

        Returns:
            Tuple containing (response_dict, http_status_code) where:
                - response_dict: Contains generated deposit address details
                - http_status_code: 200 on success, 400/503 on error

        Raises:
            ValueError: If currency is not supported or user_address invalid (400).
            RuntimeError: If crypto deposit module is disabled (503).
        """
        if not node.crypto_deposit_manager:
            return routes._error_response(
                "Crypto deposit module disabled", status=503, code="module_disabled"
            )
        auth_error = routes._require_api_auth()
        if auth_error:
            return auth_error

        model: Optional[CryptoDepositAddressInput] = getattr(request, "validated_model", None)
        if model is None:
            return routes._error_response("Invalid deposit request", status=400, code="invalid_payload")

        try:
            result = node.crypto_deposit_manager.generate_deposit_address(
                user_address=model.user_address, currency=model.currency
            )
            return routes._success_response(result if isinstance(result, dict) else {"result": result})
        except ValueError as exc:
            logger.warning(
                "ValueError in generate_crypto_deposit_address",
                error_type="ValueError",
                error=str(exc),
                function="generate_crypto_deposit_address",
            )
            return routes._error_response(str(exc), status=400, code="deposit_invalid")
        except (OSError, IOError) as exc:
            logger.error(
                "Storage error generating deposit address: %s",
                str(exc),
                extra={
                    "event": "api.deposit_storage_error",
                    "user_address": model.user_address,
                    "currency": model.currency,
                },
                exc_info=True,
            )
            return routes._error_response("Storage error", status=500, code="storage_error")
        except RuntimeError as exc:
            return routes._handle_exception(exc, "crypto_generate_address")

    @app.route("/exchange/crypto/addresses/<address>", methods=["GET"])
    def get_crypto_deposit_addresses(address: str) -> Tuple[Dict[str, Any], int]:
        """Get all crypto deposit addresses for user.

        Retrieves all deposit addresses (BTC/ETH/USDT) associated with the
        specified XAI address.

        Path Parameters:
            address (str): The XAI blockchain address

        Returns:
            Tuple containing (response_dict, http_status_code) where:
                - response_dict: List of deposit addresses with metadata
                - http_status_code: 200 on success, 500/503 on error
        """
        if not node.crypto_deposit_manager:
            return jsonify({"success": False, "error": "Crypto deposit module disabled"}), 503
        try:
            result = node.crypto_deposit_manager.get_user_deposit_addresses(address)
            return jsonify(result), 200
        except (ValueError, KeyError) as e:
            logger.error(
                "Invalid deposit address lookup: %s",
                str(e),
                extra={"event": "api.deposit_address_invalid", "address": address},
                exc_info=True,
            )
            return jsonify({"error": f"Invalid request: {e}"}), 400
        except (OSError, IOError) as e:
            logger.error(
                "Storage error reading deposit addresses: %s",
                str(e),
                extra={"event": "api.deposit_address_storage_error", "address": address},
                exc_info=True,
            )
            return jsonify({"error": "Storage error"}), 500
        except RuntimeError as e:
            logger.error(
                "Runtime error reading deposit addresses: %s",
                str(e),
                extra={"event": "api.deposit_address_runtime_error", "address": address},
                exc_info=True,
            )
            return jsonify({"error": str(e)}), 500

    @app.route("/exchange/crypto/pending-deposits", methods=["GET"])
    def get_pending_crypto_deposits() -> Tuple[Dict[str, Any], int]:
        """Get pending crypto deposits.

        Returns all pending (unconfirmed) deposits, optionally filtered by user.

        Query Parameters:
            user_address (str, optional): Filter by XAI address

        Returns:
            Tuple containing (response_dict, http_status_code) where:
                - response_dict: Contains pending_deposits list and count
                - http_status_code: 200 on success, 500/503 on error
        """
        if not node.crypto_deposit_manager:
            return jsonify({"success": False, "error": "Crypto deposit module disabled"}), 503
        try:
            user_address = request.args.get("user_address")
            pending = node.crypto_deposit_manager.get_pending_deposits(user_address)
            return (
                jsonify({"success": True, "pending_deposits": pending, "count": len(pending)}),
                200,
            )
        except (ValueError, KeyError) as e:
            logger.error(
                "Invalid pending deposits request: %s",
                str(e),
                extra={"event": "api.pending_deposits_invalid", "user_address": user_address},
                exc_info=True,
            )
            return jsonify({"error": f"Invalid request: {e}"}), 400
        except (OSError, IOError) as e:
            logger.error(
                "Storage error reading pending deposits: %s",
                str(e),
                extra={"event": "api.pending_deposits_storage_error"},
                exc_info=True,
            )
            return jsonify({"error": "Storage error"}), 500
        except RuntimeError as e:
            logger.error(
                "Runtime error reading pending deposits: %s",
                str(e),
                extra={"event": "api.pending_deposits_runtime_error"},
                exc_info=True,
            )
            return jsonify({"error": str(e)}), 500

    @app.route("/exchange/crypto/deposit-history/<address>", methods=["GET"])
    def get_crypto_deposit_history(address: str) -> Tuple[Dict[str, Any], int]:
        """Get confirmed crypto deposit history for user.

        Retrieves all confirmed deposits for the specified XAI address.

        Path Parameters:
            address (str): The XAI blockchain address

        Query Parameters:
            limit (int, optional): Maximum deposits to return (default: 50)

        Returns:
            Tuple containing (response_dict, http_status_code) where:
                - response_dict: Contains address, deposits list, and count
                - http_status_code: 200 on success, 500/503 on error
        """
        if not node.crypto_deposit_manager:
            return jsonify({"success": False, "error": "Crypto deposit module disabled"}), 503
        try:
            limit = int(request.args.get("limit", 50))
            history = node.crypto_deposit_manager.get_deposit_history(address, limit)
            return (
                jsonify(
                    {
                        "success": True,
                        "address": address,
                        "deposits": history,
                        "count": len(history),
                    }
                ),
                200,
            )
        except (ValueError, TypeError) as e:
            logger.error(
                "Invalid deposit history request: %s",
                str(e),
                extra={"event": "api.deposit_history_invalid", "address": address},
                exc_info=True,
            )
            return jsonify({"error": f"Invalid request: {e}"}), 400
        except (OSError, IOError) as e:
            logger.error(
                "Storage error reading deposit history: %s",
                str(e),
                extra={"event": "api.deposit_history_storage_error", "address": address},
                exc_info=True,
            )
            return jsonify({"error": "Storage error"}), 500
        except RuntimeError as e:
            logger.error(
                "Runtime error reading deposit history: %s",
                str(e),
                extra={"event": "api.deposit_history_runtime_error", "address": address},
                exc_info=True,
            )
            return jsonify({"error": str(e)}), 500

    @app.route("/exchange/crypto/stats", methods=["GET"])
    def get_crypto_deposit_stats() -> Tuple[Dict[str, Any], int]:
        """Get crypto deposit system statistics.

        Returns system-wide statistics for all deposit operations including
        total deposits, pending count, and currency breakdown.

        Returns:
            Tuple containing (response_dict, http_status_code) where:
                - response_dict: Contains success flag and stats object
                - http_status_code: 200 on success, 500/503 on error
        """
        if not node.crypto_deposit_manager:
            return jsonify({"success": False, "error": "Crypto deposit module disabled"}), 503
        try:
            stats = node.crypto_deposit_manager.get_stats()
            return jsonify({"success": True, "stats": stats}), 200
        except (ValueError, KeyError) as e:
            logger.error(
                "Invalid deposit stats request: %s",
                str(e),
                extra={"event": "api.deposit_stats_invalid"},
                exc_info=True,
            )
            return jsonify({"error": f"Invalid request: {e}"}), 400
        except (OSError, IOError) as e:
            logger.error(
                "Storage error reading deposit stats: %s",
                str(e),
                extra={"event": "api.deposit_stats_storage_error"},
                exc_info=True,
            )
            return jsonify({"error": "Storage error"}), 500
        except RuntimeError as e:
            logger.error(
                "Runtime error reading deposit stats: %s",
                str(e),
                extra={"event": "api.deposit_stats_runtime_error"},
                exc_info=True,
            )
            return jsonify({"error": str(e)}), 500
