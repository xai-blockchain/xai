from typing import Dict, Any
from src.aixn.blockchain.bridge_fees_insurance import BridgeFeeManager
from datetime import datetime, timezone


class InsuranceFundManager:
    def __init__(self, bridge_fee_manager: BridgeFeeManager, authorized_payout_address: str):
        if not isinstance(bridge_fee_manager, BridgeFeeManager):
            raise ValueError("bridge_fee_manager must be an instance of BridgeFeeManager.")
        if not authorized_payout_address:
            raise ValueError("Authorized payout address cannot be empty.")

        self.bridge_fee_manager = bridge_fee_manager
        self.authorized_payout_address = authorized_payout_address
        self.claims: Dict[str, Dict[str, Any]] = {}  # Stores pending/approved claims
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
        print(
            f"Claim {claim_id} submitted by {user_address} for {amount_claimed:.4f}. Status: pending."
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
        print(f"Claim {claim_id} approved by {approver_address}.")

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
        if self.fund_balance < amount_to_pay:
            print(
                f"Warning: Insurance fund balance ({self.fund_balance:.4f}) is insufficient to cover claim {claim_id} ({amount_to_pay:.4f})."
            )
            # In a real system, this might trigger a partial payout or a governance decision.
            amount_to_pay = self.fund_balance  # Pay out what's available

        self.bridge_fee_manager.insurance_fund_balance -= amount_to_pay  # Deduct from fund
        claim["status"] = "paid"
        print(
            f"Payout of {amount_to_pay:.4f} processed for claim {claim_id} to {claim['user_address']}. "
            f"Remaining fund balance: {self.fund_balance:.4f}."
        )

    def get_claim_status(self, claim_id: str) -> str:
        claim = self.claims.get(claim_id)
        return claim["status"] if claim else "not_found"


# Example Usage (for testing purposes)
if __name__ == "__main__":
    fee_manager = BridgeFeeManager(transfer_fee_percentage=0.001)  # 0.1% fee
    insurance_manager = InsuranceFundManager(
        fee_manager, authorized_payout_address="0xInsuranceDAO"
    )

    print("--- Initial State ---")
    print(f"Insurance Fund Balance: {insurance_manager.fund_balance:.4f}")

    print("\n--- Simulating Bridge Transfers to Fund Insurance ---")
    fee_manager.collect_fee(100000.0)  # Fund with 100 units
    fee_manager.collect_fee(50000.0)  # Fund with 50 units
    print(f"Insurance Fund Balance after funding: {insurance_manager.fund_balance:.4f}")

    print("\n--- Submitting Claims ---")
    claim1_id = insurance_manager.submit_claim(
        "0xVictim1", 75.0, "Lost 75 tokens due to bridge exploit in Block 123."
    )
    claim2_id = insurance_manager.submit_claim(
        "0xVictim2", 100.0, "Lost 100 tokens due to bridge exploit in Block 124."
    )
    claim3_id = insurance_manager.submit_claim(
        "0xVictim3", 200.0, "Lost 200 tokens due to bridge exploit in Block 125."
    )

    print("\n--- Approving and Processing Claims ---")
    try:
        insurance_manager.process_payout(claim1_id, "0xUnauthorized")  # Unauthorized payout attempt
    except PermissionError as e:
        print(f"Error (expected): {e}")

    insurance_manager.approve_claim(claim1_id, "0xInsuranceDAO")
    insurance_manager.process_payout(claim1_id, "0xInsuranceDAO")
    print(f"Insurance Fund Balance after claim 1 payout: {insurance_manager.fund_balance:.4f}")

    insurance_manager.approve_claim(claim2_id, "0xInsuranceDAO")
    insurance_manager.process_payout(claim2_id, "0xInsuranceDAO")
    print(f"Insurance Fund Balance after claim 2 payout: {insurance_manager.fund_balance:.4f}")

    print("\n--- Attempting to process a claim that exceeds fund ---")
    insurance_manager.approve_claim(claim3_id, "0xInsuranceDAO")
    insurance_manager.process_payout(claim3_id, "0xInsuranceDAO")
    print(f"Insurance Fund Balance after claim 3 payout: {insurance_manager.fund_balance:.4f}")

    print("\n--- Final Claim Statuses ---")
    print(f"Claim 1 status: {insurance_manager.get_claim_status(claim1_id)}")
    print(f"Claim 2 status: {insurance_manager.get_claim_status(claim2_id)}")
    print(f"Claim 3 status: {insurance_manager.get_claim_status(claim3_id)}")
