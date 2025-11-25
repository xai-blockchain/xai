import logging
from typing import Any, Dict, Set


logger = logging.getLogger("xai.blockchain.tombstone_manager")


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

        self.tombstoned_validators: Set[str] = set()  # Stores IDs of permanently banned validators
        logger.info(
            "TombstoneManager initialized with %s validators (threshold=%s)",
            len(self.active_validators),
            self.tombstone_threshold,
        )

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
            logger.warning("Validator %s already tombstoned; ignoring slashing event", validator_id)
            return

        if validator_id in self.active_validators:
            validator_info = self.active_validators[validator_id]
            validator_info["staked_amount"] -= slashed_amount
            validator_info["slashed_count"] += 1
            logger.info(
                "Slashing event recorded for %s (staked %.2f, count %s)",
                validator_id,
                validator_info["staked_amount"],
                validator_info["slashed_count"],
            )
            self.check_for_tombstone(validator_id)
        else:
            logger.warning("Slashing event recorded for unknown validator %s", validator_id)

    def check_for_tombstone(self, validator_id: str) -> bool:
        """
        Checks if a validator meets the conditions for tombstoning.
        Returns True if tombstoned, False otherwise.
        """
        if validator_id in self.tombstoned_validators:
            return True  # Already tombstoned

        if validator_id in self.active_validators:
            validator_info = self.active_validators[validator_id]
            if validator_info["slashed_count"] >= self.tombstone_threshold:
                logger.warning(
                    "Validator %s reached tombstone threshold %s", validator_id, self.tombstone_threshold
                )
                self.tombstone_validator(validator_id)
                return True
        return False

    def tombstone_validator(self, validator_id: str):
        """
        Permanently bans a validator from the network.
        """
        if validator_id in self.tombstoned_validators:
            logger.warning("Validator %s already tombstoned", validator_id)
            return

        if validator_id in self.active_validators:
            validator_info = self.active_validators[validator_id]
            logger.error(
                "Tombstoning validator %s (staked %.2f locked)",
                validator_id,
                validator_info["staked_amount"],
            )

            # Conceptual handling of staked funds (e.g., burn, send to treasury)
            # In a real system, this would involve on-chain transactions.

            self._remove_from_active(validator_id)
            self._add_to_tombstoned(validator_id)
            logger.info("Validator %s permanently tombstoned", validator_id)
        else:
            logger.warning("Cannot tombstone %s: not found in active set", validator_id)

    def get_validator_status(self, validator_id: str) -> str:
        """Returns the status of a validator (Active, Tombstoned, Unknown)."""
        if validator_id in self.tombstoned_validators:
            return "Tombstoned"
        if validator_id in self.active_validators:
            return "Active"
        return "Unknown"

