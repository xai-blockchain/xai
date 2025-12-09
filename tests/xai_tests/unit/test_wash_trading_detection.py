"""
Unit tests for WashTradingDetector.

Coverage targets:
- Self-trading detection
- Round-trip detection within window
- Input validation for trades
"""

import time

import pytest

from xai.blockchain.wash_trading_detection import WashTradingDetector
from xai.security.circuit_breaker import CircuitBreaker, CircuitBreakerState


class _MockCircuitBreaker(CircuitBreaker):
    def __init__(self):
        super().__init__(name="test_cb", failure_threshold=2, recovery_timeout_seconds=10)
        self.failures = 0
        self.successes = 0

    def record_failure(self):
        self.failures += 1
        return super().record_failure()

    def record_success(self):
        self.successes += 1
        return super().record_success()


def test_self_trading_detected_and_records_failure(monkeypatch):
    cb = _MockCircuitBreaker()
    detector = WashTradingDetector(cb, round_trip_time_window_seconds=60)
    detector.record_trade("A", "A", "ASSET", 1, 100)
    assert detector.detect_self_trading() is True
    assert cb.failures == 1


def test_round_trip_detected_within_window(monkeypatch):
    cb = _MockCircuitBreaker()
    detector = WashTradingDetector(cb, round_trip_time_window_seconds=10)
    base_time = int(time.time())
    # First trade: A sells to B
    monkeypatch.setattr("time.time", lambda: base_time)
    detector.record_trade("B", "A", "ASSET", 1, 100)
    # Second trade within window: B sells back to A
    monkeypatch.setattr("time.time", lambda: base_time + 5)
    detector.record_trade("A", "B", "ASSET", 1, 105)

    monkeypatch.setattr("time.time", lambda: base_time + 6)
    assert detector.detect_round_trip_trading() is True
    assert cb.failures == 1


def test_round_trip_not_detected_outside_window(monkeypatch):
    cb = _MockCircuitBreaker()
    detector = WashTradingDetector(cb, round_trip_time_window_seconds=5)
    base_time = int(time.time())
    monkeypatch.setattr("time.time", lambda: base_time)
    detector.record_trade("B", "A", "ASSET", 1, 100)
    monkeypatch.setattr("time.time", lambda: base_time + 10)
    detector.record_trade("A", "B", "ASSET", 1, 105)
    monkeypatch.setattr("time.time", lambda: base_time + 11)
    assert detector.detect_round_trip_trading() is False
    assert cb.successes >= 1


def test_invalid_trade_inputs():
    cb = _MockCircuitBreaker()
    detector = WashTradingDetector(cb)
    with pytest.raises(ValueError):
        detector.record_trade("", "B", "ASSET", 1, 1)
    with pytest.raises(ValueError):
        detector.record_trade("A", "B", "ASSET", -1, 1)
