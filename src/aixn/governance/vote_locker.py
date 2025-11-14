import time
from typing import Dict, Any, Optional

class VoteLocker:
    def __init__(self):
        # Stores locked tokens: {voter_address: [{"amount": float, "lock_until": int, "lock_duration": int}]}
        self.locked_tokens: Dict[str, list] = {}
        print("VoteLocker initialized.")

    def lock_tokens(self, voter_address: str, amount: float, lock_duration_seconds: int):
        """
        Allows a voter to lock tokens for a specified duration to gain voting power.
        """
        if not voter_address:
            raise ValueError("Voter address cannot be empty.")
        if not isinstance(amount, (int, float)) or amount <= 0:
            raise ValueError("Amount to lock must be a positive number.")
        if not isinstance(lock_duration_seconds, int) or lock_duration_seconds <= 0:
            raise ValueError("Lock duration must be a positive integer in seconds.")

        lock_until = int(time.time()) + lock_duration_seconds
        
        if voter_address not in self.locked_tokens:
            self.locked_tokens[voter_address] = []
        
        self.locked_tokens[voter_address].append({
            "amount": amount,
            "lock_until": lock_until,
            "lock_duration": lock_duration_seconds
        })
        print(f"Voter {voter_address} locked {amount:.2f} tokens until {time.ctime(lock_until)}.")

    def get_voting_power(self, voter_address: str, current_time: Optional[int] = None) -> float:
        """
        Calculates the total voting power for a voter based on their locked tokens.
        Voting power is proportional to amount * lock_duration.
        """
        if current_time is None:
            current_time = int(time.time())

        total_voting_power = 0.0
        if voter_address in self.locked_tokens:
            for lock_entry in self.locked_tokens[voter_address]:
                amount = lock_entry["amount"]
                lock_until = lock_entry["lock_until"]
                lock_duration = lock_entry["lock_duration"]

                if current_time < lock_until: # Only count tokens that are still locked
                    # Simple linear boost: voting power = amount * (lock_duration / base_duration)
                    # For simplicity, let's just use amount * lock_duration as a proxy for power
                    total_voting_power += amount * lock_duration
        return total_voting_power

    def withdraw_tokens(self, voter_address: str, current_time: Optional[int] = None) -> float:
        """
        Allows a voter to withdraw tokens that have passed their lock-up period.
        Returns the total amount withdrawn.
        """
        if current_time is None:
            current_time = int(time.time())

        if voter_address not in self.locked_tokens:
            return 0.0

        withdrawable_amount = 0.0
        new_locked_entries = []
        
        for lock_entry in self.locked_tokens[voter_address]:
            if current_time >= lock_entry["lock_until"]:
                withdrawable_amount += lock_entry["amount"]
            else:
                new_locked_entries.append(lock_entry)
        
        self.locked_tokens[voter_address] = new_locked_entries
        
        if withdrawable_amount > 0:
            print(f"Voter {voter_address} withdrew {withdrawable_amount:.2f} tokens.")
        else:
            print(f"No tokens available for withdrawal for {voter_address}.")
        
        return withdrawable_amount

# Example Usage (for testing purposes)
if __name__ == "__main__":
    locker = VoteLocker()

    user_a = "0xUserA"
    user_b = "0xUserB"

    print("\n--- User A locks tokens ---")
    locker.lock_tokens(user_a, 100.0, 10) # Lock 100 tokens for 10 seconds
    locker.lock_tokens(user_a, 50.0, 30)  # Lock 50 tokens for 30 seconds

    print("\n--- User B locks tokens ---")
    locker.lock_tokens(user_b, 200.0, 5)  # Lock 200 tokens for 5 seconds

    print("\n--- Initial Voting Power ---")
    initial_power_a = locker.get_voting_power(user_a)
    initial_power_b = locker.get_voting_power(user_b)
    print(f"User A voting power: {initial_power_a:.2f}") # 100*10 + 50*30 = 1000 + 1500 = 2500
    print(f"User B voting power: {initial_power_b:.2f}") # 200*5 = 1000

    print("\n--- Simulating Time Passing (5 seconds) ---")
    time.sleep(5)
    current_t1 = int(time.time())
    power_a_t1 = locker.get_voting_power(user_a, current_t1)
    power_b_t1 = locker.get_voting_power(user_b, current_t1)
    print(f"User A voting power: {power_a_t1:.2f}")
    print(f"User B voting power: {power_b_t1:.2f}")

    print("\n--- User B tries to withdraw (after 5 seconds) ---")
    withdrawn_b_t1 = locker.withdraw_tokens(user_b, current_t1) # Should withdraw 200
    print(f"User B withdrawn: {withdrawn_b_t1:.2f}")
    print(f"User B voting power after withdrawal: {locker.get_voting_power(user_b, current_t1):.2f}") # Should be 0

    print("\n--- Simulating More Time Passing (another 5 seconds, total 10) ---")
    time.sleep(5)
    current_t2 = int(time.time())
    power_a_t2 = locker.get_voting_power(user_a, current_t2)
    print(f"User A voting power: {power_a_t2:.2f}") # Only 50*30 = 1500 should remain

    print("\n--- User A tries to withdraw (after 10 seconds) ---")
    withdrawn_a_t2 = locker.withdraw_tokens(user_a, current_t2) # Should withdraw 100
    print(f"User A withdrawn: {withdrawn_a_t2:.2f}")
    print(f"User A voting power after withdrawal: {locker.get_voting_power(user_a, current_t2):.2f}") # Should be 1500

    print("\n--- Simulating Full Lock-up for User A (another 20 seconds, total 30) ---")
    time.sleep(20)
    current_t3 = int(time.time())
    power_a_t3 = locker.get_voting_power(user_a, current_t3)
    print(f"User A voting power: {power_a_t3:.2f}") # Should be 0

    print("\n--- User A withdraws remaining tokens ---")
    withdrawn_a_t3 = locker.withdraw_tokens(user_a, current_t3) # Should withdraw 50
    print(f"User A withdrawn: {withdrawn_a_t3:.2f}")
    print(f"User A voting power after full withdrawal: {locker.get_voting_power(user_a, current_t3):.2f}") # Should be 0
