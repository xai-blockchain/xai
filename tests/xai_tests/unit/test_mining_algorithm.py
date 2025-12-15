"""
Unit tests for xai.core.mining_algorithm module.

Tests cover:
- Block reward calculation (with halving)
- Block header creation
- Merkle root calculation
- Mining algorithm correctness
- Hash validation against difficulty
- Difficulty adjustment
- Block verification
- Hashrate estimation
"""

import pytest
from decimal import Decimal
import time

from xai.core.mining_algorithm import MiningAlgorithm, BrowserMiningAdapter


class TestMiningAlgorithmConstants:
    """Tests for MiningAlgorithm constants."""

    def test_block_time_target(self):
        """Block time target is 60 seconds."""
        algo = MiningAlgorithm()
        assert algo.BLOCK_TIME_TARGET == 60

    def test_block_reward(self):
        """Initial block reward is 50 XAI."""
        algo = MiningAlgorithm()
        assert algo.BLOCK_REWARD == Decimal("50.0")

    def test_halving_interval(self):
        """Halving interval is 725,760 blocks."""
        algo = MiningAlgorithm()
        assert algo.HALVING_INTERVAL == 725760

    def test_difficulty_adjustment_interval(self):
        """Difficulty adjustment every 720 blocks."""
        algo = MiningAlgorithm()
        assert algo.DIFFICULTY_ADJUSTMENT_INTERVAL == 720


class TestBlockRewardCalculation:
    """Tests for calculate_block_reward method."""

    def test_initial_reward(self):
        """Block 0 has initial reward of 50 XAI."""
        algo = MiningAlgorithm()
        assert algo.calculate_block_reward(0) == Decimal("50.0")

    def test_reward_at_block_1000(self):
        """Block 1000 (before halving) has 50 XAI reward."""
        algo = MiningAlgorithm()
        assert algo.calculate_block_reward(1000) == Decimal("50.0")

    def test_first_halving(self):
        """After first halving, reward is 25 XAI."""
        algo = MiningAlgorithm()
        block_height = algo.HALVING_INTERVAL
        assert algo.calculate_block_reward(block_height) == Decimal("25.0")

    def test_second_halving(self):
        """After second halving, reward is 12.5 XAI."""
        algo = MiningAlgorithm()
        block_height = algo.HALVING_INTERVAL * 2
        assert algo.calculate_block_reward(block_height) == Decimal("12.5")

    def test_third_halving(self):
        """After third halving, reward is 6.25 XAI."""
        algo = MiningAlgorithm()
        block_height = algo.HALVING_INTERVAL * 3
        assert algo.calculate_block_reward(block_height) == Decimal("6.25")

    def test_minimum_reward(self):
        """Reward never goes below 1 satoshi."""
        algo = MiningAlgorithm()
        # After many halvings
        block_height = algo.HALVING_INTERVAL * 100
        reward = algo.calculate_block_reward(block_height)
        assert reward >= Decimal("0.00000001")

    def test_reward_just_before_halving(self):
        """Block just before halving has pre-halving reward."""
        algo = MiningAlgorithm()
        block_height = algo.HALVING_INTERVAL - 1
        assert algo.calculate_block_reward(block_height) == Decimal("50.0")


class TestBlockHeaderCreation:
    """Tests for create_block_header method."""

    def test_creates_valid_header(self):
        """Creates a valid block header structure."""
        algo = MiningAlgorithm()
        header = algo.create_block_header(
            block_height=100,
            previous_hash="0" * 64,
            transactions=[],
            miner_address="XAI" + "0" * 40,
            nonce=0,
        )

        assert header["version"] == 1
        assert header["height"] == 100
        assert header["previous_hash"] == "0" * 64
        assert header["miner"] == "XAI" + "0" * 40
        assert header["nonce"] == 0
        assert header["difficulty"] == algo.current_difficulty
        assert "timestamp" in header
        assert "transactions_root" in header

    def test_timestamp_is_current(self):
        """Timestamp is close to current time."""
        algo = MiningAlgorithm()
        before = int(time.time())
        header = algo.create_block_header(
            block_height=1,
            previous_hash="0" * 64,
            transactions=[],
            miner_address="XAI" + "0" * 40,
            nonce=0,
        )
        after = int(time.time())

        assert before <= header["timestamp"] <= after


