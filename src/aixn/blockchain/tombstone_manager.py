from typing import Dict, Any, Set

class TombstoneManager:
    def __init__(self, initial_validators: Dict[str, float], tombstone_threshold: int = 3):
        """
        Initializes the TombstoneManager.
        :param initial_validators: A dictionary where keys are validator_ids (str) and values are staked_amounts (float).
                                   This manager will track their status.
        :param tombstone_threshold: The number of slashing events (or other severe misbehaviors)
                                    after which a validator is tombstoned.
        """
        if not isinstance(initial_validators, dict):
            raise ValueError("Initial validators must be a dictionary.")
        if not isinstance(tombstone_threshold, int) or tombstone_threshold <= 0:
            raise ValueError("Tombstone threshold must be a positive integer.")

        self.tombstone_threshold = tombstone_threshold
        
        # Stores active validators: {validator_id: {"staked_amount": float, "slashed_count": int}}
        self.active_validators: Dict[str, Dict[str, Any]] = {}
        for v_id, staked_amount in initial_validators.items():
            if not isinstance(v_id, str) or not v_id:
                raise ValueError("Validator ID must be a non-empty string.")
            if not isinstance(staked_amount, (int, float)) or staked_amount <= 0:
                raise ValueError(f"Staked amount for {v_id} must be a positive number.")
            self.active_validators[v_id] = {"staked_amount": staked_amount, "slashed_count": 0}

        self.tombstoned_validators: Set[str] = set() # Stores IDs of permanently banned validators
        print(f"TombstoneManager initialized with {len(self.active_validators)} active validators. "
              f"Tombstone threshold: {self.tombstone_threshold} slashing events.")

    def _remove_from_active(self, validator_id: str):
        """Helper to remove a validator from the active set."""
        if validator_id in self.active_validators:
            del self.active_validators[validator_id]

    def _add_to_tombstoned(self, validator_id: str):
        """Helper to add a validator to the tombstoned set."""
        self.tombstoned_validators.add(validator_id)

    def record_slashing_event(self, validator_id: str, slashed_amount: float):
        """
        Records a slashing event for a validator and updates their status.
        This method would typically be called by the SlashingManager.
        """
        if validator_id in self.tombstoned_validators:
            print(f"Validator {validator_id} is already tombstoned. No further slashing recorded.")
            return

        if validator_id in self.active_validators:
            validator_info = self.active_validators[validator_id]
            validator_info["staked_amount"] -= slashed_amount
            validator_info["slashed_count"] += 1
            print(f"Slashing event recorded for {validator_id}. New staked: {validator_info['staked_amount']:.2f}, "
                  f"Slashed count: {validator_info['slashed_count']}.")
            self.check_for_tombstone(validator_id)
        else:
            print(f"Warning: Slashing event recorded for unknown or inactive validator {validator_id}.")

    def check_for_tombstone(self, validator_id: str) -> bool:
        """
        Checks if a validator meets the conditions for tombstoning.
        Returns True if tombstoned, False otherwise.
        """
        if validator_id in self.tombstoned_validators:
            return True # Already tombstoned

        if validator_id in self.active_validators:
            validator_info = self.active_validators[validator_id]
            if validator_info["slashed_count"] >= self.tombstone_threshold:
                print(f"Validator {validator_id} reached {self.tombstone_threshold} slashing events. Initiating tombstoning.")
                self.tombstone_validator(validator_id)
                return True
        return False

    def tombstone_validator(self, validator_id: str):
        """
        Permanently bans a validator from the network.
        """
        if validator_id in self.tombstoned_validators:
            print(f"Validator {validator_id} is already tombstoned.")
            return

        if validator_id in self.active_validators:
            validator_info = self.active_validators[validator_id]
            print(f"!!! TOMBSTONING VALIDATOR {validator_id} !!! "
                  f"Staked amount {validator_info['staked_amount']:.2f} is now permanently locked/burned.")
            
            # Conceptual handling of staked funds (e.g., burn, send to treasury)
            # In a real system, this would involve on-chain transactions.
            
            self._remove_from_active(validator_id)
            self._add_to_tombstoned(validator_id)
            print(f"Validator {validator_id} has been permanently tombstoned.")
        else:
            print(f"Cannot tombstone validator {validator_id}: Not found in active set.")

    def get_validator_status(self, validator_id: str) -> str:
        """Returns the status of a validator (Active, Tombstoned, Unknown)."""
        if validator_id in self.tombstoned_validators:
            return "Tombstoned"
        if validator_id in self.active_validators:
            return "Active"
        return "Unknown"

# Example Usage (for testing purposes)
if __name__ == "__main__":
    initial_stakes = {
        "validator_A": 1000.0,
        "validator_B": 1500.0,
        "validator_C": 2000.0
    }
    manager = TombstoneManager(initial_stakes, tombstone_threshold=2) # Tombstone after 2 slashing events

    print("\n--- Initial Status ---")
    for v_id in initial_stakes.keys():
        print(f"{v_id}: {manager.get_validator_status(v_id)}")

    print("\n--- Simulating Slashing Events ---")
    manager.record_slashing_event("validator_A", 50.0) # 1st slash for A
    manager.record_slashing_event("validator_B", 100.0) # 1st slash for B
    manager.record_slashing_event("validator_A", 75.0) # 2nd slash for A - should trigger tombstone

    print("\n--- Status After Slashing ---")
    for v_id in initial_stakes.keys():
        print(f"{v_id}: {manager.get_validator_status(v_id)}")
        if manager.get_validator_status(v_id) == "Active":
            info = manager.active_validators[v_id]
            print(f"  Staked: {info['staked_amount']:.2f}, Slashed Count: {info['slashed_count']}")

    print("\n--- Simulating another slash for a tombstoned validator ---")
    manager.record_slashing_event("validator_A", 10.0) # Should not affect A as it's tombstoned

    print("\n--- Simulating a slash for C (not enough to tombstone) ---")
    manager.record_slashing_event("validator_C", 200.0)
    print(f"Validator C status: {manager.get_validator_status('validator_C')}")
    if manager.get_validator_status('validator_C') == "Active":
        info = manager.active_validators['validator_C']
        print(f"  Staked: {info['staked_amount']:.2f}, Slashed Count: {info['slashed_count']}")
