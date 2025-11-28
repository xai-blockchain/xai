"""Simple coverage test for exchange module"""
import pytest
from decimal import Decimal
from xai.exchange import (
    OrderType,
    OrderSide,
    OrderStatus,
    Order,
    Trade,
)


def test_order_type_enum():
    """Test OrderType enum"""
    assert OrderType.LIMIT.value == "limit"
    assert OrderType.MARKET.value == "market"
    assert OrderType.STOP_LIMIT.value == "stop_limit"


def test_order_side_enum():
    """Test OrderSide enum"""
    assert OrderSide.BUY.value == "buy"
    assert OrderSide.SELL.value == "sell"


def test_order_status_enum():
    """Test OrderStatus enum"""
    assert OrderStatus.PENDING.value == "pending"
    assert OrderStatus.PARTIAL.value == "partial"
    assert OrderStatus.FILLED.value == "filled"
    assert OrderStatus.CANCELLED.value == "cancelled"


def test_order_init():
    """Test Order initialization"""
    order = Order(
        id="order_1",
        user_address="user_addr",
        pair="BTC/USD",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        price=Decimal("50000"),
        amount=Decimal("1.0"),
    )

    assert order.id == "order_1"
    assert order.user_address == "user_addr"
    assert order.pair == "BTC/USD"
    assert order.side == OrderSide.BUY
    assert order.price == Decimal("50000")


def test_order_remaining():
    """Test Order.remaining method"""
    order = Order(
        id="o1",
        user_address="u1",
        pair="BTC/USD",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        price=Decimal("50000"),
        amount=Decimal("2.0"),
        filled=Decimal("0.5"),
    )

    remaining = order.remaining()
    assert remaining == Decimal("1.5")


def test_order_is_filled():
    """Test Order.is_filled method"""
    order = Order(
        id="o1",
        user_address="u1",
        pair="BTC/USD",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        price=Decimal("50000"),
        amount=Decimal("1.0"),
        filled=Decimal("1.0"),
    )

    assert order.is_filled() is True

    order.filled = Decimal("0.5")
    assert order.is_filled() is False


def test_order_to_dict():
    """Test Order.to_dict method"""
    order = Order(
        id="o1",
        user_address="u1",
        pair="BTC/USD",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        price=Decimal("50000"),
        amount=Decimal("1.0"),
    )

    data = order.to_dict()

    assert data["id"] == "o1"
    assert data["user_address"] == "u1"
    assert data["pair"] == "BTC/USD"
    assert data["side"] == "buy"
    assert data["type"] == "limit"
    assert "price" in data
    assert "amount" in data
    assert "filled" in data
    assert "remaining" in data
    assert "status" in data


def test_trade_init():
    """Test Trade initialization"""
    trade = Trade(
        id="trade_1",
        pair="BTC/USD",
        buy_order_id="buy_1",
        sell_order_id="sell_1",
        buyer_address="buyer",
        seller_address="seller",
        price=Decimal("50000"),
        amount=Decimal("1.0"),
    )

    assert trade.id == "trade_1"
    assert trade.pair == "BTC/USD"
    assert trade.buy_order_id == "buy_1"
    assert trade.sell_order_id == "sell_1"
    assert trade.buyer_address == "buyer"
    assert trade.seller_address == "seller"


def test_trade_to_dict():
    """Test Trade.to_dict method"""
    trade = Trade(
        id="t1",
        pair="BTC/USD",
        buy_order_id="b1",
        sell_order_id="s1",
        buyer_address="buyer",
        seller_address="seller",
        price=Decimal("50000"),
        amount=Decimal("0.5"),
    )

    data = trade.to_dict()

    assert data["id"] == "t1"
    assert data["pair"] == "BTC/USD"
    assert data["buy_order_id"] == "b1"
    assert data["sell_order_id"] == "s1"
    assert "price" in data
    assert "amount" in data


def test_order_market_type():
    """Test market order (price = 0)"""
    order = Order(
        id="o1",
        user_address="u1",
        pair="BTC/USD",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        price=Decimal("0"),
        amount=Decimal("1.0"),
    )

    assert order.price == Decimal("0")
    assert order.order_type == OrderType.MARKET


def test_order_sell_side():
    """Test sell order"""
    order = Order(
        id="o1",
        user_address="u1",
        pair="BTC/USD",
        side=OrderSide.SELL,
        order_type=OrderType.LIMIT,
        price=Decimal("50000"),
        amount=Decimal("1.0"),
    )

    assert order.side == OrderSide.SELL


def test_order_pay_fee_with_axn():
    """Test pay_fee_with_axn flag"""
    order = Order(
        id="o1",
        user_address="u1",
        pair="BTC/USD",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        price=Decimal("50000"),
        amount=Decimal("1.0"),
        pay_fee_with_axn=True,
    )

    assert order.pay_fee_with_axn is True

    data = order.to_dict()
    assert data["pay_fee_with_axn"] is True


def test_order_partial_status():
    """Test partial order status"""
    order = Order(
        id="o1",
        user_address="u1",
        pair="BTC/USD",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        price=Decimal("50000"),
        amount=Decimal("2.0"),
        filled=Decimal("1.0"),
        status=OrderStatus.PARTIAL,
    )

    assert order.status == OrderStatus.PARTIAL
    assert order.remaining() == Decimal("1.0")


def test_order_timestamp():
    """Test order has timestamp"""
    order = Order(
        id="o1",
        user_address="u1",
        pair="BTC/USD",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        price=Decimal("50000"),
        amount=Decimal("1.0"),
    )

    assert order.timestamp > 0


def test_trade_timestamp():
    """Test trade has timestamp"""
    trade = Trade(
        id="t1",
        pair="BTC/USD",
        buy_order_id="b1",
        sell_order_id="s1",
        buyer_address="buyer",
        seller_address="seller",
        price=Decimal("50000"),
        amount=Decimal("0.5"),
    )

    assert trade.timestamp > 0


def test_order_different_pairs():
    """Test orders with different trading pairs"""
    pairs = ["BTC/USD", "ETH/USD", "AXN/USD", "XAI/BTC"]

    for pair in pairs:
        order = Order(
            id=f"o_{pair}",
            user_address="u1",
            pair=pair,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            price=Decimal("1000"),
            amount=Decimal("1.0"),
        )

        assert order.pair == pair


def test_decimal_precision():
    """Test decimal precision handling"""
    order = Order(
        id="o1",
        user_address="u1",
        pair="BTC/USD",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        price=Decimal("50000.123456"),
        amount=Decimal("1.23456789"),
    )

    assert isinstance(order.price, Decimal)
    assert isinstance(order.amount, Decimal)
