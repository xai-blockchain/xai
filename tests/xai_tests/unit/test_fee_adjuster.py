"""
Unit tests for FeeAdjuster.

Coverage targets:
- Initialization and validation
- Network metrics updates
- Suggested fee calculations
- Congestion-based fee adjustments
- Fee bounds enforcement
- History window management
"""

from collections import deque

import pytest

from xai.network.fee_adjuster import FeeAdjuster


class TestFeeAdjusterInit:
    """Tests for FeeAdjuster initialization."""

    def test_default_initialization(self, capsys):
        """FeeAdjuster initializes with default values."""
        adjuster = FeeAdjuster()
        assert adjuster.base_fee == 0.001
        assert adjuster.max_fee == 0.1
        assert adjuster.congestion_factor == 0.01
        assert adjuster.history_window_blocks == 10

        # Check initialization message
        captured = capsys.readouterr()
        assert "FeeAdjuster initialized" in captured.out

    def test_custom_initialization(self, capsys):
        """FeeAdjuster accepts custom configuration."""
        adjuster = FeeAdjuster(
            base_fee=0.005,
            max_fee=0.5,
            congestion_factor=0.02,
            history_window_blocks=20,
        )
        assert adjuster.base_fee == 0.005
        assert adjuster.max_fee == 0.5
        assert adjuster.congestion_factor == 0.02
        assert adjuster.history_window_blocks == 20

    def test_initial_network_metrics_added(self, capsys):
        """Initial network metrics are added during initialization."""
        adjuster = FeeAdjuster()
        # Should have one entry from __init__
        assert len(adjuster.network_metrics_history) == 1
        assert adjuster.network_metrics_history[0] == (0, 0.0)


class TestFeeAdjusterValidation:
    """Tests for input validation."""

    def test_base_fee_must_be_positive(self):
        """Base fee must be a positive number."""
        with pytest.raises(ValueError, match="Base fee must be a positive number"):
            FeeAdjuster(base_fee=0)

        with pytest.raises(ValueError, match="Base fee must be a positive number"):
            FeeAdjuster(base_fee=-0.001)

    def test_base_fee_must_be_numeric(self):
        """Base fee must be numeric."""
        with pytest.raises(ValueError, match="Base fee must be a positive number"):
            FeeAdjuster(base_fee="invalid")

        with pytest.raises(ValueError, match="Base fee must be a positive number"):
            FeeAdjuster(base_fee=None)

    def test_max_fee_must_exceed_base_fee(self):
        """Max fee must be greater than base fee."""
        with pytest.raises(ValueError, match="Max fee must be greater than base fee"):
            FeeAdjuster(base_fee=0.1, max_fee=0.1)

        with pytest.raises(ValueError, match="Max fee must be greater than base fee"):
            FeeAdjuster(base_fee=0.1, max_fee=0.05)

    def test_max_fee_must_be_numeric(self):
        """Max fee must be numeric."""
        with pytest.raises(ValueError, match="Max fee must be greater than base fee"):
            FeeAdjuster(max_fee="invalid")

    def test_congestion_factor_must_be_positive(self):
        """Congestion factor must be a positive number."""
        with pytest.raises(ValueError, match="Congestion factor must be a positive number"):
            FeeAdjuster(congestion_factor=0)

        with pytest.raises(ValueError, match="Congestion factor must be a positive number"):
            FeeAdjuster(congestion_factor=-0.01)

    def test_congestion_factor_must_be_numeric(self):
        """Congestion factor must be numeric."""
        with pytest.raises(ValueError, match="Congestion factor must be a positive number"):
            FeeAdjuster(congestion_factor="invalid")

    def test_history_window_must_be_positive_int(self):
        """History window must be a positive integer."""
        with pytest.raises(ValueError, match="History window blocks must be a positive integer"):
            FeeAdjuster(history_window_blocks=0)

        with pytest.raises(ValueError, match="History window blocks must be a positive integer"):
            FeeAdjuster(history_window_blocks=-1)

    def test_history_window_must_be_int(self):
        """History window must be an integer."""
        with pytest.raises(ValueError, match="History window blocks must be a positive integer"):
            FeeAdjuster(history_window_blocks=5.5)

        with pytest.raises(ValueError, match="History window blocks must be a positive integer"):
            FeeAdjuster(history_window_blocks="10")


