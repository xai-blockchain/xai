"""
XAI Wallet Claim System

Auto-assigns pre-generated wallets to early adopters:
- TIER 1: Premium wallets (requires mining 1 block)
- TIER 2: Standard wallets (instant on node start)
"""

import json
import os
import time
import hashlib
from aixn.core.wallet import Wallet


class WalletClaimSystem:
    """Manages automatic wallet distribution to early adopters"""

    def __init__(self, data_dir=None):
        if data_dir is None:
            data_dir = os.path.dirname(os.path.dirname(__file__))

        self.data_dir = data_dir
        self.premium_wallets = []
        self.bonus_wallets = []
        self.standard_wallets = []
        self.micro_wallets = []
        self.claims_file = os.path.join(data_dir, "wallet_claims.json")
        self.claims = {}

        self._load_wallets()
        self._load_claims()

    def _load_wallets(self):
        """Load unclaimed wallets"""

        # Load premium wallets (miner tier only)
        premium_file = os.path.join(self.data_dir, "premium_wallets_PRIVATE.json")
        if os.path.exists(premium_file):
            with open(premium_file, "r") as f:
                all_premium = json.load(f)
                # Only miner tier (1,150 wallets)
            self.premium_wallets = [w for w in all_premium if w["tier"] == "miner"]

        # Load bonus wallets (early miner bonuses)
        bonus_file = os.path.join(self.data_dir, "bonus_wallets_PRIVATE.json")
        if os.path.exists(bonus_file):
            with open(bonus_file, "r") as f:
                self.bonus_wallets = json.load(f)

        # Load standard wallets
        standard_file = os.path.join(self.data_dir, "standard_wallets_PRIVATE.json")
        if os.path.exists(standard_file):
            with open(standard_file, "r") as f:
                self.standard_wallets = json.load(f)

        # Load micro wallets
        micro_file = os.path.join(self.data_dir, "micro_wallets_PRIVATE.json")
        if os.path.exists(micro_file):
            with open(micro_file, "r") as f:
                self.micro_wallets = json.load(f)

        print(f"Wallet Claim System initialized:")
        print(
            f"  Premium wallets available: {len([w for w in self.premium_wallets if not w['claimed']])}"
        )
        print(
            f"  Standard wallets available: {len([w for w in self.standard_wallets if not w['claimed']])}"
        )
        print(
            f"  Micro wallets available: {len([w for w in self.micro_wallets if not w.get('claimed', False)])}"
        )

    def _load_claims(self):
        """Load existing claims"""
        if os.path.exists(self.claims_file):
            with open(self.claims_file, "r") as f:
                self.claims = json.load(f)
        else:
            self.claims = {
                "premium_claims": [],
                "bonus_claims": [],
                "standard_claims": [],
                "micro_claims": [],
                "total_claimed": 0,
            }

    def _save_claims(self):
        """Save claims to disk"""
        with open(self.claims_file, "w") as f:
            json.dump(self.claims, f, indent=2)

    def _next_unclaimed_wallet(self, wallets):
        return next((w for w in wallets if not w.get("claimed")), None)

    def _finalize_claim(self, node_id: str, wallet: dict, tier: str, proof: str = None) -> dict:
        wallet["claimed"] = True
        wallet["claimed_by"] = node_id
        wallet["claimed_timestamp"] = time.time()

        claim_record = {
            "node_id": node_id,
            "address": wallet["address"],
            "tier": tier,
            "timestamp": time.time(),
            "proof": proof,
            "amount": wallet.get("amount", wallet.get("initial_balance")),
            "metadata": wallet.get("metadata", {}),
        }

        self.claims[f"{tier}_claims"].append(claim_record)
        self.claims["total_claimed"] += 1

        self._update_wallet_file(tier)

        response = {
            "success": True,
            "tier": tier,
            "wallet": wallet,
            "message": f'{tier.capitalize()} wallet claimed! Balance: {claim_record["amount"]} XAI',
            f"remaining_{tier}": len(
                [w for w in getattr(self, f"{tier}_wallets") if not w.get("claimed")]
            ),
        }
        return response

    def _empty_wallet_response(self, tier: str) -> dict:
        return {
            "success": True,
            "tier": "empty",
            "wallet": None,
            "message": f"No {tier} wallets remain; an empty wallet has been reserved.",
        }

    def _claim_wallet_sequence(self, node_id: str, sequence: list, proof: str = None) -> dict:
        for tier, wallets in sequence:
            wallet = self._next_unclaimed_wallet(wallets)
            if wallet:
                return self._finalize_claim(node_id, wallet, tier, proof)
        return self._empty_wallet_response(sequence[-1][0])

    def claim_premium_wallet(self, node_id: str, proof_of_mining: str = None) -> dict:
        """
        Claim premium wallet (auto-assigned to node operators)

        Args:
            node_id: Unique identifier for this node
            proof_of_mining: Optional - if provided, verifies mining proof

        Returns:
            dict with wallet data or error
        """

        # Check if node already claimed
        existing_claim = next(
            (c for c in self.claims["premium_claims"] if c["node_id"] == node_id), None
        )
        if existing_claim:
            wallet = next(
                (w for w in self.premium_wallets if w["address"] == existing_claim["address"]), None
            )
            return {
                "success": True,
                "tier": "premium",
                "wallet": wallet,
                "message": "Premium wallet already claimed.",
            }

        if proof_of_mining and not self._verify_proof_of_mining(proof_of_mining):
            proof_of_mining = None

        unclaimed = self._next_unclaimed_wallet(self.premium_wallets)
        if not unclaimed:
            return self._empty_wallet_response("premium")

        return self._finalize_claim(node_id, unclaimed, "premium", proof_of_mining)

    def claim_standard_wallet(self, node_id: str) -> dict:
        # Claim standard wallet (instant, no mining required)
        existing_claim = next(
            (c for c in self.claims["standard_claims"] if c["node_id"] == node_id), None
        )
        if existing_claim:
            wallet = next(
                (w for w in self.standard_wallets if w["address"] == existing_claim["address"]),
                None,
            )
            return {
                "success": True,
                "tier": "standard",
                "wallet": wallet,
                "message": "Standard wallet already claimed.",
            }

        return self._claim_wallet_sequence(
            node_id, [("standard", self.standard_wallets), ("micro", self.micro_wallets)]
        )

    def claim_bonus_wallet(self, miner_id: str, proof_of_mining: Optional[str] = None) -> dict:
        # Claim bonus wallet for early adopter miners
        existing_claim = next(
            (c for c in self.claims["bonus_claims"] if c["node_id"] == miner_id), None
        )
        if existing_claim:
            wallet = next(
                (w for w in self.bonus_wallets if w["address"] == existing_claim["address"]), None
            )
            return {
                "success": True,
                "tier": "bonus",
                "wallet": wallet,
                "message": "Bonus wallet already claimed.",
            }

        if proof_of_mining and not self._verify_proof_of_mining(proof_of_mining):
            proof_of_mining = None

        return self._claim_wallet_sequence(
            miner_id,
            [
                ("bonus", self.bonus_wallets),
                ("standard", self.standard_wallets),
                ("micro", self.micro_wallets),
            ],
            proof=proof_of_mining,
        )

    def claim_micro_wallet(self, node_id: str) -> dict:
        """
        Claim micro wallet (after standard wallets exhausted)

        Args:
            node_id: Unique identifier for this node

        Returns:
            dict with wallet data or error
        """

        existing_claim = next(
            (c for c in self.claims.get("micro_claims", []) if c["node_id"] == node_id), None
        )
        if existing_claim:
            wallet = next(
                (w for w in self.micro_wallets if w["address"] == existing_claim["address"]), None
            )
            return {
                "success": True,
                "tier": "micro",
                "wallet": wallet,
                "message": "Micro wallet already claimed.",
            }

        return self._claim_wallet_sequence(node_id, [("micro", self.micro_wallets)])

    def _verify_proof_of_mining(self, proof: str) -> bool:
        """
        Verify proof of mining (block hash)

        In production, this would verify:
        - Hash format is valid
        - Hash meets difficulty requirement
        - Block exists in pending chain

        For now, just verify it's a valid hex hash
        """
        if not proof or len(proof) != 64:
            return False

        try:
            int(proof, 16)
            return True
        except ValueError:
            return False

    def _update_wallet_file(self, tier: str):
        """Update wallet file with claim status"""
        if tier == "premium":
            wallet_file = os.path.join(self.data_dir, "premium_wallets_PRIVATE.json")
            # Reload all premium wallets (not just miner tier)
            with open(wallet_file, "r") as f:
                all_premium = json.load(f)

            # Update miner tier wallets
            for wallet in all_premium:
                if wallet["tier"] == "miner":
                    updated = next(
                        (w for w in self.premium_wallets if w["address"] == wallet["address"]), None
                    )
                    if updated:
                        wallet.update(updated)

            with open(wallet_file, "w") as f:
                json.dump(all_premium, f, indent=2)

        elif tier == "standard":
            wallet_file = os.path.join(self.data_dir, "standard_wallets_PRIVATE.json")
            with open(wallet_file, "w") as f:
                json.dump(self.standard_wallets, f, indent=2)

        elif tier == "micro":
            wallet_file = os.path.join(self.data_dir, "micro_wallets_PRIVATE.json")
            with open(wallet_file, "w") as f:
                json.dump(self.micro_wallets, f, indent=2)
        elif tier == "bonus":
            wallet_file = os.path.join(self.data_dir, "bonus_wallets_PRIVATE.json")
            with open(wallet_file, "w") as f:
                json.dump(self.bonus_wallets, f, indent=2)

    def get_node_wallet(self, node_id: str) -> dict:
        """Get wallet for a node if already claimed"""
        premium_claim = next(
            (c for c in self.claims["premium_claims"] if c["node_id"] == node_id), None
        )
        if premium_claim:
            wallet = next(
                (w for w in self.premium_wallets if w["address"] == premium_claim["address"]), None
            )
            return {"tier": "premium", "wallet": wallet}

        standard_claim = next(
            (c for c in self.claims["standard_claims"] if c["node_id"] == node_id), None
        )
        if standard_claim:
            wallet = next(
                (w for w in self.standard_wallets if w["address"] == standard_claim["address"]),
                None,
            )
            return {"tier": "standard", "wallet": wallet}

        return None

    def get_stats(self) -> dict:
        """Get claim statistics"""
        premium_unclaimed = len([w for w in self.premium_wallets if not w["claimed"]])
        standard_unclaimed = len([w for w in self.standard_wallets if not w["claimed"]])

        total_premium_value = sum(
            w["total_balance"] for w in self.premium_wallets if not w["claimed"]
        )
        total_standard_value = sum(
            w["initial_balance"] for w in self.standard_wallets if not w["claimed"]
        )

        return {
            "premium": {
                "total": len(self.premium_wallets),
                "claimed": len(self.premium_wallets) - premium_unclaimed,
                "unclaimed": premium_unclaimed,
                "total_unclaimed_value": total_premium_value,
            },
            "standard": {
                "total": len(self.standard_wallets),
                "claimed": len(self.standard_wallets) - standard_unclaimed,
                "unclaimed": standard_unclaimed,
                "total_unclaimed_value": total_standard_value,
            },
            "total_claims": self.claims["total_claimed"],
        }

    def _generate_time_capsule_offer_message(self, wallet_data: dict) -> str:
        """Generate time capsule offer message for eligible wallet"""

        current_balance = wallet_data.get("initial_balance", 50)
        bonus = wallet_data.get("time_capsule_bonus", 450)
        total = current_balance + bonus

        message = f"""
╔══════════════════════════════════════════════════════════════════╗
║              TIME CAPSULE PROTOCOL OFFER                         ║
╚══════════════════════════════════════════════════════════════════╝

You have been randomly selected for the Time Capsule Protocol!

SPECIAL OFFER:
  Turn your {current_balance} XAI into {total} XAI!

  Current Balance:  {current_balance} XAI
  Bonus:           +{bonus} XAI
  Total Locked:     {total} XAI

TERMS:
  - Lock {total} XAI on the blockchain for 1 year
  - Receive new empty wallet immediately to use
  - Claim {total} XAI after 1 year

This demonstrates XAI's time-locking capability.

Would you like to accept this offer?
"""
        return message


def generate_node_id():
    """Generate unique node ID based on machine characteristics"""
    import platform
    import uuid

    # Combine multiple factors for unique ID
    machine_id = f"{platform.node()}-{uuid.getnode()}-{int(time.time())}"
    return hashlib.sha256(machine_id.encode()).hexdigest()[:32]
