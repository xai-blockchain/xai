# src/xai/blockchain/slashing_manager.py
"""
Manages validator slashing for misbehavior, with persistent state.
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from ..database.storage_manager import StorageManager

logger = logging.getLogger("xai.blockchain.slashing_manager")


def get_validator_key(validator_id: str) -> str:
    """Returns the database key for a given validator ID."""
    return f"validator:{validator_id}"


class SlashingManager:
    """
    Manages validator stakes and applies slashing penalties for misbehavior,
    persisting all state to a database.
    """
    # Define types of misbehavior and their associated slashing percentages
    MISBEHAVIOR_PENALTIES = {
        "DOUBLE_SIGNING": 0.10,  # 10% of staked amount
        "OFFLINE": 0.01,  # 1% of staked amount for prolonged downtime
        "EQUIVOCATION": 0.05,  # 5% for proposing conflicting blocks
        "INVALID_BLOCK_PROPOSAL": 0.02,  # 2% for proposing a block that violates consensus rules
    }

    def __init__(self, db_path: Path, initial_validators: Optional[Dict[str, float]] = None):
        """
        Initializes the SlashingManager with a persistent database.

        Args:
            db_path (Path): The path to the SQLite database file.
            initial_validators (Optional[Dict[str, float]]): A dictionary of validators
                and their staked amounts to seed the database on first run.
        """
        self.storage = StorageManager(db_path)
        if initial_validators:
            self._seed_initial_validators(initial_validators)

    def _seed_initial_validators(self, initial_validators: Dict[str, float]):
        """Seeds the database with initial validators if they don't already exist."""
        for validator_id, staked_amount in initial_validators.items():
            if not isinstance(validator_id, str) or not validator_id:
                raise ValueError("Validator ID must be a non-empty string.")
            if not isinstance(staked_amount, (int, float)) or staked_amount <= 0:
                raise ValueError(f"Staked amount for {validator_id} must be a positive number.")

            validator_key = get_validator_key(validator_id)
            if self.storage.get(validator_key) is None:
                self.add_validator(validator_id, staked_amount)
        logger.info("SlashingManager initialized and seeded with %d validators.", len(initial_validators))

    def add_validator(self, validator_id: str, staked_amount: float):
        """Adds a new validator to the database."""
        validator_key = get_validator_key(validator_id)
        if self.storage.get(validator_key) is not None:
            raise ValueError(f"Validator {validator_id} already exists.")
        if not isinstance(staked_amount, (int, float)) or staked_amount <= 0:
            raise ValueError("Staked amount must be a positive number.")
        
        validator_data = {"staked_amount": staked_amount, "slashed_count": 0}
        self.storage.set(validator_key, validator_data)
        logger.info("Validator %s added with %.2f staked.", validator_id, staked_amount)

    def _validate_evidence(self, misbehavior_type: str, evidence: Any) -> bool:
        """
        Validates the structure of evidence provided for a misbehavior report.
        This is a preliminary, non-cryptographic check.

        Returns True if the evidence structure is plausible, False otherwise.
        """
        if evidence is None:
            logger.warning("Evidence validation failed: No evidence provided.")
            return False

        if misbehavior_type == "DOUBLE_SIGNING":
            if not isinstance(evidence, dict) or "header1" not in evidence or "header2" not in evidence:
                logger.warning("Evidence validation failed for DOUBLE_SIGNING: 'header1' and 'header2' are required in evidence.")
                return False
            # Future step: Cryptographically verify the signatures in the headers.
            logger.info("Evidence for DOUBLE_SIGNING has the correct structure.")
            return True

        # For other types, we just check that evidence is not None for now.
        # This can be expanded with specific structural checks for each type.
        logger.info("Evidence for %s is present.", misbehavior_type)
        return True


    def report_misbehavior(
        self, reporter_id: str, validator_id: str, misbehavior_type: str, evidence: Any = None
    ) -> bool:
        """
        Reports a validator's misbehavior, validates the evidence, and applies slashing if valid.
        Returns True if misbehavior is valid and slashing is applied.
        """
        validator_key = get_validator_key(validator_id)
        if self.storage.get(validator_key) is None:
            logger.warning("Misbehavior report for unknown validator %s by %s.", validator_id, reporter_id)
            return False
        if misbehavior_type not in self.MISBEHAVIOR_PENALTIES:
            logger.warning(
                "Misbehavior report for unknown type '%s' for %s by %s.",
                misbehavior_type, validator_id, reporter_id,
            )
            return False

        # Validate the provided evidence before proceeding
        if not self._validate_evidence(misbehavior_type, evidence):
            logger.error(
                "Slashing for %s on validator %s denied due to invalid evidence.",
                misbehavior_type, validator_id
            )
            return False

        logger.info(
            "Evidence for '%s' on validator %s is valid. Proceeding with slashing.",
            misbehavior_type, validator_id,
        )
        return self.apply_slashing(validator_id, misbehavior_type)

    def apply_slashing(self, validator_id: str, misbehavior_type: str) -> bool:
        """
        Applies the slashing penalty to a validator, updating their state in the database.
        """
        validator_key = get_validator_key(validator_id)
        validator_info = self.storage.get(validator_key)

        if validator_info is None:
            # This check is somewhat redundant if only called by report_misbehavior, but safe to keep.
            logger.warning("Cannot apply slashing: validator %s not found.", validator_id)
            return False
        
        staked_amount = validator_info["staked_amount"]
        penalty_percentage = self.MISBEHAVIOR_PENALTIES[misbehavior_type]
        slashed_amount = staked_amount * penalty_percentage

        if slashed_amount > 0:
            validator_info["staked_amount"] -= slashed_amount
            validator_info["slashed_count"] += 1
            self.storage.set(validator_key, validator_info)
            logger.warning(
                "Validator %s slashed %.2f for '%s'. New staked amount: %.2f.",
                validator_id, slashed_amount, misbehavior_type, validator_info["staked_amount"],
            )
            return True
        
        logger.info("No slashing applied for %s on %s (penalty is zero).", misbehavior_type, validator_id)
        return False

    def get_validator_status(self, validator_id: str) -> Optional[Dict[str, Any]]:
        """Returns the current status of a validator from the database."""
        return self.storage.get(get_validator_key(validator_id))

    def close(self):
        """Closes the underlying storage connection."""
        self.storage.close()

