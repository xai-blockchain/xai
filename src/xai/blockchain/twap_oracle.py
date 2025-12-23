from __future__ import annotations

import logging
import time

logger = logging.getLogger("xai.blockchain.twap_oracle")

class TWAPOracle:
    def __init__(self, window_size_seconds: int = 3600):  # Default to 1 hour
        if not isinstance(window_size_seconds, int) or window_size_seconds <= 0:
            raise ValueError("Window size must be a positive integer.")
        self.window_size_seconds = window_size_seconds
        # Stores (timestamp, price) tuples, ordered by timestamp
        self.price_data: list[tuple[int, float]] = []

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
        logger.debug("Recorded price %.4f at %s (total points %d)", price, current_timestamp, len(self.price_data))

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