class TestUpdateNetworkMetrics:
    """Tests for network metrics updates."""

    def test_update_adds_metrics(self, capsys):
        """Update adds metrics to history."""
        adjuster = FeeAdjuster()
        initial_len = len(adjuster.network_metrics_history)

        adjuster.update_network_metrics(100, 0.5)
        assert len(adjuster.network_metrics_history) == initial_len + 1
        assert adjuster.network_metrics_history[-1] == (100, 0.5)

        # Check output message
        captured = capsys.readouterr()
        assert "Network metrics updated" in captured.out
        assert "Pending TXs=100" in captured.out
        assert "Block Fullness=0.50" in captured.out

    def test_update_respects_window_size(self, capsys):
        """History is trimmed to window size."""
        adjuster = FeeAdjuster(history_window_blocks=3)

        # Add multiple metrics
        for i in range(5):
            adjuster.update_network_metrics(i * 100, i * 0.1)

        # Should only keep last 3 entries
        assert len(adjuster.network_metrics_history) == 3
        # Oldest entries should be removed
        assert adjuster.network_metrics_history[0] == (200, 0.2)
        assert adjuster.network_metrics_history[-1] == (400, 0.4)

    def test_update_validates_pending_transactions(self):
        """Pending transactions must be non-negative integer."""
        adjuster = FeeAdjuster()

        with pytest.raises(ValueError, match="Pending transactions must be a non-negative integer"):
            adjuster.update_network_metrics(-1, 0.5)

        with pytest.raises(ValueError, match="Pending transactions must be a non-negative integer"):
            adjuster.update_network_metrics(10.5, 0.5)

        with pytest.raises(ValueError, match="Pending transactions must be a non-negative integer"):
            adjuster.update_network_metrics("100", 0.5)

    def test_update_validates_block_fullness_range(self):
        """Block fullness must be between 0.0 and 1.0."""
        adjuster = FeeAdjuster()

        with pytest.raises(ValueError, match="Block fullness must be between 0.0 and 1.0"):
            adjuster.update_network_metrics(100, -0.1)

        with pytest.raises(ValueError, match="Block fullness must be between 0.0 and 1.0"):
            adjuster.update_network_metrics(100, 1.1)

    def test_update_validates_block_fullness_type(self):
        """Block fullness must be numeric."""
        adjuster = FeeAdjuster()

        with pytest.raises(ValueError, match="Block fullness must be between 0.0 and 1.0"):
            adjuster.update_network_metrics(100, "0.5")

    def test_update_accepts_boundary_values(self, capsys):
        """Boundary values for block fullness are accepted."""
        adjuster = FeeAdjuster()

        # Minimum boundary
        adjuster.update_network_metrics(0, 0.0)
        assert adjuster.network_metrics_history[-1] == (0, 0.0)

        # Maximum boundary
        adjuster.update_network_metrics(0, 1.0)
        assert adjuster.network_metrics_history[-1] == (0, 1.0)

    def test_update_accepts_integer_fullness(self, capsys):
        """Integer block fullness values are accepted."""
        adjuster = FeeAdjuster()

        # Integer 0 and 1 should work
        adjuster.update_network_metrics(100, 0)
        assert adjuster.network_metrics_history[-1] == (100, 0)

        adjuster.update_network_metrics(100, 1)
        assert adjuster.network_metrics_history[-1] == (100, 1)


