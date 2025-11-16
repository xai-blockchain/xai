"""
Unit tests for XAI Consensus mechanisms

Tests advanced consensus features, block propagation, and finality
"""

import pytest
import sys
import os
import time

# Add core directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "core"))

from advanced_consensus import (
    BlockStatus,
    BlockPropagationMonitor,
    OrphanBlockManager,
    TransactionOrderingRules,
    FinalityMechanism,
    DifficultyAdjustment,
)
from blockchain import Blockchain, Block
from wallet import Wallet


class TestBlockPropagationMonitor:
    """Test block propagation monitoring"""

    def test_create_monitor(self):
        """Test creating propagation monitor"""
        monitor = BlockPropagationMonitor()

        assert monitor.block_first_seen == {}
        assert len(monitor.propagation_history) == 0

    def test_record_block_first_seen(self):
        """Test recording when block is first seen"""
        monitor = BlockPropagationMonitor()

        monitor.record_block_first_seen("block_hash_1")

        assert "block_hash_1" in monitor.block_first_seen
        assert monitor.block_first_seen["block_hash_1"] > 0

    def test_record_block_from_peer(self):
        """Test recording block receipt from peer"""
        monitor = BlockPropagationMonitor()

        monitor.record_block_first_seen("block_hash_1")
        time.sleep(0.1)
        monitor.record_block_from_peer("block_hash_1", "peer1.aixn.com")

        assert "peer1.aixn.com" in monitor.peer_latency
        assert len(monitor.propagation_history) > 0

    def test_peer_performance_tracking(self):
        """Test peer performance metrics"""
        monitor = BlockPropagationMonitor()

        monitor.record_block_first_seen("block1")
        time.sleep(0.05)
        monitor.record_block_from_peer("block1", "peer1.aixn.com")

        performance = monitor.get_peer_performance("peer1.aixn.com")

        assert performance["block_count"] == 1
        assert performance["avg_latency"] > 0

    def test_multiple_peer_tracking(self):
        """Test tracking multiple peers"""
        monitor = BlockPropagationMonitor()

        # Record blocks from different peers
        monitor.record_block_first_seen("block1")
        monitor.record_block_from_peer("block1", "peer1.aixn.com")
        monitor.record_block_from_peer("block1", "peer2.aixn.com")

        assert "peer1.aixn.com" in monitor.peer_latency
        assert "peer2.aixn.com" in monitor.peer_latency

    def test_propagation_time_calculation(self):
        """Test propagation time is calculated correctly"""
        monitor = BlockPropagationMonitor()

        start_time = time.time()
        monitor.record_block_first_seen("block1")
        time.sleep(0.1)
        monitor.record_block_from_peer("block1", "peer1.aixn.com")

        # Propagation time should be approximately 0.1 seconds
        performance = monitor.get_peer_performance("peer1.aixn.com")
        assert 0.05 < performance["avg_latency"] < 0.15


