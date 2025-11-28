import time
from collections import defaultdict, deque
from typing import Dict, Deque, Tuple


class DDoSProtector:
    def __init__(
        self,
        rate_limit_per_second: int = 10,
        time_window_seconds: int = 1,
        max_tracked_ips: int = 10000,
        max_connections_per_ip: int = 100,
        max_global_connections: int = 10000,
        adaptive_rate_limiting: bool = True,
    ):
        if not isinstance(rate_limit_per_second, int) or rate_limit_per_second <= 0:
            raise ValueError("Rate limit per second must be a positive integer.")
        if not isinstance(time_window_seconds, int) or time_window_seconds <= 0:
            raise ValueError("Time window seconds must be a positive integer.")
        if not isinstance(max_tracked_ips, int) or max_tracked_ips <= 0:
            raise ValueError("Max tracked IPs must be a positive integer.")
        if not isinstance(max_connections_per_ip, int) or max_connections_per_ip <= 0:
            raise ValueError("Max connections per IP must be a positive integer.")
        if not isinstance(max_global_connections, int) or max_global_connections <= 0:
            raise ValueError("Max global connections must be a positive integer.")

        self.rate_limit_per_second = rate_limit_per_second
        self.base_rate_limit = rate_limit_per_second  # Store original for adaptive adjustment
        self.time_window_seconds = time_window_seconds
        self.max_tracked_ips = max_tracked_ips
        self.max_connections_per_ip = max_connections_per_ip
        self.max_global_connections = max_global_connections
        self.adaptive_rate_limiting = adaptive_rate_limiting

        # Stores requests: {ip_address: deque of timestamps}
        self.request_timestamps: Dict[str, Deque[int]] = defaultdict(deque)

        # Track active connections per IP
        self.active_connections: Dict[str, int] = defaultdict(int)

        # Track last activity time for each IP (for cleanup)
        self.last_activity: Dict[str, int] = {}

        # Adaptive rate limiting state
        self.total_requests_in_window = 0
        self.last_adjustment_time = int(time.time())
        self.adjustment_interval = 60  # Adjust rate limit every 60 seconds

        print(
            f"DDoSProtector initialized. Rate limit: {self.rate_limit_per_second} req/s within {self.time_window_seconds}s window. "
            f"Max tracked IPs: {self.max_tracked_ips}, Max connections per IP: {self.max_connections_per_ip}"
        )

    def _clean_old_requests(self, ip_address: str, current_time: int):
        """Removes timestamps outside the current time window for a given IP."""
        while self.request_timestamps[ip_address] and self.request_timestamps[ip_address][0] <= (
            current_time - self.time_window_seconds
        ):
            self.request_timestamps[ip_address].popleft()

    def _clean_old_ips(self, current_time: int):
        """
        Clean up inactive IPs to prevent unbounded memory growth.

        This method is called when the number of tracked IPs exceeds the maximum.
        It removes the oldest 10% of inactive IPs (IPs with no recent requests).

        Security rationale:
        - Prevents memory exhaustion attacks where attacker connects from many IPs
        - Keeps memory usage bounded while still tracking legitimate active users
        - Removes oldest inactive IPs first (least likely to reconnect soon)

        Args:
            current_time: Current timestamp for determining inactivity
        """
        num_tracked = len(self.request_timestamps)

        if num_tracked <= self.max_tracked_ips:
            return  # No cleanup needed

        # Calculate how many IPs to remove (10% of tracked IPs)
        num_to_remove = max(1, num_tracked // 10)

        # Find inactive IPs (no requests in current time window)
        inactive_ips = []
        for ip_address in list(self.request_timestamps.keys()):
            # IP is inactive if it has no recent requests
            if not self.request_timestamps[ip_address]:
                inactive_ips.append((ip_address, 0))
            else:
                # Get last activity time for this IP
                last_request_time = self.request_timestamps[ip_address][-1]
                if last_request_time <= (current_time - self.time_window_seconds):
                    inactive_ips.append((ip_address, last_request_time))

        # If we don't have enough inactive IPs, also consider least recently used
        if len(inactive_ips) < num_to_remove:
            # Get all IPs sorted by last activity (oldest first)
            all_ips_with_time = []
            for ip_address in self.request_timestamps.keys():
                if self.request_timestamps[ip_address]:
                    last_time = self.request_timestamps[ip_address][-1]
                    all_ips_with_time.append((ip_address, last_time))

            # Sort by last activity time (oldest first)
            all_ips_with_time.sort(key=lambda x: x[1])
            inactive_ips = all_ips_with_time[:num_to_remove]
        else:
            # Sort inactive IPs by last activity (oldest first)
            inactive_ips.sort(key=lambda x: x[1])
            inactive_ips = inactive_ips[:num_to_remove]

        # Remove the selected IPs
        removed_count = 0
        for ip_address, _ in inactive_ips:
            if ip_address in self.request_timestamps:
                del self.request_timestamps[ip_address]
                removed_count += 1

            # Also clean up from other tracking dictionaries
            if ip_address in self.active_connections:
                del self.active_connections[ip_address]
            if ip_address in self.last_activity:
                del self.last_activity[ip_address]

        if removed_count > 0:
            print(
                f"DDoSProtector: Cleaned up {removed_count} inactive IPs. "
                f"Tracked IPs: {len(self.request_timestamps)}/{self.max_tracked_ips}"
            )

    def _adjust_rate_limit(self, current_time: int):
        """
        Adaptive rate limiting: Adjust rate limits based on network load.

        During high load periods, temporarily reduce rate limits to protect the network.
        During low load periods, increase rate limits to allow more throughput.

        This helps prevent DoS attacks during high traffic while maximizing performance
        during normal operation.
        """
        if not self.adaptive_rate_limiting:
            return

        # Only adjust every adjustment_interval seconds
        if current_time - self.last_adjustment_time < self.adjustment_interval:
            return

        # Calculate total active connections
        total_connections = sum(self.active_connections.values())
        connection_load = total_connections / self.max_global_connections

        # Adjust rate limit based on load
        if connection_load > 0.8:  # High load (>80%)
            # Reduce rate limit by 50% during high load
            new_rate_limit = max(1, int(self.base_rate_limit * 0.5))
            if new_rate_limit != self.rate_limit_per_second:
                print(f"DDoSProtector: High load detected ({connection_load:.1%}). Reducing rate limit to {new_rate_limit} req/s")
                self.rate_limit_per_second = new_rate_limit
        elif connection_load < 0.5:  # Low load (<50%)
            # Restore normal rate limit during low load
            if self.rate_limit_per_second != self.base_rate_limit:
                print(f"DDoSProtector: Load normalized ({connection_load:.1%}). Restoring rate limit to {self.base_rate_limit} req/s")
                self.rate_limit_per_second = self.base_rate_limit

        self.last_adjustment_time = current_time

    def check_request(self, ip_address: str) -> bool:
        """
        Checks if an incoming request from an IP address exceeds the rate limit.

        This method implements multiple layers of DoS protection:
        1. Rate limiting per IP address
        2. Memory cleanup when tracking too many IPs
        3. Per-IP connection limits
        4. Adaptive rate limiting based on network load

        Returns True if allowed, False if blocked.
        """
        current_time = int(time.time())

        # Adjust rate limits based on network load (adaptive)
        self._adjust_rate_limit(current_time)

        # First, check if we need to clean up old IPs (prevent memory exhaustion)
        self._clean_old_ips(current_time)

        # Clean old requests for this specific IP
        self._clean_old_requests(ip_address, current_time)

        # Update last activity time
        self.last_activity[ip_address] = current_time

        # Check rate limit
        if len(self.request_timestamps[ip_address]) >= self.rate_limit_per_second:
            print(
                f"!!! DDoS ALERT !!! IP {ip_address} blocked due to rate limit ({self.rate_limit_per_second} req/{self.time_window_seconds}s) exceeded. "
                f"Current requests in window: {len(self.request_timestamps[ip_address])}"
            )
            return False

        # Add request timestamp
        self.request_timestamps[ip_address].append(current_time)
        return True

    def register_connection(self, ip_address: str) -> bool:
        """
        Register a new connection from an IP address.

        Implements connection-level DoS protection by limiting the number of
        concurrent connections from a single IP address and globally across all IPs.

        Args:
            ip_address: IP address attempting to connect

        Returns:
            True if connection allowed, False if blocked
        """
        current_time = int(time.time())

        # Clean up old IPs if needed
        self._clean_old_ips(current_time)

        # Check global connection limit first
        total_connections = sum(self.active_connections.values())
        if total_connections >= self.max_global_connections:
            print(
                f"!!! DDoS ALERT !!! Global connection limit reached. "
                f"Total connections: {total_connections}/{self.max_global_connections}. "
                f"Connection from {ip_address} rejected."
            )
            return False

        # Check connection limit for this IP
        if self.active_connections[ip_address] >= self.max_connections_per_ip:
            print(
                f"!!! DDoS ALERT !!! IP {ip_address} blocked due to connection limit exceeded. "
                f"Active connections: {self.active_connections[ip_address]}/{self.max_connections_per_ip}"
            )
            return False

        # Register the connection
        self.active_connections[ip_address] += 1
        self.last_activity[ip_address] = current_time
        return True

    def unregister_connection(self, ip_address: str):
        """
        Unregister a connection when it closes.

        Args:
            ip_address: IP address of the closing connection
        """
        if ip_address in self.active_connections:
            self.active_connections[ip_address] = max(0, self.active_connections[ip_address] - 1)

            # Clean up completely if no more connections
            if self.active_connections[ip_address] == 0:
                del self.active_connections[ip_address]


# Example Usage (for testing purposes)
if __name__ == "__main__":
    protector = DDoSProtector(rate_limit_per_second=5, time_window_seconds=1)

    attacker_ip = "192.168.1.100"
    legit_ip = "192.168.1.1"

    print("\n--- Legitimate Requests ---")
    for i in range(3):
        print(
            f"Request {i+1} from {legit_ip}: {'Allowed' if protector.check_request(legit_ip) else 'Blocked'}"
        )
        time.sleep(0.1)  # Simulate some delay

    print("\n--- Attacker IP exceeding rate limit ---")
    for i in range(10):
        print(
            f"Request {i+1} from {attacker_ip}: {'Allowed' if protector.check_request(attacker_ip) else 'Blocked'}"
        )
        time.sleep(0.1)  # Rapid requests

    print("\n--- Legitimate IP after attacker ---")
    print(
        f"Request from {legit_ip}: {'Allowed' if protector.check_request(legit_ip) else 'Blocked'}"
    )

    print("\n--- Attacker IP after time window reset ---")
    time.sleep(protector.time_window_seconds + 0.5)  # Wait for time window to pass
    print(
        f"Request from {attacker_ip} after reset: {'Allowed' if protector.check_request(attacker_ip) else 'Blocked'}"
    )
    print(
        f"Request from {attacker_ip} (again): {'Allowed' if protector.check_request(attacker_ip) else 'Blocked'}"
    )
