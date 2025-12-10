from decimal import Decimal

from xai.core.margin_engine import MarginEngine
from xai.core.wallet_trade_manager_impl import WalletTradeManager


def price_oracle(asset: str) -> Decimal:
    if asset.upper() == "BTC":
        return Decimal("30000")
    return Decimal("2000")


def test_margin_deposit_open_close(tmp_path):
    engine = MarginEngine(price_oracle=price_oracle)
    manager = WalletTradeManager(data_dir=str(tmp_path / "margin1"), margin_engine=engine)
    deposit = manager.margin_deposit("acct1", 5)
    assert deposit["success"] is True
    opened = manager.open_margin_position("acct1", "BTC", 0.1, leverage=5)
    assert opened["success"] is True
    overview = manager.get_margin_overview("acct1")
    assert overview["success"] is True
    assert overview["positions"], "positions should exist"
    closed = manager.close_margin_position("acct1", "BTC", 0.1)
    assert closed["success"] is True


def test_margin_calls_require_engine(tmp_path):
    manager = WalletTradeManager(data_dir=str(tmp_path / "margin2"))
    result = manager.margin_deposit("acct2", 1)
    assert result["success"] is False
