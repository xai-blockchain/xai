from __future__ import annotations

import logging
import secrets
from typing import Any

logger = logging.getLogger("xai.blockchain.validator_rotation")

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

    def to_dict(self) -> dict[str, Any]:
        return {"address": self.address, "stake": self.stake, "reputation": self.reputation}

    def __repr__(self):
        return f"Validator(address='{self.address[:8]}...', stake={self.stake}, reputation={self.reputation:.2f})"

class ValidatorSetManager:
    def __init__(self, initial_validators: list[Validator] = None, set_size: int = 5):
        if not isinstance(set_size, int) or set_size <= 0:
            raise ValueError("Validator set size must be a positive integer.")
        self.all_validators: dict[str, Validator] = {}
        if initial_validators:
            for validator in initial_validators:
                self.add_validator(validator)
        self.current_validator_set: list[Validator] = []
        self.set_size = set_size
        self.epoch = 0

    def add_validator(self, validator: Validator):
        if validator.address in self.all_validators:
            logger.warning("Validator %s already exists. Updating details.", validator.address)
        self.all_validators[validator.address] = validator

    def remove_validator(self, address: str):
        if address in self.all_validators:
            del self.all_validators[address]
            self.current_validator_set = [
                v for v in self.current_validator_set if v.address != address
            ]
            logger.info("Validator %s removed.", address)
        else:
            logger.warning("Validator %s not found.", address)

    def _select_validators(self) -> list[Validator]:
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

        # Use cryptographically secure random selection for validator rotation
        # This prevents prediction and manipulation of validator selection
        sr = secrets.SystemRandom()
        selected_set = sr.choices(eligible_validators, weights=weights, k=self.set_size)

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
            logger.warning(
                "Selected %d unique validators, expected %d. Adjusting set size.",
                len(unique_selected_set),
                self.set_size,
            )
            return unique_selected_set

        return unique_selected_set

    def rotate_validator_set(self) -> list[Validator]:
        """
        Rotates the validator set for a new epoch.
        """
        logger.info("Rotating validator set for Epoch %s", self.epoch + 1)
        new_set = self._select_validators()
        self.current_validator_set = new_set
        self.epoch += 1
        logger.info("New validator set for Epoch %s: %s", self.epoch, new_set)
        return self.current_validator_set

    def get_current_validator_set(self) -> list[Validator]:
        return self.current_validator_set