class TestGetSuggestedFee:
    """Tests for fee calculation."""

    def test_base_fee_returned_when_history_empty(self, capsys):
        """Base fee is returned when history is empty."""
        adjuster = FeeAdjuster(base_fee=0.002)
        adjuster.network_metrics_history = deque()  # Clear history

        fee = adjuster.get_suggested_fee()
        assert fee == 0.002

    def test_low_congestion_fee_near_base(self, capsys):
        """Low congestion results in fee near base."""
        adjuster = FeeAdjuster(base_fee=0.001, max_fee=0.1, congestion_factor=0.01)
        adjuster.network_metrics_history = deque()

        # Low congestion: few pending tx, low fullness
        adjuster.update_network_metrics(10, 0.1)

        fee = adjuster.get_suggested_fee()
        # With 10 pending tx and 0.1 fullness:
        # congestion_score = 10/1000 + 0.1 = 0.01 + 0.1 = 0.11
        # adjusted = 0.001 + (0.11 * 0.01) = 0.001 + 0.0011 = 0.0021
        assert fee >= adjuster.base_fee
        assert fee < 0.01  # Well below max fee

    def test_high_congestion_fee_approaches_max(self, capsys):
        """High congestion results in fee approaching max."""
        adjuster = FeeAdjuster(base_fee=0.001, max_fee=0.1, congestion_factor=0.05)
        adjuster.network_metrics_history = deque()

        # High congestion: many pending tx, high fullness
        adjuster.update_network_metrics(5000, 1.0)

        fee = adjuster.get_suggested_fee()
        # With 5000 pending tx and 1.0 fullness:
        # congestion_score = 5000/1000 + 1.0 = 5.0 + 1.0 = 6.0
        # adjusted = 0.001 + (6.0 * 0.05) = 0.001 + 0.3 = 0.301
        # Capped at max_fee = 0.1
        assert fee == adjuster.max_fee

    def test_fee_never_below_base(self, capsys):
        """Fee never drops below base fee."""
        adjuster = FeeAdjuster(base_fee=0.01, max_fee=0.1, congestion_factor=0.001)
        adjuster.network_metrics_history = deque()

        # Zero congestion
        adjuster.update_network_metrics(0, 0.0)

        fee = adjuster.get_suggested_fee()
        assert fee >= adjuster.base_fee

    def test_fee_never_exceeds_max(self, capsys):
        """Fee never exceeds max fee."""
        adjuster = FeeAdjuster(base_fee=0.001, max_fee=0.05, congestion_factor=0.1)
        adjuster.network_metrics_history = deque()

        # Extreme congestion
        adjuster.update_network_metrics(100000, 1.0)

        fee = adjuster.get_suggested_fee()
        assert fee <= adjuster.max_fee

    def test_fee_averages_history(self, capsys):
        """Fee calculation averages historical metrics."""
        adjuster = FeeAdjuster(
            base_fee=0.001,
            max_fee=0.1,
            congestion_factor=0.01,
            history_window_blocks=5,
        )
        adjuster.network_metrics_history = deque()

        # Add varied metrics
        adjuster.update_network_metrics(100, 0.2)
        adjuster.update_network_metrics(200, 0.4)
        adjuster.update_network_metrics(300, 0.6)

        fee1 = adjuster.get_suggested_fee()

        # Add more metrics that increase average
        adjuster.update_network_metrics(1000, 0.8)
        adjuster.update_network_metrics(1500, 1.0)

        fee2 = adjuster.get_suggested_fee()

        # Second fee should be higher due to increased average congestion
        assert fee2 > fee1

    def test_suggested_fee_output_format(self, capsys):
        """Suggested fee output contains expected information."""
        adjuster = FeeAdjuster()
        adjuster.network_metrics_history = deque()
        adjuster.update_network_metrics(500, 0.75)

        # Clear previous output
        capsys.readouterr()

        fee = adjuster.get_suggested_fee()
        captured = capsys.readouterr()

        assert "Suggested fee:" in captured.out
        assert "Avg Pending TXs" in captured.out
        assert "Avg Block Fullness" in captured.out


class TestCongestionScoring:
    """Tests for congestion score calculation."""

    def test_congestion_score_calculation(self, capsys):
        """Verify congestion score formula."""
        adjuster = FeeAdjuster(
            base_fee=0.001,
            max_fee=1.0,  # High max to see uncapped value
            congestion_factor=0.01,
        )
        adjuster.network_metrics_history = deque()

        # Specific values for predictable calculation
        adjuster.update_network_metrics(500, 0.5)  # Single entry for exact avg

        fee = adjuster.get_suggested_fee()

        # Expected:
        # avg_pending = 500, avg_fullness = 0.5
        # congestion_score = 500/1000 + 0.5 = 0.5 + 0.5 = 1.0
        # adjusted = 0.001 + (1.0 * 0.01) = 0.001 + 0.01 = 0.011
        assert abs(fee - 0.011) < 0.0001

    def test_zero_pending_transactions(self, capsys):
        """Zero pending transactions contribute nothing to score."""
        adjuster = FeeAdjuster(
            base_fee=0.001,
            max_fee=1.0,
            congestion_factor=0.01,
        )
        adjuster.network_metrics_history = deque()

        # Zero pending, some fullness
        adjuster.update_network_metrics(0, 0.3)

        fee = adjuster.get_suggested_fee()

        # Expected:
        # congestion_score = 0/1000 + 0.3 = 0.3
        # adjusted = 0.001 + (0.3 * 0.01) = 0.001 + 0.003 = 0.004
        assert abs(fee - 0.004) < 0.0001


