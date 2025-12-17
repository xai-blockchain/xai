import json
import time
from unittest.mock import Mock

import pytest
from flask import Flask


class DummyPeerManager:
    def __init__(self):
        now = time.time()
        self.connected_peers = {
            "peer-1": {
                "ip_address": "198.51.100.10",
                "connected_at": now,
                "last_seen": now,
                "geo": {"country": "US"},
            }
        }
        self.seen_nonces = {"peer-1": [1, 2]}
        self.trusted_peers = set()
        self.banned_peers = set()
        self.ban_counts = {"198.51.100.9": 2}
        self.banned_until = {"198.51.100.9": now + 600}

    def disconnect_peer(self, peer_id: str):
        self.connected_peers.pop(peer_id, None)

    def ban_peer(self, peer_identifier: str):
        self.banned_peers.add(peer_identifier.lower())

    def unban_peer(self, peer_identifier: str):
        self.banned_peers.discard(peer_identifier.lower())


@pytest.fixture
def mock_node(monkeypatch, tmp_path):
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
    manager = DummyPeerManager()
    node.peer_manager = manager
    return node, manager


@pytest.fixture
def api_routes(mock_node, monkeypatch):
    from xai.core.node_api import NodeAPIRoutes

    node, manager = mock_node
    routes = NodeAPIRoutes(node)
    monkeypatch.setattr(
        routes.api_auth,
        "authorize_scope",
        lambda request, allowed_scopes: (True, "admin", None),
    )
    snapshot_payload = {
        "connected_total": 1,
        "connections": [{"peer_id": "peer-1", "ip_address": "198.51.100.10"}],
        "diversity": {"unique_countries": 1},
        "limits": {},
        "trusted_peers": [],
        "banned_peers": [],
        "discovered": [],
    }
    monkeypatch.setattr(
        NodeAPIRoutes,
        "_build_peer_snapshot",
        lambda self: snapshot_payload,
    )
    routes.setup_routes()
    routes.peer_manager = manager
    routes.node.peer_manager = manager
    routes.app.config["TESTING"] = True
    return routes, manager


@pytest.fixture
def client(api_routes):
    routes, _ = api_routes
    return routes.app.test_client()


@pytest.fixture
def peer_manager(api_routes):
    _, manager = api_routes
    return manager


def test_admin_peer_status_returns_snapshot(client, peer_manager):
    resp = client.get("/admin/peers")
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["connected_total"] == 1
    assert payload["connections"][0]["peer_id"] == "peer-1"
    assert payload["ban_counts"] == peer_manager.ban_counts


def test_admin_peer_disconnect_and_ban_flow(client, peer_manager):
    disconnect = client.post("/admin/peers/disconnect", json={"peer_id": "peer-1"})
    assert disconnect.status_code == 200
    assert "peer-1" not in peer_manager.connected_peers

    ban = client.post(
        "/admin/peers/ban",
        data=json.dumps({"peer_id": "198.51.100.20", "reason": "spam"}),
        content_type="application/json",
    )
    assert ban.status_code == 200
    assert "198.51.100.20" in peer_manager.banned_peers

    unban = client.post("/admin/peers/unban", json={"peer_id": "198.51.100.20"})
    assert unban.status_code == 200
    assert "198.51.100.20" not in peer_manager.banned_peers
