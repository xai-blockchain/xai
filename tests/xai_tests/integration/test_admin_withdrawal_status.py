import time
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from flask import Flask

from xai.core.config import Config
from xai.core.exchange_wallet import ExchangeWalletManager
from xai.core.node_api import NodeAPIRoutes


@pytest.fixture
def admin_token(monkeypatch, tmp_path):
    token = "integration-admin-token"
    store_path = tmp_path / "api_keys.json"
    monkeypatch.setattr(Config, "API_KEY_STORE_PATH", str(store_path), raising=False)
    monkeypatch.setattr(Config, "API_ADMIN_KEYS", [token], raising=False)
    monkeypatch.setattr(Config, "API_AUTH_REQUIRED", True, raising=False)
    monkeypatch.setattr(Config, "API_AUTH_KEYS", [], raising=False)
    return token


@pytest.fixture
def exchange_manager(tmp_path):
    manager = ExchangeWalletManager(data_dir=str(tmp_path / "exchange"))
    manager.deposit("integration-user", "XAI", 50_000)
    return manager


def _build_node(app: Flask, exchange_manager: ExchangeWalletManager):
    node = SimpleNamespace()
    node.app = app
    node.blockchain = SimpleNamespace(
        pending_transactions=[],
        chain=[],
        add_transaction=Mock(return_value=True),
    )
    node.broadcast_transaction = Mock()
    node.recovery_manager = Mock()
    node.crypto_deposit_manager = None
    node.payment_processor = None
    node.miner_address = "XAI" + "A" * 40
    node.peers = set()
    node.is_mining = False
    node.start_time = time.time()
    node.metrics_collector = Mock()
    node.exchange_wallet_manager = exchange_manager
    node.get_withdrawal_processor_stats = Mock(return_value={"checked": 1, "completed": 1})
    node.validator = Mock()
    node.request_validator = None
    node.p2p_manager = SimpleNamespace(peer_manager=Mock())
    return node


def test_admin_withdrawal_status_endpoint_returns_real_data(admin_token, exchange_manager, monkeypatch):
    pending = exchange_manager.withdraw("integration-user", "XAI", 1_000, "custodial:ops")["transaction"]["id"]
    completed = exchange_manager.withdraw("integration-user", "XAI", 500, "custodial:cold")["transaction"]["id"]
    exchange_manager.update_withdrawal_status(completed, "completed", settlement_txid="abc123")
    exchange_manager.update_withdrawal_status(pending, "flagged", reason="manual_review")
    completed_extra = exchange_manager.withdraw("integration-user", "XAI", 750, "custodial:treasury")["transaction"]["id"]
    exchange_manager.update_withdrawal_status(completed_extra, "completed", settlement_txid="xyz789")

    app = Flask(__name__)
    node = _build_node(app, exchange_manager)
    routes = NodeAPIRoutes(node)
    routes.setup_routes()

    limiter = Mock()
    limiter.check_rate_limit.return_value = (True, None)
    monkeypatch.setattr("xai.core.node_api.get_rate_limiter", lambda: limiter)

    client = app.test_client()
    response = client.get(
        "/admin/withdrawals/status?limit=10",
        headers={"X-Admin-Token": admin_token},
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["counts"]["pending"] == 0
    assert data["counts"]["flagged"] >= 1
    assert any(w["id"] == pending for w in data["withdrawals"]["flagged"])
    assert any(w["id"] == completed for w in data["withdrawals"]["completed"])
    assert data["latest_processor_run"]["checked"] == 1

    # Filter for completed withdrawals only and enforce limit
    filtered = client.get(
        "/admin/withdrawals/status?status=completed&limit=1",
        headers={"X-Admin-Token": admin_token},
    )
    assert filtered.status_code == 200
    filtered_payload = filtered.get_json()
    assert list(filtered_payload["withdrawals"].keys()) == ["completed"]
    assert len(filtered_payload["withdrawals"]["completed"]) == 1
