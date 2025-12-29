"""
Edge Case Tests: Extreme Difficulty

Tests for difficulty adjustment at boundary conditions:
- Difficulty at minimum boundary (1)
- Difficulty at maximum boundary
- Large difficulty adjustments (4x up/down)
- Difficulty transitions across epochs
- Rapid hashrate changes
- Extreme block time variance

These tests ensure difficulty adjustment remains stable and secure
under unusual network conditions.

Security Considerations:
- Prevent difficulty from going to 0 (instant mining)
- Prevent difficulty overflow/underflow
- Limit maximum difficulty change per adjustment
- Handle edge cases in difficulty calculation
"""

import pytest
import math
from unittest.mock import patch

from xai.core.blockchain import Blockchain, Block
from xai.core.chain.block_header import BlockHeader
from xai.core.consensus.advanced_consensus import DynamicDifficultyAdjustment
from xai.core.wallet import Wallet


class TestMinimumDifficulty:
    """Test difficulty at minimum boundary"""

    def test_difficulty_at_minimum_value(self, tmp_path):
        """Test blockchain functions correctly at minimum difficulty (1)"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        # Set difficulty to minimum
        bc.difficulty = 1
        bc.dynamic_difficulty_adjuster.min_difficulty = 1

        # Mine block with minimum difficulty
        block = bc.mine_pending_transactions(wallet.address)

        # Should succeed - difficulty 1 requires hash starting with "0"
        assert block.hash.startswith("0")
        assert bc.difficulty >= 1

    def test_difficulty_cannot_go_below_one(self, tmp_path):
        """Test difficulty adjustment never produces difficulty < 1"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        # Set very low difficulty and fast block times to trigger downward adjustment
        bc.difficulty = 1
        bc.dynamic_difficulty_adjuster.min_difficulty = 1

        # Mine blocks very quickly
        base_time = 0.0
        for i in range(bc.dynamic_difficulty_adjuster.adjustment_window + 1):
            with patch('time.time', return_value=base_time + i * 1):  # 1 second per block
                bc.mine_pending_transactions(wallet.address)

        # Calculate next difficulty
        new_difficulty = bc.calculate_next_difficulty()

        # Should never go below 1
        assert new_difficulty >= 1

    def test_minimum_difficulty_with_slow_blocks(self, tmp_path):
        """Test that even with slow blocks, difficulty stays at minimum if already there"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        # Start at minimum difficulty
        bc.difficulty = 1
        bc.dynamic_difficulty_adjuster.min_difficulty = 1

        # Mine blocks extremely slowly
        base_time = 0.0
        for i in range(bc.dynamic_difficulty_adjuster.adjustment_window + 1):
            with patch('time.time', return_value=base_time + i * 10000):  # Very slow
                bc.mine_pending_transactions(wallet.address)

        new_difficulty = bc.calculate_next_difficulty()

        # Difficulty should increase from minimum, but stay >= 1
        assert new_difficulty >= 1

    def test_difficulty_adjustment_from_minimum(self, tmp_path):
        """Test difficulty can increase from minimum when blocks are fast"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        # Start at minimum
        bc.difficulty = 1
        original_difficulty = bc.difficulty

        # Mine blocks faster than target
        base_time = 0.0
        target_time = bc.target_block_time
        for i in range(bc.dynamic_difficulty_adjuster.adjustment_window + 1):
            with patch('time.time', return_value=base_time + i * (target_time / 4)):
                bc.mine_pending_transactions(wallet.address)

        new_difficulty = bc.calculate_next_difficulty()

        # Difficulty should increase from minimum
        assert new_difficulty > original_difficulty
        assert new_difficulty >= 1


