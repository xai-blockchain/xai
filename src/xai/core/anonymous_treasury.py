from __future__ import annotations

"""
XAI Anonymous Treasury System

Manages development fund from token burns with complete anonymity.

ANONYMITY PROTECTIONS:
- Treasury wallet is publicly known but controlled anonymously
- All transactions use UTC timestamps only
- No personal identifiers anywhere
- Spending proposals are anonymous
- Vote records show wallet addresses only
- No IP addresses or geographic data
- No session tracking
"""

import json
import os
from datetime import datetime, timezone
from enum import Enum


class SpendingCategory(Enum):
    """Categories for treasury spending (public, anonymous)"""

    DEVELOPMENT = "development"
    MARKETING = "marketing"
    SECURITY_AUDIT = "security_audit"
    INFRASTRUCTURE = "infrastructure"
    COMMUNITY_REWARDS = "community_rewards"
    PARTNERSHIPS = "partnerships"
    LEGAL_COMPLIANCE = "legal_compliance"
    RESEARCH = "research"
    BOUNTIES = "bounties"

class TreasuryTransaction:
    """
    Anonymous treasury transaction

    Contains ONLY:
    - Transaction ID (generated hash)
    - Category
    - Amount
    - UTC timestamp
    - Purpose (text description, no identifiers)

    NO personal data!
    """

    def __init__(
        self,
        category: SpendingCategory,
        amount: float,
        purpose: str,
        recipient_type: str = "anonymous",
    ):

        self.tx_id = self._generate_tx_id()
        self.category = category.value
        self.amount = amount
        self.purpose = purpose  # Generic description, no names!
        self.recipient_type = recipient_type  # "anonymous", "contract", "multisig"
        self.timestamp_utc = datetime.now(timezone.utc).timestamp()
        self.status = "pending"

    def _generate_tx_id(self) -> str:
        """Generate anonymous transaction ID"""
        import hashlib
        import secrets

        random_data = secrets.token_hex(16)
        timestamp = str(datetime.now(timezone.utc).timestamp())
        data = f"{random_data}{timestamp}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def to_dict(self) -> dict:
        """Convert to anonymous dictionary (UTC only!)"""
        return {
            "tx_id": self.tx_id,
            "category": self.category,
            "amount": self.amount,
            "purpose": self.purpose,
            "recipient_type": self.recipient_type,
            "timestamp_utc": self.timestamp_utc,
            "date_utc": datetime.fromtimestamp(self.timestamp_utc, tz=timezone.utc).strftime(
                "%Y-%m-%d %H:%M:%S UTC"
            ),
            "status": self.status,
        }

