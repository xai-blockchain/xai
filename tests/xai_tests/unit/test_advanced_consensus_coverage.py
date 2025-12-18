"""
Comprehensive tests for advanced_consensus.py to boost coverage from 43.99% to 95%+

Tests all classes and methods:
- BlockPropagationMonitor: network statistics, peer performance
- OrphanBlockPool: orphan handling, expiration, indexing
- TransactionOrdering: deterministic ordering, validation
- FinalityTracker: finality levels, block finalization
- DynamicDifficultyAdjustment: difficulty calculation, adjustment
- AdvancedConsensusManager: unified consensus management
"""

import pytest
import time
from xai.core.blockchain import Blockchain, Block, Transaction
from xai.core.wallet import Wallet
from xai.core.advanced_consensus import (
    BlockStatus,
    BlockPropagationMonitor,
    OrphanBlockPool,
    OrphanBlockManager,
    TransactionOrdering,
    TransactionOrderingRules,
    FinalityTracker,
    FinalityMechanism,
    DynamicDifficultyAdjustment,
    DifficultyAdjustment,
    AdvancedConsensusManager,
)


class TestBlockPropagationMonitorComprehensive:
    """Comprehensive tests for BlockPropagationMonitor"""

    def test_record_block_first_seen_multiple_blocks(self):
        """Test recording multiple blocks first seen"""
        monitor = BlockPropagationMonitor()

        hashes = ["block1", "block2", "block3"]
        for h in hashes:
            monitor.record_block_first_seen(h)

        assert len(monitor.block_first_seen) == 3
        for h in hashes:
            assert h in monitor.block_first_seen

    def test_record_block_first_seen_duplicate(self):
        """Test recording same block twice doesn't update timestamp"""
        monitor = BlockPropagationMonitor()

        monitor.record_block_first_seen("block1")
        first_time = monitor.block_first_seen["block1"]

        time.sleep(0.1)
        monitor.record_block_first_seen("block1")

        # Should not update
        assert monitor.block_first_seen["block1"] == first_time

    def test_record_block_from_peer_updates_latency(self):
        """Test that receiving blocks from peer updates latency"""
        monitor = BlockPropagationMonitor()

        monitor.record_block_first_seen("block1")
        time.sleep(0.05)
        monitor.record_block_from_peer("block1", "peer1")

        assert "peer1" in monitor.peer_latency
        assert monitor.peer_latency["peer1"] > 0

    def test_record_block_from_peer_exponential_moving_average(self):
        """Test EMA calculation for peer latency"""
        monitor = BlockPropagationMonitor()

        # First block
        monitor.record_block_first_seen("block1")
        time.sleep(0.05)
        monitor.record_block_from_peer("block1", "peer1")
        first_latency = monitor.peer_latency["peer1"]

        # Second block
        monitor.record_block_first_seen("block2")
        time.sleep(0.1)
        monitor.record_block_from_peer("block2", "peer1")
        second_latency = monitor.peer_latency["peer1"]

        # Should be different due to EMA
        assert second_latency != first_latency

    def test_get_peer_performance_no_data(self):
        """Test peer performance for peer with no data"""
        monitor = BlockPropagationMonitor()

        perf = monitor.get_peer_performance("unknown_peer")

        assert perf["avg_latency"] is None
        assert perf["block_count"] == 0
        assert perf["performance_score"] == 0

    def test_get_peer_performance_calculation(self):
        """Test peer performance metrics calculation"""
        monitor = BlockPropagationMonitor()

        monitor.record_block_first_seen("block1")
        time.sleep(0.05)
        monitor.record_block_from_peer("block1", "peer1")

        perf = monitor.get_peer_performance("peer1")

        assert perf["avg_latency"] > 0
        assert perf["block_count"] == 1
        assert 0 <= perf["performance_score"] <= 100

    def test_get_network_stats_empty(self):
        """Test network stats with no data"""
        monitor = BlockPropagationMonitor()

        stats = monitor.get_network_stats()

        assert stats["avg_propagation_time"] == 0
        assert stats["total_blocks_tracked"] == 0
        assert stats["active_peers"] == 0

    def test_get_network_stats_with_data(self):
        """Test network stats calculation"""
        monitor = BlockPropagationMonitor()

        # Record some blocks
        for i in range(3):
            block_hash = f"block{i}"
            monitor.record_block_first_seen(block_hash)
            time.sleep(0.01)
            monitor.record_block_from_peer(block_hash, f"peer{i % 2}")

        stats = monitor.get_network_stats()

        assert stats["avg_propagation_time"] > 0
        assert stats["total_blocks_tracked"] == 3
        assert stats["active_peers"] > 0
        assert "min_propagation_time" in stats
        assert "max_propagation_time" in stats

    def test_propagation_history_maxlen(self):
        """Test propagation history has maximum length"""
        monitor = BlockPropagationMonitor()

        # Add more than maxlen (1000) entries
        for i in range(1100):
            monitor.record_block_first_seen(f"block{i}")
            monitor.record_block_from_peer(f"block{i}", "peer1")

        # Should be limited to 1000
        assert len(monitor.propagation_history) == 1000


