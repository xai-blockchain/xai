import time
from collections import deque
from typing import Dict, Any, Deque, Tuple

# Assuming TokenSupplyManager is available from a previous implementation
from src.aixn.blockchain.token_supply_manager import TokenSupplyManager


class InflationMonitor:
    def __init__(
        self,
        token_supply_manager: TokenSupplyManager,
        alert_threshold_percentage: float = 5.0,
        history_window_days: int = 30,
    ):
        if not isinstance(token_supply_manager, TokenSupplyManager):
            raise ValueError("token_supply_manager must be an instance of TokenSupplyManager.")
        if not isinstance(alert_threshold_percentage, (int, float)) or not (
            0 <= alert_threshold_percentage <= 100
        ):
            raise ValueError("Alert threshold percentage must be between 0 and 100.")
        if not isinstance(history_window_days, int) or history_window_days <= 0:
            raise ValueError("History window days must be a positive integer.")

        self.token_supply_manager = token_supply_manager
        self.alert_threshold_percentage = alert_threshold_percentage
        self.history_window_seconds = history_window_days * 24 * 3600

        # Stores historical supply data: deque of (timestamp, supply) tuples
        self.supply_history: Deque[Tuple[int, float]] = deque()

        # Record initial supply
        self._record_current_supply()
        print(
            f"InflationMonitor initialized. Alert threshold: {self.alert_threshold_percentage:.2f}%, History window: {history_window_days} days."
        )

    def _record_current_supply(self):
        """Records the current supply with a timestamp."""
        current_time = int(time.time())
        current_supply = self.token_supply_manager.get_current_supply()
        self.supply_history.append((current_time, current_supply))

        # Remove old entries outside the history window
        while (
            self.supply_history
            and (current_time - self.supply_history[0][0]) > self.history_window_seconds
        ):
            self.supply_history.popleft()

    def calculate_inflation_rate(self, period_seconds: int) -> float:
        """
        Calculates the inflation rate over a specified period in seconds.
        Returns the inflation rate as a percentage.
        """
        self._record_current_supply()  # Ensure history is up-to-date

        if len(self.supply_history) < 2:
            return 0.0  # Not enough data to calculate inflation

        # Find the supply at the beginning of the period
        start_time = int(time.time()) - period_seconds

        initial_supply = None
        for timestamp, supply in self.supply_history:
            if timestamp >= start_time:
                initial_supply = supply
                break

        if initial_supply is None:
            # If no data point exactly at or after start_time, use the oldest available
            initial_supply = self.supply_history[0][1]

        current_supply = self.token_supply_manager.get_current_supply()

        if initial_supply == 0:
            return 0.0  # Avoid division by zero if initial supply was zero

        inflation_rate = ((current_supply - initial_supply) / initial_supply) * 100
        return inflation_rate

    def check_for_alerts(self, period_seconds: int) -> bool:
        """
        Checks if the inflation rate exceeds the alert threshold and triggers a conceptual alert.
        """
        inflation_rate = self.calculate_inflation_rate(period_seconds)

        if inflation_rate > self.alert_threshold_percentage:
            print(
                f"!!! INFLATION ALERT !!! Inflation rate ({inflation_rate:.2f}%) "
                f"exceeds threshold ({self.alert_threshold_percentage:.2f}%) over the last {period_seconds / 3600 / 24:.0f} days."
            )
            # In a real system, this would trigger an actual alert (email, PagerDuty, etc.)
            return True
        else:
            print(f"Inflation rate ({inflation_rate:.2f}%) is within acceptable limits.")
            return False


# Example Usage (for testing purposes)
if __name__ == "__main__":
    # Initialize TokenSupplyManager
    supply_manager = TokenSupplyManager(max_supply=1000000.0)

    # Initialize InflationMonitor with a 1-day history window and 1% alert threshold
    monitor = InflationMonitor(
        supply_manager, alert_threshold_percentage=1.0, history_window_days=1
    )

    print("\n--- Initial Check ---")
    monitor.check_for_alerts(24 * 3600)  # Check over 1 day

    print("\n--- Simulating Normal Minting ---")
    supply_manager.mint_tokens(10000.0)  # 1% of max supply
    time.sleep(5)  # Simulate some time passing
    monitor.check_for_alerts(24 * 3600)

    print("\n--- Simulating High Minting (triggering alert) ---")
    supply_manager.mint_tokens(50000.0)  # Another 5%
    time.sleep(5)
    monitor.check_for_alerts(24 * 3600)

    print("\n--- Simulating Burning ---")
    supply_manager.burn_tokens(20000.0)
    time.sleep(5)
    monitor.check_for_alerts(24 * 3600)

    print("\n--- Simulating Long-Term Inflation (conceptual) ---")
    # To properly test long-term inflation, we'd need to simulate more time and minting.
    # For this example, we'll just show the current state.
    print(f"\nCurrent supply: {supply_manager.get_current_supply():.2f}")
    print(f"Max supply: {supply_manager.get_max_supply():.2f}")
    print(f"Inflation rate over 1 day: {monitor.calculate_inflation_rate(24 * 3600):.2f}%")
