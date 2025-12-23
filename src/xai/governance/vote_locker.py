from __future__ import annotations

import logging
import threading
import time
from typing import Any

logger = logging.getLogger(__name__)

class VoteLocker:
    def __init__(self, base_duration: int = 86400, early_unlock_penalty_percentage: float = 10.0):
        """
        Initialize VoteLocker with time-weighted voting power.

        Args:
            base_duration: Base duration for voting power calculation (default: 1 day)
            early_unlock_penalty_percentage: Penalty for early unlock (default: 10%)
        """
        # Stores locked tokens: {voter_address: [{"amount": float, "lock_until": int, "lock_duration": int, "id": int}]}
        self.locked_tokens: dict[str, list] = {}
        self.base_duration = base_duration
        self.early_unlock_penalty_percentage = early_unlock_penalty_percentage
        self._lock_id_counter = 0
        self._lock = threading.RLock()

        logger.info(
            f"VoteLocker initialized. Base duration: {base_duration}s, "
            f"Early unlock penalty: {early_unlock_penalty_percentage}%"
        )

    def lock_tokens(self, voter_address: str, amount: float, lock_duration_seconds: int) -> int:
        """
        Allows a voter to lock tokens for a specified duration to gain voting power.
        Longer lock = more voting power using formula: power = amount * (duration / base_duration)

        Args:
            voter_address: Address of the voter
            amount: Amount of tokens to lock
            lock_duration_seconds: Duration to lock tokens

        Returns:
            Lock ID for tracking
        """
        if not voter_address:
            raise ValueError("Voter address cannot be empty.")
        if not isinstance(amount, (int, float)) or amount <= 0:
            raise ValueError("Amount to lock must be a positive number.")
        if not isinstance(lock_duration_seconds, int) or lock_duration_seconds <= 0:
            raise ValueError("Lock duration must be a positive integer in seconds.")

        with self._lock:
            lock_until = int(time.time()) + lock_duration_seconds
            self._lock_id_counter += 1
            lock_id = self._lock_id_counter

            if voter_address not in self.locked_tokens:
                self.locked_tokens[voter_address] = []

            # Calculate initial voting power
            time_multiplier = lock_duration_seconds / self.base_duration
            initial_voting_power = amount * time_multiplier

            self.locked_tokens[voter_address].append({
                "id": lock_id,
                "amount": amount,
                "lock_until": lock_until,
                "lock_duration": lock_duration_seconds,
                "locked_at": int(time.time()),
                "initial_voting_power": initial_voting_power
            })

            logger.info(
                f"Voter {voter_address} locked {amount:.2f} tokens for {lock_duration_seconds}s "
                f"(until {time.ctime(lock_until)}). Initial voting power: {initial_voting_power:.2f} "
                f"(multiplier: {time_multiplier:.2f}x)"
            )

            return lock_id

    def get_voting_power(self, voter_address: str, current_time: int | None = None) -> float:
        """
        Calculates the total voting power for a voter based on their locked tokens.
        Voting power formula: power = amount * (time_remaining / base_duration)
        Power decays linearly as lock approaches expiration.

        Args:
            voter_address: Address of the voter
            current_time: Current timestamp (defaults to now)

        Returns:
            Total voting power across all locks
        """
        if current_time is None:
            current_time = int(time.time())

        with self._lock:
            total_voting_power = 0.0
            if voter_address in self.locked_tokens:
                for lock_entry in self.locked_tokens[voter_address]:
                    if current_time < lock_entry["lock_until"]:  # Only count active locks
                        # Calculate voting power based on time remaining
                        time_remaining = lock_entry["lock_until"] - current_time
                        time_multiplier = time_remaining / self.base_duration
                        voting_power = lock_entry["amount"] * time_multiplier
                        total_voting_power += voting_power

            return total_voting_power

    def get_lock_details(self, voter_address: str, current_time: int | None = None) -> list[dict[str, Any]]:
        """Get detailed information about all locks for a voter."""
        if current_time is None:
            current_time = int(time.time())

        with self._lock:
            if voter_address not in self.locked_tokens:
                return []

            details = []
            for lock_entry in self.locked_tokens[voter_address]:
                time_remaining = max(0, lock_entry["lock_until"] - current_time)
                is_active = current_time < lock_entry["lock_until"]

                voting_power = 0.0
                if is_active:
                    time_multiplier = time_remaining / self.base_duration
                    voting_power = lock_entry["amount"] * time_multiplier

                details.append({
                    "lock_id": lock_entry["id"],
                    "amount": lock_entry["amount"],
                    "locked_at": lock_entry["locked_at"],
                    "lock_until": lock_entry["lock_until"],
                    "lock_duration": lock_entry["lock_duration"],
                    "time_remaining": time_remaining,
                    "is_active": is_active,
                    "voting_power": voting_power,
                    "initial_voting_power": lock_entry["initial_voting_power"]
                })

            return details

    def early_unlock(self, voter_address: str, lock_id: int, current_time: int | None = None) -> dict[str, float]:
        """
        Allow early unlock with penalty.

        Args:
            voter_address: Address of the voter
            lock_id: ID of the lock to unlock early
            current_time: Current timestamp

        Returns:
            Dictionary with 'amount_returned' and 'penalty_amount'
        """
        if current_time is None:
            current_time = int(time.time())

        with self._lock:
            if voter_address not in self.locked_tokens:
                raise ValueError(f"No locks found for {voter_address}")

            lock_entry = None
            lock_index = None

            for idx, entry in enumerate(self.locked_tokens[voter_address]):
                if entry["id"] == lock_id:
                    lock_entry = entry
                    lock_index = idx
                    break

            if lock_entry is None:
                raise ValueError(f"Lock ID {lock_id} not found for {voter_address}")

            if current_time >= lock_entry["lock_until"]:
                raise ValueError(f"Lock {lock_id} has already expired, use withdraw_tokens instead")

            # Calculate penalty
            penalty_amount = lock_entry["amount"] * (self.early_unlock_penalty_percentage / 100.0)
            amount_returned = lock_entry["amount"] - penalty_amount

            # Remove the lock
            del self.locked_tokens[voter_address][lock_index]

            logger.warning(
                f"Early unlock for {voter_address}, lock {lock_id}: "
                f"Returned {amount_returned:.2f}, Penalty {penalty_amount:.2f} "
                f"({self.early_unlock_penalty_percentage}%)"
            )

            return {
                "amount_returned": amount_returned,
                "penalty_amount": penalty_amount,
                "total_locked": lock_entry["amount"]
            }

    def withdraw_tokens(self, voter_address: str, current_time: int | None = None) -> float:
        """
        Allows a voter to withdraw tokens that have passed their lock-up period.
        Returns the total amount withdrawn.

        Args:
            voter_address: Address of the voter
            current_time: Current timestamp

        Returns:
            Total amount withdrawn
        """
        if current_time is None:
            current_time = int(time.time())

        with self._lock:
            if voter_address not in self.locked_tokens:
                return 0.0

            withdrawable_amount = 0.0
            new_locked_entries = []
            withdrawn_locks = []

            for lock_entry in self.locked_tokens[voter_address]:
                if current_time >= lock_entry["lock_until"]:
                    withdrawable_amount += lock_entry["amount"]
                    withdrawn_locks.append(lock_entry["id"])
                else:
                    new_locked_entries.append(lock_entry)

            self.locked_tokens[voter_address] = new_locked_entries

            if withdrawable_amount > 0:
                logger.info(
                    f"Voter {voter_address} withdrew {withdrawable_amount:.2f} tokens "
                    f"from {len(withdrawn_locks)} lock(s): {withdrawn_locks}"
                )
            else:
                logger.debug(f"No tokens available for withdrawal for {voter_address}")

            return withdrawable_amount

