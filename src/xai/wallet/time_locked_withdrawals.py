from typing import Dict, Any, Optional
from datetime import datetime, timezone
import threading
import json
import os
import uuid
import logging

from xai.core.security_validation import log_security_event
from xai.core.monitoring import MetricsCollector

logger = logging.getLogger("xai.wallet.time_lock")


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
            logger.info(
                "Withdrawal %s for %s cancelled", self.withdrawal_id, self.user_address
            )
        else:
            logger.warning(
                "Cannot cancel withdrawal %s in status %s",
                self.withdrawal_id,
                self.status,
            )

    def confirm(self):
        if self.status == "pending":
            self.status = "confirmed"
            logger.info(
                "Withdrawal %s for %s confirmed", self.withdrawal_id, self.user_address
            )
        else:
            logger.warning(
                "Cannot confirm withdrawal %s in status %s",
                self.withdrawal_id,
                self.status,
            )

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
        storage_path: Optional[str] = None,
    ):
        if not isinstance(withdrawal_threshold, (int, float)) or withdrawal_threshold <= 0:
            raise ValueError("Withdrawal threshold must be a positive number.")
        if not isinstance(time_lock_seconds, int) or time_lock_seconds <= 0:
            raise ValueError("Time lock duration must be a positive integer.")

        self.withdrawal_threshold = withdrawal_threshold
        self.time_lock_seconds = time_lock_seconds
        self.pending_withdrawals: Dict[str, PendingWithdrawal] = {}
        self.storage_path = storage_path
        self._lock = threading.Lock()
        self._load_state()

    def request_withdrawal(
        self, user_address: str, amount: float, current_timestamp: Optional[int] = None
    ) -> PendingWithdrawal:
        ts = (
            current_timestamp
            if current_timestamp is not None
            else int(datetime.now(timezone.utc).timestamp())
        )
        withdrawal_id = str(uuid.uuid4())

        if amount >= self.withdrawal_threshold:
            release_timestamp = ts + self.time_lock_seconds
            withdrawal = PendingWithdrawal(
                withdrawal_id, user_address, amount, ts, release_timestamp
            )
            with self._lock:
                self.pending_withdrawals[withdrawal_id] = withdrawal
                self._persist_state_locked()
                pending_count = len(self.pending_withdrawals)
            logger.info(
                "Time-lock applied for %s amount %.2f (release at %s)",
                user_address,
                amount,
                datetime.fromtimestamp(release_timestamp, timezone.utc),
            )
            log_security_event(
                "time_locked_withdrawal_requested",
                {
                    "user": user_address,
                    "withdrawal_id": withdrawal_id,
                    "amount": amount,
                    "release_timestamp": release_timestamp,
                    "pending_backlog": pending_count,
                },
                severity="INFO",
            )
            MetricsCollector.instance().record_time_locked_request(pending_count)
        else:
            release_timestamp = ts
            withdrawal = PendingWithdrawal(
                withdrawal_id, user_address, amount, ts, release_timestamp
            )
            withdrawal.confirm()
            log_security_event(
                "withdrawal_processed_immediately",
                {
                    "user": user_address,
                    "withdrawal_id": withdrawal_id,
                    "amount": amount,
                },
            )
            logger.info(
                "Immediate withdrawal processed for %s amount %.2f", user_address, amount
            )

        return withdrawal

    def cancel_withdrawal(self, withdrawal_id: str, user_address: str):
        with self._lock:
            withdrawal = self.pending_withdrawals.get(withdrawal_id)
        if not withdrawal:
            logger.error("Withdrawal %s not found", withdrawal_id)
            return False
        if withdrawal.user_address != user_address:
            logger.error(
                "User %s not authorized to cancel withdrawal %s",
                user_address,
                withdrawal_id,
            )
            return False

        withdrawal.cancel()
        with self._lock:
            self.pending_withdrawals.pop(withdrawal_id, None)
            self._persist_state_locked()
            pending_count = len(self.pending_withdrawals)
        log_security_event(
            "time_locked_withdrawal_cancelled",
            {
                "user": user_address,
                "withdrawal_id": withdrawal_id,
                "amount": withdrawal.amount,
                "pending_backlog": pending_count,
            },
        )
        MetricsCollector.instance().update_time_locked_backlog(pending_count)
        return True

    def process_releasable_withdrawals(self, current_timestamp: int):
        """
        Checks for and processes withdrawals that are past their time-lock.
        In a real system, this would be called by a cron job or a dedicated service.
        """
        processed_count = 0
        with self._lock:
            for withdrawal_id, withdrawal in list(self.pending_withdrawals.items()):
                if withdrawal.is_releasable(current_timestamp):
                    withdrawal.confirm()
                    processed_count += 1
                    self.pending_withdrawals.pop(withdrawal_id, None)
                    pending_after = len(self.pending_withdrawals)
                    log_security_event(
                        "time_locked_withdrawal_released",
                        {
                            "user": withdrawal.user_address,
                            "withdrawal_id": withdrawal.withdrawal_id,
                            "amount": withdrawal.amount,
                            "pending_backlog": pending_after,
                        },
                    )
                elif (
                    withdrawal.status == "pending"
                    and current_timestamp < withdrawal.release_timestamp
                ):
                    logger.info(
                        "Withdrawal %s for %s unlocks in %s seconds",
                        withdrawal.withdrawal_id,
                        withdrawal.user_address,
                        withdrawal.release_timestamp - current_timestamp,
                    )
            if processed_count:
                self._persist_state_locked()
            pending_count = len(self.pending_withdrawals)
        MetricsCollector.instance().update_time_locked_backlog(pending_count)
        return processed_count

    def _persist_state_locked(self) -> None:
        if not self.storage_path:
            return
        try:
            directory = os.path.dirname(self.storage_path)
            if directory:
                os.makedirs(directory, exist_ok=True)
            snapshot = [w.to_dict() for w in self.pending_withdrawals.values() if w.status == "pending"]
            with open(self.storage_path, "w", encoding="utf-8") as handle:
                json.dump(snapshot, handle, indent=2)
        except Exception as exc:
            logger.error("Failed to persist withdrawals: %s", exc)

    def _load_state(self) -> None:
        if not self.storage_path or not os.path.exists(self.storage_path):
            return
        try:
            with open(self.storage_path, "r", encoding="utf-8") as handle:
                entries = json.load(handle)
            for item in entries:
                withdrawal = PendingWithdrawal(
                    item["withdrawal_id"],
                    item["user_address"],
                    item["amount"],
                    item["initiation_timestamp"],
                    item["release_timestamp"],
                )
                self.pending_withdrawals[withdrawal.withdrawal_id] = withdrawal
        except Exception as exc:
            logger.error("Failed to load withdrawal state: %s", exc)


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