class AnonymousTreasury:
    """
    Anonymous Treasury Management

    Receives 20% of all token burns for development.
    Spending is transparent but anonymous.

    ANONYMITY FEATURES:
    - All transactions use UTC timestamps
    - No personal identifiers
    - Wallet addresses only
    - Public spending but anonymous recipients
    - Vote records are anonymous
    """

    def __init__(self, data_dir=None):
        if data_dir is None:
            data_dir = os.path.dirname(os.path.dirname(__file__))

        self.data_dir = data_dir

        # Treasury address (publicly known, anonymously controlled)
        self.treasury_address = "XAITREASURY_ANONYMOUS_DEVELOPMENT_FUND"

        # Anonymous files
        self.transactions_file = os.path.join(data_dir, "treasury_transactions.json")
        self.balance_file = os.path.join(data_dir, "treasury_balance.json")
        self.stats_file = os.path.join(data_dir, "treasury_statistics.json")

        self._load_data()

    def _load_data(self):
        """Load anonymous treasury data"""

        # Transactions (anonymous, UTC only)
        if os.path.exists(self.transactions_file):
            with open(self.transactions_file, "r") as f:
                self.transactions = json.load(f)
        else:
            self.transactions = []

        # Balance
        if os.path.exists(self.balance_file):
            with open(self.balance_file, "r") as f:
                self.balance_data = json.load(f)
        else:
            self.balance_data = {
                "current_balance": 0.0,
                "total_received": 0.0,
                "total_spent": 0.0,
                "last_updated_utc": datetime.now(timezone.utc).timestamp(),
            }

        # Statistics (anonymous aggregation)
        if os.path.exists(self.stats_file):
            with open(self.stats_file, "r") as f:
                self.stats = json.load(f)
        else:
            self.stats = {
                "spending_by_category": {},
                "transaction_count": 0,
                "last_updated_utc": datetime.now(timezone.utc).timestamp(),
            }

    def _save_transactions(self):
        """Save anonymous transactions (UTC only)"""
        with open(self.transactions_file, "w") as f:
            json.dump(self.transactions, f, indent=2)

    def _save_balance(self):
        """Save balance (anonymous, UTC timestamp)"""
        self.balance_data["last_updated_utc"] = datetime.now(timezone.utc).timestamp()
        with open(self.balance_file, "w") as f:
            json.dump(self.balance_data, f, indent=2)

    def _save_stats(self):
        """Save anonymous statistics (UTC only)"""
        self.stats["last_updated_utc"] = datetime.now(timezone.utc).timestamp()
        with open(self.stats_file, "w") as f:
            json.dump(self.stats, f, indent=2)

    def receive_burn_distribution(self, amount: float):
        """
        Receive XAI from token burns (20% allocation)

        Anonymous receipt - only amount and UTC timestamp tracked
        """
        self.balance_data["current_balance"] += amount
        self.balance_data["total_received"] += amount
        self._save_balance()

        print(f"[Treasury] Received {amount} XAI from burn distribution")

    def propose_spending(
        self,
        category: SpendingCategory,
        amount: float,
        purpose: str,
        recipient_type: str = "anonymous",
    ) -> dict:
        """
        Propose treasury spending (anonymous)

        Args:
            category: Spending category
            amount: XAI amount
            purpose: Generic description (NO personal identifiers!)
            recipient_type: "anonymous", "contract", "multisig" (NO names!)

        Returns:
            Proposal details (anonymous)
        """

        if amount > self.balance_data["current_balance"]:
            return {
                "success": False,
                "error": f'Insufficient treasury balance. Available: {self.balance_data["current_balance"]} XAI',
            }

        # Create anonymous transaction
        tx = TreasuryTransaction(
            category=category, amount=amount, purpose=purpose, recipient_type=recipient_type
        )

        self.transactions.append(tx.to_dict())
        self._save_transactions()

        return {
            "success": True,
            "tx_id": tx.tx_id,
            "category": category.value,
            "amount": amount,
            "status": "pending",
            "message": "Treasury spending proposal created (anonymous)",
            "timestamp_utc": tx.timestamp_utc,
        }

    def execute_spending(self, tx_id: str) -> dict:
        """
        Execute approved spending (anonymous)

        Args:
            tx_id: Transaction ID

        Returns:
            Execution result (anonymous, UTC only)
        """

        # Find transaction
        tx = next((t for t in self.transactions if t["tx_id"] == tx_id), None)

        if not tx:
            return {"success": False, "error": "Transaction not found"}

        if tx["status"] != "pending":
            return {"success": False, "error": f'Transaction already {tx["status"]}'}

        amount = tx["amount"]

        if amount > self.balance_data["current_balance"]:
            return {"success": False, "error": "Insufficient treasury balance"}

        # Execute (deduct from treasury)
        self.balance_data["current_balance"] -= amount
        self.balance_data["total_spent"] += amount
        self._save_balance()

        # Update transaction status
        tx["status"] = "executed"
        tx["executed_utc"] = datetime.now(timezone.utc).timestamp()
        self._save_transactions()

        # Update anonymous statistics
        category = tx["category"]
        if category not in self.stats["spending_by_category"]:
            self.stats["spending_by_category"][category] = {"count": 0, "total_spent": 0.0}

        self.stats["spending_by_category"][category]["count"] += 1
        self.stats["spending_by_category"][category]["total_spent"] += amount
        self.stats["transaction_count"] += 1
        self._save_stats()

        return {
            "success": True,
            "tx_id": tx_id,
            "amount": amount,
            "category": category,
            "status": "executed",
            "message": "Treasury spending executed (anonymous)",
            "timestamp_utc": tx["executed_utc"],
        }

    def get_balance(self) -> dict:
        """Get current treasury balance (anonymous)"""
        return {
            "treasury_address": self.treasury_address,
            "current_balance": self.balance_data["current_balance"],
            "total_received": self.balance_data["total_received"],
            "total_spent": self.balance_data["total_spent"],
            "last_updated_utc": self.balance_data["last_updated_utc"],
            "last_updated_date_utc": datetime.fromtimestamp(
                self.balance_data["last_updated_utc"], tz=timezone.utc
            ).strftime("%Y-%m-%d %H:%M:%S UTC"),
        }

    def get_anonymous_stats(self) -> dict:
        """
        Get anonymous treasury statistics

        Returns aggregated spending data - NO personal information!
        """
        return {
            "spending_by_category": self.stats["spending_by_category"],
            "transaction_count": self.stats["transaction_count"],
            "total_received": self.balance_data["total_received"],
            "total_spent": self.balance_data["total_spent"],
            "current_balance": self.balance_data["current_balance"],
            "last_updated_utc": self.stats["last_updated_utc"],
            "last_updated_date_utc": datetime.fromtimestamp(
                self.stats["last_updated_utc"], tz=timezone.utc
            ).strftime("%Y-%m-%d %H:%M:%S UTC"),
        }

    def get_recent_transactions(self, limit: int = 50) -> list[dict]:
        """
        Get recent anonymous treasury transactions

        Returns transactions with:
        - Transaction ID (hash)
        - Category
        - Amount
        - UTC timestamp
        - Status

        NO personal identifiers!
        """
        return self.transactions[-limit:]

    def get_spending_by_category(self, category: SpendingCategory) -> dict:
        """Get anonymous spending statistics for category"""
        category_key = category.value

        if category_key in self.stats["spending_by_category"]:
            return self.stats["spending_by_category"][category_key]
        else:
            return {"count": 0, "total_spent": 0.0}
