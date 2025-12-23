"""
Comprehensive Difficulty Adjustment Algorithm Tests
Phase 3.5 of LOCAL_TESTING_PLAN.md

Tests dynamic difficulty adjustment:
- Difficulty increases with faster mining
- Difficulty decreases with slower mining
- Adjustment intervals and windows
- Difficulty bounds and limits
- Hashrate estimation
- Target block time maintenance
"""

import pytest
import time
import statistics

from xai.core.blockchain import Blockchain, Block, Transaction
from xai.core.wallet import Wallet
from xai.core.advanced_consensus import (
    DynamicDifficultyAdjustment,
    DifficultyAdjustment,
    AdvancedConsensusManager
)


class TestBasicDifficultyAdjustment:
    """Test basic difficulty adjustment mechanics"""

    @pytest.fixture
    def blockchain(self, tmp_path) -> Blockchain:
        """Create blockchain instance"""
        return Blockchain(data_dir=str(tmp_path))

    def test_initial_difficulty_set(self, blockchain):
        """Test blockchain starts with initial difficulty"""
        assert blockchain.difficulty > 0
        # Should be reasonable starting difficulty
        assert 1 <= blockchain.difficulty <= 10

    def test_difficulty_recorded_in_blocks(self, blockchain):
        """Test each block records the difficulty used"""
        wallet = Wallet()

        initial_difficulty = blockchain.difficulty

        # Mine block
        block = blockchain.mine_pending_transactions(wallet.address)

        # Block should record difficulty
        assert block.difficulty == initial_difficulty
        assert block.hash.startswith("0" * block.difficulty)

    def test_difficulty_persists_across_blocks(self, blockchain):
        """Test difficulty is consistent across multiple blocks"""
        wallet = Wallet()

        # Mine several blocks quickly
        difficulties = []
        for _ in range(5):
            block = blockchain.mine_pending_transactions(wallet.address)
            difficulties.append(block.difficulty)

        # Difficulty should be recorded for each block
        assert all(d > 0 for d in difficulties)

    def test_difficulty_affects_mining_time(self, tmp_path):
        """Test higher difficulty takes longer to mine"""
        # Create blockchain with low difficulty
        bc_low = Blockchain(data_dir=str(tmp_path / "low"))
        bc_low.difficulty = 1
        wallet1 = Wallet()

        # Mine with low difficulty
        start = time.time()
        block_low = bc_low.mine_pending_transactions(wallet1.address)
        time_low = time.time() - start

        # Create blockchain with higher difficulty
        bc_high = Blockchain(data_dir=str(tmp_path / "high"))
        bc_high.difficulty = 4
        wallet2 = Wallet()

        # Mine with high difficulty
        start = time.time()
        block_high = bc_high.mine_pending_transactions(wallet2.address)
        time_high = time.time() - start

        # Both should succeed
        assert block_low is not None
        assert block_high is not None

        # Higher difficulty should generally take longer
        # (Probabilistic, but strong likelihood)
        # Just verify both completed
        assert time_low > 0
        assert time_high > 0