class TestOrphanBlockPoolComprehensive:
    """Comprehensive tests for OrphanBlockPool"""

    def test_add_orphan_with_explicit_parent_hash(self, tmp_path):
        """Test adding orphan with explicit parent hash"""
        pool = OrphanBlockPool()
        bc = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        block = bc.mine_pending_transactions(wallet.address)

        pool.add_orphan(block, "explicit_parent_hash")

        orphans = pool.get_orphans_by_parent("explicit_parent_hash")
        assert len(orphans) > 0

    def test_add_orphan_max_capacity(self, tmp_path):
        """Test orphan pool respects max capacity"""
        pool = OrphanBlockPool(max_orphans=5)
        bc = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        # Add 10 blocks
        for i in range(10):
            block = bc.mine_pending_transactions(wallet.address)
            pool.add_orphan(block)

        # Should only keep 5
        assert len(pool.orphan_blocks) == 5

    def test_remove_oldest_orphan(self, tmp_path):
        """Test that oldest orphan is removed when capacity reached"""
        pool = OrphanBlockPool(max_orphans=3)
        bc = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        blocks = []
        for i in range(4):
            block = bc.mine_pending_transactions(wallet.address)
            blocks.append(block)
            pool.add_orphan(block)
            time.sleep(0.01)  # Ensure different timestamps

        # First block should be removed
        assert blocks[0].hash not in pool.orphan_blocks

    def test_get_orphans_by_parent_multiple(self, tmp_path):
        """Test getting multiple orphans with same parent"""
        pool = OrphanBlockPool()
        bc = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        parent_hash = "common_parent"

        # Add multiple orphans with same parent
        for i in range(3):
            block = bc.mine_pending_transactions(wallet.address)
            pool.add_orphan(block, parent_hash)

        orphans = pool.get_orphans_by_parent(parent_hash)
        assert len(orphans) == 3

    def test_get_orphans_by_previous_alias(self, tmp_path):
        """Test get_orphans_by_previous is alias for get_orphans_by_parent"""
        pool = OrphanBlockPool()
        bc = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        block = bc.mine_pending_transactions(wallet.address)
        pool.add_orphan(block)

        orphans1 = pool.get_orphans_by_parent(block.previous_hash)
        orphans2 = pool.get_orphans_by_previous(block.previous_hash)

        assert orphans1 == orphans2

    def test_remove_orphan_cleans_indexes(self, tmp_path):
        """Test removing orphan cleans up all indexes"""
        pool = OrphanBlockPool()
        bc = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        block = bc.mine_pending_transactions(wallet.address)
        pool.add_orphan(block)

        parent_hash = block.previous_hash

        # Verify it's indexed
        assert block.hash in pool.orphan_blocks
        assert len(pool.get_orphans_by_parent(parent_hash)) > 0

        # Remove it
        pool.remove_orphan(block.hash)

        # Should be completely removed
        assert block.hash not in pool.orphan_blocks
        assert block.hash not in pool.orphan_timestamps

    def test_cleanup_expired_orphans_removes_old(self, tmp_path):
        """Test cleanup removes expired orphans"""
        pool = OrphanBlockPool(max_orphan_age=0.5)  # 0.5 second timeout
        bc = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        # Add old block
        old_block = bc.mine_pending_transactions(wallet.address)
        pool.add_orphan(old_block)

        time.sleep(0.6)  # Wait for expiration

        # Add new block
        new_block = bc.mine_pending_transactions(wallet.address)
        pool.add_orphan(new_block)

        # Cleanup
        pool.cleanup_expired_orphans()

        # Old should be removed, new should remain
        assert old_block.hash not in pool.orphan_blocks
        assert new_block.hash in pool.orphan_blocks

    def test_cleanup_expired_orphans_keeps_recent(self, tmp_path):
        """Test cleanup keeps recent orphans"""
        pool = OrphanBlockPool(max_orphan_age=10)
        bc = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        block = bc.mine_pending_transactions(wallet.address)
        pool.add_orphan(block)

        pool.cleanup_expired_orphans()

        # Should still be there
        assert block.hash in pool.orphan_blocks

    def test_get_stats(self, tmp_path):
        """Test orphan pool statistics"""
        pool = OrphanBlockPool(max_orphans=10)
        bc = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        # Add some orphans
        for i in range(3):
            block = bc.mine_pending_transactions(wallet.address)
            pool.add_orphan(block)

        stats = pool.get_stats()

        assert stats["total_orphans"] == 3
        assert stats["max_capacity"] == 10
        assert stats["parents_tracked"] >= 1