class TestEdgeCases:
    """Edge case and boundary tests."""

    def test_integer_base_fee(self, capsys):
        """Integer base fee is accepted."""
        adjuster = FeeAdjuster(base_fee=1, max_fee=10)
        assert adjuster.base_fee == 1

    def test_integer_max_fee(self, capsys):
        """Integer max fee is accepted."""
        adjuster = FeeAdjuster(base_fee=1, max_fee=10)
        assert adjuster.max_fee == 10

    def test_very_small_base_fee(self, capsys):
        """Very small base fee is handled."""
        adjuster = FeeAdjuster(base_fee=0.0000001, max_fee=0.001)
        assert adjuster.base_fee == 0.0000001

        # Fee calculation should still work
        adjuster.update_network_metrics(10, 0.1)
        fee = adjuster.get_suggested_fee()
        assert fee >= adjuster.base_fee

    def test_very_large_congestion_factor(self, capsys):
        """Large congestion factor is capped by max fee."""
        adjuster = FeeAdjuster(
            base_fee=0.001,
            max_fee=0.1,
            congestion_factor=100.0,  # Very aggressive
        )
        adjuster.network_metrics_history = deque()
        adjuster.update_network_metrics(1, 0.1)

        fee = adjuster.get_suggested_fee()
        assert fee == adjuster.max_fee

    def test_single_block_history_window(self, capsys):
        """Single block history window works correctly."""
        adjuster = FeeAdjuster(history_window_blocks=1)

        # Add multiple updates
        adjuster.update_network_metrics(100, 0.5)
        adjuster.update_network_metrics(200, 0.8)
        adjuster.update_network_metrics(300, 0.9)

        # Only last entry should remain
        assert len(adjuster.network_metrics_history) == 1
        assert adjuster.network_metrics_history[0] == (300, 0.9)

    def test_fee_with_float_pending_boundary(self, capsys):
        """Integer boundary for pending transactions is enforced."""
        adjuster = FeeAdjuster()

        # This should fail because 100.0 is float, not int
        with pytest.raises(ValueError):
            adjuster.update_network_metrics(100.0, 0.5)


class TestHistoryManagement:
    """Tests for history deque management."""

    def test_history_is_deque(self):
        """History is stored in a deque."""
        adjuster = FeeAdjuster()
        assert isinstance(adjuster.network_metrics_history, deque)

    def test_history_fifo_behavior(self, capsys):
        """History follows FIFO when exceeding window."""
        adjuster = FeeAdjuster(history_window_blocks=3)
        adjuster.network_metrics_history = deque()  # Clear initial entry

        # Add entries
        adjuster.update_network_metrics(100, 0.1)
        adjuster.update_network_metrics(200, 0.2)
        adjuster.update_network_metrics(300, 0.3)

        # At capacity
        assert len(adjuster.network_metrics_history) == 3
        assert adjuster.network_metrics_history[0] == (100, 0.1)

        # Add one more - should evict oldest
        adjuster.update_network_metrics(400, 0.4)

        assert len(adjuster.network_metrics_history) == 3
        assert adjuster.network_metrics_history[0] == (200, 0.2)  # 100 evicted
        assert adjuster.network_metrics_history[-1] == (400, 0.4)

    def test_multiple_rapid_updates(self, capsys):
        """Multiple rapid updates are handled correctly."""
        adjuster = FeeAdjuster(history_window_blocks=10)

        # Rapid updates
        for i in range(100):
            adjuster.update_network_metrics(i * 10, (i % 10) / 10)

        # Should only keep last 10
        assert len(adjuster.network_metrics_history) == 10


class TestIntegrationScenarios:
    """Integration-style tests for realistic scenarios."""

    def test_network_congestion_cycle(self, capsys):
        """Simulate a congestion cycle: low -> high -> low."""
        adjuster = FeeAdjuster(
            base_fee=0.001,
            max_fee=0.05,
            congestion_factor=0.005,
            history_window_blocks=5,
        )
        adjuster.network_metrics_history = deque()

        # Phase 1: Low congestion
        adjuster.update_network_metrics(10, 0.1)
        adjuster.update_network_metrics(15, 0.2)
        low_fee = adjuster.get_suggested_fee()

        # Phase 2: Building congestion
        adjuster.update_network_metrics(500, 0.5)
        adjuster.update_network_metrics(700, 0.7)
        medium_fee = adjuster.get_suggested_fee()

        # Phase 3: High congestion
        adjuster.update_network_metrics(1500, 0.9)
        adjuster.update_network_metrics(2000, 1.0)
        adjuster.update_network_metrics(2500, 1.0)
        high_fee = adjuster.get_suggested_fee()

        # Phase 4: Congestion easing
        adjuster.update_network_metrics(100, 0.3)
        adjuster.update_network_metrics(50, 0.1)
        easing_fee = adjuster.get_suggested_fee()

        # Verify fee progression
        assert low_fee < medium_fee < high_fee
        assert easing_fee < high_fee  # Should decrease as congestion eases

    def test_stable_network_stable_fee(self, capsys):
        """Stable network conditions produce stable fees."""
        adjuster = FeeAdjuster(
            base_fee=0.001,
            max_fee=0.05,
            congestion_factor=0.005,
            history_window_blocks=5,
        )
        adjuster.network_metrics_history = deque()

        # Consistent metrics
        for _ in range(10):
            adjuster.update_network_metrics(200, 0.4)

        fees = [adjuster.get_suggested_fee() for _ in range(5)]

        # All fees should be identical
        assert all(f == fees[0] for f in fees)