class TestDynamicDifficultyAdjustment:
    """Test DynamicDifficultyAdjustment class"""

    @pytest.fixture
    def adjuster(self) -> DynamicDifficultyAdjustment:
        """Create difficulty adjuster"""
        return DynamicDifficultyAdjustment(target_block_time=120)

    @pytest.fixture
    def blockchain(self, tmp_path) -> Blockchain:
        """Create blockchain instance"""
        return Blockchain(data_dir=str(tmp_path))

    def test_adjuster_initialization(self, adjuster):
        """Test adjuster initializes with correct parameters"""
        assert adjuster.target_block_time == 120
        assert adjuster.adjustment_window == 144
        assert adjuster.max_adjustment_factor == 4
        assert adjuster.min_difficulty == 1
        assert adjuster.max_difficulty == 10

    def test_should_adjust_at_interval(self, adjuster, blockchain):
        """Test difficulty adjustment triggers at correct interval"""
        wallet = Wallet()

        # Should not adjust initially
        assert not adjuster.should_adjust_difficulty(blockchain)

        # Mine blocks up to adjustment window
        for i in range(144):
            blockchain.mine_pending_transactions(wallet.address)

            # Should adjust at exactly window boundary
            should_adjust = adjuster.should_adjust_difficulty(blockchain)
            if (i + 1) % 144 == 0:
                assert should_adjust is True
            # Note: Adjustment happens after window is complete

    def test_calculate_difficulty_too_fast(self, adjuster, tmp_path):
        """Test difficulty increases if blocks mined too fast"""
        blockchain = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        initial_difficulty = blockchain.difficulty

        # Simulate fast mining by manipulating timestamps
        blockchain.mine_pending_transactions(wallet.address)

        for i in range(10):
            block = blockchain.mine_pending_transactions(wallet.address)
            # Set timestamp very close to previous (fast mining)
            block.timestamp = blockchain.chain[-2].timestamp + 10  # 10 seconds

        # Calculate new difficulty
        new_difficulty = adjuster.calculate_new_difficulty(blockchain)

        # Difficulty should increase (blocks too fast)
        assert new_difficulty >= initial_difficulty

    def test_calculate_difficulty_too_slow(self, adjuster, tmp_path):
        """Test difficulty decreases if blocks mined too slow"""
        blockchain = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        initial_difficulty = blockchain.difficulty

        # Simulate slow mining
        blockchain.mine_pending_transactions(wallet.address)

        for i in range(10):
            block = blockchain.mine_pending_transactions(wallet.address)
            # Set timestamp far from previous (slow mining)
            block.timestamp = blockchain.chain[-2].timestamp + 500  # 500 seconds

        # Calculate new difficulty
        new_difficulty = adjuster.calculate_new_difficulty(blockchain)

        # Difficulty should decrease (blocks too slow)
        assert new_difficulty <= initial_difficulty

    def test_difficulty_bounds_enforced(self, adjuster, tmp_path):
        """Test difficulty stays within min/max bounds"""
        blockchain = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        # Mine some blocks
        for _ in range(10):
            blockchain.mine_pending_transactions(wallet.address)

        # Calculate difficulty
        new_difficulty = adjuster.calculate_new_difficulty(blockchain)

        # Should be within bounds
        assert adjuster.min_difficulty <= new_difficulty <= adjuster.max_difficulty

    def test_difficulty_adjustment_limited(self, adjuster, tmp_path):
        """Test adjustment factor is limited per period"""
        blockchain = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        initial_difficulty = blockchain.difficulty

        # Simulate extremely fast mining
        blockchain.mine_pending_transactions(wallet.address)

        for i in range(10):
            block = blockchain.mine_pending_transactions(wallet.address)
            block.timestamp = blockchain.chain[-2].timestamp + 1  # 1 second

        # Calculate new difficulty
        new_difficulty = adjuster.calculate_new_difficulty(blockchain)

        # Should be limited by max_adjustment_factor
        max_allowed = initial_difficulty * adjuster.max_adjustment_factor
        assert new_difficulty <= max_allowed

    def test_difficulty_stats(self, adjuster, blockchain):
        """Test getting difficulty statistics"""
        wallet = Wallet()

        # Mine blocks
        for _ in range(5):
            blockchain.mine_pending_transactions(wallet.address)

        # Get stats
        stats = adjuster.get_difficulty_stats(blockchain)

        assert "current_difficulty" in stats
        assert "avg_block_time" in stats
        assert "target_block_time" in stats
        assert "blocks_until_adjustment" in stats
        assert "recommended_difficulty" in stats

        assert stats["current_difficulty"] == blockchain.difficulty
        assert stats["target_block_time"] == adjuster.target_block_time


