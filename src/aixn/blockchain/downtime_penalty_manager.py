import time
from typing import Dict, Any

class DowntimePenaltyManager:
    def __init__(self, initial_validators: Dict[str, float], grace_period_seconds: int = 300, penalty_rate_per_second: float = 0.00001):
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
        if not isinstance(penalty_rate_per_second, (int, float)) or not (0 <= penalty_rate_per_second <= 1):
            raise ValueError("Penalty rate must be a number between 0 and 1.")

        self.grace_period_seconds = grace_period_seconds
        self.penalty_rate_per_second = penalty_rate_per_second

        self.validators: Dict[str, Dict[str, Any]] = {}
        for v_id, staked_amount in initial_validators.items():
            if not isinstance(v_id, str) or not v_id:
                raise ValueError("Validator ID must be a non-empty string.")
            if not isinstance(staked_amount, (int, float)) or staked_amount <= 0:
                raise ValueError(f"Staked amount for {v_id} must be a positive number.")
            self.validators[v_id] = {
                "staked_amount": staked_amount,
                "last_active_time": time.time(),
                "total_penalties": 0.0,
                "is_jailed": False # Conceptual jailing status
            }
        print(f"DowntimePenaltyManager initialized with {len(self.validators)} validators. Grace period: {grace_period_seconds}s.")

    def record_activity(self, validator_id: str):
        """Records activity for a validator, resetting their last_active_time."""
        if validator_id in self.validators:
            self.validators[validator_id]["last_active_time"] = time.time()
            # print(f"Activity recorded for {validator_id}.")
        else:
            print(f"Warning: Activity recorded for unknown validator {validator_id}.")

    def check_for_downtime(self, current_time: float = None):
        """
        Checks all validators for downtime and applies penalties if necessary.
        :param current_time: Optional. The current time to use for calculation. Defaults to time.time().
        """
        if current_time is None:
            current_time = time.time()

        print(f"\n--- Checking for downtime at {current_time:.2f} ---")
        for validator_id, info in self.validators.items():
            if info["is_jailed"]:
                print(f"Validator {validator_id} is jailed. No further penalties applied until unjailed.")
                continue

            time_since_last_activity = current_time - info["last_active_time"]

            if time_since_last_activity > self.grace_period_seconds:
                downtime_duration = time_since_last_activity - self.grace_period_seconds
                penalty_amount = info["staked_amount"] * self.penalty_rate_per_second * downtime_duration
                
                # Ensure penalty doesn't exceed staked amount
                penalty_amount = min(penalty_amount, info["staked_amount"])

                if penalty_amount > 0:
                    info["staked_amount"] -= penalty_amount
                    info["total_penalties"] += penalty_amount
                    # Update last_active_time to current_time to prevent re-penalizing for same period
                    info["last_active_time"] = current_time 
                    print(f"Validator {validator_id} penalized {penalty_amount:.4f} for {downtime_duration:.2f}s downtime. "
                          f"New staked amount: {info['staked_amount']:.2f}. Total penalties: {info['total_penalties']:.2f}.")
                    
                    # Conceptual jailing for severe downtime (e.g., if staked amount drops too low)
                    if info["staked_amount"] < self.validators[validator_id]["staked_amount"] * 0.5: # Example threshold
                        info["is_jailed"] = True
                        print(f"Validator {validator_id} has been JAILED due to significant penalties!")
                else:
                    print(f"Validator {validator_id} is within grace period or no significant penalty to apply.")
            else:
                print(f"Validator {validator_id} is active (last active {time_since_last_activity:.2f}s ago).")

    def get_validator_status(self, validator_id: str) -> Dict[str, Any] | None:
        """Returns the current status of a validator."""
        return self.validators.get(validator_id)

# Example Usage (for testing purposes)
if __name__ == "__main__":
    initial_stakes = {
        "validator_X": 1000.0,
        "validator_Y": 1500.0,
        "validator_Z": 500.0
    }
    manager = DowntimePenaltyManager(initial_stakes, grace_period_seconds=5, penalty_rate_per_second=0.001) # 0.1% per second after grace

    print("\n--- Initial Status ---")
    for v_id in initial_stakes.keys():
        status = manager.get_validator_status(v_id)
        print(f"{v_id}: Staked={status['staked_amount']:.2f}, Last Active={status['last_active_time']:.2f}, Jailed={status['is_jailed']}")

    # Simulate some activity
    manager.record_activity("validator_X")
    time.sleep(2)
    manager.record_activity("validator_Y")

    # Simulate time passing beyond grace period for Z
    print("\n--- Simulating 10 seconds pass (Z should be penalized) ---")
    time.sleep(10)
    manager.check_for_downtime()

    print("\n--- Status After First Check ---")
    for v_id in initial_stakes.keys():
        status = manager.get_validator_status(v_id)
        print(f"{v_id}: Staked={status['staked_amount']:.2f}, Last Active={status['last_active_time']:.2f}, Jailed={status['is_jailed']}")

    # Simulate more time passing, X and Y might now be penalized
    print("\n--- Simulating another 10 seconds pass (X and Y might be penalized) ---")
    time.sleep(10)
    manager.check_for_downtime()

    print("\n--- Status After Second Check ---")
    for v_id in initial_stakes.keys():
        status = manager.get_validator_status(v_id)
        print(f"{v_id}: Staked={status['staked_amount']:.2f}, Last Active={status['last_active_time']:.2f}, Jailed={status['is_jailed']}")

    # Simulate Z being active again
    print("\n--- Validator Z becomes active ---")
    manager.record_activity("validator_Z")
    time.sleep(2)
    manager.check_for_downtime() # Z should not be penalized now
