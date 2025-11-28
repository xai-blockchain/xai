import time
from tempfile import TemporaryDirectory
from unittest.mock import Mock

import pytest

from xai.core.blockchain import Blockchain, Transaction
from xai.core.config import Config
from xai.core.monitoring import MetricsCollector
from xai.core.nonce_tracker import NonceTracker
from xai.core.transaction_validator import TransactionValidator
from xai.core.wallet import Wallet


def _make_basic_tx(sender: Wallet, recipient: Wallet, fee: float = 0.0) -> Transaction:
    tx = Transaction(
        sender.address,
        recipient.address,
        1.0,
        fee,
        public_key=sender.public_key,
        nonce=1,
        inputs=[{"txid": "a" * 64, "vout": 0}],
        outputs=[{"address": recipient.address, "amount": 1.0}],
    )
    return tx


def test_mempool_ban_window_enforced():
    with TemporaryDirectory() as data_dir:
        chain = Blockchain(data_dir=data_dir)
        chain._mempool_invalid_threshold = 1  # single strike triggers ban
        chain._mempool_invalid_ban_seconds = 60
        chain._mempool_invalid_window_seconds = 300

        sender = Wallet()
        recipient = Wallet()

        def utxo_stub(_txid, _vout):
            return {"amount": 2.0, "script_pubkey": f"P2PKH {sender.address}"}

        chain.utxo_manager.get_unspent_output = utxo_stub

        first_tx = _make_basic_tx(sender, recipient, fee=0.0)
        first_tx.txid = first_tx.calculate_hash()

        assert chain.add_transaction(first_tx) is False
        assert chain._mempool_rejected_invalid_total == 1
        assert chain._is_sender_banned(sender.address, time.time()) is True

        second_tx = _make_basic_tx(sender, recipient, fee=0.0)
        second_tx.txid = second_tx.calculate_hash()
        chain.utxo_manager.get_unspent_output = utxo_stub

        assert chain.add_transaction(second_tx) is False
        assert chain._mempool_rejected_banned_total == 1


def test_min_fee_rate_enforced(monkeypatch):
    mock_blockchain = Mock()
    mock_blockchain.pending_transactions = []

    mock_nonce_tracker = Mock(spec=NonceTracker)
    mock_nonce_tracker.validate_nonce.return_value = True
    mock_nonce_tracker.get_next_nonce.return_value = 1

    mock_logger = Mock()

    mock_utxo = Mock()
    wallet_sender = Wallet()
    wallet_recipient = Wallet()
    mock_utxo.get_unspent_output.return_value = {
        "amount": 5.0,
        "script_pubkey": f"P2PKH {wallet_sender.address}",
    }

    validator = TransactionValidator(mock_blockchain, mock_nonce_tracker, mock_logger, mock_utxo)

    low_fee_tx = _make_basic_tx(wallet_sender, wallet_recipient, fee=0.0)
    low_fee_tx.nonce = 1
    low_fee_tx.sign_transaction(wallet_sender.private_key)

    original_min_fee = getattr(Config, "MEMPOOL_MIN_FEE_RATE", 0.0)
    monkeypatch.setattr(Config, "MEMPOOL_MIN_FEE_RATE", 0.01)

    try:
        assert validator.validate_transaction(low_fee_tx) is False
    finally:
        monkeypatch.setattr(Config, "MEMPOOL_MIN_FEE_RATE", original_min_fee)


def test_mempool_metrics_surface_to_monitoring(monkeypatch):
    stats_snapshot = {
        "chain_height": 1,
        "pending_transactions_count": 0,
        "orphan_blocks_count": 0,
        "orphan_transactions_count": 0,
        "total_circulating_supply": 0,
        "difficulty": 1,
        "mempool_size_bytes": 0,
        "latest_block_hash": "",
        "timestamp": time.time(),
        "mempool_rejected_invalid_total": 3,
        "mempool_rejected_banned_total": 2,
        "mempool_rejected_low_fee_total": 1,
        "mempool_rejected_sender_cap_total": 0,
        "mempool_evicted_low_fee_total": 1,
        "mempool_expired_total": 0,
        "mempool_active_bans": 2,
    }

    class StubProvider:
        def get_stats(self):
            return stats_snapshot

    collector = MetricsCollector(blockchain_data_provider=StubProvider(), update_interval=1)

    # Lower alert thresholds for the test to force alert generation
    collector._mempool_alert_invalid_delta = 1
    collector._mempool_alert_ban_delta = 1
    collector._mempool_alert_active_bans = 1

    try:
        collector._update_blockchain_metrics()

        assert collector.get_metric("xai_mempool_rejected_invalid_total").value == 3
        assert collector.get_metric("xai_mempool_rejected_banned_total").value == 2
        assert collector.get_metric("xai_mempool_active_bans").value == 2

        alert_names = {alert.name for alert in collector.alerts}
        assert "mempool.invalid_rejections_surge" in alert_names
        assert "mempool.banned_senders_surge" in alert_names
        assert "mempool.active_bans" in alert_names
    finally:
        collector.shutdown()
