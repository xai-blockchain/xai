import logging
from typing import Dict, Any, List
import time

logger = logging.getLogger("xai.blockchain.liquidity_locker")


class LiquidityLocker:
    def __init__(self):
        # Stores locked positions: {lock_id: {"lp_token_amount": float, "lock_duration_seconds": int, "unlock_timestamp": int, "owner": str}}
        self.locked_positions: Dict[str, Dict[str, Any]] = {}
        self._lock_id_counter = 0

    def lock_liquidity(
        self,
        owner_address: str,
        lp_token_amount: float,
        lock_duration_seconds: int,
        current_time: int | None = None,
    ) -> str:
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
        now = int(current_time if current_time is not None else time.time())
        unlock_timestamp = now + lock_duration_seconds

        self.locked_positions[lock_id] = {
            "lp_token_amount": lp_token_amount,
            "lock_duration_seconds": lock_duration_seconds,
            "unlock_timestamp": unlock_timestamp,
            "owner": owner_address,
            "status": "locked",
        }
        logger.info(
            "Liquidity locked: %.4f LP tokens by %s until %s (lock_id=%s)",
            lp_token_amount,
            owner_address,
            unlock_timestamp,
            lock_id,
        )
        return lock_id

    def unlock_liquidity(
        self,
        lock_id: str,
        caller_address: str,
        current_time: int | None = None,
    ) -> float:
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

        now = int(current_time if current_time is not None else time.time())
        if now < position["unlock_timestamp"]:
            remaining_time = position["unlock_timestamp"] - now
            raise ValueError(
                f"Liquidity for lock ID {lock_id} is still locked. "
                f"Unlock available in {remaining_time} seconds."
            )

        position["status"] = "unlocked"
        unlocked_amount = position["lp_token_amount"]
        logger.info(
            "Liquidity unlocked: %.4f LP tokens for lock %s by %s",
            unlocked_amount,
            lock_id,
            caller_address,
        )
        # In a real system, the LP tokens would be transferred back to the owner.
        return unlocked_amount

    def get_locked_liquidity(self, owner_address: str = None) -> List[Dict[str, Any]]:
        """
        Returns a list of all locked liquidity positions, or positions for a specific owner.
        """
        if owner_address:
            return [
                pos
                for pos in self.locked_positions.values()
                if pos["owner"] == owner_address and pos["status"] == "locked"
            ]
        return [pos for pos in self.locked_positions.values() if pos["status"] == "locked"]

    def get_total_locked_liquidity(self) -> float:
        """
        Returns the total amount of LP tokens currently locked.
        """
        return sum(
            pos["lp_token_amount"]
            for pos in self.locked_positions.values()
            if pos["status"] == "locked"
        )
