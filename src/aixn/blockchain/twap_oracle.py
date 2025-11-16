from typing import List, Tuple
import time


class TWAPOracle:
    def __init__(self, window_size_seconds: int = 3600):  # Default to 1 hour
        if not isinstance(window_size_seconds, int) or window_size_seconds <= 0:
            raise ValueError("Window size must be a positive integer.")
        self.window_size_seconds = window_size_seconds
        # Stores (timestamp, price) tuples, ordered by timestamp
        self.price_data: List[Tuple[int, float]] = []

    def record_price(self, price: float, timestamp: int = None):
        """
        Records a new price data point with a timestamp.
        If timestamp is None, uses the current UTC timestamp.
        """
        if not isinstance(price, (int, float)) or price <= 0:
            raise ValueError("Price must be a positive number.")

        current_timestamp = timestamp if timestamp is not None else int(time.time())
        if not isinstance(current_timestamp, int) or current_timestamp <= 0:
            raise ValueError("Timestamp must be a positive integer.")

        # Remove old data points outside the window
        self._clean_old_data(current_timestamp)
        self.price_data.append((current_timestamp, price))
        # Keep data sorted by timestamp
        self.price_data.sort(key=lambda x: x[0])
        print(
            f"Recorded price {price:.4f} at {current_timestamp}. Data points: {len(self.price_data)}"
        )

    def _clean_old_data(self, current_timestamp: int):
        """Removes price data points older than the window size."""
        cutoff_time = current_timestamp - self.window_size_seconds
        self.price_data = [data for data in self.price_data if data[0] >= cutoff_time]

    def get_twap(self, current_timestamp: int = None) -> float:
        """
        Calculates the Time-Weighted Average Price over the defined window.
        If current_timestamp is None, uses the current UTC timestamp.
        """
        current_timestamp = current_timestamp if current_timestamp is not None else int(time.time())
        self._clean_old_data(current_timestamp)  # Ensure only relevant data is considered

        if not self.price_data:
            return 0.0  # Or raise an error, depending on desired behavior

        total_weighted_price = 0.0
        total_time_weight = 0.0

        # Iterate through sorted price data
        for i in range(len(self.price_data)):
            timestamp_i, price_i = self.price_data[i]

            # The effective start time for this price segment is the timestamp of the current data point
            # The effective end time is the timestamp of the next data point, or the current_timestamp if it's the last one

            if i < len(self.price_data) - 1:
                timestamp_j = self.price_data[i + 1][0]
            else:
                timestamp_j = current_timestamp  # Use current time for the last segment

            # Ensure the segment is within the window and valid
            segment_start = max(timestamp_i, current_timestamp - self.window_size_seconds)
            segment_end = min(timestamp_j, current_timestamp)

            if segment_end > segment_start:
                time_duration = segment_end - segment_start
                total_weighted_price += price_i * time_duration
                total_time_weight += time_duration

        if total_time_weight == 0:
            return 0.0  # No valid data points within the window

        return total_weighted_price / total_time_weight


# Example Usage (for testing purposes)
if __name__ == "__main__":
    oracle = TWAPOracle(window_size_seconds=600)  # 10-minute TWAP

    # Simulate price data over time
    current_sim_time = int(time.time()) - 1200  # Start 20 minutes ago

    print("--- Recording Prices ---")
    oracle.record_price(100.0, current_sim_time)
    current_sim_time += 60  # 1 minute later
    oracle.record_price(101.0, current_sim_time)
    current_sim_time += 120  # 2 minutes later
    oracle.record_price(102.0, current_sim_time)
    current_sim_time += 30  # 30 seconds later
    oracle.record_price(101.5, current_sim_time)
    current_sim_time += 300  # 5 minutes later
    oracle.record_price(103.0, current_sim_time)
    current_sim_time += 60  # 1 minute later
    oracle.record_price(102.5, current_sim_time)

    print("\n--- Calculating TWAP ---")
    # Calculate TWAP at a specific point in simulated time
    twap_at_current_sim_time = oracle.get_twap(current_sim_time)
    print(f"TWAP at simulated time {current_sim_time}: {twap_at_current_sim_time:.4f}")

    # Simulate more time passing and new prices
    current_sim_time += 300  # 5 minutes later
    oracle.record_price(104.0, current_sim_time)
    current_sim_time += 60  # 1 minute later
    oracle.record_price(103.5, current_sim_time)

    twap_later = oracle.get_twap(current_sim_time)
    print(f"TWAP at simulated time {current_sim_time}: {twap_later:.4f}")

    # Test with no data in window
    empty_oracle = TWAPOracle(window_size_seconds=100)
    print(f"\nTWAP for empty oracle: {empty_oracle.get_twap()}")
