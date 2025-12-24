"""Exchange wallet and balance management API routes.

This module provides REST API endpoints for managing exchange wallet balances,
deposits, withdrawals, and transaction history.

Endpoints:
- POST /exchange/deposit - Deposit funds to exchange wallet
- POST /exchange/withdraw - Withdraw funds from exchange wallet
- GET /exchange/balance/<address> - Get all balances for user
- GET /exchange/balance/<address>/<currency> - Get specific currency balance
- GET /exchange/transactions/<address> - Get transaction history
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from flask import jsonify, request

from xai.core.input_validation_schemas import ExchangeTransferInput
from xai.core.request_validator_middleware import validate_request

if TYPE_CHECKING:
    from xai.core.node_api import NodeAPIRoutes

logger = logging.getLogger(__name__)


def register_exchange_wallet_routes(routes: "NodeAPIRoutes") -> None:
    """Register exchange wallet management endpoints."""
    app = routes.app
    node = routes.node

    @app.route("/exchange/deposit", methods=["POST"])
    @validate_request(routes.request_validator, ExchangeTransferInput)
    def deposit_funds() -> tuple[dict[str, Any], int]:
        """Deposit funds to exchange wallet (admin only).

        Credits user's exchange balance with specified currency and amount.
        Used for both manual deposits and automated deposit processing.

        This endpoint requires API authentication.

        Request Body (ExchangeTransferInput):
            {
                "to_address": "user address",
                "currency": "XAI" | "USD" | etc,
                "amount": float,
                "deposit_type": "manual" | "credit_card" (optional),
                "tx_hash": "transaction hash" (optional)
            }

        Returns:
            Tuple containing (response_dict, http_status_code) where:
                - response_dict: Deposit confirmation
                - http_status_code: 200 on success, 400/401/503 on error

        Raises:
            AuthenticationError: If API key is missing or invalid (401).
            ServiceUnavailable: If exchange module is disabled (503).
            ValidationError: If deposit data is invalid (400).
        """
        if not node.exchange_wallet_manager:
            return routes._error_response(
                "Exchange module disabled", status=503, code="module_disabled"
            )
        auth_error = routes._require_api_auth()
        if auth_error:
            return auth_error

        try:
            model = getattr(request, "validated_model", None)
            if model is None:
                return routes._error_response("Invalid deposit payload", status=400, code="invalid_payload")
            result = node.exchange_wallet_manager.deposit(
                user_address=model.to_address,
                currency=model.currency,
                amount=float(model.amount),
                deposit_type=request.json.get("deposit_type", "manual"),
                tx_hash=request.json.get("tx_hash"),
            )
            return routes._success_response(result if isinstance(result, dict) else {"result": result})
        except ValueError as exc:
            logger.warning(
                "ValueError in deposit_funds",
                extra={
                    "error_type": "ValueError",
                    "error": str(exc),
                    "function": "deposit_funds"
                }
            )
            return routes._error_response(str(exc), status=400, code="deposit_invalid")
        except (RuntimeError, OSError, json.JSONDecodeError) as exc:
            return routes._handle_exception(exc, "exchange_deposit")

    @app.route("/exchange/withdraw", methods=["POST"])
    @validate_request(routes.request_validator, ExchangeTransferInput)
    def withdraw_funds() -> tuple[dict[str, Any], int]:
        """Withdraw funds from exchange wallet (admin only).

        Debits user's exchange balance and initiates withdrawal to destination address.
        Includes fraud checks and withdrawal limits.

        This endpoint requires API authentication.

        Request Body (ExchangeTransferInput):
            {
                "from_address": "user address",
                "destination": "withdrawal destination address",
                "currency": "XAI" | "USD" | etc,
                "amount": float
            }

        Returns:
            Tuple containing (response_dict, http_status_code) where:
                - response_dict: Withdrawal confirmation
                - http_status_code: 200 on success, 400/401/503 on error

        Raises:
            AuthenticationError: If API key is missing or invalid (401).
            ServiceUnavailable: If exchange module is disabled (503).
            ValidationError: If withdrawal data is invalid or insufficient balance (400).
        """
        if not node.exchange_wallet_manager:
            return routes._error_response(
                "Exchange module disabled", status=503, code="module_disabled"
            )
        auth_error = routes._require_api_auth()
        if auth_error:
            return auth_error

        try:
            model = getattr(request, "validated_model", None)
            if model is None or not (model.destination or model.to_address):
                return routes._error_response("Invalid withdraw payload", status=400, code="invalid_payload")
            result = node.exchange_wallet_manager.withdraw(
                user_address=model.from_address,
                currency=model.currency,
                amount=float(model.amount),
                destination=model.destination or model.to_address,
            )
            return routes._success_response(result if isinstance(result, dict) else {"result": result})
        except ValueError as exc:
            logger.warning(
                "ValueError in withdraw_funds",
                extra={
                    "error_type": "ValueError",
                    "error": str(exc),
                    "function": "withdraw_funds"
                }
            )
            return routes._error_response(str(exc), status=400, code="withdraw_invalid")
        except (RuntimeError, OSError, json.JSONDecodeError) as exc:
            return routes._handle_exception(exc, "exchange_withdraw")

    @app.route("/exchange/balance/<address>", methods=["GET"])
    def get_user_balance(address: str) -> tuple[dict[str, Any], int]:
        """Get all exchange balances for a user.

        Returns all currency balances (available and locked) for the specified address.

        Path Parameters:
            address (str): The user's blockchain address

        Returns:
            Tuple containing (response_dict, http_status_code) where:
                - response_dict: Contains address and balances object
                - http_status_code: 200 on success, 500/503 on error

        Response balances include:
            - available_balances: Currencies and amounts available for trading
            - locked_balances: Currencies and amounts locked in open orders

        Raises:
            ServiceUnavailable: If exchange module is disabled (503).
        """
        if not node.exchange_wallet_manager:
            return jsonify({"success": False, "error": "Exchange module disabled"}), 503
        try:
            balances = node.exchange_wallet_manager.get_all_balances(address)
            return jsonify({"success": True, "address": address, "balances": balances}), 200
        except (RuntimeError, OSError, json.JSONDecodeError, ValueError) as exc:
            return jsonify({"error": str(exc)}), 500

    @app.route("/exchange/balance/<address>/<currency>", methods=["GET"])
    def get_currency_balance(address: str, currency: str) -> tuple[dict[str, Any], int]:
        """Get specific currency balance for a user.

        Returns available and locked balance for a single currency.

        Path Parameters:
            address (str): The user's blockchain address
            currency (str): The currency code (e.g., "XAI", "USD")

        Returns:
            Tuple containing (response_dict, http_status_code) where:
                - response_dict: Contains address, available, and locked amounts
                - http_status_code: 200 on success, 500/503 on error

        Raises:
            ServiceUnavailable: If exchange module is disabled (503).
        """
        if not node.exchange_wallet_manager:
            return jsonify({"success": False, "error": "Exchange module disabled"}), 503
        try:
            balance = node.exchange_wallet_manager.get_balance(address, currency)
            return jsonify({"success": True, "address": address, **balance}), 200
        except (RuntimeError, OSError, json.JSONDecodeError, ValueError) as exc:
            return jsonify({"error": str(exc)}), 500

    @app.route("/exchange/transactions/<address>", methods=["GET"])
    def get_transactions(address: str) -> tuple[dict[str, Any], int]:
        """Get transaction history for a user's exchange wallet.

        Returns deposit and withdrawal transaction history.

        Path Parameters:
            address (str): The user's blockchain address

        Query Parameters:
            limit (int, optional): Maximum transactions to return (default: 50)

        Returns:
            Tuple containing (response_dict, http_status_code) where:
                - response_dict: Contains address and transactions list
                - http_status_code: 200 on success, 500/503 on error

        Raises:
            ServiceUnavailable: If exchange module is disabled (503).
        """
        if not node.exchange_wallet_manager:
            return jsonify({"success": False, "error": "Exchange module disabled"}), 503
        try:
            limit = int(request.args.get("limit", 50))
            transactions = node.exchange_wallet_manager.get_transaction_history(address, limit)
            return jsonify({"success": True, "address": address, "transactions": transactions}), 200
        except (RuntimeError, OSError, json.JSONDecodeError, ValueError) as exc:
            return jsonify({"error": str(exc)}), 500
