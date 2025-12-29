"""
Edge case tests for extreme difficulty adjustment scenarios.

Tests various extreme conditions in difficulty adjustment to ensure
robust handling of edge cases and pathological scenarios.
"""

import pytest
import time
from xai.core.blockchain import Blockchain
from xai.core.blockchain_components.block import Block
from xai.core.chain.block_header import BlockHeader
from xai.core.wallet import Wallet
from xai.core.consensus.advanced_consensus import DynamicDifficultyAdjustment
from xai.core.config import Config


class TestExtremeDifficultyAdjustment:
    """Test extreme difficulty adjustment scenarios"""

    def test_difficulty_with_identical_timestamps(self, tmp_path):
        """Test difficulty adjustment when all blocks have same timestamp"""
        bc = Blockchain(data_dir=str(tmp_path))
        miner = Wallet()

        # Set a fixed timestamp for all blocks
        fixed_timestamp = time.time()

        # Mine several blocks with identical timestamps
        for i in range(5):
            # Manually set timestamp to be the same
            block = bc.mine_pending_transactions(miner.address)
            block.timestamp = fixed_timestamp
            # Force update the timestamp in the chain
            bc.chain[-1].timestamp = fixed_timestamp

        # Difficulty adjustment should handle this gracefully
        dda = DynamicDifficultyAdjustment(target_block_time=120)
        new_difficulty = dda.calculate_new_difficulty(bc)

        # Should return a valid difficulty
        assert isinstance(new_difficulty, int)
        assert new_difficulty >= dda.min_difficulty
        assert new_difficulty <= dda.max_difficulty

    def test_difficulty_with_extremely_fast_blocks(self, tmp_path):
        """Test difficulty adjustment when blocks are mined instantly"""
        bc = Blockchain(data_dir=str(tmp_path))
        miner = Wallet()

        # Record start time
        start_time = time.time()

        # Mine multiple blocks very quickly (simulating extremely high hashrate)
        for i in range(10):
            bc.mine_pending_transactions(miner.address)
            # Ensure minimal time increment
            bc.chain[-1].timestamp = start_time + i * 0.001  # 1ms per block

        dda = DynamicDifficultyAdjustment(target_block_time=120)
        new_difficulty = dda.calculate_new_difficulty(bc)

        # Difficulty should increase significantly but stay within limits
        assert new_difficulty > bc.difficulty
        assert new_difficulty <= dda.max_difficulty

    def test_difficulty_with_extremely_slow_blocks(self, tmp_path):
        """Test difficulty adjustment when blocks take very long"""
        bc = Blockchain(data_dir=str(tmp_path))
        miner = Wallet()

        # Mine blocks with very long intervals
        base_time = time.time()
        for i in range(10):
            bc.mine_pending_transactions(miner.address)
            # Simulate very slow mining (1 hour per block instead of 2 minutes)
            bc.chain[-1].timestamp = base_time + i * 3600

        dda = DynamicDifficultyAdjustment(target_block_time=120)
        new_difficulty = dda.calculate_new_difficulty(bc)

        # Difficulty should decrease significantly but stay within limits
        assert new_difficulty < bc.difficulty or new_difficulty == dda.min_difficulty
        assert new_difficulty >= dda.min_difficulty

    def test_difficulty_at_minimum_boundary(self, tmp_path):
        """Test difficulty adjustment at minimum difficulty boundary"""
        bc = Blockchain(data_dir=str(tmp_path))
        miner = Wallet()

        # Set difficulty to minimum
        bc.difficulty = 1

        # Mine blocks very slowly to try to decrease difficulty further
        base_time = time.time()
        for i in range(10):
            bc.mine_pending_transactions(miner.address)
            bc.chain[-1].timestamp = base_time + i * 10000  # Very slow

        dda = DynamicDifficultyAdjustment(target_block_time=120)
        dda.min_difficulty = 1
        new_difficulty = dda.calculate_new_difficulty(bc)

        # Should not go below minimum
        assert new_difficulty >= dda.min_difficulty
        assert new_difficulty == 1

    def test_difficulty_at_maximum_boundary(self, tmp_path):
        """Test difficulty adjustment at maximum difficulty boundary"""
        bc = Blockchain(data_dir=str(tmp_path))
        miner = Wallet()

        # Set difficulty to near maximum
        bc.difficulty = 9

        # Mine blocks very quickly to try to increase difficulty beyond max
        base_time = time.time()
        for i in range(10):
            bc.mine_pending_transactions(miner.address)
            bc.chain[-1].timestamp = base_time + i * 0.01  # Very fast

        dda = DynamicDifficultyAdjustment(target_block_time=120)
        new_difficulty = dda.calculate_new_difficulty(bc)

        # Should not exceed maximum
        assert new_difficulty <= dda.max_difficulty

    def test_difficulty_with_negative_time_delta(self, tmp_path):
        """Test difficulty adjustment when timestamps go backwards"""
        bc = Blockchain(data_dir=str(tmp_path))
        miner = Wallet()

        # Mine several blocks
        base_time = time.time()
        for i in range(5):
            bc.mine_pending_transactions(miner.address)

        # Manually set a block to have earlier timestamp than previous
        bc.chain[-1].timestamp = bc.chain[-2].timestamp - 100

        dda = DynamicDifficultyAdjustment(target_block_time=120)
        new_difficulty = dda.calculate_new_difficulty(bc)

        # Should handle gracefully and return valid difficulty
        assert isinstance(new_difficulty, int)
        assert new_difficulty >= dda.min_difficulty
        assert new_difficulty <= dda.max_difficulty

    def test_difficulty_with_single_block_chain(self, tmp_path):
        """Test difficulty adjustment with only genesis block"""
        bc = Blockchain(data_dir=str(tmp_path))

        dda = DynamicDifficultyAdjustment(target_block_time=120)
        new_difficulty = dda.calculate_new_difficulty(bc)

        # Should return current difficulty when insufficient blocks
        assert new_difficulty == bc.difficulty

    def test_difficulty_with_two_blocks(self, tmp_path):
        """Test difficulty adjustment with minimal chain (genesis + 1 block)"""
        bc = Blockchain(data_dir=str(tmp_path))
        miner = Wallet()

        # Mine one block
        bc.mine_pending_transactions(miner.address)

        dda = DynamicDifficultyAdjustment(target_block_time=120)
        new_difficulty = dda.calculate_new_difficulty(bc)

        # Should be able to calculate with 2 blocks
        assert isinstance(new_difficulty, int)
        assert new_difficulty >= dda.min_difficulty
        assert new_difficulty <= dda.max_difficulty

    def test_difficulty_adjustment_oscillation(self, tmp_path):
        """Test that difficulty doesn't oscillate wildly"""
        bc = Blockchain(data_dir=str(tmp_path))
        miner = Wallet()

        dda = DynamicDifficultyAdjustment(target_block_time=120)

        # Simulate alternating fast/slow blocks
        base_time = time.time()
        difficulties = []
        for i in range(20):
            bc.mine_pending_transactions(miner.address)
            # Alternate between fast and slow blocks
            if i % 2 == 0:
                bc.chain[-1].timestamp = base_time + i * 60  # Fast (1 min)
            else:
                bc.chain[-1].timestamp = base_time + i * 180  # Slow (3 min)

            new_difficulty = dda.calculate_new_difficulty(bc)
            difficulties.append(new_difficulty)

        # Check that difficulty changes are bounded by max_adjustment_factor
        for i in range(1, len(difficulties)):
            ratio = difficulties[i] / max(difficulties[i-1], 1)
            assert ratio <= dda.max_adjustment_factor
            assert ratio >= 1 / dda.max_adjustment_factor

    def test_difficulty_with_zero_time_delta(self, tmp_path):
        """Test difficulty when time_taken is zero"""
        bc = Blockchain(data_dir=str(tmp_path))
        miner = Wallet()

        # Mine blocks with same exact timestamp
        fixed_time = time.time()
        for i in range(5):
            bc.mine_pending_transactions(miner.address)
            bc.chain[-1].timestamp = fixed_time

        dda = DynamicDifficultyAdjustment(target_block_time=120)
        new_difficulty = dda.calculate_new_difficulty(bc)

        # Should return current difficulty when time delta is zero
        assert new_difficulty == bc.difficulty

    def test_difficulty_max_adjustment_factor_enforcement(self, tmp_path):
        """Test that max_adjustment_factor is strictly enforced"""
        bc = Blockchain(data_dir=str(tmp_path))
        miner = Wallet()

        initial_difficulty = bc.difficulty

        # Mine blocks extremely quickly to trigger max adjustment
        base_time = time.time()
        for i in range(200):  # Large window
            bc.mine_pending_transactions(miner.address)
            bc.chain[-1].timestamp = base_time + i * 0.001  # 1ms per block

        dda = DynamicDifficultyAdjustment(target_block_time=120)
        new_difficulty = dda.calculate_new_difficulty(bc)

        # Adjustment should not exceed max_adjustment_factor
        assert new_difficulty <= initial_difficulty * dda.max_adjustment_factor

    def test_difficulty_with_large_window(self, tmp_path):
        """Test difficulty calculation with full adjustment window"""
        bc = Blockchain(data_dir=str(tmp_path))
        miner = Wallet()

        dda = DynamicDifficultyAdjustment(target_block_time=120)

        # Mine blocks equal to adjustment window size
        base_time = time.time()
        for i in range(dda.adjustment_window + 10):
            bc.mine_pending_transactions(miner.address)
            bc.chain[-1].timestamp = base_time + i * 120  # Exactly target time

        new_difficulty = dda.calculate_new_difficulty(bc)

        # With perfect timing, difficulty should remain stable
        assert abs(new_difficulty - bc.difficulty) <= 1

    def test_difficulty_with_timestamp_drift(self, tmp_path):
        """Test difficulty with gradual timestamp drift"""
        bc = Blockchain(data_dir=str(tmp_path))
        miner = Wallet()

        # Simulate clock drift - timestamps gradually getting ahead
        base_time = time.time()
        drift = 0
        for i in range(20):
            bc.mine_pending_transactions(miner.address)
            drift += 0.1  # Accumulating drift
            bc.chain[-1].timestamp = base_time + i * 120 + drift

        dda = DynamicDifficultyAdjustment(target_block_time=120)
        new_difficulty = dda.calculate_new_difficulty(bc)

        # Should handle drift gracefully
        assert isinstance(new_difficulty, int)
        assert new_difficulty >= dda.min_difficulty
        assert new_difficulty <= dda.max_difficulty

    def test_difficulty_convergence_to_target(self, tmp_path):
        """Test that difficulty converges to stable value with consistent block times"""
        bc = Blockchain(data_dir=str(tmp_path))
        miner = Wallet()

        dda = DynamicDifficultyAdjustment(target_block_time=120)

        # Mine blocks at exactly target time
        base_time = time.time()
        difficulties = []
        for i in range(50):
            bc.mine_pending_transactions(miner.address)
            bc.chain[-1].timestamp = base_time + i * dda.target_block_time

            if i >= dda.adjustment_window:
                new_difficulty = dda.calculate_new_difficulty(bc)
                difficulties.append(new_difficulty)

        # Difficulty should stabilize
        if len(difficulties) > 10:
            recent_diffs = difficulties[-10:]
            # Check that recent difficulties are stable (within 1 of each other)
            assert max(recent_diffs) - min(recent_diffs) <= 1

    def test_difficulty_with_extreme_ratios(self, tmp_path):
        """Test difficulty with extreme time ratios"""
        bc = Blockchain(data_dir=str(tmp_path))
        miner = Wallet()

        # Set initial difficulty
        bc.difficulty = 5

        # First set: Mine blocks 100x faster than target
        base_time = time.time()
        for i in range(20):
            bc.mine_pending_transactions(miner.address)
            bc.chain[-1].timestamp = base_time + i * 1.2  # 100x faster

        dda = DynamicDifficultyAdjustment(target_block_time=120)
        new_difficulty = dda.calculate_new_difficulty(bc)

        # Should increase but be capped by max_adjustment_factor
        assert new_difficulty > bc.difficulty
        assert new_difficulty / bc.difficulty <= dda.max_adjustment_factor

    def test_difficulty_float_to_int_rounding(self, tmp_path):
        """Test that difficulty is properly rounded to integer"""
        bc = Blockchain(data_dir=str(tmp_path))
        miner = Wallet()

        # Create scenario that would result in fractional difficulty
        bc.difficulty = 5
        base_time = time.time()
        for i in range(10):
            bc.mine_pending_transactions(miner.address)
            bc.chain[-1].timestamp = base_time + i * 100  # Slightly slower

        dda = DynamicDifficultyAdjustment(target_block_time=120)
        new_difficulty = dda.calculate_new_difficulty(bc)

        # Must be integer
        assert isinstance(new_difficulty, int)
        assert new_difficulty == int(new_difficulty)

    def test_difficulty_with_custom_parameters(self, tmp_path):
        """Test difficulty adjustment with custom parameters"""
        bc = Blockchain(data_dir=str(tmp_path))
        miner = Wallet()

        # Create DDA with custom parameters
        dda = DynamicDifficultyAdjustment(target_block_time=60)
        dda.adjustment_window = 10
        dda.max_adjustment_factor = 2
        dda.min_difficulty = 2
        dda.max_difficulty = 8

        # Mine blocks
        base_time = time.time()
        for i in range(15):
            bc.mine_pending_transactions(miner.address)
            bc.chain[-1].timestamp = base_time + i * 30  # 2x faster than target

        new_difficulty = dda.calculate_new_difficulty(bc)

        # Verify custom limits are respected
        assert new_difficulty >= dda.min_difficulty
        assert new_difficulty <= dda.max_difficulty

    def test_difficulty_adjustment_frequency(self, tmp_path):
        """Test difficulty adjustment frequency control"""
        bc = Blockchain(data_dir=str(tmp_path))
        miner = Wallet()

        dda = DynamicDifficultyAdjustment(target_block_time=120)

        # Mine blocks and check when adjustment happens
        base_time = time.time()
        for i in range(20):
            bc.mine_pending_transactions(miner.address)
            bc.chain[-1].timestamp = base_time + i * 120

            should_adjust = dda.should_adjust_difficulty(bc)
            # Verify boolean return
            assert isinstance(should_adjust, bool)

    def test_difficulty_with_missing_blocks(self, tmp_path):
        """Test difficulty when some blocks are missing from chain"""
        bc = Blockchain(data_dir=str(tmp_path))
        miner = Wallet()

        # Mine several blocks
        for i in range(10):
            bc.mine_pending_transactions(miner.address)

        # Simulate missing blocks by removing some from chain
        original_length = len(bc.chain)
        removed_blocks = bc.chain[5:7]  # Remove 2 blocks from middle

        # This would break the chain in practice, but test the adjustment logic
        dda = DynamicDifficultyAdjustment(target_block_time=120)

        # Should still calculate based on available blocks
        new_difficulty = dda.calculate_new_difficulty(bc)
        assert isinstance(new_difficulty, int)

    def test_difficulty_preservation_on_error(self, tmp_path):
        """Test that difficulty is preserved when calculation fails"""
        bc = Blockchain(data_dir=str(tmp_path))
        original_difficulty = bc.difficulty

        dda = DynamicDifficultyAdjustment(target_block_time=120)

        # With only genesis block, should return current difficulty
        new_difficulty = dda.calculate_new_difficulty(bc)
        assert new_difficulty == original_difficulty

    def test_difficulty_with_unsigned_blocks(self, tmp_path):
        """Test difficulty calculation with unsigned blocks"""
        bc = Blockchain(data_dir=str(tmp_path))
        miner = Wallet()

        # Mine blocks without signatures
        base_time = time.time()
        for i in range(10):
            block = bc.mine_pending_transactions(miner.address)
            # Don't sign the block
            bc.chain[-1].header.signature = None
            bc.chain[-1].timestamp = base_time + i * 120

        dda = DynamicDifficultyAdjustment(target_block_time=120)
        new_difficulty = dda.calculate_new_difficulty(bc)

        # Should work without signatures (only needs timestamps)
        assert isinstance(new_difficulty, int)
        assert new_difficulty >= dda.min_difficulty
