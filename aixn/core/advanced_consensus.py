"""
XAI Blockchain - Advanced Consensus Features

Medium Priority Security/Robustness Features:
- Block propagation monitoring
- Orphan block handling
- Transaction ordering rules
- Finality mechanism
- Difficulty adjustment algorithm
"""

import time
import hashlib
from typing import Dict, List, Optional, Tuple
from collections import defaultdict, deque
from enum import Enum


class BlockStatus(Enum):
    """Block validation status"""
    VALID = "valid"
    ORPHAN = "orphan"
    INVALID = "invalid"
    PENDING = "pending"


class BlockPropagationMonitor:
    """
    Monitor block propagation across the network

    Tracks:
    - Block propagation times
    - Network latency
    - Peer performance
    """

    def __init__(self):
        self.block_first_seen = {}  # block_hash -> timestamp
        self.block_propagation_times = defaultdict(list)  # peer_url -> [propagation_times]
        self.peer_latency = defaultdict(float)  # peer_url -> avg_latency
        self.propagation_history = deque(maxlen=1000)  # Recent propagation events

    def record_block_first_seen(self, block_hash: str):
        """
        Record when a block was first seen by this node

        Args:
            block_hash: Block hash
        """
        if block_hash not in self.block_first_seen:
            self.block_first_seen[block_hash] = time.time()

    def record_block_from_peer(self, block_hash: str, peer_url: str):
        """
        Record receiving a block from a peer

        Args:
            block_hash: Block hash
            peer_url: Peer URL that sent the block
        """
        current_time = time.time()

        if block_hash in self.block_first_seen:
            # Calculate propagation time
            propagation_time = current_time - self.block_first_seen[block_hash]
            self.block_propagation_times[peer_url].append(propagation_time)

            # Update peer latency (exponential moving average)
            if peer_url in self.peer_latency:
                self.peer_latency[peer_url] = 0.7 * self.peer_latency[peer_url] + 0.3 * propagation_time
            else:
                self.peer_latency[peer_url] = propagation_time

            # Record in history
            self.propagation_history.append({
                'block_hash': block_hash,
                'peer': peer_url,
                'propagation_time': propagation_time,
                'timestamp': current_time
            })

    def get_peer_performance(self, peer_url: str) -> Dict:
        """
        Get performance metrics for a peer

        Args:
            peer_url: Peer URL

        Returns:
            dict: Performance metrics
        """
        if peer_url not in self.block_propagation_times:
            return {
                'avg_latency': None,
                'block_count': 0,
                'performance_score': 0
            }

        times = self.block_propagation_times[peer_url]
        avg_latency = sum(times) / len(times)

        # Performance score (lower latency = higher score)
        # Score: 100 for instant, decreasing with latency
        performance_score = max(0, 100 - (avg_latency * 10))

        return {
            'avg_latency': avg_latency,
            'block_count': len(times),
            'performance_score': performance_score
        }

    def get_network_stats(self) -> Dict:
        """Get overall network propagation statistics"""
        if not self.propagation_history:
            return {
                'avg_propagation_time': 0,
                'total_blocks_tracked': 0,
                'active_peers': 0
            }

        all_times = [event['propagation_time'] for event in self.propagation_history]

        return {
            'avg_propagation_time': sum(all_times) / len(all_times),
            'min_propagation_time': min(all_times),
            'max_propagation_time': max(all_times),
            'total_blocks_tracked': len(self.block_first_seen),
            'active_peers': len(self.peer_latency)
        }


