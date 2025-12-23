from __future__ import annotations

"""
XAI SDK Data Models

Defines all data structures used in the SDK.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

class TransactionStatus(str, Enum):
    """Transaction status enumeration."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"

class WalletType(str, Enum):
    """Wallet type enumeration."""

    STANDARD = "standard"
    EMBEDDED = "embedded"
    HARDWARE = "hardware"

class ProposalStatus(str, Enum):
    """Proposal status enumeration."""

    PENDING = "pending"
    ACTIVE = "active"
    PASSED = "passed"
    FAILED = "failed"

@dataclass
class Wallet:
    """Represents a blockchain wallet."""

    address: str
    public_key: str
    created_at: datetime
    wallet_type: WalletType = WalletType.STANDARD
    private_key: str | None = None
    nonce: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_valid(self) -> bool:
        """Check if wallet address is valid."""
        return len(self.address) > 0 and len(self.public_key) > 0

    def to_dict(self) -> dict[str, Any]:
        """Convert wallet to dictionary."""
        return {
            "address": self.address,
            "public_key": self.public_key,
            "created_at": self.created_at.isoformat(),
            "wallet_type": self.wallet_type.value,
            "nonce": self.nonce,
            "metadata": self.metadata,
        }

@dataclass
class Balance:
    """Represents wallet balance information."""

    address: str
    balance: str
    locked_balance: str = "0"
    available_balance: str = "0"
    nonce: int = 0
    last_updated: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert balance to dictionary."""
        return {
            "address": self.address,
            "balance": self.balance,
            "locked_balance": self.locked_balance,
            "available_balance": self.available_balance,
            "nonce": self.nonce,
        }

@dataclass
class Transaction:
    """Represents a blockchain transaction."""

    hash: str
    from_address: str
    to_address: str
    amount: str
    timestamp: datetime
    status: TransactionStatus = TransactionStatus.PENDING
    fee: str = "0"
    gas_limit: str = "21000"
    gas_used: str = "0"
    gas_price: str = "0"
    nonce: int = 0
    data: str | None = None
    block_number: int | None = None
    block_hash: str | None = None
    confirmations: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_confirmed(self) -> bool:
        """Check if transaction is confirmed."""
        return self.status == TransactionStatus.CONFIRMED

    @property
    def is_pending(self) -> bool:
        """Check if transaction is pending."""
        return self.status == TransactionStatus.PENDING

    @property
    def is_failed(self) -> bool:
        """Check if transaction failed."""
        return self.status == TransactionStatus.FAILED

    def to_dict(self) -> dict[str, Any]:
        """Convert transaction to dictionary."""
        return {
            "hash": self.hash,
            "from": self.from_address,
            "to": self.to_address,
            "amount": self.amount,
            "fee": self.fee,
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat(),
            "gas_used": self.gas_used,
            "block_number": self.block_number,
            "confirmations": self.confirmations,
        }

@dataclass
class Block:
    """Represents a blockchain block."""

    number: int
    hash: str
    parent_hash: str
    timestamp: int
    miner: str
    difficulty: str
    gas_limit: str
    gas_used: str
    transactions: int
    transaction_hashes: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert block to dictionary."""
        return {
            "number": self.number,
            "hash": self.hash,
            "parent_hash": self.parent_hash,
            "timestamp": self.timestamp,
            "miner": self.miner,
            "difficulty": self.difficulty,
            "gas_used": self.gas_used,
            "transactions": self.transactions,
        }

@dataclass
class Proposal:
    """Represents a governance proposal."""

    id: int
    title: str
    description: str
    creator: str
    status: ProposalStatus
    created_at: datetime
    voting_starts_at: datetime | None = None
    voting_ends_at: datetime | None = None
    votes_for: int = 0
    votes_against: int = 0
    votes_abstain: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_active(self) -> bool:
        """Check if proposal is currently active."""
        return self.status == ProposalStatus.ACTIVE

    @property
    def total_votes(self) -> int:
        """Get total number of votes."""
        return self.votes_for + self.votes_against + self.votes_abstain

    def to_dict(self) -> dict[str, Any]:
        """Convert proposal to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "creator": self.creator,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "voting_ends_at": self.voting_ends_at.isoformat()
            if self.voting_ends_at
            else None,
            "votes_for": self.votes_for,
            "votes_against": self.votes_against,
            "votes_abstain": self.votes_abstain,
        }

@dataclass
class MiningStatus:
    """Represents mining status information."""

    mining: bool
    threads: int
    hashrate: str
    blocks_found: int
    current_difficulty: str
    uptime: int
    last_block_time: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert mining status to dictionary."""
        return {
            "mining": self.mining,
            "threads": self.threads,
            "hashrate": self.hashrate,
            "blocks_found": self.blocks_found,
            "current_difficulty": self.current_difficulty,
            "uptime": self.uptime,
        }

@dataclass
class TradeOrder:
    """Represents a trading order."""

    id: str
    from_address: str
    to_address: str
    from_amount: str
    to_amount: str
    created_at: datetime
    status: str = "pending"
    expires_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert trade order to dictionary."""
        return {
            "id": self.id,
            "from_address": self.from_address,
            "to_address": self.to_address,
            "from_amount": self.from_amount,
            "to_amount": self.to_amount,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
        }

@dataclass
class BlockchainStats:
    """Represents blockchain statistics."""

    total_blocks: int
    total_transactions: int
    total_accounts: int
    difficulty: str
    hashrate: str
    average_block_time: float
    total_supply: str
    network: str = "mainnet"
    timestamp: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert blockchain stats to dictionary."""
        return {
            "total_blocks": self.total_blocks,
            "total_transactions": self.total_transactions,
            "total_accounts": self.total_accounts,
            "difficulty": self.difficulty,
            "hashrate": self.hashrate,
            "average_block_time": self.average_block_time,
            "total_supply": self.total_supply,
            "network": self.network,
        }
