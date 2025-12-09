"""
Unit tests for PacketFilter.

Coverage targets:
- Port allowlist enforcement
- Blocked IP enforcement
- Add/remove operations
"""

import pytest

from xai.network.packet_filter import PacketFilter


def test_filter_blocked_ip_and_port_allowlist():
    pf = PacketFilter(default_allowed_ports=[80])
    pf.add_blocked_ip("1.1.1.1")

    assert pf.filter_packet("1.1.1.1", 80) is False  # blocked IP
    assert pf.filter_packet("2.2.2.2", 22) is False  # port not allowed

    pf.add_allowed_port(22)
    assert pf.filter_packet("2.2.2.2", 22) is True


def test_add_remove_ports_and_blocklist():
    pf = PacketFilter()
    with pytest.raises(ValueError):
        pf.add_allowed_port(-1)

    pf.add_allowed_port(443)
    assert pf.filter_packet("3.3.3.3", 443) is True

    pf.remove_allowed_port(443)
    assert pf.filter_packet("3.3.3.3", 443) is False

    pf.add_blocked_ip("4.4.4.4")
    pf.remove_blocked_ip("4.4.4.4")
    pf.add_allowed_port(8080)
    assert pf.filter_packet("4.4.4.4", 8080) is True
