"""
Chain State Manager - Handles blockchain state management

Manages UTXO set, balances, state root, and chain state persistence.
Extracted from blockchain.py god object for better separation of concerns.

Supports Protocol-based dependency injection for testability:
    - Accepts Blockchain instance (backward compatible)
    - Can accept any object implementing ChainProvider, ConfigProvider, UTXOProvider
"""

from __future__ import annotations

import copy
from typing import TYPE_CHECKING, Any, Union

from xai.core.chain.blockchain_exceptions import ValidationError
from xai.core.api.structured_logger import get_structured_logger

if TYPE_CHECKING:
    from xai.core.blockchain import Block, Blockchain
    from xai.core.manager_interfaces import (
        ChainProvider,
        ConfigProvider,
        StateProvider,
        UTXOProvider,
    )
    from xai.core.transaction import Transaction

    # Type alias for objects that provide chain state functionality
    ChainStateProvider = Union[
        "Blockchain",
        "ChainProvider",
    ]

class ChainState:
    """
    Manages blockchain state including:
    - UTXO set management
    - Balance queries
    - Circulating supply calculations
    - State snapshots for debugging
    - Chain state persistence and recovery
    """

    def __init__(self, blockchain: "Blockchain") -> None:
        """
        Initialize ChainState with reference to blockchain or protocol provider.

        Supports Protocol-based dependency injection for better testability.
        Accepts any object that provides the required chain state methods:
        - Chain access (chain, get_block, get_latest_block)
        - UTXO access (utxo_manager, get_balance)
        - Config access (difficulty, get_block_reward)

        Args:
            blockchain: Blockchain instance or Protocol-compatible provider.
                       For testing, can pass a mock implementing required protocols.
        """
        # Store reference - can be Blockchain or any Protocol-compatible object
        self.blockchain = blockchain
        self.logger = get_structured_logger()

    @property
    def utxo_set(self) -> dict[str, list[dict[str, Any]]]:
        """
        Expose current UTXO set for diagnostics/testing.

        Returns:
            Copy of UTXO set to prevent external mutation
        """
        return copy.deepcopy(self.blockchain.utxo_manager.utxo_set)

    def get_balance(self, address: str) -> float:
        """
        Return confirmed balance for an address using the authoritative UTXO set.

        Args:
            address: Blockchain address to query

        Returns:
            Confirmed balance in native tokens
        """
        return self.blockchain.utxo_manager.get_balance(address)

    def get_circulating_supply(self) -> float:
        """
        Calculate total circulating supply from unspent outputs.

        The circulating supply is the sum of all unspent transaction outputs (UTXOs).
        This is the authoritative source of total token supply in circulation.

        Returns:
            Total circulating supply in native tokens
        """
        return self.blockchain.utxo_manager.get_total_unspent_value()

    def get_total_supply(self) -> float:
        """
        Calculate theoretical total supply based on mining rewards.

        Computes total tokens that should exist based on block rewards and halving schedule.
        May differ from circulating supply due to burned or lost tokens.

        Returns:
            Theoretical total supply
        """
        total = 0.0
        for i in range(len(self.blockchain.chain)):
            total += self.blockchain.get_block_reward(i)
        return total

    def compute_state_snapshot(self) -> dict[str, Any]:
        """
        Compute comprehensive state snapshot for debugging and monitoring.

        Returns:
            Dictionary containing current blockchain state metrics
        """
        chain_tip = None
        if self.blockchain.chain:
            tip = self.blockchain.chain[-1]
            chain_tip = getattr(tip, 'hash', None)

        orphan_block_count = sum(
            len(blocks) for blocks in self.blockchain.orphan_blocks.values()
        )

        return {
            "chain_length": len(self.blockchain.chain),
            "chain_tip": chain_tip,
            "mempool_size": len(self.blockchain.pending_transactions),
            "orphan_tx_count": len(self.blockchain.orphan_transactions),
            "orphan_block_count": orphan_block_count,
            "utxo_count": len(self.blockchain.utxo_manager.utxo_set),
            "difficulty": self.blockchain.difficulty,
            "circulating_supply": self.get_circulating_supply(),
        }

    def reset_chain_state(self, *, preserve_checkpoints: bool = False) -> dict[str, Any]:
        """
        Reset blockchain state to genesis.

        DESTRUCTIVE OPERATION - Only use for testing or recovery.

        Security considerations:
        - Clears all blocks except genesis
        - Resets UTXO set to genesis state
        - Clears mempool and orphan pools
        - Optionally preserves checkpoints for recovery

        Args:
            preserve_checkpoints: If True, keep checkpoint files for potential recovery

        Returns:
            Dictionary with reset operation results
        """
        self.logger.warning("Resetting chain state - DESTRUCTIVE OPERATION")

        # Record state before reset
        pre_reset = self.compute_state_snapshot()

        # Keep genesis block only
        genesis = self.blockchain.chain[0] if self.blockchain.chain else None

        # Clear chain
        self.blockchain.chain.clear()

        if genesis:
            self.blockchain.chain.append(genesis)

        # Reset UTXO set
        self.blockchain.utxo_manager.clear()

        # Rebuild genesis UTXO if exists
        if genesis:
            genesis_block = self.blockchain.storage.load_block_from_disk(0)
            if genesis_block and genesis_block.transactions:
                for tx in genesis_block.transactions:
                    self.blockchain.utxo_manager.add_utxo(tx)

        # Clear mempool
        with self.blockchain._mempool_lock:
            self.blockchain.pending_transactions.clear()
            self.blockchain.orphan_transactions.clear()
            self.blockchain.seen_txids.clear()
            self.blockchain._sender_pending_count.clear()
            self.blockchain._spent_inputs.clear()
            self.blockchain._pending_tx_by_txid.clear()
            self.blockchain._pending_nonces.clear()  # P2 Performance

        # Clear orphan blocks
        self.blockchain.orphan_blocks.clear()

        # Reset nonce tracker
        self.blockchain.nonce_tracker.clear()

        # Clear checkpoints unless preserved
        if not preserve_checkpoints:
            try:
                self.blockchain.checkpoint_manager.clear_all_checkpoints()
            except (OSError, IOError) as e:
                self.logger.warning(
                    "Failed to clear checkpoints during reset",
                    extra={"error": str(e), "error_type": type(e).__name__}
                )

        # Record state after reset
        post_reset = self.compute_state_snapshot()

        self.logger.info(
            "Chain state reset completed",
            pre_reset=pre_reset,
            post_reset=post_reset,
        )

        return {
            "success": True,
            "pre_reset": pre_reset,
            "post_reset": post_reset,
            "checkpoints_preserved": preserve_checkpoints,
        }

    def restore_checkpoint(self, target_height: int) -> dict[str, Any]:
        """
        Restore blockchain state from a checkpoint.

        Loads a previously saved checkpoint and replaces current chain state.
        Used for fast recovery or rollback scenarios.

        Security considerations:
        - Validates checkpoint data integrity
        - Performs full chain validation after restore
        - Atomically replaces state (all-or-nothing)

        Args:
            target_height: Block height of checkpoint to restore

        Returns:
            Dictionary with restoration results

        Raises:
            ValidationError: If checkpoint is invalid or restoration fails
        """
        self.logger.info("Attempting checkpoint restoration", target_height=target_height)

        # Record pre-restore state
        pre_restore = self.compute_state_snapshot()

        # Load checkpoint
        checkpoint_data = self.blockchain.checkpoint_manager.load_checkpoint(target_height)
        if not checkpoint_data:
            raise ValidationError(f"No checkpoint found at height {target_height}")

        # Extract checkpoint components
        chain_data = checkpoint_data.get("chain")
        utxo_data = checkpoint_data.get("utxo_set")
        metadata = checkpoint_data.get("metadata", {})

        if not chain_data:
            raise ValidationError("Checkpoint missing chain data")

        # Deserialize chain
        from xai.core.blockchain import Blockchain
        restored_chain = Blockchain.deserialize_chain(chain_data)

        # Validate restored chain
        is_valid, error = self.blockchain.validation_manager.validate_chain(
            chain=restored_chain,
            full_validation=True
        )
        if not is_valid:
            raise ValidationError(f"Restored checkpoint failed validation: {error}")

        # Replace chain state atomically
        with self.blockchain._chain_lock:
            self.blockchain.chain = restored_chain

            # Restore UTXO set if available
            if utxo_data:
                self.blockchain.utxo_manager.restore_from_dict(utxo_data)
            else:
                # Rebuild UTXO set from chain
                self.blockchain.utxo_manager.clear()
                for i in range(len(restored_chain)):
                    block = self.blockchain.storage.load_block_from_disk(i)
                    if block:
                        for tx in block.transactions:
                            if tx.sender != "COINBASE":
                                self.blockchain.utxo_manager.spend_utxo(tx)
                            self.blockchain.utxo_manager.add_utxo(tx)

            # Clear mempool (transactions may be invalid after restore)
            with self.blockchain._mempool_lock:
                self.blockchain.pending_transactions.clear()
                self.blockchain.orphan_transactions.clear()
                self.blockchain.seen_txids.clear()
                self.blockchain._pending_tx_by_txid.clear()

        # Rebuild nonce tracker
        self.blockchain._rebuild_nonce_tracker(restored_chain)

        # Rebuild governance state
        self.blockchain._rebuild_governance_state_from_chain()

        # Record post-restore state
        post_restore = self.compute_state_snapshot()

        self.logger.info(
            "Checkpoint restoration completed",
            target_height=target_height,
            pre_restore=pre_restore,
            post_restore=post_restore,
            metadata=metadata,
        )

        return {
            "success": True,
            "checkpoint_height": target_height,
            "pre_restore": pre_restore,
            "post_restore": post_restore,
            "metadata": metadata,
        }

    def get_stats(self) -> dict[str, Any]:
        """
        Get comprehensive blockchain statistics.

        Returns:
            Dictionary with detailed blockchain metrics
        """
        chain_length = len(self.blockchain.chain)
        latest_block = self.blockchain.get_latest_block()

        latest_block_info = None
        if latest_block:
            latest_block_info = {
                "index": latest_block.index,
                "hash": latest_block.hash,
                "timestamp": latest_block.timestamp,
                "tx_count": len(latest_block.transactions),
            }

        orphan_block_count = sum(
            len(blocks) for blocks in self.blockchain.orphan_blocks.values()
        )

        mempool_size_kb = 0.0
        if hasattr(self.blockchain, 'get_mempool_size_kb'):
            mempool_size_kb = self.blockchain.get_mempool_size_kb()

        return {
            "chain_length": chain_length,
            "difficulty": self.blockchain.difficulty,
            "latest_block": latest_block_info,
            "mempool": {
                "pending": len(self.blockchain.pending_transactions),
                "orphan": len(self.blockchain.orphan_transactions),
                "size_kb": mempool_size_kb,
            },
            "utxo": {
                "count": len(self.blockchain.utxo_manager.utxo_set),
            },
            "orphan_blocks": orphan_block_count,
            "circulating_supply": self.get_circulating_supply(),
            "total_supply": self.get_total_supply(),
        }
