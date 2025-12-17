import json
from unittest.mock import Mock

import pytest
from flask import Flask

from xai.core import config as ConfigModule


@pytest.fixture
def mock_node(monkeypatch, tmp_path):
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


def test_config_reload_updates_runtime(client, monkeypatch):
    monkeypatch.setenv("XAI_API_RATE_LIMIT", "120")
    monkeypatch.setenv("XAI_API_MAX_JSON_BYTES", "1024")
    payload = {
        "overrides": {
            "XAI_API_RATE_LIMIT": "250",
            "XAI_API_MAX_JSON_BYTES": "2048",
        }
    }
    resp = client.post("/admin/config/reload", data=json.dumps(payload), content_type="application/json")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["changed"]["API_RATE_LIMIT"]["new"] == 250
    assert ConfigModule.API_RATE_LIMIT == 250
    assert client.application.config["MAX_CONTENT_LENGTH"] == 2048


def test_config_reload_validates_payload(client):
    resp = client.post("/admin/config/reload", json={"overrides": "bad"})
    assert resp.status_code == 400
    assert resp.get_json()["code"] == "invalid_payload"
