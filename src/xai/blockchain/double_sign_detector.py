import logging
import time
from typing import Dict, Any, Tuple

logger = logging.getLogger("xai.blockchain.double_sign_detector")


class DoubleSignDetector:
    def __init__(self):
        # Stores validator signatures for blocks:
        # {validator_id: {block_height: signed_block_hash}}
        self.validator_signatures: Dict[str, Dict[int, str]] = {}
        logger.info("DoubleSignDetector initialized.")

    def _generate_double_sign_proof(
        self,
        validator_id: str,
        block_height: int,
        first_signed_block_hash: str,
        second_signed_block_hash: str,
    ) -> Dict[str, Any]:
        """
        Generates a conceptual proof of double-signing.
        In a real system, this would include the full signed block headers/messages.
        """
        proof = {
            "misbehavior_type": "DOUBLE_SIGNING",
            "validator_id": validator_id,
            "block_height": block_height,
            "conflicting_signatures": [
                {
                    "block_hash": first_signed_block_hash,
                    "signature": f"sig_for_{first_signed_block_hash}",
                },
                {
                    "block_hash": second_signed_block_hash,
                    "signature": f"sig_for_{second_signed_block_hash}",
                },
            ],
            "timestamp": time.time(),
        }
        logger.warning("Generated double-sign proof for %s at height %s", validator_id, block_height)
        return proof

    def process_signed_block(
        self, validator_id: str, block_height: int, signed_block_hash: str
    ) -> Tuple[bool, Dict[str, Any] | None]:
        """
        Processes a newly signed block and checks for double-signing.
        Returns (is_double_sign_detected, proof_if_detected).
        """
        if not isinstance(validator_id, str) or not validator_id:
            raise ValueError("Validator ID must be a non-empty string.")
        if not isinstance(block_height, int) or block_height < 0:
            raise ValueError("Block height must be a non-negative integer.")
        if not isinstance(signed_block_hash, str) or not signed_block_hash:
            raise ValueError("Signed block hash must be a non-empty string.")

        if validator_id not in self.validator_signatures:
            self.validator_signatures[validator_id] = {}

        validator_blocks = self.validator_signatures[validator_id]

        if block_height in validator_blocks:
            # A block at this height has already been signed by this validator
            existing_signed_block_hash = validator_blocks[block_height]

            if existing_signed_block_hash != signed_block_hash:
                # Double-sign detected!
                logger.error(
                    "Double-sign detected: validator %s height %s (%s vs %s)",
                    validator_id,
                    block_height,
                    existing_signed_block_hash,
                    signed_block_hash,
                )
                proof = self._generate_double_sign_proof(
                    validator_id, block_height, existing_signed_block_hash, signed_block_hash
                )
                return True, proof
            else:
                # Same block signed again (e.g., re-broadcast), not a double-sign
                logger.debug(
                    "Validator %s re-signed block %s at height %s",
                    validator_id,
                    signed_block_hash,
                    block_height,
                )
                return False, None
        else:
            # First time this validator signed a block at this height
            validator_blocks[block_height] = signed_block_hash
            logger.info(
                "Validator %s signed block %s at height %s",
                validator_id,
                signed_block_hash,
                block_height,
            )
            return False, None

    def get_state(self) -> Dict[str, Any]:
        """
        Get current detector state for snapshotting.

        Returns:
            Dictionary containing validator signatures state
        """
        import copy
        return {
            "validator_signatures": copy.deepcopy(self.validator_signatures)
        }

    def restore_state(self, state: Dict[str, Any]) -> None:
        """
        Restore detector state from a snapshot.

        Args:
            state: State dictionary from get_state()
        """
        import copy
        self.validator_signatures = copy.deepcopy(state.get("validator_signatures", {}))
        logger.info("DoubleSignDetector state restored from snapshot.")