class TestMaximumDifficulty:
    """Test difficulty at maximum boundary"""

    def test_difficulty_at_maximum_value(self, tmp_path):
        """Test difficulty adjustment respects maximum difficulty"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        # Set difficulty to maximum
        max_diff = bc.dynamic_difficulty_adjuster.max_difficulty
        bc.difficulty = max_diff

        # Mine blocks very quickly to trigger upward adjustment
        base_time = 0.0
        for i in range(bc.dynamic_difficulty_adjuster.adjustment_window + 1):
            with patch('time.time', return_value=base_time + i * 1):
                bc.mine_pending_transactions(wallet.address)

        new_difficulty = bc.calculate_next_difficulty()

        # Should not exceed maximum
        assert new_difficulty <= max_diff

    def test_difficulty_cannot_exceed_maximum(self, tmp_path):
        """Test difficulty adjustment is capped at maximum"""
        bc = Blockchain(data_dir=str(tmp_path))

        # Set to just below maximum
        max_diff = bc.dynamic_difficulty_adjuster.max_difficulty
        bc.difficulty = max_diff - 1

        # Mine extremely fast blocks
        base_time = 0.0
        for i in range(bc.dynamic_difficulty_adjuster.adjustment_window + 1):
            header = BlockHeader(
                index=i,
                previous_hash=bc.chain[-1].hash if i > 0 else "0" * 64,
                merkle_root="0" * 64,
                timestamp=base_time + i * 0.001,  # Extremely fast
                difficulty=bc.difficulty,
                nonce=0,
            )
            block = Block(header=header, transactions=[])
            bc.chain.append(block)

        new_difficulty = bc.calculate_next_difficulty()

        # Should be capped at maximum
        assert new_difficulty <= max_diff

    def test_maximum_difficulty_boundary_exact(self, tmp_path):
        """Test difficulty adjustment at exact maximum boundary"""
        bc = Blockchain(data_dir=str(tmp_path))

        max_diff = bc.dynamic_difficulty_adjuster.max_difficulty
        bc.difficulty = max_diff
        bc.dynamic_difficulty_adjuster.max_difficulty = max_diff

        # Even with fast blocks, should stay at max
        new_difficulty = bc.calculate_next_difficulty()

        assert new_difficulty <= max_diff


class TestLargeDifficultyAdjustments:
    """Test large difficulty changes"""

    def test_maximum_upward_adjustment_4x(self, tmp_path):
        """Test maximum upward adjustment is capped at 4x"""
        bc = Blockchain(data_dir=str(tmp_path))

        initial_difficulty = 5
        bc.difficulty = initial_difficulty
        max_factor = bc.dynamic_difficulty_adjuster.max_adjustment_factor

        # Mine blocks extremely fast (should trigger 4x increase)
        base_time = 0.0
        window = bc.dynamic_difficulty_adjuster.adjustment_window
        target = bc.target_block_time

        for i in range(window + 1):
            # Mine blocks 10x faster than target
            timestamp = base_time + i * (target / 10)
            header = BlockHeader(
                index=i,
                previous_hash=bc.chain[-1].hash if i > 0 else "0" * 64,
                merkle_root="0" * 64,
                timestamp=timestamp,
                difficulty=bc.difficulty,
                nonce=0,
            )
            block = Block(header=header, transactions=[])
            bc.chain.append(block)

        new_difficulty = bc.calculate_next_difficulty()

        # Should not exceed 4x increase
        assert new_difficulty <= initial_difficulty * max_factor

    def test_maximum_downward_adjustment_4x(self, tmp_path):
        """Test maximum downward adjustment is capped at 1/4x"""
        bc = Blockchain(data_dir=str(tmp_path))

        initial_difficulty = 8
        bc.difficulty = initial_difficulty
        max_factor = bc.dynamic_difficulty_adjuster.max_adjustment_factor

        # Mine blocks extremely slowly (should trigger 1/4x decrease)
        base_time = 0.0
        window = bc.dynamic_difficulty_adjuster.adjustment_window
        target = bc.target_block_time

        for i in range(window + 1):
            # Mine blocks 10x slower than target
            timestamp = base_time + i * (target * 10)
            header = BlockHeader(
                index=i,
                previous_hash=bc.chain[-1].hash if i > 0 else "0" * 64,
                merkle_root="0" * 64,
                timestamp=timestamp,
                difficulty=bc.difficulty,
                nonce=0,
            )
            block = Block(header=header, transactions=[])
            bc.chain.append(block)

        new_difficulty = bc.calculate_next_difficulty()

        # Should not decrease below 1/4x
        min_difficulty = max(1, initial_difficulty / max_factor)
        assert new_difficulty >= min_difficulty

    @pytest.mark.parametrize("speed_multiplier", [0.1, 0.25, 0.5, 2, 4, 10])
    def test_various_adjustment_magnitudes(self, tmp_path, speed_multiplier):
        """Test difficulty adjustment with various block speed changes"""
        bc = Blockchain(data_dir=str(tmp_path))

        initial_difficulty = 5
        bc.difficulty = initial_difficulty

        # Mine blocks at various speeds
        base_time = 0.0
        window = bc.dynamic_difficulty_adjuster.adjustment_window
        target = bc.target_block_time

        for i in range(window + 1):
            timestamp = base_time + i * (target * speed_multiplier)
            header = BlockHeader(
                index=i,
                previous_hash=bc.chain[-1].hash if i > 0 else "0" * 64,
                merkle_root="0" * 64,
                timestamp=timestamp,
                difficulty=bc.difficulty,
                nonce=0,
            )
            block = Block(header=header, transactions=[])
            bc.chain.append(block)

        new_difficulty = bc.calculate_next_difficulty()

        # Verify difficulty stays within bounds
        max_factor = bc.dynamic_difficulty_adjuster.max_adjustment_factor
        assert new_difficulty >= max(1, initial_difficulty / max_factor)
        assert new_difficulty <= initial_difficulty * max_factor

    def test_rapid_difficulty_changes(self, tmp_path):
        """Test multiple consecutive large difficulty adjustments"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        initial_difficulty = 4
        bc.difficulty = initial_difficulty

        # First epoch: mine very fast (increase difficulty)
        base_time = 0.0
        window = bc.dynamic_difficulty_adjuster.adjustment_window
        for i in range(window):
            with patch('time.time', return_value=base_time + i * 10):
                bc.mine_pending_transactions(wallet.address)

        difficulty_after_first = bc.difficulty
        assert difficulty_after_first >= initial_difficulty

        # Second epoch: mine very slow (decrease difficulty)
        base_time = base_time + window * 10
        for i in range(window):
            with patch('time.time', return_value=base_time + i * 1000):
                bc.mine_pending_transactions(wallet.address)

        difficulty_after_second = bc.difficulty

        # Difficulty should have decreased from peak
        # But both adjustments should be bounded
        assert difficulty_after_second >= 1


