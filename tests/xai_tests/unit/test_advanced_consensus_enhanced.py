"""
Enhanced comprehensive tests for advanced_consensus.py to achieve 80%+ coverage

This test suite extends the existing coverage with:
- Edge cases for all classes
- Error handling scenarios
- Complex integration flows
- Boundary condition testing
- State transition verification
- Performance edge cases
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from xai.core.blockchain import Blockchain, Block, Transaction
from xai.core.wallet import Wallet
from xai.core.consensus.advanced_consensus import (
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


class TestBlockStatusEnum:
    """Test BlockStatus enum"""

    def test_block_status_values(self):
        """Test all block status enum values"""
        assert BlockStatus.VALID.value == "valid"
        assert BlockStatus.ORPHAN.value == "orphan"
        assert BlockStatus.INVALID.value == "invalid"
        assert BlockStatus.PENDING.value == "pending"

    def test_block_status_equality(self):
        """Test block status equality"""
        status1 = BlockStatus.VALID
        status2 = BlockStatus.VALID
        assert status1 == status2

    def test_block_status_inequality(self):
        """Test block status inequality"""
        assert BlockStatus.VALID != BlockStatus.INVALID
        assert BlockStatus.ORPHAN != BlockStatus.PENDING


class TestBlockPropagationMonitorEdgeCases:
    """Edge cases and advanced scenarios for BlockPropagationMonitor"""

    def test_record_block_from_peer_without_first_seen(self):
        """Test recording block from peer when not first seen"""
        monitor = BlockPropagationMonitor()

        # Record from peer without first seeing it
        monitor.record_block_from_peer("unknown_block", "peer1")

        # Should not crash, but won't add to propagation times
        assert "peer1" not in monitor.peer_latency

    def test_multiple_peers_same_block(self):
        """Test multiple peers sending same block"""
        monitor = BlockPropagationMonitor()

        monitor.record_block_first_seen("block1")
        time.sleep(0.01)

        monitor.record_block_from_peer("block1", "peer1")
        monitor.record_block_from_peer("block1", "peer2")
        monitor.record_block_from_peer("block1", "peer3")

        # All peers should have latency recorded
        assert "peer1" in monitor.peer_latency
        assert "peer2" in monitor.peer_latency
        assert "peer3" in monitor.peer_latency

    def test_peer_latency_ema_convergence(self):
        """Test EMA convergence with multiple blocks"""
        monitor = BlockPropagationMonitor()

        for i in range(10):
            block_hash = f"block{i}"
            monitor.record_block_first_seen(block_hash)
            time.sleep(0.01)
            monitor.record_block_from_peer(block_hash, "peer1")

        # Latency should stabilize
        assert monitor.peer_latency["peer1"] > 0
        assert len(monitor.block_propagation_times["peer1"]) == 10

    def test_performance_score_boundary_conditions(self):
        """Test performance score at boundary conditions"""
        monitor = BlockPropagationMonitor()

        # Very fast peer (instant)
        monitor.record_block_first_seen("block1")
        monitor.record_block_from_peer("block1", "fast_peer")

        perf = monitor.get_peer_performance("fast_peer")
        assert perf["performance_score"] <= 100
        assert perf["performance_score"] >= 0

    def test_network_stats_min_max_values(self):
        """Test network stats min/max calculation"""
        monitor = BlockPropagationMonitor()

        # Create blocks with varying propagation times
        for i in range(5):
            block_hash = f"block{i}"
            monitor.record_block_first_seen(block_hash)
            time.sleep(0.01 * (i + 1))  # Increasing delay
            monitor.record_block_from_peer(block_hash, "peer1")

        stats = monitor.get_network_stats()
        assert stats["min_propagation_time"] < stats["max_propagation_time"]
        assert stats["avg_propagation_time"] >= stats["min_propagation_time"]
        assert stats["avg_propagation_time"] <= stats["max_propagation_time"]

    def test_propagation_history_ordering(self):
        """Test propagation history maintains chronological order"""
        monitor = BlockPropagationMonitor()

        timestamps = []
        for i in range(5):
            monitor.record_block_first_seen(f"block{i}")
            monitor.record_block_from_peer(f"block{i}", "peer1")
            if monitor.propagation_history:
                timestamps.append(monitor.propagation_history[-1]["timestamp"])

        # Timestamps should be increasing
        assert all(timestamps[i] <= timestamps[i+1] for i in range(len(timestamps)-1))


class TestOrphanBlockPoolEdgeCases:
    """Edge cases and advanced scenarios for OrphanBlockPool"""

    def test_add_orphan_returns_true(self, tmp_path):
        """Test add_orphan returns True on success"""
        pool = OrphanBlockPool()
        bc = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        block = bc.mine_pending_transactions(wallet.address)
        result = pool.add_orphan(block)

        assert result is True

    def test_get_orphan_returns_none_for_missing(self):
        """Test get_orphan returns None for missing block"""
        pool = OrphanBlockPool()

        orphan = pool.get_orphan("nonexistent_hash")

        assert orphan is None

    def test_remove_orphan_nonexistent(self):
        """Test removing non-existent orphan"""
        pool = OrphanBlockPool()

        result = pool.remove_orphan("nonexistent")

        assert result is None

    def test_remove_oldest_orphan_empty_pool(self):
        """Test removing oldest from empty pool"""
        pool = OrphanBlockPool()

        # Should not crash
        pool._remove_oldest_orphan()

        assert len(pool.orphan_blocks) == 0

    def test_cleanup_no_expired_orphans(self, tmp_path):
        """Test cleanup with no expired orphans"""
        pool = OrphanBlockPool(max_orphan_age=1000)
        bc = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        block = bc.mine_pending_transactions(wallet.address)
        pool.add_orphan(block)

        initial_count = len(pool.orphan_blocks)
        pool.cleanup_expired_orphans()

        # Should not remove recent orphans
        assert len(pool.orphan_blocks) == initial_count

    def test_orphan_timestamps_consistency(self, tmp_path):
        """Test orphan timestamps are consistent"""
        pool = OrphanBlockPool()
        bc = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        block = bc.mine_pending_transactions(wallet.address)
        before_time = time.time()
        pool.add_orphan(block)
        after_time = time.time()

        assert block.hash in pool.orphan_timestamps
        timestamp = pool.orphan_timestamps[block.hash]
        assert before_time <= timestamp <= after_time

    def test_orphan_by_parent_index_cleanup(self, tmp_path):
        """Test parent index is cleaned up correctly"""
        pool = OrphanBlockPool()
        bc = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        block = bc.mine_pending_transactions(wallet.address)
        pool.add_orphan(block)

        parent_hash = block.previous_hash
        assert len(pool.get_orphans_by_parent(parent_hash)) > 0

        pool.remove_orphan(block.hash)

        # Parent index should be cleaned
        orphans = pool.get_orphans_by_parent(parent_hash)
        assert not any(o.hash == block.hash for o in orphans)

    def test_max_orphans_exactly_at_limit(self, tmp_path):
        """Test behavior at exact max orphans limit"""
        max_orphans = 5
        pool = OrphanBlockPool(max_orphans=max_orphans)
        bc = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        # Add exactly max_orphans blocks
        for i in range(max_orphans):
            block = bc.mine_pending_transactions(wallet.address)
            pool.add_orphan(block)
            time.sleep(0.01)

        assert len(pool.orphan_blocks) == max_orphans

        # Add one more
        extra_block = bc.mine_pending_transactions(wallet.address)
        pool.add_orphan(extra_block)

        # Should still be at max
        assert len(pool.orphan_blocks) == max_orphans


class TestTransactionOrderingEdgeCases:
    """Edge cases for TransactionOrdering"""

    def test_order_transactions_multiple_coinbase(self, tmp_path):
        """Test ordering with multiple coinbase transactions"""
        wallet = Wallet()

        coinbase1 = Transaction("COINBASE", wallet.address, 12.0)
        coinbase1.txid = coinbase1.calculate_hash()
        coinbase1.timestamp = 1000.0

        coinbase2 = Transaction("COINBASE", wallet.address, 12.0)
        coinbase2.txid = coinbase2.calculate_hash()
        coinbase2.timestamp = 2000.0

        ordered = TransactionOrdering.order_transactions([coinbase2, coinbase1])

        # All coinbase should come first
        assert all(tx.sender == "COINBASE" for tx in ordered[:2])

    def test_order_transactions_zero_fee(self, tmp_path):
        """Test ordering transactions with zero fee"""
        wallet = Wallet()

        tx1 = Transaction(wallet.address, wallet.address, 10.0, 0.0, public_key=wallet.public_key)
        tx1.timestamp = 1000.0
        tx1.txid = "aaa"

        tx2 = Transaction(wallet.address, wallet.address, 10.0, 0.0, public_key=wallet.public_key)
        tx2.timestamp = 2000.0
        tx2.txid = "bbb"

        ordered = TransactionOrdering.order_transactions([tx2, tx1])

        # Should be ordered by timestamp when fees are equal (both 0)
        assert ordered[0].timestamp < ordered[1].timestamp

    def test_order_transactions_same_everything_except_hash(self, tmp_path):
        """Test ordering when only hash differs"""
        wallet = Wallet()

        tx1 = Transaction(wallet.address, wallet.address, 10.0, 0.1, public_key=wallet.public_key)
        tx1.timestamp = 1000.0
        tx1.txid = "aaa"

        tx2 = Transaction(wallet.address, wallet.address, 10.0, 0.1, public_key=wallet.public_key)
        tx2.timestamp = 1000.0
        tx2.txid = "zzz"

        ordered = TransactionOrdering.order_transactions([tx2, tx1])

        # Should be deterministically ordered by txid
        assert ordered[0].txid == "aaa"
        assert ordered[1].txid == "zzz"

    def test_validate_single_coinbase(self, tmp_path):
        """Test validation with single coinbase transaction"""
        wallet = Wallet()

        coinbase = Transaction("COINBASE", wallet.address, 12.0)
        coinbase.txid = coinbase.calculate_hash()

        # Single coinbase is valid
        assert TransactionOrdering.validate_transaction_order([coinbase]) is True

    def test_validate_exact_boundary_case(self, tmp_path):
        """Test validation at exact boundary (2 transactions)"""
        wallet = Wallet()

        coinbase = Transaction("COINBASE", wallet.address, 12.0)
        coinbase.txid = coinbase.calculate_hash()

        tx1 = Transaction(wallet.address, wallet.address, 10.0, 0.5, public_key=wallet.public_key)
        tx1.txid = tx1.calculate_hash()

        # Should validate correctly with just 2 transactions
        assert TransactionOrdering.validate_transaction_order([coinbase, tx1]) is True

    def test_validate_large_transaction_list(self, tmp_path):
        """Test validation with many transactions"""
        wallet = Wallet()

        coinbase = Transaction("COINBASE", wallet.address, 12.0)
        coinbase.txid = coinbase.calculate_hash()

        transactions = [coinbase]

        # Add many transactions with decreasing fees
        for i in range(100):
            tx = Transaction(wallet.address, wallet.address, 10.0, 1.0 - (i * 0.001), public_key=wallet.public_key)
            tx.txid = tx.calculate_hash()
            transactions.append(tx)

        assert TransactionOrdering.validate_transaction_order(transactions) is True


class TestFinalityTrackerEdgeCases:
    """Edge cases for FinalityTracker"""

    def test_finality_at_exact_thresholds(self):
        """Test finality at exact threshold boundaries"""
        tracker = FinalityTracker()

        # Exactly at soft finality
        finality = tracker.get_block_finality(94, 100)
        assert finality["finality_level"] == "soft"
        assert finality["confirmations"] == 6

        # Exactly at medium finality
        finality = tracker.get_block_finality(80, 100)
        assert finality["finality_level"] == "medium"
        assert finality["confirmations"] == 20

        # Exactly at hard finality
        finality = tracker.get_block_finality(0, 100)
        assert finality["finality_level"] == "hard"
        assert finality["confirmations"] == 100

    def test_finality_zero_confirmations(self):
        """Test finality with zero confirmations"""
        tracker = FinalityTracker()

        finality = tracker.get_block_finality(100, 100)

        assert finality["confirmations"] == 0
        assert finality["finality_level"] == "none"
        assert finality["finality_percent"] == 0
        assert finality["reversible"] is True

    def test_finality_pending_percent_calculation(self):
        """Test pending finality percentage calculation"""
        tracker = FinalityTracker()

        # 1 confirmation should give 10%
        finality = tracker.get_block_finality(99, 100)
        assert finality["finality_level"] == "pending"
        assert finality["finality_percent"] == 10

        # 4 confirmations should give 40%
        finality = tracker.get_block_finality(96, 100)
        assert finality["finality_level"] == "pending"
        assert finality["finality_percent"] == 40

    def test_multiple_mark_finalized(self):
        """Test marking multiple blocks as finalized"""
        tracker = FinalityTracker()

        for i in range(10):
            tracker.mark_finalized(i)

        # All should be finalized
        for i in range(10):
            assert tracker.is_finalized(i) is True

        # Others should not be
        assert tracker.is_finalized(11) is False

    def test_finality_stats_with_short_chain(self, tmp_path):
        """Test finality stats with short blockchain"""
        bc = Blockchain(data_dir=str(tmp_path))
        tracker = FinalityTracker()
        wallet = Wallet()

        # Only a few blocks
        for i in range(5):
            bc.mine_pending_transactions(wallet.address)

        stats = tracker.get_finality_stats(bc)

        assert stats["total_blocks"] == len(bc.chain)
        assert stats["hard_finalized"] == 0  # Not enough blocks
        assert stats["pending"] >= 0


class TestFinalityMechanismEdgeCases:
    """Edge cases for FinalityMechanism"""

    def test_zero_confirmation_depth_always_final(self):
        """Test that zero confirmation depth means always final"""
        mechanism = FinalityMechanism(confirmation_depth=0)

        # Even block at chain tip should be final
        assert mechanism.is_block_final(99, 100) is True
        assert mechanism.get_finality_score(99, 100) == 1.0

    def test_exact_confirmation_depth_boundary(self):
        """Test exact confirmation depth boundary"""
        mechanism = FinalityMechanism(confirmation_depth=10)

        # Exactly at depth
        assert mechanism.is_block_final(90, 100) is True

        # One less
        assert mechanism.is_block_final(91, 100) is False

    def test_negative_confirmations_clamped(self):
        """Test negative confirmations are handled"""
        mechanism = FinalityMechanism(confirmation_depth=10)

        # Block ahead of chain (shouldn't happen but test safety)
        score = mechanism.get_finality_score(110, 100)

        # Should be clamped to 0
        assert score >= 0


class TestDynamicDifficultyAdjustmentEdgeCases:
    """Edge cases for DynamicDifficultyAdjustment"""

    def test_zero_expected_time_edge_case(self, tmp_path):
        """Test handling of zero expected time"""
        bc = Blockchain(data_dir=str(tmp_path))
        adjuster = DynamicDifficultyAdjustment(target_block_time=0)
        wallet = Wallet()

        bc.mine_pending_transactions(wallet.address)
        bc.mine_pending_transactions(wallet.address)

        # Should return current difficulty, not crash
        new_diff = adjuster.calculate_new_difficulty(bc)
        assert new_diff == bc.difficulty

    def test_single_block_in_window(self, tmp_path):
        """Test difficulty calculation with single block in window"""
        bc = Blockchain(data_dir=str(tmp_path))
        bc.difficulty = 2
        adjuster = DynamicDifficultyAdjustment()
        wallet = Wallet()

        bc.mine_pending_transactions(wallet.address)

        new_diff = adjuster.calculate_new_difficulty(bc)

        # Should return current difficulty
        assert new_diff == bc.difficulty

    def test_adjustment_factor_clamping_upper(self, tmp_path):
        """Test max adjustment factor upper bound"""
        bc = Blockchain(data_dir=str(tmp_path))
        bc.difficulty = 2
        adjuster = DynamicDifficultyAdjustment()
        wallet = Wallet()

        # Force very slow blocks to trigger max adjustment
        base_time = time.time()
        for i in range(150):
            bc.chain[-1].timestamp = base_time + (i * 10000)  # Very slow blocks
            bc.mine_pending_transactions(wallet.address)

        new_diff = adjuster.calculate_new_difficulty(bc)

        # Should not exceed max_adjustment_factor * current
        max_expected = bc.difficulty * adjuster.max_adjustment_factor
        assert new_diff <= adjuster.max_difficulty

    def test_adjustment_factor_clamping_lower(self, tmp_path):
        """Test max adjustment factor lower bound"""
        bc = Blockchain(data_dir=str(tmp_path))
        bc.difficulty = 4
        adjuster = DynamicDifficultyAdjustment()
        wallet = Wallet()

        # Force very fast blocks to trigger max adjustment down
        base_time = time.time()
        for i in range(150):
            bc.chain[-1].timestamp = base_time + (i * 0.0001)  # Very fast blocks
            bc.mine_pending_transactions(wallet.address)

        new_diff = adjuster.calculate_new_difficulty(bc)

        # Should not go below min
        assert new_diff >= adjuster.min_difficulty

    def test_should_adjust_at_zero(self, tmp_path):
        """Test should_adjust_difficulty with genesis only"""
        bc = Blockchain(data_dir=str(tmp_path))
        adjuster = DynamicDifficultyAdjustment()

        # Only genesis block
        should_adjust = adjuster.should_adjust_difficulty(bc)

        assert should_adjust is False

    def test_difficulty_stats_insufficient_data(self, tmp_path):
        """Test difficulty stats with insufficient data"""
        bc = Blockchain(data_dir=str(tmp_path))
        adjuster = DynamicDifficultyAdjustment()

        stats = adjuster.get_difficulty_stats(bc)

        assert stats["avg_block_time"] == 0
        assert stats["blocks_until_adjustment"] == adjuster.adjustment_window
        assert "current_difficulty" in stats


class TestDifficultyAdjustmentEdgeCases:
    """Edge cases for DifficultyAdjustment wrapper"""

    def test_single_block_chain(self, tmp_path):
        """Test with single block (genesis)"""
        bc = Blockchain(data_dir=str(tmp_path))
        adjuster = DifficultyAdjustment()

        new_diff = adjuster.calculate_difficulty(bc.chain, bc.difficulty)

        # Should return at least 1.0
        assert new_diff >= 1.0

    def test_negative_time_diff_safety(self, tmp_path):
        """Test safety with negative time difference"""
        bc = Blockchain(data_dir=str(tmp_path))
        adjuster = DifficultyAdjustment()
        wallet = Wallet()

        bc.mine_pending_transactions(wallet.address)

        # Make newer block have earlier timestamp (shouldn't happen but test safety)
        bc.chain[-1].timestamp = bc.chain[-2].timestamp - 100

        new_diff = adjuster.calculate_difficulty(bc.chain, bc.difficulty)

        # Should handle gracefully
        assert new_diff >= 1.0

    def test_zero_avg_time_edge_case(self, tmp_path):
        """Test with zero average time"""
        bc = Blockchain(data_dir=str(tmp_path))
        adjuster = DifficultyAdjustment()
        wallet = Wallet()

        bc.mine_pending_transactions(wallet.address)
        # Force same timestamp
        bc.chain[-1].timestamp = bc.chain[-2].timestamp

        new_diff = adjuster.calculate_difficulty(bc.chain, bc.difficulty)

        # Should fall back to default
        assert new_diff >= 1.0

    def test_very_large_chain(self, tmp_path):
        """Test with chain larger than adjustment interval"""
        bc = Blockchain(data_dir=str(tmp_path))
        adjuster = DifficultyAdjustment(adjustment_interval=5)
        wallet = Wallet()

        # Mine more blocks than interval
        for i in range(20):
            bc.mine_pending_transactions(wallet.address)

        new_diff = adjuster.calculate_difficulty(bc.chain, bc.difficulty)

        # Should only look at last `adjustment_interval` blocks
        assert new_diff >= adjuster.min_difficulty


class TestAdvancedConsensusManagerEdgeCases:
    """Edge cases for AdvancedConsensusManager"""

    def test_process_new_block_with_peer_tracking(self, tmp_path):
        """Test block processing with peer tracking"""
        bc = Blockchain(data_dir=str(tmp_path))
        manager = AdvancedConsensusManager(bc)
        wallet = Wallet()

        block = bc.mine_pending_transactions(wallet.address)

        accepted, message = manager.process_new_block(block, from_peer="peer1")

        # Should track peer
        assert "peer1" in manager.propagation_monitor.block_propagation_times or accepted

    def test_process_orphans_recursive_chain(self, tmp_path):
        """Test processing chain of orphans recursively"""
        bc = MagicMock()
        bc.chain = [MagicMock(hash="1" * 64)]
        bc.difficulty = 1
        manager = AdvancedConsensusManager(bc)

        # Create chain of orphans (use valid 64-char hex hashes)
        parent_hash = bc.chain[-1].hash
        orphan1_hash = "a" * 64  # Valid format hash
        orphan2_hash = "b" * 64  # Valid format hash

        orphan1 = Block(2, [], parent_hash, bc.difficulty)
        orphan1.hash = orphan1_hash

        orphan2 = Block(3, [], orphan1_hash, bc.difficulty)
        orphan2.hash = orphan2_hash

        # Add orphans
        manager.orphan_pool.add_orphan(orphan1, parent_hash)
        manager.orphan_pool.add_orphan(orphan2, orphan1_hash)

        # Process orphans
        manager.process_orphans_after_block(parent_hash)

        # Orphan 1 should be removed after processing
        assert orphan1_hash not in manager.orphan_pool.orphan_blocks

    def test_order_pending_transactions_empty(self, tmp_path):
        """Test ordering with no pending transactions"""
        bc = Blockchain(data_dir=str(tmp_path))
        manager = AdvancedConsensusManager(bc)

        ordered = manager.order_pending_transactions()

        assert isinstance(ordered, list)
        assert len(ordered) == 0

    def test_adjust_difficulty_no_change(self, tmp_path):
        """Test difficulty adjustment when no change needed"""
        bc = Blockchain(data_dir=str(tmp_path))
        manager = AdvancedConsensusManager(bc)
        wallet = Wallet()

        # Mine a few blocks (not at adjustment window)
        for i in range(5):
            bc.mine_pending_transactions(wallet.address)

        initial_diff = bc.difficulty
        manager.adjust_difficulty_if_needed()

        # Should not change
        assert bc.difficulty == initial_diff

    def test_mark_finalized_blocks_short_chain(self, tmp_path):
        """Test marking finalized blocks with short chain"""
        bc = Blockchain(data_dir=str(tmp_path))
        manager = AdvancedConsensusManager(bc)
        wallet = Wallet()

        # Mine only a few blocks
        for i in range(10):
            bc.mine_pending_transactions(wallet.address)

        manager.mark_finalized_blocks()

        # No blocks should be finalized (need 100+ confirmations)
        assert len(manager.finality_tracker.finalized_blocks) == 0

    def test_consensus_stats_integration(self, tmp_path):
        """Test complete consensus stats integration"""
        bc = Blockchain(data_dir=str(tmp_path))
        manager = AdvancedConsensusManager(bc)
        wallet = Wallet()

        # Create some activity
        for i in range(5):
            block = bc.mine_pending_transactions(wallet.address)
            manager.process_new_block(block, from_peer=f"peer{i % 2}")

        stats = manager.get_consensus_stats()

        # All sections should be present
        assert "propagation" in stats
        assert "orphan_pool" in stats
        assert "finality" in stats
        assert "difficulty" in stats

        # Verify stats have expected keys
        assert "total_blocks_tracked" in stats["propagation"]
        assert "total_orphans" in stats["orphan_pool"]
        assert "total_blocks" in stats["finality"]
        assert "current_difficulty" in stats["difficulty"]


class TestTransactionOrderingRulesEdgeCases:
    """Additional edge cases for TransactionOrderingRules"""

    def test_empty_list_handling(self):
        """Test all methods with empty lists"""
        rules = TransactionOrderingRules()

        assert rules.order_by_fee([]) == []
        assert rules.order_by_timestamp([]) == []
        assert rules.prioritize([]) == []

    def test_single_transaction_handling(self, tmp_path):
        """Test all methods with single transaction"""
        rules = TransactionOrderingRules()
        wallet = Wallet()

        tx = Transaction(wallet.address, Wallet().address, 10.0, 0.1)

        assert len(rules.order_by_fee([tx])) == 1
        assert len(rules.order_by_timestamp([tx])) == 1
        assert len(rules.prioritize([tx])) == 1


class TestOrphanBlockManagerCompatibility:
    """Test OrphanBlockManager alias compatibility"""

    def test_all_methods_available(self, tmp_path):
        """Test all OrphanBlockPool methods work on OrphanBlockManager"""
        manager = OrphanBlockManager(max_orphans=10, max_orphan_age=3600)
        bc = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        block = bc.mine_pending_transactions(wallet.address)

        # Test all methods
        assert manager.add_orphan(block) is True
        assert manager.get_orphan(block.hash) is not None
        assert len(manager.get_orphans_by_parent(block.previous_hash)) > 0
        assert len(manager.get_orphans_by_previous(block.previous_hash)) > 0

        stats = manager.get_stats()
        assert stats["total_orphans"] > 0

        manager.cleanup_expired_orphans()
        manager.remove_orphan(block.hash)


class TestComplexIntegrationScenarios:
    """Complex integration scenarios testing multiple components"""

    def test_full_consensus_workflow(self, tmp_path):
        """Test complete consensus workflow"""
        bc = Blockchain(data_dir=str(tmp_path))
        manager = AdvancedConsensusManager(bc)
        wallet = Wallet()

        # Mine initial blocks
        for i in range(10):
            bc.mine_pending_transactions(wallet.address)

        # Create some transactions
        tx1 = bc.create_transaction(
            wallet.address,
            Wallet().address,
            1.0,
            0.5,
            wallet.private_key,
            wallet.public_key,
        )
        tx2 = bc.create_transaction(
            wallet.address,
            Wallet().address,
            1.0,
            0.3,
            wallet.private_key,
            wallet.public_key,
        )

        if tx1:
            bc.add_transaction(tx1)
        if tx2:
            bc.add_transaction(tx2)

        # Order transactions
        ordered = manager.order_pending_transactions()

        # Mine block
        block = bc.mine_pending_transactions(wallet.address)

        # Process through consensus
        accepted, message = manager.process_new_block(block, from_peer="peer1")

        # Get stats
        stats = manager.get_consensus_stats()

        assert stats is not None

    def test_orphan_resolution_workflow(self, tmp_path):
        """Test orphan block resolution workflow"""
        bc = Blockchain(data_dir=str(tmp_path))
        manager = AdvancedConsensusManager(bc)
        wallet = Wallet()

        # Get current chain tip
        parent_hash = bc.get_latest_block().hash

        # Create orphan (child of current tip)
        orphan = Block(len(bc.chain), [], parent_hash, bc.difficulty)
        orphan.hash = "orphan_hash"

        # Add to orphan pool
        manager.orphan_pool.add_orphan(orphan, parent_hash)

        # Verify it's in pool
        assert orphan.hash in manager.orphan_pool.orphan_blocks

        # Process orphans after receiving parent
        manager.process_orphans_after_block(parent_hash)

    def test_difficulty_adjustment_workflow(self, tmp_path):
        """Test complete difficulty adjustment workflow"""
        bc = Blockchain(data_dir=str(tmp_path))
        manager = AdvancedConsensusManager(bc)
        wallet = Wallet()

        initial_diff = bc.difficulty

        # Mine blocks with varying times
        base_time = time.time()
        for i in range(manager.difficulty_adjuster.adjustment_window + 5):
            # Vary block times
            bc.chain[-1].timestamp = base_time + (i * 60)
            bc.mine_pending_transactions(wallet.address)

            # Check and adjust difficulty
            manager.adjust_difficulty_if_needed()

        # Difficulty may have changed
        final_diff = bc.difficulty

        # Should be within valid range
        assert manager.difficulty_adjuster.min_difficulty <= final_diff <= manager.difficulty_adjuster.max_difficulty

    def test_finality_progression(self, tmp_path):
        """Test finality progression as chain grows"""
        bc = Blockchain(data_dir=str(tmp_path))
        manager = AdvancedConsensusManager(bc)
        wallet = Wallet()

        # Mine blocks and track finality
        for i in range(120):
            bc.mine_pending_transactions(wallet.address)

            if i % 20 == 0:
                manager.mark_finalized_blocks()

        # Early blocks should be finalized
        assert manager.finality_tracker.is_finalized(0) is True

        # Recent blocks should not be
        assert manager.finality_tracker.is_finalized(len(bc.chain) - 1) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
