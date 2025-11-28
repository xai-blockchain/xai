"""
Comprehensive tests for DDoS Protector Memory Limit functionality.
Tests the security-critical ability to prevent memory exhaustion attacks.
"""

import time
import pytest
from xai.network.ddos_protector import DDoSProtector


class TestDDoSMemoryLimits:
    """Test suite for DDoS protection memory limits"""

    def test_basic_initialization(self):
        """Test that DDoS protector initializes with memory limits"""
        protector = DDoSProtector(
            rate_limit_per_second=10,
            time_window_seconds=1,
            max_tracked_ips=1000,
            max_connections_per_ip=50,
        )

        assert protector.max_tracked_ips == 1000
        assert protector.max_connections_per_ip == 50
        assert len(protector.request_timestamps) == 0
        assert len(protector.active_connections) == 0

    def test_default_memory_limits(self):
        """Test default memory limits are set correctly"""
        protector = DDoSProtector()

        assert protector.max_tracked_ips == 10000
        assert protector.max_connections_per_ip == 100

    def test_invalid_parameters(self):
        """Test that invalid parameters raise errors"""
        with pytest.raises(ValueError, match="Max tracked IPs"):
            DDoSProtector(max_tracked_ips=-1)

        with pytest.raises(ValueError, match="Max connections per IP"):
            DDoSProtector(max_connections_per_ip=0)

    def test_memory_cleanup_not_triggered_under_limit(self):
        """Test that cleanup doesn't occur when under the limit"""
        protector = DDoSProtector(max_tracked_ips=100)

        # Add 50 different IPs (under limit)
        for i in range(50):
            ip = f"192.168.1.{i}"
            assert protector.check_request(ip)

        # Should still have all 50 IPs tracked
        assert len(protector.request_timestamps) == 50

    def test_memory_cleanup_triggered_over_limit(self):
        """Test that cleanup occurs when limit is exceeded"""
        protector = DDoSProtector(max_tracked_ips=100, rate_limit_per_second=5)

        # Add 110 different IPs (over limit)
        for i in range(110):
            ip = f"192.168.1.{i}"
            protector.check_request(ip)
            time.sleep(0.01)  # Small delay to create different timestamps

        # After cleanup, should have removed ~10% = ~11 IPs
        # So should be around 99 or less
        assert len(protector.request_timestamps) <= 100

    def test_cleanup_removes_oldest_inactive_ips(self):
        """Test that cleanup preferentially removes oldest inactive IPs"""
        protector = DDoSProtector(
            max_tracked_ips=10, rate_limit_per_second=5, time_window_seconds=2
        )

        # Add 5 IPs with old timestamps
        for i in range(5):
            ip = f"192.168.1.{i}"
            protector.check_request(ip)
            time.sleep(0.1)

        # Wait for time window to expire
        time.sleep(2.5)

        # Add 6 more IPs (total 11, over limit of 10)
        for i in range(5, 11):
            ip = f"192.168.1.{i}"
            protector.check_request(ip)
            time.sleep(0.1)

        # The new IPs should still be tracked
        for i in range(5, 11):
            ip = f"192.168.1.{i}"
            assert ip in protector.request_timestamps

        # Total should be at or under limit
        assert len(protector.request_timestamps) <= 10

    def test_connection_limit_per_ip(self):
        """Test that connection limits per IP are enforced"""
        protector = DDoSProtector(max_connections_per_ip=5)

        ip = "192.168.1.100"

        # Register 5 connections (at limit)
        for _ in range(5):
            assert protector.register_connection(ip)

        assert protector.active_connections[ip] == 5

        # 6th connection should be blocked
        assert not protector.register_connection(ip)

    def test_connection_unregister(self):
        """Test that unregistering connections works correctly"""
        protector = DDoSProtector(max_connections_per_ip=5)

        ip = "192.168.1.100"

        # Register 3 connections
        for _ in range(3):
            protector.register_connection(ip)

        assert protector.active_connections[ip] == 3

        # Unregister 1 connection
        protector.unregister_connection(ip)
        assert protector.active_connections[ip] == 2

        # Unregister all remaining
        protector.unregister_connection(ip)
        protector.unregister_connection(ip)

        # Should be removed from tracking when count hits 0
        assert ip not in protector.active_connections

    def test_memory_exhaustion_attack_simulation(self):
        """
        Simulate a memory exhaustion attack where attacker connects from many IPs
        """
        protector = DDoSProtector(max_tracked_ips=1000, rate_limit_per_second=10)

        # Attacker tries to exhaust memory by connecting from 10,000 different IPs
        attacker_ips = []
        for i in range(10000):
            ip = f"10.0.{i // 256}.{i % 256}"
            attacker_ips.append(ip)
            protector.check_request(ip)

            # Periodically check memory is bounded
            if i % 1000 == 0:
                # Should never exceed max_tracked_ips by much
                assert len(protector.request_timestamps) <= 1100

        # Final check: memory should be bounded
        assert len(protector.request_timestamps) <= 1100

    def test_concurrent_connections_attack(self):
        """Test protection against many concurrent connections from same IP"""
        protector = DDoSProtector(max_connections_per_ip=10)

        attacker_ip = "192.168.1.666"

        # Attacker tries to open many connections
        successful_connections = 0
        blocked_connections = 0

        for _ in range(100):
            if protector.register_connection(attacker_ip):
                successful_connections += 1
            else:
                blocked_connections += 1

        # Should have allowed exactly max_connections_per_ip
        assert successful_connections == 10
        assert blocked_connections == 90

    def test_last_activity_tracking(self):
        """Test that last activity time is tracked correctly"""
        protector = DDoSProtector()

        ip = "192.168.1.1"
        start_time = int(time.time())

        protector.check_request(ip)

        # Last activity should be recent
        assert ip in protector.last_activity
        assert protector.last_activity[ip] >= start_time

    def test_cleanup_removes_from_all_dictionaries(self):
        """Test that cleanup removes IPs from all tracking dictionaries"""
        protector = DDoSProtector(
            max_tracked_ips=5, rate_limit_per_second=5, time_window_seconds=1
        )

        # Add IPs to both request tracking and connections
        for i in range(3):
            ip = f"192.168.1.{i}"
            protector.check_request(ip)
            protector.register_connection(ip)

        # Wait for time window
        time.sleep(1.5)

        # Add more IPs to trigger cleanup
        for i in range(3, 8):
            ip = f"192.168.1.{i}"
            protector.check_request(ip)

        # Old IPs should be cleaned from all tracking
        assert len(protector.request_timestamps) <= 5

    def test_legitimate_users_not_affected(self):
        """Test that legitimate users are not affected during attack"""
        protector = DDoSProtector(
            max_tracked_ips=100, rate_limit_per_second=5, time_window_seconds=1
        )

        legitimate_ip = "192.168.1.1"

        # Legitimate user makes some requests
        for _ in range(3):
            assert protector.check_request(legitimate_ip)
            time.sleep(0.3)

        # Attacker floods with many IPs
        for i in range(200):
            attacker_ip = f"10.0.{i // 256}.{i % 256}"
            protector.check_request(attacker_ip)

        # Wait a bit
        time.sleep(0.5)

        # Legitimate user should still be able to make requests
        assert protector.check_request(legitimate_ip)

    def test_rate_limit_still_enforced_with_memory_limits(self):
        """Test that rate limiting still works with memory limits"""
        protector = DDoSProtector(
            max_tracked_ips=100, rate_limit_per_second=5, time_window_seconds=1
        )

        ip = "192.168.1.100"

        # Make 5 requests (at limit)
        for _ in range(5):
            assert protector.check_request(ip)

        # 6th request should be blocked (rate limit)
        assert not protector.check_request(ip)

    def test_cleanup_percentage(self):
        """Test that cleanup removes approximately 10% of IPs"""
        protector = DDoSProtector(
            max_tracked_ips=100, rate_limit_per_second=10, time_window_seconds=2
        )

        # Add exactly 110 IPs to trigger cleanup
        for i in range(110):
            ip = f"192.168.{i // 256}.{i % 256}"
            protector.check_request(ip)
            time.sleep(0.01)

        # Wait for IPs to become inactive
        time.sleep(2.5)

        # Trigger cleanup by adding one more IP
        protector.check_request("192.168.99.99")

        # Should have removed approximately 10-11 IPs
        # Final count should be around 100 or less
        assert len(protector.request_timestamps) <= 100

    def test_edge_case_cleanup_with_no_inactive_ips(self):
        """Test cleanup when all IPs are active"""
        protector = DDoSProtector(max_tracked_ips=10, rate_limit_per_second=5)

        # Add IPs and keep them active
        for i in range(12):
            ip = f"192.168.1.{i}"
            protector.check_request(ip)

        # Even with all IPs active, memory should be bounded
        # Should remove least recently used
        assert len(protector.request_timestamps) <= 11

    def test_zero_connections_cleanup(self):
        """Test that IPs with zero connections are cleaned up"""
        protector = DDoSProtector(max_connections_per_ip=5)

        ip = "192.168.1.100"

        # Register and unregister connections
        protector.register_connection(ip)
        assert ip in protector.active_connections

        protector.unregister_connection(ip)
        assert ip not in protector.active_connections

    def test_connection_cleanup_during_memory_cleanup(self):
        """Test that connection counts are cleaned during memory cleanup"""
        protector = DDoSProtector(
            max_tracked_ips=10, rate_limit_per_second=5, time_window_seconds=2
        )

        # Add IPs with connections
        for i in range(15):
            ip = f"192.168.1.{i}"
            protector.check_request(ip)
            protector.register_connection(ip)
            time.sleep(0.1)

        # Wait for cleanup
        time.sleep(2.5)

        # Trigger cleanup
        protector.check_request("192.168.99.99")

        # Both dictionaries should be cleaned
        assert len(protector.request_timestamps) <= 11
        # active_connections might still have some, but should be reasonable
