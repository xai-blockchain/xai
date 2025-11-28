"""
Account abstraction helpers and embedded wallet management.
Task 178: Gas sponsorship for account abstraction
"""

import json
import os
import hashlib
import secrets
import time
from pathlib import Path
from typing import Dict, Optional, List
from dataclasses import dataclass, field

from xai.core.wallet import WalletManager
from xai.core.config import Config


@dataclass
class SponsoredTransaction:
    """Record of a sponsored transaction"""
    user_address: str
    txid: str
    gas_amount: float
    timestamp: float
    sponsor_address: str


class GasSponsor:
    """
    Gas sponsorship for account abstraction (Task 178)

    Allows sponsors to pay transaction fees on behalf of users,
    enabling gasless transactions for better UX.
    """

    def __init__(self, sponsor_address: str, budget: float, rate_limit: int = 10):
        """
        Initialize gas sponsor

        Args:
            sponsor_address: Address of the sponsor
            budget: Total budget for sponsorship
            rate_limit: Max transactions per user per day
        """
        self.sponsor_address = sponsor_address
        self.total_budget = budget
        self.remaining_budget = budget
        self.rate_limit = rate_limit
        self.sponsored_transactions: List[SponsoredTransaction] = []
        self.user_daily_usage: Dict[str, List[float]] = {}  # user -> timestamps
        self.whitelist: List[str] = []  # Whitelisted user addresses
        self.blacklist: List[str] = []  # Blacklisted user addresses
        self.min_balance_required = 0.0  # Minimum balance user must have
        self.max_gas_per_transaction = 0.1  # Maximum gas per transaction
        self.enabled = True

    def sponsor_transaction(self, user_address: str, gas_amount: float) -> bool:
        """
        Sponsor a transaction for a user

        Args:
            user_address: User address
            gas_amount: Amount of gas needed

        Returns:
            True if sponsorship approved
        """
        if not self.enabled:
            return False

        # Check blacklist
        if user_address in self.blacklist:
            return False

        # Check whitelist (if configured)
        if self.whitelist and user_address not in self.whitelist:
            return False

        # Check budget
        if gas_amount > self.remaining_budget:
            return False

        # Check per-transaction limit
        if gas_amount > self.max_gas_per_transaction:
            return False

        # Check rate limit
        if not self._check_rate_limit(user_address):
            return False

        # Approve sponsorship
        self.remaining_budget -= gas_amount

        # Record transaction (will be updated with txid later)
        tx = SponsoredTransaction(
            user_address=user_address,
            txid="pending",
            gas_amount=gas_amount,
            timestamp=time.time(),
            sponsor_address=self.sponsor_address
        )
        self.sponsored_transactions.append(tx)

        # Update user usage
        if user_address not in self.user_daily_usage:
            self.user_daily_usage[user_address] = []
        self.user_daily_usage[user_address].append(time.time())

        return True

    def _check_rate_limit(self, user_address: str) -> bool:
        """Check if user has exceeded rate limit"""
        if user_address not in self.user_daily_usage:
            return True

        # Clean up old entries (older than 24 hours)
        current_time = time.time()
        day_ago = current_time - 86400

        self.user_daily_usage[user_address] = [
            ts for ts in self.user_daily_usage[user_address]
            if ts > day_ago
        ]

        # Check count
        return len(self.user_daily_usage[user_address]) < self.rate_limit

    def add_budget(self, amount: float) -> None:
        """Add more budget to sponsor"""
        self.total_budget += amount
        self.remaining_budget += amount

    def set_whitelist(self, addresses: List[str]) -> None:
        """Set whitelist of allowed users"""
        self.whitelist = addresses

    def set_blacklist(self, addresses: List[str]) -> None:
        """Set blacklist of denied users"""
        self.blacklist = addresses

    def set_max_gas_per_transaction(self, amount: float) -> None:
        """Set maximum gas per transaction"""
        self.max_gas_per_transaction = amount

    def set_rate_limit(self, limit: int) -> None:
        """Set rate limit (transactions per user per day)"""
        self.rate_limit = limit

    def enable(self) -> None:
        """Enable sponsorship"""
        self.enabled = True

    def disable(self) -> None:
        """Disable sponsorship"""
        self.enabled = False

    def get_stats(self) -> Dict[str, any]:
        """Get sponsorship statistics"""
        total_sponsored = sum(tx.gas_amount for tx in self.sponsored_transactions)
        unique_users = len(set(tx.user_address for tx in self.sponsored_transactions))

        return {
            "sponsor_address": self.sponsor_address,
            "total_budget": self.total_budget,
            "remaining_budget": self.remaining_budget,
            "spent": total_sponsored,
            "transaction_count": len(self.sponsored_transactions),
            "unique_users": unique_users,
            "enabled": self.enabled,
            "rate_limit": self.rate_limit
        }

    def get_user_usage(self, user_address: str) -> Dict[str, any]:
        """Get usage stats for a specific user"""
        user_txs = [
            tx for tx in self.sponsored_transactions
            if tx.user_address == user_address
        ]

        total_gas = sum(tx.gas_amount for tx in user_txs)

        # Count today's transactions
        current_time = time.time()
        day_ago = current_time - 86400
        today_count = len([
            ts for ts in self.user_daily_usage.get(user_address, [])
            if ts > day_ago
        ])

        return {
            "user_address": user_address,
            "total_transactions": len(user_txs),
            "total_gas_sponsored": total_gas,
            "transactions_today": today_count,
            "rate_limit_remaining": max(0, self.rate_limit - today_count)
        }