class TestOrphanBlockManagerAlias:
    """Test OrphanBlockManager is proper alias"""

    def test_orphan_block_manager_is_orphan_pool(self, tmp_path):
        """Test OrphanBlockManager is same as OrphanBlockPool"""
        manager = OrphanBlockManager()
        bc = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        block = bc.mine_pending_transactions(wallet.address)
        manager.add_orphan(block)

        assert block.hash in manager.orphan_blocks


class TestTransactionOrderingComprehensive:
    """Comprehensive tests for TransactionOrdering"""

    def test_order_transactions_empty_list(self):
        """Test ordering empty transaction list"""
        ordered = TransactionOrdering.order_transactions([])

        assert ordered == []

    def test_order_transactions_single_transaction(self, tmp_path):
        """Test ordering single transaction"""
        wallet = Wallet()
        tx = Transaction("COINBASE", wallet.address, 12.0)
        tx.txid = tx.calculate_hash()

        ordered = TransactionOrdering.order_transactions([tx])

        assert len(ordered) == 1
        assert ordered[0] == tx

    def test_order_transactions_coinbase_first(self, tmp_path):
        """Test coinbase transaction comes first"""
        wallet = Wallet()

        coinbase = Transaction("COINBASE", wallet.address, 12.0)
        coinbase.txid = coinbase.calculate_hash()

        regular = Transaction(wallet.address, "XAI" + "a" * 40, 10.0, 0.5, public_key=wallet.public_key)
        regular.txid = regular.calculate_hash()

        # Add in reverse order
        ordered = TransactionOrdering.order_transactions([regular, coinbase])

        # Coinbase should be first
        assert ordered[0].sender == "COINBASE"

    def test_order_transactions_by_fee_descending(self, tmp_path):
        """Test transactions ordered by fee (highest first)"""
        wallet = Wallet()

        tx1 = Transaction(wallet.address, "XAI" + "1" * 40, 10.0, 0.1, public_key=wallet.public_key)
        tx1.txid = tx1.calculate_hash()

        tx2 = Transaction(wallet.address, "XAI" + "2" * 40, 10.0, 0.5, public_key=wallet.public_key)
        tx2.txid = tx2.calculate_hash()

        tx3 = Transaction(wallet.address, "XAI" + "3" * 40, 10.0, 0.3, public_key=wallet.public_key)
        tx3.txid = tx3.calculate_hash()

        ordered = TransactionOrdering.order_transactions([tx1, tx2, tx3])

        # Should be tx2 (0.5), tx3 (0.3), tx1 (0.1)
        assert ordered[0].fee == 0.5
        assert ordered[1].fee == 0.3
        assert ordered[2].fee == 0.1

    def test_order_transactions_by_timestamp_when_fees_equal(self, tmp_path):
        """Test transactions with same fee ordered by timestamp"""
        wallet = Wallet()

        tx1 = Transaction(wallet.address, "XAI" + "1" * 40, 10.0, 0.1, public_key=wallet.public_key)
        tx1.timestamp = time.time()
        tx1.txid = tx1.calculate_hash()

        time.sleep(0.01)

        tx2 = Transaction(wallet.address, "XAI" + "2" * 40, 10.0, 0.1, public_key=wallet.public_key)
        tx2.timestamp = time.time()
        tx2.txid = tx2.calculate_hash()

        ordered = TransactionOrdering.order_transactions([tx2, tx1])

        # Older should come first
        assert ordered[0].timestamp < ordered[1].timestamp

    def test_order_transactions_deterministic_tiebreaker(self, tmp_path):
        """Test transactions with same fee and timestamp ordered by hash"""
        wallet = Wallet()

        tx1 = Transaction(wallet.address, "XAI" + "1" * 40, 10.0, 0.1, public_key=wallet.public_key)
        tx1.timestamp = 1000.0
        tx1.txid = "aaa"

        tx2 = Transaction(wallet.address, "XAI" + "2" * 40, 10.0, 0.1, public_key=wallet.public_key)
        tx2.timestamp = 1000.0
        tx2.txid = "zzz"

        ordered = TransactionOrdering.order_transactions([tx2, tx1])

        # Should be sorted by txid
        assert ordered[0].txid == "aaa"
        assert ordered[1].txid == "zzz"

    def test_validate_transaction_order_valid(self, tmp_path):
        """Test validation of correctly ordered transactions"""
        wallet = Wallet()

        coinbase = Transaction("COINBASE", wallet.address, 12.0)
        coinbase.txid = coinbase.calculate_hash()

        tx1 = Transaction(wallet.address, "XAI" + "1" * 40, 10.0, 0.5, public_key=wallet.public_key)
        tx1.txid = tx1.calculate_hash()

        tx2 = Transaction(wallet.address, "XAI" + "2" * 40, 10.0, 0.3, public_key=wallet.public_key)
        tx2.txid = tx2.calculate_hash()

        ordered = [coinbase, tx1, tx2]

        assert TransactionOrdering.validate_transaction_order(ordered) is True

    def test_validate_transaction_order_empty(self):
        """Test validation of empty transaction list"""
        assert TransactionOrdering.validate_transaction_order([]) is True

    def test_validate_transaction_order_no_coinbase_first(self, tmp_path):
        """Test validation fails if coinbase not first"""
        wallet = Wallet()

        tx1 = Transaction(wallet.address, "XAI" + "1" * 40, 10.0, 0.5, public_key=wallet.public_key)
        tx1.txid = tx1.calculate_hash()

        coinbase = Transaction("COINBASE", wallet.address, 12.0)
        coinbase.txid = coinbase.calculate_hash()

        # Wrong order
        ordered = [tx1, coinbase]

        assert TransactionOrdering.validate_transaction_order(ordered) is False

    def test_validate_transaction_order_wrong_fee_order(self, tmp_path):
        """Test validation fails if fees not descending"""
        wallet = Wallet()

        coinbase = Transaction("COINBASE", wallet.address, 12.0)
        coinbase.txid = coinbase.calculate_hash()

        tx1 = Transaction(wallet.address, "XAI" + "1" * 40, 10.0, 0.1, public_key=wallet.public_key)
        tx1.txid = tx1.calculate_hash()

        tx2 = Transaction(wallet.address, "XAI" + "2" * 40, 10.0, 0.5, public_key=wallet.public_key)
        tx2.txid = tx2.calculate_hash()

        # Wrong order (low fee before high fee)
        ordered = [coinbase, tx1, tx2]

        assert TransactionOrdering.validate_transaction_order(ordered) is False

    def test_validate_transaction_order_wrong_timestamp_order(self, tmp_path):
        """Test validation fails if timestamps wrong when fees equal"""
        wallet = Wallet()

        coinbase = Transaction("COINBASE", wallet.address, 12.0)
        coinbase.txid = coinbase.calculate_hash()

        tx1 = Transaction(wallet.address, "XAI" + "1" * 40, 10.0, 0.1, public_key=wallet.public_key)
        tx1.timestamp = 2000.0
        tx1.txid = tx1.calculate_hash()

        tx2 = Transaction(wallet.address, "XAI" + "2" * 40, 10.0, 0.1, public_key=wallet.public_key)
        tx2.timestamp = 1000.0
        tx2.txid = tx2.calculate_hash()

        # Wrong order (newer before older with same fee)
        ordered = [coinbase, tx1, tx2]

        assert TransactionOrdering.validate_transaction_order(ordered) is False


