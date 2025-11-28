import logging
from typing import Dict, List, Any
import time

from ..security.circuit_breaker import CircuitBreaker, CircuitBreakerState

logger = logging.getLogger("xai.blockchain.order_book_manipulation")


class OrderBook:
    def __init__(self):
        # Orders stored as {order_id: {"price": float, "amount": float, "type": "buy"|"sell", "timestamp": int, "status": "open"|"canceled"|"filled"}}
        self.buy_orders: Dict[str, Dict[str, Any]] = {}
        self.sell_orders: Dict[str, Dict[str, Any]] = {}
        self._order_id_counter = 0

    def place_order(self, order_type: str, price: float, amount: float, timestamp: int | None = None) -> str:
        if order_type not in ["buy", "sell"]:
            raise ValueError("Order type must be 'buy' or 'sell'.")
        if price <= 0 or amount <= 0:
            raise ValueError("Price and amount must be positive.")

        self._order_id_counter += 1
        order_id = f"order_{self._order_id_counter}"
        order = {
            "price": price,
            "amount": amount,
            "type": order_type,
            "timestamp": int(timestamp if timestamp is not None else time.time()),
            "status": "open",
        }
        if order_type == "buy":
            self.buy_orders[order_id] = order
        else:
            self.sell_orders[order_id] = order
        logger.info("Placed %s order %s: %s @ %s", order_type, order_id, amount, price)
        return order_id

    def cancel_order(self, order_id: str) -> bool:
        if order_id in self.buy_orders and self.buy_orders[order_id]["status"] == "open":
            self.buy_orders[order_id]["status"] = "canceled"
            logger.info("Canceled buy order %s", order_id)
            return True
        elif order_id in self.sell_orders and self.sell_orders[order_id]["status"] == "open":
            self.sell_orders[order_id]["status"] = "canceled"
            logger.info("Canceled sell order %s", order_id)
            return True
        logger.warning("Order %s not found or already processed", order_id)
        return False

    def get_order_book_depth(self) -> Dict[str, List[Dict[str, Any]]]:
        """Returns current open buy and sell orders, sorted by price."""
        sorted_buy_orders = sorted(
            [o for o in self.buy_orders.values() if o["status"] == "open"],
            key=lambda x: x["price"],
            reverse=True,
        )
        sorted_sell_orders = sorted(
            [o for o in self.sell_orders.values() if o["status"] == "open"],
            key=lambda x: x["price"],
        )
        return {"buy": sorted_buy_orders, "sell": sorted_sell_orders}

    def get_current_market_price(self) -> float:
        """Estimates current market price from the best bid/ask."""
        depth = self.get_order_book_depth()
        best_bid = depth["buy"][0]["price"] if depth["buy"] else 0
        best_ask = depth["sell"][0]["price"] if depth["sell"] else float("inf")
        if best_bid > 0 and best_ask != float("inf"):
            return (best_bid + best_ask) / 2
        elif best_bid > 0:
            return best_bid
        elif best_ask != float("inf"):
            return best_ask
        return 0.0


class OrderBookManipulationDetector:
    def __init__(
        self,
        order_book: OrderBook,
        circuit_breaker: CircuitBreaker,
        spoofing_threshold_percentage: float = 50.0,  # % of order book depth
        spoofing_cancel_time_seconds: int = 5,
        layering_min_orders: int = 3,
        layering_price_increment_percentage: float = 0.1,
    ):
        if not isinstance(order_book, OrderBook):
            raise ValueError("order_book must be an instance of OrderBook.")
        if not isinstance(circuit_breaker, CircuitBreaker):
            raise ValueError("circuit_breaker must be an instance of CircuitBreaker.")

        self.order_book = order_book
        self.circuit_breaker = circuit_breaker
        self.spoofing_threshold_percentage = spoofing_threshold_percentage
        self.spoofing_cancel_time_seconds = spoofing_cancel_time_seconds
        self.layering_min_orders = layering_min_orders
        self.layering_price_increment_percentage = layering_price_increment_percentage

    def detect_spoofing(self, current_time: int | None = None) -> bool:
        """
        Detects spoofing by looking for large orders that are quickly canceled.
        This is a simplified conceptual model.
        """
        logger.info("Detecting spoofing attempts")
        current_time = int(current_time if current_time is not None else time.time())

        total_buy_depth = sum(
            o["amount"] * o["price"]
            for o in self.order_book.buy_orders.values()
            if o["status"] == "open"
        )
        total_sell_depth = sum(
            o["amount"] * o["price"]
            for o in self.order_book.sell_orders.values()
            if o["status"] == "open"
        )

        for order_id, order in list(self.order_book.buy_orders.items()) + list(
            self.order_book.sell_orders.items()
        ):
            if (
                order["status"] == "canceled"
                and (current_time - order["timestamp"]) <= self.spoofing_cancel_time_seconds
            ):
                # Check if the canceled order was significantly large relative to the book
                if (
                    order["type"] == "buy"
                    and total_buy_depth > 0
                    and (order["amount"] * order["price"] / total_buy_depth) * 100
                    > self.spoofing_threshold_percentage
                ):
                    logger.warning("Spoofing detected: large buy order %s canceled quickly", order_id)
                    self.circuit_breaker.record_failure()
                    return True
                elif (
                    order["type"] == "sell"
                    and total_sell_depth > 0
                    and (order["amount"] * order["price"] / total_sell_depth) * 100
                    > self.spoofing_threshold_percentage
                ):
                    logger.warning("Spoofing detected: large sell order %s canceled quickly", order_id)
                    self.circuit_breaker.record_failure()
                    return True
        logger.info("No spoofing detected.")
        self.circuit_breaker.record_success()
        return False

    def detect_layering(self) -> bool:
        """
        Detects layering by looking for multiple small orders placed at incrementally increasing/decreasing prices.
        This is a simplified conceptual model.
        """
        logger.info("Detecting layering attempts")
        depth = self.order_book.get_order_book_depth()

        def check_layering_side(orders: List[Dict[str, Any]], is_buy_side: bool) -> bool:
            if len(orders) < self.layering_min_orders:
                return False

            # Sort orders by price (desc for buy, asc for sell)
            sorted_orders = sorted(orders, key=lambda x: x["price"], reverse=is_buy_side)

            # Check for consistent small price increments
            for i in range(len(sorted_orders) - self.layering_min_orders + 1):
                potential_layer = sorted_orders[i : i + self.layering_min_orders]

                is_layered = True
                for j in range(len(potential_layer) - 1):
                    price_diff = abs(potential_layer[j]["price"] - potential_layer[j + 1]["price"])
                    avg_price = (potential_layer[j]["price"] + potential_layer[j + 1]["price"]) / 2
                    if (
                        avg_price > 0
                        and (price_diff / avg_price) * 100
                        > self.layering_price_increment_percentage
                    ):
                        is_layered = False
                        break
                if is_layered:
                    logger.warning(
                        "Layering detected (%d orders) on %s side",
                        self.layering_min_orders,
                        "buy" if is_buy_side else "sell",
                    )
                    self.circuit_breaker.record_failure()
                    return True
            return False

        if check_layering_side(depth["buy"], True) or check_layering_side(depth["sell"], False):
            return True

        logger.info("No layering detected.")
        self.circuit_breaker.record_success()
        return False
