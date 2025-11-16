"""Core trading primitives for wallet-based trading."""

from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass
import time


class SwapOrderType(Enum):
    """Type of swap order"""
    BUY = "buy"
    SELL = "sell"


class OrderStatus(Enum):
    """Status of a trade order"""
    PENDING = "pending"
    MATCHED = "matched"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class TradeMatchStatus(Enum):
    """Status of a trade match"""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    SETTLED = "settled"
    FAILED = "failed"


@dataclass
class TradeOrder:
    """Represents a trade order"""
    order_id: str
    order_type: SwapOrderType
    amount: float
    price: float
    user_address: str
    timestamp: float = None
    status: OrderStatus = OrderStatus.PENDING

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "order_id": self.order_id,
            "order_type": self.order_type.value,
            "amount": self.amount,
            "price": self.price,
            "user_address": self.user_address,
            "timestamp": self.timestamp,
            "status": self.status.value,
        }


@dataclass
class TradeMatch:
    """Represents a matched trade"""
    match_id: str
    buy_order_id: str
    sell_order_id: str
    amount: float
    price: float
    timestamp: float = None
    status: TradeMatchStatus = TradeMatchStatus.PENDING

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "match_id": self.match_id,
            "buy_order_id": self.buy_order_id,
            "sell_order_id": self.sell_order_id,
            "amount": self.amount,
            "price": self.price,
            "timestamp": self.timestamp,
            "status": self.status.value,
        }


class TradeManager:
    """Manages trading operations"""

    def __init__(self):
        self.orders = {}
        self.matches = {}

    def create_order(self, order: TradeOrder) -> str:
        """Create a new order"""
        self.orders[order.order_id] = order
        return order.order_id

    def get_order(self, order_id: str) -> Optional[TradeOrder]:
        """Get an order by ID"""
        return self.orders.get(order_id)

    def create_match(self, match: TradeMatch) -> str:
        """Create a new match"""
        self.matches[match.match_id] = match
        return match.match_id

    def get_match(self, match_id: str) -> Optional[TradeMatch]:
        """Get a match by ID"""
        return self.matches.get(match_id)


__all__ = [
    "SwapOrderType",
    "TradeOrder",
    "OrderStatus",
    "TradeMatch",
    "TradeMatchStatus",
    "TradeManager",
]
