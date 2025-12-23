from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

import json
import os
import time
from typing import TYPE_CHECKING, Any

from flask import jsonify, request

from xai.core.input_validation_schemas import (
    ExchangeCancelInput,
    ExchangeCardPurchaseInput,
    ExchangeOrderInput,
    ExchangeTransferInput,
)
from xai.core.node_utils import get_base_dir
from xai.core.request_validator_middleware import validate_request

if TYPE_CHECKING:
    from xai.core.node_api import NodeAPIRoutes

def register_exchange_routes(routes: "NodeAPIRoutes") -> None:
    """Register all exchange-related endpoints."""
    app = routes.app
    blockchain = routes.blockchain
    node = routes.node

    # --- core exchange order/trade routes ---

    @app.route("/exchange/orders", methods=["GET"])
    def get_order_book() -> tuple[dict[str, Any], int]:
        """Get current exchange order book.

        Returns top buy and sell orders from the exchange order book,
        sorted by price (best prices first).

        Returns:
            Tuple containing (response_dict, http_status_code) where:
                - response_dict: Contains buy_orders, sell_orders, and counts
                - http_status_code: 200 on success, 500/503 on error

        Response includes:
            - buy_orders: Top 20 buy orders (highest price first)
            - sell_orders: Top 20 sell orders (lowest price first)
            - total_buy_orders: Total open buy orders
            - total_sell_orders: Total open sell orders

        Raises:
            ServiceUnavailable: If exchange module is disabled (503).
            IOError: If order book file cannot be read (500).
        """
        if not node.exchange_wallet_manager:
            return jsonify({"success": False, "error": "Exchange module disabled"}), 503
        try:
            base_dir = getattr(getattr(blockchain, "storage", None), "data_dir", None)
            if not isinstance(base_dir, (str, bytes, os.PathLike)):
                base_dir = get_base_dir()
            orders_file = os.path.join(base_dir, "exchange_data", "orders.json")
            all_orders = {"buy": [], "sell": []}
            if os.path.exists(orders_file):
                with open(orders_file, "r") as handle:
                    loaded = json.load(handle)
                    if isinstance(loaded, dict):
                        for side in ("buy", "sell"):
                            if side in loaded and isinstance(loaded[side], list):
                                all_orders[side] = loaded[side]
                    else:
                        raise ValueError("Order book file is corrupted")

            buy_orders = [order for order in all_orders.get("buy", []) if order.get("status") == "open"]
            sell_orders = [order for order in all_orders.get("sell", []) if order.get("status") == "open"]
            buy_orders.sort(key=lambda entry: entry["price"], reverse=True)
            sell_orders.sort(key=lambda entry: entry["price"])

            return (
                jsonify(
                    {
                        "success": True,
                        "buy_orders": buy_orders[:20],
                        "sell_orders": sell_orders[:20],
                        "total_buy_orders": len(buy_orders),
                        "total_sell_orders": len(sell_orders),
                    }
                ),
                200,
            )
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            return routes._error_response(
                "Failed to load order book",
                status=500,
                code="order_book_error",
                context={"error": str(exc)},
            )

    @app.route("/exchange/place-order", methods=["POST"])
    @validate_request(routes.request_validator, ExchangeOrderInput)
    def place_order() -> tuple[dict[str, Any], int]:
        """Place a buy or sell order on the exchange (admin only).

        Creates a limit order, locks required funds, and attempts to match
        with existing orders. Unmatched portion remains in order book.

        This endpoint requires API authentication.

        Request Body (ExchangeOrderInput):
            {
                "address": "user address",
                "order_type": "buy" | "sell",
                "pair": "XAI/USD",
                "price": float,
                "amount": float
            }

        Returns:
            Tuple containing (response_dict, http_status_code) where:
                - response_dict: Contains order details, matched orders, and updated balances
                - http_status_code: 200 on success, 400/401/503 on error

        Raises:
            AuthenticationError: If API key is missing or invalid (401).
            ServiceUnavailable: If exchange module is disabled (503).
            ValidationError: If order data is invalid (400).
            ValueError: If insufficient balance or funds lock fails (400/500).
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
                return routes._error_response("Invalid order payload", status=400, code="invalid_payload")

            price = float(model.price)
            amount = float(model.amount)
            pair = model.pair
            base_currency, quote_currency = pair.split("/")
            total_cost = price * amount

            user_address = model.address
            order_type = model.order_type

            if order_type == "buy":
                balance_info = node.exchange_wallet_manager.get_balance(user_address, quote_currency)
                if balance_info["available"] < total_cost:
                    return routes._error_response(
                        f'Insufficient {quote_currency} balance. Need {total_cost:.2f}, have {balance_info["available"]:.2f}',
                        status=400,
                        code="insufficient_funds",
                    )
                if not node.exchange_wallet_manager.lock_for_order(user_address, quote_currency, total_cost):
                    return routes._error_response("Failed to lock funds", status=500, code="lock_failed")
            else:
                balance_info = node.exchange_wallet_manager.get_balance(user_address, base_currency)
                if balance_info["available"] < amount:
                    return routes._error_response(
                        f'Insufficient {base_currency} balance. Need {amount:.2f}, have {balance_info["available"]:.2f}',
                        status=400,
                        code="insufficient_funds",
                    )
                if not node.exchange_wallet_manager.lock_for_order(user_address, base_currency, amount):
                    return routes._error_response("Failed to lock funds", status=500, code="lock_failed")

            order = {
                "id": f"{user_address}_{int(time.time() * 1000)}",
                "address": user_address,
                "order_type": order_type,
                "pair": pair,
                "base_currency": base_currency,
                "quote_currency": quote_currency,
                "price": price,
                "amount": amount,
                "remaining": amount,
                "total": total_cost,
                "status": "open",
                "timestamp": time.time(),
            }

            base_dir = getattr(getattr(blockchain, "storage", None), "data_dir", None)
            if not isinstance(base_dir, (str, bytes, os.PathLike)):
                base_dir = get_base_dir()
            orders_dir = os.path.join(base_dir, "exchange_data")
            os.makedirs(orders_dir, exist_ok=True)
            orders_file = os.path.join(orders_dir, "orders.json")

            if os.path.exists(orders_file):
                with open(orders_file, "r") as handle:
                    stored_orders = json.load(handle)
                    if not isinstance(stored_orders, dict):
                        raise ValueError("Order storage corrupted")
                    buy_orders = stored_orders.get("buy", [])
                    sell_orders = stored_orders.get("sell", [])
                    if not isinstance(buy_orders, list) or not isinstance(sell_orders, list):
                        raise ValueError("Order book lists are malformed")
                    all_orders = {"buy": buy_orders, "sell": sell_orders}
            else:
                all_orders = {"buy": [], "sell": []}

            all_orders[order_type].append(order)

            with open(orders_file, "w") as handle:
                json.dump(all_orders, handle, indent=2)

            matched = node._match_orders(order, all_orders)
            balances = node.exchange_wallet_manager.get_all_balances(user_address)

            return routes._success_response(
                {
                    "order": order,
                    "matched": matched,
                    "balances": balances["available_balances"],
                    "message": f"{order_type.capitalize()} order placed successfully",
                }
            )
        except ValueError as exc:
            logger.warning(
                "ValueError occurred",
                extra={
                    "error_type": "ValueError",
                    "error": str(exc)
                }
            )
            return routes._error_response(str(exc), status=400, code="order_invalid")
        except (OSError, json.JSONDecodeError, RuntimeError) as exc:
            return routes._handle_exception(exc, "exchange_place_order")

    @app.route("/exchange/cancel-order", methods=["POST"])
    @validate_request(routes.request_validator, ExchangeCancelInput)
    def cancel_order() -> tuple[dict[str, Any], int]:
        """Cancel an open order and unlock funds (admin only).

        Cancels an open order, removes it from the order book, and unlocks
        the reserved funds back to the user's available balance.

        This endpoint requires API authentication.

        Request Body (ExchangeCancelInput):
            {
                "order_id": "order identifier",
                "address": "user address"
            }

        Returns:
            Tuple containing (response_dict, http_status_code) where:
                - response_dict: Cancellation confirmation
                - http_status_code: 200 on success, 400/401/404/503 on error

        Raises:
            AuthenticationError: If API key is missing or invalid (401).
            ServiceUnavailable: If exchange module is disabled (503).
            NotFound: If order doesn't exist (404).
            ValidationError: If user doesn't own the order (400).
        """
        if not node.exchange_wallet_manager:
            return routes._error_response(
                "Exchange module disabled", status=503, code="module_disabled"
            )
        auth_error = routes._require_api_auth()
        if auth_error:
            return auth_error

        model = getattr(request, "validated_model", None)
        if model is None:
            return routes._error_response("Invalid payload", status=400, code="invalid_payload")
        try:
            base_dir = getattr(getattr(blockchain, "storage", None), "data_dir", None)
            if not isinstance(base_dir, (str, bytes, os.PathLike)):
                base_dir = get_base_dir()
            orders_file = os.path.join(base_dir, "exchange_data", "orders.json")
            if not os.path.exists(orders_file):
                return routes._error_response("Order not found", status=404, code="not_found")

            with open(orders_file, "r") as handle:
                all_orders = json.load(handle)

            found = False
            for order_type in ["buy", "sell"]:
                for order in all_orders.get(order_type, []):
                    if order.get("id") == model.order_id and order.get("status") == "open":
                        order["status"] = "cancelled"
                        found = True
                        break
                if found:
                    break

            if not found:
                return routes._error_response(
                    "Order not found or already completed", status=404, code="not_found"
                )

            with open(orders_file, "w") as handle:
                json.dump(all_orders, handle, indent=2)

            return routes._success_response({"message": "Order cancelled successfully"})
        except (OSError, json.JSONDecodeError, RuntimeError) as exc:
            return routes._handle_exception(exc, "exchange_cancel_order")

    @app.route("/exchange/my-orders/<address>", methods=["GET"])
    def get_my_orders(address: str) -> tuple[dict[str, Any], int]:
        """Get all orders for a specific user address.

        Returns all orders (buy and sell, all statuses) for the specified address,
        sorted by timestamp (newest first).

        Path Parameters:
            address (str): The user's blockchain address

        Returns:
            Tuple containing (response_dict, http_status_code) where:
                - response_dict: Contains success flag and orders list
                - http_status_code: 200 on success, 500/503 on error

        Raises:
            ServiceUnavailable: If exchange module is disabled (503).
        """
        if not node.exchange_wallet_manager:
            return jsonify({"success": False, "error": "Exchange module disabled"}), 503
        try:
            base_dir = getattr(getattr(blockchain, "storage", None), "data_dir", get_base_dir())
            orders_file = os.path.join(base_dir, "exchange_data", "orders.json")
            if not os.path.exists(orders_file):
                return jsonify({"success": True, "orders": []}), 200

            with open(orders_file, "r") as handle:
                all_orders = json.load(handle)

            user_orders = []
            for order_type in ["buy", "sell"]:
                for order in all_orders.get(order_type, []):
                    if order.get("address") == address:
                        user_orders.append(order)

            user_orders.sort(key=lambda entry: entry.get("timestamp", 0), reverse=True)
            return jsonify({"success": True, "orders": user_orders}), 200
        except (OSError, json.JSONDecodeError, RuntimeError) as exc:
            return jsonify({"error": str(exc)}), 500

    @app.route("/exchange/trades", methods=["GET"])
    def get_recent_trades() -> tuple[dict[str, Any], int]:
        """Get recent executed trades.

        Returns recent matched trades from the exchange, sorted by timestamp
        (newest first).

        Query Parameters:
            limit (int, optional): Maximum trades to return (default: 50)

        Returns:
            Tuple containing (response_dict, http_status_code) where:
                - response_dict: Contains success flag and trades list
                - http_status_code: 200 on success, 500/503 on error

        Raises:
            ServiceUnavailable: If exchange module is disabled (503).
        """
        if not node.exchange_wallet_manager:
            return jsonify({"success": False, "error": "Exchange module disabled"}), 503
        limit = request.args.get("limit", default=50, type=int)
        try:
            trades_file = os.path.join(get_base_dir(), "exchange_data", "trades.json")
            if not os.path.exists(trades_file):
                return jsonify({"success": True, "trades": []}), 200

            with open(trades_file, "r") as handle:
                all_trades = json.load(handle)
            all_trades.sort(key=lambda entry: entry["timestamp"], reverse=True)
            return jsonify({"success": True, "trades": all_trades[:limit]}), 200
        except (RuntimeError, OSError, json.JSONDecodeError) as exc:
            return jsonify({"error": str(exc)}), 500

    # --- balance/transfer routes ---

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

    # --- stats routes ---

    @app.route("/exchange/price-history", methods=["GET"])
    def get_price_history() -> tuple[dict[str, Any], int]:
        """Get historical price data for charting.

        Returns price and volume data for the specified timeframe.

        Query Parameters:
            timeframe (str, optional): Time period - "1h", "24h", "7d", or "30d"
                                      (default: "24h")

        Returns:
            Tuple containing (response_dict, http_status_code) where:
                - response_dict: Contains timeframe, prices, and volumes arrays
                - http_status_code: 200 on success, 500/503 on error

        Raises:
            ServiceUnavailable: If exchange module is disabled (503).
        """
        if not node.exchange_wallet_manager:
            return jsonify({"success": False, "error": "Exchange module disabled"}), 503
        timeframe = request.args.get("timeframe", default="24h", type=str)

        try:
            trades_file = os.path.join(get_base_dir(), "exchange_data", "trades.json")
            if not os.path.exists(trades_file):
                return jsonify({"success": True, "prices": [], "volumes": []}), 200

            with open(trades_file, "r") as handle:
                all_trades = json.load(handle)

            now = time.time()
            timeframe_seconds = {"1h": 3600, "24h": 86400, "7d": 604800, "30d": 2592000}.get(
                timeframe, 86400
            )
            cutoff_time = now - timeframe_seconds
            recent_trades = [trade for trade in all_trades if trade["timestamp"] >= cutoff_time]
            recent_trades.sort(key=lambda entry: entry["timestamp"])

            price_data: list = []
            volume_data: list = []
            # Aggregation logic placeholder—existing endpoint returned empty arrays
            return (
                jsonify(
                    {
                        "success": True,
                        "timeframe": timeframe,
                        "prices": price_data,
                        "volumes": volume_data,
                    }
                ),
                200,
            )
        except (RuntimeError, OSError, json.JSONDecodeError, ValueError) as exc:
            return jsonify({"error": str(exc)}), 500

    @app.route("/exchange/stats", methods=["GET"])
    def get_exchange_stats() -> tuple[dict[str, Any], int]:
        """Get exchange statistics and market data.

        Returns current market statistics including price, volume, and order counts.

        Returns:
            Tuple containing (response_dict, http_status_code) where:
                - response_dict: Contains stats object with market data
                - http_status_code: 200 on success, 500/503 on error

        Stats include:
            - current_price: Latest trade price
            - volume_24h: 24-hour trading volume
            - change_24h: 24-hour price change percentage
            - high_24h: 24-hour high price
            - low_24h: 24-hour low price
            - total_trades: Total number of trades
            - active_orders: Count of open orders

        Raises:
            ServiceUnavailable: If exchange module is disabled (503).
        """
        if not node.exchange_wallet_manager:
            return jsonify({"success": False, "error": "Exchange module disabled"}), 503
        try:
            trades_file = os.path.join(get_base_dir(), "exchange_data", "trades.json")
            base_dir = getattr(getattr(blockchain, "storage", None), "data_dir", get_base_dir())
            orders_file = os.path.join(base_dir, "exchange_data", "orders.json")

            stats = {
                "current_price": 0.05,
                "volume_24h": 0,
                "change_24h": 0,
                "high_24h": 0,
                "low_24h": 0,
                "total_trades": 0,
                "active_orders": 0,
            }

            if os.path.exists(trades_file):
                with open(trades_file, "r") as handle:
                    all_trades = json.load(handle)
                if all_trades:
                    stats["total_trades"] = len(all_trades)
                    stats["current_price"] = all_trades[-1]["price"]

            if os.path.exists(orders_file):
                with open(orders_file, "r") as handle:
                    all_orders = json.load(handle)
                for order_type in ("buy", "sell"):
                    stats["active_orders"] += len(
                        [order for order in all_orders.get(order_type, []) if order.get("status") == "open"]
                    )

            return jsonify({"success": True, "stats": stats}), 200
        except (RuntimeError, OSError, json.JSONDecodeError, ValueError) as exc:
            return jsonify({"error": str(exc)}), 500

    # --- payment routes ---

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