class TestOrphanBlockManager:
    """Test orphan block handling"""

    def test_create_orphan_manager(self):
        """Test creating orphan block manager"""
        manager = OrphanBlockManager()

        assert manager.orphan_blocks == {}
        assert manager.orphan_by_previous == {}

    def test_add_orphan_block(self):
        """Test adding orphan block"""
        manager = OrphanBlockManager()
        bc = Blockchain()
        wallet = Wallet()

        block = bc.mine_pending_transactions(wallet.address)

        manager.add_orphan(block)

        assert block.hash in manager.orphan_blocks

    def test_retrieve_orphan_block(self):
        """Test retrieving orphan block"""
        manager = OrphanBlockManager()
        bc = Blockchain()
        wallet = Wallet()

        block = bc.mine_pending_transactions(wallet.address)
        manager.add_orphan(block)

        retrieved = manager.get_orphan(block.hash)

        assert retrieved is not None
        assert retrieved.hash == block.hash

    def test_orphan_by_previous_hash(self):
        """Test indexing orphans by previous hash"""
        manager = OrphanBlockManager()
        bc = Blockchain()
        wallet = Wallet()

        block = bc.mine_pending_transactions(wallet.address)
        manager.add_orphan(block)

        orphans = manager.get_orphans_by_previous(block.previous_hash)

        assert len(orphans) > 0

    def test_remove_orphan(self):
        """Test removing orphan block"""
        manager = OrphanBlockManager()
        bc = Blockchain()
        wallet = Wallet()

        block = bc.mine_pending_transactions(wallet.address)
        manager.add_orphan(block)

        removed = manager.remove_orphan(block.hash)

        assert removed is not None
        assert block.hash not in manager.orphan_blocks

    def test_orphan_expiration(self):
        """Test orphan blocks expire after timeout"""
        manager = OrphanBlockManager(max_orphan_age=1)  # 1 second timeout
        bc = Blockchain()
        wallet = Wallet()

        block = bc.mine_pending_transactions(wallet.address)
        manager.add_orphan(block)

        # Wait for expiration
        time.sleep(2)

        # Clean expired orphans
        manager.cleanup_expired_orphans()

        assert block.hash not in manager.orphan_blocks


class TestTransactionOrderingRules:
    """Test transaction ordering in blocks"""

    def test_create_ordering_rules(self):
        """Test creating transaction ordering rules"""
        rules = TransactionOrderingRules()

        assert rules is not None

    def test_order_by_fee(self):
        """Test ordering transactions by fee"""
        rules = TransactionOrderingRules()
        wallet = Wallet()

        from blockchain import Transaction

        # Create transactions with different fees
        tx1 = Transaction(wallet.address, "XAI123", 10.0, 0.1)
        tx2 = Transaction(wallet.address, "XAI456", 10.0, 0.5)
        tx3 = Transaction(wallet.address, "XAI789", 10.0, 0.3)

        transactions = [tx1, tx2, tx3]
        ordered = rules.order_by_fee(transactions)

        # Should be ordered by fee (highest first)
        assert ordered[0].fee == 0.5
        assert ordered[1].fee == 0.3
        assert ordered[2].fee == 0.1

    def test_order_by_time(self):
        """Test ordering transactions by timestamp"""
        rules = TransactionOrderingRules()
        wallet = Wallet()

        from blockchain import Transaction

        tx1 = Transaction(wallet.address, "XAI123", 10.0, 0.1)
        time.sleep(0.01)
        tx2 = Transaction(wallet.address, "XAI456", 10.0, 0.1)
        time.sleep(0.01)
        tx3 = Transaction(wallet.address, "XAI789", 10.0, 0.1)

        transactions = [tx3, tx1, tx2]
        ordered = rules.order_by_timestamp(transactions)

        # Should be ordered by timestamp (earliest first)
        assert ordered[0].timestamp <= ordered[1].timestamp <= ordered[2].timestamp

    def test_prioritize_transactions(self):
        """Test transaction prioritization"""
        rules = TransactionOrderingRules()
        wallet = Wallet()

        from blockchain import Transaction

        # Create mix of transactions
        tx1 = Transaction(wallet.address, "XAI123", 10.0, 0.1)
        tx2 = Transaction(wallet.address, "XAI456", 10.0, 1.0)  # High fee
        tx3 = Transaction(wallet.address, "XAI789", 10.0, 0.2)

        transactions = [tx1, tx2, tx3]
        prioritized = rules.prioritize(transactions)

        # High fee transaction should be first
        assert prioritized[0].fee == 1.0


