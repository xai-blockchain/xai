import time

from xai.core.wallets.wallet_trade_manager_impl import WalletTradeManager
from xai.core.transactions.trading import SwapOrderType


def test_create_and_process_twap_order(tmp_path):
    manager = WalletTradeManager(data_dir=str(tmp_path / "twap"))
    response = manager.create_twap_order(
        maker_address="addr1",
        token_offered="XAI",
        amount_offered=100.0,
        token_requested="USDT",
        amount_requested=50.0,
        price=0.5,
        order_type=SwapOrderType.SELL,
        slice_count=2,
        duration_seconds=2,
    )
    assert response["success"] is True
    schedule_id = response["schedule_id"]
    executed = manager.process_twap_schedules()
    assert len(executed) == 1
    # fast-forward schedule for next slice
    manager.twap_schedules[schedule_id]["next_execution"] = 0
    executed += manager.process_twap_schedules()
    assert len(executed) == 2


def test_create_vwap_order(tmp_path):
    manager = WalletTradeManager(data_dir=str(tmp_path / "vwap"))
    profile = [
        {"weight": 1, "price": 0.49},
        {"weight": 2, "price": 0.51},
    ]
    response = manager.create_vwap_order(
        maker_address="addr1",
        token_offered="XAI",
        amount_offered=90.0,
        token_requested="USDT",
        amount_requested=45.0,
        order_type=SwapOrderType.SELL,
        volume_profile=profile,
    )
    assert response["success"] is True
    assert len(response["orders"]) == 2
