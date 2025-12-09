"""
Unit tests for EclipseProtector.

Coverage targets:
- Per-IP connection caps
- Risk detection based on diversity thresholds
- Disconnect handling updates accounting
"""

import pytest

from xai.network.eclipse_protector import EclipseProtector


def test_connect_enforces_per_ip_limit():
    protector = EclipseProtector(max_connections_per_ip=1, min_diverse_peers=2)
    protector.connect_peer("1.1.1.1")
    with pytest.raises(ValueError, match="Exceeds max connections per IP"):
        protector.connect_peer("1.1.1.1")


def test_risk_detected_when_not_diverse():
    protector = EclipseProtector(max_connections_per_ip=2, min_diverse_peers=3)
    protector.connect_peer("1.1.1.1")
    protector.connect_peer("2.2.2.2")
    assert protector.check_for_eclipse_risk() is True  # only 2 unique < 3


def test_disconnect_updates_counts_and_risk():
    protector = EclipseProtector(max_connections_per_ip=2, min_diverse_peers=2)
    p1 = protector.connect_peer("1.1.1.1")
    p2 = protector.connect_peer("2.2.2.2")
    assert protector.check_for_eclipse_risk() is False

    protector.disconnect_peer(p1)
    assert "1.1.1.1" not in protector.connections_by_ip
    assert protector.check_for_eclipse_risk() is True
