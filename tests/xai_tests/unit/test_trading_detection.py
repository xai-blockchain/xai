import time

import pytest

from xai.blockchain.wash_trading_detection import WashTradingDetector
from xai.security.circuit_breaker import CircuitBreaker


def test_self_trading_detection():
    cb = CircuitBreaker("wash-test", failure_threshold=1, recovery_timeout_seconds=60)
    detector = WashTradingDetector(cb, round_trip_time_window_seconds=10)
    detector.record_trade("0xBuyer", "0xSeller", "ETH", 1, 2000)
    assert detector.detect_self_trading() is False
    detector.record_trade("0xBuyer", "0xBuyer", "ETH", 1, 2000)
    assert detector.detect_self_trading() is True


def test_round_trip_detection():
    cb = CircuitBreaker("wash-round", failure_threshold=1, recovery_timeout_seconds=60)
    detector = WashTradingDetector(cb, round_trip_time_window_seconds=10)
    detector.record_trade("0xA", "0xB", "ETH", 1, 2000)
    detector.record_trade("0xB", "0xC", "ETH", 1, 2010)
    assert detector.detect_round_trip_trading() is False
    detector.record_trade("0xB", "0xA", "ETH", 1, 2015)
    assert detector.detect_round_trip_trading() is True
