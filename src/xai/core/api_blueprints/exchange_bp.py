"""
Exchange API Blueprint

Handles exchange-related endpoints: orders, trades, deposits, withdrawals.
Extracted from node_api.py as part of god class refactoring.

Note: This is a partial extraction containing the most commonly used endpoints.
Additional exchange routes remain in node_api.py for now.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Optional, Tuple

from flask import Blueprint, jsonify, request

from xai.core.api_blueprints.base import (
    error_response,
    get_blockchain,
    get_node,
    handle_exception,
    require_api_auth,
    success_response,
)
from xai.core.node_utils import get_base_dir

logger = logging.getLogger(__name__)

exchange_bp = Blueprint("exchange", __name__, url_prefix="/exchange")


@exchange_bp.route("/orders", methods=["GET"])
def get_order_book() -> Tuple[Dict[str, Any], int]:
    """Get current order book (buy and sell orders)."""
    node = get_node()
    blockchain = get_blockchain()

    if not node.exchange_wallet_manager:
        return jsonify({"success": False, "error": "Exchange module disabled"}), 503
    try:
        base_dir = getattr(getattr(blockchain, "storage", None), "data_dir", None)
        if not isinstance(base_dir, (str, bytes, os.PathLike)):
            base_dir = get_base_dir()
        orders_file = os.path.join(base_dir, "exchange_data", "orders.json")
        all_orders = {"buy": [], "sell": []}
        if os.path.exists(orders_file):
            with open(orders_file, "r") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    for book_side in ("buy", "sell"):
                        if book_side in loaded and isinstance(loaded[book_side], list):
                            all_orders[book_side] = loaded[book_side]
                else:
                    raise ValueError("Order book file is corrupted")

        # Filter only open orders
        buy_orders = [o for o in all_orders.get("buy", []) if o["status"] == "open"]
        sell_orders = [o for o in all_orders.get("sell", []) if o["status"] == "open"]

        # Sort orders
        buy_orders.sort(key=lambda x: x["price"], reverse=True)
        sell_orders.sort(key=lambda x: x["price"])

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
    except (ValueError, KeyError) as exc:
        logger.error(
            "Invalid order book data: %s",
            str(exc),
            extra={"event": "api.order_book_invalid_data"},
            exc_info=True,
        )
        return jsonify({"success": False, "error": "Invalid order book data"}), 500
    except (OSError, IOError) as exc:
        logger.error(
            "Storage error reading order book: %s",
            str(exc),
            extra={"event": "api.order_book_storage_error"},
            exc_info=True,
        )
        return jsonify({"success": False, "error": "Storage error"}), 500
    except RuntimeError as exc:
        logger.warning(
            "RuntimeError in get_order_book",
            extra={
                "error_type": "RuntimeError",
                "error": str(exc),
                "function": "get_order_book"
            }
        )
        return handle_exception(exc, "exchange_get_order_book")


@exchange_bp.route("/balance/<address>", methods=["GET"])
def get_exchange_balance(address: str) -> Tuple[Dict[str, Any], int]:
    """Get exchange balances for an address."""
    node = get_node()

    if not node.exchange_wallet_manager:
        return jsonify({"success": False, "error": "Exchange module disabled"}), 503

    try:
        balances = node.exchange_wallet_manager.get_all_balances(address)
        return jsonify({"success": True, "address": address, "balances": balances}), 200
    except (ValueError, KeyError) as exc:
        logger.error(
            "Invalid balance request: %s",
            str(exc),
            extra={"event": "api.balance_invalid_request", "address": address},
            exc_info=True,
        )
        return jsonify({"success": False, "error": f"Invalid request: {exc}"}), 400
    except (OSError, IOError) as exc:
        logger.error(
            "Storage error reading balance: %s",
            str(exc),
            extra={"event": "api.balance_storage_error", "address": address},
            exc_info=True,
        )
        return jsonify({"success": False, "error": "Storage error"}), 500
    except RuntimeError as exc:
        logger.warning(
            "RuntimeError in get_exchange_balance",
            extra={
                "error_type": "RuntimeError",
                "error": str(exc),
                "function": "get_exchange_balance"
            }
        )
        return handle_exception(exc, "exchange_get_balance")


@exchange_bp.route("/balance/<address>/<currency>", methods=["GET"])
def get_exchange_balance_currency(address: str, currency: str) -> Tuple[Dict[str, Any], int]:
    """Get exchange balance for a specific currency."""
    node = get_node()

    if not node.exchange_wallet_manager:
        return jsonify({"success": False, "error": "Exchange module disabled"}), 503

    try:
        balance = node.exchange_wallet_manager.get_balance(address, currency)
        return jsonify({"success": True, "address": address, "currency": currency, "balance": balance}), 200
    except (ValueError, KeyError) as exc:
        logger.error(
            "Invalid currency balance request: %s",
            str(exc),
            extra={"event": "api.currency_balance_invalid_request", "address": address, "currency": currency},
            exc_info=True,
        )
        return jsonify({"success": False, "error": f"Invalid request: {exc}"}), 400
    except (OSError, IOError) as exc:
        logger.error(
            "Storage error reading currency balance: %s",
            str(exc),
            extra={"event": "api.currency_balance_storage_error", "address": address, "currency": currency},
            exc_info=True,
        )
        return jsonify({"success": False, "error": "Storage error"}), 500
    except RuntimeError as exc:
        logger.warning(
            "RuntimeError in get_exchange_balance_currency",
            extra={
                "error_type": "RuntimeError",
                "error": str(exc),
                "function": "get_exchange_balance_currency"
            }
        )
        return handle_exception(exc, "exchange_get_balance_currency")


@exchange_bp.route("/stats", methods=["GET"])
def get_exchange_stats() -> Tuple[Dict[str, Any], int]:
    """Get exchange statistics."""
    node = get_node()
    blockchain = get_blockchain()

    if not node.exchange_wallet_manager:
        return jsonify({"success": False, "error": "Exchange module disabled"}), 503

    try:
        base_dir = getattr(getattr(blockchain, "storage", None), "data_dir", None)
        if not isinstance(base_dir, (str, bytes, os.PathLike)):
            base_dir = get_base_dir()

        # Load orders for stats
        orders_file = os.path.join(base_dir, "exchange_data", "orders.json")
        all_orders = {"buy": [], "sell": []}
        if os.path.exists(orders_file):
            with open(orders_file, "r") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    all_orders = loaded

        buy_orders = all_orders.get("buy", [])
        sell_orders = all_orders.get("sell", [])

        open_buys = len([o for o in buy_orders if o.get("status") == "open"])
        open_sells = len([o for o in sell_orders if o.get("status") == "open"])

        # Load trades for volume stats
        trades_file = os.path.join(base_dir, "exchange_data", "trades.json")
        trades = []
        if os.path.exists(trades_file):
            with open(trades_file, "r") as f:
                trades = json.load(f)

        total_volume = sum(float(t.get("amount", 0)) * float(t.get("price", 0)) for t in trades)

        return jsonify({
            "success": True,
            "stats": {
                "total_orders": len(buy_orders) + len(sell_orders),
                "open_buy_orders": open_buys,
                "open_sell_orders": open_sells,
                "total_trades": len(trades),
                "total_volume": total_volume,
            }
        }), 200
    except (ValueError, KeyError, TypeError) as exc:
        logger.error(
            "Invalid exchange stats data: %s",
            str(exc),
            extra={"event": "api.exchange_stats_invalid_data"},
            exc_info=True,
        )
        return jsonify({"success": False, "error": "Invalid exchange data"}), 500
    except (OSError, IOError) as exc:
        logger.error(
            "Storage error reading exchange stats: %s",
            str(exc),
            extra={"event": "api.exchange_stats_storage_error"},
            exc_info=True,
        )
        return jsonify({"success": False, "error": "Storage error"}), 500
    except RuntimeError as exc:
        logger.warning(
            "RuntimeError in get_exchange_stats",
            extra={
                "error_type": "RuntimeError",
                "error": str(exc),
                "function": "get_exchange_stats"
            }
        )
        return handle_exception(exc, "exchange_get_stats")
