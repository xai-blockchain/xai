"""
Blockchain Orphan Processing Mixin - Handles orphan blocks and transactions.

Extracted from blockchain.py for better separation of concerns.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from xai.core.chain.blockchain_exceptions import DatabaseError, StorageError

if TYPE_CHECKING:
    from xai.core.blockchain_components.block import Block


class BlockchainOrphanMixin:
    """
    Mixin providing orphan processing functionality for the Blockchain class.

    Handles:
    - Processing orphan blocks when they can be connected to chain
    - Processing orphan transactions when UTXOs become available
    - Chain reorganization based on orphan chains with more work
    """

    def _process_orphan_blocks(self) -> None:
        """Try to connect any orphan blocks to the chain."""
        next_index = len(self.chain)

        # Keep trying to add orphan blocks as long as we find matches
        while next_index in self.orphan_blocks:
            added = False
            for orphan in self.orphan_blocks[next_index]:
                if orphan.header.previous_hash == self.chain[-1].hash:
                    # This orphan can now be connected
                    self.chain.append(orphan)
                    # P2 Performance: Update cumulative transaction count
                    self._cumulative_tx_count += len(orphan.transactions)
                    self._process_governance_block_transactions(orphan)

                    # Update UTXO set
                    for tx in orphan.transactions:
                        if tx.sender != "COINBASE":
                            self.utxo_manager.process_transaction_inputs(tx)
                        self.utxo_manager.process_transaction_outputs(tx)

                    # Index transactions for O(log n) address lookups
                    try:
                        for tx_index, tx in enumerate(orphan.transactions):
                            self.address_index.index_transaction(
                                tx,
                                orphan.index,
                                tx_index,
                                orphan.timestamp
                            )
                        self.address_index.commit()
                    except (DatabaseError, StorageError, ValueError, RuntimeError) as e:
                        self.logger.error(
                            "Failed to index orphan block transactions",
                            extra={
                                "block_index": orphan.index,
                                "error": str(e),
                                "error_type": type(e).__name__
                            }
                        )
                        try:
                            self.address_index.rollback()
                        except (DatabaseError, StorageError, RuntimeError) as rollback_err:
                            self.logger.warning(
                                "Failed to rollback address index after orphan block indexing failure",
                                extra={
                                    "block_index": orphan.index,
                                    "error": str(rollback_err),
                                    "error_type": type(rollback_err).__name__
                                }
                            )

                    # Save to disk
                    self.storage._save_block_to_disk(orphan)
                    self.storage.save_state_to_disk(
                        self.utxo_manager,
                        self.pending_transactions,
                        self.contracts,
                        self.contract_receipts,
                    )

                    # Remove from orphans
                    self.orphan_blocks[next_index].remove(orphan)
                    if not self.orphan_blocks[next_index]:
                        del self.orphan_blocks[next_index]

                    added = True
                    next_index += 1
                    break

            if not added:
                break

    def _process_orphan_transactions(self) -> None:
        """
        Try to add orphan transactions to the mempool after new blocks are added.

        Orphan transactions are those that reference UTXOs that didn't exist when they
        were first received. After new blocks are added, those UTXOs may now exist,
        so we retry validation on orphan transactions.
        """
        if not self.orphan_transactions:
            return

        # Try to validate and add each orphan transaction
        successfully_added = []
        for orphan_tx in self.orphan_transactions[:]:  # Copy list to allow modification
            # Try to validate the transaction again
            if self.transaction_validator.validate_transaction(orphan_tx):
                # Check for double-spend in pending transactions
                is_double_spend = False
                if orphan_tx.inputs:
                    for tx_input in orphan_tx.inputs:
                        input_key = f"{tx_input['txid']}:{tx_input['vout']}"
                        for pending_tx in self.pending_transactions:
                            if pending_tx.inputs:
                                for pending_input in pending_tx.inputs:
                                    pending_key = f"{pending_input['txid']}:{pending_input['vout']}"
                                    if input_key == pending_key:
                                        is_double_spend = True
                                        break
                            if is_double_spend:
                                break

                if not is_double_spend:
                    # Transaction is now valid, add to pending pool
                    self.pending_transactions.append(orphan_tx)
                    successfully_added.append(orphan_tx)
                    self.logger.info(f"Orphan transaction {orphan_tx.txid[:10]}... successfully added to mempool")

        # Remove successfully added transactions from orphan pool
        for tx in successfully_added:
            self.orphan_transactions.remove(tx)

        # Clean up very old orphan transactions (older than 24 hours)
        current_time = time.time()
        MAX_ORPHAN_AGE = 86400  # 24 hours
        self.orphan_transactions = [
            tx for tx in self.orphan_transactions
            if current_time - tx.timestamp < MAX_ORPHAN_AGE
        ]

    def _check_orphan_chains_for_reorg(self) -> bool:
        """
        Check if orphan blocks can form a chain with more cumulative work than the current chain.

        This implements the work-based fork choice rule (heaviest chain wins), which is
        more secure than length-based selection as it accounts for actual mining difficulty.

        Returns:
            True if reorganization occurred, False otherwise
        """
        if not self.orphan_blocks:
            return False

        best_candidate = None
        best_work = self._calculate_chain_work(self.chain)

        # Try to build chains starting from each possible fork point
        for fork_point_index in range(len(self.chain)):
            # Check if there are orphan blocks at the next index
            start_index = fork_point_index + 1
            if start_index not in self.orphan_blocks:
                continue

            # Try each orphan block at this position as a potential fork start
            for potential_fork_block in self.orphan_blocks[start_index]:
                # Check if this block connects to the fork point
                if fork_point_index >= 0:
                    expected_prev_hash = self.chain[fork_point_index].hash if fork_point_index < len(self.chain) else ""
                    if potential_fork_block.header.previous_hash != expected_prev_hash:
                        continue

                # Build candidate chain from this fork point
                candidate_chain = self.chain[:fork_point_index + 1].copy()
                candidate_chain.append(potential_fork_block)

                # Try to extend with more orphans
                current_index = start_index + 1
                while current_index in self.orphan_blocks:
                    added = False
                    for orphan in self.orphan_blocks[current_index]:
                        if orphan.header.previous_hash == candidate_chain[-1].hash:
                            candidate_chain.append(orphan)
                            added = True
                            break
                    if not added:
                        break
                    current_index += 1

                # Calculate cumulative work for candidate chain
                candidate_work = self._calculate_chain_work(candidate_chain)

                # Select candidate with most cumulative work (not just length)
                if candidate_work > best_work:
                    # Validate the candidate chain
                    if self._validate_chain_structure(candidate_chain):
                        best_candidate = candidate_chain
                        best_work = candidate_work

        # If we found a chain with more work, reorganize to it
        if best_candidate:
            self.logger.info(
                "Reorganizing to chain with more cumulative work",
                extra={
                    "event": "chain.reorg",
                    "current_length": len(self.chain),
                    "new_length": len(best_candidate),
                    "current_work": self._calculate_chain_work(self.chain),
                    "new_work": best_work
                }
            )
            return self.replace_chain(best_candidate)

        return False

    def _prune_orphans(self) -> None:
        """
        Remove orphan blocks that are too old to be useful.

        Orphan blocks older than a certain threshold or below the checkpoint
        height can be safely removed to free memory.
        """
        if not self.orphan_blocks:
            return

        current_height = len(self.chain)
        # Keep orphans within 100 blocks of current height
        MAX_ORPHAN_DEPTH = 100

        indices_to_remove = []
        for index in self.orphan_blocks:
            if index < current_height - MAX_ORPHAN_DEPTH:
                indices_to_remove.append(index)

        for index in indices_to_remove:
            removed_count = len(self.orphan_blocks[index])
            del self.orphan_blocks[index]
            self.logger.debug(
                f"Pruned {removed_count} orphan blocks at index {index}",
                extra={"event": "orphan.pruned", "index": index, "count": removed_count}
            )
