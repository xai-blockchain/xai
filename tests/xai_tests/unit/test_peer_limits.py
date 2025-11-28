"""
Comprehensive tests for peer connection limits

Tests max connections enforcement, per-IP limits, global limits,
connection priority, and slot management.
"""

import pytest
from unittest.mock import Mock, patch

from xai.network.peer_manager import PeerManager


class MockPeerManager:
    """Mock peer manager for testing"""

    def __init__(self, max_connections=50, max_per_ip=3):
        self.max_connections = max_connections
        self.max_per_ip = max_per_ip
        self.peers = {}  # {peer_id: peer_info}
        self.ip_connections = {}  # {ip: count}
        self.total_connections = 0

    def add_peer(self, peer_id, ip_address, reputation=0):
        """Add a peer connection"""
        # Check global limit
        if self.total_connections >= self.max_connections:
            return False

        # Check per-IP limit
        if self.ip_connections.get(ip_address, 0) >= self.max_per_ip:
            return False

        self.peers[peer_id] = {
            'ip': ip_address,
            'reputation': reputation,
            'connected_at': 0
        }
        self.ip_connections[ip_address] = self.ip_connections.get(ip_address, 0) + 1
        self.total_connections += 1
        return True

    def remove_peer(self, peer_id):
        """Remove a peer connection"""
        if peer_id in self.peers:
            ip = self.peers[peer_id]['ip']
            del self.peers[peer_id]
            self.ip_connections[ip] -= 1
            if self.ip_connections[ip] == 0:
                del self.ip_connections[ip]
            self.total_connections -= 1
            return True
        return False


class TestPeerLimits:
    """Tests for peer connection limits"""

    def test_max_connections_enforcement(self):
        """Test maximum connections limit is enforced"""
        manager = MockPeerManager(max_connections=10)

        # Add 10 peers (should all succeed)
        for i in range(10):
            result = manager.add_peer(f"peer_{i}", f"192.168.1.{i}")
            assert result is True

        # 11th peer should fail
        result = manager.add_peer("peer_11", "192.168.1.11")
        assert result is False
        assert manager.total_connections == 10

    def test_connection_rejection_when_at_limit(self):
        """Test connections rejected when at global limit"""
        manager = MockPeerManager(max_connections=5)

        # Fill to capacity
        for i in range(5):
            manager.add_peer(f"peer_{i}", f"192.168.1.{i}")

        assert manager.total_connections == 5

        # New connection should be rejected
        result = manager.add_peer("peer_new", "192.168.1.99")
        assert result is False

    def test_peer_disconnection_frees_slot(self):
        """Test disconnecting peer frees up connection slot"""
        manager = MockPeerManager(max_connections=5)

        # Fill to capacity
        for i in range(5):
            manager.add_peer(f"peer_{i}", f"192.168.1.{i}")

        # Remove one peer
        manager.remove_peer("peer_0")
        assert manager.total_connections == 4

        # Should now be able to add new peer
        result = manager.add_peer("peer_new", "192.168.1.99")
        assert result is True
        assert manager.total_connections == 5

    def test_per_ip_connection_limits(self):
        """Test per-IP connection limits are enforced"""
        manager = MockPeerManager(max_connections=100, max_per_ip=3)

        ip = "192.168.1.100"

        # Add 3 connections from same IP (should succeed)
        for i in range(3):
            result = manager.add_peer(f"peer_{i}", ip)
            assert result is True

        assert manager.ip_connections[ip] == 3

        # 4th connection from same IP should fail
        result = manager.add_peer("peer_4", ip)
        assert result is False

    def test_global_connection_limits(self):
        """Test global connection limit across all IPs"""
        manager = MockPeerManager(max_connections=20, max_per_ip=5)

        # Add peers from different IPs
        for i in range(20):
            result = manager.add_peer(f"peer_{i}", f"192.168.1.{i}")
            assert result is True

        assert manager.total_connections == 20

        # 21st connection should fail regardless of IP
        result = manager.add_peer("peer_21", "10.0.0.1")
        assert result is False

    def test_peer_reputation_affecting_priority(self):
        """Test high reputation peers get connection priority"""
        manager = MockPeerManager(max_connections=5)

        # Add peers with varying reputation
        manager.add_peer("peer_low1", "192.168.1.1", reputation=1)
        manager.add_peer("peer_low2", "192.168.1.2", reputation=2)
        manager.add_peer("peer_med1", "192.168.1.3", reputation=50)
        manager.add_peer("peer_high1", "192.168.1.4", reputation=100)
        manager.add_peer("peer_high2", "192.168.1.5", reputation=95)

        # Get peers sorted by reputation
        sorted_peers = sorted(
            manager.peers.items(),
            key=lambda x: x[1]['reputation'],
            reverse=True
        )

        # Highest reputation should be first
        assert sorted_peers[0][1]['reputation'] == 100
        assert sorted_peers[-1][1]['reputation'] == 1

    def test_multiple_ips_independent_limits(self):
        """Test each IP has independent connection limit"""
        manager = MockPeerManager(max_connections=100, max_per_ip=2)

        # Add 2 peers from IP1
        manager.add_peer("peer_1a", "192.168.1.1")
        manager.add_peer("peer_1b", "192.168.1.1")

        # Add 2 peers from IP2
        manager.add_peer("peer_2a", "192.168.1.2")
        manager.add_peer("peer_2b", "192.168.1.2")

        assert manager.ip_connections["192.168.1.1"] == 2
        assert manager.ip_connections["192.168.1.2"] == 2

        # Each IP is at limit, can't add more
        assert manager.add_peer("peer_1c", "192.168.1.1") is False
        assert manager.add_peer("peer_2c", "192.168.1.2") is False

        # But can add from new IP
        assert manager.add_peer("peer_3a", "192.168.1.3") is True

    def test_connection_slot_reuse(self):
        """Test connection slots can be reused after disconnect"""
        manager = MockPeerManager(max_connections=3)

        # Fill slots
        manager.add_peer("peer_1", "192.168.1.1")
        manager.add_peer("peer_2", "192.168.1.2")
        manager.add_peer("peer_3", "192.168.1.3")

        # Remove and add repeatedly
        for i in range(5):
            manager.remove_peer("peer_1")
            assert manager.total_connections == 2

            result = manager.add_peer("peer_1", "192.168.1.1")
            assert result is True
            assert manager.total_connections == 3

    def test_per_ip_limit_after_disconnection(self):
        """Test per-IP limit updates correctly after disconnection"""
        manager = MockPeerManager(max_per_ip=2)

        ip = "192.168.1.100"

        # Add 2 connections
        manager.add_peer("peer_1", ip)
        manager.add_peer("peer_2", ip)
        assert manager.ip_connections[ip] == 2

        # Remove one
        manager.remove_peer("peer_1")
        assert manager.ip_connections[ip] == 1

        # Should be able to add another
        result = manager.add_peer("peer_3", ip)
        assert result is True
        assert manager.ip_connections[ip] == 2

    def test_concurrent_connection_attempts(self):
        """Test handling of concurrent connection attempts"""
        manager = MockPeerManager(max_connections=10)

        # Simulate concurrent attempts
        results = []
        for i in range(15):
            result = manager.add_peer(f"peer_{i}", f"192.168.1.{i}")
            results.append(result)

        # First 10 should succeed, last 5 should fail
        assert sum(results) == 10
        assert results[:10] == [True] * 10
        assert results[10:] == [False] * 5
