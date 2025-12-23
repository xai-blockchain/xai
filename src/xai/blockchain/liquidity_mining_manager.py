from __future__ import annotations

import logging
import time
from typing import Callable

logger = logging.getLogger("xai.blockchain.liquidity_mining_manager")

class LiquidityMiningManager:
    def __init__(
        self,
        daily_reward_cap: float,
        time_provider: Callable[[], int] | None = None,
    ):
        if not isinstance(daily_reward_cap, (int, float)) or daily_reward_cap <= 0:
            raise ValueError("Daily reward cap must be a positive number.")

        self.daily_reward_cap = daily_reward_cap
        self.rewards_distributed_today = 0.0
        self._time_provider = time_provider or (lambda: int(time.time()))
        self.last_reset_timestamp = self._current_time()
        logger.info(
            "LiquidityMiningManager initialized with daily cap %.2f (deterministic time provider: %s)",
            self.daily_reward_cap,
            bool(time_provider),
        )

    def _current_time(self) -> int:
        timestamp = self._time_provider()
        try:
            return int(timestamp)
        except (TypeError, ValueError) as exc:
            raise ValueError("time_provider must return an integer timestamp") from exc

    def _normalize_timestamp(self, current_time: int | None) -> int:
        if current_time is None:
            return self._current_time()
        if not isinstance(current_time, int):
            raise ValueError("current_time must be provided as an integer timestamp")
        return current_time

    def _check_and_reset_daily_rewards(self, current_time: int | None = None) -> int:
        """Resets daily rewards if a new day has started."""
        normalized_time = self._normalize_timestamp(current_time)
        # Simple daily reset: if more than 24 hours passed since last reset
        if (normalized_time - self.last_reset_timestamp) >= (24 * 3600):
            self.rewards_distributed_today = 0.0
            self.last_reset_timestamp = normalized_time
            logger.info("Daily rewards reset at %s", normalized_time)
        return normalized_time

    def distribute_rewards(self, amount: float, current_time: int | None = None) -> float:
        """
        Distributes liquidity mining rewards, enforcing the daily cap.
        Returns the amount actually distributed.
        """
        if not isinstance(amount, (int, float)) or amount <= 0:
            raise ValueError("Reward amount must be a positive number.")

        normalized_time = self._check_and_reset_daily_rewards(current_time)

        remaining_cap = self.daily_reward_cap - self.rewards_distributed_today
        amount_to_distribute = min(amount, remaining_cap)

        if amount_to_distribute <= 0:
            logger.warning(
                "Cannot distribute %.2f rewards. Daily cap %.2f already reached at %s",
                amount,
                self.daily_reward_cap,
                normalized_time,
            )
            return 0.0

        self.rewards_distributed_today += amount_to_distribute
        logger.info(
            "Distributed %.2f rewards at %s (total today %.2f / %.2f cap)",
            amount_to_distribute,
            normalized_time,
            self.rewards_distributed_today,
            self.daily_reward_cap,
        )
        return amount_to_distribute

    def get_rewards_distributed_today(self) -> float:
        """Returns the total rewards distributed today."""
        self._check_and_reset_daily_rewards()
        return self.rewards_distributed_today

    def get_daily_reward_cap(self) -> float:
        """Returns the daily reward cap."""
        return self.daily_reward_cap
