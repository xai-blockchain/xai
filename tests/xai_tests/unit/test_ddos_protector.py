"""
Unit tests for DDoSProtector.

Coverage targets:
- Per-IP rate limiting
- Connection limits (per-IP and global)
- Adaptive rate limit adjustments
- Cleanup of inactive IPs to bound memory
"""

from collections import deque

import pytest

from xai.network.ddos_protector import DDoSProtector


def test_rate_limit_enforced(monkeypatch):
    """Requests beyond per-IP limit are blocked within window."""
    protector = DDoSProtector(rate_limit_per_second=2, time_window_seconds=1)
    monkeypatch.setattr("time.time", lambda: 0)

    assert protector.check_request("1.1.1.1") is True
    assert protector.check_request("1.1.1.1") is True
    assert protector.check_request("1.1.1.1") is False  # exceeds limit


def test_connection_limits_enforced(monkeypatch):
    """Per-IP and global connection caps enforced."""
    protector = DDoSProtector(max_connections_per_ip=1, max_global_connections=1)
    monkeypatch.setattr("time.time", lambda: 0)

    assert protector.register_connection("1.1.1.1") is True
    # Per-IP and global limits now hit
    assert protector.register_connection("1.1.1.1") is False
    assert protector.register_connection("2.2.2.2") is False


def test_adaptive_rate_limit_reduces_and_restores(monkeypatch):
    """Adaptive rate limiting halves under high load and restores on low load."""
    protector = DDoSProtector(rate_limit_per_second=10, max_global_connections=10, adaptive_rate_limiting=True)
    # Force adjustment interval to pass
    protector.last_adjustment_time = 0
    # Simulate high load: 9 connections out of 10 (>80%)
    protector.active_connections = {"ip1": 5, "ip2": 4}
    monkeypatch.setattr("time.time", lambda: 120)

    protector.check_request("3.3.3.3")
    assert protector.rate_limit_per_second == 5  # reduced by 50%

    # Simulate low load to restore base
    protector.active_connections = {"ip1": 1}
    protector.last_adjustment_time = 0
    protector.check_request("4.4.4.4")
    assert protector.rate_limit_per_second == protector.base_rate_limit


def test_cleanup_inactive_ips(monkeypatch):
    """Inactive IPs pruned when max tracked exceeded."""
    protector = DDoSProtector(max_tracked_ips=2, time_window_seconds=1)
    protector.request_timestamps = {
        "old1": deque(),
        "old2": deque([0]),
        "active": deque([100]),
    }
    protector.active_connections = {"old1": 0, "old2": 0, "active": 1}
    protector.last_activity = {"old1": 0, "old2": 0, "active": 100}
    protector.request_timestamps.setdefault("new", deque())
    monkeypatch.setattr("time.time", lambda: 200)

    protector.check_request("new")

    assert "old1" not in protector.request_timestamps  # removed as inactive
    assert "active" in protector.request_timestamps
    assert "new" in protector.request_timestamps
