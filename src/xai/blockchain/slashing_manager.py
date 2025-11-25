import logging
from typing import Dict, Any

logger = logging.getLogger("xai.blockchain.slashing_manager")

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
        logger.info("SlashingManager initialized with %d validators.", len(self.validators))

    def add_validator(self, validator_id: str, staked_amount: float):
        """Adds a new validator to the system."""
        if validator_id in self.validators:
            raise ValueError(f"Validator {validator_id} already exists.")
        if not isinstance(staked_amount, (int, float)) or staked_amount <= 0:
            raise ValueError("Staked amount must be a positive number.")
        self.validators[validator_id] = {"staked_amount": staked_amount, "slashed_count": 0}
        logger.info("Validator %s added with %.2f staked.", validator_id, staked_amount)

    def report_misbehavior(
        self, reporter_id: str, validator_id: str, misbehavior_type: str, evidence: Any = None
    ) -> bool:
        """
        Reports a validator's misbehavior.
        In a real system, 'evidence' would be cryptographically verifiable.
        Returns True if misbehavior is valid and slashing is applied, False otherwise.
        """
        if validator_id not in self.validators:
            logger.warning(
                "Misbehavior report for unknown validator %s by %s.", validator_id, reporter_id
            )
            return False
        if misbehavior_type not in self.MISBEHAVIOR_PENALTIES:
            logger.warning(
                "Misbehavior report for unknown type '%s' for %s by %s.",
                misbehavior_type,
                validator_id,
                reporter_id,
            )
            return False

        # Conceptual evidence validation
        if not evidence:
            logger.warning(
                "No evidence provided for %s misbehavior on %s (reported by %s).",
                misbehavior_type,
                validator_id,
                reporter_id,
            )
            # In a real system, lack of evidence would prevent slashing.
            # For this simulation, we'll proceed to demonstrate slashing logic.

        logger.info(
            "Misbehavior '%s' reported for validator %s by %s.",
            misbehavior_type,
            validator_id,
            reporter_id,
        )
        return self.apply_slashing(validator_id, misbehavior_type)

    def apply_slashing(self, validator_id: str, misbehavior_type: str) -> bool:
        """
        Applies the slashing penalty to a validator based on the misbehavior type.
        """
        if validator_id not in self.validators:
            logger.warning("Cannot apply slashing: validator %s not found.", validator_id)
            return False
        if misbehavior_type not in self.MISBEHAVIOR_PENALTIES:
            logger.warning(
                "Cannot apply slashing: unknown misbehavior type '%s'.", misbehavior_type
            )
            return False

        validator_info = self.validators[validator_id]
        staked_amount = validator_info["staked_amount"]
        penalty_percentage = self.MISBEHAVIOR_PENALTIES[misbehavior_type]
        slashed_amount = staked_amount * penalty_percentage

        if slashed_amount > 0:
            validator_info["staked_amount"] -= slashed_amount
            validator_info["slashed_count"] += 1
            logger.warning(
                "Validator %s slashed %.2f for '%s'. New staked amount: %.2f.",
                validator_id,
                slashed_amount,
                misbehavior_type,
                validator_info["staked_amount"],
            )
            return True
        else:
            logger.info(
                "No slashing applied for %s on %s (penalty is zero).", misbehavior_type, validator_id
            )
            return False

    def get_validator_status(self, validator_id: str) -> Dict[str, Any] | None:
        """Returns the current status of a validator."""
        return self.validators.get(validator_id)

