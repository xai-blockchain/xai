"""
Manager Protocol Interfaces - Decoupling managers from Blockchain class.

This module defines Protocol interfaces that managers can depend on instead
of the full Blockchain class. This breaks circular coupling and enables:
- Better testability (easy to mock specific protocols)
- Interface segregation (managers only see methods they need)
- Reduced import complexity

Usage:
    # In managers, accept protocols instead of Blockchain:
    class MiningManager:
        def __init__(
            self,
            chain: ChainProvider,
            config: ConfigProvider,
            state: StateProvider,
        ): ...

    # Blockchain implements all protocols and passes itself:
    self.mining_manager = MiningManager(self, self, self)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from threading import RLock

    from xai.core.chain.address_index import AddressTransactionIndex
    from xai.core.chain.block_header import BlockHeader
    from xai.core.blockchain_components.block import Block
    from xai.core.transactions.nonce_tracker import NonceTracker
    from xai.core.api.structured_logger import StructuredLogger
    from xai.core.transaction import Transaction
    from xai.core.transactions.utxo_manager import UTXOManager


@runtime_checkable
class ChainProvider(Protocol):
    """
    Protocol for blockchain chain data access.

    Provides access to the chain of block headers, pending transactions,
    and orphan transactions.
    """

    @property
    def chain(self) -> list["BlockHeader"]:
        """Get the list of block headers in the chain."""
        ...

    @property
    def pending_transactions(self) -> list["Transaction"]:
        """Get list of transactions waiting to be mined."""
        ...

    @property
    def orphan_transactions(self) -> list["Transaction"]:
        """Get list of transactions with unmet dependencies."""
        ...

    def get_block(self, index: int) -> "Block | None":
        """Get a block by index. Returns None if not found."""
        ...

    def get_block_by_hash(self, block_hash: str) -> "Block | None":
        """Get a block by hash. Returns None if not found."""
        ...

    def get_latest_block(self) -> "BlockHeader":
        """Get the latest block header."""
        ...

    def get_height(self) -> int:
        """Get current chain height (number of blocks - 1)."""
        ...


@runtime_checkable
class ConfigProvider(Protocol):
    """
    Protocol for blockchain configuration access.

    Provides access to network configuration, difficulty, and paths.
    """

    @property
    def difficulty(self) -> int:
        """Get current mining difficulty."""
        ...

    @property
    def max_supply(self) -> float:
        """Get maximum token supply cap."""
        ...

    @property
    def network_type(self) -> str:
        """Get network type: 'mainnet', 'testnet', 'regtest'."""
        ...

    @property
    def data_dir(self) -> str:
        """Get blockchain data directory path."""
        ...

    @property
    def logger(self) -> "StructuredLogger":
        """Get structured logger instance."""
        ...

    @property
    def block_reward(self) -> float:
        """Get current block reward amount."""
        ...


@runtime_checkable
class StateProvider(Protocol):
    """
    Protocol for blockchain state access.

    Provides access to indexes, locks, and state managers.
    """

    @property
    def _block_hash_index(self) -> dict[str, int]:
        """Get block hash to index mapping."""
        ...

    @property
    def _chain_lock(self) -> "RLock":
        """Get chain modification lock."""
        ...

    @property
    def _mempool_lock(self) -> "RLock":
        """Get mempool modification lock."""
        ...

    @property
    def address_index(self) -> "AddressTransactionIndex":
        """Get address transaction index."""
        ...

    @property
    def nonce_tracker(self) -> "NonceTracker":
        """Get nonce tracker for replay protection."""
        ...


@runtime_checkable
class UTXOProvider(Protocol):
    """
    Protocol for UTXO-related operations.

    Provides access to balances and UTXO management.
    """

    @property
    def utxo_manager(self) -> "UTXOManager":
        """Get UTXO manager instance."""
        ...

    def get_balance(self, address: str) -> float:
        """Get balance for an address."""
        ...

    def get_utxo_set(self) -> dict[str, list[dict[str, Any]]]:
        """Get the current UTXO set."""
        ...


@runtime_checkable
class ValidationProvider(Protocol):
    """
    Protocol for validation operations.

    Provides access to block and transaction validation.
    """

    def validate_block(self, block: "Block") -> tuple[bool, str]:
        """Validate a block. Returns (valid, reason)."""
        ...

    def validate_transaction(self, tx: "Transaction") -> bool:
        """Validate a transaction. Returns True if valid."""
        ...

    def is_valid_proof_of_work(self, block: "Block") -> bool:
        """Check if block meets proof of work requirements."""
        ...


@runtime_checkable
class StorageProvider(Protocol):
    """
    Protocol for blockchain storage operations.

    Provides access to disk persistence operations.
    """

    def load_block_from_disk(self, index: int) -> "Block | None":
        """Load a block from disk storage."""
        ...

    def save_block_to_disk(self, index: int, block_data: dict[str, Any]) -> None:
        """Save a block to disk storage."""
        ...

    def verify_integrity(self) -> bool:
        """Verify storage integrity."""
        ...

    def save_blockchain_sync(self) -> None:
        """Synchronously save blockchain state."""
        ...


@runtime_checkable
class MiningProvider(Protocol):
    """
    Protocol for mining-related operations.

    Provides access to mining state and rewards.
    """

    @property
    def mining_active(self) -> bool:
        """Check if mining is currently active."""
        ...

    def calculate_block_reward(self, height: int) -> float:
        """Calculate block reward for a given height."""
        ...

    def get_mining_stats(self) -> dict[str, Any]:
        """Get mining statistics."""
        ...


@runtime_checkable
class GovernanceProvider(Protocol):
    """
    Protocol for governance-related operations.

    Provides access to governance state and proposal management.
    """

    @property
    def governance_state(self) -> Any:
        """Get current governance state."""
        ...

    def get_active_proposals(self) -> list[dict[str, Any]]:
        """Get list of active governance proposals."""
        ...


# Type alias for managers that need full blockchain access (migration path)
class FullBlockchainProvider(
    ChainProvider,
    ConfigProvider,
    StateProvider,
    UTXOProvider,
    ValidationProvider,
    StorageProvider,
    Protocol,
):
    """
    Combined protocol for managers that need broad blockchain access.

    This is a migration path - prefer using specific protocols where possible.
    """

    pass


__all__ = [
    "ChainProvider",
    "ConfigProvider",
    "StateProvider",
    "UTXOProvider",
    "ValidationProvider",
    "StorageProvider",
    "MiningProvider",
    "GovernanceProvider",
    "FullBlockchainProvider",
]
