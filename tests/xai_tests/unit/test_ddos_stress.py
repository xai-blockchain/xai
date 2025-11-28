"""
Comprehensive DDoS protection stress tests

Tests rate limiting, connection limits, adaptive throttling,
and cleanup under high-volume attack scenarios.
"""

import pytest
import time
from unittest.mock import Mock, patch

from xai.network.ddos_protector import DDoSProtector


class TestDDoSStress:
    """Stress tests for DDoS protection"""

    def test_1000_requests_single_ip_should_throttle(self):
        """Test 1000 requests from single IP triggers throttling"""
        protector = DDoSProtector(
            rate_limit_per_second=10,
            time_window_seconds=1
        )

        ip = "192.168.1.100"
        allowed_count = 0
        blocked_count = 0

        # Send 1000 requests rapidly
        for i in range(1000):
            if protector.check_rate_limit(ip):
                allowed_count += 1
            else:
                blocked_count += 1

        # Most requests should be blocked
        assert blocked_count > allowed_count
        # Only about 10 requests per second should be allowed
        assert allowed_count <= 20  # Some tolerance for timing

    def test_10000_requests_from_100_ips(self):
        """Test 10000 requests distributed across 100 IPs"""
        protector = DDoSProtector(
            rate_limit_per_second=10,
            time_window_seconds=1,
            max_tracked_ips=200
        )

        total_allowed = 0
        total_blocked = 0

        # 100 IPs, each sending 100 requests
        for ip_num in range(100):
            ip = f"192.168.1.{ip_num}"
            for _ in range(100):
                if protector.check_rate_limit(ip):
                    total_allowed += 1
                else:
                    total_blocked += 1

        # Each IP gets rate limited individually
        # With 10 req/s limit, ~1000 requests should pass (100 IPs * 10 req/s)
        assert total_allowed > 500  # Reasonable allowance
        assert total_blocked > total_allowed  # Most should be blocked

    def test_connection_limit_enforcement(self):
        """Test maximum connection limit is enforced"""
        protector = DDoSProtector(
            max_connections_per_ip=5,
            max_global_connections=100
        )

        ip = "192.168.1.100"

        # Open 5 connections (should succeed)
        for i in range(5):
            result = protector.add_connection(ip)
            assert result is True

        # 6th connection should fail
        result = protector.add_connection(ip)
        assert result is False

        # Check connection count
        assert protector.active_connections[ip] == 5

    def test_connection_rejection_when_at_limit(self):
        """Test connections are rejected when at global limit"""
        protector = DDoSProtector(
            max_connections_per_ip=10,
            max_global_connections=50
        )

        # Fill up to global limit with different IPs
        for ip_num in range(5):
            ip = f"192.168.1.{ip_num}"
            for _ in range(10):
                protector.add_connection(ip)

        total_connections = sum(protector.active_connections.values())
        assert total_connections == 50

        # Next connection should fail
        new_ip = "192.168.1.99"
        result = protector.add_connection(new_ip)
        assert result is False

    def test_peer_disconnection_frees_slot(self):
        """Test that disconnecting peer frees connection slot"""
        protector = DDoSProtector(max_connections_per_ip=5)

        ip = "192.168.1.100"

        # Fill connections
        for _ in range(5):
            protector.add_connection(ip)

        assert protector.active_connections[ip] == 5

        # Remove one connection
        protector.remove_connection(ip)

        assert protector.active_connections[ip] == 4

        # Should be able to add new connection
        result = protector.add_connection(ip)
        assert result is True
        assert protector.active_connections[ip] == 5

    def test_adaptive_rate_limiting_under_load(self):
        """Test adaptive rate limiting adjusts under high load"""
        protector = DDoSProtector(
            rate_limit_per_second=10,
            adaptive_rate_limiting=True
        )

        # Simulate high load
        for ip_num in range(50):
            ip = f"192.168.1.{ip_num}"
            for _ in range(20):
                protector.check_rate_limit(ip)

        # Adaptive limiting should track load
        # Check that system is tracking many IPs
        assert len(protector.request_timestamps) > 30

    def test_cleanup_of_old_request_tracking(self):
        """Test cleanup removes old request tracking data"""
        protector = DDoSProtector(
            rate_limit_per_second=10,
            time_window_seconds=1,
            max_tracked_ips=50
        )

        # Add many IPs
        for ip_num in range(100):
            ip = f"192.168.1.{ip_num}"
            protector.check_rate_limit(ip)

        # Should trigger cleanup when max_tracked_ips exceeded
        # Cleanup should keep count under or near max
        assert len(protector.request_timestamps) <= 60  # Some tolerance

    def test_legitimate_high_volume_traffic(self):
        """Test legitimate distributed traffic is handled properly"""
        protector = DDoSProtector(
            rate_limit_per_second=10,
            time_window_seconds=1
        )

        # Simulate 20 legitimate users, each sending 5 requests/sec
        # Total: 100 requests/sec
        allowed_requests = []

        for round_num in range(2):  # 2 time windows
            round_allowed = 0
            for ip_num in range(20):
                ip = f"192.168.1.{ip_num}"
                # Each IP sends 5 requests (under limit of 10)
                for _ in range(5):
                    if protector.check_rate_limit(ip):
                        round_allowed += 1
            allowed_requests.append(round_allowed)
            time.sleep(1)  # Wait for next time window

        # Most legitimate traffic should be allowed
        # Each IP sending 5 req/s is under 10 req/s limit
        for count in allowed_requests:
            assert count >= 80  # Allow ~80% of legitimate traffic

    def test_burst_detection_and_throttling(self):
        """Test detection and throttling of burst attacks"""
        protector = DDoSProtector(
            rate_limit_per_second=5,
            time_window_seconds=1
        )

        ip = "192.168.1.100"

        # Send burst of 50 requests
        start_time = time.time()
        allowed_in_burst = 0

        for _ in range(50):
            if protector.check_rate_limit(ip):
                allowed_in_burst += 1

        # Only ~5 requests should be allowed in the burst
        assert allowed_in_burst <= 10  # Small tolerance
        assert allowed_in_burst < 50  # Most blocked

    def test_per_ip_isolation(self):
        """Test that one IP's rate limit doesn't affect others"""
        protector = DDoSProtector(rate_limit_per_second=5)

        ip1 = "192.168.1.100"
        ip2 = "192.168.1.101"

        # Exhaust IP1's rate limit
        for _ in range(20):
            protector.check_rate_limit(ip1)

        # IP2 should still be able to send requests
        allowed_ip2 = 0
        for _ in range(5):
            if protector.check_rate_limit(ip2):
                allowed_ip2 += 1

        # IP2 should not be affected by IP1's exhaustion
        assert allowed_ip2 >= 4  # Most should be allowed

    def test_memory_efficiency_under_attack(self):
        """Test memory usage stays bounded during attack"""
        protector = DDoSProtector(
            max_tracked_ips=100,
            rate_limit_per_second=10
        )

        # Simulate attack from many IPs
        for ip_num in range(500):
            ip = f"192.168.{ip_num // 256}.{ip_num % 256}"
            protector.check_rate_limit(ip)

        # Memory should be bounded by max_tracked_ips
        tracked_count = len(protector.request_timestamps)
        assert tracked_count <= 120  # Close to max_tracked_ips with some tolerance
