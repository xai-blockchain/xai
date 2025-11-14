from typing import Dict, Any
from datetime import datetime, timezone
from src.aixn.blockchain.slashing import SlashingManager, ValidatorStake # Import SlashingManager

class FraudProof:
    def __init__(self, challenger_address: str, challenged_validator_address: str,
                 proof_data: Dict[str, Any], block_number: int,
                 challenge_period_ends_at: int):
        if not challenger_address or not challenged_validator_address:
            raise ValueError("Challenger and challenged validator addresses cannot be empty.")
        if not proof_data:
            raise ValueError("Proof data cannot be empty.")
        if block_number <= 0:
            raise ValueError("Block number must be positive.")
        if challenge_period_ends_at <= datetime.now(timezone.utc).timestamp():
            print("Warning: Challenge period ends in the past or immediately. Ensure future timestamp.")

        self.challenger_address = challenger_address
        self.challenged_validator_address = challenged_validator_address
        self.proof_data = proof_data
        self.block_number = block_number
        self.submission_timestamp = int(datetime.now(timezone.utc).timestamp())
        self.challenge_period_ends_at = challenge_period_ends_at
        self.status = "pending" # pending, verified, rejected

    def to_dict(self) -> Dict[str, Any]:
        return {
            "challenger_address": self.challenger_address,
            "challenged_validator_address": self.challenged_validator_address,
            "proof_data": self.proof_data,
            "block_number": self.block_number,
            "submission_timestamp": self.submission_timestamp,
            "challenge_period_ends_at": self.challenge_period_ends_at,
            "status": self.status
        }

    def __repr__(self):
        return (
                f"FraudProof(challenger='{self.challenger_address[:8]}...', "
                f"challenged='{self.challenged_validator_address[:8]}...', "
                f"block={self.block_number}, status='{self.status}')"
        )

class FraudProofManager:
    def __init__(self, slashing_manager: SlashingManager):
        self.fraud_proofs: Dict[str, FraudProof] = {} # Key: unique proof ID
        self.slashing_manager = slashing_manager
        self._proof_counter = 0

    def _generate_proof_id(self) -> str:
        self._proof_counter += 1
        return f"fraud_proof_{self._proof_counter}"

    def submit_fraud_proof(self, challenger_address: str, challenged_validator_address: str,
                           proof_data: Dict[str, Any], block_number: int,
                           challenge_period_duration_seconds: int = 3600) -> FraudProof:
        
        challenge_period_ends_at = int(datetime.now(timezone.utc).timestamp()) + challenge_period_duration_seconds
        
        proof = FraudProof(challenger_address, challenged_validator_address,
                           proof_data, block_number, challenge_period_ends_at)
        proof_id = self._generate_proof_id()
        self.fraud_proofs[proof_id] = proof
        print(f"Fraud proof {proof_id} submitted by {challenger_address} against {challenged_validator_address} for block {block_number}.")
        return proof

    def verify_fraud_proof(self, proof_id: str) -> bool:
        """
        Simulates the verification of a fraud proof.
        In a real system, this would involve complex on-chain logic or an interactive verification game.
        Here, we'll use a simplified heuristic for demonstration.
        """
        proof = self.fraud_proofs.get(proof_id)
        if not proof:
            print(f"Error: Fraud proof {proof_id} not found.")
            return False

        if proof.status != "pending":
            print(f"Fraud proof {proof_id} already {proof.status}.")
            return proof.status == "verified"

        current_time = int(datetime.now(timezone.utc).timestamp())
        if current_time > proof.challenge_period_ends_at:
            print(f"Fraud proof {proof_id}: Challenge period has ended. Proof cannot be verified.")
            proof.status = "rejected"
            return False

        print(f"Verifying fraud proof {proof_id}...")
        # Simplified verification logic: assume proof is valid if it contains "invalid_state"
        # In a real system, this would be a cryptographic verification.
        is_valid = "invalid_state" in proof.proof_data.get("type", "") or \
                   "incorrect_signature" in proof.proof_data.get("type", "")

        if is_valid:
            proof.status = "verified"
            print(f"Fraud proof {proof_id} VERIFIED. Slashing challenged validator {proof.challenged_validator_address}.")
            self.slashing_manager.report_malicious_behavior(
                proof.challenged_validator_address,
                "fraud_proven" # A new offense type for fraud
            )
            # Optionally reward challenger here
            return True
        else:
            proof.status = "rejected"
            print(f"Fraud proof {proof_id} REJECTED. Proof data was insufficient or invalid.")
            return False

# Example Usage (for testing purposes)
if __name__ == "__main__":
    # Setup SlashingManager
    slashing_manager = SlashingManager()
    slashing_manager.add_validator_stake(ValidatorStake("0xValidatorA", 10000))
    slashing_manager.add_validator_stake(ValidatorStake("0xChallengedValidator", 25000))
    slashing_manager.add_validator_stake(ValidatorStake("0xHonestValidator", 15000))

    # Add a new offense type for fraud to the SlashingManager
    SlashingManager.OFFENSE_PENALTIES["fraud_proven"] = 0.50 # 50% slash for proven fraud

    fraud_manager = FraudProofManager(slashing_manager)

    print("\n--- Submitting Fraud Proofs ---")
    proof1 = fraud_manager.submit_fraud_proof(
        challenger_address="0xChallenger1",
        challenged_validator_address="0xChallengedValidator",
        proof_data={"type": "invalid_state_transition", "details": "State hash mismatch at block 123"},
        block_number=123,
        challenge_period_duration_seconds=10 # Short period for testing
    )

    proof2 = fraud_manager.submit_fraud_proof(
        challenger_address="0xChallenger2",
        challenged_validator_address="0xHonestValidator",
        proof_data={"type": "minor_error", "details": "Small discrepancy"},
        block_number=456,
        challenge_period_duration_seconds=10
    )

    print("\n--- Verifying Fraud Proofs ---")
    # Verify proof 1 (should be successful)
    fraud_manager.verify_fraud_proof(proof1._proof_counter)
    print(f"Validator 0xChallengedValidator stake after verification: {slashing_manager.get_validator_stake('0xChallengedValidator').staked_amount}")

    # Verify proof 2 (should be rejected due to simplified logic)
    fraud_manager.verify_fraud_proof(proof2._proof_counter)
    print(f"Validator 0xHonestValidator stake after verification: {slashing_manager.get_validator_stake('0xHonestValidator').staked_amount}")

    # Try to verify an expired proof (will be rejected)
    import time
    time.sleep(11) # Wait for challenge period to end
    print("\n--- Verifying Expired Proof ---")
    proof3 = fraud_manager.submit_fraud_proof(
        challenger_address="0xChallenger3",
        challenged_validator_address="0xValidatorA",
        proof_data={"type": "incorrect_signature_in_block", "details": "Signature for tx 789 is invalid"},
        block_number=789,
        challenge_period_duration_seconds=1 # Very short period
    )
    fraud_manager.verify_fraud_proof(proof3._proof_counter)
    print(f"Validator 0xValidatorA stake after expired proof attempt: {slashing_manager.get_validator_stake('0xValidatorA').staked_amount}")