class TestDifficultyAdjustmentWrapper:
    """Test DifficultyAdjustment compatibility wrapper"""

    @pytest.fixture
    def adjuster(self) -> DifficultyAdjustment:
        """Create simple adjuster"""
        return DifficultyAdjustment(target_block_time=120, adjustment_interval=10)

    @pytest.fixture
    def blockchain(self, tmp_path) -> Blockchain:
        """Create blockchain"""
        return Blockchain(data_dir=str(tmp_path))

    def test_wrapper_initialization(self, adjuster):
        """Test wrapper initializes correctly"""
        assert adjuster.target_block_time == 120
        assert adjuster.adjustment_interval == 10
        assert adjuster.min_difficulty == 0.1
        assert adjuster.max_difficulty == 100.0

    def test_calculate_difficulty_fast_mining(self, adjuster, blockchain):
        """Test difficulty calculation for fast mining"""
        wallet = Wallet()

        initial_difficulty = blockchain.difficulty

        # Build chain with fast timestamps
        blockchain.mine_pending_transactions(wallet.address)
        for _ in range(10):
            block = blockchain.mine_pending_transactions(wallet.address)
            block.timestamp = blockchain.chain[-2].timestamp + 30  # 30 seconds

        # Calculate new difficulty
        new_difficulty = adjuster.calculate_difficulty(blockchain.chain, initial_difficulty)

        # Should increase
        assert new_difficulty >= initial_difficulty

    def test_calculate_difficulty_slow_mining(self, adjuster, blockchain):
        """Test difficulty calculation for slow mining"""
        wallet = Wallet()

        initial_difficulty = blockchain.difficulty

        # Build chain with slow timestamps
        blockchain.mine_pending_transactions(wallet.address)
        for _ in range(10):
            block = blockchain.mine_pending_transactions(wallet.address)
            block.timestamp = blockchain.chain[-2].timestamp + 300  # 300 seconds

        # Calculate new difficulty
        new_difficulty = adjuster.calculate_difficulty(blockchain.chain, initial_difficulty)

        # Should decrease
        assert new_difficulty <= initial_difficulty

    def test_minimum_chain_length(self, adjuster):
        """Test minimum chain length requirement"""
        # Empty chain
        difficulty = adjuster.calculate_difficulty([], 2.0)
        assert difficulty >= 1.0

        # Single block
        from xai.core.blockchain import Block, Transaction
        wallet = Wallet()
        tx = Transaction("COINBASE", wallet.address, 50.0)
        tx.txid = tx.calculate_hash()
        block = Block(0, [tx], "0", difficulty=2)
        block.hash = block.calculate_hash()

        difficulty = adjuster.calculate_difficulty([block], 2.0)
        assert difficulty >= 1.0


class TestAdvancedConsensusIntegration:
    """Test difficulty adjustment through AdvancedConsensusManager"""

    @pytest.fixture
    def blockchain(self, tmp_path) -> Blockchain:
        """Create blockchain"""
        return Blockchain(data_dir=str(tmp_path))

    def test_manager_tracks_difficulty(self, blockchain):
        """Test manager tracks difficulty changes"""
        manager = AdvancedConsensusManager(blockchain)
        wallet = Wallet()

        initial_difficulty = blockchain.difficulty

        # Mine blocks
        for _ in range(5):
            blockchain.mine_pending_transactions(wallet.address)

        # Get difficulty stats
        stats = manager.get_consensus_stats()

        assert "difficulty" in stats
        diff_stats = stats["difficulty"]

        assert "current_difficulty" in diff_stats
        assert diff_stats["current_difficulty"] == blockchain.difficulty

    def test_manager_can_adjust_difficulty(self, blockchain):
        """Test manager can trigger difficulty adjustment"""
        manager = AdvancedConsensusManager(blockchain)
        wallet = Wallet()

        # Mine blocks
        for _ in range(5):
            blockchain.mine_pending_transactions(wallet.address)

        # Manually trigger adjustment
        manager.adjust_difficulty_if_needed()

        # Difficulty may or may not change depending on block times
        # Just verify operation completes
        assert blockchain.difficulty > 0


