from typing import Dict, Any
import math
import time


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


class ILProtectionManager:
    def __init__(
        self,
        il_calculator: ImpermanentLossCalculator,
        protection_percentage: float = 50.0,
        min_lock_duration_days: int = 30,
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
        self.lp_positions: Dict[str, Dict[str, Any]] = (
            {}
        )  # {lp_address: {"initial_deposit_value": float, "initial_price_ratio": float, "deposit_timestamp": int}}

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
            "deposit_timestamp": int(time.time()),
        }
        print(
            f"LP deposit recorded for {lp_address}. Initial value: {initial_deposit_value:.4f}, Price ratio: {initial_price_ratio:.4f}"
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
        if int(time.time()) - deposit_timestamp >= self.min_lock_duration_seconds:
            protected_amount = loss_amount * self.protection_percentage
            print(
                f"LP {lp_address} is eligible for IL protection. "
                f"Calculated IL: {loss_amount:.4f}. Protected amount: {protected_amount:.4f}."
            )
        else:
            print(
                f"LP {lp_address} is not yet eligible for IL protection (needs {self.min_lock_duration_seconds / 3600 / 24:.0f} days)."
            )

        return protected_amount


# Example Usage (for testing purposes)
if __name__ == "__main__":
    il_calculator = ImpermanentLossCalculator()
    il_protection_manager = ILProtectionManager(
        il_calculator, protection_percentage=75.0, min_lock_duration_days=1
    )  # 75% protection after 1 day

    lp_address = "0xLiquidityProvider1"
    initial_deposit_value = 10000.0  # Total USD value of initial deposit
    initial_price_ratio = 1.0  # Assuming 1:1 price ratio initially

    il_protection_manager.record_lp_deposit(lp_address, initial_deposit_value, initial_price_ratio)

    print("\n--- Simulating price divergence (after a short time) ---")
    # Simulate price of one asset doubling, so ratio becomes 2.0
    current_price_ratio_short_time = 2.0
    current_pool_value_short_time = 9500.0  # Hypothetical value after some IL

    protected_il_short = il_protection_manager.calculate_protected_il(
        lp_address, current_pool_value_short_time, current_price_ratio_short_time
    )
    print(f"Protected IL (short time): {protected_il_short:.4f}")

    print("\n--- Simulating price divergence (after lock-up period) ---")
    # Advance time past the lock-up duration
    time.sleep(il_protection_manager.min_lock_duration_seconds + 1)

    # Simulate price of one asset quadrupling, so ratio becomes 4.0
    current_price_ratio_long_time = 4.0
    current_pool_value_long_time = 8000.0  # Hypothetical value after more IL

    protected_il_long = il_protection_manager.calculate_protected_il(
        lp_address, current_pool_value_long_time, current_price_ratio_long_time
    )
    print(f"Protected IL (long time): {protected_il_long:.4f}")

    # Calculate total IL for context
    il_percentage = il_calculator.calculate_il(initial_price_ratio, current_price_ratio_long_time)
    total_il_amount = initial_deposit_value * abs(il_percentage / 100)
    print(f"Total Impermanent Loss (unprotected): {total_il_amount:.4f}")
