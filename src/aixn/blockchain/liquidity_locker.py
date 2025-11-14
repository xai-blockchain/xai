from typing import Dict, Any, List
import time

class LiquidityLocker:
    def __init__(self):
        # Stores locked positions: {lock_id: {"lp_token_amount": float, "lock_duration_seconds": int, "unlock_timestamp": int, "owner": str}}
        self.locked_positions: Dict[str, Dict[str, Any]] = {}
        self._lock_id_counter = 0

    def lock_liquidity(self, owner_address: str, lp_token_amount: float, lock_duration_seconds: int) -> str:
        """
        Simulates locking LP tokens for a specified duration.
        """
        if not owner_address:
            raise ValueError("Owner address cannot be empty.")
        if not isinstance(lp_token_amount, (int, float)) or lp_token_amount <= 0:
            raise ValueError("LP token amount must be a positive number.")
        if not isinstance(lock_duration_seconds, int) or lock_duration_seconds <= 0:
            raise ValueError("Lock duration must be a positive integer in seconds.")

        self._lock_id_counter += 1
        lock_id = f"lock_{self._lock_id_counter}"
        unlock_timestamp = int(time.time()) + lock_duration_seconds

        self.locked_positions[lock_id] = {
            "lp_token_amount": lp_token_amount,
            "lock_duration_seconds": lock_duration_seconds,
            "unlock_timestamp": unlock_timestamp,
            "owner": owner_address,
            "status": "locked"
        }
        print(f"Liquidity locked: {lp_token_amount:.4f} LP tokens by {owner_address} until {time.ctime(unlock_timestamp)}. Lock ID: {lock_id}")
        return lock_id

    def unlock_liquidity(self, lock_id: str, caller_address: str) -> float:
        """
        Simulates unlocking and withdrawing LP tokens after the lock-up period expires.
        """
        position = self.locked_positions.get(lock_id)
        if not position:
            raise ValueError(f"Lock ID {lock_id} not found.")
        if position["owner"] != caller_address:
            raise PermissionError(f"Caller {caller_address} is not the owner of lock ID {lock_id}.")
        if position["status"] == "unlocked":
            raise ValueError(f"Liquidity for lock ID {lock_id} is already unlocked.")

        current_time = int(time.time())
        if current_time < position["unlock_timestamp"]:
            remaining_time = position["unlock_timestamp"] - current_time
            raise ValueError(f"Liquidity for lock ID {lock_id} is still locked. "
                             f"Unlock available in {remaining_time} seconds.")

        position["status"] = "unlocked"
        unlocked_amount = position["lp_token_amount"]
        print(f"Liquidity unlocked: {unlocked_amount:.4f} LP tokens for lock ID {lock_id} by {caller_address}.")
        # In a real system, the LP tokens would be transferred back to the owner.
        return unlocked_amount

    def get_locked_liquidity(self, owner_address: str = None) -> List[Dict[str, Any]]:
        """
        Returns a list of all locked liquidity positions, or positions for a specific owner.
        """
        if owner_address:
            return [pos for pos in self.locked_positions.values() if pos["owner"] == owner_address and pos["status"] == "locked"]
        return [pos for pos in self.locked_positions.values() if pos["status"] == "locked"]

    def get_total_locked_liquidity(self) -> float:
        """
        Returns the total amount of LP tokens currently locked.
        """
        return sum(pos["lp_token_amount"] for pos in self.locked_positions.values() if pos["status"] == "locked")

# Example Usage (for testing purposes)
if __name__ == "__main__":
    locker = LiquidityLocker()
    user1 = "0xUser1"
    user2 = "0xUser2"

    print("--- Initial State ---")
    print(f"Total locked liquidity: {locker.get_total_locked_liquidity():.4f}")

    print("\n--- Locking Liquidity ---")
    lock1_id = locker.lock_liquidity(user1, 100.0, 10) # Lock for 10 seconds
    lock2_id = locker.lock_liquidity(user2, 250.0, 20) # Lock for 20 seconds
    lock3_id = locker.lock_liquidity(user1, 50.0, 5)  # Lock for 5 seconds

    print(f"Total locked liquidity: {locker.get_total_locked_liquidity():.4f}")
    print(f"User1 locked positions: {locker.get_locked_liquidity(user1)}")

    print("\n--- Attempting to unlock prematurely ---")
    try:
        locker.unlock_liquidity(lock1_id, user1)
    except ValueError as e:
        print(f"Error (expected): {e}")

    print("\n--- Waiting for some locks to expire ---")
    time.sleep(6) # Wait for lock3 to expire

    print("\n--- Unlocking expired liquidity ---")
    try:
        locker.unlock_liquidity(lock3_id, user1)
    except ValueError as e:
        print(f"Error: {e}") # Should not error now
    print(f"Total locked liquidity: {locker.get_total_locked_liquidity():.4f}")

    print("\n--- Attempting unauthorized unlock ---")
    try:
        locker.unlock_liquidity(lock1_id, user2)
    except PermissionError as e:
        print(f"Error (expected): {e}")

    print("\n--- Waiting for all locks to expire ---")
    time.sleep(15) # Wait for lock1 and lock2 to expire

    print("\n--- Unlocking remaining liquidity ---")
    locker.unlock_liquidity(lock1_id, user1)
    locker.unlock_liquidity(lock2_id, user2)
    print(f"Total locked liquidity: {locker.get_total_locked_liquidity():.4f}")