import logging
import time
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger("xai.blockchain.vesting_manager")


class VestingManager:
    def __init__(self, time_provider: Optional[Callable[[], int]] = None):
        # Stores vesting schedules: {schedule_id: {"recipient": str, "total_amount": float, "start_time": int, "end_time": int, "cliff_duration": int, "claimed_amount": float}}
        self.vesting_schedules: Dict[str, Dict[str, Any]] = {}
        self._schedule_id_counter = 0
        self._time_provider = time_provider or (lambda: int(time.time()))
        logger.info("VestingManager initialized with deterministic time provider: %s", bool(time_provider))

    def _current_time(self) -> int:
        timestamp = self._time_provider()
        try:
            return int(timestamp)
        except (TypeError, ValueError) as exc:
            raise ValueError("time_provider must return an integer timestamp") from exc

    def create_vesting_schedule(
        self,
        recipient_address: str,
        total_amount: float,
        start_time: int,
        end_time: int,
        cliff_duration: int,
    ) -> str:
        """
        Creates a new vesting schedule.
        - total_amount: Total tokens to be vested.
        - start_time: Unix timestamp when vesting begins.
        - end_time: Unix timestamp when vesting fully completes.
        - cliff_duration: Duration in seconds before any tokens start vesting.
        """
        if not recipient_address:
            raise ValueError("Recipient address cannot be empty.")
        if not isinstance(total_amount, (int, float)) or total_amount <= 0:
            raise ValueError("Total amount must be a positive number.")
        if (
            not isinstance(start_time, int)
            or not isinstance(end_time, int)
            or not isinstance(cliff_duration, int)
        ):
            raise ValueError("Time parameters must be integers (Unix timestamps/durations).")
        if start_time >= end_time:
            raise ValueError("Start time must be before end time.")
        if cliff_duration < 0:
            raise ValueError("Cliff duration cannot be negative.")

        self._schedule_id_counter += 1
        schedule_id = f"vesting_{self._schedule_id_counter}"

        self.vesting_schedules[schedule_id] = {
            "recipient": recipient_address,
            "total_amount": total_amount,
            "start_time": start_time,
            "end_time": end_time,
            "cliff_duration": cliff_duration,
            "claimed_amount": 0.0,
        }
        logger.info(
            "Vesting schedule %s created for %s (%.2f tokens, start %s, end %s, cliff %s)",
            schedule_id,
            recipient_address,
            total_amount,
            start_time,
            end_time,
            cliff_duration,
        )
        return schedule_id

    def get_vested_amount(self, schedule_id: str, current_time: Optional[int] = None) -> float:
        """
        Calculates the amount of tokens that have vested for a given schedule up to current_time.
        """
        schedule = self.vesting_schedules.get(schedule_id)
        if not schedule:
            raise ValueError(f"Vesting schedule {schedule_id} not found.")

        if current_time is None:
            current_time = self._current_time()

        total_amount = schedule["total_amount"]
        start_time = schedule["start_time"]
        end_time = schedule["end_time"]
        cliff_duration = schedule["cliff_duration"]
        claimed_amount = schedule["claimed_amount"]

        # Before cliff, no tokens vest
        if current_time < (start_time + cliff_duration):
            return 0.0

        # After end_time, all tokens have vested
        if current_time >= end_time:
            return total_amount - claimed_amount

        # Calculate vested amount proportionally between start_time and end_time (after cliff)
        vesting_start_after_cliff = start_time + cliff_duration
        if current_time < vesting_start_after_cliff:  # Should be caught by first if, but for safety
            return 0.0

        vesting_duration = end_time - vesting_start_after_cliff
        time_elapsed_since_cliff = current_time - vesting_start_after_cliff

        if vesting_duration <= 0:  # Should not happen with start_time < end_time
            return total_amount - claimed_amount

        vested_proportion = time_elapsed_since_cliff / vesting_duration
        vested_amount = total_amount * min(vested_proportion, 1.0)  # Cap at 100%

        return max(0.0, vested_amount - claimed_amount)  # Only return unclaimed vested amount

    def claim_vested_tokens(self, schedule_id: str, current_time: Optional[int] = None) -> float:
        """
        Simulates claiming available vested tokens for a given schedule.
        """
        schedule = self.vesting_schedules.get(schedule_id)
        if not schedule:
            raise ValueError(f"Vesting schedule {schedule_id} not found.")

        if current_time is None:
            current_time = self._current_time()

        available_to_claim = self.get_vested_amount(schedule_id, current_time)

        if available_to_claim <= 0:
            logger.warning(
                "No tokens available to claim for schedule %s at current time %s",
                schedule_id,
                current_time,
            )
            return 0.0

        schedule["claimed_amount"] += available_to_claim
        logger.info(
            "Claimed %.2f tokens for schedule %s (total claimed %.2f)",
            available_to_claim,
            schedule_id,
            schedule["claimed_amount"],
        )
        return available_to_claim
