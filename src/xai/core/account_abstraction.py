"""
Account abstraction helpers and embedded wallet management.
Task 178: Gas sponsorship for account abstraction

This module provides:
- Embedded wallet management for social/email login
- Gas sponsorship for gasless transactions (account abstraction)
- Rate limiting and budget controls for sponsors
- Full integration with the transaction pipeline

Gas Sponsorship Flow:
1. Sponsor registers with a budget and rate limit
2. User creates a transaction with gas_sponsor field set
3. Sponsor authorizes the transaction (signs approval)
4. Transaction validator checks sponsor authorization
5. Fee is deducted from sponsor's budget, not user's balance
6. Transaction is processed normally

Security Considerations:
- Sponsors must cryptographically authorize each transaction
- Rate limits prevent abuse (per user per day)
- Budget caps prevent unlimited spending
- Blacklist/whitelist support for access control
"""

import json
import logging
import os
import hashlib
import secrets
import time
from pathlib import Path
from typing import Dict, Optional, List, Tuple, TYPE_CHECKING
from dataclasses import dataclass, field
from enum import Enum

from xai.core.wallet import WalletManager
from xai.core.config import Config
from xai.core.crypto_utils import sign_message_hex, verify_signature_hex

if TYPE_CHECKING:
    from xai.core.transaction import Transaction
    from xai.core.blockchain import Blockchain

logger = logging.getLogger(__name__)


class TransactionStatus(Enum):
    """Status of a sponsored transaction"""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"


