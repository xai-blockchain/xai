from pathlib import Path
import json
import time

import pytest

from xai.core.wallets.crypto_deposit_manager import CryptoDepositManager
from xai.core.wallets.crypto_deposit_monitor import (
    CryptoDepositMonitor,
    DepositEvent,
    ExplorerDepositSource,
    FileDepositSource,
    InMemoryDepositSource,
    create_deposit_source,
)


class DummyExchangeWalletManager:
    def __init__(self):
        self.deposits = []

    def deposit(self, user_address, currency, amount, deposit_type="manual", tx_hash=None):
        tx_id = f"deposit_tx_{len(self.deposits) + 1}"
        self.deposits.append(
            {
                "user_address": user_address,
                "currency": currency,
                "amount": amount,
                "tx_hash": tx_hash,
                "deposit_type": deposit_type,
                "tx_id": tx_id,
            }
        )
        return {"success": True, "transaction": {"id": tx_id}, "new_balance": amount}


def _create_manager(tmp_path: Path) -> CryptoDepositManager:
    wallet = DummyExchangeWalletManager()
    return CryptoDepositManager(wallet, data_dir=str(tmp_path))


def test_monitor_processes_events_run_once(tmp_path):
    manager = _create_manager(tmp_path)
    addr = manager.generate_deposit_address("user1", "btc")["deposit_address"]
    event = DepositEvent(
        tx_hash="aa" * 32,
        user_address="user1",
        deposit_address=addr,
        currency="btc",
        amount=0.55,
        confirmations=6,
        required_confirmations=6,
    )
    source = InMemoryDepositSource([event])
    monitor = CryptoDepositMonitor(manager, poll_interval=1, jitter_seconds=0)
    monitor.register_source("BTC", source)
    monitor.run_once()

    history = manager.get_deposit_history("user1")
    assert history
    assert history[0]["status"] == "credited"
    stats = monitor.get_stats()
    assert stats["processed"] == 1
    assert stats["credited"] == 1


def test_file_deposit_source_tracks_confirmations(tmp_path):
    events_file = tmp_path / "btc_events.json"
    entry = {
        "tx_hash": "bb" * 32,
        "user_address": "user-file",
        "deposit_address": "addr123",
        "currency": "btc",
        "amount": 1.23,
        "confirmations": 2,
    }
    events_file.write_text(json.dumps([entry]), encoding="utf-8")

    source = FileDepositSource(str(events_file), min_confirmations=1, max_events_per_poll=10)
    events = source.poll()
    assert len(events) == 1
    assert events[0].confirmations == 2

    # No change means no new events
    assert source.poll() == []

    # Increase confirmations -> event returned again
    entry["confirmations"] = 5
    events_file.write_text(json.dumps([entry]), encoding="utf-8")
    refreshed = source.poll()
    assert len(refreshed) == 1
    assert refreshed[0].confirmations == 5


def test_monitor_start_stop(tmp_path):
    manager = _create_manager(tmp_path)
    addr = manager.generate_deposit_address("user2", "btc")["deposit_address"]
    source = InMemoryDepositSource(
        [
            DepositEvent(
                tx_hash="cc" * 32,
                user_address="user2",
                deposit_address=addr,
                currency="btc",
                amount=0.1,
                confirmations=6,
            )
        ]
    )
    monitor = CryptoDepositMonitor(manager, poll_interval=1, jitter_seconds=0)
    monitor.register_source("BTC", source)
    assert monitor.start() is True
    time.sleep(0.2)  # allow thread to process at least once
    monitor.stop()
    history = manager.get_deposit_history("user2")
    assert history


def test_explorer_deposit_source_parses_records(monkeypatch, tmp_path):
    manager = _create_manager(tmp_path)
    addr = manager.generate_deposit_address("user-exp", "btc")["deposit_address"]

    payload = {
        "transactions": [
            {
                "txid": "dd" * 32,
                "value": 123456789,
                "confirmations": 6,
                "meta": {"memo": "integration"},
            }
        ]
    }

    class DummyResponse:
        def __init__(self, data):
            self._data = data

        def raise_for_status(self):
            return None

        def json(self):
            return self._data

    def fake_request(method, url, headers=None, params=None, timeout=0):
        assert addr in url
        return DummyResponse(payload)

    monkeypatch.setattr("xai.core.wallets.crypto_deposit_monitor.requests.request", fake_request)

    source = ExplorerDepositSource(
        manager,
        currency="btc",
        endpoint_template="https://explorer.example/address/{address}",
        records_path="transactions",
        amount_path="value",
        amount_divisor=100000000,
        metadata_paths={"memo": "meta.memo"},
    )

    events = source.poll()
    assert len(events) == 1
    event = events[0]
    assert event.tx_hash == "dd" * 32
    assert event.amount == pytest.approx(1.23456789)
    assert event.metadata["memo"] == "integration"
    assert event.user_address == "user-exp"


def test_create_deposit_source_helper(tmp_path):
    manager = _create_manager(tmp_path)
    file_cfg = {"type": "file", "path": str(tmp_path / "events.json"), "min_confirmations": 2}
    file_source = create_deposit_source("BTC", file_cfg, manager)
    assert isinstance(file_source, FileDepositSource)

    explorer_cfg = {
        "type": "explorer",
        "endpoint": "https://api.example/address/{address}",
        "records_path": "records",
        "amount_path": "value",
    }
    explorer_source = create_deposit_source("BTC", explorer_cfg, manager)
    assert isinstance(explorer_source, ExplorerDepositSource)