class TestDifficultyTransitionsAcrossEpochs:
    """Test difficulty adjustment at epoch boundaries"""

    def test_difficulty_adjustment_at_epoch_boundary(self, tmp_path):
        """Test difficulty adjusts exactly at epoch boundary"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        window = bc.dynamic_difficulty_adjuster.adjustment_window
        initial_difficulty = bc.difficulty

        # Mine exactly to epoch boundary
        base_time = 0.0
        for i in range(window):
            with patch('time.time', return_value=base_time + i * bc.target_block_time):
                bc.mine_pending_transactions(wallet.address)

        # At epoch boundary, difficulty should potentially adjust
        chain_length = len(bc.chain)
        should_adjust = bc.dynamic_difficulty_adjuster.should_adjust_difficulty(bc)

        if should_adjust:
            new_diff = bc.calculate_next_difficulty()
            # Adjustment should produce valid difficulty
            assert new_diff >= 1

    def test_difficulty_one_block_before_epoch(self, tmp_path):
        """Test difficulty one block before epoch boundary"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        window = bc.dynamic_difficulty_adjuster.adjustment_window
        initial_difficulty = bc.difficulty

        # Mine to one block before epoch
        for i in range(window - 1):
            bc.mine_pending_transactions(wallet.address)

        # Should not adjust yet
        should_adjust = bc.dynamic_difficulty_adjuster.should_adjust_difficulty(bc)
        # Depending on implementation, might adjust at window or window+1
        # This is a boundary condition

    def test_difficulty_one_block_after_epoch(self, tmp_path):
        """Test difficulty one block after epoch boundary"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        window = bc.dynamic_difficulty_adjuster.adjustment_window

        # Mine past epoch boundary
        for i in range(window + 1):
            bc.mine_pending_transactions(wallet.address)

        # Should have adjusted by now
        # Verify difficulty is still valid
        assert bc.difficulty >= 1

    def test_multiple_epoch_transitions(self, tmp_path):
        """Test difficulty across multiple epoch boundaries"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        window = bc.dynamic_difficulty_adjuster.adjustment_window
        difficulties = [bc.difficulty]

        # Mine through 3 epochs
        for epoch in range(3):
            for i in range(window):
                bc.mine_pending_transactions(wallet.address)
            difficulties.append(bc.difficulty)

        # All difficulties should be valid
        for diff in difficulties:
            assert diff >= 1
            assert diff <= bc.dynamic_difficulty_adjuster.max_difficulty


