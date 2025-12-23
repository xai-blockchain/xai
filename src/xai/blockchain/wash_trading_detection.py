from __future__ import annotations

import logging
import time
from typing import Any

from ..security.circuit_breaker import CircuitBreaker, CircuitBreakerState

logger = logging.getLogger("xai.blockchain.wash_trading_detector")

class WashTradingDetector:
    def __init__(self, circuit_breaker: CircuitBreaker, round_trip_time_window_seconds: int = 300):
        if not isinstance(circuit_breaker, CircuitBreaker):
            raise ValueError("circuit_breaker must be an instance of CircuitBreaker.")
        if (
            not isinstance(round_trip_time_window_seconds, int)
            or round_trip_time_window_seconds <= 0
        ):
            raise ValueError("Round trip time window must be a positive integer.")

        self.circuit_breaker = circuit_breaker
        self.round_trip_time_window_seconds = round_trip_time_window_seconds
        # Stores trades: {trade_id: {"buyer": str, "seller": str, "asset": str, "amount": float, "price": float, "timestamp": int}}
        self.trade_history: list[dict[str, Any]] = []
        self._trade_id_counter = 0

    def record_trade(
        self, buyer_address: str, seller_address: str, asset: str, amount: float, price: float
    ):
        """Records a new trade."""
        if not buyer_address or not seller_address or not asset:
            raise ValueError("Buyer, seller, and asset cannot be empty.")
        if amount <= 0 or price <= 0:
            raise ValueError("Amount and price must be positive.")

        self._trade_id_counter += 1
        trade_id = f"trade_{self._trade_id_counter}"
        trade = {
            "trade_id": trade_id,
            "buyer": buyer_address,
            "seller": seller_address,
            "asset": asset,
            "amount": amount,
            "price": price,
            "timestamp": int(time.time()),
        }
        self.trade_history.append(trade)
        logger.debug(
            "Recorded trade %s: %s %s @ %s from %s to %s",
            trade_id,
            asset,
            amount,
            price,
            seller_address,
            buyer_address,
        )

    def detect_self_trading(self) -> bool:
        """
        Detects self-trading where the buyer and seller are the same address.
        """
        logger.info("Detecting self-trading")
        for trade in self.trade_history:
            if trade["buyer"] == trade["seller"]:
                logger.warning("Self-trading detected for trade %s (%s)", trade["trade_id"], trade["buyer"])
                self.circuit_breaker.record_failure()
                return True
        logger.info("No self-trading detected")
        self.circuit_breaker.record_success()
        return False

    def detect_round_trip_trading(self) -> bool:
        """
        Detects round-trip trading where an asset is sold and then bought back
        by the same entity (or a related entity) within a short time window.
        This is a simplified conceptual model.
        """
        logger.info("Detecting round-trip trading (window=%ss)", self.round_trip_time_window_seconds)
        current_time = int(time.time())

        # Group trades by asset and then by participant
        asset_trades: dict[str, list[dict[str, Any]]] = {}
        for trade in self.trade_history:
            asset_trades.setdefault(trade["asset"], []).append(trade)

        for asset, trades in asset_trades.items():
            # Filter trades within the time window
            recent_trades = [
                t
                for t in trades
                if (current_time - t["timestamp"]) <= self.round_trip_time_window_seconds
            ]

            # Sort by timestamp to check sequence
            recent_trades.sort(key=lambda x: x["timestamp"])

            for i in range(len(recent_trades)):
                trade1 = recent_trades[i]
                for j in range(i + 1, len(recent_trades)):
                    trade2 = recent_trades[j]

                    # Check for a sell followed by a buy of the same asset by the same entity
                    # (or a buy followed by a sell)
                    if (
                        trade1["seller"] == trade2["buyer"]
                        and trade1["buyer"] == trade2["seller"]
                        and trade1["asset"] == trade2["asset"]
                        and (trade2["timestamp"] - trade1["timestamp"])
                        <= self.round_trip_time_window_seconds
                    ):
                        logger.warning(
                            "Round-trip trading detected for %s between %s and %s (trades %s/%s)",
                            asset,
                            trade1["seller"],
                            trade1["buyer"],
                            trade1["trade_id"],
                            trade2["trade_id"],
                        )
                        self.circuit_breaker.record_failure()
                        return True
        logger.info("No round-trip trading detected")
        self.circuit_breaker.record_success()
        return False