class OrphanBlockPool:
    """
    Handle orphan blocks (blocks received before their parent)

    Orphan blocks are temporarily stored until their parent arrives
    """

    def __init__(self, max_orphans: int = 100, max_orphan_age: int = 3600):
        self.orphan_blocks = {}  # block_hash -> block
        self.orphan_by_parent = defaultdict(list)  # parent_hash -> [orphan_blocks]
        self.orphan_by_previous = self.orphan_by_parent
        self.max_orphans = max_orphans
        self.orphan_timestamps = {}  # block_hash -> timestamp
        self.orphan_timeout = max_orphan_age

    def add_orphan(self, block, parent_hash: Optional[str] = None) -> bool:
        """
        Add orphan block to pool

        Args:
            block: Orphan block
            parent_hash: Hash of missing parent block (optional)

        Returns:
            bool: Successfully added
        """
        # Check pool size limit
        if len(self.orphan_blocks) >= self.max_orphans:
            self._remove_oldest_orphan()

        block_hash = block.hash
        if parent_hash is None:
            parent_hash = getattr(block, 'previous_hash', None)

        # Store orphan
        self.orphan_blocks[block_hash] = block
        self.orphan_by_parent[parent_hash].append(block)
        self.orphan_timestamps[block_hash] = time.time()

        return True

    def get_orphans_by_parent(self, parent_hash: str) -> List:
        """
        Get orphan blocks that depend on a specific parent

        Args:
            parent_hash: Parent block hash

        Returns:
            list: Orphan blocks
        """
        return self.orphan_by_parent.get(parent_hash, [])

    def get_orphan(self, block_hash: str):
        """Get a specific orphan block"""
        return self.orphan_blocks.get(block_hash)

    def get_orphans_by_previous(self, previous_hash: str) -> List:
        """Get orphans indexed by previous hash (legacy alias)"""
        return self.get_orphans_by_parent(previous_hash)

    def remove_orphan(self, block_hash: str):
        """Remove orphan block from pool"""
        if block_hash in self.orphan_blocks:
            block = self.orphan_blocks[block_hash]
            parent_hash = block.previous_hash

            # Remove from storage
            del self.orphan_blocks[block_hash]
            self.orphan_timestamps.pop(block_hash, None)

            # Remove from parent index
            if parent_hash in self.orphan_by_parent:
                self.orphan_by_parent[parent_hash] = [
                    b for b in self.orphan_by_parent[parent_hash]
                    if b.hash != block_hash
                ]

            return block

    def _remove_oldest_orphan(self):
        """Remove oldest orphan to make space"""
        if not self.orphan_timestamps:
            return

        # Find oldest orphan
        oldest_hash = min(self.orphan_timestamps.items(), key=lambda x: x[1])[0]
        self.remove_orphan(oldest_hash)

    def cleanup_expired_orphans(self):
        """Remove orphans that have timed out"""
        current_time = time.time()
        expired = [
            block_hash for block_hash, timestamp in self.orphan_timestamps.items()
            if current_time - timestamp > self.orphan_timeout
        ]

        for block_hash in expired:
            self.remove_orphan(block_hash)

    def get_stats(self) -> Dict:
        """Get orphan pool statistics"""
        return {
            'total_orphans': len(self.orphan_blocks),
            'max_capacity': self.max_orphans,
            'parents_tracked': len(self.orphan_by_parent)
        }


class OrphanBlockManager(OrphanBlockPool):
    """Alias used by legacy tests and integrations."""
    pass


class TransactionOrdering:
    """
    Deterministic transaction ordering within blocks

    Ensures consistent transaction ordering across all nodes
    """

    @staticmethod
    def order_transactions(transactions: List) -> List:
        """
        Order transactions deterministically

        Priority rules:
        1. COINBASE always first
        2. Then by fee (highest first)
        3. Then by timestamp (oldest first)
        4. Then by hash (lexicographic)

        Args:
            transactions: List of transactions

        Returns:
            list: Ordered transactions
        """
        if not transactions:
            return []

        # Separate coinbase from regular transactions
        coinbase = []
        regular = []

        for tx in transactions:
            if tx.sender == "COINBASE":
                coinbase.append(tx)
            else:
                regular.append(tx)

        # Sort regular transactions
        regular.sort(key=lambda tx: (
            -tx.fee,  # Higher fee first (negative for descending)
            tx.timestamp,  # Older first
            tx.txid  # Deterministic tiebreaker
        ))

        # Coinbase first, then regular
        return coinbase + regular

    @staticmethod
    def validate_transaction_order(transactions: List) -> bool:
        """
        Validate that transactions are in correct order

        Args:
            transactions: List of transactions

        Returns:
            bool: Valid ordering
        """
        if not transactions:
            return True

        # First transaction must be COINBASE
        if transactions[0].sender != "COINBASE":
            return False

        # Check remaining transactions are ordered correctly
        for i in range(1, len(transactions) - 1):
            current = transactions[i]
            next_tx = transactions[i + 1]

            # Higher fee should come before lower fee
            if current.fee < next_tx.fee:
                return False

            # If fees equal, older should come before newer
            if current.fee == next_tx.fee and current.timestamp > next_tx.timestamp:
                return False

        return True


