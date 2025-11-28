import pytest

from xai.blockchain.slippage_limits import LiquidityPool


def test_swap_within_limits():
    pool = LiquidityPool(
        token_x_reserve=1000.0,
        token_y_reserve=1000000.0,
        pool_slippage_limit_percentage=1.0,
        max_trade_size=50.0,
        price_impact_rejection_threshold_percentage=2.0,
    )
    amount_out = pool.swap(amount_in=1.0, token_in="X", min_amount_out=900.0)
    assert amount_out > 0
    assert pool.reserve_x > 1000.0
    assert pool.reserve_y < 1000000.0


def test_swap_exceeds_trade_size():
    pool = LiquidityPool(
        token_x_reserve=1000.0,
        token_y_reserve=1000000.0,
        pool_slippage_limit_percentage=1.0,
        max_trade_size=10.0,
        price_impact_rejection_threshold_percentage=2.0,
    )
    with pytest.raises(ValueError, match="exceeds maximum allowed trade size"):
        pool.swap(amount_in=50.0, token_in="X", min_amount_out=0.0)


def test_price_impact_rejection():
    pool = LiquidityPool(
        token_x_reserve=1000.0,
        token_y_reserve=1000000.0,
        pool_slippage_limit_percentage=1.0,
        max_trade_size=100.0,
        price_impact_rejection_threshold_percentage=0.1,
    )
    with pytest.raises(ValueError, match="Price impact"):
        pool.swap(amount_in=50.0, token_in="X", min_amount_out=0.0)
