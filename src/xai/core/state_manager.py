"""
State Manager - Handles blockchain state management
Extracted from Blockchain god class for better separation of concerns
"""

from __future__ import annotations
from typing import TYPE_CHECKING, Optional, List, Dict, Any, Tuple
import json
import os
import time

from xai.core.block_header import BlockHeader
from xai.core.transaction import Transaction
from xai.core.structured_logger import get_structured_logger

if TYPE_CHECKING:
    from xai.core.blockchain import Block, Blockchain


class StateManager:
    """
    Manages blockchain state including:
    - Chain state (adding blocks, managing tips)
    - Mempool management
    - Orphan block/transaction handling
    - State snapshots and recovery
    - Persistence coordination
    """

    def __init__(self, blockchain: 'Blockchain'):
        """
        Initialize StateManager with reference to blockchain.

        Args:
            blockchain: Parent blockchain instance
        """
        self.blockchain = blockchain
        self.logger = get_structured_logger()

    def add_block_to_chain(self, block: 'Block') -> bool:
        """
        Add validated block to the chain.

        This is the internal method that actually modifies chain state.
        Should only be called after full validation.

        Thread safety:
        - Acquires chain lock for atomic state updates
        - Updates UTXO set atomically with chain

        Args:
            block: Validated block to add

        Returns:
            True if added successfully, False otherwise
        """
        with self.blockchain._chain_lock:
            try:
                # Append block header to chain
                self.blockchain.chain.append(block.header)

                # Update UTXO set
                self._update_utxo_set(block)

                # Remove mined transactions from mempool
                self._remove_mined_transactions(block)

                # Update address index
                self._update_address_index(block)

                # Persist block to disk
                self.blockchain.storage.save_block_to_disk(block)

                # Update checkpoint if needed
                self._update_checkpoint(block)

                # Record state snapshot for debugging
                self._record_state_snapshot(f"after_block_{block.index}")

                self.logger.info(
                    "Block added to chain",
                    index=block.index,
                    hash=block.hash,
                    tx_count=len(block.transactions),
                )

                return True

            except (ValueError, KeyError, AttributeError, TypeError, RuntimeError, OSError, IOError) as e:
                self.logger.error(
                    "Failed to add block to chain",
                    index=block.index,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                return False

    def _update_utxo_set(self, block: 'Block') -> None:
        """
        Update UTXO set with block transactions.

        Processes all transactions in the block:
        - Removes spent UTXOs
        - Adds new UTXOs from outputs

        Args:
            block: Block containing transactions to process
        """
        for tx in block.transactions:
            # Remove spent inputs (except coinbase)
            if tx.sender != "COINBASE":
                self.blockchain.utxo_manager.spend_utxo(tx)

            # Add new outputs
            self.blockchain.utxo_manager.add_utxo(tx)

    def _remove_mined_transactions(self, block: 'Block') -> None:
        """
        Remove mined transactions from mempool.

        Thread-safe mempool cleanup after block is added.

        Args:
            block: Block containing mined transactions
        """
        with self.blockchain._mempool_lock:
            mined_txids = {tx.txid for tx in block.transactions if tx.txid}

            # Remove from pending transactions
            self.blockchain.pending_transactions = [
                tx for tx in self.blockchain.pending_transactions
                if tx.txid not in mined_txids
            ]

            # Update seen txids
            self.blockchain.seen_txids.update(mined_txids)

            # Update sender pending counts
            for tx in block.transactions:
                if tx.sender and tx.sender != "COINBASE":
                    if tx.sender in self.blockchain._sender_pending_count:
                        self.blockchain._sender_pending_count[tx.sender] = max(
                            0,
                            self.blockchain._sender_pending_count[tx.sender] - 1
                        )

    def _update_address_index(self, block: 'Block') -> None:
        """
        Update address transaction index with block transactions.

        Args:
            block: Block containing transactions to index
        """
        try:
            self.blockchain.address_index.index_block(block)
        except (ValueError, KeyError, AttributeError, TypeError, RuntimeError, OSError, IOError) as e:
            # Don't fail block addition if indexing fails
            self.logger.warning(
                "Failed to update address index for block",
                index=block.index,
                error=str(e),
                error_type=type(e).__name__,
            )

    def _update_checkpoint(self, block: 'Block') -> None:
        """
        Update checkpoint if at checkpoint interval.

        Args:
            block: Newly added block
        """
        try:
            self.blockchain.checkpoint_manager.maybe_create_checkpoint(
                block_height=block.index,
                blockchain=self.blockchain,
            )
        except (ValueError, KeyError, OSError, IOError, RuntimeError) as e:
            # Don't fail block addition if checkpointing fails
            self.logger.warning(
                "Failed to create checkpoint",
                block_height=block.index,
                error=str(e),
                error_type=type(e).__name__,
            )

    def process_orphan_transactions(self) -> None:
        """
        Process orphan transactions and try to add them to mempool.

        Orphan transactions reference UTXOs that didn't exist when
        they were first received. After new blocks arrive, we retry
        adding them.
        """
        if not self.blockchain.orphan_transactions:
            return

        self.logger.debug(
            "Processing orphan transactions",
            count=len(self.blockchain.orphan_transactions),
        )

        processed = []
        for tx in self.blockchain.orphan_transactions:
            # Try to validate transaction now
            if self.blockchain.transaction_validator.validate(tx):
                # Add to mempool
                if self.blockchain.add_transaction(tx):
                    processed.append(tx)
                    self.logger.info(
                        "Orphan transaction promoted to mempool",
                        txid=tx.txid,
                    )

        # Remove processed transactions
        with self.blockchain._mempool_lock:
            self.blockchain.orphan_transactions = [
                tx for tx in self.blockchain.orphan_transactions
                if tx not in processed
            ]

    def prune_expired_mempool(self) -> int:
        """
        Remove expired transactions from mempool.

        Returns:
            Number of transactions pruned
        """
        import time
        current_time = time.time()

        with self.blockchain._mempool_lock:
            initial_count = len(self.blockchain.pending_transactions)

            self.blockchain.pending_transactions = [
                tx for tx in self.blockchain.pending_transactions
                if (current_time - tx.timestamp) < self.blockchain._mempool_max_age_seconds
            ]

            pruned = initial_count - len(self.blockchain.pending_transactions)

            if pruned > 0:
                self.blockchain._mempool_expired_total += pruned
                self.logger.info(
                    "Pruned expired transactions from mempool",
                    pruned=pruned,
                    remaining=len(self.blockchain.pending_transactions),
                )

            return pruned

    def prune_orphan_pool(self) -> int:
        """
        Remove old orphan transactions.

        Returns:
            Number of orphans pruned
        """
        import time
        current_time = time.time()
        max_age = 3600  # 1 hour

        with self.blockchain._mempool_lock:
            initial_count = len(self.blockchain.orphan_transactions)

            self.blockchain.orphan_transactions = [
                tx for tx in self.blockchain.orphan_transactions
                if (current_time - tx.timestamp) < max_age
            ]

            pruned = initial_count - len(self.blockchain.orphan_transactions)

            if pruned > 0:
                self.logger.info(
                    "Pruned old orphan transactions",
                    pruned=pruned,
                    remaining=len(self.blockchain.orphan_transactions),
                )

            return pruned

    def _record_state_snapshot(self, label: str) -> None:
        """
        Record a snapshot of current blockchain state for debugging.

        Args:
            label: Description of when snapshot was taken
        """
        try:
            snapshot = {
                "label": label,
                "timestamp": time.time(),
                "chain_length": len(self.blockchain.chain),
                "mempool_size": len(self.blockchain.pending_transactions),
                "orphan_count": len(self.blockchain.orphan_transactions),
                "utxo_count": len(self.blockchain.utxo_manager.utxo_set),
            }

            self.blockchain._state_integrity_snapshots.append(snapshot)

            # Keep only last 100 snapshots
            if len(self.blockchain._state_integrity_snapshots) > 100:
                self.blockchain._state_integrity_snapshots = \
                    self.blockchain._state_integrity_snapshots[-100:]

        except (ValueError, KeyError, AttributeError, TypeError) as e:
            # Don't fail operations due to snapshot errors
            self.logger.debug(f"Failed to record state snapshot: {e}", extra={"error_type": type(e).__name__})

    def compute_state_snapshot(self) -> Dict[str, Any]:
        """
        Compute comprehensive state snapshot.

        Returns:
            Dictionary containing current blockchain state
        """
        return {
            "chain_length": len(self.blockchain.chain),
            "chain_tip": self.blockchain.chain[-1].hash if self.blockchain.chain else None,
            "mempool_size": len(self.blockchain.pending_transactions),
            "orphan_tx_count": len(self.blockchain.orphan_transactions),
            "orphan_block_count": sum(len(blocks) for blocks in self.blockchain.orphan_blocks.values()),
            "utxo_count": len(self.blockchain.utxo_manager.utxo_set),
            "difficulty": self.blockchain.difficulty,
        }

    def get_mempool_size_kb(self) -> float:
        """
        Calculate mempool size in kilobytes.

        Returns:
            Mempool size in KB
        """
        import sys

        total_bytes = sum(
            sys.getsizeof(tx) for tx in self.blockchain.pending_transactions
        )
        return total_bytes / 1024.0

    def get_mempool_overview(self, limit: int = 100) -> Dict[str, Any]:
        """
        Get detailed mempool overview.

        Args:
            limit: Maximum transactions to include

        Returns:
            Dictionary with mempool statistics and transactions
        """
        with self.blockchain._mempool_lock:
            transactions = list(self.blockchain.pending_transactions[:limit])

            tx_list = []
            for tx in transactions:
                tx_list.append({
                    "txid": tx.txid,
                    "sender": tx.sender,
                    "recipient": tx.recipient,
                    "amount": tx.amount,
                    "fee": getattr(tx, 'fee', 0.0),
                    "timestamp": tx.timestamp,
                    "type": tx.tx_type,
                })

            return {
                "total": len(self.blockchain.pending_transactions),
                "size_kb": self.get_mempool_size_kb(),
                "transactions": tx_list,
                "orphan_count": len(self.blockchain.orphan_transactions),
            }

    def get_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive blockchain statistics.

        Returns:
            Dictionary with blockchain stats
        """
        chain_length = len(self.blockchain.chain)
        latest_block = self.blockchain.get_latest_block()

        return {
            "chain_length": chain_length,
            "difficulty": self.blockchain.difficulty,
            "latest_block": {
                "index": latest_block.index,
                "hash": latest_block.hash,
                "timestamp": latest_block.timestamp,
                "tx_count": len(latest_block.transactions),
            } if latest_block else None,
            "mempool": {
                "pending": len(self.blockchain.pending_transactions),
                "orphan": len(self.blockchain.orphan_transactions),
                "size_kb": self.get_mempool_size_kb(),
            },
            "utxo": {
                "count": len(self.blockchain.utxo_manager.utxo_set),
            },
            "orphan_blocks": sum(len(blocks) for blocks in self.blockchain.orphan_blocks.values()),
        }
