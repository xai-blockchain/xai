from typing import Dict, Any


class SlashingManager:
    # Define types of misbehavior and their associated slashing percentages
    MISBEHAVIOR_PENALTIES = {
        "DOUBLE_SIGNING": 0.10,  # 10% of staked amount
        "OFFLINE": 0.01,  # 1% of staked amount for prolonged downtime
        "EQUIVOCATION": 0.05,  # 5% for proposing conflicting blocks
        "INVALID_BLOCK_PROPOSAL": 0.02,  # 2% for proposing a block that violates consensus rules
    }

    def __init__(self, initial_validators: Dict[str, float]):
        """
        Initializes the SlashingManager with a dictionary of validators and their staked amounts.
        :param initial_validators: A dictionary where keys are validator_ids (str) and values are staked_amounts (float).
        """
        if not isinstance(initial_validators, dict):
            raise ValueError("Initial validators must be a dictionary.")
        for validator_id, staked_amount in initial_validators.items():
            if not isinstance(validator_id, str) or not validator_id:
                raise ValueError("Validator ID must be a non-empty string.")
            if not isinstance(staked_amount, (int, float)) or staked_amount <= 0:
                raise ValueError(f"Staked amount for {validator_id} must be a positive number.")

        self.validators: Dict[str, Dict[str, Any]] = {
            v_id: {"staked_amount": amount, "slashed_count": 0}
            for v_id, amount in initial_validators.items()
        }
        print(f"SlashingManager initialized with {len(self.validators)} validators.")

    def add_validator(self, validator_id: str, staked_amount: float):
        """Adds a new validator to the system."""
        if validator_id in self.validators:
            raise ValueError(f"Validator {validator_id} already exists.")
        if not isinstance(staked_amount, (int, float)) or staked_amount <= 0:
            raise ValueError("Staked amount must be a positive number.")
        self.validators[validator_id] = {"staked_amount": staked_amount, "slashed_count": 0}
        print(f"Validator {validator_id} added with {staked_amount:.2f} staked.")

    def report_misbehavior(
        self, reporter_id: str, validator_id: str, misbehavior_type: str, evidence: Any = None
    ) -> bool:
        """
        Reports a validator's misbehavior.
        In a real system, 'evidence' would be cryptographically verifiable.
        Returns True if misbehavior is valid and slashing is applied, False otherwise.
        """
        if validator_id not in self.validators:
            print(f"Misbehavior report for unknown validator {validator_id} by {reporter_id}.")
            return False
        if misbehavior_type not in self.MISBEHAVIOR_PENALTIES:
            print(
                f"Misbehavior report for unknown type '{misbehavior_type}' for {validator_id} by {reporter_id}."
            )
            return False

        # Conceptual evidence validation
        if not evidence:
            print(
                f"Warning: No evidence provided for {misbehavior_type} by {validator_id}. Slashing might not be applied."
            )
            # In a real system, lack of evidence would prevent slashing.
            # For this simulation, we'll proceed to demonstrate slashing logic.

        print(
            f"Misbehavior '{misbehavior_type}' reported for validator {validator_id} by {reporter_id}."
        )
        return self.apply_slashing(validator_id, misbehavior_type)

    def apply_slashing(self, validator_id: str, misbehavior_type: str) -> bool:
        """
        Applies the slashing penalty to a validator based on the misbehavior type.
        """
        if validator_id not in self.validators:
            print(f"Cannot apply slashing: Validator {validator_id} not found.")
            return False
        if misbehavior_type not in self.MISBEHAVIOR_PENALTIES:
            print(f"Cannot apply slashing: Unknown misbehavior type '{misbehavior_type}'.")
            return False

        validator_info = self.validators[validator_id]
        staked_amount = validator_info["staked_amount"]
        penalty_percentage = self.MISBEHAVIOR_PENALTIES[misbehavior_type]
        slashed_amount = staked_amount * penalty_percentage

        if slashed_amount > 0:
            validator_info["staked_amount"] -= slashed_amount
            validator_info["slashed_count"] += 1
            print(
                f"Validator {validator_id} slashed {slashed_amount:.2f} for '{misbehavior_type}'. "
                f"New staked amount: {validator_info['staked_amount']:.2f}."
            )
            return True
        else:
            print(
                f"No slashing applied for {misbehavior_type} on {validator_id} (penalty is zero)."
            )
            return False

    def get_validator_status(self, validator_id: str) -> Dict[str, Any] | None:
        """Returns the current status of a validator."""
        return self.validators.get(validator_id)


# Example Usage (for testing purposes)
if __name__ == "__main__":
    initial_stakes = {"validator_A": 1000.0, "validator_B": 500.0, "validator_C": 2000.0}
    slashing_manager = SlashingManager(initial_stakes)

    print("\n--- Initial Validator Status ---")
    for v_id in initial_stakes.keys():
        status = slashing_manager.get_validator_status(v_id)
        print(
            f"{v_id}: Staked={status['staked_amount']:.2f}, Slashed Count={status['slashed_count']}"
        )

    print("\n--- Reporting Misbehavior ---")
    slashing_manager.report_misbehavior(
        "watcher_1", "validator_A", "DOUBLE_SIGNING", evidence="proof_A_double_sign"
    )
    slashing_manager.report_misbehavior("watcher_2", "validator_B", "OFFLINE")
    slashing_manager.report_misbehavior(
        "watcher_3", "validator_C", "EQUIVOCATION", evidence="proof_C_equivocation"
    )
    slashing_manager.report_misbehavior(
        "watcher_4", "validator_A", "OFFLINE"
    )  # Validator A misbehaves again

    print("\n--- Validator Status After Slashing ---")
    for v_id in initial_stakes.keys():
        status = slashing_manager.get_validator_status(v_id)
        print(
            f"{v_id}: Staked={status['staked_amount']:.2f}, Slashed Count={status['slashed_count']}"
        )

    print("\n--- Reporting Unknown Validator or Misbehavior ---")
    slashing_manager.report_misbehavior("watcher_5", "validator_D", "DOUBLE_SIGNING")
    slashing_manager.report_misbehavior("watcher_6", "validator_A", "UNKNOWN_MISBEHAVIOR")
