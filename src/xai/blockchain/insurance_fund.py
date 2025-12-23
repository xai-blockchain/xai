from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from .bridge_fees_insurance import BridgeFeeManager

logger = logging.getLogger("xai.blockchain.insurance_fund")

class InsuranceFundManager:
    def __init__(self, bridge_fee_manager: BridgeFeeManager, authorized_payout_address: str):
        if not isinstance(bridge_fee_manager, BridgeFeeManager):
            raise ValueError("bridge_fee_manager must be an instance of BridgeFeeManager.")
        if not authorized_payout_address:
            raise ValueError("Authorized payout address cannot be empty.")

        self.bridge_fee_manager = bridge_fee_manager
        self.authorized_payout_address = authorized_payout_address
        self.claims: dict[str, dict[str, Any]] = {}  # Stores pending/approved claims
        self._claim_counter = 0

    @property
    def fund_balance(self) -> float:
        return self.bridge_fee_manager.get_insurance_fund_balance()

    def submit_claim(self, user_address: str, amount_claimed: float, description: str) -> str:
        """
        Simulates a user submitting a claim for losses due to a bridge exploit.
        In a real system, this would involve detailed evidence and a formal review process.
        """
        if not user_address or not description:
            raise ValueError("User address and description cannot be empty.")
        if not isinstance(amount_claimed, (int, float)) or amount_claimed <= 0:
            raise ValueError("Amount claimed must be a positive number.")

        self._claim_counter += 1
        claim_id = f"claim_{self._claim_counter}"
        self.claims[claim_id] = {
            "user_address": user_address,
            "amount_claimed": amount_claimed,
            "description": description,
            "status": "pending",  # pending, approved, rejected, paid
            "submission_timestamp": int(datetime.now(timezone.utc).timestamp()),
        }
        logger.info(
            "Claim %s submitted by %s for %.4f (pending)",
            claim_id,
            user_address,
            amount_claimed,
        )
        return claim_id

    def approve_claim(self, claim_id: str, approver_address: str):
        """
        Simulates approving a claim. In a real system, this would be a multi-sig or governance action.
        """
        claim = self.claims.get(claim_id)
        if not claim:
            raise ValueError(f"Claim {claim_id} not found.")
        if claim["status"] != "pending":
            raise ValueError(
                f"Claim {claim_id} is not in pending status (current: {claim['status']})."
            )

        # For simplicity, any authorized payout address can approve
        if approver_address != self.authorized_payout_address:
            raise PermissionError(
                f"Approver {approver_address} is not authorized to approve claims."
            )

        claim["status"] = "approved"
        logger.info("Claim %s approved by %s", claim_id, approver_address)

    def process_payout(self, claim_id: str, caller_address: str):
        """
        Simulates disbursing funds for an approved claim.
        """
        claim = self.claims.get(claim_id)
        if not claim:
            raise ValueError(f"Claim {claim_id} not found.")
        if claim["status"] != "approved":
            raise ValueError(
                f"Claim {claim_id} is not in approved status (current: {claim['status']})."
            )

        if caller_address != self.authorized_payout_address:
            raise PermissionError(f"Caller {caller_address} is not authorized to process payouts.")

        amount_to_pay = claim["amount_claimed"]
        balance = self.fund_balance
        if balance < amount_to_pay:
            logger.warning(
                "Insurance fund balance %.4f insufficient to cover claim %s (%.4f). Paying remaining balance.",
                balance,
                claim_id,
                amount_to_pay,
            )
            amount_to_pay = balance  # Pay out what's available

        self.bridge_fee_manager.insurance_fund_balance -= amount_to_pay
        claim["status"] = "paid"
        logger.info(
            "Payout %.4f processed for claim %s to %s (remaining balance %.4f)",
            amount_to_pay,
            claim_id,
            claim["user_address"],
            self.fund_balance,
        )

    def get_claim_status(self, claim_id: str) -> str:
        claim = self.claims.get(claim_id)
        return claim["status"] if claim else "not_found"