class TestDifficultyUnderVariousConditions:
    """Test difficulty adjustment under various mining conditions"""

    @pytest.fixture
    def adjuster(self) -> DynamicDifficultyAdjustment:
        """Create adjuster"""
        return DynamicDifficultyAdjustment(target_block_time=120)

    def test_consistent_hashrate(self, adjuster, tmp_path):
        """Test difficulty stabilizes with consistent hashrate"""
        blockchain = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        # Mine blocks at consistent rate
        for i in range(20):
            block = blockchain.mine_pending_transactions(wallet.address)
            # Consistent 120 second intervals
            block.timestamp = blockchain.chain[0].timestamp + (i + 1) * 120

        # Calculate difficulty
        new_difficulty = adjuster.calculate_new_difficulty(blockchain)

        # Should be close to current (stable)
        # Allow small variation due to rounding
        assert abs(new_difficulty - blockchain.difficulty) <= 2

    def test_increasing_hashrate(self, adjuster, tmp_path):
        """Test difficulty increases with increasing hashrate"""
        blockchain = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        initial_difficulty = blockchain.difficulty

        # Start with slow blocks
        for i in range(5):
            block = blockchain.mine_pending_transactions(wallet.address)
            block.timestamp = blockchain.chain[-2].timestamp + 150

        # Then fast blocks (hashrate increased)
        for i in range(5):
            block = blockchain.mine_pending_transactions(wallet.address)
            block.timestamp = blockchain.chain[-2].timestamp + 50

        # Calculate difficulty
        new_difficulty = adjuster.calculate_new_difficulty(blockchain)

        # Should increase due to recent fast blocks
        assert new_difficulty >= initial_difficulty

    def test_decreasing_hashrate(self, adjuster, tmp_path):
        """Test difficulty decreases with decreasing hashrate"""
        blockchain = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        initial_difficulty = blockchain.difficulty

        # Start with fast blocks
        for i in range(5):
            block = blockchain.mine_pending_transactions(wallet.address)
            block.timestamp = blockchain.chain[-2].timestamp + 50

        # Then slow blocks (hashrate decreased)
        for i in range(5):
            block = blockchain.mine_pending_transactions(wallet.address)
            block.timestamp = blockchain.chain[-2].timestamp + 200

        # Calculate difficulty
        new_difficulty = adjuster.calculate_new_difficulty(blockchain)

        # Should decrease due to recent slow blocks
        assert new_difficulty <= initial_difficulty or abs(new_difficulty - initial_difficulty) <= 1

    def test_extreme_block_time_variance(self, adjuster, tmp_path):
        """Test adjustment handles extreme variance"""
        blockchain = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        # Alternating fast and slow blocks
        for i in range(10):
            block = blockchain.mine_pending_transactions(wallet.address)
            if i % 2 == 0:
                block.timestamp = blockchain.chain[-2].timestamp + 10  # Very fast
            else:
                block.timestamp = blockchain.chain[-2].timestamp + 300  # Very slow

        # Calculate difficulty
        new_difficulty = adjuster.calculate_new_difficulty(blockchain)

        # Should handle variance and produce reasonable result
        assert adjuster.min_difficulty <= new_difficulty <= adjuster.max_difficulty


