import math
import pytest

from xai.exchange import MatchingEngine, OrderValidationError, OrderType


def _engine() -> MatchingEngine:
    return MatchingEngine()


def test_limit_order_rejects_negative_price():
    ex = _engine()
    with pytest.raises(OrderValidationError):
        ex.place_order(
            user_address="user-1",
            pair="XAI/USD",
            side="buy",
            order_type="limit",
            price=-5.0,
            amount=1.0,
        )


def test_limit_order_rejects_non_finite_price():
    ex = _engine()
    with pytest.raises(OrderValidationError):
        ex.place_order(
            user_address="user-1",
            pair="XAI/USD",
            side="sell",
            order_type="limit",
            price=float("inf"),
            amount=2.0,
        )
    with pytest.raises(OrderValidationError):
        ex.place_order(
            user_address="user-1",
            pair="XAI/USD",
            side="sell",
            order_type="limit",
            price=math.nan,
            amount=2.0,
        )


def test_market_order_requires_zero_price():
    ex = _engine()
    with pytest.raises(OrderValidationError):
        ex.place_order(
            user_address="user-1",
            pair="XAI/USD",
            side="buy",
            order_type=OrderType.MARKET.value,
            price=15.0,
            amount=1.0,
        )


def test_rejects_zero_amount():
    ex = _engine()
    with pytest.raises(OrderValidationError):
        ex.place_order(
            user_address="user-1",
            pair="XAI/USD",
            side="buy",
            order_type="limit",
            price=10.0,
            amount=0.0,
        )


def test_valid_limit_order_passes_and_rounds():
    ex = _engine()
    order = ex.place_order(
        user_address="user-1",
        pair="XAI/USD",
        side="buy",
        order_type="limit",
        price=10.5,
        amount=1.25,
    )
    assert float(order.price) == pytest.approx(10.5)
    assert float(order.amount) == pytest.approx(1.25)


def test_stop_limit_requires_stop_price():
    ex = _engine()
    with pytest.raises(OrderValidationError):
        ex.place_order(
            user_address="user-1",
            pair="XAI/USD",
            side="buy",
            order_type=OrderType.STOP_LIMIT.value,
            price=100.0,
            amount=1.0,
        )


def test_stop_limit_directional_validation():
    ex = _engine()
    with pytest.raises(OrderValidationError):
        ex.place_order(
            user_address="user-1",
            pair="XAI/USD",
            side="buy",
            order_type=OrderType.STOP_LIMIT.value,
            price=95.0,
            amount=1.0,
            stop_price=90.0,
        )
    with pytest.raises(OrderValidationError):
        ex.place_order(
            user_address="user-1",
            pair="XAI/USD",
            side="sell",
            order_type=OrderType.STOP_LIMIT.value,
            price=95.0,
            amount=1.0,
            stop_price=110.0,
        )


def test_stop_limit_valid_configuration_returns_order():
    ex = _engine()
    order = ex.place_order(
        user_address="user-1",
        pair="XAI/USD",
        side="buy",
        order_type=OrderType.STOP_LIMIT.value,
        price=105.0,
        amount=2.0,
        stop_price=110.0,
    )
    assert order.stop_price is not None
    assert float(order.stop_price) == pytest.approx(110.0)
    assert order.triggered is False
    assert order.order_type == OrderType.STOP_LIMIT


def test_slippage_only_allowed_for_market_orders():
    ex = _engine()
    with pytest.raises(OrderValidationError):
        ex.place_order(
            user_address="user-1",
            pair="XAI/USD",
            side="buy",
            order_type="limit",
            price=10.0,
            amount=1.0,
            max_slippage_bps=100,
        )


def test_slippage_requires_positive_integer():
    ex = _engine()
    with pytest.raises(OrderValidationError):
        ex.place_order(
            user_address="user-1",
            pair="XAI/USD",
            side="buy",
            order_type=OrderType.MARKET.value,
            price=0,
            amount=1.0,
            max_slippage_bps=0,
        )
    with pytest.raises(OrderValidationError):
        ex.place_order(
            user_address="user-1",
            pair="XAI/USD",
            side="buy",
            order_type=OrderType.MARKET.value,
            price=0,
            amount=1.0,
            max_slippage_bps="bad",  # type: ignore[arg-type]
        )


def test_slippage_requires_available_liquidity():
    ex = _engine()
    with pytest.raises(OrderValidationError):
        ex.place_order(
            user_address="user-1",
            pair="XAI/USD",
            side="buy",
            order_type=OrderType.MARKET.value,
            price=0,
            amount=1.0,
            max_slippage_bps=200,
        )
