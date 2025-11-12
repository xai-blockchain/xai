"""Convenience wrapper exposing core trading primitives."""

from core.trading import (
    SwapOrderType,
    TradeOrder,
    OrderStatus,
    TradeMatch,
    TradeMatchStatus,
    TradeManager,
)

__all__ = [
    'SwapOrderType',
    'TradeOrder',
    'OrderStatus',
    'TradeMatch',
    'TradeMatchStatus',
    'TradeManager',
]