@dataclass
class SponsoredTransaction:
    """Record of a sponsored transaction"""
    user_address: str
    txid: str
    gas_amount: float
    timestamp: float
    sponsor_address: str
    status: str = "pending"  # TransactionStatus value
    blockchain_txid: Optional[str] = None  # Final confirmed txid


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
        self._txid_map: Dict[str, SponsoredTransaction] = {}  # preliminary_txid -> transaction

    def _generate_preliminary_txid(self, user_address: str, gas_amount: float, timestamp: float) -> str:
        """
        Generate preliminary transaction ID from transaction parameters.

        This provides a unique identifier before the blockchain txid is available.

        Args:
            user_address: User address
            gas_amount: Amount of gas
            timestamp: Transaction timestamp

        Returns:
            SHA256 hash as preliminary txid
        """
        data = f"{user_address}:{gas_amount}:{timestamp}:{self.sponsor_address}".encode()
        return hashlib.sha256(data).hexdigest()

    def sponsor_transaction(self, user_address: str, gas_amount: float) -> Optional[str]:
        """
        Sponsor a transaction for a user

        Args:
            user_address: User address
            gas_amount: Amount of gas needed

        Returns:
            Preliminary transaction ID if approved, None if rejected
        """
        if not self.enabled:
            logger.debug(
                "Sponsorship rejected: sponsor disabled",
                extra={"event": "gas_sponsor.rejected", "reason": "disabled"}
            )
            return None

        # Check blacklist
        if user_address in self.blacklist:
            logger.debug(
                "Sponsorship rejected: user blacklisted",
                extra={
                    "event": "gas_sponsor.rejected",
                    "reason": "blacklisted",
                    "user": user_address[:16] + "..."
                }
            )
            return None

        # Check whitelist (if configured)
        if self.whitelist and user_address not in self.whitelist:
            logger.debug(
                "Sponsorship rejected: user not whitelisted",
                extra={
                    "event": "gas_sponsor.rejected",
                    "reason": "not_whitelisted",
                    "user": user_address[:16] + "..."
                }
            )
            return None

        # Check budget
        if gas_amount > self.remaining_budget:
            logger.warning(
                "Sponsorship rejected: insufficient budget",
                extra={
                    "event": "gas_sponsor.rejected",
                    "reason": "insufficient_budget",
                    "requested": gas_amount,
                    "remaining": self.remaining_budget
                }
            )
            return None

        # Check per-transaction limit
        if gas_amount > self.max_gas_per_transaction:
            logger.warning(
                "Sponsorship rejected: exceeds per-tx limit",
                extra={
                    "event": "gas_sponsor.rejected",
                    "reason": "exceeds_limit",
                    "requested": gas_amount,
                    "limit": self.max_gas_per_transaction
                }
            )
            return None

        # Check rate limit
        if not self._check_rate_limit(user_address):
            logger.warning(
                "Sponsorship rejected: rate limit exceeded",
                extra={
                    "event": "gas_sponsor.rejected",
                    "reason": "rate_limit",
                    "user": user_address[:16] + "...",
                    "limit": self.rate_limit
                }
            )
            return None

        # Approve sponsorship
        self.remaining_budget -= gas_amount

        # Generate preliminary txid
        timestamp = time.time()
        preliminary_txid = self._generate_preliminary_txid(user_address, gas_amount, timestamp)

        # Record transaction with preliminary txid
        tx = SponsoredTransaction(
            user_address=user_address,
            txid=preliminary_txid,
            gas_amount=gas_amount,
            timestamp=timestamp,
            sponsor_address=self.sponsor_address,
            status=TransactionStatus.PENDING.value,
            blockchain_txid=None
        )
        self.sponsored_transactions.append(tx)
        self._txid_map[preliminary_txid] = tx

        # Update user usage
        if user_address not in self.user_daily_usage:
            self.user_daily_usage[user_address] = []
        self.user_daily_usage[user_address].append(timestamp)

        logger.info(
            "Transaction sponsored",
            extra={
                "event": "gas_sponsor.sponsored",
                "preliminary_txid": preliminary_txid[:16] + "...",
                "user": user_address[:16] + "...",
                "gas_amount": gas_amount,
                "remaining_budget": self.remaining_budget
            }
        )

        return preliminary_txid

    def confirm_sponsored_transaction(self, preliminary_txid: str, blockchain_txid: str) -> bool:
        """
        Update sponsored transaction with confirmed blockchain txid.

        This should be called after the transaction is confirmed in a block.

        Args:
            preliminary_txid: Preliminary txid returned from sponsor_transaction()
            blockchain_txid: Actual blockchain transaction ID

        Returns:
            True if transaction found and updated
        """
        tx = self._txid_map.get(preliminary_txid)
        if not tx:
            logger.warning(
                "Cannot confirm transaction: preliminary txid not found",
                extra={
                    "event": "gas_sponsor.confirm_failed",
                    "preliminary_txid": preliminary_txid[:16] + "..."
                }
            )
            return False

        tx.blockchain_txid = blockchain_txid
        tx.status = TransactionStatus.CONFIRMED.value

        logger.info(
            "Sponsored transaction confirmed",
            extra={
                "event": "gas_sponsor.tx_confirmed",
                "preliminary_txid": preliminary_txid[:16] + "...",
                "blockchain_txid": blockchain_txid[:16] + "...",
                "user": tx.user_address[:16] + "...",
                "gas_amount": tx.gas_amount
            }
        )

        return True

    def fail_sponsored_transaction(self, preliminary_txid: str, reason: str = "") -> bool:
        """
        Mark a sponsored transaction as failed.

        This should be called if the transaction fails to be confirmed.
        The gas amount will be refunded to the sponsor's budget.

        Args:
            preliminary_txid: Preliminary txid returned from sponsor_transaction()
            reason: Optional reason for failure

        Returns:
            True if transaction found and updated
        """
        tx = self._txid_map.get(preliminary_txid)
        if not tx:
            logger.warning(
                "Cannot fail transaction: preliminary txid not found",
                extra={
                    "event": "gas_sponsor.fail_failed",
                    "preliminary_txid": preliminary_txid[:16] + "..."
                }
            )
            return False

        # Only refund if still pending (not already confirmed)
        if tx.status == TransactionStatus.PENDING.value:
            self.remaining_budget += tx.gas_amount
            tx.status = TransactionStatus.FAILED.value

            logger.info(
                "Sponsored transaction failed",
                extra={
                    "event": "gas_sponsor.tx_failed",
                    "preliminary_txid": preliminary_txid[:16] + "...",
                    "user": tx.user_address[:16] + "...",
                    "gas_amount": tx.gas_amount,
                    "refunded": True,
                    "reason": reason,
                    "remaining_budget": self.remaining_budget
                }
            )

            return True

        logger.warning(
            "Cannot fail transaction: already in final state",
            extra={
                "event": "gas_sponsor.fail_rejected",
                "preliminary_txid": preliminary_txid[:16] + "...",
                "status": tx.status
            }
        )
        return False

    def get_transaction_by_preliminary_txid(self, preliminary_txid: str) -> Optional[SponsoredTransaction]:
        """
        Get transaction by preliminary txid.

        Args:
            preliminary_txid: Preliminary transaction ID

        Returns:
            SponsoredTransaction if found, None otherwise
        """
        return self._txid_map.get(preliminary_txid)

    def get_transaction_by_blockchain_txid(self, blockchain_txid: str) -> Optional[SponsoredTransaction]:
        """
        Get transaction by blockchain txid.

        Args:
            blockchain_txid: Blockchain transaction ID

        Returns:
            SponsoredTransaction if found, None otherwise
        """
        for tx in self.sponsored_transactions:
            if tx.blockchain_txid == blockchain_txid:
                return tx
        return None

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
    ) -> Optional[str]:
        """
        Request sponsored gas for a transaction

        Args:
            user_address: User requesting sponsorship
            sponsor_address: Sponsor address
            gas_amount: Amount of gas needed

        Returns:
            Preliminary transaction ID if approved, None if rejected
        """
        sponsor = self.gas_sponsors.get(sponsor_address)
        if not sponsor:
            return None

        return sponsor.sponsor_transaction(user_address, gas_amount)


