from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Callable

from xai.blockchain.slashing import SlashingManager

logger = logging.getLogger("xai.blockchain.fraud_proofs")

class FraudProof:
    def __init__(
        self,
        challenger_address: str,
        challenged_validator_address: str,
        proof_data: dict[str, Any],
        block_number: int,
        challenge_period_ends_at: int,
        submission_timestamp: int | None = None,
    ):
        if not challenger_address or not challenged_validator_address:
            raise ValueError("Challenger and challenged validator addresses cannot be empty.")
        if not proof_data:
            raise ValueError("Proof data cannot be empty.")
        if block_number <= 0:
            raise ValueError("Block number must be positive.")
        if challenge_period_ends_at <= datetime.now(timezone.utc).timestamp():
            logger.warning(
                "Challenge period for fraud proof targeting %s ends immediately."
                " Ensure timestamps are in the future.",
                challenged_validator_address,
            )

        self.challenger_address = challenger_address
        self.challenged_validator_address = challenged_validator_address
        self.proof_data = proof_data
        self.block_number = block_number
        self.submission_timestamp = submission_timestamp or int(datetime.now(timezone.utc).timestamp())
        self.challenge_period_ends_at = challenge_period_ends_at
        self.status = "pending"  # pending, verified, rejected, expired

    def to_dict(self) -> dict[str, Any]:
        return {
            "challenger_address": self.challenger_address,
            "challenged_validator_address": self.challenged_validator_address,
            "proof_data": self.proof_data,
            "block_number": self.block_number,
            "submission_timestamp": self.submission_timestamp,
            "challenge_period_ends_at": self.challenge_period_ends_at,
            "status": self.status,
        }

    def __repr__(self):
        return (
            f"FraudProof(challenger='{self.challenger_address[:8]}...', "
            f"challenged='{self.challenged_validator_address[:8]}...', "
            f"block={self.block_number}, status='{self.status}')"
        )

class FraudProofManager:
    def __init__(
        self,
        slashing_manager: SlashingManager,
        time_provider: Callable[[], int] | None = None,
    ):
        self.fraud_proofs: dict[str, FraudProof] = {}  # Key: unique proof ID
        self.slashing_manager = slashing_manager
        self._proof_counter = 0
        self._time_provider = time_provider or (lambda: int(datetime.now(timezone.utc).timestamp()))
        self.logger = logger
        SlashingManager.OFFENSE_PENALTIES.setdefault("fraud_proven", 0.50)

    def _generate_proof_id(self) -> str:
        self._proof_counter += 1
        return f"fraud_proof_{self._proof_counter}"

    def submit_fraud_proof(
        self,
        challenger_address: str,
        challenged_validator_address: str,
        proof_data: dict[str, Any],
        block_number: int,
        challenge_period_duration_seconds: int = 3600,
    ) -> str:
        if challenge_period_duration_seconds <= 0:
            raise ValueError("Challenge period must be greater than zero seconds.")

        submission_time = self._current_time()
        challenge_period_ends_at = submission_time + challenge_period_duration_seconds

        proof = FraudProof(
            challenger_address,
            challenged_validator_address,
            proof_data,
            block_number,
            challenge_period_ends_at,
            submission_timestamp=submission_time,
        )
        proof_id = self._generate_proof_id()
        self.fraud_proofs[proof_id] = proof
        self.logger.info(
            "Fraud proof %s submitted by %s against %s for block %s",
            proof_id,
            challenger_address,
            challenged_validator_address,
            block_number,
        )
        return proof_id

    def get_proof(self, proof_id: str) -> FraudProof | None:
        return self.fraud_proofs.get(proof_id)

    def verify_fraud_proof(self, proof_id: str) -> bool:
        """
        Simulates the verification of a fraud proof.
        In a real system, this would involve complex on-chain logic or an interactive verification game.
        Here, we'll use a simplified heuristic for demonstration.
        """
        proof = self.fraud_proofs.get(proof_id)
        if not proof:
            self.logger.error("Fraud proof %s not found.", proof_id)
            return False

        if proof.status == "verified":
            self.logger.info("Fraud proof %s already verified.", proof_id)
            return True
        if proof.status in {"rejected", "expired"}:
            self.logger.warning("Fraud proof %s already %s.", proof_id, proof.status)
            return False

        current_time = self._current_time()
        if current_time > proof.challenge_period_ends_at:
            proof.status = "expired"
            self.logger.warning(
                "Fraud proof %s expired before verification (deadline %s, now %s)",
                proof_id,
                proof.challenge_period_ends_at,
                current_time,
            )
            return False

        self.logger.info(
            "Verifying fraud proof %s submitted by %s against %s",
            proof_id,
            proof.challenger_address,
            proof.challenged_validator_address,
        )
        # Simplified verification logic: assume proof is valid if it contains "invalid_state"
        # In a real system, this would be a cryptographic verification.
        is_valid = "invalid_state" in proof.proof_data.get(
            "type", ""
        ) or "incorrect_signature" in proof.proof_data.get("type", "")

        if is_valid:
            proof.status = "verified"
            self.logger.info(
                "Fraud proof %s verified. Slashing validator %s",
                proof_id,
                proof.challenged_validator_address,
            )
            self.slashing_manager.report_malicious_behavior(
                proof.challenged_validator_address,
                "fraud_proven",  # A new offense type for fraud
                evidence=proof.proof_data,
            )
            # Optionally reward challenger here
            return True
        else:
            proof.status = "rejected"
            self.logger.warning("Fraud proof %s rejected: insufficient evidence", proof_id)
            return False

    def _current_time(self) -> int:
        return int(self._time_provider())
