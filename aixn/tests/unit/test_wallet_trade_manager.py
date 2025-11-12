"""Unit tests for the wallet trade manager"""

import os
import sys
import tempfile

import pytest

# Add core directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'core'))

from exchange_wallet import ExchangeWalletManager
from nonce_tracker import NonceTracker
from trading import SwapOrderType, TradeMatchStatus
from wallet_trade_manager import WalletTradeManager


def test_wallet_trade_settlement(tmp_path):
    exchange_dir = tmp_path / 'exchange'
    trade_dir = tmp_path / 'wallet_trades'
    nonce_dir = tmp_path / 'nonces'

    exchange_wallet = ExchangeWalletManager(data_dir=str(exchange_dir))
    nonce_tracker = NonceTracker(data_dir=str(nonce_dir))
    manager = WalletTradeManager(
        exchange_wallet_manager=exchange_wallet,
        data_dir=str(trade_dir),
        nonce_tracker=nonce_tracker,
    )

    exchange_wallet.deposit('seller', 'XAI', 15.0, deposit_type='test')
    exchange_wallet.deposit('buyer', 'USDT', 100.0, deposit_type='test')

    seller_order, _ = manager.place_order(
        maker_address='seller',
        token_offered='XAI',
        amount_offered=10.0,
        token_requested='USDT',
        amount_requested=20.0,
        price=2.0,
        order_type=SwapOrderType.SELL,
    )

    buyer_order, matches = manager.place_order(
        maker_address='buyer',
        token_offered='USDT',
        amount_offered=20.0,
        token_requested='XAI',
        amount_requested=10.0,
        price=0.5,
        order_type=SwapOrderType.BUY,
    )

    assert matches, 'Buy order should match the seller'
    match = matches[0]
    assert match.status == TradeMatchStatus.MATCHED

    settled = manager.settle_match(match.match_id, match.secret)
    assert settled.status == TradeMatchStatus.SETTLED

    buyer_balance = exchange_wallet.get_balance('buyer', 'XAI')
    seller_balance = exchange_wallet.get_balance('seller', 'USDT')

    assert pytest.approx(buyer_balance['available'], rel=1e-8) == 10.0
    assert pytest.approx(seller_balance['available'], rel=1e-8) == 20.0