class TestMerkleRoot:
    """Tests for _merkle_root method."""

    def test_empty_transactions(self):
        """Empty transactions produce zero hash."""
        algo = MiningAlgorithm()
        root = algo._merkle_root([])
        assert root == "0" * 64

    def test_single_transaction(self):
        """Single transaction produces valid merkle root."""
        algo = MiningAlgorithm()
        txs = [{"sender": "A", "recipient": "B", "amount": 10}]
        root = algo._merkle_root(txs)
        assert len(root) == 64
        assert all(c in "0123456789abcdef" for c in root)

    def test_multiple_transactions(self):
        """Multiple transactions produce different root than single."""
        algo = MiningAlgorithm()
        tx1 = [{"sender": "A", "recipient": "B", "amount": 10}]
        tx2 = [
            {"sender": "A", "recipient": "B", "amount": 10},
            {"sender": "C", "recipient": "D", "amount": 20},
        ]
        root1 = algo._merkle_root(tx1)
        root2 = algo._merkle_root(tx2)
        assert root1 != root2

    def test_deterministic(self):
        """Same transactions produce same merkle root."""
        algo = MiningAlgorithm()
        txs = [{"sender": "A", "recipient": "B", "amount": 10}]
        root1 = algo._merkle_root(txs)
        root2 = algo._merkle_root(txs)
        assert root1 == root2


class TestHashValidation:
    """Tests for _is_valid_hash method."""

    def test_low_hash_valid(self):
        """Very low hash value is valid at low difficulty."""
        algo = MiningAlgorithm()
        # Low difficulty = high target
        low_hash = "0" * 64
        assert algo._is_valid_hash(low_hash, 1) is True

    def test_high_hash_invalid_at_high_difficulty(self):
        """High hash value invalid at high difficulty."""
        algo = MiningAlgorithm()
        # Hash with all f's is very high
        high_hash = "f" * 64
        # Very high difficulty
        assert algo._is_valid_hash(high_hash, 2**200) is False

    def test_boundary_hash(self):
        """Hash at exactly target boundary."""
        algo = MiningAlgorithm()
        difficulty = 1000
        target = (2**256) // difficulty
        # Hash just below target
        below_target = hex(target - 1)[2:].zfill(64)
        assert algo._is_valid_hash(below_target, difficulty) is True


class TestMining:
    """Tests for mine_block method."""

    def test_mining_low_difficulty(self):
        """Mining succeeds at very low difficulty."""
        algo = MiningAlgorithm()
        algo.current_difficulty = 1  # Very easy
        header = algo.create_block_header(
            block_height=1,
            previous_hash="0" * 64,
            transactions=[],
            miner_address="XAI" + "0" * 40,
            nonce=0,
        )
        result = algo.mine_block(header, max_iterations=10000)

        assert result is not None
        assert "block_hash" in result
        assert "nonce" in result
        assert "time" in result
        assert "hashrate" in result

    def test_mining_returns_none_if_not_found(self):
        """Mining returns None if no valid hash found in iterations."""
        algo = MiningAlgorithm()
        algo.current_difficulty = 2**255  # Impossibly hard
        header = algo.create_block_header(
            block_height=1,
            previous_hash="0" * 64,
            transactions=[],
            miner_address="XAI" + "0" * 40,
            nonce=0,
        )
        result = algo.mine_block(header, max_iterations=10)
        assert result is None

    def test_mining_result_structure(self):
        """Mining result has all required fields."""
        algo = MiningAlgorithm()
        algo.current_difficulty = 1
        header = algo.create_block_header(
            block_height=1,
            previous_hash="0" * 64,
            transactions=[],
            miner_address="XAI" + "0" * 40,
            nonce=0,
        )
        result = algo.mine_block(header, max_iterations=10000)

        assert "block_header" in result
        assert "block_hash" in result
        assert "nonce" in result
        assert "iterations" in result
        assert "time" in result
        assert "hashrate" in result


