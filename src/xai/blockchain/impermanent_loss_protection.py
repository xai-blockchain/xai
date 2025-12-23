from __future__ import annotations

import logging
import math
import time
from typing import Any, Callable


class ImpermanentLossCalculator:
    def calculate_il(self, initial_price_ratio: float, current_price_ratio: float) -> float:
        """
        Calculates impermanent loss as a percentage.
        Formula: 2 * sqrt(price_ratio) / (1 + price_ratio) - 1
        Where price_ratio = current_price_ratio / initial_price_ratio
        Returns a negative value for loss, positive for gain (though IL is always a loss relative to holding).
        """
        if initial_price_ratio <= 0 or current_price_ratio <= 0:
            raise ValueError("Price ratios must be positive.")

        price_ratio_change = current_price_ratio / initial_price_ratio

        # Impermanent Loss formula
        il_factor = (2 * math.sqrt(price_ratio_change)) / (1 + price_ratio_change)
        impermanent_loss = (il_factor - 1) * 100  # Convert to percentage

        return impermanent_loss

logger = logging.getLogger("xai.blockchain.impermanent_loss_protection")

class ILProtectionManager:
    def __init__(
        self,
        il_calculator: ImpermanentLossCalculator,
        protection_percentage: float = 50.0,
        min_lock_duration_days: int = 30,
        time_provider: Callable[[], int] | None = None,
    ):
        if not isinstance(il_calculator, ImpermanentLossCalculator):
            raise ValueError("il_calculator must be an instance of ImpermanentLossCalculator.")
        if not isinstance(protection_percentage, (int, float)) or not (
            0 <= protection_percentage <= 100
        ):
            raise ValueError("Protection percentage must be between 0 and 100.")
        if not isinstance(min_lock_duration_days, int) or min_lock_duration_days <= 0:
            raise ValueError("Minimum lock duration must be a positive integer.")

        self.il_calculator = il_calculator
        self.protection_percentage = protection_percentage / 100.0  # Convert to decimal
        self.min_lock_duration_seconds = min_lock_duration_days * 24 * 3600
        self.lp_positions: dict[str, dict[str, Any]] = {}
        self._time_provider = time_provider or (lambda: int(time.time()))

    def record_lp_deposit(
        self, lp_address: str, initial_deposit_value: float, initial_price_ratio: float
    ):
        """
        Records an LP's initial deposit details for IL tracking.
        """
        if not lp_address:
            raise ValueError("LP address cannot be empty.")
        if initial_deposit_value <= 0 or initial_price_ratio <= 0:
            raise ValueError("Initial deposit value and price ratio must be positive.")

        self.lp_positions[lp_address] = {
            "initial_deposit_value": initial_deposit_value,
            "initial_price_ratio": initial_price_ratio,
            "deposit_timestamp": self._current_time(),
        }
        logger.info(
            "LP deposit recorded for %s (value %.4f, ratio %.4f)",
            lp_address,
            initial_deposit_value,
            initial_price_ratio,
        )

    def calculate_protected_il(
        self, lp_address: str, current_pool_value: float, current_price_ratio: float
    ) -> float:
        """
        Calculates the impermanent loss for an LP and applies protection if eligible.
        Returns the protected IL amount (positive value if protection is applied).
        """
        position = self.lp_positions.get(lp_address)
        if not position:
            raise ValueError(f"No LP position found for {lp_address}.")
        if current_pool_value <= 0 or current_price_ratio <= 0:
            raise ValueError("Current pool value and price ratio must be positive.")

        initial_deposit_value = position["initial_deposit_value"]
        initial_price_ratio = position["initial_price_ratio"]
        deposit_timestamp = position["deposit_timestamp"]

        # Calculate IL
        il_percentage = self.il_calculator.calculate_il(initial_price_ratio, current_price_ratio)

        # Value if held outside pool (no IL)
        value_if_held = initial_deposit_value * (
            current_price_ratio / initial_price_ratio
        )  # Simplified, assumes one asset changes value

        # Actual value in pool (after IL)
        actual_pool_value_after_il = initial_deposit_value * (
            1 + (il_percentage / 100)
        )  # This is incorrect, IL is relative to holding

        # Correct calculation of actual value in pool and IL amount
        # Value if held: initial_deposit_value * (current_price_ratio / initial_price_ratio) is not quite right.
        # It should be: initial_deposit_value * ( (1 + current_price_ratio/initial_price_ratio) / 2 ) for a 50/50 pool
        # Let's simplify: IL is the difference between holding and being in the pool.

        # For this conceptual model, let's assume initial_deposit_value is the total USD value of the deposit.
        # And il_percentage is the percentage loss relative to holding.

        loss_amount = initial_deposit_value * abs(
            il_percentage / 100
        )  # Absolute value of IL as a percentage of initial deposit

        protected_amount = 0.0
        if self._current_time() - deposit_timestamp >= self.min_lock_duration_seconds:
            protected_amount = loss_amount * self.protection_percentage
            logger.info(
                "LP %s eligible for protection (loss %.4f, protected %.4f)",
                lp_address,
                loss_amount,
                protected_amount,
            )
        else:
            logger.info(
                "LP %s not yet eligible for protection (lock period %s seconds)",
                lp_address,
                self.min_lock_duration_seconds,
            )

        return protected_amount

    def _current_time(self) -> int:
        return int(self._time_provider())