# Example Usage (for testing purposes)
if __name__ == "__main__":
    locker = VoteLocker()

    user_a = "0xUserA"
    user_b = "0xUserB"

    print("\n--- User A locks tokens ---")
    locker.lock_tokens(user_a, 100.0, 10)  # Lock 100 tokens for 10 seconds
    locker.lock_tokens(user_a, 50.0, 30)  # Lock 50 tokens for 30 seconds

    print("\n--- User B locks tokens ---")
    locker.lock_tokens(user_b, 200.0, 5)  # Lock 200 tokens for 5 seconds

    print("\n--- Initial Voting Power ---")
    initial_power_a = locker.get_voting_power(user_a)
    initial_power_b = locker.get_voting_power(user_b)
    print(f"User A voting power: {initial_power_a:.2f}")  # 100*10 + 50*30 = 1000 + 1500 = 2500
    print(f"User B voting power: {initial_power_b:.2f}")  # 200*5 = 1000

    print("\n--- Simulating Time Passing (5 seconds) ---")
    time.sleep(5)
    current_t1 = int(time.time())
    power_a_t1 = locker.get_voting_power(user_a, current_t1)
    power_b_t1 = locker.get_voting_power(user_b, current_t1)
    print(f"User A voting power: {power_a_t1:.2f}")
    print(f"User B voting power: {power_b_t1:.2f}")

    print("\n--- User B tries to withdraw (after 5 seconds) ---")
    withdrawn_b_t1 = locker.withdraw_tokens(user_b, current_t1)  # Should withdraw 200
    print(f"User B withdrawn: {withdrawn_b_t1:.2f}")
    print(
        f"User B voting power after withdrawal: {locker.get_voting_power(user_b, current_t1):.2f}"
    )  # Should be 0

    print("\n--- Simulating More Time Passing (another 5 seconds, total 10) ---")
    time.sleep(5)
    current_t2 = int(time.time())
    power_a_t2 = locker.get_voting_power(user_a, current_t2)
    print(f"User A voting power: {power_a_t2:.2f}")  # Only 50*30 = 1500 should remain

    print("\n--- User A tries to withdraw (after 10 seconds) ---")
    withdrawn_a_t2 = locker.withdraw_tokens(user_a, current_t2)  # Should withdraw 100
    print(f"User A withdrawn: {withdrawn_a_t2:.2f}")
    print(
        f"User A voting power after withdrawal: {locker.get_voting_power(user_a, current_t2):.2f}"
    )  # Should be 1500

    print("\n--- Simulating Full Lock-up for User A (another 20 seconds, total 30) ---")
    time.sleep(20)
    current_t3 = int(time.time())
    power_a_t3 = locker.get_voting_power(user_a, current_t3)
    print(f"User A voting power: {power_a_t3:.2f}")  # Should be 0

    print("\n--- User A withdraws remaining tokens ---")
    withdrawn_a_t3 = locker.withdraw_tokens(user_a, current_t3)  # Should withdraw 50
    print(f"User A withdrawn: {withdrawn_a_t3:.2f}")
    print(
        f"User A voting power after full withdrawal: {locker.get_voting_power(user_a, current_t3):.2f}"
    )  # Should be 0
