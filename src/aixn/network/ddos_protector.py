import time
from collections import defaultdict, deque
from typing import Dict, Deque, Tuple

class DDoSProtector:
    def __init__(self, rate_limit_per_second: int = 10, time_window_seconds: int = 1):
        if not isinstance(rate_limit_per_second, int) or rate_limit_per_second <= 0:
            raise ValueError("Rate limit per second must be a positive integer.")
        if not isinstance(time_window_seconds, int) or time_window_seconds <= 0:
            raise ValueError("Time window seconds must be a positive integer.")

        self.rate_limit_per_second = rate_limit_per_second
        self.time_window_seconds = time_window_seconds
        
        # Stores requests: {ip_address: deque of timestamps}
        self.request_timestamps: Dict[str, Deque[int]] = defaultdict(deque)
        print(f"DDoSProtector initialized. Rate limit: {self.rate_limit_per_second} req/s within {self.time_window_seconds}s window.")

    def _clean_old_requests(self, ip_address: str, current_time: int):
        """Removes timestamps outside the current time window for a given IP."""
        while self.request_timestamps[ip_address] and \
              self.request_timestamps[ip_address][0] <= (current_time - self.time_window_seconds):
            self.request_timestamps[ip_address].popleft()

    def check_request(self, ip_address: str) -> bool:
        """
        Checks if an incoming request from an IP address exceeds the rate limit.
        Returns True if allowed, False if blocked.
        """
        current_time = int(time.time())
        self._clean_old_requests(ip_address, current_time)

        if len(self.request_timestamps[ip_address]) >= self.rate_limit_per_second:
            print(f"!!! DDoS ALERT !!! IP {ip_address} blocked due to rate limit ({self.rate_limit_per_second} req/{self.time_window_seconds}s) exceeded. "
                  f"Current requests in window: {len(self.request_timestamps[ip_address])}")
            return False
        
        self.request_timestamps[ip_address].append(current_time)
        # print(f"Request from {ip_address} allowed. Current requests in window: {len(self.request_timestamps[ip_address])}")
        return True

# Example Usage (for testing purposes)
if __name__ == "__main__":
    protector = DDoSProtector(rate_limit_per_second=5, time_window_seconds=1)

    attacker_ip = "192.168.1.100"
    legit_ip = "192.168.1.1"

    print("\n--- Legitimate Requests ---")
    for i in range(3):
        print(f"Request {i+1} from {legit_ip}: {'Allowed' if protector.check_request(legit_ip) else 'Blocked'}")
        time.sleep(0.1) # Simulate some delay

    print("\n--- Attacker IP exceeding rate limit ---")
    for i in range(10):
        print(f"Request {i+1} from {attacker_ip}: {'Allowed' if protector.check_request(attacker_ip) else 'Blocked'}")
        time.sleep(0.1) # Rapid requests

    print("\n--- Legitimate IP after attacker ---")
    print(f"Request from {legit_ip}: {'Allowed' if protector.check_request(legit_ip) else 'Blocked'}")

    print("\n--- Attacker IP after time window reset ---")
    time.sleep(protector.time_window_seconds + 0.5) # Wait for time window to pass
    print(f"Request from {attacker_ip} after reset: {'Allowed' if protector.check_request(attacker_ip) else 'Blocked'}")
    print(f"Request from {attacker_ip} (again): {'Allowed' if protector.check_request(attacker_ip) else 'Blocked'}")
