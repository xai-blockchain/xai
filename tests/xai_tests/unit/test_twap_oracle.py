"""
Unit tests for TWAPOracle.

Coverage targets:
- Recording prices with validation
- Window-based cleaning and TWAP calculation
"""

import pytest

from xai.blockchain.twap_oracle import TWAPOracle


def test_record_and_twap_simple_window():
    oracle = TWAPOracle(window_size_seconds=10)
    oracle.record_price(100, timestamp=1)
    oracle.record_price(200, timestamp=6)
    # At t=10, both points contribute: 100 for 5s, 200 for 5s => twap 150
    assert oracle.get_twap(current_timestamp=11) == 150


def test_window_cleanup_and_empty():
    oracle = TWAPOracle(window_size_seconds=5)
    oracle.record_price(100, timestamp=1)
    # At t=10, old data removed; no price data => 0
    assert oracle.get_twap(current_timestamp=10) == 0.0


def test_invalid_inputs():
    with pytest.raises(ValueError):
        TWAPOracle(window_size_seconds=0)
    oracle = TWAPOracle(window_size_seconds=5)
    with pytest.raises(ValueError):
        oracle.record_price(-1)
    with pytest.raises(ValueError):
        oracle.record_price(10, timestamp=-1)


def test_price_spike_has_bounded_effect():
    """Short-lived spike should have limited impact on TWAP."""
    oracle = TWAPOracle(window_size_seconds=10)
    oracle.record_price(100, timestamp=1)
    oracle.record_price(100, timestamp=6)
    # Manipulation attempt: brief spike near window end
    oracle.record_price(1000, timestamp=9)
    twap = oracle.get_twap(current_timestamp=11)
    # Spike should be diluted over the window (~280 in this setup)
    assert 200 < twap < 400
