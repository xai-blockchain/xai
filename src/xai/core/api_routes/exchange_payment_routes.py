"""Exchange payment processing API routes.

This module provides REST API endpoints for credit card payments and
purchase calculations for token purchases on the exchange.

Endpoints:
- POST /exchange/buy-with-card - Purchase tokens with credit card
- GET /exchange/payment-methods - Get supported payment methods
- POST /exchange/calculate-purchase - Calculate token purchase amount
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from flask import jsonify, request

from xai.core.security.input_validation_schemas import ExchangeCardPurchaseInput
from xai.core.security.request_validator_middleware import validate_request

if TYPE_CHECKING:
    from xai.core.node_api import NodeAPIRoutes

logger = logging.getLogger(__name__)


def register_exchange_payment_routes(routes: "NodeAPIRoutes") -> None:
    """Register exchange payment processing endpoints."""
    app = routes.app
    node = routes.node

    @app.route("/exchange/buy-with-card", methods=["POST"])
    @validate_request(routes.request_validator, ExchangeCardPurchaseInput)
    def buy_with_card() -> tuple[dict[str, Any], int]:
        """Purchase tokens with credit card (admin only).

        Processes credit card payment and deposits purchased tokens to user's
        exchange wallet.

        This endpoint requires API authentication.

        Request Body (ExchangeCardPurchaseInput):
            {
                "from_address": "payer address",
                "to_address": "recipient address",
                "usd_amount": float,
                "payment_token": "stripe token or card ID",
                "email": "user email",
                "card_id": "card identifier" (optional),
                "user_id": "user identifier" (optional)
            }

        Returns:
            Tuple containing (response_dict, http_status_code) where:
                - response_dict: Contains payment and deposit confirmations
                - http_status_code: 200 on success, 400/401/503 on error

        Raises:
            AuthenticationError: If API key is missing or invalid (401).
            ServiceUnavailable: If payment or exchange module is disabled (503).
            ValidationError: If payment data is invalid (400).
            PaymentError: If card processing fails (400).
        """
        if not (node.payment_processor and node.exchange_wallet_manager):
            return routes._error_response(
                "Payment module disabled", status=503, code="module_disabled"
            )
        auth_error = routes._require_api_auth()
        if auth_error:
            return auth_error
        try:
            model = getattr(request, "validated_model", None)
            if model is None:
                return routes._error_response("Invalid payload", status=400, code="invalid_payload")

            calc = node.payment_processor.calculate_purchase(model.usd_amount)
            if not calc.get("success"):
                return jsonify(calc), 400

            payment_result = node.payment_processor.process_card_payment(
                user_address=model.from_address,
                usd_amount=model.usd_amount,
                card_token=model.payment_token or request.json.get("payment_token", "tok_test"),
                email=model.email,
                card_id=model.card_id,
                user_id=model.user_id,
            )
            if not payment_result.get("success"):
                return jsonify(payment_result), 400

            deposit_result = node.exchange_wallet_manager.deposit(
                user_address=model.to_address,
                currency="AXN",
                amount=payment_result["axn_amount"],
                deposit_type="credit_card",
                tx_hash=payment_result["payment_id"],
            )

            return routes._success_response(
                {
                    "payment": payment_result,
                    "deposit": deposit_result,
                    "message": f"Successfully purchased {payment_result['axn_amount']:.2f} AXN",
                }
            )
        except ValueError as exc:
            logger.warning(
                "ValueError in buy_with_card",
                extra={
                    "error_type": "ValueError",
                    "error": str(exc),
                    "function": "buy_with_card"
                }
            )
            return routes._error_response(str(exc), status=400, code="payment_invalid")
        except (RuntimeError, KeyError, TypeError) as exc:
            return routes._handle_exception(exc, "exchange_buy_with_card")

    @app.route("/exchange/payment-methods", methods=["GET"])
    def get_payment_methods() -> tuple[dict[str, Any], int]:
        """Get supported payment methods.

        Returns list of available payment methods for purchasing tokens.

        Returns:
            Tuple containing (response_dict, http_status_code) where:
                - response_dict: Contains success flag and methods list
                - http_status_code: 200 on success, 500/503 on error

        Raises:
            ServiceUnavailable: If payment module is disabled (503).
        """
        if not node.payment_processor:
            return jsonify({"success": False, "error": "Payment module disabled"}), 503
        try:
            methods = node.payment_processor.get_supported_payment_methods()
            return jsonify({"success": True, "methods": methods}), 200
        except (RuntimeError, ValueError, KeyError, TypeError) as exc:
            return routes._handle_exception(exc, "exchange_payment_methods")

    @app.route("/exchange/calculate-purchase", methods=["POST"])
    def calculate_purchase() -> tuple[dict[str, Any], int]:
        """Calculate token purchase amount and fees.

        Calculates how many tokens will be received for a USD amount,
        including fees and exchange rate.

        Request Body:
            {
                "usd_amount": float
            }

        Returns:
            Tuple containing (response_dict, http_status_code) where:
                - response_dict: Contains calculation breakdown
                - http_status_code: 200 on success, 400/500/503 on error

        Response includes:
            - success: Calculation succeeded
            - axn_amount: Tokens to be received
            - usd_amount: USD amount input
            - fee_amount: Processing fees
            - exchange_rate: Current rate

        Raises:
            ServiceUnavailable: If payment module is disabled (503).
            ValidationError: If usd_amount is missing or invalid (400).
        """
        if not node.payment_processor:
            return jsonify({"success": False, "error": "Payment module disabled"}), 503
        data = request.get_json(silent=True) or {}
        if "usd_amount" not in data:
            return jsonify({"error": "Missing usd_amount"}), 400

        try:
            calc = node.payment_processor.calculate_purchase(data["usd_amount"])
            return jsonify(calc), 200
        except ValueError as exc:
            logger.warning(
                "ValueError in calculate_purchase",
                extra={
                    "error_type": "ValueError",
                    "error": str(exc),
                    "function": "calculate_purchase"
                }
            )
            return routes._error_response(str(exc), status=400, code="payment_invalid")
        except (RuntimeError, KeyError, TypeError) as exc:
            return routes._handle_exception(exc, "exchange_calculate_purchase")