class TransactionOrderingRules:
    """Simple ordering helpers used by the unit tests."""

    @staticmethod
    def order_by_fee(transactions: List) -> List:
        return sorted(transactions, key=lambda tx: tx.fee, reverse=True)

    @staticmethod
    def order_by_timestamp(transactions: List) -> List:
        return sorted(transactions, key=lambda tx: tx.timestamp)

    def prioritize(self, transactions: List) -> List:
        return sorted(transactions, key=lambda tx: (-tx.fee, tx.timestamp))


class FinalityTracker:
    """
    Track block finality

    Blocks become increasingly "final" with more confirmations
    Provides different finality levels for different use cases
    """

    def __init__(self):
        # Finality thresholds
        self.FINALITY_SOFT = 6  # Soft finality (low-value transactions)
        self.FINALITY_MEDIUM = 20  # Medium finality (normal transactions)
        self.FINALITY_HARD = 100  # Hard finality (high-value, cannot reorg)

        self.finalized_blocks = set()  # Blocks with hard finality

    def get_block_finality(self, block_index: int, chain_height: int) -> Dict:
        """
        Get finality status of a block

        Args:
            block_index: Block index
            chain_height: Current chain height

        Returns:
            dict: Finality information
        """
        confirmations = chain_height - block_index

        # Determine finality level
        finality_level = "none"
        finality_percent = 0

        if confirmations >= self.FINALITY_HARD:
            finality_level = "hard"
            finality_percent = 100
        elif confirmations >= self.FINALITY_MEDIUM:
            finality_level = "medium"
            finality_percent = 75
        elif confirmations >= self.FINALITY_SOFT:
            finality_level = "soft"
            finality_percent = 50
        elif confirmations > 0:
            finality_level = "pending"
            finality_percent = min(40, confirmations * 10)

        return {
            'confirmations': confirmations,
            'finality_level': finality_level,
            'finality_percent': finality_percent,
            'reversible': confirmations < self.FINALITY_HARD,
            'safe_for_small_tx': confirmations >= self.FINALITY_SOFT,
            'safe_for_medium_tx': confirmations >= self.FINALITY_MEDIUM,
            'safe_for_large_tx': confirmations >= self.FINALITY_HARD
        }

    def mark_finalized(self, block_index: int):
        """Mark block as having hard finality"""
        self.finalized_blocks.add(block_index)

    def is_finalized(self, block_index: int) -> bool:
        """Check if block has hard finality"""
        return block_index in self.finalized_blocks

    def get_finality_stats(self, blockchain) -> Dict:
        """Get overall finality statistics"""
        chain_height = len(blockchain.chain)

        soft_finalized = sum(1 for i in range(max(0, chain_height - self.FINALITY_SOFT), chain_height))
        medium_finalized = sum(1 for i in range(max(0, chain_height - self.FINALITY_MEDIUM), chain_height))
        hard_finalized = len(self.finalized_blocks)

        return {
            'total_blocks': chain_height,
            'hard_finalized': hard_finalized,
            'medium_finalized': medium_finalized,
            'soft_finalized': soft_finalized,
            'pending': max(0, chain_height - self.FINALITY_SOFT)
        }


class FinalityMechanism:
    """Lightweight finality helper required by the test suite."""

    def __init__(self, confirmation_depth: int = 6):
        self.confirmation_depth = confirmation_depth

    def is_block_final(self, block_index: int, chain_height: int) -> bool:
        return (chain_height - block_index) >= self.confirmation_depth

    def get_finality_score(self, block_index: int, chain_height: int) -> float:
        confirmations = max(0, chain_height - block_index)
        if self.confirmation_depth == 0:
            return 1.0
        return min(1.0, confirmations / self.confirmation_depth)


