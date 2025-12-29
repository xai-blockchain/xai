from __future__ import annotations

"""
Interface for blockchain data needed by external modules (e.g., monitoring and gamification).

This module helps to break cyclic dependencies by providing lightweight,
abstract views of blockchain data without directly importing the full
Blockchain implementation.
"""

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class BlockchainDataProvider:
    """
    Provides essential blockchain statistics without a direct dependency
    on the full Blockchain class.
    """
    chain_height: int
    pending_transactions_count: int
    orphan_blocks_count: int
    orphan_transactions_count: int
    total_circulating_supply: float
    difficulty: int
    mempool_size_bytes: int = 0

    def get_stats(self) -> dict[str, Any]:
        """Return a dictionary of the provided statistics."""
        return {
            "chain_height": self.chain_height,
            "pending_transactions_count": self.pending_transactions_count,
            "orphan_blocks_count": self.orphan_blocks_count,
            "orphan_transactions_count": self.orphan_transactions_count,
            "total_circulating_supply": self.total_circulating_supply,
            "difficulty": self.difficulty,
            "mempool_size_bytes": self.mempool_size_bytes,
        }

class GamificationBlockchainInterface(ABC):
    """
    Interface for blockchain methods needed by gamification managers.
    This helps to break cyclic dependencies by abstracting the Blockchain class.
    """
    @abstractmethod
    def get_balance(self, address: str) -> float:
        """Get the balance of a given address."""

    @abstractmethod
    def get_chain_length(self) -> int:
        """Get the current length of the blockchain."""

    @abstractmethod
    def get_block_by_index(self, index: int) -> Any | None:
        """Get a block by its index (returns a simplified view or header)."""

    @abstractmethod
    def get_latest_block_hash(self) -> str:
        """Get the hash of the latest block."""

    @abstractmethod
    def get_pending_transactions(self) -> list[Any]:
        """Get the list of pending transactions."""
    
    @abstractmethod
    def add_transaction_to_mempool(self, transaction: Any) -> bool:
        """Add a transaction to the mempool."""
