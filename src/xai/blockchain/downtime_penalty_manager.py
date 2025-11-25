import logging
import time
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger("xai.blockchain.downtime_penalty")


class DowntimePenaltyManager:
    def __init__(
        self,
        initial_validators: Dict[str, float],
        grace_period_seconds: int = 300,
        penalty_rate_per_second: float = 0.00001,
        time_provider: Optional[Callable[[], float]] = None,
    ):
        """
        Initializes the DowntimePenaltyManager.
        :param initial_validators: A dictionary where keys are validator_ids (str) and values are staked_amounts (float).
        :param grace_period_seconds: Time in seconds a validator can be inactive before penalties start.
        :param penalty_rate_per_second: The fraction of staked amount penalized per second of downtime after grace period.
        """
        if not isinstance(initial_validators, dict):
            raise ValueError("Initial validators must be a dictionary.")
        if not isinstance(grace_period_seconds, int) or grace_period_seconds < 0:
            raise ValueError("Grace period must be a non-negative integer.")
        if not isinstance(penalty_rate_per_second, (int, float)) or not (
            0 <= penalty_rate_per_second <= 1
        ):
            raise ValueError("Penalty rate must be a number between 0 and 1.")

        self.grace_period_seconds = grace_period_seconds
        self.penalty_rate_per_second = penalty_rate_per_second

        self.validators: Dict[str, Dict[str, Any]] = {}
        self._time_provider = time_provider or time.time
        now = self._current_time()
        for v_id, staked_amount in initial_validators.items():
            if not isinstance(v_id, str) or not v_id:
                raise ValueError("Validator ID must be a non-empty string.")
            if not isinstance(staked_amount, (int, float)) or staked_amount <= 0:
                raise ValueError(f"Staked amount for {v_id} must be a positive number.")
            self.validators[v_id] = {
                "staked_amount": staked_amount,
                "initial_stake": staked_amount,
                "last_active_time": now,
                "total_penalties": 0.0,
                "is_jailed": False,  # Conceptual jailing status
            }
        logger.info(
            "DowntimePenaltyManager initialized with %d validators (grace=%ss, rate=%s)",
            len(self.validators),
            grace_period_seconds,
            penalty_rate_per_second,
        )

    def record_activity(self, validator_id: str, current_time: float | None = None):
        """Records activity for a validator, resetting their last_active_time."""
        now = current_time if current_time is not None else self._current_time()
        if validator_id in self.validators:
            self.validators[validator_id]["last_active_time"] = now
            logger.debug("Activity recorded for %s at %s", validator_id, now)
        else:
            logger.warning("Activity recorded for unknown validator %s", validator_id)

    def check_for_downtime(self, current_time: float | None = None):
        """
        Checks all validators for downtime and applies penalties if necessary.
        :param current_time: Optional. The current time to use for calculation. Defaults to time.time().
        """
        if current_time is None:
            current_time = self._current_time()

        logger.info("Checking for downtime at %s", current_time)
        for validator_id, info in self.validators.items():
            if info["is_jailed"]:
                logger.debug("Validator %s jailed, skipping penalties", validator_id)
                continue

            time_since_last_activity = current_time - info["last_active_time"]

            if time_since_last_activity > self.grace_period_seconds:
                downtime_duration = time_since_last_activity - self.grace_period_seconds
                penalty_amount = (
                    info["staked_amount"] * self.penalty_rate_per_second * downtime_duration
                )

                # Ensure penalty doesn't exceed staked amount
                penalty_amount = min(penalty_amount, info["staked_amount"])

                if penalty_amount > 0:
                    info["staked_amount"] -= penalty_amount
                    info["total_penalties"] += penalty_amount
                    # Update last_active_time to current_time to prevent re-penalizing for same period
                    info["last_active_time"] = current_time
                    logger.warning(
                        "Validator %s penalized %.4f for %.2fs downtime (new stake %.2f, total penalties %.2f)",
                        validator_id,
                        penalty_amount,
                        downtime_duration,
                        info["staked_amount"],
                        info["total_penalties"],
                    )

                    # Conceptual jailing for severe downtime when stake drops below half of initial
                    if info["staked_amount"] < (info["initial_stake"] * 0.5):
                        info["is_jailed"] = True
                        logger.error("Validator %s jailed due to excessive downtime penalties", validator_id)
                else:
                    logger.debug("Validator %s within grace period or no significant penalty", validator_id)
            else:
                logger.debug("Validator %s active (%.2fs since last activity)", validator_id, time_since_last_activity)

    def get_validator_status(self, validator_id: str) -> Dict[str, Any] | None:
        """Returns the current status of a validator."""
        return self.validators.get(validator_id)


    def _current_time(self) -> float:
        return float(self._time_provider())
