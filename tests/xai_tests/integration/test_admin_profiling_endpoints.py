import json
from unittest.mock import Mock

import pytest
from flask import Flask


@pytest.fixture
def mock_node():
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


def test_memory_profiling_flow(client):
    status = client.get("/admin/profiling/status")
    assert status.status_code == 200
    assert status.get_json()["memory"]["running"] is False

    start = client.post("/admin/profiling/memory/start")
    assert start.status_code == 200
    assert start.get_json()["started"] is True

    snapshot = client.post("/admin/profiling/memory/snapshot", json={"top_n": 3})
    assert snapshot.status_code == 200
    snapshot_payload = snapshot.get_json()
    assert snapshot_payload["snapshot_count"] >= 1
    assert isinstance(snapshot_payload["top_allocations"], list)

    stop = client.post("/admin/profiling/memory/stop")
    assert stop.status_code == 200
    assert stop.get_json()["stopped"] is True


def test_cpu_profiling_flow(client):
    start = client.post("/admin/profiling/cpu/start")
    assert start.status_code == 200
    assert start.get_json()["started"] is True

    # Run a small workload to capture stats
    _ = sum(range(1000))

    stop = client.post("/admin/profiling/cpu/stop")
    assert stop.status_code == 200
    payload = stop.get_json()
    assert payload["stopped"] is True
    assert isinstance(payload["summary"], str)

    hotspots = client.get("/admin/profiling/cpu/hotspots?top=3")
    assert hotspots.status_code == 200
    data = hotspots.get_json()
    assert isinstance(data["hotspots"], list)
