from typing import Dict, Any, List
from datetime import datetime, timedelta, timezone


class UserWithdrawalTracker:
    def __init__(self, user_address: str):
        self.user_address = user_address
        self.withdrawals: List[Dict[str, Any]] = []  # Stores {"amount": float, "timestamp": int}
        self.current_day_start_timestamp = self._get_current_day_start_timestamp()

    def _get_current_day_start_timestamp(self) -> int:
        """Returns the UTC timestamp for the start of the current day (00:00:00 UTC)."""
        now_utc = datetime.now(timezone.utc)
        start_of_day = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
        return int(start_of_day.timestamp())

    def add_withdrawal(self, amount: float, timestamp: int):
        self.withdrawals.append({"amount": amount, "timestamp": timestamp})

    def get_daily_total(self, current_timestamp: int) -> float:
        """Calculates the total withdrawals for the current 24-hour period."""
        # Filter out withdrawals older than 24 hours from the current day's start
        # This ensures the "daily" limit resets consistently at 00:00 UTC
        self.withdrawals = [
            w for w in self.withdrawals if w["timestamp"] >= self.current_day_start_timestamp
        ]
        return sum(w["amount"] for w in self.withdrawals)

    def reset_if_new_day(self, current_timestamp: int):
        """Resets the tracker if a new UTC day has started."""
        new_day_start = self._get_current_day_start_timestamp()
        if new_day_start > self.current_day_start_timestamp:
            print(f"Resetting daily withdrawal tracker for {self.user_address} for new day.")
            self.withdrawals = []
            self.current_day_start_timestamp = new_day_start

    def __repr__(self):
        return (
            f"UserWithdrawalTracker(user='{self.user_address[:8]}...', "
            f"withdrawals_count={len(self.withdrawals)}, "
            f"day_start={datetime.fromtimestamp(self.current_day_start_timestamp, timezone.utc)})"
        )


class DailyWithdrawalLimitManager:
    DEFAULT_DAILY_LIMIT = 5000.0  # Max amount per user per 24 hours

    def __init__(self, daily_limit: float = DEFAULT_DAILY_LIMIT):
        if not isinstance(daily_limit, (int, float)) or daily_limit <= 0:
            raise ValueError("Daily limit must be a positive number.")
        self.daily_limit = daily_limit
        self.user_trackers: Dict[str, UserWithdrawalTracker] = {}

    def _get_user_tracker(self, user_address: str) -> UserWithdrawalTracker:
        if user_address not in self.user_trackers:
            self.user_trackers[user_address] = UserWithdrawalTracker(user_address)
        return self.user_trackers[user_address]

    def check_and_record_withdrawal(self, user_address: str, amount: float) -> bool:
        if not isinstance(amount, (int, float)) or amount <= 0:
            raise ValueError("Withdrawal amount must be a positive number.")

        current_timestamp = int(datetime.now(timezone.utc).timestamp())
        tracker = self._get_user_tracker(user_address)
        tracker.reset_if_new_day(
            current_timestamp
        )  # Ensure tracker is up-to-date for the current day

        current_daily_total = tracker.get_daily_total(current_timestamp)

        if (current_daily_total + amount) > self.daily_limit:
            print(
                f"Withdrawal for {user_address} of {amount} FAILED. "
                f"Exceeds daily limit. Current total: {current_daily_total}, Limit: {self.daily_limit}."
            )
            return False
        else:
            tracker.add_withdrawal(amount, current_timestamp)
            print(
                f"Withdrawal for {user_address} of {amount} APPROVED. "
                f"New daily total: {tracker.get_daily_total(current_timestamp)} / {self.daily_limit}."
            )
            return True


# Example Usage (for testing purposes)
if __name__ == "__main__":
    manager = DailyWithdrawalLimitManager(daily_limit=1000.0)  # Set a daily limit of 1000

    user_a = "0xUserA"
    user_b = "0xUserB"

    print("--- User A Withdrawals ---")
    manager.check_and_record_withdrawal(user_a, 300)  # OK
    manager.check_and_record_withdrawal(user_a, 400)  # OK
    manager.check_and_record_withdrawal(user_a, 300)  # OK (total 1000)
    manager.check_and_record_withdrawal(user_a, 100)  # FAILED (exceeds 1000)

    print("\n--- User B Withdrawals ---")
    manager.check_and_record_withdrawal(user_b, 900)  # OK
    manager.check_and_record_withdrawal(user_b, 200)  # FAILED

    # Simulate a new day (for testing purposes, normally this happens automatically)
    print("\n--- Simulating New Day ---")
    # To simulate a new day, we'd typically advance the system clock or manually reset.
    # For this example, we'll just create a new manager or manually reset trackers.
    # In a real system, a cron job would call reset_if_new_day on all trackers.

    # Manually reset User A's tracker for demonstration
    user_a_tracker = manager._get_user_tracker(user_a)
    # Artificially set the day start to a past day to force a reset
    user_a_tracker.current_day_start_timestamp = int(
        (datetime.now(timezone.utc) - timedelta(days=1))
        .replace(hour=0, minute=0, second=0, microsecond=0)
        .timestamp()
    )
    user_a_tracker.reset_if_new_day(int(datetime.now(timezone.utc).timestamp()))

    print("\n--- User A Withdrawals on New Day ---")
    manager.check_and_record_withdrawal(user_a, 500)  # OK again
    manager.check_and_record_withdrawal(user_a, 600)  # FAILED