class TestTransactionOrderingRulesComprehensive:
    """Comprehensive tests for TransactionOrderingRules"""

    def test_order_by_fee(self, tmp_path):
        """Test ordering by fee"""
        rules = TransactionOrderingRules()
        wallet = Wallet()

        tx1 = Transaction(wallet.address, "XAI" + "1" * 40, 10.0, 0.1)
        tx2 = Transaction(wallet.address, "XAI" + "2" * 40, 10.0, 0.5)
        tx3 = Transaction(wallet.address, "XAI" + "3" * 40, 10.0, 0.3)

        ordered = rules.order_by_fee([tx1, tx2, tx3])

        assert ordered[0].fee == 0.5
        assert ordered[1].fee == 0.3
        assert ordered[2].fee == 0.1

    def test_order_by_timestamp(self, tmp_path):
        """Test ordering by timestamp"""
        rules = TransactionOrderingRules()
        wallet = Wallet()

        tx1 = Transaction(wallet.address, "XAI" + "1" * 40, 10.0, 0.1)
        tx1.timestamp = 3000.0

        tx2 = Transaction(wallet.address, "XAI" + "2" * 40, 10.0, 0.1)
        tx2.timestamp = 1000.0

        tx3 = Transaction(wallet.address, "XAI" + "3" * 40, 10.0, 0.1)
        tx3.timestamp = 2000.0

        ordered = rules.order_by_timestamp([tx1, tx2, tx3])

        assert ordered[0].timestamp == 1000.0
        assert ordered[1].timestamp == 2000.0
        assert ordered[2].timestamp == 3000.0

    def test_prioritize_combines_fee_and_timestamp(self, tmp_path):
        """Test prioritize method combines fee and timestamp"""
        rules = TransactionOrderingRules()
        wallet = Wallet()

        tx1 = Transaction(wallet.address, "XAI" + "1" * 40, 10.0, 0.1)
        tx1.timestamp = 1000.0

        tx2 = Transaction(wallet.address, "XAI" + "2" * 40, 10.0, 0.5)
        tx2.timestamp = 3000.0

        tx3 = Transaction(wallet.address, "XAI" + "3" * 40, 10.0, 0.1)
        tx3.timestamp = 2000.0

        ordered = rules.prioritize([tx1, tx2, tx3])

        # Should be tx2 (high fee), then tx1 (same fee but older), then tx3
        assert ordered[0].fee == 0.5
        assert ordered[1].timestamp < ordered[2].timestamp