class SponsorshipResult(Enum):
    """Result of sponsorship validation"""
    APPROVED = "approved"
    NO_SPONSOR = "no_sponsor"
    SPONSOR_NOT_FOUND = "sponsor_not_found"
    SPONSOR_DISABLED = "sponsor_disabled"
    INSUFFICIENT_BUDGET = "insufficient_budget"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    USER_BLACKLISTED = "user_blacklisted"
    USER_NOT_WHITELISTED = "user_not_whitelisted"
    INVALID_SIGNATURE = "invalid_signature"
    FEE_TOO_HIGH = "fee_too_high"


@dataclass
class SponsorshipValidation:
    """Result of sponsorship validation"""
    result: SponsorshipResult
    sponsor_address: Optional[str] = None
    fee_amount: float = 0.0
    message: str = ""


class SponsoredTransactionProcessor:
    """
    Processes sponsored transactions for account abstraction.

    This processor integrates with the blockchain to enable gasless transactions
    where sponsors pay fees on behalf of users.

    Usage:
        processor = SponsoredTransactionProcessor()

        # Register a sponsor
        sponsor = processor.register_sponsor(
            sponsor_address="XAI...",
            sponsor_private_key="...",
            budget=100.0,
            rate_limit=50
        )

        # Create sponsored transaction
        tx = Transaction(
            sender="XAIuser...",
            recipient="XAIrecipient...",
            amount=10.0,
            fee=0.001,
            gas_sponsor="XAIsponsor..."
        )

        # Authorize and process
        processor.authorize_transaction(tx, sponsor_private_key)
        validation = processor.validate_sponsored_transaction(tx)
        if validation.result == SponsorshipResult.APPROVED:
            blockchain.add_transaction(tx)
    """

    def __init__(self):
        """Initialize the sponsored transaction processor"""
        self.sponsors: Dict[str, GasSponsor] = {}
        self.sponsor_keys: Dict[str, str] = {}  # sponsor_address -> public_key
        self._persistence_path: Optional[str] = None

    def register_sponsor(
        self,
        sponsor_address: str,
        sponsor_public_key: str,
        budget: float,
        rate_limit: int = 50,
        max_fee_per_tx: float = 0.1,
        whitelist: Optional[List[str]] = None,
        blacklist: Optional[List[str]] = None,
    ) -> GasSponsor:
        """
        Register a new gas sponsor.

        Args:
            sponsor_address: Address of the sponsor
            sponsor_public_key: Public key for signature verification
            budget: Total budget for sponsorship (in XAI)
            rate_limit: Maximum transactions per user per day
            max_fee_per_tx: Maximum fee sponsor will pay per transaction
            whitelist: Optional list of allowed user addresses
            blacklist: Optional list of blocked user addresses

        Returns:
            GasSponsor instance

        Example:
            sponsor = processor.register_sponsor(
                sponsor_address="XAI1234...",
                sponsor_public_key="04abc...",
                budget=100.0,
                rate_limit=50,
                max_fee_per_tx=0.01
            )
        """
        sponsor = GasSponsor(sponsor_address, budget, rate_limit)
        sponsor.max_gas_per_transaction = max_fee_per_tx

        if whitelist:
            sponsor.set_whitelist(whitelist)
        if blacklist:
            sponsor.set_blacklist(blacklist)

        self.sponsors[sponsor_address] = sponsor
        self.sponsor_keys[sponsor_address] = sponsor_public_key

        logger.info(
            "Registered gas sponsor",
            extra={
                "event": "gas_sponsor.registered",
                "sponsor": sponsor_address[:16] + "...",
                "budget": budget,
                "rate_limit": rate_limit
            }
        )

        return sponsor

    def authorize_transaction(
        self,
        transaction: "Transaction",
        sponsor_private_key: str
    ) -> bool:
        """
        Authorize a sponsored transaction by signing with sponsor's key.

        This creates a signature proving the sponsor approves paying the fee
        for this specific transaction.

        Args:
            transaction: Transaction to authorize
            sponsor_private_key: Sponsor's private key for signing

        Returns:
            True if authorization successful
        """
        if not transaction.gas_sponsor:
            logger.warning("Cannot authorize: no gas_sponsor set on transaction")
            return False

        # Create authorization message: sponsor_address + txid + fee + timestamp
        auth_data = {
            "sponsor": transaction.gas_sponsor,
            "sender": transaction.sender,
            "recipient": transaction.recipient,
            "amount": transaction.amount,
            "fee": transaction.fee,
            "timestamp": transaction.timestamp,
        }
        auth_message = json.dumps(auth_data, sort_keys=True)
        auth_hash = hashlib.sha256(auth_message.encode()).hexdigest()

        try:
            signature = sign_message_hex(sponsor_private_key, auth_hash.encode())
            transaction.gas_sponsor_signature = signature

            logger.debug(
                "Transaction authorized by sponsor",
                extra={
                    "event": "gas_sponsor.authorized",
                    "sponsor": transaction.gas_sponsor[:16] + "...",
                    "txid": transaction.txid[:16] + "..." if transaction.txid else "pending"
                }
            )
            return True

        except Exception as e:
            logger.error(
                f"Failed to authorize transaction: {e}",
                extra={"event": "gas_sponsor.auth_failed"}
            )
            return False

    def verify_sponsor_signature(self, transaction: "Transaction") -> bool:
        """
        Verify the sponsor's authorization signature.

        Args:
            transaction: Transaction with gas_sponsor_signature

        Returns:
            True if signature is valid
        """
        if not transaction.gas_sponsor or not transaction.gas_sponsor_signature:
            return False

        sponsor_public_key = self.sponsor_keys.get(transaction.gas_sponsor)
        if not sponsor_public_key:
            return False

        # Recreate authorization message
        auth_data = {
            "sponsor": transaction.gas_sponsor,
            "sender": transaction.sender,
            "recipient": transaction.recipient,
            "amount": transaction.amount,
            "fee": transaction.fee,
            "timestamp": transaction.timestamp,
        }
        auth_message = json.dumps(auth_data, sort_keys=True)
        auth_hash = hashlib.sha256(auth_message.encode()).hexdigest()

        try:
            return verify_signature_hex(
                sponsor_public_key,
                auth_hash.encode(),
                transaction.gas_sponsor_signature
            )
        except Exception as e:
            logger.warning(
                f"Sponsor signature verification failed: {e}",
                extra={"event": "gas_sponsor.sig_verify_failed"}
            )
            return False

    def validate_sponsored_transaction(
        self,
        transaction: "Transaction"
    ) -> SponsorshipValidation:
        """
        Validate a sponsored transaction.

        Checks:
        1. Sponsor exists and is enabled
        2. Sponsor has sufficient budget
        3. User hasn't exceeded rate limit
        4. User is not blacklisted (and is whitelisted if required)
        5. Fee doesn't exceed per-transaction limit
        6. Sponsor signature is valid

        Args:
            transaction: Transaction to validate

        Returns:
            SponsorshipValidation with result and details
        """
        # Check if transaction has a sponsor
        if not transaction.gas_sponsor:
            return SponsorshipValidation(
                result=SponsorshipResult.NO_SPONSOR,
                message="Transaction has no gas sponsor"
            )

        sponsor = self.sponsors.get(transaction.gas_sponsor)
        if not sponsor:
            return SponsorshipValidation(
                result=SponsorshipResult.SPONSOR_NOT_FOUND,
                sponsor_address=transaction.gas_sponsor,
                message=f"Sponsor {transaction.gas_sponsor[:16]}... not registered"
            )

        # Check sponsor is enabled
        if not sponsor.enabled:
            return SponsorshipValidation(
                result=SponsorshipResult.SPONSOR_DISABLED,
                sponsor_address=transaction.gas_sponsor,
                message="Sponsor is disabled"
            )

        # Check blacklist
        if transaction.sender in sponsor.blacklist:
            return SponsorshipValidation(
                result=SponsorshipResult.USER_BLACKLISTED,
                sponsor_address=transaction.gas_sponsor,
                message=f"User {transaction.sender[:16]}... is blacklisted"
            )

        # Check whitelist (if configured)
        if sponsor.whitelist and transaction.sender not in sponsor.whitelist:
            return SponsorshipValidation(
                result=SponsorshipResult.USER_NOT_WHITELISTED,
                sponsor_address=transaction.gas_sponsor,
                message=f"User {transaction.sender[:16]}... not in whitelist"
            )

        # Check fee limit
        if transaction.fee > sponsor.max_gas_per_transaction:
            return SponsorshipValidation(
                result=SponsorshipResult.FEE_TOO_HIGH,
                sponsor_address=transaction.gas_sponsor,
                fee_amount=transaction.fee,
                message=f"Fee {transaction.fee} exceeds limit {sponsor.max_gas_per_transaction}"
            )

        # Check budget
        if transaction.fee > sponsor.remaining_budget:
            return SponsorshipValidation(
                result=SponsorshipResult.INSUFFICIENT_BUDGET,
                sponsor_address=transaction.gas_sponsor,
                fee_amount=transaction.fee,
                message=f"Insufficient budget: {sponsor.remaining_budget} < {transaction.fee}"
            )

        # Check rate limit
        if not sponsor._check_rate_limit(transaction.sender):
            return SponsorshipValidation(
                result=SponsorshipResult.RATE_LIMIT_EXCEEDED,
                sponsor_address=transaction.gas_sponsor,
                message=f"User exceeded rate limit of {sponsor.rate_limit}/day"
            )

        # Verify sponsor signature
        if not self.verify_sponsor_signature(transaction):
            return SponsorshipValidation(
                result=SponsorshipResult.INVALID_SIGNATURE,
                sponsor_address=transaction.gas_sponsor,
                message="Invalid sponsor authorization signature"
            )

        # All checks passed
        return SponsorshipValidation(
            result=SponsorshipResult.APPROVED,
            sponsor_address=transaction.gas_sponsor,
            fee_amount=transaction.fee,
            message="Sponsorship approved"
        )

    def deduct_sponsor_fee(
        self,
        transaction: "Transaction",
        preliminary_txid: Optional[str] = None
    ) -> bool:
        """
        Deduct the fee from sponsor's budget after transaction is processed.

        This should be called after the transaction is successfully added
        to the mempool or confirmed in a block.

        Args:
            transaction: The processed transaction
            preliminary_txid: Optional preliminary txid if transaction was pre-authorized

        Returns:
            True if deduction successful
        """
        if not transaction.gas_sponsor:
            return False

        sponsor = self.sponsors.get(transaction.gas_sponsor)
        if not sponsor:
            return False

        # If preliminary_txid provided, update existing record
        if preliminary_txid:
            existing_tx = sponsor.get_transaction_by_preliminary_txid(preliminary_txid)
            if existing_tx:
                # Update with blockchain txid
                if transaction.txid:
                    sponsor.confirm_sponsored_transaction(preliminary_txid, transaction.txid)
                logger.info(
                    "Sponsor fee deducted (existing authorization)",
                    extra={
                        "event": "gas_sponsor.fee_deducted",
                        "sponsor": transaction.gas_sponsor[:16] + "...",
                        "user": transaction.sender[:16] + "...",
                        "fee": transaction.fee,
                        "preliminary_txid": preliminary_txid[:16] + "...",
                        "blockchain_txid": (transaction.txid[:16] + "...") if transaction.txid else "none",
                        "remaining_budget": sponsor.remaining_budget
                    }
                )
                return True

        # New transaction not pre-authorized
        # Generate preliminary txid and create new record
        timestamp = time.time()
        new_preliminary_txid = sponsor._generate_preliminary_txid(
            transaction.sender,
            transaction.fee,
            timestamp
        )

        # Deduct fee from budget
        sponsor.remaining_budget -= transaction.fee

        # Record the sponsored transaction
        sponsored_tx = SponsoredTransaction(
            user_address=transaction.sender,
            txid=new_preliminary_txid,
            gas_amount=transaction.fee,
            timestamp=timestamp,
            sponsor_address=transaction.gas_sponsor,
            status=TransactionStatus.CONFIRMED.value if transaction.txid else TransactionStatus.PENDING.value,
            blockchain_txid=transaction.txid
        )
        sponsor.sponsored_transactions.append(sponsored_tx)
        sponsor._txid_map[new_preliminary_txid] = sponsored_tx

        # Update rate limit tracking
        if transaction.sender not in sponsor.user_daily_usage:
            sponsor.user_daily_usage[transaction.sender] = []
        sponsor.user_daily_usage[transaction.sender].append(timestamp)

        logger.info(
            "Sponsor fee deducted (new transaction)",
            extra={
                "event": "gas_sponsor.fee_deducted",
                "sponsor": transaction.gas_sponsor[:16] + "...",
                "user": transaction.sender[:16] + "...",
                "fee": transaction.fee,
                "preliminary_txid": new_preliminary_txid[:16] + "...",
                "blockchain_txid": (transaction.txid[:16] + "...") if transaction.txid else "none",
                "remaining_budget": sponsor.remaining_budget
            }
        )

        return True

    def get_sponsor(self, sponsor_address: str) -> Optional[GasSponsor]:
        """Get a registered sponsor by address"""
        return self.sponsors.get(sponsor_address)

    def get_all_sponsors(self) -> Dict[str, Dict]:
        """Get stats for all registered sponsors"""
        return {
            addr: sponsor.get_stats()
            for addr, sponsor in self.sponsors.items()
        }

    def is_sponsored_transaction(self, transaction: "Transaction") -> bool:
        """Check if a transaction has gas sponsorship"""
        return bool(transaction.gas_sponsor)


