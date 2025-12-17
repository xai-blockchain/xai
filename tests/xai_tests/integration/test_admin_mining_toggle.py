import json
from unittest.mock import Mock

import pytest
from flask import Flask


@pytest.fixture
def mock_node(monkeypatch, tmp_path):
    """Mock node with controllable mining methods."""
    from xai.blockchain import emergency_pause as ep

    monkeypatch.setattr(ep.Path, "home", lambda: tmp_path)

    node = Mock()
    node.app = Flask(__name__)
    node.blockchain = Mock()
    node.blockchain.chain = [Mock(index=0), Mock(index=1)]
    node.blockchain.pending_transactions = []
    node.blockchain.get_stats = Mock(return_value={"height": 2})
    node.miner_address = "miner-admin"
    node.is_mining = False
    node.start_time = 0
    node.metrics_collector = Mock()
    node.metrics_collector.export_prometheus = Mock(return_value="# HELP test\nmetric 1")

    def _start():
        node.is_mining = True

    def _stop():
        node.is_mining = False

    node.start_mining = Mock(side_effect=_start)
    node.stop_mining = Mock(side_effect=_stop)
    return node


@pytest.fixture
def api_routes(mock_node, monkeypatch):
    from xai.core.node_api import NodeAPIRoutes

    routes = NodeAPIRoutes(mock_node)
    monkeypatch.setattr(
        routes.api_auth,
        "authorize_scope",
        lambda request, allowed_scopes: (True, "admin", None),
    )
    routes.setup_routes()
    routes.app.config["TESTING"] = True
    return routes


@pytest.fixture
def client(api_routes):
    return api_routes.app.test_client()


def test_admin_can_enable_and_disable_mining(client):
    client.post(
        "/admin/emergency/unpause",
        data=json.dumps({"reason": "reset"}),
        content_type="application/json",
    )
    status = client.get("/admin/mining/status")
    assert status.status_code == 200
    assert status.get_json()["is_mining"] is False

    enable = client.post("/admin/mining/enable")
    assert enable.status_code == 200
    enable_payload = enable.get_json()
    assert enable_payload["started"] is True
    assert enable_payload["is_mining"] is True

    status_after = client.get("/admin/mining/status")
    assert status_after.status_code == 200
    assert status_after.get_json()["is_mining"] is True

    disable = client.post("/admin/mining/disable")
    assert disable.status_code == 200
    disable_payload = disable.get_json()
    assert disable_payload["stopped"] is True
    assert disable_payload["is_mining"] is False


def test_admin_enable_rejected_when_paused(client):
    pause = client.post(
        "/admin/emergency/pause",
        data=json.dumps({"reason": "maintenance"}),
        content_type="application/json",
    )
    assert pause.status_code == 200

    enable = client.post("/admin/mining/enable")
    assert enable.status_code == 423
    body = enable.get_json()
    assert body["code"] == "paused"
