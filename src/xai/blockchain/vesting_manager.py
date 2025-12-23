from __future__ import annotations

import logging
import time
from typing import Any, Callable

logger = logging.getLogger("xai.blockchain.vesting_manager")

from dataclasses import dataclass


@dataclass
class VestingScheduleData:
    recipient_address: str
    total_amount: float
    start_time: int
    end_time: int
    cliff_duration: int

class VestingManager:
    def __init__(self, time_provider: Callable[[], int] | None = None):
        # Stores vesting schedules: {schedule_id: {"recipient": str, "total_amount": float, "start_time": int, "end_time": int, "cliff_duration": int, "claimed_amount": float}}
        self.vesting_schedules: dict[str, dict[str, Any]] = {}
        self._schedule_id_counter = 0
        self._time_provider = time_provider or (lambda: int(time.time()))
        logger.info("VestingManager initialized with deterministic time provider: %s", bool(time_provider))

    def _current_time(self) -> int:
        timestamp = self._time_provider()
        try:
            return int(timestamp)
        except (TypeError, ValueError) as exc:
            raise ValueError("time_provider must return an integer timestamp") from exc

    def create_vesting_schedule(self, data: VestingScheduleData) -> str:
        """
        Creates a new vesting schedule.
        """
        if not data.recipient_address:
            raise ValueError("Recipient address cannot be empty.")
        if not isinstance(data.total_amount, (int, float)) or data.total_amount <= 0:
            raise ValueError("Total amount must be a positive number.")
        if (
            not isinstance(data.start_time, int)
            or not isinstance(data.end_time, int)
            or not isinstance(data.cliff_duration, int)
        ):
            raise ValueError("Time parameters must be integers (Unix timestamps/durations).")
        if data.start_time >= data.end_time:
            raise ValueError("Start time must be before end time.")
        if data.cliff_duration < 0:
            raise ValueError("Cliff duration cannot be negative.")

        self._schedule_id_counter += 1
        schedule_id = f"vesting_{self._schedule_id_counter}"

        self.vesting_schedules[schedule_id] = {
            "recipient": data.recipient_address,
            "total_amount": data.total_amount,
            "start_time": data.start_time,
            "end_time": data.end_time,
            "cliff_duration": data.cliff_duration,
            "claimed_amount": 0.0,
        }
        logger.info(
            "Vesting schedule %s created for %s",
            schedule_id,
            data.recipient_address
        )
        return schedule_id

    def get_vested_amount(self, schedule_id: str, current_time: int | None = None) -> float:
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

    def claim_vested_tokens(self, schedule_id: str, current_time: int | None = None) -> float:
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
                "No tokens available to claim for schedule %s",
                schedule_id
            )
            return 0.0

        schedule["claimed_amount"] += available_to_claim
        logger.info(
            "Claimed %.2f tokens for schedule %s",
            available_to_claim,
            schedule_id
        )
        return available_to_claim