class TestFinalityTrackerComprehensive:
    """Comprehensive tests for FinalityTracker"""

    def test_get_block_finality_pending(self):
        """Test finality for very recent block"""
        tracker = FinalityTracker()

        finality = tracker.get_block_finality(99, 100)

        assert finality["confirmations"] == 1
        assert finality["finality_level"] == "pending"
        assert finality["reversible"] is True

    def test_get_block_finality_soft(self):
        """Test soft finality (6 confirmations)"""
        tracker = FinalityTracker()

        finality = tracker.get_block_finality(94, 100)

        assert finality["confirmations"] == 6
        assert finality["finality_level"] == "soft"
        assert finality["finality_percent"] == 50
        assert finality["safe_for_small_tx"] is True

    def test_get_block_finality_medium(self):
        """Test medium finality (20 confirmations)"""
        tracker = FinalityTracker()

        finality = tracker.get_block_finality(80, 100)

        assert finality["confirmations"] == 20
        assert finality["finality_level"] == "medium"
        assert finality["finality_percent"] == 75
        assert finality["safe_for_medium_tx"] is True

    def test_get_block_finality_hard(self):
        """Test hard finality (100 confirmations)"""
        tracker = FinalityTracker()

        finality = tracker.get_block_finality(0, 100)

        assert finality["confirmations"] == 100
        assert finality["finality_level"] == "hard"
        assert finality["finality_percent"] == 100
        assert finality["reversible"] is False
        assert finality["safe_for_large_tx"] is True

    def test_mark_finalized(self):
        """Test marking block as finalized"""
        tracker = FinalityTracker()

        tracker.mark_finalized(50)

        assert tracker.is_finalized(50) is True
        assert tracker.is_finalized(51) is False

    def test_get_finality_stats(self, tmp_path):
        """Test getting overall finality statistics"""
        bc = Blockchain(data_dir=str(tmp_path))
        tracker = FinalityTracker()
        wallet = Wallet()

        # Mine some blocks
        for i in range(10):
            bc.mine_pending_transactions(wallet.address)

        stats = tracker.get_finality_stats(bc)

        assert "total_blocks" in stats
        assert "hard_finalized" in stats
        assert "medium_finalized" in stats
        assert "soft_finalized" in stats


