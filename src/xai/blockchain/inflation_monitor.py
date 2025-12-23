from __future__ import annotations

import logging
import time
from collections import deque

from .token_supply_manager import TokenSupplyManager

logger = logging.getLogger("xai.blockchain.inflation_monitor")

class InflationMonitor:
    def __init__(
        self,
        token_supply_manager: TokenSupplyManager,
        alert_threshold_percentage: float = 5.0,
        history_window_days: int = 30,
    ):
        if not isinstance(token_supply_manager, TokenSupplyManager):
            raise ValueError("token_supply_manager must be an instance of TokenSupplyManager.")
        if not isinstance(alert_threshold_percentage, (int, float)) or not (
            0 <= alert_threshold_percentage <= 100
        ):
            raise ValueError("Alert threshold percentage must be between 0 and 100.")
        if not isinstance(history_window_days, int) or history_window_days <= 0:
            raise ValueError("History window days must be a positive integer.")

        self.token_supply_manager = token_supply_manager
        self.alert_threshold_percentage = alert_threshold_percentage
        self.history_window_seconds = history_window_days * 24 * 3600
        self.supply_history: deque[tuple[int, float]] = deque()
        self._record_current_supply()
        logger.info(
            "InflationMonitor initialized (threshold %.2f%%, window %d days)",
            self.alert_threshold_percentage,
            history_window_days,
        )

    def _record_current_supply(self, current_time: int | None = None):
        now = current_time if current_time is not None else int(time.time())
        current_supply = self.token_supply_manager.get_current_supply()
        self.supply_history.append((now, current_supply))
        self._prune_history(now)

    def _prune_history(self, current_time: int):
        while (
            self.supply_history
            and current_time - self.supply_history[0][0] > self.history_window_seconds
        ):
            self.supply_history.popleft()

    def calculate_inflation_rate(self, period_seconds: int, current_time: int | None = None) -> float:
        current_time = current_time if current_time is not None else int(time.time())
        self._record_current_supply(current_time)
        if len(self.supply_history) < 2:
            return 0.0

        start_time = current_time - period_seconds
        initial_supply = None
        for timestamp, supply in self.supply_history:
            if timestamp >= start_time:
                initial_supply = supply
                break
        if initial_supply is None:
            initial_supply = self.supply_history[0][1]

        current_supply = self.token_supply_manager.get_current_supply()
        if initial_supply == 0:
            return 0.0
        return ((current_supply - initial_supply) / initial_supply) * 100

    def check_for_alerts(self, period_seconds: int, current_time: int | None = None) -> bool:
        rate = self.calculate_inflation_rate(period_seconds, current_time=current_time)
        if rate > self.alert_threshold_percentage:
            logger.error(
                "Inflation alert: rate %.2f%% exceeds threshold %.2f%% over period %ss",
                rate,
                self.alert_threshold_percentage,
                period_seconds,
            )
            return True
        logger.info(
            "Inflation %.2f%% within threshold %.2f%% over period %ss",
            rate,
            self.alert_threshold_percentage,
            period_seconds,
        )
        return False
