from typing import Dict, Any
from datetime import datetime, timedelta, timezone
import uuid


class PendingWithdrawal:
    def __init__(
        self,
        withdrawal_id: str,
        user_address: str,
        amount: float,
        initiation_timestamp: int,
        release_timestamp: int,
    ):
        if not withdrawal_id:
            raise ValueError("Withdrawal ID cannot be empty.")
        if not user_address:
            raise ValueError("User address cannot be empty.")
        if not isinstance(amount, (int, float)) or amount <= 0:
            raise ValueError("Withdrawal amount must be a positive number.")
        if not isinstance(initiation_timestamp, int) or initiation_timestamp <= 0:
            raise ValueError("Initiation timestamp must be a positive integer.")
        if not isinstance(release_timestamp, int) or release_timestamp <= initiation_timestamp:
            raise ValueError("Release timestamp must be after initiation timestamp.")

        self.withdrawal_id = withdrawal_id
        self.user_address = user_address
        self.amount = amount
        self.initiation_timestamp = initiation_timestamp
        self.release_timestamp = release_timestamp
        self.status = "pending"  # pending, cancelled, confirmed, expired

    def is_releasable(self, current_timestamp: int) -> bool:
        return self.status == "pending" and current_timestamp >= self.release_timestamp

    def cancel(self):
        if self.status == "pending":
            self.status = "cancelled"
            print(f"Withdrawal {self.withdrawal_id} for {self.user_address} cancelled.")
        else:
            print(f"Cannot cancel withdrawal {self.withdrawal_id} in status '{self.status}'.")

    def confirm(self):
        if self.status == "pending":
            self.status = "confirmed"
            print(f"Withdrawal {self.withdrawal_id} for {self.user_address} confirmed.")
        else:
            print(f"Cannot confirm withdrawal {self.withdrawal_id} in status '{self.status}'.")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "withdrawal_id": self.withdrawal_id,
            "user_address": self.user_address,
            "amount": self.amount,
            "initiation_timestamp": self.initiation_timestamp,
            "release_timestamp": self.release_timestamp,
            "status": self.status,
        }

    def __repr__(self):
        return (
            f"PendingWithdrawal(id='{self.withdrawal_id[:8]}...', user='{self.user_address[:8]}...', "
            f"amount={self.amount}, status='{self.status}', release_at={datetime.fromtimestamp(self.release_timestamp, timezone.utc)})"
        )


class TimeLockedWithdrawalManager:
    DEFAULT_THRESHOLD = 1000.0  # Amount in some currency unit
    DEFAULT_TIME_LOCK_SECONDS = 3600  # 1 hour

    def __init__(
        self,
        withdrawal_threshold: float = DEFAULT_THRESHOLD,
        time_lock_seconds: int = DEFAULT_TIME_LOCK_SECONDS,
    ):
        if not isinstance(withdrawal_threshold, (int, float)) or withdrawal_threshold <= 0:
            raise ValueError("Withdrawal threshold must be a positive number.")
        if not isinstance(time_lock_seconds, int) or time_lock_seconds <= 0:
            raise ValueError("Time lock duration must be a positive integer.")

        self.withdrawal_threshold = withdrawal_threshold
        self.time_lock_seconds = time_lock_seconds
        self.pending_withdrawals: Dict[str, PendingWithdrawal] = {}

    def request_withdrawal(self, user_address: str, amount: float) -> PendingWithdrawal:
        current_timestamp = int(datetime.now(timezone.utc).timestamp())
        withdrawal_id = str(uuid.uuid4())

        if amount >= self.withdrawal_threshold:
            release_timestamp = current_timestamp + self.time_lock_seconds
            withdrawal = PendingWithdrawal(
                withdrawal_id, user_address, amount, current_timestamp, release_timestamp
            )
            self.pending_withdrawals[withdrawal_id] = withdrawal
            print(
                f"Large withdrawal requested for {user_address} of {amount}. "
                f"Time-lock applied. Release at: {datetime.fromtimestamp(release_timestamp, timezone.utc)} UTC."
            )
        else:
            # For smaller amounts, withdrawal can be processed immediately (conceptually)
            release_timestamp = current_timestamp  # No actual time lock
            withdrawal = PendingWithdrawal(
                withdrawal_id, user_address, amount, current_timestamp, release_timestamp
            )
            withdrawal.confirm()  # Immediately confirm small withdrawals
            print(
                f"Small withdrawal requested for {user_address} of {amount}. Processed immediately."
            )

        return withdrawal

    def cancel_withdrawal(self, withdrawal_id: str, user_address: str):
        withdrawal = self.pending_withdrawals.get(withdrawal_id)
        if not withdrawal:
            print(f"Error: Withdrawal {withdrawal_id} not found.")
            return False
        if withdrawal.user_address != user_address:
            print(
                f"Error: User {user_address} is not authorized to cancel withdrawal {withdrawal_id}."
            )
            return False

        withdrawal.cancel()
        return True

    def process_releasable_withdrawals(self, current_timestamp: int):
        """
        Checks for and processes withdrawals that are past their time-lock.
        In a real system, this would be called by a cron job or a dedicated service.
        """
        print(
            f"\n--- Processing releasable withdrawals at {datetime.fromtimestamp(current_timestamp, timezone.utc)} UTC ---"
        )
        processed_count = 0
        for withdrawal_id, withdrawal in list(
            self.pending_withdrawals.items()
        ):  # Iterate over a copy
            if withdrawal.is_releasable(current_timestamp):
                withdrawal.confirm()
                # In a real system, funds would be transferred here.
                # For this mock, we just change the status.
                processed_count += 1
            elif (
                withdrawal.status == "pending" and current_timestamp < withdrawal.release_timestamp
            ):
                print(
                    f"Withdrawal {withdrawal_id} for {withdrawal.user_address} still time-locked. "
                    f"Releases in {withdrawal.release_timestamp - current_timestamp} seconds."
                )
        if processed_count == 0:
            print("No withdrawals currently releasable.")
        return processed_count


# Example Usage (for testing purposes)
if __name__ == "__main__":
    manager = TimeLockedWithdrawalManager(
        withdrawal_threshold=1000, time_lock_seconds=5
    )  # 5-second lock for testing

    user1 = "0xUserA"
    user2 = "0xUserB"
    user3 = "0xUserC"

    print("--- Requesting Withdrawals ---")
    # Small withdrawal (should be immediate)
    w1 = manager.request_withdrawal(user1, 500)
    print(w1)

    # Large withdrawal (should be time-locked)
    w2 = manager.request_withdrawal(user2, 1500)
    print(w2)

    # Another large withdrawal
    w3 = manager.request_withdrawal(user3, 2500)
    print(w3)

    print("\n--- Attempting to process immediately (should not release large ones) ---")
    manager.process_releasable_withdrawals(int(datetime.now(timezone.utc).timestamp()))

    print("\n--- Cancelling a pending withdrawal ---")
    manager.cancel_withdrawal(w3.withdrawal_id, user3)
    print(w3)

    print("\n--- Waiting for time lock to expire ---")
    import time

    time.sleep(6)  # Wait for 5-second time lock to pass

    print("\n--- Processing after time lock ---")
    manager.process_releasable_withdrawals(int(datetime.now(timezone.utc).timestamp()))
    print(w2)
