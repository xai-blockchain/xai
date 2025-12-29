"""
XAI Blockchain - Core Protocol Interfaces

This module defines Protocol interfaces for core blockchain components.
Using Protocol (from typing) allows for structural subtyping, enabling:
- Better testability through mock implementations
- Dependency injection without class inheritance
- Clear API contracts for core components
- Type checking without runtime overhead

Security Notes:
- Protocol interfaces define minimum expected behavior
- Implementations must validate all inputs
- Thread safety requirements documented per interface
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, Sequence, runtime_checkable

if TYPE_CHECKING:
    from xai.core.transaction import Transaction


@runtime_checkable
class IUTXOManager(Protocol):
    """
    Protocol for UTXO (Unspent Transaction Output) management.

    Thread Safety: All implementations MUST be thread-safe.
    Implementations should use RLock for concurrent access.
    """

    def add_utxo(
        self,
        address: str,
        txid: str,
        vout: int,
        amount: float,
        script_pubkey: str | None = None,
    ) -> bool:
        """
        Add a new UTXO to the set.

        Args:
            address: Owner address
            txid: Transaction ID that created this UTXO
            vout: Output index in the transaction
            amount: Value in XAI
            script_pubkey: Optional locking script

        Returns:
            True if added successfully, False if duplicate or invalid

        Security:
            - Must validate amount is positive and within bounds
            - Must reject duplicate UTXOs
        """
        ...

    def remove_utxo(self, address: str, txid: str, vout: int) -> bool:
        """
        Remove (spend) a UTXO from the set.

        Args:
            address: Owner address
            txid: Transaction ID of the UTXO
            vout: Output index

        Returns:
            True if removed successfully, False if not found
        """
        ...

    def get_utxos(self, address: str) -> list[dict[str, Any]]:
        """
        Get all unspent UTXOs for an address.

        Args:
            address: Address to query

        Returns:
            List of UTXO dictionaries with txid, vout, amount, script_pubkey
        """
        ...

    def get_balance(self, address: str) -> float:
        """
        Get total balance for an address.

        Args:
            address: Address to query

        Returns:
            Total balance in XAI
        """
        ...

    def utxo_exists(self, txid: str, vout: int) -> bool:
        """
        Check if a specific UTXO exists.

        Args:
            txid: Transaction ID
            vout: Output index

        Returns:
            True if UTXO exists and is unspent
        """
        ...

    def snapshot_digest(self) -> str:
        """
        Generate deterministic hash of UTXO state.

        Returns:
            SHA-256 hex digest of sorted UTXO entries
        """
        ...


@runtime_checkable
class IMempool(Protocol):
    """
    Protocol for transaction mempool management.

    Thread Safety: All implementations MUST be thread-safe.
    Must prevent double-spend across pending transactions.
    """

    def add_transaction(self, tx: "Transaction") -> tuple[bool, str]:
        """
        Add a transaction to the mempool.

        Args:
            tx: Transaction to add

        Returns:
            Tuple of (success, message)

        Security:
            - Must validate transaction before adding
            - Must check for double-spend against pending txs
            - Must enforce per-sender limits
        """
        ...

    def remove_transaction(self, txid: str) -> bool:
        """
        Remove a transaction from the mempool.

        Args:
            txid: Transaction ID to remove

        Returns:
            True if removed, False if not found
        """
        ...

    def get_transaction(self, txid: str) -> "Transaction | None":
        """
        Get a transaction from the mempool by ID.

        Args:
            txid: Transaction ID

        Returns:
            Transaction if found, None otherwise
        """
        ...

    def get_pending_transactions(self, limit: int = 100) -> list["Transaction"]:
        """
        Get pending transactions for block inclusion.

        Args:
            limit: Maximum transactions to return

        Returns:
            List of transactions sorted by priority (fee, timestamp)
        """
        ...

    def size(self) -> int:
        """
        Get current number of transactions in mempool.

        Returns:
            Transaction count
        """
        ...

    def clear(self) -> int:
        """
        Clear all transactions from mempool.

        Returns:
            Number of transactions cleared
        """
        ...


@runtime_checkable
class IValidator(Protocol):
    """
    Protocol for transaction and block validation.

    Thread Safety: Must be safe for concurrent validation calls.
    """

    def validate_transaction(self, tx: "Transaction") -> bool:
        """
        Validate a transaction.

        Args:
            tx: Transaction to validate

        Returns:
            True if valid, False otherwise

        Security:
            - Must verify signature
            - Must check balance sufficiency
            - Must validate all inputs
        """
        ...

    def validate_block(self, block: Any) -> tuple[bool, str | None]:
        """
        Validate a block for chain inclusion.

        Args:
            block: Block to validate

        Returns:
            Tuple of (is_valid, error_message)

        Security:
            - Must verify proof-of-work
            - Must validate all transactions
            - Must check coinbase reward
        """
        ...

    def validate_coinbase_reward(self, block: Any) -> tuple[bool, str | None]:
        """
        Validate coinbase transaction reward.

        Args:
            block: Block containing coinbase

        Returns:
            Tuple of (is_valid, error_message)
        """
        ...


@runtime_checkable
class IBlockchain(Protocol):
    """
    Protocol for core blockchain operations.

    Thread Safety: All state-modifying operations MUST be thread-safe.
    """

    def add_block(self, block: Any) -> bool:
        """
        Add a new block to the chain.

        Args:
            block: Block to add

        Returns:
            True if added successfully

        Security:
            - Must validate block before adding
            - Must update UTXO set atomically
        """
        ...

    def get_block(self, index: int) -> Any | None:
        """
        Get block by index.

        Args:
            index: Block height

        Returns:
            Block if found, None otherwise
        """
        ...

    def get_block_by_hash(self, block_hash: str) -> Any | None:
        """
        Get block by hash.

        Args:
            block_hash: Block hash

        Returns:
            Block if found, None otherwise
        """
        ...

    def get_latest_block(self) -> Any:
        """
        Get the latest block in the chain.

        Returns:
            Latest block
        """
        ...

    def get_chain_length(self) -> int:
        """
        Get current chain length.

        Returns:
            Number of blocks in chain
        """
        ...

    def get_balance(self, address: str) -> float:
        """
        Get balance for an address.

        Args:
            address: Address to query

        Returns:
            Balance in XAI
        """
        ...

    def add_transaction(self, tx: "Transaction") -> tuple[bool, str]:
        """
        Add transaction to mempool.

        Args:
            tx: Transaction to add

        Returns:
            Tuple of (success, message)
        """
        ...


@runtime_checkable
class IP2PNetwork(Protocol):
    """
    Protocol for peer-to-peer network operations.

    Thread Safety: Must handle concurrent peer connections safely.
    """

    def broadcast_block(self, block: Any) -> int:
        """
        Broadcast a block to all connected peers.

        Args:
            block: Block to broadcast

        Returns:
            Number of peers block was sent to
        """
        ...

    def broadcast_transaction(self, tx: "Transaction") -> int:
        """
        Broadcast a transaction to all connected peers.

        Args:
            tx: Transaction to broadcast

        Returns:
            Number of peers transaction was sent to
        """
        ...

    def get_peer_count(self) -> int:
        """
        Get number of connected peers.

        Returns:
            Peer count
        """
        ...

    def add_peer(self, peer_url: str) -> bool:
        """
        Add a peer connection.

        Args:
            peer_url: Peer URL to connect to

        Returns:
            True if connected successfully
        """
        ...

    def remove_peer(self, peer_url: str) -> bool:
        """
        Remove a peer connection.

        Args:
            peer_url: Peer URL to disconnect

        Returns:
            True if disconnected successfully
        """
        ...

    def sync_with_network(self) -> bool:
        """
        Synchronize chain state with network.

        Returns:
            True if sync successful
        """
        ...


@runtime_checkable
class IConsensus(Protocol):
    """
    Protocol for consensus mechanism operations.

    Thread Safety: Consensus decisions must be atomic.
    """

    def validate_proof_of_work(self, block: Any) -> bool:
        """
        Validate block proof-of-work.

        Args:
            block: Block to validate

        Returns:
            True if PoW is valid
        """
        ...

    def calculate_difficulty(self, chain: list[Any]) -> int:
        """
        Calculate next block difficulty.

        Args:
            chain: Current blockchain

        Returns:
            Difficulty target
        """
        ...

    def select_chain(self, chains: list[list[Any]]) -> list[Any]:
        """
        Select the canonical chain from competing chains.

        Args:
            chains: List of competing chains

        Returns:
            Selected canonical chain
        """
        ...


@runtime_checkable
class IWebhookManager(Protocol):
    """
    Protocol for webhook notification management.

    Thread Safety: Must handle concurrent event dispatches safely.
    """

    def register(
        self,
        url: str,
        events: list[str],
        owner: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Register a webhook subscription.

        Args:
            url: Webhook endpoint URL
            events: List of event types to subscribe to
            owner: Owner address
            metadata: Optional metadata

        Returns:
            Registration result with webhook_id and secret
        """
        ...

    def unregister(self, webhook_id: str, owner: str) -> bool:
        """
        Unregister a webhook subscription.

        Args:
            webhook_id: Webhook ID
            owner: Owner address (for authorization)

        Returns:
            True if unregistered successfully
        """
        ...

    def dispatch(self, event_type: str, payload: dict[str, Any]) -> int:
        """
        Dispatch an event to all subscribed webhooks.

        Args:
            event_type: Type of event
            payload: Event payload

        Returns:
            Number of webhooks notified
        """
        ...


# Type aliases for common manager patterns
UTXOSet = dict[str, list[dict[str, Any]]]
MempoolState = dict[str, "Transaction"]
BlockList = list[Any]


__all__ = [
    "IUTXOManager",
    "IMempool",
    "IValidator",
    "IBlockchain",
    "IP2PNetwork",
    "IConsensus",
    "IWebhookManager",
    "UTXOSet",
    "MempoolState",
    "BlockList",
]
