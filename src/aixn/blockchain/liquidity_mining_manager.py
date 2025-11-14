import time
from typing import Dict, Any

class LiquidityMiningManager:
    def __init__(self, daily_reward_cap: float):
        if not isinstance(daily_reward_cap, (int, float)) or daily_reward_cap <= 0:
            raise ValueError("Daily reward cap must be a positive number.")
        
        self.daily_reward_cap = daily_reward_cap
        self.rewards_distributed_today = 0.0
        self.last_reset_timestamp = int(time.time())
        print(f"LiquidityMiningManager initialized. Daily reward cap: {self.daily_reward_cap:.2f}")

    def _check_and_reset_daily_rewards(self):
        """Resets daily rewards if a new day has started."""
        current_time = int(time.time())
        # Simple daily reset: if more than 24 hours passed since last reset
        if (current_time - self.last_reset_timestamp) >= (24 * 3600):
            self.rewards_distributed_today = 0.0
            self.last_reset_timestamp = current_time
            print("Daily rewards reset.")

    def distribute_rewards(self, amount: float) -> float:
        """
        Distributes liquidity mining rewards, enforcing the daily cap.
        Returns the amount actually distributed.
        """
        if not isinstance(amount, (int, float)) or amount <= 0:
            raise ValueError("Reward amount must be a positive number.")
        
        self._check_and_reset_daily_rewards()

        remaining_cap = self.daily_reward_cap - self.rewards_distributed_today
        amount_to_distribute = min(amount, remaining_cap)

        if amount_to_distribute <= 0:
            print(f"Cannot distribute {amount:.2f} rewards. Daily cap of {self.daily_reward_cap:.2f} reached.")
            return 0.0
        
        self.rewards_distributed_today += amount_to_distribute
        print(f"Distributed {amount_to_distribute:.2f} rewards. Total distributed today: {self.rewards_distributed_today:.2f}")
        return amount_to_distribute

    def get_rewards_distributed_today(self) -> float:
        """Returns the total rewards distributed today."""
        self._check_and_reset_daily_rewards()
        return self.rewards_distributed_today

    def get_daily_reward_cap(self) -> float:
        """Returns the daily reward cap."""
        return self.daily_reward_cap

# Example Usage (for testing purposes)
if __name__ == "__main__":
    manager = LiquidityMiningManager(daily_reward_cap=1000.0)

    print("\n--- Initial State ---")
    print(f"Rewards distributed today: {manager.get_rewards_distributed_today():.2f}")
    print(f"Daily reward cap: {manager.get_daily_reward_cap():.2f}")

    print("\n--- Distributing Rewards ---")
    manager.distribute_rewards(300.0)
    manager.distribute_rewards(400.0)
    print(f"Current distributed: {manager.get_rewards_distributed_today():.2f}")

    print("\n--- Attempting to Exceed Daily Cap ---")
    manager.distribute_rewards(500.0) # Should distribute only 300 (1000 - 700)
    print(f"Current distributed: {manager.get_rewards_distributed_today():.2f}")

    print("\n--- Attempting to Distribute After Cap Reached ---")
    manager.distribute_rewards(100.0) # Should distribute 0
    print(f"Current distributed: {manager.get_rewards_distributed_today():.2f}")

    print("\n--- Simulating Day Change and Reset ---")
    # Manually advance time for demonstration
    manager.last_reset_timestamp -= (24 * 3600 + 10) # Set timestamp to yesterday
    print(f"Time advanced. Last reset was: {time.ctime(manager.last_reset_timestamp)}")
    
    manager.distribute_rewards(200.0) # Should now distribute
    print(f"Current distributed after reset: {manager.get_rewards_distributed_today():.2f}")
