"""
Unit tests for token burning API endpoints wiring and validation.
"""

from flask import Flask

from xai.core import burning_api_endpoints as burn_api
from xai.core.token_burning_engine import ServiceType


class FakeEngine:
    """Stub TokenBurningEngine used to avoid disk IO."""

    def __init__(self, *a, **k):
        self.calls = []
        self.xai_price_usd = 1.0

    def consume_service(self, wallet_address, service_type, custom_amount=None):
        self.calls.append(("consume", wallet_address, service_type, custom_amount))
        return {"success": True, "burn_id": "id1", "total_cost_xai": 1.0, "burned_xai": 0.5, "to_miners_xai": 0.5}

    def get_anonymous_stats(self):
        self.calls.append(("stats",))
        return {"total_burned": 1}

    def get_recent_burns(self, limit=100):
        self.calls.append(("recent", limit))
        return [{"burn_id": "id1"}]

    def get_burn_by_service(self, service):
        self.calls.append(("service_stats", service))
        return {"count": 1, "total_burned": 1.0}

    def calculate_service_cost(self, service):
        self.calls.append(("price", service))
        return 0.1


def _make_app(monkeypatch):
    app = Flask(__name__)
    # monkeypatch TokenBurningEngine constructor to return FakeEngine
    monkeypatch.setattr(burn_api, "TokenBurningEngine", FakeEngine)
    engine = burn_api.setup_burning_api(app, type("node", (), {"blockchain": None}))
    return app, engine


def test_consume_service_requires_fields(monkeypatch):
    """Missing wallet/service_type returns 400 and does not call engine."""
    app, engine = _make_app(monkeypatch)
    client = app.test_client()

    resp = client.post("/burn/consume-service", json={"wallet_address": "X"})
    assert resp.status_code == 400
    assert engine.calls == []


def test_consume_service_invokes_engine(monkeypatch):
    """Valid consume request delegates to engine and returns data."""
    app, engine = _make_app(monkeypatch)
    client = app.test_client()

    resp = client.post(
        "/burn/consume-service",
        json={"wallet_address": "X", "service_type": ServiceType.AI_QUERY_SIMPLE.value},
    )

    assert resp.status_code == 200
    assert ("consume", "X", ServiceType.AI_QUERY_SIMPLE, None) in engine.calls


def test_price_and_service_stats(monkeypatch):
    """Price and per-service stats routes succeed and touch engine."""
    app, engine = _make_app(monkeypatch)
    client = app.test_client()

    price_resp = client.get(f"/burn/price/{ServiceType.AI_QUERY_SIMPLE.value}")
    stats_resp = client.get(f"/burn/service/{ServiceType.AI_QUERY_SIMPLE.value}")

    assert price_resp.status_code == 200
    assert stats_resp.status_code == 200
    assert any(call[0] == "price" for call in engine.calls)
    assert any(call[0] == "service_stats" for call in engine.calls)
