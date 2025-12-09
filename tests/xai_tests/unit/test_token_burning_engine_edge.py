"""
Additional edge tests for TokenBurningEngine burn history/stats updates.
"""

from xai.core.token_burning_engine import TokenBurningEngine, ServiceType


class InMemoryEngine(TokenBurningEngine):
    def __init__(self, tmp_dir):
        super().__init__(blockchain=None, data_dir=str(tmp_dir))

    def _save_burn_history(self):
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


def test_mark_depleted_key_removes_history(tmp_path):
    """consume_service repeatedly updates stats and history grows."""
    engine = InMemoryEngine(tmp_path)
    engine.xai_price_usd = 1.0

    for _ in range(3):
        engine.consume_service("addr", ServiceType.AI_QUERY_SIMPLE)

    assert engine.burn_stats["total_services_used"] == 3
    assert len(engine.burn_history) == 3
