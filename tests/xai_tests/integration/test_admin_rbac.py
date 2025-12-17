from unittest.mock import Mock

import pytest
from flask import Flask

from xai.core.config import Config


@pytest.fixture
def node():
    node = Mock()
    node.app = Flask(__name__)
    node.blockchain = Mock()
    node.blockchain.chain = [Mock(index=0), Mock(index=1)]
    node.blockchain.pending_transactions = []
    node.blockchain.get_stats = Mock(return_value={"height": 2})
    node.miner_address = "miner"
    node.is_mining = False
    node.start_time = 0
    node.metrics_collector = Mock()
    node.metrics_collector.export_prometheus = Mock(return_value="# HELP test\nmetric 1")
    return node


@pytest.fixture
def api_routes(node, monkeypatch, tmp_path):
    from xai.core.node_api import NodeAPIRoutes

    monkeypatch.setattr(Config, "API_AUTH_REQUIRED", True, raising=False)
    monkeypatch.setattr(Config, "API_AUTH_KEYS", ["user-secret"], raising=False)
    monkeypatch.setattr(Config, "API_ADMIN_KEYS", ["admin-secret"], raising=False)
    monkeypatch.setattr(Config, "API_OPERATOR_KEYS", ["operator-secret"], raising=False)
    monkeypatch.setattr(Config, "API_AUDITOR_KEYS", ["auditor-secret"], raising=False)
    monkeypatch.setattr(Config, "API_KEY_STORE_PATH", str(tmp_path / "api_keys.json"), raising=False)

    routes = NodeAPIRoutes(node)
    routes.setup_routes()
    routes.app.config["TESTING"] = True
    return routes


@pytest.fixture
def client(api_routes):
    return api_routes.app.test_client()


def test_rbac_allows_operator_and_auditor_roles(client):
    # Missing auth
    resp = client.get("/admin/mining/status")
    assert resp.status_code == 401

    # Operator can access operator endpoints
    resp = client.get("/admin/mining/status", headers={"X-API-Key": "operator-secret"})
    assert resp.status_code == 200

    # Auditor can access auditor-allowed endpoints
    resp = client.get("/admin/peers", headers={"X-API-Key": "auditor-secret"})
    assert resp.status_code == 200

    # User scope cannot access operator endpoints
    resp = client.get("/admin/mining/status", headers={"X-API-Key": "user-secret"})
    assert resp.status_code in {401, 403}


def test_rbac_enforces_admin_scope(client):
    # Operator cannot access admin-only endpoint
    resp = client.post("/admin/config/reload", headers={"X-API-Key": "operator-secret"}, json={})
    assert resp.status_code == 403

    # Admin token allows access
    resp = client.post(
        "/admin/config/reload",
        headers={"X-Admin-Token": "admin-secret"},
        json={"overrides": {}},
    )
    assert resp.status_code == 200