class TestFinalityMechanism:
    """Test block finality mechanism"""

    def test_create_finality_mechanism(self):
        """Test creating finality mechanism"""
        finality = FinalityMechanism()

        assert finality.confirmation_depth > 0

    def test_block_not_final(self):
        """Test newly mined block is not final"""
        finality = FinalityMechanism(confirmation_depth=6)
        bc = Blockchain()
        wallet = Wallet()

        block = bc.mine_pending_transactions(wallet.address)

        is_final = finality.is_block_final(block.index, len(bc.chain))

        assert not is_final

    def test_block_becomes_final(self):
        """Test block becomes final after confirmations"""
        finality = FinalityMechanism(confirmation_depth=6)
        bc = Blockchain()
        wallet = Wallet()

        # Mine initial block
        block = bc.mine_pending_transactions(wallet.address)
        block_index = block.index

        # Mine 6 more blocks
        for _ in range(6):
            bc.mine_pending_transactions(wallet.address)

        is_final = finality.is_block_final(block_index, len(bc.chain))

        assert is_final

    def test_finality_score(self):
        """Test finality score calculation"""
        finality = FinalityMechanism()
        bc = Blockchain()
        wallet = Wallet()

        block = bc.mine_pending_transactions(wallet.address)

        score = finality.get_finality_score(block.index, len(bc.chain))

        assert 0 <= score <= 1.0

    def test_increasing_finality(self):
        """Test finality increases with confirmations"""
        finality = FinalityMechanism()
        bc = Blockchain()
        wallet = Wallet()

        block = bc.mine_pending_transactions(wallet.address)
        score1 = finality.get_finality_score(block.index, len(bc.chain))

        # Mine more blocks
        bc.mine_pending_transactions(wallet.address)
        score2 = finality.get_finality_score(block.index, len(bc.chain))

        assert score2 > score1


class TestDifficultyAdjustment:
    """Test difficulty adjustment algorithm"""

    def test_create_difficulty_adjustment(self):
        """Test creating difficulty adjustment"""
        adj = DifficultyAdjustment()

        assert adj.target_block_time > 0
        assert adj.adjustment_interval > 0

    def test_calculate_new_difficulty(self):
        """Test calculating new difficulty"""
        adj = DifficultyAdjustment()
        bc = Blockchain()

        new_difficulty = adj.calculate_difficulty(bc.chain, bc.difficulty)

        assert new_difficulty > 0

    def test_difficulty_increases_when_fast(self):
        """Test difficulty increases when blocks are too fast"""
        adj = DifficultyAdjustment(target_block_time=60)

        # Create mock chain with fast blocks
        class MockBlock:
            def __init__(self, timestamp):
                self.timestamp = timestamp

        # Blocks every 30 seconds (too fast)
        chain = [MockBlock(i * 30) for i in range(100)]

        new_diff = adj.calculate_difficulty(chain, 4)

        # Difficulty should increase or stay same
        assert new_diff >= 4

    def test_difficulty_decreases_when_slow(self):
        """Test difficulty decreases when blocks are too slow"""
        adj = DifficultyAdjustment(target_block_time=60)

        # Create mock chain with slow blocks
        class MockBlock:
            def __init__(self, timestamp):
                self.timestamp = timestamp

        # Blocks every 120 seconds (too slow)
        chain = [MockBlock(i * 120) for i in range(100)]

        new_diff = adj.calculate_difficulty(chain, 4)

        # Difficulty should decrease or stay same
        assert new_diff <= 4

    def test_difficulty_limits(self):
        """Test difficulty has min/max limits"""
        adj = DifficultyAdjustment()

        # Test minimum
        assert adj.min_difficulty > 0

        # Test maximum
        assert adj.max_difficulty > adj.min_difficulty


class TestBlockStatus:
    """Test block status enumeration"""

    def test_block_status_types(self):
        """Test all block status types exist"""
        assert BlockStatus.VALID
        assert BlockStatus.ORPHAN
        assert BlockStatus.INVALID
        assert BlockStatus.PENDING

    def test_status_values(self):
        """Test status values are strings"""
        assert isinstance(BlockStatus.VALID.value, str)
        assert isinstance(BlockStatus.ORPHAN.value, str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
