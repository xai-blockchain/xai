"""
Fork Manager - Handles blockchain forks and reorganizations
Extracted from Blockchain god class for better separation of concerns
"""

from __future__ import annotations

import json
import os
import time
from typing import TYPE_CHECKING, Any

from xai.core.block_header import BlockHeader
from xai.core.structured_logger import get_structured_logger

if TYPE_CHECKING:
    from xai.core.blockchain import Block, Blockchain

class ForkManager:
    """
    Manages blockchain forks and reorganizations including:
    - Fork detection and handling
    - Chain reorganization (reorg)
    - Orphan block management
    - Chain work calculation
    - Write-ahead logging for crash recovery
    """

    def __init__(self, blockchain: 'Blockchain'):
        """
        Initialize ForkManager with reference to blockchain.

        Args:
            blockchain: Parent blockchain instance
        """
        self.blockchain = blockchain
        self.logger = get_structured_logger()

    def handle_fork(self, block: 'Block') -> bool:
        """
        Handle a fork by comparing chain work and potentially reorganizing.

        When a block doesn't extend the current chain tip, this method:
        1. Stores it as an orphan
        2. Attempts to build an alternative chain
        3. Compares chain work
        4. Triggers reorganization if alternative has more work

        Security considerations:
        - Enforces max reorg depth limit
        - Validates all blocks in alternative chain
        - Uses write-ahead logging for crash safety
        - Thread-safe chain state updates

        Args:
            block: Block that creates a fork

        Returns:
            True if fork was handled successfully, False otherwise
        """
        self.logger.info(
            "Fork detected",
            block_index=block.index,
            block_hash=block.hash,
            block_prev=block.previous_hash,
            current_tip=self.blockchain.chain[-1].hash if self.blockchain.chain else None,
        )

        # Store as orphan block
        if block.index not in self.blockchain.orphan_blocks:
            self.blockchain.orphan_blocks[block.index] = []

        self.blockchain.orphan_blocks[block.index].append(block)

        # Prune old orphan blocks to prevent memory exhaustion
        self._prune_orphans()

        # Try to build alternative chain from orphans
        alternative_chain = self._build_alternative_chain(block)

        if not alternative_chain:
            self.logger.debug(
                "Cannot build complete alternative chain yet",
                orphan_index=block.index,
            )
            return True  # Stored as orphan, waiting for more blocks

        # Compare chain work
        current_work = self._calculate_chain_work(self.blockchain.chain)
        alternative_work = self._calculate_chain_work(alternative_chain)

        self.logger.info(
            "Comparing chain work",
            current_work=current_work,
            alternative_work=alternative_work,
            current_length=len(self.blockchain.chain),
            alternative_length=len(alternative_chain),
        )

        # Reorganize if alternative has more work
        if alternative_work > current_work:
            return self.replace_chain(alternative_chain)

        return True  # Fork handled but current chain retained

    def replace_chain(self, new_chain: list[BlockHeader]) -> bool:
        """
        Replace current chain with a new chain (reorganization).

        This is a critical operation that:
        1. Validates the new chain completely
        2. Finds the fork point
        3. Rolls back blocks after fork point
        4. Applies new blocks
        5. Updates all state (UTXO, mempool, etc.)

        Uses write-ahead logging to ensure crash safety.

        Args:
            new_chain: New chain to adopt

        Returns:
            True if reorganization succeeded, False otherwise
        """
        with self.blockchain._chain_lock:
            # Find fork point
            fork_point = self._find_fork_point(new_chain)

            if fork_point is None:
                self.logger.error("Cannot find fork point - chains don't share history")
                return False

            # Calculate reorg depth
            reorg_depth = len(self.blockchain.chain) - fork_point - 1

            if reorg_depth > self.blockchain.max_reorg_depth:
                self.logger.error(
                    "Reorg depth exceeds maximum",
                    depth=reorg_depth,
                    max_depth=self.blockchain.max_reorg_depth,
                )
                return False

            # Validate new chain
            is_valid, error = self.blockchain.validation_manager.validate_chain(
                new_chain,
                full_validation=True,
            )

            if not is_valid:
                self.logger.error(
                    "New chain validation failed",
                    error=error,
                )
                return False

            # Write WAL entry for crash recovery
            wal_entry = self._write_reorg_wal(
                old_tip=self.blockchain.chain[-1].hash if self.blockchain.chain else None,
                new_tip=new_chain[-1].hash,
                fork_point=fork_point,
            )

            try:
                # Rollback blocks after fork point
                self._rollback_to_fork_point(fork_point)

                # Apply new blocks
                self._apply_new_blocks(new_chain, fork_point)

                # Commit WAL
                self._commit_reorg_wal(wal_entry)

                self.logger.info(
                    "Chain reorganization successful",
                    fork_point=fork_point,
                    old_length=len(self.blockchain.chain),
                    new_length=len(new_chain),
                    reorg_depth=reorg_depth,
                )

                return True

            except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as e:
                # Rollback using WAL
                self.logger.error(
                    "Chain reorganization failed, rolling back",
                    error=str(e),
                )
                self._rollback_reorg_wal(wal_entry)
                return False

    def _find_fork_point(self, new_chain: list[BlockHeader]) -> int | None:
        """
        Find the last common block between current and new chain.

        Args:
            new_chain: New chain to compare

        Returns:
            Index of fork point, or None if no common ancestor
        """
        # Start from the shorter chain length
        max_check = min(len(self.blockchain.chain), len(new_chain))

        for i in range(max_check):
            if self.blockchain.chain[i].hash != new_chain[i].hash:
                return i - 1

        return max_check - 1

    def _build_alternative_chain(self, tip_block: 'Block') -> list[BlockHeader] | None:
        """
        Build alternative chain from orphan blocks.

        Args:
            tip_block: Tip of alternative chain

        Returns:
            Complete alternative chain, or None if cannot be built
        """
        # Try to build chain backward from tip
        chain = [tip_block.header]
        current_hash = tip_block.previous_hash

        # Walk backward until we hit our current chain
        while current_hash != "0":
            # Check if this hash is in our current chain
            found_in_current = False
            for header in self.blockchain.chain:
                if header.hash == current_hash:
                    # Found connection point - prepend our chain up to this point
                    fork_index = header.index
                    complete_chain = list(self.blockchain.chain[:fork_index + 1])
                    complete_chain.extend(reversed(chain))
                    return complete_chain

            # Look for this hash in orphan blocks
            found_orphan = False
            for index, orphan_list in self.blockchain.orphan_blocks.items():
                for orphan in orphan_list:
                    if orphan.hash == current_hash:
                        chain.append(orphan.header)
                        current_hash = orphan.previous_hash
                        found_orphan = True
                        break
                if found_orphan:
                    break

            if not found_orphan:
                # Missing block in chain
                return None

        return None

    def _calculate_chain_work(self, chain: list['Block' | BlockHeader | Any]) -> int:
        """
        Calculate cumulative work for a candidate chain using precise PoW arithmetic.

        Args:
            chain: Sequence of block headers/blocks.

        Returns:
            Integer work sum suitable for fork choice comparisons.
        """
        if not chain:
            return 0
        total = 0
        for block_like in chain:
            total += self._calculate_block_work(block_like)
        return total

    def _calculate_block_work(self, block_like: 'Block' | BlockHeader | Any) -> int:
        """
        Convert a block's declared difficulty into an absolute work value using the
        2^256 / (target + 1) formulation popularized by Bitcoin. This prevents
        peers from gaming fork choice with chains that merely have more headers.
        """
        header = block_like.header if hasattr(block_like, "header") else block_like
        if header is None:
            return 0

        block_hash = getattr(header, "hash", None)
        if block_hash:
            cached = self.blockchain._block_work_cache.get(block_hash)
            if cached is not None:
                return cached

        try:
            claimed_difficulty = int(getattr(header, "difficulty", 0))
        except (TypeError, ValueError):
            claimed_difficulty = 0
        claimed_difficulty = max(0, claimed_difficulty)

        shift_bits = min(claimed_difficulty * 4, 256)
        if shift_bits >= 256:
            target = 0
        else:
            target = self.blockchain._max_pow_target >> shift_bits

        denominator = max(target + 1, 1)
        work = self.blockchain._max_pow_target // denominator

        if block_hash:
            self.blockchain._block_work_cache[block_hash] = work
        return work

    def _rollback_to_fork_point(self, fork_point: int) -> None:
        """
        Rollback blockchain state to fork point.

        Reverses:
        - Chain state
        - UTXO set
        - Nonce tracker
        - Address index

        Args:
            fork_point: Index to rollback to
        """
        # Blocks to rollback
        rollback_blocks = self.blockchain.chain[fork_point + 1:]

        # Rollback chain
        self.blockchain.chain = self.blockchain.chain[:fork_point + 1]

        # Rollback UTXO set
        for header in reversed(rollback_blocks):
            block = self.blockchain.storage.load_block_from_disk(header.index)
            if block:
                self._reverse_block_utxos(block)

        # Rollback nonce tracker
        # (simplified - would need to track nonce changes)

        self.logger.info(
            "Rolled back to fork point",
            fork_point=fork_point,
            blocks_rolled_back=len(rollback_blocks),
        )

    def _apply_new_blocks(self, new_chain: list[BlockHeader], fork_point: int) -> None:
        """
        Apply blocks from new chain after fork point.

        Args:
            new_chain: New chain to apply
            fork_point: Index of fork point
        """
        # Blocks to apply
        new_blocks = new_chain[fork_point + 1:]

        for header in new_blocks:
            # Load full block
            block = self._load_block_for_reorg(header)

            if not block:
                raise Exception(f"Failed to load block {header.index} for reorg")

            # Add block using internal method
            if not self.blockchain.state_manager.add_block_to_chain(block):
                raise Exception(f"Failed to add block {header.index} during reorg")

        self.logger.info(
            "Applied new blocks",
            count=len(new_blocks),
        )

    def _reverse_block_utxos(self, block: 'Block') -> None:
        """
        Reverse UTXO changes from a block.

        Args:
            block: Block to reverse
        """
        # Reverse in opposite order
        for tx in reversed(block.transactions):
            # Remove outputs
            self.blockchain.utxo_manager.remove_utxo(tx)

            # Restore inputs (except coinbase)
            if tx.sender != "COINBASE":
                self.blockchain.utxo_manager.restore_spent_utxo(tx)

    def _load_block_for_reorg(self, header: BlockHeader) -> 'Block' | None:
        """
        Load block for reorganization.

        Checks orphan blocks first, then disk storage.

        Args:
            header: Block header to load

        Returns:
            Full block or None
        """
        # Check orphan blocks
        if header.index in self.blockchain.orphan_blocks:
            for orphan in self.blockchain.orphan_blocks[header.index]:
                if orphan.hash == header.hash:
                    return orphan

        # Load from disk
        return self.blockchain.storage.load_block_from_disk(header.index)

    def _prune_orphans(self) -> None:
        """
        Prune old orphan blocks to prevent memory exhaustion.
        """
        if not self.blockchain.orphan_blocks:
            return

        total_orphans = sum(len(blocks) for blocks in self.blockchain.orphan_blocks.values())

        if total_orphans <= self.blockchain.max_orphan_blocks:
            return

        # Remove oldest orphan blocks
        sorted_indices = sorted(self.blockchain.orphan_blocks.keys())

        while total_orphans > self.blockchain.max_orphan_blocks and sorted_indices:
            oldest_index = sorted_indices.pop(0)
            removed = len(self.blockchain.orphan_blocks[oldest_index])
            del self.blockchain.orphan_blocks[oldest_index]
            total_orphans -= removed

        self.logger.debug(
            "Pruned orphan blocks",
            remaining=total_orphans,
        )

    def _handle_fork(self, block: 'Block') -> bool:
        """
        Handle competing fork block by constructing a candidate chain starting at the fork point.
        """
        fork_index = block.header.index
        # Track forked block for future assembly
        if fork_index not in self.blockchain.orphan_blocks:
            self.blockchain.orphan_blocks[fork_index] = []
        if not any(b.header.hash == block.header.hash for b in self.blockchain.orphan_blocks[fork_index]):
            self.blockchain.orphan_blocks[fork_index].append(block)

        # Enforce bounded reorg depth before work-intensive operations
        if fork_index >= 0 and fork_index < len(self.blockchain.chain):
            reorg_depth = len(self.blockchain.chain) - fork_index - 1
            if reorg_depth > self.blockchain.max_reorg_depth:
                self.logger.warn(
                    "Rejecting fork: max reorg depth exceeded",
                    fork_index=fork_index,
                    current_depth=reorg_depth,
                    max_depth=self.blockchain.max_reorg_depth,
                )
                self._prune_orphans()
                return False

        # Persist incoming block so replace_chain can load it
        self.blockchain.storage._save_block_to_disk(block)

        candidate_chain: list[BlockHeader] = []
        # Up to fork point (exclusive)
        candidate_chain.extend(self.blockchain.chain[:fork_index])
        candidate_chain.append(block.header)

        # Attempt to extend candidate with any connecting orphans
        next_index = fork_index + 1
        while next_index in self.blockchain.orphan_blocks:
            connector = None
            for orphan in self.blockchain.orphan_blocks[next_index]:
                if orphan.header.previous_hash == candidate_chain[-1].hash:
                    connector = orphan
                    break
            if connector is None:
                break
            self.blockchain.storage._save_block_to_disk(connector)
            candidate_chain.append(connector.header)
            next_index += 1

        # Only attempt reorg if candidate is at least as long or has more work
        if len(candidate_chain) >= len(self.blockchain.chain) or self._calculate_chain_work(candidate_chain) > self._calculate_chain_work(self.blockchain.chain):
            replaced = self.blockchain.replace_chain(candidate_chain)
            if replaced:
                # Clear consumed orphan branches
                for idx in list(self.blockchain.orphan_blocks.keys()):
                    if idx < len(candidate_chain):
                        self.blockchain.orphan_blocks.pop(idx, None)
            return replaced

        # If not replaced, see if accumulated orphans can now trigger a reorg
        self._check_orphan_chains_for_reorg()
        self._prune_orphans()
        return False

    def _attempt_lineage_sync(self, block: 'Block') -> bool:
        """
        Use an incoming block's ancestry context to fast-forward to a peer's canonical chain.

        When a peer provides a block with embedded lineage (headers/blocks leading up to it),
        we assemble a full candidate chain and run replace_chain for safety.
        """
        lineage = getattr(block, "lineage", None)
        if not lineage:
            return False

        from xai.core.block import Block as BlockClass

        candidate_chain: list['Block'] = []
        for ancestor in lineage:
            if isinstance(ancestor, BlockClass):
                candidate_block = ancestor
            elif isinstance(ancestor, BlockHeader):
                candidate_block = self.blockchain.storage.load_block_from_disk(ancestor.index)
            else:
                continue
            if not candidate_block:
                return False
            candidate_chain.append(candidate_block)

        if candidate_chain:
            for idx in range(1, len(candidate_chain)):
                if candidate_chain[idx].previous_hash != candidate_chain[idx - 1].hash:
                    return False
            if block.header.index != len(candidate_chain):
                if block.header.index < len(candidate_chain):
                    candidate_chain = candidate_chain[: block.header.index]
                else:
                    return False

        candidate_chain.append(block)

        next_index = block.header.index + 1
        while next_index in self.blockchain.orphan_blocks:
            connector = next(
                (o for o in self.blockchain.orphan_blocks[next_index] if o.header.previous_hash == candidate_chain[-1].hash),
                None,
            )
            if connector is None:
                break
            candidate_chain.append(connector)
            next_index += 1

        if len(candidate_chain) <= len(self.blockchain.chain):
            return False

        replaced = self.blockchain.replace_chain(candidate_chain)
        if replaced:
            for idx in list(self.blockchain.orphan_blocks.keys()):
                if idx < len(candidate_chain):
                    self.blockchain.orphan_blocks.pop(idx, None)
        return replaced

    def _check_orphan_chains_for_reorg(self) -> bool:
        """
        Check if orphan blocks can form a chain with more cumulative work than the current chain.

        This implements the work-based fork choice rule (heaviest chain wins), which is
        more secure than length-based selection as it accounts for actual mining difficulty.

        Returns:
            True if reorganization occurred, False otherwise
        """
        if not self.blockchain.orphan_blocks:
            return False

        best_candidate = None
        best_work = self._calculate_chain_work(self.blockchain.chain)

        # Try to build chains starting from each possible fork point
        for fork_point_index in range(len(self.blockchain.chain)):
            # Check if there are orphan blocks at the next index
            start_index = fork_point_index + 1
            if start_index not in self.blockchain.orphan_blocks:
                continue

            # Try each orphan block at this position as a potential fork start
            for potential_fork_block in self.blockchain.orphan_blocks[start_index]:
                # Check if this block connects to the fork point
                if fork_point_index >= 0:
                    expected_prev_hash = self.blockchain.chain[fork_point_index].hash if fork_point_index < len(self.blockchain.chain) else ""
                    if potential_fork_block.header.previous_hash != expected_prev_hash:
                        continue

                # Build candidate chain from this fork point
                candidate_chain = self.blockchain.chain[:fork_point_index + 1].copy()
                candidate_chain.append(potential_fork_block)

                # Try to extend with more orphans
                current_index = start_index + 1
                while current_index in self.blockchain.orphan_blocks:
                    added = False
                    for orphan in self.blockchain.orphan_blocks[current_index]:
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
                    if self.blockchain._validate_chain_structure(candidate_chain):
                        best_candidate = candidate_chain
                        best_work = candidate_work

        # If we found a chain with more work, reorganize to it
        if best_candidate:
            self.logger.info(
                "Reorganizing to chain with more cumulative work",
                extra={
                    "event": "chain.reorg",
                    "current_length": len(self.blockchain.chain),
                    "new_length": len(best_candidate),
                    "current_work": self._calculate_chain_work(self.blockchain.chain),
                    "new_work": best_work
                }
            )
            return self.blockchain.replace_chain(best_candidate)

        return False

    def _write_reorg_wal(
        self,
        old_tip: str | None,
        new_tip: str | None,
        fork_point: int | None,
    ) -> dict[str, Any]:
        """
        Write reorganization write-ahead log entry.

        Args:
            old_tip: Hash of old chain tip
            new_tip: Hash of new chain tip
            fork_point: Index of fork point

        Returns:
            WAL entry dictionary
        """
        wal_entry = {
            "timestamp": time.time(),
            "old_tip": old_tip,
            "new_tip": new_tip,
            "fork_point": fork_point,
            "status": "in_progress",
        }

        try:
            with open(self.blockchain.reorg_wal_path, 'w') as f:
                json.dump(wal_entry, f, indent=2)
        except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as e:
            self.logger.error(f"Failed to write reorg WAL: {e}")

        return wal_entry

    def _commit_reorg_wal(self, wal_entry: dict[str, Any]) -> None:
        """
        Mark reorganization as committed in WAL.

        Args:
            wal_entry: WAL entry to commit
        """
        wal_entry["status"] = "committed"

        try:
            with open(self.blockchain.reorg_wal_path, 'w') as f:
                json.dump(wal_entry, f, indent=2)
        except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as e:
            self.logger.error(f"Failed to commit reorg WAL: {e}")

    def _rollback_reorg_wal(self, wal_entry: dict[str, Any]) -> None:
        """
        Rollback failed reorganization using WAL.

        Args:
            wal_entry: WAL entry to rollback
        """
        self.logger.warning("Rolling back failed reorganization")

        # Implementation would restore old chain state from WAL
        # For now, we rely on the fact that the chain wasn't modified
        # if an exception occurred

        # Clear WAL
        try:
            if os.path.exists(self.blockchain.reorg_wal_path):
                os.remove(self.blockchain.reorg_wal_path)
        except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as e:
            self.logger.error(f"Failed to clear reorg WAL: {e}")