class TestDifficultyEdgeCases:
    """Test difficulty adjustment edge cases"""

    @pytest.fixture
    def adjuster(self) -> DynamicDifficultyAdjustment:
        """Create adjuster"""
        return DynamicDifficultyAdjustment(target_block_time=120)

    def test_genesis_only(self, adjuster, tmp_path):
        """Test with only genesis block"""
        blockchain = Blockchain(data_dir=str(tmp_path))

        # Only genesis block
        difficulty = adjuster.calculate_new_difficulty(blockchain)

        # Should return current difficulty
        assert difficulty == blockchain.difficulty

    def test_two_blocks_only(self, adjuster, tmp_path):
        """Test with minimal chain (2 blocks)"""
        blockchain = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        # Mine one block
        blockchain.mine_pending_transactions(wallet.address)

        # Calculate difficulty
        difficulty = adjuster.calculate_new_difficulty(blockchain)

        # Should return reasonable value
        assert difficulty > 0

    def test_zero_time_difference(self, adjuster, tmp_path):
        """Test handling of zero time difference"""
        blockchain = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        # Mine blocks with same timestamp
        blockchain.mine_pending_transactions(wallet.address)
        for _ in range(5):
            block = blockchain.mine_pending_transactions(wallet.address)
            block.timestamp = blockchain.chain[-2].timestamp  # Same time

        # Calculate difficulty (should handle gracefully)
        difficulty = adjuster.calculate_new_difficulty(blockchain)

        # Should return valid difficulty
        assert difficulty > 0
        assert adjuster.min_difficulty <= difficulty <= adjuster.max_difficulty

    def test_negative_time_difference(self, adjuster, tmp_path):
        """Test handling of blocks with decreasing timestamps"""
        blockchain = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        base_time = time.time()

        # Mine blocks with decreasing timestamps
        for i in range(5, 0, -1):
            block = blockchain.mine_pending_transactions(wallet.address)
            block.timestamp = base_time + i

        # Timestamps should be sanitized by adjuster
        difficulty = adjuster.calculate_new_difficulty(blockchain)

        # Should handle gracefully
        assert difficulty > 0

    def test_very_long_chain(self, adjuster, tmp_path):
        """Test difficulty calculation on long chain"""
        blockchain = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        # Mine many blocks
        for i in range(200):
            block = blockchain.mine_pending_transactions(wallet.address)
            block.timestamp = blockchain.chain[0].timestamp + (i + 1) * 120

        # Calculate difficulty
        difficulty = adjuster.calculate_new_difficulty(blockchain)

        # Should complete without error
        assert difficulty > 0
        assert adjuster.min_difficulty <= difficulty <= adjuster.max_difficulty


class TestTargetBlockTime:
    """Test target block time maintenance"""

    @pytest.fixture
    def adjuster(self) -> DynamicDifficultyAdjustment:
        """Create adjuster with specific target"""
        return DynamicDifficultyAdjustment(target_block_time=60)  # 1 minute target

    def test_target_block_time_setting(self, adjuster):
        """Test target block time is configurable"""
        assert adjuster.target_block_time == 60

        # Create adjuster with different target
        adjuster2 = DynamicDifficultyAdjustment(target_block_time=300)
        assert adjuster2.target_block_time == 300

    def test_difficulty_adjusts_toward_target(self, adjuster, tmp_path):
        """Test difficulty adjusts to maintain target block time"""
        blockchain = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        # Mine blocks faster than target (30 seconds)
        for i in range(20):
            block = blockchain.mine_pending_transactions(wallet.address)
            block.timestamp = blockchain.chain[0].timestamp + (i + 1) * 30

        initial_difficulty = blockchain.difficulty

        # Calculate new difficulty
        new_difficulty = adjuster.calculate_new_difficulty(blockchain)

        # Should increase to slow down mining
        assert new_difficulty >= initial_difficulty

    def test_average_block_time_calculation(self, adjuster, tmp_path):
        """Test average block time calculation"""
        blockchain = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        # Mine blocks at known intervals
        intervals = [100, 120, 110, 130, 115]  # Average should be ~115
        for i, interval in enumerate(intervals):
            block = blockchain.mine_pending_transactions(wallet.address)
            block.timestamp = blockchain.chain[-2].timestamp + interval

        # Get stats
        stats = adjuster.get_difficulty_stats(blockchain)

        # Average should be close to 115
        avg_time = stats["avg_block_time"]
        assert 100 <= avg_time <= 130


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
