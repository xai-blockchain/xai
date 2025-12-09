"""
Unit tests for TokenBurningEngine cost calculation and burn stats updates.
"""

from types import SimpleNamespace

from xai.core.token_burning_engine import (
    SERVICE_PRICES_USD,
    ServiceType,
    TokenBurningEngine,
)


class InMemoryEngine(TokenBurningEngine):
    """TokenBurningEngine variant keeping data in temporary paths."""

    def __init__(self, tmp_dir):
        super().__init__(blockchain=None, data_dir=str(tmp_dir))

    def _save_burn_history(self):
        # Avoid disk writes during tests
        pass

    def _load_burn_history(self):
        self.burn_history = []

    def _load_burn_stats(self):
        self.burn_stats = {
            "total_burned": 0.0,
            "total_to_miners": 0.0,
            "total_services_used": 0,
            "service_usage": {},
            "last_updated_utc": 0,
        }


def test_calculate_service_cost_uses_usd_price(tmp_path, monkeypatch):
    """Service cost converts USD price to XAI using current oracle price."""
    engine = InMemoryEngine(tmp_path)
    engine.xai_price_usd = 2.0  # 1 XAI = $2
    cost = engine.calculate_service_cost(ServiceType.AI_QUERY_SIMPLE)
    assert cost == SERVICE_PRICES_USD[ServiceType.AI_QUERY_SIMPLE] / 2.0


def test_consume_service_updates_stats_and_history(tmp_path, monkeypatch):
    """consume_service records burn split and updates statistics counters."""
    engine = InMemoryEngine(tmp_path)
    engine.xai_price_usd = 1.0

    result = engine.consume_service(wallet_address="addr", service_type=ServiceType.AI_QUERY_SIMPLE)

    assert result["success"] is True
    assert engine.burn_stats["total_services_used"] == 1
    assert engine.burn_stats["total_burned"] > 0
    assert len(engine.burn_history) == 1
    entry = engine.burn_history[0]
    assert entry["wallet_address"] == "addr"
    assert entry["service_type"] == ServiceType.AI_QUERY_SIMPLE.value
