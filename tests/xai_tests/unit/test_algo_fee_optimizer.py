import pytest

from xai.core.algo_fee_optimizer import FeeOptimizer


class TestAlgoFeeOptimizer:
    """Unit tests for the adaptive fee optimizer."""

    def test_percentile_based_recommendation(self):
        optimizer = FeeOptimizer(base_fee=5.0)
        fee_rates = [0.5, 0.8, 1.2, 1.8, 2.4, 3.0]

        result = optimizer.predict_optimal_fee(
            pending_tx_count=120,
            priority="fast",
            fee_rates=fee_rates,
            mempool_bytes=2400,
            avg_block_capacity=40,
        )

        assert result["success"] is True
        assert result["priority"] == "fast"
        assert "fee_percentiles" in result
        assert result["fee_percentiles"]["p50"] == pytest.approx(1.5, rel=1e-9)
        # Fast priority should map near the upper quantiles and scale with congestion.
        assert result["recommended_fee"] == pytest.approx(3.2625, rel=1e-3)
        assert result["congestion_level"] in {"high", "critical"}
        assert result["pressure"]["block_capacity"] == 40

    def test_fallback_without_fee_rates(self):
        optimizer = FeeOptimizer(base_fee=10.0)

        result = optimizer.predict_optimal_fee(
            pending_tx_count=0,
            priority="slow",
            fee_rates=None,
            mempool_bytes=None,
            avg_block_capacity=200,
        )

        assert result["success"] is True
        assert result["priority"] == "slow"
        assert result["fee_percentiles"] == {}
        # Low congestion and slow priority fall back to base fee scaled by multiplier.
        assert result["recommended_fee"] == pytest.approx(7.5, rel=1e-9)
        assert result["congestion_level"] == "low"
