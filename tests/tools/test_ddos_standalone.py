#!/usr/bin/env python3
from __future__ import annotations

"""
Standalone test for DDoS Memory Limits functionality.
Tests the core algorithm without requiring full dependencies.
"""

import time
from collections import defaultdict, deque

class DDoSProtectorTest:
    """Simplified DDoS protector for testing"""

    def __init__(
        self,
        rate_limit_per_second: int = 10,
        time_window_seconds: int = 1,
        max_tracked_ips: int = 10000,
        max_connections_per_ip: int = 100,
    ):
        self.rate_limit_per_second = rate_limit_per_second
        self.time_window_seconds = time_window_seconds
        self.max_tracked_ips = max_tracked_ips
        self.max_connections_per_ip = max_connections_per_ip

        self.request_timestamps: dict[str, deque[int]] = defaultdict(deque)
        self.active_connections: dict[str, int] = defaultdict(int)
        self.last_activity: dict[str, int] = {}

    def _clean_old_requests(self, ip_address: str, current_time: int):
        """Remove old timestamps"""
        while (
            self.request_timestamps[ip_address]
            and self.request_timestamps[ip_address][0]
            <= (current_time - self.time_window_seconds)
        ):
            self.request_timestamps[ip_address].popleft()

    def _clean_old_ips(self, current_time: int):
        """Clean up inactive IPs to prevent memory growth"""
        num_tracked = len(self.request_timestamps)

        if num_tracked <= self.max_tracked_ips:
            return

        num_to_remove = max(1, num_tracked // 10)

        inactive_ips = []
        for ip_address in list(self.request_timestamps.keys()):
            if not self.request_timestamps[ip_address]:
                inactive_ips.append((ip_address, 0))
            else:
                last_request_time = self.request_timestamps[ip_address][-1]
                if last_request_time <= (current_time - self.time_window_seconds):
                    inactive_ips.append((ip_address, last_request_time))

        if len(inactive_ips) < num_to_remove:
            all_ips_with_time = []
            for ip_address in self.request_timestamps.keys():
                if self.request_timestamps[ip_address]:
                    last_time = self.request_timestamps[ip_address][-1]
                    all_ips_with_time.append((ip_address, last_time))

            all_ips_with_time.sort(key=lambda x: x[1])
            inactive_ips = all_ips_with_time[:num_to_remove]
        else:
            inactive_ips.sort(key=lambda x: x[1])
            inactive_ips = inactive_ips[:num_to_remove]

        for ip_address, _ in inactive_ips:
            if ip_address in self.request_timestamps:
                del self.request_timestamps[ip_address]
            if ip_address in self.active_connections:
                del self.active_connections[ip_address]
            if ip_address in self.last_activity:
                del self.last_activity[ip_address]

    def check_request(self, ip_address: str) -> bool:
        """Check if request should be allowed"""
        current_time = int(time.time())

        self._clean_old_ips(current_time)
        self._clean_old_requests(ip_address, current_time)

        self.last_activity[ip_address] = current_time

        if len(self.request_timestamps[ip_address]) >= self.rate_limit_per_second:
            return False

        self.request_timestamps[ip_address].append(current_time)
        return True

    def register_connection(self, ip_address: str) -> bool:
        """Register a new connection"""
        current_time = int(time.time())

        self._clean_old_ips(current_time)

        if self.active_connections[ip_address] >= self.max_connections_per_ip:
            return False

        self.active_connections[ip_address] += 1
        self.last_activity[ip_address] = current_time
        return True

    def unregister_connection(self, ip_address: str):
        """Unregister a connection"""
        if ip_address in self.active_connections:
            self.active_connections[ip_address] = max(
                0, self.active_connections[ip_address] - 1
            )

            if self.active_connections[ip_address] == 0:
                del self.active_connections[ip_address]

def test_ddos_protector():
    """Test DDoS protector functionality"""
    print("=" * 70)
    print("DDOS MEMORY LIMITS - STANDALONE TEST")
    print("=" * 70)

    # Test 1: Basic initialization
    print("\n[TEST 1] Initialization...")
    protector = DDoSProtectorTest(
        rate_limit_per_second=10,
        time_window_seconds=1,
        max_tracked_ips=1000,
        max_connections_per_ip=50,
    )

    assert protector.max_tracked_ips == 1000
    assert protector.max_connections_per_ip == 50
    print("✓ Initialization: PASS")

    # Test 2: Memory not cleaned under limit
    print("\n[TEST 2] No cleanup when under limit...")
    protector = DDoSProtectorTest(max_tracked_ips=100)

    for i in range(50):
        ip = f"192.168.1.{i}"
        protector.check_request(ip)

    assert len(protector.request_timestamps) == 50
    print("✓ No cleanup under limit: PASS")

    # Test 3: Memory cleanup over limit
    print("\n[TEST 3] Cleanup when over limit...")
    protector = DDoSProtectorTest(max_tracked_ips=100, rate_limit_per_second=5)

    for i in range(110):
        ip = f"192.168.{i // 256}.{i % 256}"
        protector.check_request(ip)
        time.sleep(0.001)

    tracked = len(protector.request_timestamps)
    print(f"  Tracked IPs: {tracked} (limit: 100)")
    assert tracked <= 105  # Allow small overshoot
    print("✓ Cleanup triggered: PASS")

    # Test 4: Connection limits
    print("\n[TEST 4] Connection limits per IP...")
    protector = DDoSProtectorTest(max_connections_per_ip=5)

    ip = "192.168.1.100"

    for _ in range(5):
        assert protector.register_connection(ip)

    assert protector.active_connections[ip] == 5
    assert not protector.register_connection(ip)  # 6th should fail
    print("✓ Connection limits enforced: PASS")

    # Test 5: Connection cleanup
    print("\n[TEST 5] Connection cleanup...")
    protector.unregister_connection(ip)
    assert protector.active_connections[ip] == 4

    for _ in range(4):
        protector.unregister_connection(ip)

    assert ip not in protector.active_connections
    print("✓ Connection cleanup: PASS")

    # Test 6: Memory exhaustion attack
    print("\n[TEST 6] Memory exhaustion attack (5000 IPs)...")
    protector = DDoSProtectorTest(max_tracked_ips=1000, rate_limit_per_second=10)

    max_memory = 0
    for i in range(5000):
        ip = f"10.{i // 65536}.{(i // 256) % 256}.{i % 256}"
        protector.check_request(ip)

        current_memory = len(protector.request_timestamps)
        max_memory = max(max_memory, current_memory)

        if i % 1000 == 0 and i > 0:
            print(f"  After {i} IPs: tracking {current_memory} IPs")

    print(f"  Peak memory: {max_memory} IPs (limit: 1000)")
    assert max_memory <= 1100
    print("✓ Memory bounded during attack: PASS")

    # Test 7: Concurrent connections attack
    print("\n[TEST 7] Concurrent connections attack...")
    protector = DDoSProtectorTest(max_connections_per_ip=10)

    attacker_ip = "192.168.1.666"
    successful = 0
    blocked = 0

    for _ in range(100):
        if protector.register_connection(attacker_ip):
            successful += 1
        else:
            blocked += 1

    print(f"  Allowed: {successful}, Blocked: {blocked}")
    assert successful == 10
    assert blocked == 90
    print("✓ Connection flood blocked: PASS")

    # Test 8: Rate limiting
    print("\n[TEST 8] Rate limiting...")
    protector = DDoSProtectorTest(rate_limit_per_second=5, time_window_seconds=1)

    ip = "192.168.1.99"

    for _ in range(5):
        assert protector.check_request(ip)

    assert not protector.check_request(ip)  # 6th should fail
    print("✓ Rate limiting works: PASS")

    # Test 9: Cleanup percentage
    print("\n[TEST 9] Cleanup removes ~10%...")
    protector = DDoSProtectorTest(
        max_tracked_ips=100, rate_limit_per_second=10, time_window_seconds=2
    )

    # Add 110 IPs
    for i in range(110):
        ip = f"192.168.{i // 256}.{i % 256}"
        protector.check_request(ip)
        time.sleep(0.001)

    # Wait for IPs to become inactive
    time.sleep(2.5)

    # Trigger cleanup
    protector.check_request("192.168.99.99")

    tracked = len(protector.request_timestamps)
    print(f"  After cleanup: {tracked} IPs (target: ~100)")
    assert tracked <= 101
    print("✓ Cleanup percentage correct: PASS")

    # Test 10: Last activity tracking
    print("\n[TEST 10] Last activity tracking...")
    protector = DDoSProtectorTest()

    ip = "192.168.1.1"
    start_time = int(time.time())

    protector.check_request(ip)

    assert ip in protector.last_activity
    assert protector.last_activity[ip] >= start_time
    print("✓ Last activity tracked: PASS")

    print("\n" + "=" * 70)
    print("✅ ALL DDOS MEMORY LIMIT TESTS PASSED!")
    print("=" * 70)
    return True

if __name__ == "__main__":
    import sys

    try:
        test_ddos_protector()
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
