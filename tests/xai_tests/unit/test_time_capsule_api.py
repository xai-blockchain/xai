"""
Unit tests for time capsule API routes covering validation and wiring.
"""

from flask import Flask

from xai.core.api.time_capsule_api import add_time_capsule_routes


class DummyTimeCapsuleManager:
    """Lightweight manager stub that records calls."""

    def __init__(self):
        self.last_call = None

    def create_xai_capsule(self, **kwargs):
        self.last_call = ("create_xai", kwargs)
        return {"success": True, "capsule_id": "cap-1"}

    def create_cross_chain_capsule(self, **kwargs):
        self.last_call = ("create_cross", kwargs)
        return {"success": True, "capsule_id": "cap-2"}

    def claim_capsule(self, capsule_id, claimer):
        self.last_call = ("claim", capsule_id, claimer)
        return {"success": True, "capsule_id": capsule_id}

    def get_user_capsules(self, address):
        self.last_call = ("user_capsules", address)
        return [{"id": "c1", "address": address}]

    def get_unlocked_capsules(self, address):
        self.last_call = ("unlocked", address)
        return [{"id": "c2"}]

    def get_capsule(self, capsule_id):
        self.last_call = ("get_capsule", capsule_id)
        return None

    def get_statistics(self):
        self.last_call = ("stats",)
        return {"total": 0}


class DummyNode:
    """Node stub exposing blockchain and time capsule manager."""

    def __init__(self):
        self.blockchain = self
        self.time_capsule_manager = DummyTimeCapsuleManager()

    def add_transaction(self, tx):
        # Accept everything for these wiring tests
        return True


def _make_app():
    app = Flask(__name__)
    node = DummyNode()
    add_time_capsule_routes(app, node)
    return app, node


def test_create_xai_capsule_success_with_unlock_days():
    """Create XAI capsule with unlock_days returns 201 and hits manager."""
    app, node = _make_app()
    client = app.test_client()

    resp = client.post(
        "/time-capsule/create/xai",
        json={
            "creator": "c",
            "amount": 10,
            "unlock_days": 1,
        },
    )

    assert resp.status_code == 201
    assert node.time_capsule_manager.last_call[0] == "create_xai"


def test_create_cross_chain_missing_unlock_fails():
    """Cross-chain capsule without unlock date returns 400."""
    app, node = _make_app()
    client = app.test_client()

    resp = client.post(
        "/time-capsule/create/cross-chain",
        json={
            "creator": "c",
            "beneficiary": "b",
            "coin_type": "BTC",
            "amount": 1,
        },
    )

    assert resp.status_code == 400
    assert node.time_capsule_manager.last_call is None


def test_claim_requires_claimer():
    """Missing claimer address returns 400 and does not call manager."""
    app, node = _make_app()
    client = app.test_client()

    resp = client.post("/time-capsule/claim/c1", json={})

    assert resp.status_code == 400
    assert node.time_capsule_manager.last_call is None


def test_get_capsule_not_found_returns_404():
    """Unknown capsule id returns 404 response."""
    app, node = _make_app()
    client = app.test_client()

    resp = client.get("/time-capsule/unknown")

    assert resp.status_code == 404
    assert node.time_capsule_manager.last_call[0] == "get_capsule"


def test_stats_and_unlocked_routes_use_manager():
    """Stats and unlocked routes forward to manager and return 200."""
    app, node = _make_app()
    client = app.test_client()

    stats_resp = client.get("/time-capsule/stats")
    unlocked_resp = client.get("/time-capsule/unlocked/addr1")

    assert stats_resp.status_code == 200
    assert unlocked_resp.status_code == 200
    assert node.time_capsule_manager.last_call[0] == "unlocked"
