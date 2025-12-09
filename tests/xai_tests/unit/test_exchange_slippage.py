"""
Tests for exchange slippage guard against sandwich/high-slippage execution.
"""

from decimal import Decimal

from xai.exchange import (
    MatchingEngine,
    Order,
    OrderSide,
    OrderType,
    OrderStatus,
)


def test_market_order_cancels_on_slippage_guard():
    """Market order with strict slippage limit should not fill at extreme price."""
    ex = MatchingEngine()
    pair = "XAI/USDT"

    # Maker places a high-priced ask (200)
    ex.place_order(
        user_address="maker",
        pair=pair,
        side="sell",
        order_type="limit",
        price=200,
        amount=1,
    )

    # Craft a market buy with a low reference price and strict slippage bps
    mkt_order = Order(
        id="mkt1",
        user_address="taker",
        pair=pair,
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        price=Decimal("0"),
        amount=Decimal("1"),
        slippage_bps=10,  # 0.10% max slippage
        reference_price=Decimal("100"),  # Expected fair price
    )

    ex.match_market_order(mkt_order)

    # No trades executed because price violates slippage guard
    assert mkt_order.status == OrderStatus.CANCELLED
    assert mkt_order.remaining() == Decimal("1")
    assert ex.trade_history == []