class TestDifficultyAdjustment:
    """Tests for adjust_difficulty method."""

    def test_no_adjustment_before_interval(self):
        """No adjustment if fewer blocks than interval."""
        algo = MiningAlgorithm()
        initial_diff = algo.current_difficulty
        blocks = [{"timestamp": i * 60} for i in range(100)]
        new_diff = algo.adjust_difficulty(blocks)
        assert new_diff == initial_diff

    def test_difficulty_increase_fast_blocks(self):
        """Difficulty increases if blocks come too fast."""
        algo = MiningAlgorithm()
        initial_diff = algo.current_difficulty

        # Blocks coming 2x faster than target
        blocks = [{"timestamp": i * 30} for i in range(algo.DIFFICULTY_ADJUSTMENT_INTERVAL)]
        new_diff = algo.adjust_difficulty(blocks)

        # Difficulty should increase (ratio < 1)
        assert new_diff > initial_diff

    def test_difficulty_decrease_slow_blocks(self):
        """Difficulty decreases if blocks come too slow."""
        algo = MiningAlgorithm()
        initial_diff = algo.current_difficulty

        # Blocks coming 2x slower than target
        blocks = [{"timestamp": i * 120} for i in range(algo.DIFFICULTY_ADJUSTMENT_INTERVAL)]
        new_diff = algo.adjust_difficulty(blocks)

        # Difficulty should decrease (ratio > 1)
        assert new_diff < initial_diff

    def test_difficulty_limited_to_4x_increase(self):
        """Difficulty adjustment capped at 4x increase."""
        algo = MiningAlgorithm()
        initial_diff = algo.current_difficulty

        # Blocks coming 10x faster
        blocks = [{"timestamp": i * 6} for i in range(algo.DIFFICULTY_ADJUSTMENT_INTERVAL)]
        new_diff = algo.adjust_difficulty(blocks)

        assert new_diff <= initial_diff * 4

    def test_difficulty_limited_to_4x_decrease(self):
        """Difficulty adjustment capped at 4x decrease."""
        algo = MiningAlgorithm()
        initial_diff = algo.current_difficulty

        # Blocks coming 10x slower
        blocks = [{"timestamp": i * 600} for i in range(algo.DIFFICULTY_ADJUSTMENT_INTERVAL)]
        new_diff = algo.adjust_difficulty(blocks)

        assert new_diff >= initial_diff // 4


class TestBlockVerification:
    """Tests for verify_block method."""

    def test_verify_valid_block(self):
        """Verification passes for valid block."""
        algo = MiningAlgorithm()
        algo.current_difficulty = 1  # Easy mining
        header = algo.create_block_header(
            block_height=1,
            previous_hash="0" * 64,
            transactions=[],
            miner_address="XAI" + "0" * 40,
            nonce=0,
        )
        result = algo.mine_block(header, max_iterations=10000)

        assert result is not None
        assert algo.verify_block(result["block_header"], result["block_hash"]) is True

    def test_verify_invalid_hash(self):
        """Verification fails for tampered hash."""
        algo = MiningAlgorithm()
        algo.current_difficulty = 1
        header = algo.create_block_header(
            block_height=1,
            previous_hash="0" * 64,
            transactions=[],
            miner_address="XAI" + "0" * 40,
            nonce=0,
        )
        result = algo.mine_block(header, max_iterations=10000)

        assert result is not None
        # Tamper with hash
        fake_hash = "f" * 64
        assert algo.verify_block(result["block_header"], fake_hash) is False


class TestHashrateEstimation:
    """Tests for hashrate estimation methods."""

    def test_estimate_hashrate(self):
        """Hashrate estimation from difficulty."""
        algo = MiningAlgorithm()
        hashrate = algo.estimate_hashrate(difficulty=6000, block_time=60)
        assert hashrate == 100  # 6000 / 60 = 100

    def test_estimate_time_to_mine(self):
        """Time to mine estimation."""
        algo = MiningAlgorithm()
        time_est = algo.estimate_time_to_mine(hashrate=100, difficulty=6000)
        assert time_est == 60  # 6000 / 100 = 60

    def test_estimate_time_zero_hashrate(self):
        """Zero hashrate returns infinity."""
        algo = MiningAlgorithm()
        time_est = algo.estimate_time_to_mine(hashrate=0, difficulty=1000)
        assert time_est == float("inf")


class TestBrowserMiningAdapter:
    """Tests for BrowserMiningAdapter class."""

    def test_adapter_initialization(self):
        """Adapter initializes with reduced parameters."""
        adapter = BrowserMiningAdapter()
        assert adapter.algorithm.MEMORY_SIZE == adapter.BROWSER_MEMORY_SIZE
        assert adapter.algorithm.HASH_ITERATIONS == adapter.BROWSER_HASH_ITERATIONS

    def test_get_mining_job(self):
        """get_mining_job returns valid job structure."""
        adapter = BrowserMiningAdapter()
        job = adapter.get_mining_job(
            block_height=100,
            previous_hash="0" * 64,
            miner_address="XAI" + "0" * 40,
        )

        assert "job_id" in job
        assert job["block_height"] == 100
        assert job["previous_hash"] == "0" * 64
        assert "timestamp" in job
        assert "difficulty" in job
        assert job["miner_address"] == "XAI" + "0" * 40
        assert "target" in job

    def test_browser_memory_size_reduced(self):
        """Browser mode uses less memory."""
        algo = MiningAlgorithm()
        adapter = BrowserMiningAdapter()
        assert adapter.BROWSER_MEMORY_SIZE < algo.MEMORY_SIZE

    def test_browser_hash_iterations_reduced(self):
        """Browser mode uses fewer hash iterations."""
        algo = MiningAlgorithm()
        adapter = BrowserMiningAdapter()
        assert adapter.BROWSER_HASH_ITERATIONS < algo.HASH_ITERATIONS
