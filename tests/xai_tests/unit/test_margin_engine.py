from decimal import Decimal

import pytest

from xai.core.transactions.margin_engine import (
    AssetRiskParams,
    MarginEngine,
    MarginException,
)


def price_oracle_factory(prices):
    def oracle(asset):
        return Decimal(str(prices[asset.upper()]))

    return oracle


@pytest.fixture
def engine():
    prices = {"BTC": Decimal("30000"), "ETH": Decimal("2000")}
    return MarginEngine(price_oracle=price_oracle_factory(prices))


def test_open_position_requires_margin(engine):
    with pytest.raises(MarginException):
        engine.open_position("acct", "BTC", Decimal("0.1"))
    engine.deposit("acct", Decimal("5"))
    position = engine.open_position("acct", "BTC", Decimal("0.1"), leverage=5)
    assert position.size == Decimal("0.1")
    overview = engine.account_overview("acct")
    assert overview["collateral"] < Decimal("5")


def test_isolated_position_limits(engine):
    engine.deposit("acct", Decimal("2"))
    with pytest.raises(MarginException):
        engine.open_position("acct", "BTC", Decimal("0.2"), isolated=True, leverage=10)
    position = engine.open_position("acct", "BTC", Decimal("0.05"), isolated=True, leverage=5)
    assert position.isolated is True


def test_position_averaging_and_pnl(engine):
    engine.deposit("acct", Decimal("4"))
    engine.open_position("acct", "ETH", Decimal("1"), leverage=4)
    engine.open_position("acct", "ETH", Decimal("1"), leverage=4)
    position = engine._get_account("acct").positions["ETH"]
    assert position.size == Decimal("2")
    result = engine.close_position("acct", "ETH", Decimal("1"), mark_price=Decimal("2200"))
    assert result["realized_pnl"] == Decimal("200")
    assert position.size == Decimal("1")


def test_liquidation_triggered_when_health_factor_below_one():
    prices = {"BTC": Decimal("20000")}
    risk = {"BTC": AssetRiskParams(max_leverage=Decimal("2"), initial_margin=Decimal("0.5"), maintenance_margin=Decimal("0.4"))}
    engine = MarginEngine(price_oracle=price_oracle_factory(prices), asset_risk=risk)
    engine.deposit("acct", Decimal("5"))
    engine.open_position("acct", "BTC", Decimal("0.5"), leverage=2)
    # drop price to trigger liquidation
    engine.price_oracle = price_oracle_factory({"BTC": Decimal("12000")})
    liquidated = engine.perform_liquidations()
    assert "acct" in liquidated
    assert "BTC" not in engine._get_account("acct").positions
