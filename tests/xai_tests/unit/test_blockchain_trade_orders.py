"""Unit tests for blockchain trade order normalization."""

import math
import pytest

from xai.core.blockchain import Blockchain


@pytest.fixture
def blockchain(tmp_path):
    """Initialize a blockchain instance for trade normalization tests."""
    return Blockchain(data_dir=str(tmp_path))


def _base_order(**overrides):
    order = {
        "wallet_address": "XAI123",
        "token_offered": "XAI",
        "token_requested": "USDT",
        "amount_offered": 10.0,
        "amount_requested": 100.0,
    }
    order.update(overrides)
    return order


def test_normalize_trade_order_derives_price(blockchain):
    normalized = blockchain._normalize_trade_order(_base_order(price=None))
    assert normalized["price"] == pytest.approx(10.0)


def test_normalize_trade_order_rejects_zero_amount_for_price(blockchain):
    with pytest.raises(ValueError):
        blockchain._normalize_trade_order(
            _base_order(amount_offered=0.0, amount_requested=1.0, price=None)
        )


def test_normalize_trade_order_rejects_invalid_price_values(blockchain):
    for invalid_price in (0, -1, math.inf, float("nan")):
        with pytest.raises(ValueError):
            blockchain._normalize_trade_order(_base_order(price=invalid_price))