class DynamicDifficultyAdjustment:
    """
    Advanced difficulty adjustment algorithm

    Adjusts mining difficulty based on:
    - Block time variance
    - Network hashrate
    - Recent block times
    """

    def __init__(self, target_block_time: int = 120):
        """
        Initialize difficulty adjustment

        Args:
            target_block_time: Target time between blocks (seconds)
        """
        self.target_block_time = target_block_time
        self.adjustment_window = 144  # Blocks to consider (12 hours at 5min/block)
        self.max_adjustment_factor = 4  # Max 4x adjustment per period
        self.min_difficulty = 1
        self.max_difficulty = 10

    def calculate_new_difficulty(self, blockchain) -> int:
        """
        Calculate new difficulty based on recent block times

        Args:
            blockchain: Blockchain instance

        Returns:
            int: New difficulty
        """
        chain_length = len(blockchain.chain)

        # Need at least 2 blocks to calculate
        if chain_length < 2:
            return blockchain.difficulty

        # Get recent blocks for calculation
        window_size = min(self.adjustment_window, chain_length - 1)
        recent_blocks = blockchain.chain[-window_size:]

        # Calculate actual time taken
        time_taken = recent_blocks[-1].timestamp - recent_blocks[0].timestamp

        # Calculate expected time
        expected_time = self.target_block_time * (window_size - 1)

        if expected_time == 0:
            return blockchain.difficulty

        # Calculate adjustment ratio
        adjustment_ratio = expected_time / time_taken

        # Limit adjustment magnitude
        adjustment_ratio = max(
            1 / self.max_adjustment_factor,
            min(self.max_adjustment_factor, adjustment_ratio)
        )

        # Calculate new difficulty
        current_difficulty = blockchain.difficulty
        new_difficulty = current_difficulty * adjustment_ratio

        # Round to integer and enforce limits
        new_difficulty = int(round(new_difficulty))
        new_difficulty = max(self.min_difficulty, min(self.max_difficulty, new_difficulty))

        return new_difficulty

    def should_adjust_difficulty(self, blockchain) -> bool:
        """
        Check if difficulty should be adjusted

        Args:
            blockchain: Blockchain instance

        Returns:
            bool: Should adjust
        """
        chain_length = len(blockchain.chain)

        # Adjust every adjustment_window blocks
        return chain_length > 0 and chain_length % self.adjustment_window == 0

    def get_difficulty_stats(self, blockchain) -> Dict:
        """
        Get difficulty adjustment statistics

        Args:
            blockchain: Blockchain instance

        Returns:
            dict: Statistics
        """
        chain_length = len(blockchain.chain)

        if chain_length < 2:
            return {
                'current_difficulty': blockchain.difficulty,
                'avg_block_time': 0,
                'target_block_time': self.target_block_time,
                'blocks_until_adjustment': self.adjustment_window
            }

        # Calculate average block time from recent blocks
        window_size = min(self.adjustment_window, chain_length - 1)
        recent_blocks = blockchain.chain[-window_size:]

        time_taken = recent_blocks[-1].timestamp - recent_blocks[0].timestamp
        avg_block_time = time_taken / (window_size - 1)

        blocks_until_adjustment = self.adjustment_window - (chain_length % self.adjustment_window)

        return {
            'current_difficulty': blockchain.difficulty,
            'avg_block_time': avg_block_time,
            'target_block_time': self.target_block_time,
            'blocks_until_adjustment': blocks_until_adjustment,
            'adjustment_window': self.adjustment_window,
            'recommended_difficulty': self.calculate_new_difficulty(blockchain)
        }


