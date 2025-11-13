"""Convenience wrapper exposing core trading primitives."""

from aixn.core.trading import (
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
