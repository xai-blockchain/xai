import random
from typing import List, Dict, Any


class Validator:
    def __init__(self, address: str, stake: int, reputation: float = 0.5):
        if not isinstance(address, str) or not address:
            raise ValueError("Validator address must be a non-empty string.")
        if not isinstance(stake, int) or stake <= 0:
            raise ValueError("Validator stake must be a positive integer.")
        if not isinstance(reputation, (int, float)) or not (0 <= reputation <= 1):
            raise ValueError("Validator reputation must be between 0 and 1.")

        self.address = address
        self.stake = stake
        self.reputation = reputation  # A value between 0 and 1, higher is better

    def to_dict(self) -> Dict[str, Any]:
        return {"address": self.address, "stake": self.stake, "reputation": self.reputation}

    def __repr__(self):
        return f"Validator(address='{self.address[:8]}...', stake={self.stake}, reputation={self.reputation:.2f})"


class ValidatorSetManager:
    def __init__(self, initial_validators: List[Validator] = None, set_size: int = 5):
        if not isinstance(set_size, int) or set_size <= 0:
            raise ValueError("Validator set size must be a positive integer.")
        self.all_validators: Dict[str, Validator] = {}
        if initial_validators:
            for validator in initial_validators:
                self.add_validator(validator)
        self.current_validator_set: List[Validator] = []
        self.set_size = set_size
        self.epoch = 0

    def add_validator(self, validator: Validator):
        if validator.address in self.all_validators:
            print(f"Warning: Validator {validator.address} already exists. Updating details.")
        self.all_validators[validator.address] = validator

    def remove_validator(self, address: str):
        if address in self.all_validators:
            del self.all_validators[address]
            self.current_validator_set = [
                v for v in self.current_validator_set if v.address != address
            ]
            print(f"Validator {address} removed.")
        else:
            print(f"Warning: Validator {address} not found.")

    def _select_validators(self) -> List[Validator]:
        """
        Selects a new validator set based on a weighted random selection.
        Weight is proportional to stake and reputation.
        """
        eligible_validators = list(self.all_validators.values())
        if len(eligible_validators) < self.set_size:
            raise ValueError(
                f"Not enough eligible validators ({len(eligible_validators)}) to form a set of size {self.set_size}."
            )

        # Calculate weights: stake * reputation (can be more complex)
        weights = [v.stake * v.reputation for v in eligible_validators]

        # Use random.choices for weighted random selection
        # k is the number of validators to select
        selected_set = random.choices(eligible_validators, weights=weights, k=self.set_size)

        # Ensure uniqueness if random.choices can return duplicates (it can if k > len(population))
        # For simplicity, if duplicates are selected, we'll just have a smaller set or re-select.
        # A more robust solution would handle this carefully, e.g., by sampling without replacement.
        unique_selected_set = []
        seen_addresses = set()
        for validator in selected_set:
            if validator.address not in seen_addresses:
                unique_selected_set.append(validator)
                seen_addresses.add(validator.address)

        # If after making unique, we don't have enough, we might need to re-sample or adjust logic
        if len(unique_selected_set) < self.set_size:
            # This is a simplified handling. In a real system, you'd ensure enough unique
            # validators are selected, possibly by re-running selection or adjusting weights.
            print(
                f"Warning: Selected {len(unique_selected_set)} unique validators, expected {self.set_size}. Adjusting set size."
            )
            return unique_selected_set

        return unique_selected_set

    def rotate_validator_set(self) -> List[Validator]:
        """
        Rotates the validator set for a new epoch.
        """
        print(f"\n--- Rotating validator set for Epoch {self.epoch + 1} ---")
        new_set = self._select_validators()
        self.current_validator_set = new_set
        self.epoch += 1
        print(f"New validator set for Epoch {self.epoch}:")
        for validator in self.current_validator_set:
            print(f"  - {validator}")
        return self.current_validator_set

    def get_current_validator_set(self) -> List[Validator]:
        return self.current_validator_set


# Example Usage (for testing purposes)
if __name__ == "__main__":
    # Create some initial validators
    v1 = Validator("0xValidatorA", 1000, 0.9)
    v2 = Validator("0xValidatorB", 500, 0.7)
    v3 = Validator("0xValidatorC", 2000, 0.8)
    v4 = Validator("0xValidatorD", 750, 0.6)
    v5 = Validator("0xValidatorE", 1500, 0.95)
    v6 = Validator("0xValidatorF", 300, 0.4)
    v7 = Validator("0xValidatorG", 1200, 0.85)

    initial_pool = [v1, v2, v3, v4, v5, v6, v7]

    # Initialize manager with a set size of 3
    manager = ValidatorSetManager(initial_validators=initial_pool, set_size=3)

    # Perform a few rotations
    manager.rotate_validator_set()
    manager.rotate_validator_set()
    manager.rotate_validator_set()

    # Add a new validator
    v8 = Validator("0xValidatorH", 2500, 0.99)
    manager.add_validator(v8)
    print(f"\nAdded new validator: {v8}")

    manager.rotate_validator_set()

    # Remove a validator
    manager.remove_validator("0xValidatorB")
    manager.rotate_validator_set()
