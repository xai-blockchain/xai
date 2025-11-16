from typing import Dict, Any, Tuple
import time


class DoubleSignDetector:
    def __init__(self):
        # Stores validator signatures for blocks:
        # {validator_id: {block_height: signed_block_hash}}
        self.validator_signatures: Dict[str, Dict[int, str]] = {}
        print("DoubleSignDetector initialized.")

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
        print(f"Generated double-sign proof for {validator_id} at height {block_height}.")
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
                print(
                    f"!!! DOUBLE-SIGN DETECTED !!! Validator {validator_id} signed two different blocks "
                    f"at height {block_height}: {existing_signed_block_hash[:8]}... and {signed_block_hash[:8]}..."
                )
                proof = self._generate_double_sign_proof(
                    validator_id, block_height, existing_signed_block_hash, signed_block_hash
                )
                return True, proof
            else:
                # Same block signed again (e.g., re-broadcast), not a double-sign
                print(
                    f"Validator {validator_id} re-signed block {signed_block_hash[:8]}... at height {block_height}."
                )
                return False, None
        else:
            # First time this validator signed a block at this height
            validator_blocks[block_height] = signed_block_hash
            print(
                f"Validator {validator_id} signed block {signed_block_hash[:8]}... at height {block_height}."
            )
            return False, None


# Example Usage (for testing purposes)
if __name__ == "__main__":
    # For timestamp in proof
    detector = DoubleSignDetector()

    # Scenario 1: Normal operation
    print("\n--- Scenario 1: Normal Operation ---")
    is_ds, proof = detector.process_signed_block("validator_X", 100, "0xblock100_v1")
    print(f"Double-sign detected: {is_ds}")
    is_ds, proof = detector.process_signed_block("validator_Y", 100, "0xblock100_v2")
    print(f"Double-sign detected: {is_ds}")
    is_ds, proof = detector.process_signed_block("validator_X", 101, "0xblock101_v1")
    print(f"Double-sign detected: {is_ds}")

    # Scenario 2: Double-signing by validator_Z
    print("\n--- Scenario 2: Double-signing ---")
    is_ds, proof = detector.process_signed_block("validator_Z", 102, "0xblock102_A")
    print(f"Double-sign detected: {is_ds}")
    is_ds, proof = detector.process_signed_block(
        "validator_Z", 102, "0xblock102_B"
    )  # Different hash at same height
    print(f"Double-sign detected: {is_ds}")
    if is_ds:
        print("Proof:", proof)

    # Scenario 3: Validator re-signs the same block (not a double-sign)
    print("\n--- Scenario 3: Re-signing same block ---")
    is_ds, proof = detector.process_signed_block("validator_A", 50, "0xblock50_main")
    print(f"Double-sign detected: {is_ds}")
    is_ds, proof = detector.process_signed_block("validator_A", 50, "0xblock50_main")  # Same hash
    print(f"Double-sign detected: {is_ds}")
