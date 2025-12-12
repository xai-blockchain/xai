from __future__ import annotations

import json
import os
import time
from typing import TYPE_CHECKING, Dict, Tuple, Optional, Any

from flask import jsonify, request

from xai.core.request_validator_middleware import validate_request
from xai.core.input_validation_schemas import (
    ExchangeOrderInput,
    ExchangeTransferInput,
    ExchangeCancelInput,
    ExchangeCardPurchaseInput,
)
from xai.core.node_utils import get_base_dir

if TYPE_CHECKING:
    from xai.core.node_api import NodeAPIRoutes


def register_exchange_routes(routes: "NodeAPIRoutes") -> None:
    """Register all exchange-related endpoints."""
    app = routes.app
    blockchain = routes.blockchain
    node = routes.node

    # --- core exchange order/trade routes ---

    @app.route("/exchange/orders", methods=["GET"])
    def get_order_book() -> Tuple[Dict[str, Any], int]:
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
    def place_order() -> Tuple[Dict[str, Any], int]:
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
            return routes._error_response(str(exc), status=400, code="order_invalid")
        except (OSError, json.JSONDecodeError, RuntimeError) as exc:
            return routes._handle_exception(exc, "exchange_place_order")

    @app.route("/exchange/cancel-order", methods=["POST"])
    @validate_request(routes.request_validator, ExchangeCancelInput)
    def cancel_order() -> Tuple[Dict[str, Any], int]:
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
    def get_my_orders(address: str) -> Tuple[Dict[str, Any], int]:
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
    def get_recent_trades() -> Tuple[Dict[str, Any], int]:
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
    def deposit_funds() -> Tuple[Dict[str, Any], int]:
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
            return routes._error_response(str(exc), status=400, code="deposit_invalid")
        except (RuntimeError, OSError, json.JSONDecodeError) as exc:
            return routes._handle_exception(exc, "exchange_deposit")

    @app.route("/exchange/withdraw", methods=["POST"])
    @validate_request(routes.request_validator, ExchangeTransferInput)
    def withdraw_funds() -> Tuple[Dict[str, Any], int]:
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
            return routes._error_response(str(exc), status=400, code="withdraw_invalid")
        except (RuntimeError, OSError, json.JSONDecodeError) as exc:
            return routes._handle_exception(exc, "exchange_withdraw")

    @app.route("/exchange/balance/<address>", methods=["GET"])
    def get_user_balance(address: str) -> Tuple[Dict[str, Any], int]:
        if not node.exchange_wallet_manager:
            return jsonify({"success": False, "error": "Exchange module disabled"}), 503
        try:
            balances = node.exchange_wallet_manager.get_all_balances(address)
            return jsonify({"success": True, "address": address, "balances": balances}), 200
        except (RuntimeError, OSError, json.JSONDecodeError, ValueError) as exc:
            return jsonify({"error": str(exc)}), 500

    @app.route("/exchange/balance/<address>/<currency>", methods=["GET"])
    def get_currency_balance(address: str, currency: str) -> Tuple[Dict[str, Any], int]:
        if not node.exchange_wallet_manager:
            return jsonify({"success": False, "error": "Exchange module disabled"}), 503
        try:
            balance = node.exchange_wallet_manager.get_balance(address, currency)
            return jsonify({"success": True, "address": address, **balance}), 200
        except (RuntimeError, OSError, json.JSONDecodeError, ValueError) as exc:
            return jsonify({"error": str(exc)}), 500

    @app.route("/exchange/transactions/<address>", methods=["GET"])
    def get_transactions(address: str) -> Tuple[Dict[str, Any], int]:
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
    def get_price_history() -> Tuple[Dict[str, Any], int]:
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
    def get_exchange_stats() -> Tuple[Dict[str, Any], int]:
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
    def buy_with_card() -> Tuple[Dict[str, Any], int]:
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
            return routes._error_response(str(exc), status=400, code="payment_invalid")
        except (RuntimeError, KeyError, TypeError) as exc:
            return routes._handle_exception(exc, "exchange_buy_with_card")

    @app.route("/exchange/payment-methods", methods=["GET"])
    def get_payment_methods() -> Tuple[Dict[str, Any], int]:
        if not node.payment_processor:
            return jsonify({"success": False, "error": "Payment module disabled"}), 503
        try:
            methods = node.payment_processor.get_supported_payment_methods()
            return jsonify({"success": True, "methods": methods}), 200
        except (RuntimeError, ValueError, KeyError, TypeError) as exc:
            return routes._handle_exception(exc, "exchange_payment_methods")

    @app.route("/exchange/calculate-purchase", methods=["POST"])
    def calculate_purchase() -> Tuple[Dict[str, Any], int]:
        if not node.payment_processor:
            return jsonify({"success": False, "error": "Payment module disabled"}), 503
        data = request.get_json(silent=True) or {}
        if "usd_amount" not in data:
            return jsonify({"error": "Missing usd_amount"}), 400

        try:
            calc = node.payment_processor.calculate_purchase(data["usd_amount"])
            return jsonify(calc), 200
        except ValueError as exc:
            return routes._error_response(str(exc), status=400, code="payment_invalid")
        except (RuntimeError, KeyError, TypeError) as exc:
            return routes._handle_exception(exc, "exchange_calculate_purchase")