class TestFinalityMechanismComprehensive:
    """Comprehensive tests for FinalityMechanism"""

    def test_is_block_final_true(self):
        """Test block is final with enough confirmations"""
        mechanism = FinalityMechanism(confirmation_depth=6)

        is_final = mechanism.is_block_final(0, 10)

        assert is_final is True

    def test_is_block_final_false(self):
        """Test block not final without enough confirmations"""
        mechanism = FinalityMechanism(confirmation_depth=6)

        is_final = mechanism.is_block_final(5, 10)

        assert is_final is False

    def test_get_finality_score_full(self):
        """Test finality score at 100%"""
        mechanism = FinalityMechanism(confirmation_depth=10)

        score = mechanism.get_finality_score(0, 20)

        assert score == 1.0

    def test_get_finality_score_partial(self):
        """Test finality score at 50%"""
        mechanism = FinalityMechanism(confirmation_depth=10)

        score = mechanism.get_finality_score(5, 10)

        assert score == 0.5

    def test_get_finality_score_zero_depth(self):
        """Test finality score with zero confirmation depth"""
        mechanism = FinalityMechanism(confirmation_depth=0)

        score = mechanism.get_finality_score(0, 10)

        assert score == 1.0


class TestDynamicDifficultyAdjustmentComprehensive:
    """Comprehensive tests for DynamicDifficultyAdjustment"""

    def test_calculate_new_difficulty_insufficient_blocks(self, tmp_path):
        """Test difficulty calculation with insufficient blocks"""
        bc = Blockchain(data_dir=str(tmp_path))
        adjuster = DynamicDifficultyAdjustment()

        new_diff = adjuster.calculate_new_difficulty(bc)

        # Should return current difficulty
        assert new_diff == bc.difficulty

    def test_calculate_new_difficulty_stable(self, tmp_path):
        """Test difficulty stays same when block time is on target"""
        bc = Blockchain(data_dir=str(tmp_path))
        adjuster = DynamicDifficultyAdjustment(target_block_time=1)
        wallet = Wallet()

        # Mine blocks with exactly 1 second between them
        base_time = time.time()
        for i in range(10):
            bc.chain[-1].timestamp = base_time + i
            bc.mine_pending_transactions(wallet.address)

        initial_diff = bc.difficulty
        new_diff = adjuster.calculate_new_difficulty(bc)

        # Should be close to initial
        assert abs(new_diff - initial_diff) <= 1

    def test_should_adjust_difficulty_true(self, tmp_path):
        """Test should adjust at adjustment window"""
        bc = Blockchain(data_dir=str(tmp_path))
        adjuster = DynamicDifficultyAdjustment()
        wallet = Wallet()

        # Mine to adjustment window
        for i in range(adjuster.adjustment_window):
            bc.mine_pending_transactions(wallet.address)

        should_adjust = adjuster.should_adjust_difficulty(bc)

        assert should_adjust is True

    def test_should_adjust_difficulty_false(self, tmp_path):
        """Test should not adjust before window"""
        bc = Blockchain(data_dir=str(tmp_path))
        adjuster = DynamicDifficultyAdjustment()
        wallet = Wallet()

        bc.mine_pending_transactions(wallet.address)

        should_adjust = adjuster.should_adjust_difficulty(bc)

        assert should_adjust is False

    def test_get_difficulty_stats(self, tmp_path):
        """Test difficulty statistics"""
        bc = Blockchain(data_dir=str(tmp_path))
        adjuster = DynamicDifficultyAdjustment()
        wallet = Wallet()

        bc.mine_pending_transactions(wallet.address)

        stats = adjuster.get_difficulty_stats(bc)

        assert "current_difficulty" in stats
        assert "avg_block_time" in stats
        assert "target_block_time" in stats
        assert "blocks_until_adjustment" in stats
        assert "recommended_difficulty" in stats

    def test_difficulty_clamped_to_max(self, tmp_path):
        """Test difficulty doesn't exceed maximum"""
        bc = Blockchain(data_dir=str(tmp_path))
        adjuster = DynamicDifficultyAdjustment()
        wallet = Wallet()

        # Set very high current difficulty
        bc.difficulty = 100

        # Force very slow blocks
        base_time = time.time()
        for i in range(150):
            bc.chain[-1].timestamp = base_time + (i * 1000)  # Very slow
            bc.mine_pending_transactions(wallet.address)

        new_diff = adjuster.calculate_new_difficulty(bc)

        # Should be clamped to max_difficulty
        assert new_diff <= adjuster.max_difficulty

    def test_difficulty_clamped_to_min(self, tmp_path):
        """Test difficulty doesn't go below minimum"""
        bc = Blockchain(data_dir=str(tmp_path))
        adjuster = DynamicDifficultyAdjustment()
        wallet = Wallet()

        # Set low current difficulty
        bc.difficulty = 1

        # Force very fast blocks
        base_time = time.time()
        for i in range(150):
            bc.chain[-1].timestamp = base_time + (i * 0.01)  # Very fast
            bc.mine_pending_transactions(wallet.address)

        new_diff = adjuster.calculate_new_difficulty(bc)

        # Should be clamped to min_difficulty
        assert new_diff >= adjuster.min_difficulty


