"""
Blockchain Serialization Module

Handles serialization and deserialization of blockchain data including:
- Block deserialization from network/disk
- Chain deserialization
- Blockchain state export/import
- Disk loading with checkpoint support
"""

from __future__ import annotations

import hashlib
import time
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

from xai.core.chain.block_header import BlockHeader
from xai.core.blockchain_components.block import Block
from xai.core.chain.blockchain_exceptions import (
    ChainReorgError,
    DatabaseError,
    StorageError,
    ValidationError,
)
from xai.core.chain.blockchain_interface import BlockchainDataProvider
from xai.core.transaction import Transaction

if TYPE_CHECKING:
    from xai.core.blockchain import Blockchain


class BlockchainSerializer:
    """Handles all blockchain serialization and deserialization operations."""

    def __init__(self, blockchain: Blockchain) -> None:
        """
        Initialize the serializer with a reference to the blockchain.

        Args:
            blockchain: The blockchain instance to serialize/deserialize
        """
        self.blockchain = blockchain

    @staticmethod
    def _transaction_from_dict(tx_data: dict[str, Any]) -> Transaction:
        """
        Convert a transaction dictionary to a Transaction object.

        Args:
            tx_data: Dictionary containing transaction data

        Returns:
            Transaction object
        """
        tx = Transaction(
            tx_data.get("sender", ""),
            tx_data.get("recipient", ""),
            tx_data.get("amount", 0.0),
            tx_data.get("fee", 0.0),
            tx_data.get("public_key"),
            tx_data.get("tx_type", "normal"),
            tx_data.get("nonce"),
            tx_data.get("inputs", []),
            tx_data.get("outputs", []),
            rbf_enabled=tx_data.get("rbf_enabled", False),
            replaces_txid=tx_data.get("replaces_txid"),
        )
        tx.timestamp = tx_data.get("timestamp", time.time())
        tx.signature = tx_data.get("signature")
        tx.txid = tx_data.get("txid") or tx.calculate_hash()
        tx.metadata = tx_data.get("metadata", {})
        return tx

    @classmethod
    def deserialize_block(cls, block_data: dict[str, Any]) -> Block:
        """
        Convert a block dictionary to a Block object.

        Handles both nested-header and flattened block formats from network/disk.

        Args:
            block_data: Dictionary containing block data

        Returns:
            Block object with header and transactions
        """
        # Accept both nested-header and flattened block dicts over the wire
        header_data = {}
        if isinstance(block_data, dict):
            header_data = dict(block_data.get("header") or {})
        if not header_data:
            header_data = {
                "index": block_data.get("index", 0),
                "previous_hash": block_data.get("previous_hash"),
                "merkle_root": block_data.get("merkle_root"),
                "timestamp": block_data.get("timestamp", time.time()),
                "difficulty": block_data.get("difficulty", 4),
                "nonce": block_data.get("nonce", 0),
                "signature": block_data.get("signature"),
                "miner_pubkey": block_data.get("miner_pubkey"),
                "version": block_data.get("version"),
            }
        # Ensure required header fields exist even when peers omit them
        header_data.setdefault("previous_hash", "0" * 64)
        header_data.setdefault("merkle_root", hashlib.sha256(b"").hexdigest())
        header_data.setdefault("timestamp", time.time())
        header_data.setdefault("difficulty", 4)
        header_data.setdefault("nonce", 0)
        header = BlockHeader(
            index=header_data.get("index", 0),
            previous_hash=header_data.get("previous_hash", "0"),
            merkle_root=header_data.get("merkle_root", "0"),
            timestamp=header_data.get("timestamp", time.time()),
            difficulty=header_data.get("difficulty", 4),
            nonce=header_data.get("nonce", 0),
            signature=header_data.get("signature"),
            miner_pubkey=header_data.get("miner_pubkey"),
            version=header_data.get("version"),
        )
        transactions = [cls._transaction_from_dict(td) for td in block_data.get("transactions", [])]
        return Block(header, transactions)

    @classmethod
    def deserialize_chain(cls, chain_data: list[dict[str, Any]]) -> list[BlockHeader]:
        """
        Convert a list of block dictionaries to a list of BlockHeaders.

        Args:
            chain_data: List of block dictionaries

        Returns:
            List of BlockHeader objects
        """
        headers = []
        for bd in chain_data:
            header_data = dict(bd.get("header") or {})
            if not header_data:
                header_data = {
                    "index": bd.get("index", 0),
                    "previous_hash": bd.get("previous_hash"),
                    "merkle_root": bd.get("merkle_root"),
                    "timestamp": bd.get("timestamp", time.time()),
                    "difficulty": bd.get("difficulty", 4),
                    "nonce": bd.get("nonce", 0),
                    "signature": bd.get("signature"),
                    "miner_pubkey": bd.get("miner_pubkey"),
                    "version": bd.get("version"),
                }
            header_data.setdefault("previous_hash", "0" * 64)
            header_data.setdefault("merkle_root", hashlib.sha256(b"").hexdigest())
            header_data.setdefault("timestamp", time.time())
            header_data.setdefault("difficulty", 4)
            header_data.setdefault("nonce", 0)
            header = BlockHeader(
                index=header_data.get("index", 0),
                previous_hash=header_data.get("previous_hash", "0"),
                merkle_root=header_data.get("merkle_root", "0"),
                timestamp=header_data.get("timestamp", time.time()),
                difficulty=header_data.get("difficulty", 4),
                nonce=header_data.get("nonce", 0),
                signature=header_data.get("signature"),
                miner_pubkey=header_data.get("miner_pubkey"),
                version=header_data.get("version"),
            )
            headers.append(header)
        return headers

    def load_from_disk(self) -> bool:
        """
        Load the blockchain state from disk with checkpoint fast-recovery.

        If a valid checkpoint exists, load from it and only validate blocks after.
        Otherwise, fall back to full chain validation.

        Returns:
            True if load successful, False otherwise
        """
        # Try to load from checkpoint first for fast recovery
        checkpoint = self.blockchain.checkpoint_manager.load_latest_checkpoint()

        if checkpoint:
            self.blockchain.logger.info(f"Found checkpoint at height {checkpoint.height}, attempting fast recovery...")
            try:
                # Restore UTXO set from checkpoint
                self.blockchain.utxo_manager.restore(checkpoint.utxo_snapshot)

                # Load chain blocks up to checkpoint
                self.blockchain.chain = []
                for i in range(checkpoint.height + 1):
                    # For fast recovery, we need to load full blocks to process UTXOs
                    block = self.blockchain.storage.load_block_from_disk(i)
                    if not block:
                        self.blockchain.logger.warn(f"Warning: Missing block {i}, falling back to full load")
                        return self.load_from_disk_full()
                    self.blockchain.chain.append(block)

                # Verify checkpoint block hash matches
                checkpoint_block = self.blockchain.chain[checkpoint.height]
                checkpoint_hash = checkpoint_block.hash if hasattr(checkpoint_block, "hash") else checkpoint_block.header.hash
                if checkpoint_hash != checkpoint.block_hash:
                    self.blockchain.logger.warn(f"Warning: Checkpoint hash mismatch, falling back to full load")
                    return self.load_from_disk_full()

                # Load remaining blocks after checkpoint
                next_index = checkpoint.height + 1
                while True:
                    block = self.blockchain.storage.load_block_from_disk(next_index)
                    if not block:
                        break

                    # Validate and apply block
                    last_block = self.blockchain.chain[-1]
                    last_hash = last_block.hash if hasattr(last_block, "hash") else last_block.header.hash
                    if block.header.previous_hash != last_hash:
                        self.blockchain.logger.warn(f"Warning: Invalid chain at block {next_index}")
                        break

                    self.blockchain.chain.append(block)

                    # Update UTXO set for blocks after checkpoint
                    for tx in block.transactions:
                        if tx.sender != "COINBASE":
                            self.blockchain.utxo_manager.process_transaction_inputs(tx)
                        self.blockchain.utxo_manager.process_transaction_outputs(tx)

                    next_index += 1

                # Load pending transactions and contracts
                loaded_state = self.blockchain.storage.load_state_from_disk()
                self.blockchain.pending_transactions = loaded_state.get("pending_transactions", [])
                self.blockchain.contracts = loaded_state.get("contracts", {})
                self.blockchain.contract_receipts = loaded_state.get("receipts", [])

                self.blockchain.logger.info(f"Fast recovery successful: loaded {len(self.blockchain.chain)} blocks "
                      f"(checkpoint at {checkpoint.height}, "
                      f"validated {len(self.blockchain.chain) - checkpoint.height - 1} new blocks)")
                return True

            except (StorageError, DatabaseError, ChainReorgError, ValidationError, OSError, ValueError) as e:
                self.blockchain.logger.error(
                    "Checkpoint recovery failed, falling back to full load",
                    extra={
                        "error": str(e),
                        "error_type": type(e).__name__
                    }
                )
                return self.load_from_disk_full()
        else:
            # No checkpoint found, do full load
            self.blockchain.logger.info("No checkpoint found, performing full blockchain load...")
            return self.load_from_disk_full()

    def load_from_disk_full(self) -> bool:
        """
        Full blockchain load without checkpoints (fallback method).

        Returns:
            True if load successful, False otherwise
        """
        loaded_state = self.blockchain.storage.load_state_from_disk()
        self.blockchain.utxo_manager.load_utxo_set(loaded_state.get("utxo_set", {}))
        if not self.blockchain.utxo_manager.verify_utxo_consistency()["is_consistent"]:
            raise Exception("UTXO set consistency check failed. Data may be corrupted.")

        self.blockchain.pending_transactions = loaded_state.get("pending_transactions", [])
        self.blockchain.contracts = loaded_state.get("contracts", {})
        self.blockchain.contract_receipts = loaded_state.get("receipts", [])

        full_chain = self.blockchain.storage.load_chain_from_disk()
        if not full_chain:
            return False

        # Store only headers in memory
        self.blockchain.chain = [block.header for block in full_chain]

        self.blockchain.logger.info(f"Full blockchain load complete: {len(self.blockchain.chain)} blocks")
        return True

    # Default batch size for paginated chain sync (100 blocks per batch)
    DEFAULT_CHAIN_SYNC_BATCH_SIZE: int = 100

    def get_blocks_range(
        self,
        start_height: int,
        end_height: int | None = None,
        limit: int | None = None,
    ) -> list[Block]:
        """
        Retrieve blocks within a height range.

        Supports two modes:
        1. Range mode: start_height to end_height (inclusive)
        2. Limit mode: start_height with max `limit` blocks

        Args:
            start_height: Starting block height (0-indexed, inclusive)
            end_height: Ending block height (inclusive). If None, uses limit.
            limit: Maximum number of blocks to return. If None, defaults to
                   DEFAULT_CHAIN_SYNC_BATCH_SIZE.

        Returns:
            List of Block objects in ascending height order.
            Empty list if start_height is beyond chain length.

        Raises:
            ValueError: If start_height is negative or end_height < start_height
        """
        if start_height < 0:
            raise ValueError("start_height must be non-negative")

        chain_length = len(self.blockchain.chain)
        if start_height >= chain_length:
            return []

        # Determine effective end based on mode
        if end_height is not None:
            if end_height < start_height:
                raise ValueError("end_height must be >= start_height")
            effective_end = min(end_height, chain_length - 1)
        else:
            batch_size = limit if limit is not None else self.DEFAULT_CHAIN_SYNC_BATCH_SIZE
            effective_end = min(start_height + batch_size - 1, chain_length - 1)

        # Load blocks, ensuring we get full blocks (not just headers)
        blocks: list[Block] = []
        for idx in range(start_height, effective_end + 1):
            block = self.blockchain.get_block(idx)
            if block is not None:
                blocks.append(block)
            else:
                # If we can't load a block, stop here to maintain contiguity
                self.blockchain.logger.warning(
                    "Failed to load block during range retrieval",
                    extra={"height": idx, "start": start_height, "end": effective_end}
                )
                break

        return blocks

    def to_dict_paginated(
        self,
        offset: int = 0,
        limit: int | None = None,
        include_pending: bool = True,
    ) -> dict[str, Any]:
        """
        Export blockchain state with paginated chain serialization.

        This method provides O(limit) serialization instead of O(n) for the
        entire chain, suitable for incremental chain sync over P2P.

        Args:
            offset: Starting block height (0-indexed)
            limit: Maximum number of blocks to include. Defaults to
                   DEFAULT_CHAIN_SYNC_BATCH_SIZE.
            include_pending: Whether to include pending transactions.
                           Set to False after first batch for efficiency.

        Returns:
            Dict containing:
            - chain: List of block dicts for the requested range
            - pending_transactions: List of pending tx dicts (if include_pending)
            - difficulty: Current difficulty
            - pagination: Metadata about the current page
            - stats: Chain statistics
        """
        effective_limit = limit if limit is not None else self.DEFAULT_CHAIN_SYNC_BATCH_SIZE
        chain_length = len(self.blockchain.chain)

        # Get blocks for this page
        blocks = self.get_blocks_range(offset, limit=effective_limit)
        serialized_blocks = [self._block_to_full_dict(block) for block in blocks]

        # Calculate pagination metadata
        has_more = (offset + len(blocks)) < chain_length
        next_offset = offset + len(blocks) if has_more else None

        result: dict[str, Any] = {
            "chain": serialized_blocks,
            "difficulty": self.blockchain.difficulty,
            "pagination": {
                "offset": offset,
                "limit": effective_limit,
                "count": len(serialized_blocks),
                "total_blocks": chain_length,
                "has_more": has_more,
                "next_offset": next_offset,
            },
            "stats": {
                "blocks": chain_length,
                "total_transactions": sum(
                    len(block.transactions) if hasattr(block, "transactions") else 0
                    for block in blocks
                ),
                "total_supply": self.blockchain.get_circulating_supply(),
                "difficulty": self.blockchain.difficulty,
            },
        }

        # Only include pending transactions on first page or when explicitly requested
        if include_pending:
            result["pending_transactions"] = [
                tx.to_dict() for tx in self.blockchain.pending_transactions
            ]

        return result

    def to_dict(self) -> dict[str, Any]:
        """
        Export the entire blockchain state to a dictionary.

        WARNING: This method has O(n) complexity where n is chain length.
        For long chains, prefer to_dict_paginated() for incremental sync.

        Returns:
            Dict containing chain, pending transactions, difficulty, and stats
        """
        return {
            "chain": [self._block_to_full_dict(block) for block in self.blockchain.chain],
            "pending_transactions": [tx.to_dict() for tx in self.blockchain.pending_transactions],
            "difficulty": self.blockchain.difficulty,
            "stats": {
                "blocks": len(self.blockchain.chain),
                "total_transactions": sum(
                    len(block.transactions) if hasattr(block, "transactions") else 0
                    for block in self.blockchain.chain
                ),
                "total_supply": self.blockchain.get_circulating_supply(),
                "difficulty": self.blockchain.difficulty,
            },
        }

    def from_dict(self, data: dict[str, Any]) -> SimpleNamespace:
        """
        Materialize a lightweight blockchain snapshot from serialized data.

        Args:
            data: Dict produced by to_dict() containing chain/pending/difficulty

        Returns:
            SimpleNamespace with `chain`, `pending_transactions`, and `difficulty`
        """
        if not isinstance(data, dict):
            raise ValueError("Serialized blockchain data must be a dict")

        raw_chain = data.get("chain") or []
        materialized_chain = []
        for block_dict in raw_chain:
            try:
                block = self.deserialize_block(block_dict)
                materialized_chain.append(block)
            except (ValueError, KeyError, TypeError) as exc:
                self.blockchain.logger.debug(
                    "Failed to deserialize block from peer data",
                    extra={
                        "error": str(exc),
                        "error_type": type(exc).__name__
                    }
                )
                return SimpleNamespace(chain=[], pending_transactions=[], difficulty=self.blockchain.difficulty)

        raw_pending = data.get("pending_transactions") or []
        pending_txs = []
        for tx_dict in raw_pending:
            try:
                pending_txs.append(self._transaction_from_dict(tx_dict))
            except (ValueError, KeyError, TypeError) as exc:
                self.blockchain.logger.debug(
                    "Failed to deserialize pending transaction from peer data",
                    extra={
                        "error": str(exc),
                        "error_type": type(exc).__name__
                    }
                )

        difficulty = data.get("difficulty", self.blockchain.difficulty)
        return SimpleNamespace(
            chain=materialized_chain,
            pending_transactions=pending_txs,
            difficulty=difficulty,
        )

    def _block_to_full_dict(self, block: Any) -> dict[str, Any]:
        """
        Convert a block (header or full) to dictionary with transactions.

        Args:
            block: Block or BlockHeader object

        Returns:
            Dictionary representation including transactions
        """
        if hasattr(block, "to_dict"):
            return block.to_dict()

        # BlockHeader doesn't have transactions - need to load full block
        full_block = self.blockchain.get_block(block.index)
        if full_block and hasattr(full_block, "to_dict"):
            return full_block.to_dict()

        # Fallback for headers
        return {
            "index": block.index,
            "hash": block.hash,
            "previous_hash": block.previous_hash,
            "timestamp": block.timestamp,
            "difficulty": block.difficulty,
            "nonce": block.nonce,
            "merkle_root": getattr(block, "merkle_root", ""),
            "transactions": [],
        }

    def get_blockchain_data_provider(self) -> BlockchainDataProvider:
        """
        Returns an object conforming to the BlockchainDataProvider interface,
        providing essential blockchain stats.

        Returns:
            BlockchainDataProvider with current blockchain metrics
        """
        # Calculate mempool size in bytes
        mempool_size = sum(tx.get_size() for tx in self.blockchain.pending_transactions) if self.blockchain.pending_transactions else 0

        return BlockchainDataProvider(
            chain_height=len(self.blockchain.chain),
            pending_transactions_count=len(self.blockchain.pending_transactions),
            orphan_blocks_count=len(self.blockchain.orphan_blocks),
            orphan_transactions_count=len(self.blockchain.orphan_transactions),
            total_circulating_supply=self.blockchain.get_circulating_supply(),
            difficulty=self.blockchain.difficulty,
            mempool_size_bytes=mempool_size,
        )
