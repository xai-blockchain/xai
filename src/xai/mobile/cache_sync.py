"""
Mobile Cache Differential Sync
Task 176: Implement mobile cache differential sync

This module provides efficient data synchronization for mobile wallets
using differential updates to minimize bandwidth usage.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

@dataclass
class SyncCheckpoint:
    """Checkpoint for tracking sync state"""
    block_height: int
    block_hash: str
    timestamp: float
    transaction_count: int
    balance_snapshot: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SyncCheckpoint:
        return cls(**data)

    def calculate_hash(self) -> str:
        """Calculate hash of checkpoint for verification"""
        data = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()

@dataclass
class DiffUpdate:
    """Differential update for mobile clients"""
    update_type: str  # 'new_block', 'new_tx', 'balance_change', 'utxo_update'
    timestamp: float
    data: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DiffUpdate:
        return cls(**data)

class MobileCacheSyncManager:
    """
    Manages differential synchronization for mobile wallets

    Instead of downloading entire blockchain, mobile clients download:
    1. Initial checkpoint
    2. Differential updates since checkpoint
    3. Periodic checkpoint updates
    """

    def __init__(self, blockchain=None):
        self.blockchain = blockchain
        self.checkpoints: list[SyncCheckpoint] = []
        self.updates_cache: dict[str, list[DiffUpdate]] = {}  # checkpoint_hash -> updates
        self.max_checkpoint_age = 86400  # 24 hours

    def create_checkpoint(self, addresses: list[str]) -> SyncCheckpoint:
        """
        Create a sync checkpoint for mobile client

        Args:
            addresses: List of addresses to track

        Returns:
            Sync checkpoint
        """
        if not self.blockchain:
            raise ValueError("Blockchain not initialized")

        # Get current state
        latest_block = self.blockchain.get_latest_block()

        # Calculate balance snapshot for tracked addresses
        balance_snapshot = {}
        for address in addresses:
            balance_snapshot[address] = self.blockchain.get_balance(address)

        # Count transactions involving these addresses
        tx_count = 0
        for block in self.blockchain.chain:
            for tx in block.transactions:
                if tx.sender in addresses or tx.recipient in addresses:
                    tx_count += 1

        checkpoint = SyncCheckpoint(
            block_height=latest_block.index,
            block_hash=latest_block.hash,
            timestamp=time.time(),
            transaction_count=tx_count,
            balance_snapshot=balance_snapshot
        )

        self.checkpoints.append(checkpoint)
        return checkpoint

    def get_differential_updates(
        self,
        checkpoint_hash: str,
        addresses: list[str]
    ) -> list[DiffUpdate]:
        """
        Get differential updates since checkpoint

        Args:
            checkpoint_hash: Hash of last checkpoint
            addresses: Addresses to track

        Returns:
            List of differential updates
        """
        # Check cache first
        if checkpoint_hash in self.updates_cache:
            return self.updates_cache[checkpoint_hash]

        # Find checkpoint
        checkpoint = self._find_checkpoint(checkpoint_hash)
        if not checkpoint:
            raise ValueError("Checkpoint not found")

        updates = []

        # Get blocks since checkpoint
        start_height = checkpoint.block_height + 1
        for i in range(start_height, len(self.blockchain.chain)):
            block = self.blockchain.chain[i]

            # Add block update
            updates.append(DiffUpdate(
                update_type="new_block",
                timestamp=block.timestamp,
                data={
                    "height": block.index,
                    "hash": block.hash,
                    "timestamp": block.timestamp,
                    "tx_count": len(block.transactions)
                }
            ))

            # Add relevant transactions
            for tx in block.transactions:
                if tx.sender in addresses or tx.recipient in addresses:
                    updates.append(DiffUpdate(
                        update_type="new_tx",
                        timestamp=tx.timestamp,
                        data=self._create_lightweight_tx(tx, addresses)
                    ))

                    # Add balance changes
                    if tx.sender in addresses:
                        new_balance = self.blockchain.get_balance(tx.sender)
                        updates.append(DiffUpdate(
                            update_type="balance_change",
                            timestamp=tx.timestamp,
                            data={
                                "address": tx.sender,
                                "new_balance": new_balance,
                                "change": -(tx.amount + tx.fee)
                            }
                        ))

                    if tx.recipient in addresses:
                        new_balance = self.blockchain.get_balance(tx.recipient)
                        updates.append(DiffUpdate(
                            update_type="balance_change",
                            timestamp=tx.timestamp,
                            data={
                                "address": tx.recipient,
                                "new_balance": new_balance,
                                "change": tx.amount
                            }
                        ))

        # Cache updates
        self.updates_cache[checkpoint_hash] = updates

        return updates

    def _create_lightweight_tx(self, tx: Any, addresses: list[str]) -> dict[str, Any]:
        """Create lightweight transaction data for mobile client"""
        is_sender = tx.sender in addresses
        is_recipient = tx.recipient in addresses

        return {
            "txid": tx.txid,
            "sender": tx.sender,
            "recipient": tx.recipient,
            "amount": tx.amount,
            "fee": tx.fee,
            "timestamp": tx.timestamp,
            "direction": "sent" if is_sender else "received" if is_recipient else "unknown",
            "confirmed": True  # If in blockchain, it's confirmed
        }

    def _find_checkpoint(self, checkpoint_hash: str) -> SyncCheckpoint | None:
        """Find checkpoint by hash"""
        for cp in self.checkpoints:
            if cp.calculate_hash() == checkpoint_hash:
                return cp
        return None

    def compress_updates(self, updates: list[DiffUpdate]) -> bytes:
        """
        Compress updates for bandwidth optimization

        Args:
            updates: List of updates

        Returns:
            Compressed data
        """
        import gzip

        # Convert to JSON
        data = json.dumps([u.to_dict() for u in updates], sort_keys=True)

        # Compress
        return gzip.compress(data.encode())

    def decompress_updates(self, compressed_data: bytes) -> list[DiffUpdate]:
        """
        Decompress updates

        Args:
            compressed_data: Compressed data

        Returns:
            List of updates
        """
        import gzip

        # Decompress
        data = gzip.decompress(compressed_data).decode()

        # Parse JSON
        updates_data = json.loads(data)

        return [DiffUpdate.from_dict(u) for u in updates_data]

class IncrementalSyncProtocol:
    """
    Protocol for incremental sync between mobile and full node

    Mobile client workflow:
    1. Request latest checkpoint
    2. Get differential updates since last sync
    3. Apply updates to local cache
    4. Update local checkpoint
    """

    @staticmethod
    def create_sync_request(
        last_checkpoint_hash: str | None,
        addresses: list[str],
        max_updates: int = 100
    ) -> dict[str, Any]:
        """
        Create sync request from mobile client

        Args:
            last_checkpoint_hash: Hash of last checkpoint (None for initial sync)
            addresses: Addresses to track
            max_updates: Maximum updates to retrieve

        Returns:
            Sync request data
        """
        return {
            "version": 1,
            "last_checkpoint": last_checkpoint_hash,
            "addresses": addresses,
            "max_updates": max_updates,
            "timestamp": time.time()
        }

    @staticmethod
    def create_sync_response(
        checkpoint: SyncCheckpoint,
        updates: list[DiffUpdate],
        has_more: bool = False
    ) -> dict[str, Any]:
        """
        Create sync response from full node

        Args:
            checkpoint: Current checkpoint
            updates: Differential updates
            has_more: Whether more updates are available

        Returns:
            Sync response data
        """
        return {
            "version": 1,
            "checkpoint": checkpoint.to_dict(),
            "checkpoint_hash": checkpoint.calculate_hash(),
            "updates": [u.to_dict() for u in updates],
            "update_count": len(updates),
            "has_more": has_more,
            "timestamp": time.time()
        }

    @staticmethod
    def validate_sync_response(response: dict[str, Any]) -> bool:
        """
        Validate sync response

        Args:
            response: Sync response

        Returns:
            True if valid
        """
        required_fields = ["version", "checkpoint", "checkpoint_hash", "updates"]
        for field in required_fields:
            if field not in response:
                return False

        # Verify checkpoint hash
        checkpoint = SyncCheckpoint.from_dict(response["checkpoint"])
        if checkpoint.calculate_hash() != response["checkpoint_hash"]:
            return False

        return True

class MobileCacheStorage:
    """Local storage for mobile cache"""

    def __init__(self, storage_path: str = "./mobile_cache"):
        self.storage_path = storage_path
        import os
        os.makedirs(storage_path, exist_ok=True)

        self.checkpoint_file = f"{storage_path}/checkpoint.json"
        self.cache_file = f"{storage_path}/cache.json"

    def save_checkpoint(self, checkpoint: SyncCheckpoint) -> None:
        """Save checkpoint to disk"""
        with open(self.checkpoint_file, 'w') as f:
            json.dump(checkpoint.to_dict(), f, indent=2)

    def load_checkpoint(self) -> SyncCheckpoint | None:
        """Load checkpoint from disk"""
        try:
            with open(self.checkpoint_file, 'r') as f:
                data = json.load(f)
                return SyncCheckpoint.from_dict(data)
        except FileNotFoundError:
            return None

    def save_cache(self, cache_data: dict[str, Any]) -> None:
        """Save cache data"""
        with open(self.cache_file, 'w') as f:
            json.dump(cache_data, f, indent=2)

    def load_cache(self) -> dict[str, Any]:
        """Load cache data"""
        try:
            with open(self.cache_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def apply_updates(self, updates: list[DiffUpdate]) -> None:
        """Apply differential updates to cache"""
        cache = self.load_cache()

        for update in updates:
            if update.update_type == "new_tx":
                # Add transaction to cache
                if "transactions" not in cache:
                    cache["transactions"] = []
                cache["transactions"].append(update.data)

            elif update.update_type == "balance_change":
                # Update balance
                if "balances" not in cache:
                    cache["balances"] = {}
                address = update.data["address"]
                cache["balances"][address] = update.data["new_balance"]

            elif update.update_type == "new_block":
                # Update block height
                cache["latest_block_height"] = update.data["height"]
                cache["latest_block_hash"] = update.data["hash"]

        self.save_cache(cache)

    def get_transactions(self, address: str | None = None) -> list[dict[str, Any]]:
        """Get transactions from cache"""
        cache = self.load_cache()
        transactions = cache.get("transactions", [])

        if address:
            return [
                tx for tx in transactions
                if tx["sender"] == address or tx["recipient"] == address
            ]

        return transactions

    def get_balance(self, address: str) -> float:
        """Get balance from cache"""
        cache = self.load_cache()
        balances = cache.get("balances", {})
        return balances.get(address, 0.0)

class BandwidthOptimizer:
    """Optimize bandwidth usage for mobile sync"""

    @staticmethod
    def estimate_sync_size(num_blocks: int, avg_txs_per_block: int = 10) -> int:
        """
        Estimate sync data size

        Args:
            num_blocks: Number of blocks to sync
            avg_txs_per_block: Average transactions per block

        Returns:
            Estimated size in bytes
        """
        # Rough estimates
        block_header_size = 200  # bytes
        tx_size = 300  # bytes average

        total_size = num_blocks * (block_header_size + avg_txs_per_block * tx_size)

        return total_size

    @staticmethod
    def should_use_full_sync(checkpoint_age_hours: float, threshold_hours: float = 168) -> bool:
        """
        Determine if full sync is more efficient than differential

        Args:
            checkpoint_age_hours: Age of checkpoint in hours
            threshold_hours: Threshold for switching to full sync

        Returns:
            True if full sync recommended
        """
        # If checkpoint is too old (>1 week), full sync may be more efficient
        return checkpoint_age_hours > threshold_hours

    @staticmethod
    def calculate_optimal_checkpoint_interval(
        avg_blocks_per_day: int,
        target_update_size_kb: int = 100
    ) -> int:
        """
        Calculate optimal checkpoint interval

        Args:
            avg_blocks_per_day: Average blocks per day
            target_update_size_kb: Target update size in KB

        Returns:
            Recommended checkpoint interval in blocks
        """
        # Estimate blocks until update size exceeds target
        avg_tx_per_block = 10
        tx_size = 300  # bytes
        block_size = tx_size * avg_tx_per_block

        target_size_bytes = target_update_size_kb * 1024
        blocks = target_size_bytes // block_size

        return max(100, min(blocks, 10000))  # Between 100 and 10000 blocks