# Global processor instance for integration with blockchain
_global_processor: Optional[SponsoredTransactionProcessor] = None


def get_sponsored_transaction_processor() -> SponsoredTransactionProcessor:
    """
    Get the global sponsored transaction processor.

    This provides a singleton processor that can be used across the codebase
    for consistent gas sponsorship management.

    Returns:
        SponsoredTransactionProcessor instance
    """
    global _global_processor
    if _global_processor is None:
        _global_processor = SponsoredTransactionProcessor()
    return _global_processor


def process_sponsored_transaction(
    transaction: "Transaction",
    blockchain: Optional["Blockchain"] = None
) -> Tuple[bool, str]:
    """
    Process a sponsored transaction through the full pipeline.

    This is a convenience function that:
    1. Validates the sponsorship
    2. If valid, allows the transaction to proceed (fee paid by sponsor)
    3. Deducts the fee from sponsor's budget

    Args:
        transaction: Transaction to process
        blockchain: Optional blockchain instance for additional validation

    Returns:
        Tuple of (success, message)

    Example:
        success, message = process_sponsored_transaction(tx)
        if success:
            print(f"Transaction sponsored: {message}")
        else:
            print(f"Sponsorship failed: {message}")
    """
    processor = get_sponsored_transaction_processor()

    # Validate sponsorship
    validation = processor.validate_sponsored_transaction(transaction)

    if validation.result != SponsorshipResult.APPROVED:
        return False, validation.message

    # Sponsorship approved - fee will be covered by sponsor
    # The actual fee deduction happens when the transaction is confirmed
    return True, f"Sponsored by {validation.sponsor_address[:16]}..."