class EmbeddedWalletRecord:
    def __init__(self, alias: str, contact: str, wallet_name: str, address: str, secret_hash: str):
        self.alias = alias
        self.contact = contact
        self.wallet_name = wallet_name
        self.address = address
        self.secret_hash = secret_hash

    def to_dict(self) -> Dict[str, str]:
        return {
            "alias": self.alias,
            "contact": self.contact,
            "wallet_name": self.wallet_name,
            "address": self.address,
            "secret_hash": self.secret_hash,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> "EmbeddedWalletRecord":
        return cls(
            alias=data["alias"],
            contact=data["contact"],
            wallet_name=data["wallet_name"],
            address=data["address"],
            secret_hash=data["secret_hash"],
        )


class AccountAbstractionManager:
    """Manage embedded wallets that map to social/email identities."""

    def __init__(self, wallet_manager: WalletManager, storage_path: Optional[str] = None):
        self.wallet_manager = wallet_manager
        self.storage_path = storage_path or Config.EMBEDDED_WALLET_DIR
        os.makedirs(self.storage_path, exist_ok=True)
        self.records_file = os.path.join(self.storage_path, "embedded_wallets.json")
        self.records: Dict[str, EmbeddedWalletRecord] = {}
        self.sessions: Dict[str, str] = {}
        self.gas_sponsors: Dict[str, 'GasSponsor'] = {}  # Task 178: Gas sponsorship
        self._load()

    def _hash_secret(self, secret: str) -> str:
        salted = f"{secret}{Config.EMBEDDED_WALLET_SALT}"
        return hashlib.sha256(salted.encode()).hexdigest()

    def _wallet_filename(self, alias: str) -> str:
        safe_alias = alias.replace(" ", "_")
        return os.path.join(self.storage_path, f"{safe_alias}.wallet")

    def _load(self):
        if os.path.exists(self.records_file):
            with open(self.records_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for entry in data:
                    record = EmbeddedWalletRecord.from_dict(entry)
                    self.records[record.alias] = record

    def _save(self):
        with open(self.records_file, "w", encoding="utf-8") as f:
            json.dump([rec.to_dict() for rec in self.records.values()], f, indent=2)

    def create_embedded_wallet(self, alias: str, contact: str, secret: str) -> EmbeddedWalletRecord:
        if alias in self.records:
            raise ValueError("Alias already exists")

        wallet_name = f"embedded_{alias}"
        password = secret or Config.WALLET_PASSWORD or secrets.token_hex(16)
        wallet = self.wallet_manager.create_wallet(wallet_name, password=password)
        record = EmbeddedWalletRecord(
            alias=alias,
            contact=contact,
            wallet_name=wallet_name,
            address=wallet.address,
            secret_hash=self._hash_secret(secret),
        )
        self.records[alias] = record
        self.sessions[alias] = secrets.token_hex(16)
        self._save()
        return record

    def authenticate(self, alias: str, secret: str) -> Optional[str]:
        record = self.records.get(alias)
        if not record:
            return None
        if record.secret_hash != self._hash_secret(secret):
            return None
        token = secrets.token_hex(16)
        self.sessions[alias] = token
        return token

    def get_session_token(self, alias: str) -> Optional[str]:
        return self.sessions.get(alias)

    def get_session(self, alias: str) -> Optional[str]:
        return self.sessions.get(alias)

    def get_record(self, alias: str) -> Optional[EmbeddedWalletRecord]:
        return self.records.get(alias)

    def add_gas_sponsor(self, sponsor_address: str, budget: float, rate_limit: int = 10) -> 'GasSponsor':
        """
        Add a gas sponsor for account abstraction (Task 178)

        Args:
            sponsor_address: Address of the sponsor
            budget: Total budget for gas sponsorship
            rate_limit: Maximum transactions per user per day

        Returns:
            GasSponsor instance
        """
        sponsor = GasSponsor(sponsor_address, budget, rate_limit)
        self.gas_sponsors[sponsor_address] = sponsor
        return sponsor

    def get_gas_sponsor(self, sponsor_address: str) -> Optional['GasSponsor']:
        """Get gas sponsor by address"""
        return self.gas_sponsors.get(sponsor_address)

    def request_sponsored_gas(
        self,
        user_address: str,
        sponsor_address: str,
        gas_amount: float
    ) -> bool:
        """
        Request sponsored gas for a transaction

        Args:
            user_address: User requesting sponsorship
            sponsor_address: Sponsor address
            gas_amount: Amount of gas needed

        Returns:
            True if sponsorship approved
        """
        sponsor = self.gas_sponsors.get(sponsor_address)
        if not sponsor:
            return False

        return sponsor.sponsor_transaction(user_address, gas_amount)
