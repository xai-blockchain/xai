from __future__ import annotations

import time
from typing import Any

class BandwidthThrottler:
    def __init__(
        self, max_upload_rate_kbps: float = 1000.0, max_download_rate_kbps: float = 1000.0
    ):
        if not isinstance(max_upload_rate_kbps, (int, float)) or max_upload_rate_kbps <= 0:
            raise ValueError("Max upload rate must be a positive number.")
        if not isinstance(max_download_rate_kbps, (int, float)) or max_download_rate_kbps <= 0:
            raise ValueError("Max download rate must be a positive number.")

        self.max_upload_rate_kbps = max_upload_rate_kbps
        self.max_download_rate_kbps = max_download_rate_kbps

        # Stores usage per peer: {peer_id: {"last_check_time": float, "uploaded_kb": float, "downloaded_kb": float}}
        self.peer_usage: dict[str, dict[str, float]] = {}
        print(
            f"BandwidthThrottler initialized. Max upload: {self.max_upload_rate_kbps} KB/s, Max download: {self.max_download_rate_kbps} KB/s."
        )

    def _get_peer_usage(self, peer_id: str) -> dict[str, float]:
        """Initializes or retrieves usage data for a peer."""
        if peer_id not in self.peer_usage:
            self.peer_usage[peer_id] = {
                "last_check_time": time.time(),
                "uploaded_kb": 0.0,
                "downloaded_kb": 0.0,
            }
        return self.peer_usage[peer_id]

    def _reset_usage_if_needed(self, peer_id: str, current_time: float):
        """Resets usage counters if a second has passed."""
        usage = self._get_peer_usage(peer_id)
        if current_time - usage["last_check_time"] >= 1.0:
            usage["uploaded_kb"] = 0.0
            usage["downloaded_kb"] = 0.0
            usage["last_check_time"] = current_time

    def send_data(self, peer_id: str, data_kb: float) -> float:
        """
        Simulates sending data to a peer, applying upload throttling.
        Returns the actual amount of data sent.
        """
        if not isinstance(data_kb, (int, float)) or data_kb < 0:
            raise ValueError("Data amount must be a non-negative number.")

        current_time = time.time()
        usage = self._get_peer_usage(peer_id)
        self._reset_usage_if_needed(peer_id, current_time)

        available_bandwidth = self.max_upload_rate_kbps - usage["uploaded_kb"]
        actual_sent_kb = min(data_kb, max(0.0, available_bandwidth))

        if actual_sent_kb < data_kb:
            print(
                f"Throttling upload for {peer_id}. Attempted {data_kb:.2f} KB, sent {actual_sent_kb:.2f} KB."
            )
        else:
            print(f"Sent {actual_sent_kb:.2f} KB to {peer_id}.")

        usage["uploaded_kb"] += actual_sent_kb
        return actual_sent_kb

    def receive_data(self, peer_id: str, data_kb: float) -> float:
        """
        Simulates receiving data from a peer, applying download throttling.
        Returns the actual amount of data received.
        """
        if not isinstance(data_kb, (int, float)) or data_kb < 0:
            raise ValueError("Data amount must be a non-negative number.")

        current_time = time.time()
        usage = self._get_peer_usage(peer_id)
        self._reset_usage_if_needed(peer_id, current_time)

        available_bandwidth = self.max_download_rate_kbps - usage["downloaded_kb"]
        actual_received_kb = min(data_kb, max(0.0, available_bandwidth))

        if actual_received_kb < data_kb:
            print(
                f"Throttling download from {peer_id}. Attempted {data_kb:.2f} KB, received {actual_received_kb:.2f} KB."
            )
        else:
            print(f"Received {actual_received_kb:.2f} KB from {peer_id}.")

        usage["downloaded_kb"] += actual_received_kb
        return actual_received_kb

# Example Usage (for testing purposes)
if __name__ == "__main__":
    throttler = BandwidthThrottler(max_upload_rate_kbps=100.0, max_download_rate_kbps=50.0)

    peer_fast = "peer_fast_node"
    peer_slow = "peer_slow_node"

    print("\n--- Sending Data ---")
    throttler.send_data(peer_fast, 50.0)
    throttler.send_data(peer_fast, 60.0)  # Should be throttled (100 - 50 = 50 available)
    throttler.send_data(peer_slow, 120.0)  # Should be throttled

    print("\n--- Receiving Data ---")
    throttler.receive_data(peer_fast, 20.0)
    throttler.receive_data(peer_fast, 40.0)  # Should be throttled (50 - 20 = 30 available)
    throttler.receive_data(peer_slow, 60.0)  # Should be throttled

    print("\n--- Simulating Time Pass (1 second) ---")
    time.sleep(1.1)  # Wait for more than 1 second to reset usage

    print("\n--- Sending Data After Reset ---")
    throttler.send_data(peer_fast, 70.0)  # Should now be allowed again
    throttler.send_data(peer_slow, 80.0)  # Should now be allowed again
