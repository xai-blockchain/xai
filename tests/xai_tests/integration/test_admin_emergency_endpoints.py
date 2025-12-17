import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from flask import Flask


@pytest.fixture
def mock_node(monkeypatch, tmp_path):
    """Create a mock node with deterministic storage paths."""
    # Force emergency pause storage under tmp_path
    from xai.blockchain import emergency_pause as ep

    monkeypatch.setattr(ep.Path, "home", lambda: tmp_path)

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
def api_routes(mock_node, monkeypatch):
    """Instantiate NodeAPIRoutes with patched auth for admin scope."""
    from xai.core.node_api import NodeAPIRoutes

    routes = NodeAPIRoutes(mock_node)
    # Force admin scope allow
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


def test_emergency_status_pause_unpause(client, api_routes):
    # initial status
    resp = client.get("/admin/emergency/status")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "is_paused" in data

    # pause operations
    pause = client.post(
        "/admin/emergency/pause",
        data=json.dumps({"reason": "integration-test"}),
        content_type="application/json",
    )
    assert pause.status_code == 200
    assert pause.get_json()["paused"] is True

    # status reflects pause
    resp = client.get("/admin/emergency/status")
    assert resp.status_code == 200
    assert resp.get_json()["is_paused"] is True

    # unpause
    unpause = client.post(
        "/admin/emergency/unpause",
        data=json.dumps({"reason": "resume"}),
        content_type="application/json",
    )
    assert unpause.status_code == 200
    assert unpause.get_json()["paused"] is False

    resp = client.get("/admin/emergency/status")
    assert resp.status_code == 200
    assert resp.get_json()["is_paused"] is False


def test_circuit_breaker_trip_and_reset(client, api_routes):
    trip = client.post("/admin/emergency/circuit-breaker/trip")
    assert trip.status_code == 200
    trip_data = trip.get_json()
    assert trip_data["state"] == "OPEN"
    assert trip_data["paused"] is True

    reset = client.post("/admin/emergency/circuit-breaker/reset")
    assert reset.status_code == 200
    reset_data = reset.get_json()
    assert reset_data["state"] == "CLOSED"
    assert reset_data["paused"] is False
