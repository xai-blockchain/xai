#!/usr/bin/env python3
"""
XAI Trading Bot Example

A simple market-making trading bot demonstrating:
- Connecting to XAI node
- Fetching order book data
- Placing and canceling orders
- Basic spread trading strategy
- Error handling and recovery

IMPORTANT: This is an EXAMPLE for educational purposes only.
Do NOT use in production without proper testing, risk management,
and security hardening.

Usage:
    python trading_bot_example.py --node-url http://localhost:12001 --wallet YOUR_WALLET
"""

from __future__ import annotations

import argparse
import logging
import signal
import sys
import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@dataclass
class OrderBookEntry:
    """Represents a single order book entry."""
    price: Decimal
    amount: Decimal
    side: str  # "buy" or "sell"


@dataclass
class TradingConfig:
    """Trading bot configuration."""
    node_url: str
    wallet_address: str
    trading_pair: str = "XAI/USDT"
    spread_percent: Decimal = Decimal("0.5")  # 0.5% spread
    order_amount: Decimal = Decimal("10.0")  # Amount per order
    update_interval: int = 30  # Seconds between updates
    max_orders: int = 5  # Maximum open orders


class XAITradingClient:
    """Client for XAI exchange trading operations."""

    def __init__(self, node_url: str, api_key: str | None = None):
        self.node_url = node_url.rstrip("/")
        self.api_key = api_key
        self.session = requests.Session()
        if api_key:
            self.session.headers["X-API-Key"] = api_key

    def get_order_book(self, pair: str, depth: int = 20) -> dict[str, Any]:
        """Fetch order book for a trading pair."""
        resp = self.session.get(
            f"{self.node_url}/api/v1/exchange/orderbook/{pair}",
            params={"depth": depth},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    def get_balance(self, address: str) -> dict[str, Any]:
        """Get wallet balance."""
        resp = self.session.get(
            f"{self.node_url}/balance/{address}",
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    def place_order(
        self,
        pair: str,
        side: str,
        price: Decimal,
        amount: Decimal,
        wallet: str,
    ) -> dict[str, Any]:
        """Place a limit order."""
        resp = self.session.post(
            f"{self.node_url}/api/v1/exchange/orders",
            json={
                "pair": pair,
                "side": side,
                "type": "limit",
                "price": str(price),
                "amount": str(amount),
                "wallet": wallet,
            },
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    def cancel_order(self, order_id: str, wallet: str) -> dict[str, Any]:
        """Cancel an open order."""
        resp = self.session.delete(
            f"{self.node_url}/api/v1/exchange/orders/{order_id}",
            json={"wallet": wallet},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    def get_my_orders(self, wallet: str) -> dict[str, Any]:
        """Get open orders for wallet."""
        resp = self.session.get(
            f"{self.node_url}/api/v1/exchange/orders",
            params={"wallet": wallet, "status": "open"},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()


class SimpleTradingBot:
    """
    Simple spread trading bot example.

    Strategy:
    1. Fetch current mid-price from order book
    2. Place buy order below mid-price (by spread%)
    3. Place sell order above mid-price (by spread%)
    4. Cancel stale orders and repeat
    """

    def __init__(self, config: TradingConfig):
        self.config = config
        self.client = XAITradingClient(config.node_url)
        self.running = False
        self.order_ids: list[str] = []

    def get_mid_price(self) -> Decimal | None:
        """Calculate mid-price from order book."""
        try:
            book = self.client.get_order_book(self.config.trading_pair)
            bids = book.get("bids", [])
            asks = book.get("asks", [])

            if not bids or not asks:
                logger.warning("Order book is empty")
                return None

            best_bid = Decimal(str(bids[0]["price"]))
            best_ask = Decimal(str(asks[0]["price"]))

            return (best_bid + best_ask) / 2

        except Exception as e:
            logger.error("Failed to get order book: %s", e)
            return None

    def cancel_all_orders(self) -> None:
        """Cancel all bot's open orders."""
        for order_id in self.order_ids:
            try:
                self.client.cancel_order(order_id, self.config.wallet_address)
                logger.info("Cancelled order: %s", order_id)
            except Exception as e:
                logger.warning("Failed to cancel order %s: %s", order_id, e)
        self.order_ids.clear()

    def place_spread_orders(self, mid_price: Decimal) -> None:
        """Place buy and sell orders around mid-price."""
        spread_factor = self.config.spread_percent / 100

        # Calculate prices
        buy_price = mid_price * (1 - spread_factor)
        sell_price = mid_price * (1 + spread_factor)

        # Round to 4 decimal places
        buy_price = buy_price.quantize(Decimal("0.0001"))
        sell_price = sell_price.quantize(Decimal("0.0001"))

        # Place buy order
        try:
            result = self.client.place_order(
                pair=self.config.trading_pair,
                side="buy",
                price=buy_price,
                amount=self.config.order_amount,
                wallet=self.config.wallet_address,
            )
            if result.get("order_id"):
                self.order_ids.append(result["order_id"])
                logger.info(
                    "Placed BUY order: %s @ %s",
                    self.config.order_amount,
                    buy_price,
                )
        except Exception as e:
            logger.error("Failed to place buy order: %s", e)

        # Place sell order
        try:
            result = self.client.place_order(
                pair=self.config.trading_pair,
                side="sell",
                price=sell_price,
                amount=self.config.order_amount,
                wallet=self.config.wallet_address,
            )
            if result.get("order_id"):
                self.order_ids.append(result["order_id"])
                logger.info(
                    "Placed SELL order: %s @ %s",
                    self.config.order_amount,
                    sell_price,
                )
        except Exception as e:
            logger.error("Failed to place sell order: %s", e)

    def check_balance(self) -> bool:
        """Check if wallet has sufficient balance."""
        try:
            balance = self.client.get_balance(self.config.wallet_address)
            available = Decimal(str(balance.get("balance", 0)))
            required = self.config.order_amount * 2  # For buy + buffer

            if available < required:
                logger.warning(
                    "Insufficient balance: %s < %s required",
                    available,
                    required,
                )
                return False

            logger.info("Balance check passed: %s XAI available", available)
            return True

        except Exception as e:
            logger.error("Failed to check balance: %s", e)
            return False

    def run_cycle(self) -> None:
        """Run one trading cycle."""
        # Cancel old orders
        self.cancel_all_orders()

        # Get current mid-price
        mid_price = self.get_mid_price()
        if mid_price is None:
            logger.warning("Skipping cycle - no mid-price available")
            return

        logger.info("Mid-price: %s", mid_price)

        # Check balance
        if not self.check_balance():
            logger.warning("Skipping cycle - insufficient balance")
            return

        # Place new orders
        self.place_spread_orders(mid_price)

    def run(self) -> None:
        """Main bot loop."""
        self.running = True
        logger.info("Starting trading bot for %s", self.config.trading_pair)
        logger.info("Wallet: %s", self.config.wallet_address)
        logger.info("Spread: %s%%", self.config.spread_percent)

        try:
            while self.running:
                try:
                    self.run_cycle()
                except Exception as e:
                    logger.error("Cycle error: %s", e)

                # Wait for next cycle
                logger.info(
                    "Sleeping %d seconds until next cycle...",
                    self.config.update_interval,
                )
                time.sleep(self.config.update_interval)

        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        finally:
            self.shutdown()

    def shutdown(self) -> None:
        """Clean shutdown."""
        logger.info("Shutting down trading bot...")
        self.running = False
        self.cancel_all_orders()
        logger.info("Trading bot stopped")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="XAI Simple Trading Bot Example",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Run with default settings
    python trading_bot_example.py --node-url http://localhost:12001 --wallet TXAI...

    # Custom spread and amount
    python trading_bot_example.py --node-url http://localhost:12001 --wallet TXAI... \\
        --spread 1.0 --amount 50

WARNING: This is an educational example. Do not use real funds without
proper testing and risk management.
        """,
    )
    parser.add_argument(
        "--node-url",
        default="http://localhost:12001",
        help="XAI node URL (default: http://localhost:12001)",
    )
    parser.add_argument(
        "--wallet",
        required=True,
        help="Wallet address for trading",
    )
    parser.add_argument(
        "--pair",
        default="XAI/USDT",
        help="Trading pair (default: XAI/USDT)",
    )
    parser.add_argument(
        "--spread",
        type=float,
        default=0.5,
        help="Spread percentage (default: 0.5)",
    )
    parser.add_argument(
        "--amount",
        type=float,
        default=10.0,
        help="Order amount (default: 10.0)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=30,
        help="Update interval in seconds (default: 30)",
    )

    args = parser.parse_args()

    config = TradingConfig(
        node_url=args.node_url,
        wallet_address=args.wallet,
        trading_pair=args.pair,
        spread_percent=Decimal(str(args.spread)),
        order_amount=Decimal(str(args.amount)),
        update_interval=args.interval,
    )

    bot = SimpleTradingBot(config)

    # Handle SIGTERM
    def signal_handler(signum, frame):
        logger.info("Received signal %s", signum)
        bot.running = False

    signal.signal(signal.SIGTERM, signal_handler)

    bot.run()


if __name__ == "__main__":
    main()