class TestDifficultyAdjustmentComprehensive:
    """Comprehensive tests for DifficultyAdjustment compatibility wrapper"""

    def test_calculate_difficulty_basic(self, tmp_path):
        """Test basic difficulty calculation"""
        bc = Blockchain(data_dir=str(tmp_path))
        adjuster = DifficultyAdjustment()
        wallet = Wallet()

        bc.mine_pending_transactions(wallet.address)

        new_diff = adjuster.calculate_difficulty(bc.chain, bc.difficulty)

        assert new_diff >= 0.1  # Minimum

    def test_calculate_difficulty_zero_time_diff(self, tmp_path):
        """Test difficulty when time diff is zero"""
        bc = Blockchain(data_dir=str(tmp_path))
        adjuster = DifficultyAdjustment()
        wallet = Wallet()

        # Make all blocks have same timestamp
        bc.mine_pending_transactions(wallet.address)
        bc.chain[-1].timestamp = bc.chain[-2].timestamp

        new_diff = adjuster.calculate_difficulty(bc.chain, bc.difficulty)

        # Should return at least 1.0
        assert new_diff >= 1.0


class TestAdvancedConsensusManagerComprehensive:
    """Comprehensive tests for AdvancedConsensusManager"""

    def test_process_new_block_valid(self, tmp_path):
        """Test processing valid new block"""
        bc = Blockchain(data_dir=str(tmp_path))
        manager = AdvancedConsensusManager(bc)
        wallet = Wallet()

        block = bc.mine_pending_transactions(wallet.address)

        accepted, message = manager.process_new_block(block)

        assert accepted is True
        assert "accepted" in message.lower()

    def test_process_new_block_invalid_ordering(self, tmp_path):
        """Test processing block with invalid transaction ordering"""
        bc = Blockchain(data_dir=str(tmp_path))
        manager = AdvancedConsensusManager(bc)
        wallet = Wallet()

        # Create block with wrong transaction order
        tx1 = Transaction(wallet.address, "XAI" + "1" * 40, 10.0, 0.1, public_key=wallet.public_key)
        tx1.txid = tx1.calculate_hash()

        coinbase = Transaction("COINBASE", wallet.address, 12.0)
        coinbase.txid = coinbase.calculate_hash()

        # Wrong order (regular before coinbase)
        block = Block(1, [tx1, coinbase], bc.get_latest_block().hash, bc.difficulty)
        block.hash = "fake_hash"

        accepted, message = manager.process_new_block(block)

        assert accepted is False
        assert "ordering" in message.lower()

    def test_process_new_block_orphan(self, tmp_path):
        """Test processing orphan block"""
        bc = Blockchain(data_dir=str(tmp_path))
        manager = AdvancedConsensusManager(bc)
        wallet = Wallet()

        # Create block with non-existent parent (valid 64-char hex format but not in chain)
        fake_parent_hash = "0" * 64  # Valid format but doesn't exist
        block = Block(100, [], fake_parent_hash, bc.difficulty)
        block.hash = "a" * 64  # Valid format hash

        accepted, message = manager.process_new_block(block)

        assert accepted is False
        assert "orphan" in message.lower()

        # Should be in orphan pool
        assert block.hash in manager.orphan_pool.orphan_blocks

    def test_process_orphans_after_block(self, tmp_path):
        """Test processing orphans after parent arrives"""
        bc = Blockchain(data_dir=str(tmp_path))
        manager = AdvancedConsensusManager(bc)
        wallet = Wallet()

        # Add orphan
        parent_hash = bc.get_latest_block().hash
        orphan = Block(2, [], parent_hash, bc.difficulty)
        orphan.hash = "orphan_hash"
        manager.orphan_pool.add_orphan(orphan, parent_hash)

        # Process orphans
        manager.process_orphans_after_block(parent_hash)

        # Orphan should have been processed (though may fail validation)

    def test_order_pending_transactions(self, tmp_path):
        """Test ordering pending transactions"""
        bc = Blockchain(data_dir=str(tmp_path))
        manager = AdvancedConsensusManager(bc)
        wallet = Wallet()

        # Add some pending transactions
        bc.mine_pending_transactions(wallet.address)

        tx1 = bc.create_transaction(wallet.address, "XAI" + "1" * 40, 1.0, 0.1, wallet.private_key, wallet.public_key)
        tx2 = bc.create_transaction(wallet.address, "XAI" + "2" * 40, 1.0, 0.5, wallet.private_key, wallet.public_key)

        if tx1:
            bc.add_transaction(tx1)
        if tx2:
            bc.add_transaction(tx2)

        ordered = manager.order_pending_transactions()

        # Should return ordered list
        assert isinstance(ordered, list)

    def test_adjust_difficulty_if_needed(self, tmp_path):
        """Test automatic difficulty adjustment"""
        bc = Blockchain(data_dir=str(tmp_path))
        manager = AdvancedConsensusManager(bc)
        wallet = Wallet()

        initial_diff = bc.difficulty

        # Mine to adjustment window
        for i in range(manager.difficulty_adjuster.adjustment_window + 1):
            bc.mine_pending_transactions(wallet.address)

        manager.adjust_difficulty_if_needed()

        # Difficulty may have changed
        assert bc.difficulty >= manager.difficulty_adjuster.min_difficulty

    def test_mark_finalized_blocks(self, tmp_path):
        """Test marking finalized blocks"""
        bc = Blockchain(data_dir=str(tmp_path))
        manager = AdvancedConsensusManager(bc)
        wallet = Wallet()

        # Mine many blocks
        for i in range(110):
            bc.mine_pending_transactions(wallet.address)

        manager.mark_finalized_blocks()

        # First blocks should be finalized
        assert manager.finality_tracker.is_finalized(0) is True

    def test_get_consensus_stats(self, tmp_path):
        """Test getting consensus statistics"""
        bc = Blockchain(data_dir=str(tmp_path))
        manager = AdvancedConsensusManager(bc)

        stats = manager.get_consensus_stats()

        assert "propagation" in stats
        assert "orphan_pool" in stats
        assert "finality" in stats
        assert "difficulty" in stats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
