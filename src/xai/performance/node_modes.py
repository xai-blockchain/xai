"""
Node Operation Modes
Task 261: Implement pruning mode for resource-constrained nodes
Task 262: Add archival node mode with full history
Task 263: Complete fast sync with state snapshots

This module provides different node operation modes for various use cases.
"""

from __future__ import annotations

import logging
import os
import json
import hashlib
import time
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, asdict
from enum import Enum

try:
    from xai.core import config
except ImportError:
    config = None

try:
    from xai.core.pruning import BlockPruningManager, PruningPolicy
except ImportError:
    BlockPruningManager = None  # type: ignore
    PruningPolicy = None  # type: ignore

logger = logging.getLogger(__name__)


class NodeMode(Enum):
    """Node operation modes"""
    FULL = "full"  # Full node with complete blockchain
    PRUNED = "pruned"  # Pruned node (recent blocks only)
    ARCHIVAL = "archival"  # Archival node (full history + indices)
    LIGHT = "light"  # Light client (headers only)


@dataclass
class StateSnapshot:
    """State snapshot for fast sync"""
    block_height: int
    block_hash: str
    timestamp: float
    account_states: Dict[str, float]  # address -> balance
    utxo_set: List[Dict[str, Any]]
    total_supply: float
    snapshot_hash: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> StateSnapshot:
        return cls(**data)

    def calculate_hash(self) -> str:
        """Calculate hash of snapshot for verification"""
        data = {
            "block_height": self.block_height,
            "block_hash": self.block_hash,
            "account_states": self.account_states,
            "utxo_set": self.utxo_set,
            "total_supply": self.total_supply
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


class PrunedNode:
    """
    Pruned node mode (Task 261)

    Keeps only recent blocks to save disk space while maintaining security.
    Suitable for resource-constrained devices.
    """

    def __init__(self, blockchain, keep_blocks: Optional[int] = None):
        """
        Initialize pruned node

        Args:
            blockchain: Blockchain instance
            keep_blocks: Number of recent blocks to keep (None = use config)
        """
        self.blockchain = blockchain

        # Use config if available and keep_blocks not explicitly provided
        if keep_blocks is None and config:
            keep_blocks = config.PRUNE_BLOCKS

        # Default to 1000 if still not set
        if keep_blocks is None or keep_blocks <= 0:
            keep_blocks = 1000

        # Enforce minimum of 100 blocks
        self.keep_blocks = max(100, keep_blocks)
        self.pruned_height = 0  # Height up to which blockchain is pruned

        logger.info(
            "PrunedNode initialized with keep_blocks=%d",
            self.keep_blocks,
            extra={"event": "pruned_node.init", "keep_blocks": self.keep_blocks}
        )

    def prune_blockchain(self) -> int:
        """
        Prune old blocks from blockchain

        Returns:
            Number of blocks pruned
        """
        chain_length = len(self.blockchain.chain)

        # Keep genesis block + recent blocks
        if chain_length <= self.keep_blocks + 1:
            return 0

        # Determine prune height
        prune_to_height = chain_length - self.keep_blocks - 1

        # Can't prune past current pruned height
        if prune_to_height <= self.pruned_height:
            return 0

        # Actually remove blocks from the chain (keep genesis block at index 0)
        # Remove blocks between pruned_height+1 and prune_to_height (inclusive)
        blocks_to_remove = prune_to_height - self.pruned_height

        # Only prune if there are blocks to remove
        if blocks_to_remove > 0:
            # Remove from index 1 up to (but not including) prune_to_height+1
            # This keeps genesis (index 0) and blocks from prune_to_height+1 onwards
            for _ in range(blocks_to_remove):
                # Always remove at index 1 (after genesis)
                if len(self.blockchain.chain) > self.keep_blocks + 1:
                    removed_block = self.blockchain.chain.pop(1)
                    logger.debug(
                        "Pruned block at height %d, hash=%s",
                        removed_block.index,
                        removed_block.hash,
                        extra={
                            "event": "pruned_node.block_pruned",
                            "height": removed_block.index,
                            "hash": removed_block.hash
                        }
                    )

            logger.info(
                "Pruned %d blocks, new chain length: %d",
                blocks_to_remove,
                len(self.blockchain.chain),
                extra={
                    "event": "pruned_node.prune_complete",
                    "pruned_count": blocks_to_remove,
                    "chain_length": len(self.blockchain.chain)
                }
            )

        # Update pruned height
        self.pruned_height = prune_to_height

        return blocks_to_remove

    def get_pruned_stats(self) -> Dict[str, Any]:
        """Get pruning statistics"""
        chain_length = len(self.blockchain.chain)
        kept_blocks = chain_length - self.pruned_height

        return {
            "mode": "pruned",
            "chain_length": chain_length,
            "pruned_height": self.pruned_height,
            "kept_blocks": kept_blocks,
            "keep_blocks_target": self.keep_blocks,
            "space_saved_percentage": (self.pruned_height / max(1, chain_length)) * 100
        }

    def is_block_available(self, height: int) -> bool:
        """Check if block at height is available"""
        if height == 0:  # Genesis always available
            return True

        return height > self.pruned_height

    def set_keep_blocks(self, count: int) -> None:
        """Set number of blocks to keep"""
        self.keep_blocks = max(100, count)  # Minimum 100 blocks


class ArchivalNode:
    """
    Archival node mode (Task 262)

    Stores complete blockchain history with additional indices
    for historical queries.
    """

    def __init__(self, blockchain, storage_path: str = "./archival_data"):
        """
        Initialize archival node

        Args:
            blockchain: Blockchain instance
            storage_path: Path for archival data
        """
        self.blockchain = blockchain
        self.storage_path = storage_path
        os.makedirs(storage_path, exist_ok=True)

        # Additional indices for archival node
        self.tx_index: Dict[str, int] = {}  # txid -> block_height
        self.address_index: Dict[str, List[str]] = {}  # address -> [txids]
        self.block_index: Dict[int, str] = {}  # height -> block_hash

        self._build_indices()

    def _build_indices(self) -> None:
        """Build archival indices"""
        for block in self.blockchain.chain:
            self.block_index[block.index] = block.hash

            for tx in block.transactions:
                # Transaction index
                self.tx_index[tx.txid] = block.index

                # Address index
                if tx.sender not in self.address_index:
                    self.address_index[tx.sender] = []
                self.address_index[tx.sender].append(tx.txid)

                if tx.recipient not in self.address_index:
                    self.address_index[tx.recipient] = []
                self.address_index[tx.recipient].append(tx.txid)

    def get_transaction_by_id(self, txid: str) -> Optional[Dict[str, Any]]:
        """Get transaction by ID from anywhere in history"""
        block_height = self.tx_index.get(txid)
        if block_height is None:
            return None

        block = self.blockchain.chain[block_height]
        for tx in block.transactions:
            if tx.txid == txid:
                return tx.to_dict()

        return None

    def get_address_history(
        self,
        address: str,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get complete transaction history for address"""
        txids = self.address_index.get(address, [])

        # Apply offset and limit
        txids = txids[offset:]
        if limit:
            txids = txids[:limit]

        # Get transactions
        transactions = []
        for txid in txids:
            tx = self.get_transaction_by_id(txid)
            if tx:
                transactions.append(tx)

        return transactions

    def get_block_by_hash(self, block_hash: str) -> Optional[Dict[str, Any]]:
        """Get block by hash"""
        for block in self.blockchain.chain:
            if block.hash == block_hash:
                return {
                    "index": block.index,
                    "hash": block.hash,
                    "previous_hash": block.previous_hash,
                    "timestamp": block.timestamp,
                    "nonce": block.nonce,
                    "difficulty": block.difficulty,
                    "transactions": [tx.to_dict() for tx in block.transactions]
                }

        return None

    def get_archival_stats(self) -> Dict[str, Any]:
        """Get archival node statistics"""
        return {
            "mode": "archival",
            "total_blocks": len(self.blockchain.chain),
            "total_transactions": len(self.tx_index),
            "indexed_addresses": len(self.address_index),
            "storage_path": self.storage_path
        }

    def export_indices(self) -> None:
        """Export indices to disk"""
        indices = {
            "tx_index": self.tx_index,
            "address_index": self.address_index,
            "block_index": self.block_index
        }

        with open(f"{self.storage_path}/indices.json", 'w') as f:
            json.dump(indices, f)

    def import_indices(self) -> bool:
        """Import indices from disk"""
        try:
            with open(f"{self.storage_path}/indices.json", 'r') as f:
                indices = json.load(f)

            self.tx_index = indices.get("tx_index", {})
            self.address_index = indices.get("address_index", {})
            self.block_index = {int(k): v for k, v in indices.get("block_index", {}).items()}

            return True
        except FileNotFoundError:
            return False


class FastSyncManager:
    """
    Fast sync with state snapshots (Task 263)

    Allows new nodes to sync quickly by downloading state snapshots
    instead of processing entire blockchain history.
    """

    def __init__(self, blockchain):
        self.blockchain = blockchain
        self.snapshot_interval = 1000  # Create snapshot every N blocks
        self.snapshots: Dict[int, StateSnapshot] = {}

    def create_snapshot(self, height: Optional[int] = None) -> StateSnapshot:
        """
        Create state snapshot at current or specified height

        Args:
            height: Block height (None for current)

        Returns:
            State snapshot
        """
        if height is None:
            height = len(self.blockchain.chain) - 1

        block = self.blockchain.chain[height]

        # Calculate account states
        account_states = {}
        for address in self._get_all_addresses():
            account_states[address] = self.blockchain.get_balance(address)

        # Get UTXO set
        utxo_set = []
        if hasattr(self.blockchain, 'utxo_manager'):
            utxo_set = self.blockchain.utxo_manager.get_all_utxos()

        # Calculate total supply
        total_supply = sum(account_states.values())

        snapshot = StateSnapshot(
            block_height=height,
            block_hash=block.hash,
            timestamp=time.time(),
            account_states=account_states,
            utxo_set=utxo_set,
            total_supply=total_supply,
            snapshot_hash=""
        )

        # Calculate snapshot hash
        snapshot.snapshot_hash = snapshot.calculate_hash()

        # Store snapshot
        self.snapshots[height] = snapshot

        return snapshot

    def _get_all_addresses(self) -> Set[str]:
        """Get all addresses that have ever transacted"""
        addresses = set()

        for block in self.blockchain.chain:
            for tx in block.transactions:
                addresses.add(tx.sender)
                addresses.add(tx.recipient)

        return addresses

    def get_latest_snapshot(self) -> Optional[StateSnapshot]:
        """Get the most recent snapshot"""
        if not self.snapshots:
            return None

        latest_height = max(self.snapshots.keys())
        return self.snapshots[latest_height]

    def apply_snapshot(self, snapshot: StateSnapshot) -> bool:
        """
        Apply a snapshot to sync blockchain state

        Args:
            snapshot: State snapshot to apply

        Returns:
            True if applied successfully
        """
        # Verify snapshot hash
        if snapshot.snapshot_hash != snapshot.calculate_hash():
            return False

        # In production, would:
        # 1. Restore account states
        # 2. Restore UTXO set
        # 3. Verify total supply
        # 4. Set blockchain height

        return True

    def fast_sync(self, snapshot: StateSnapshot, blocks_since_snapshot: List[Any]) -> bool:
        """
        Perform fast sync using snapshot + recent blocks

        Args:
            snapshot: State snapshot
            blocks_since_snapshot: Blocks after snapshot

        Returns:
            True if sync successful
        """
        # Apply snapshot
        if not self.apply_snapshot(snapshot):
            return False

        # Apply blocks since snapshot
        for block in blocks_since_snapshot:
            # In production, would validate and add block
            pass

        return True

    def should_create_snapshot(self) -> bool:
        """Check if it's time to create a snapshot"""
        height = len(self.blockchain.chain) - 1

        if not self.snapshots:
            return True

        latest_snapshot_height = max(self.snapshots.keys())
        return height - latest_snapshot_height >= self.snapshot_interval

    def get_sync_stats(self) -> Dict[str, Any]:
        """Get fast sync statistics"""
        return {
            "snapshot_count": len(self.snapshots),
            "snapshot_interval": self.snapshot_interval,
            "latest_snapshot_height": max(self.snapshots.keys()) if self.snapshots else None,
            "current_height": len(self.blockchain.chain) - 1
        }

    def export_snapshot(self, height: int, filepath: str) -> bool:
        """Export snapshot to file"""
        snapshot = self.snapshots.get(height)
        if not snapshot:
            return False

        with open(filepath, 'w') as f:
            json.dump(snapshot.to_dict(), f, indent=2)

        return True

    def import_snapshot(self, filepath: str) -> Optional[StateSnapshot]:
        """Import snapshot from file"""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)

            snapshot = StateSnapshot.from_dict(data)

            # Verify hash
            if snapshot.snapshot_hash != snapshot.calculate_hash():
                return None

            self.snapshots[snapshot.block_height] = snapshot
            return snapshot
        except Exception as e:
            logger.debug("Failed to load state snapshot: %s", e)
            return None


class NodeModeManager:
    """Manage node operation mode"""

    def __init__(self, blockchain, auto_configure: bool = True):
        """
        Initialize node mode manager

        Args:
            blockchain: Blockchain instance
            auto_configure: Automatically configure from environment (default: True)
        """
        self.blockchain = blockchain
        self.mode = NodeMode.FULL
        self.pruned_node: Optional[PrunedNode] = None
        self.archival_node: Optional[ArchivalNode] = None
        self.fast_sync: Optional[FastSyncManager] = None
        self.pruning_manager: Optional[Any] = None  # BlockPruningManager instance

        # Auto-configure from environment
        if auto_configure and config:
            self._configure_from_environment()

    def _configure_from_environment(self) -> None:
        """Configure node mode from environment variables"""
        if not config:
            return

        mode_str = config.NODE_MODE
        prune_blocks = config.PRUNE_BLOCKS

        # Initialize new BlockPruningManager if available and configured
        if BlockPruningManager and hasattr(config, 'PRUNE_MODE'):
            prune_mode = getattr(config, 'PRUNE_MODE', 'none')
            if prune_mode != 'none':
                try:
                    self.pruning_manager = BlockPruningManager(self.blockchain)
                    logger.info(
                        "BlockPruningManager initialized with mode=%s",
                        prune_mode,
                        extra={"event": "pruning_manager.init", "mode": prune_mode}
                    )
                except Exception as e:
                    logger.warning(
                        "Failed to initialize BlockPruningManager: %s",
                        str(e),
                        extra={"event": "pruning_manager.init_failed", "error": str(e)}
                    )

        # Determine mode
        if mode_str == "pruned" or (mode_str == "full" and prune_blocks > 0):
            self.set_mode(NodeMode.PRUNED, keep_blocks=prune_blocks)
            logger.info(
                "Node configured in PRUNED mode, keeping %d blocks",
                prune_blocks,
                extra={"event": "node_mode.configured", "mode": "pruned", "keep_blocks": prune_blocks}
            )
        elif mode_str == "archival":
            self.set_mode(NodeMode.ARCHIVAL)
            logger.info(
                "Node configured in ARCHIVAL mode",
                extra={"event": "node_mode.configured", "mode": "archival"}
            )
        elif mode_str == "light":
            self.set_mode(NodeMode.LIGHT)
            logger.info(
                "Node configured in LIGHT mode",
                extra={"event": "node_mode.configured", "mode": "light"}
            )
        else:
            self.set_mode(NodeMode.FULL)
            logger.info(
                "Node configured in FULL mode",
                extra={"event": "node_mode.configured", "mode": "full"}
            )

    def set_mode(self, mode: NodeMode, **kwargs) -> None:
        """Set node operation mode"""
        self.mode = mode

        if mode == NodeMode.PRUNED:
            keep_blocks = kwargs.get('keep_blocks')
            self.pruned_node = PrunedNode(self.blockchain, keep_blocks)

        elif mode == NodeMode.ARCHIVAL:
            storage_path = kwargs.get('storage_path', './archival_data')
            self.archival_node = ArchivalNode(self.blockchain, storage_path)

        elif mode == NodeMode.FULL:
            self.fast_sync = FastSyncManager(self.blockchain)

    def get_mode(self) -> NodeMode:
        """Get current node mode"""
        return self.mode

    def on_new_block(self, block) -> None:
        """
        Called when a new block is added to the chain.
        Performs mode-specific actions like auto-pruning.

        Args:
            block: The newly added block
        """
        if self.mode == NodeMode.PRUNED and self.pruned_node:
            # Auto-prune old blocks
            pruned_count = self.pruned_node.prune_blockchain()
            if pruned_count > 0:
                logger.info(
                    "Auto-pruned %d blocks after new block %d",
                    pruned_count,
                    block.index,
                    extra={
                        "event": "node_mode.auto_prune",
                        "pruned_count": pruned_count,
                        "new_block_height": block.index
                    }
                )

        elif self.mode == NodeMode.ARCHIVAL and self.archival_node:
            # Update archival indices
            self.archival_node._build_indices()

        elif self.mode == NodeMode.FULL and self.fast_sync:
            # Check if we should create a snapshot
            if self.fast_sync.should_create_snapshot():
                snapshot = self.fast_sync.create_snapshot()
                logger.info(
                    "Created state snapshot at height %d",
                    snapshot.block_height,
                    extra={
                        "event": "node_mode.snapshot_created",
                        "height": snapshot.block_height,
                        "hash": snapshot.snapshot_hash
                    }
                )

    def get_stats(self) -> Dict[str, Any]:
        """Get mode-specific statistics"""
        if self.mode == NodeMode.PRUNED and self.pruned_node:
            return self.pruned_node.get_pruned_stats()
        elif self.mode == NodeMode.ARCHIVAL and self.archival_node:
            return self.archival_node.get_archival_stats()
        elif self.fast_sync:
            return self.fast_sync.get_sync_stats()

        return {"mode": self.mode.value}
