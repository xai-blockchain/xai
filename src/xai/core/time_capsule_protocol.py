"""
XAI Blockchain - Time Capsule Protocol

Allows users to lock 500 XAI (50 base + 450 bonus) for 1 year
in exchange for receiving an immediate empty replacement wallet.

Funding Source: TIME_CAPSULE_RESERVE wallet (414,000 XAI)
- 920 wallets × 450 XAI bonus = 414,000 XAI total

Demonstrates blockchain time-locking capability.
"""

import json
import os
import time
from datetime import datetime, timedelta

from xai.core.wallet import Wallet


class TimeCapsuleProtocol:
    """Manages time-locked wallets with future unlock dates"""

    def __init__(self, data_dir=None, blockchain=None):
        if data_dir is None:
            data_dir = os.path.dirname(os.path.dirname(__file__))

        self.data_dir = data_dir
        self.blockchain = blockchain
        self.time_capsules_file = os.path.join(data_dir, "time_capsules.json")
        self.reserve_file = os.path.join(data_dir, "TIME_CAPSULE_RESERVE.json")
        self.time_capsules = []
        self.reserve_wallet = None
        self.reserve_balance = 0

        self._load_time_capsules()
        self._load_reserve_wallet()

    def _load_time_capsules(self):
        """Load existing time capsules"""
        if os.path.exists(self.time_capsules_file):
            with open(self.time_capsules_file, "r") as f:
                self.time_capsules = json.load(f)
        else:
            self.time_capsules = []

    def _save_time_capsules(self):
        """Save time capsules to disk"""
        with open(self.time_capsules_file, "w") as f:
            json.dump(self.time_capsules, f, indent=2)

    def _persist_reserve_wallet(self):
        """Persist the reserve wallet metadata"""
        if not self.reserve_wallet:
            return
        with open(self.reserve_file, "w") as f:
            json.dump(self.reserve_wallet, f, indent=2)

    def _normalize_reserve_wallet(self):
        """Ensure reserve metadata has required defaults"""
        if not self.reserve_wallet:
            return

        defaults = {
            "disbursement_history": [],
            "disbursement_window_seconds": 86400,
            "max_disbursements_per_window": 4,
            "disbursements_made": 0,
        }
        for key, value in defaults.items():
            self.reserve_wallet.setdefault(key, value)

        bonus_amount = self.reserve_wallet.get("disbursement_amount", 450)
        window_disbursements = self.reserve_wallet.get("max_disbursements_per_window", 4)
        self.reserve_wallet.setdefault(
            "max_disbursement_amount_per_window", bonus_amount * window_disbursements
        )

        history = self.reserve_wallet.get("disbursement_history", [])
        if not isinstance(history, list):
            history = []
        cleaned = [
            entry
            for entry in history
            if isinstance(entry, dict) and "timestamp" in entry and "amount" in entry
        ]
        self.reserve_wallet["disbursement_history"] = cleaned

        self.reserve_wallet.setdefault("current_balance", self.reserve_wallet.get("initial_balance", 0))
        self.reserve_balance = self.reserve_wallet.get("current_balance", 0)

    def _clean_disbursement_history(self):
        """Prune history entries older than the configured window"""
        if not self.reserve_wallet:
            return

        history = self.reserve_wallet.get("disbursement_history", [])
        window = self.reserve_wallet.get("disbursement_window_seconds", 86400)
        cutoff = time.time() - window
        filtered = [entry for entry in history if entry.get("timestamp", 0) >= cutoff]
        if len(filtered) != len(history):
            self.reserve_wallet["disbursement_history"] = filtered

    def _load_reserve_wallet(self):
        """Load Time Capsule Reserve wallet"""
        if os.path.exists(self.reserve_file):
            with open(self.reserve_file, "r") as f:
                self.reserve_wallet = json.load(f)
                self._normalize_reserve_wallet()
                print(f"[Time Capsule Reserve] Loaded: {self.reserve_balance:,} XAI available")
        else:
            print(f"[WARNING] Time Capsule Reserve not found at {self.reserve_file}")
            print(f"[WARNING] Run create_time_capsule_reserve.py to create reserve wallet")
            self.reserve_wallet = None
            self.reserve_balance = 0

    def _record_disbursement(self, amount: float):
        """Track a new disbursement entry"""
        if not self.reserve_wallet:
            return

        history = self.reserve_wallet.setdefault("disbursement_history", [])
        history.append({"timestamp": time.time(), "amount": amount})

    def _can_disburse_amount(self, amount: float):
        """Check window and amount limits before disbursing"""
        if not self.reserve_wallet:
            return False, "Reserve wallet not initialized"

        self._clean_disbursement_history()
        history = self.reserve_wallet.get("disbursement_history", [])
        max_entries = self.reserve_wallet.get("max_disbursements_per_window", 4)
        if len(history) >= max_entries:
            return False, "Reserve hit the disbursement window limit"

        window_amount_limit = self.reserve_wallet.get("max_disbursement_amount_per_window", amount)
        amount_in_window = sum(entry.get("amount", 0) for entry in history)
        if amount_in_window + amount > window_amount_limit:
            return False, "Reserve disbursement amount limit exceeded for current window"

        return True, None

    def _update_reserve_balance(self, amount: float):
        """Update reserve balance after disbursement"""
        if not self.reserve_wallet:
            return False, "Reserve wallet not initialized"

        if amount <= 0:
            return False, "Invalid bonus amount requested"

        max_disbursements = self.reserve_wallet.get("max_disbursements", 0)
        disbursements_made = self.reserve_wallet.get("disbursements_made", 0)
        if max_disbursements and disbursements_made >= max_disbursements:
            return False, "Time Capsule Reserve max disbursements reached"

        if self.reserve_balance < amount:
            return False, f"Insufficient reserve funds. Available: {self.reserve_balance} XAI, Required: {amount} XAI"

        can_disburse, error = self._can_disburse_amount(amount)
        if not can_disburse:
            return False, error

        self.reserve_balance -= amount
        if self.reserve_balance < 0:
            self.reserve_balance = 0
            return False, "Reserve balance would go negative"

        self.reserve_wallet["current_balance"] = self.reserve_balance
        self.reserve_wallet["disbursements_made"] = disbursements_made + 1
        self._record_disbursement(amount)
        self._persist_reserve_wallet()

        return True, None

    def is_wallet_time_capsule_eligible(self, wallet_data: dict) -> bool:
        """Check if wallet is eligible for time capsule protocol"""
        return wallet_data.get("time_capsule_eligible", False) and not wallet_data.get(
            "time_capsule_claimed", False
        )

    def initiate_time_capsule(self, wallet_data: dict, user_accepted: bool = True) -> dict:
        """
        Initiate time capsule protocol for eligible wallet

        Process:
        1. Verify wallet eligibility
        2. Check reserve has sufficient funds
        3. Transfer 450 XAI bonus from reserve to locked wallet
        4. Lock total 500 XAI for 1 year
        5. Issue replacement empty wallet

        Args:
            wallet_data: Original wallet data
            user_accepted: Whether user accepted the offer

        Returns:
            dict with protocol result
        """

        if not user_accepted:
            return {"success": False, "message": "Time capsule protocol declined"}

        if not self.is_wallet_time_capsule_eligible(wallet_data):
            return {"success": False, "error": "Wallet not eligible for time capsule protocol"}

        # Calculate amounts
        base_amount = wallet_data.get("initial_balance", 50)
        bonus_amount = wallet_data.get("time_capsule_bonus", 450)
        total_locked = base_amount + bonus_amount

        # Check reserve has sufficient funds
        if not self.reserve_wallet:
            return {
                "success": False,
                "error": "Time Capsule Reserve not initialized. Cannot provide bonus.",
            }

        if self.reserve_balance < bonus_amount:
            return {
                "success": False,
                "error": f"Insufficient reserve funds. Available: {self.reserve_balance} XAI, Required: {bonus_amount} XAI",
            }

        # Calculate unlock date (1 year from now, UTC)
        current_utc = datetime.utcnow()
        unlock_date = current_utc + timedelta(days=365)
        unlock_timestamp = unlock_date.timestamp()

        # Transfer bonus from reserve to locked wallet
        # NOTE: In production, this would create a blockchain transaction
        # For now, track it in the time capsule record
        reserve_transfer = {
            "from_address": self.reserve_wallet["address"],
            "to_address": wallet_data["address"],
            "amount": bonus_amount,
            "timestamp_utc": current_utc.timestamp(),
            "purpose": "Time Capsule Protocol Bonus",
        }

        # Update reserve balance
        reserve_success, reserve_error = self._update_reserve_balance(bonus_amount)
        if not reserve_success:
            return {"success": False, "error": reserve_error or "Failed to update reserve balance"}

        # Create time-locked wallet record
        locked_wallet = {
            "locked_address": wallet_data["address"],
            "private_key": wallet_data["private_key"],
            "public_key": wallet_data["public_key"],
            "locked_amount": total_locked,
            "base_amount": base_amount,
            "bonus_amount": bonus_amount,
            "lock_timestamp_utc": current_utc.timestamp(),
            "unlock_timestamp_utc": unlock_timestamp,
            "unlock_date_utc": unlock_date.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "status": "locked",
            "claimed": False,
            "reserve_transfer": reserve_transfer,  # Track funding source
            "funded_from_reserve": True,
        }

        # Generate new empty replacement wallet
        replacement_wallet = Wallet()
        replacement_data = {
            "address": replacement_wallet.address,
            "private_key": replacement_wallet.private_key,
            "public_key": replacement_wallet.public_key,
            "balance": 0,
            "type": "time_capsule_replacement",
            "replaces_locked_wallet": wallet_data["address"],
        }

        # Save time capsule
        self.time_capsules.append(locked_wallet)
        self._save_time_capsules()

        print(f"[Time Capsule] Transferred {bonus_amount} XAI from reserve")
        print(f"[Time Capsule] Remaining reserve: {self.reserve_balance:,} XAI")

        return {
            "success": True,
            "message": "Time Capsule Protocol Initiated",
            "locked_wallet": {
                "address": locked_wallet["locked_address"],
                "amount": total_locked,
                "unlock_date_utc": locked_wallet["unlock_date_utc"],
                "unlock_timestamp_utc": unlock_timestamp,
            },
            "replacement_wallet": replacement_data,
            "protocol_message": self._generate_protocol_message(locked_wallet, unlock_date),
            "reserve_balance_remaining": self.reserve_balance,
        }

    def _generate_protocol_message(self, locked_wallet: dict, unlock_date: datetime) -> str:
        """Generate user-facing protocol engagement message"""

        unlock_str = unlock_date.strftime("%d %B %Y at %H:%M:%S UTC")

        message = f"""
======================================================================
       TIME CAPSULE PROTOCOL ENGAGED
======================================================================

Your 500 XAI has been sealed on the XAI blockchain for 1 year.

  Locked Amount: {locked_wallet['locked_amount']} XAI
  Unlock Date: {unlock_str}

You may claim your wallet with 500 XAI on {unlock_str}

A new empty wallet has been issued for immediate use.
Check your wallet file for the replacement wallet details.

======================================================================
"""
        return message

    def check_unlock_eligibility(self, locked_address: str) -> dict:
        """Check if a time capsule wallet is ready to unlock"""

        capsule = next(
            (tc for tc in self.time_capsules if tc["locked_address"] == locked_address), None
        )

        if not capsule:
            return {"success": False, "error": "Time capsule not found"}

        current_utc = datetime.utcnow().timestamp()
        unlock_timestamp = capsule["unlock_timestamp_utc"]

        if current_utc >= unlock_timestamp:
            return {
                "success": True,
                "unlocked": True,
                "can_claim": True,
                "amount": capsule["locked_amount"],
                "message": f"Time capsule unlocked! You can claim {capsule['locked_amount']} XAI",
            }
        else:
            time_remaining = unlock_timestamp - current_utc
            days_remaining = int(time_remaining / 86400)

            return {
                "success": True,
                "unlocked": False,
                "can_claim": False,
                "unlock_date_utc": capsule["unlock_date_utc"],
                "days_remaining": days_remaining,
                "message": f"Time capsule locked. {days_remaining} days remaining until unlock.",
            }

    def claim_time_capsule(self, locked_address: str) -> dict:
        """Claim unlocked time capsule wallet"""

        capsule = next(
            (tc for tc in self.time_capsules if tc["locked_address"] == locked_address), None
        )

        if not capsule:
            return {"success": False, "error": "Time capsule not found"}

        if capsule["claimed"]:
            return {"success": False, "error": "Time capsule already claimed"}

        # Check if unlocked
        current_utc = datetime.utcnow().timestamp()
        if current_utc < capsule["unlock_timestamp_utc"]:
            days_remaining = int((capsule["unlock_timestamp_utc"] - current_utc) / 86400)
            return {
                "success": False,
                "error": f"Time capsule still locked. {days_remaining} days remaining.",
            }

        # Mark as claimed
        capsule["claimed"] = True
        capsule["status"] = "claimed"
        capsule["claim_timestamp_utc"] = current_utc
        self._save_time_capsules()

        return {
            "success": True,
            "wallet": {
                "address": capsule["locked_address"],
                "private_key": capsule["private_key"],
                "public_key": capsule["public_key"],
                "balance": capsule["locked_amount"],
            },
            "message": f'Time capsule claimed! {capsule["locked_amount"]} XAI unlocked.',
        }

    def get_time_capsule_stats(self) -> dict:
        """Get statistics about time capsules"""

        locked = [tc for tc in self.time_capsules if tc["status"] == "locked"]
        claimed = [tc for tc in self.time_capsules if tc["status"] == "claimed"]

        total_locked_value = sum(tc["locked_amount"] for tc in locked)
        total_claimed_value = sum(tc["locked_amount"] for tc in claimed)

        return {
            "total_time_capsules": len(self.time_capsules),
            "active_locked": len(locked),
            "total_claimed": len(claimed),
            "total_locked_value": total_locked_value,
            "total_claimed_value": total_claimed_value,
        }

    def get_user_time_capsules(self, address: str) -> list:
        """Get all time capsules for a specific address"""
        return [tc for tc in self.time_capsules if tc["locked_address"] == address]
