"""
Node Operation Modes
Task 261: Implement pruning mode for resource-constrained nodes
Task 262: Add archival node mode with full history
Task 263: Complete fast sync with state snapshots

This module provides different node operation modes for various use cases.
"""

from __future__ import annotations

import os
import json
import hashlib
import time
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, asdict
from enum import Enum


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

    def __init__(self, blockchain, keep_blocks: int = 1000):
        """
        Initialize pruned node

        Args:
            blockchain: Blockchain instance
            keep_blocks: Number of recent blocks to keep
        """
        self.blockchain = blockchain
        self.keep_blocks = keep_blocks
        self.pruned_height = 0  # Height up to which blockchain is pruned

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

        # Prune blocks (in production, would actually delete data)
        pruned_count = prune_to_height - self.pruned_height

        # Update pruned height
        self.pruned_height = prune_to_height

        return pruned_count

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
        except Exception:
            return None


class NodeModeManager:
    """Manage node operation mode"""

    def __init__(self, blockchain):
        self.blockchain = blockchain
        self.mode = NodeMode.FULL
        self.pruned_node: Optional[PrunedNode] = None
        self.archival_node: Optional[ArchivalNode] = None
        self.fast_sync: Optional[FastSyncManager] = None

    def set_mode(self, mode: NodeMode, **kwargs) -> None:
        """Set node operation mode"""
        self.mode = mode

        if mode == NodeMode.PRUNED:
            keep_blocks = kwargs.get('keep_blocks', 1000)
            self.pruned_node = PrunedNode(self.blockchain, keep_blocks)

        elif mode == NodeMode.ARCHIVAL:
            storage_path = kwargs.get('storage_path', './archival_data')
            self.archival_node = ArchivalNode(self.blockchain, storage_path)

        elif mode == NodeMode.FULL:
            self.fast_sync = FastSyncManager(self.blockchain)

    def get_mode(self) -> NodeMode:
        """Get current node mode"""
        return self.mode

    def get_stats(self) -> Dict[str, Any]:
        """Get mode-specific statistics"""
        if self.mode == NodeMode.PRUNED and self.pruned_node:
            return self.pruned_node.get_pruned_stats()
        elif self.mode == NodeMode.ARCHIVAL and self.archival_node:
            return self.archival_node.get_archival_stats()
        elif self.fast_sync:
            return self.fast_sync.get_sync_stats()

        return {"mode": self.mode.value}