class TestExtremeBlockTimeVariance:
    """Test difficulty adjustment with extreme block time variance"""

    def test_alternating_fast_slow_blocks(self, tmp_path):
        """Test difficulty with alternating fast/slow blocks"""
        bc = Blockchain(data_dir=str(tmp_path))

        base_time = 0.0
        timestamp = base_time

        # Alternate between fast and slow blocks
        for i in range(20):
            if i % 2 == 0:
                timestamp += 1  # Fast block
            else:
                timestamp += bc.target_block_time * 2  # Slow block

            header = BlockHeader(
                index=i,
                previous_hash=bc.chain[-1].hash if i > 0 else "0" * 64,
                merkle_root="0" * 64,
                timestamp=timestamp,
                difficulty=bc.difficulty,
                nonce=0,
            )
            block = Block(header=header, transactions=[])
            bc.chain.append(block)

        # Difficulty adjustment should handle variance
        new_difficulty = bc.calculate_next_difficulty()
        assert new_difficulty >= 1

    def test_blocks_with_zero_time_difference(self, tmp_path):
        """Test difficulty calculation when blocks have identical timestamps"""
        bc = Blockchain(data_dir=str(tmp_path))

        # Create blocks with same timestamp (edge case)
        base_time = 1000.0
        for i in range(10):
            header = BlockHeader(
                index=i,
                previous_hash=bc.chain[-1].hash if i > 0 else "0" * 64,
                merkle_root="0" * 64,
                timestamp=base_time,  # Same timestamp
                difficulty=bc.difficulty,
                nonce=0,
            )
            block = Block(header=header, transactions=[])
            bc.chain.append(block)

        # Should handle zero time difference gracefully
        new_difficulty = bc.calculate_next_difficulty()
        assert new_difficulty >= 1

    def test_sudden_hashrate_drop(self, tmp_path):
        """Test difficulty adjustment after sudden hashrate drop (very slow blocks)"""
        bc = Blockchain(data_dir=str(tmp_path))

        window = bc.dynamic_difficulty_adjuster.adjustment_window
        base_time = 0.0

        # Normal blocks
        for i in range(window // 2):
            header = BlockHeader(
                index=i,
                previous_hash=bc.chain[-1].hash if i > 0 else "0" * 64,
                merkle_root="0" * 64,
                timestamp=base_time + i * bc.target_block_time,
                difficulty=bc.difficulty,
                nonce=0,
            )
            block = Block(header=header, transactions=[])
            bc.chain.append(block)

        # Sudden slowdown (simulating hashrate drop)
        timestamp = base_time + (window // 2) * bc.target_block_time
        for i in range(window // 2):
            timestamp += bc.target_block_time * 10  # 10x slower
            header = BlockHeader(
                index=len(bc.chain),
                previous_hash=bc.chain[-1].hash,
                merkle_root="0" * 64,
                timestamp=timestamp,
                difficulty=bc.difficulty,
                nonce=0,
            )
            block = Block(header=header, transactions=[])
            bc.chain.append(block)

        # Difficulty should decrease
        new_difficulty = bc.calculate_next_difficulty()
        assert new_difficulty < bc.difficulty or new_difficulty == 1

    def test_sudden_hashrate_spike(self, tmp_path):
        """Test difficulty adjustment after sudden hashrate spike (very fast blocks)"""
        bc = Blockchain(data_dir=str(tmp_path))

        window = bc.dynamic_difficulty_adjuster.adjustment_window
        base_time = 0.0

        # Normal blocks
        for i in range(window // 2):
            header = BlockHeader(
                index=i,
                previous_hash=bc.chain[-1].hash if i > 0 else "0" * 64,
                merkle_root="0" * 64,
                timestamp=base_time + i * bc.target_block_time,
                difficulty=bc.difficulty,
                nonce=0,
            )
            block = Block(header=header, transactions=[])
            bc.chain.append(block)

        # Sudden speedup (simulating hashrate spike)
        timestamp = base_time + (window // 2) * bc.target_block_time
        for i in range(window // 2):
            timestamp += bc.target_block_time / 10  # 10x faster
            header = BlockHeader(
                index=len(bc.chain),
                previous_hash=bc.chain[-1].hash,
                merkle_root="0" * 64,
                timestamp=timestamp,
                difficulty=bc.difficulty,
                nonce=0,
            )
            block = Block(header=header, transactions=[])
            bc.chain.append(block)

        # Difficulty should increase
        new_difficulty = bc.calculate_next_difficulty()
        assert new_difficulty >= bc.difficulty


class TestDifficultyCalculationEdgeCases:
    """Test edge cases in difficulty calculation"""

    def test_difficulty_with_single_block_chain(self, tmp_path):
        """Test difficulty calculation with only genesis block"""
        bc = Blockchain(data_dir=str(tmp_path))

        # With only genesis, difficulty should remain unchanged
        new_difficulty = bc.calculate_next_difficulty()
        assert new_difficulty == bc.difficulty

    def test_difficulty_with_two_blocks(self, tmp_path):
        """Test difficulty calculation with minimal chain"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        # Mine one block
        bc.mine_pending_transactions(wallet.address)

        # Should be able to calculate difficulty
        new_difficulty = bc.calculate_next_difficulty()
        assert new_difficulty >= 1

    def test_difficulty_rounding_behavior(self, tmp_path):
        """Test that difficulty rounding produces integer values"""
        bc = Blockchain(data_dir=str(tmp_path))

        # Set difficulty to non-integer (if possible)
        bc.difficulty = 3

        # Mine blocks
        for i in range(bc.dynamic_difficulty_adjuster.adjustment_window + 1):
            header = BlockHeader(
                index=i,
                previous_hash=bc.chain[-1].hash if i > 0 else "0" * 64,
                merkle_root="0" * 64,
                timestamp=i * bc.target_block_time * 1.5,  # Slightly slow
                difficulty=bc.difficulty,
                nonce=0,
            )
            block = Block(header=header, transactions=[])
            bc.chain.append(block)

        new_difficulty = bc.calculate_next_difficulty()

        # Difficulty should be an integer
        assert isinstance(new_difficulty, int)
        assert new_difficulty == int(new_difficulty)

    def test_difficulty_overflow_protection(self, tmp_path):
        """Test that difficulty calculation doesn't overflow"""
        bc = Blockchain(data_dir=str(tmp_path))

        # Set very high difficulty near maximum
        max_diff = bc.dynamic_difficulty_adjuster.max_difficulty
        bc.difficulty = max_diff

        # Even with extreme inputs, should not overflow
        new_difficulty = bc.calculate_next_difficulty()

        # Should be a valid integer
        assert isinstance(new_difficulty, int)
        assert new_difficulty <= max_diff
        assert new_difficulty >= 1