class DifficultyAdjustment:
    """Compatibility wrapper providing a simpler adjustment interface."""

    def __init__(self, target_block_time: int = 120, adjustment_interval: int = 10):
        self.target_block_time = target_block_time
        self.adjustment_interval = adjustment_interval
        self.min_difficulty = 0.1
        self.max_difficulty = 100.0

    def calculate_difficulty(self, chain: List, current_difficulty: float) -> float:
        if len(chain) < 2:
            return max(1.0, current_difficulty)

        window = min(self.adjustment_interval, len(chain) - 1)
        first_block = chain[-1 - window]
        last_block = chain[-1]
        time_diff = last_block.timestamp - first_block.timestamp
        if time_diff <= 0:
            return max(1.0, current_difficulty)

        avg_time = time_diff / window
        ratio = self.target_block_time / avg_time if avg_time > 0 else 1.0
        new_difficulty = current_difficulty * ratio
        return max(0.1, new_difficulty)


class AdvancedConsensusManager:
    """
    Unified manager for advanced consensus features
    """

    def __init__(self, blockchain):
        """
        Initialize advanced consensus manager

        Args:
            blockchain: Blockchain instance
        """
        self.blockchain = blockchain
        self.propagation_monitor = BlockPropagationMonitor()
        self.orphan_pool = OrphanBlockPool()
        self.transaction_ordering = TransactionOrdering()
        self.finality_tracker = FinalityTracker()
        self.difficulty_adjuster = DynamicDifficultyAdjustment()

    def process_new_block(self, block, from_peer: Optional[str] = None) -> Tuple[bool, str]:
        """
        Process newly received block with orphan handling

        Args:
            block: Block to process
            from_peer: Peer URL that sent the block (if any)

        Returns:
            (accepted, message)
        """
        # Record propagation
        self.propagation_monitor.record_block_first_seen(block.hash)
        if from_peer:
            self.propagation_monitor.record_block_from_peer(block.hash, from_peer)

        # Validate transaction ordering
        if not self.transaction_ordering.validate_transaction_order(block.transactions):
            return False, "Invalid transaction ordering"

        # Check if parent exists
        parent_exists = any(b.hash == block.previous_hash for b in self.blockchain.chain)

        if not parent_exists:
            # Orphan block - store for later
            self.orphan_pool.add_orphan(block, block.previous_hash)
            return False, "Orphan block - parent not found"

        # Process block normally
        # (This would integrate with blockchain's existing validation)
        return True, "Block accepted"

    def process_orphans_after_block(self, block_hash: str):
        """
        Process orphan blocks that were waiting for this block

        Args:
            block_hash: Hash of newly added block
        """
        orphans = self.orphan_pool.get_orphans_by_parent(block_hash)

        for orphan in orphans:
            # Try to process orphan again
            accepted, message = self.process_new_block(orphan)

            if accepted:
                # Remove from orphan pool
                self.orphan_pool.remove_orphan(orphan.hash)

                # Check for more orphans depending on this one
                self.process_orphans_after_block(orphan.hash)

    def order_pending_transactions(self) -> List:
        """
        Order pending transactions for next block

        Returns:
            list: Ordered transactions
        """
        return self.transaction_ordering.order_transactions(
            self.blockchain.pending_transactions
        )

    def adjust_difficulty_if_needed(self):
        """Check and adjust difficulty if needed"""
        if self.difficulty_adjuster.should_adjust_difficulty(self.blockchain):
            new_difficulty = self.difficulty_adjuster.calculate_new_difficulty(self.blockchain)

            if new_difficulty != self.blockchain.difficulty:
                old_difficulty = self.blockchain.difficulty
                self.blockchain.difficulty = new_difficulty
                print(f"Difficulty adjusted: {old_difficulty} -> {new_difficulty}")

    def mark_finalized_blocks(self):
        """Mark blocks that have achieved hard finality"""
        chain_height = len(self.blockchain.chain)

        # Mark blocks with 100+ confirmations as finalized
        for i in range(max(0, chain_height - self.finality_tracker.FINALITY_HARD)):
            if not self.finality_tracker.is_finalized(i):
                self.finality_tracker.mark_finalized(i)

    def get_consensus_stats(self) -> Dict:
        """Get comprehensive consensus statistics"""
        return {
            'propagation': self.propagation_monitor.get_network_stats(),
            'orphan_pool': self.orphan_pool.get_stats(),
            'finality': self.finality_tracker.get_finality_stats(self.blockchain),
            'difficulty': self.difficulty_adjuster.get_difficulty_stats(self.blockchain)
        }
