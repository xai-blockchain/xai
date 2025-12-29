"""
Comprehensive Blockchain Security Tests

Tests for 100% coverage of blockchain_security.py module.
Tests all blockchain security features including reorganization protection,
supply validation, overflow protection, mempool management, and more.
"""

import pytest
import time
import json
import os
import tempfile
import hashlib
from unittest.mock import Mock, MagicMock, patch
from decimal import Decimal

from xai.core.security.blockchain_security import (
    BlockchainSecurityConfig,
    ReorganizationProtection,
    SupplyValidator,
    OverflowProtection,
    MempoolManager,
    BlockSizeValidator,
    ResourceLimiter,
    DustProtection,
    MedianTimePast,
    TimeValidator,
    EmergencyGovernanceTimelock,
    BlockchainSecurityManager,
)
from xai.core.blockchain import Blockchain, Block, Transaction
from xai.core.wallet import Wallet


@pytest.mark.security
class TestBlockchainSecurityConfig:
    """Test security configuration constants"""

    def test_config_constants_defined(self):
        """Test that all security config constants are defined"""
        assert BlockchainSecurityConfig.MAX_BLOCK_SIZE > 0
        assert BlockchainSecurityConfig.MAX_TRANSACTION_SIZE > 0
        assert BlockchainSecurityConfig.MAX_TRANSACTIONS_PER_BLOCK > 0
        assert BlockchainSecurityConfig.MAX_MEMPOOL_SIZE > 0
        assert BlockchainSecurityConfig.MAX_MEMPOOL_BYTES > 0
        assert BlockchainSecurityConfig.MIN_TRANSACTION_AMOUNT > 0
        assert BlockchainSecurityConfig.MIN_UTXO_VALUE > 0
        assert BlockchainSecurityConfig.MAX_REORG_DEPTH > 0
        assert BlockchainSecurityConfig.CHECKPOINT_INTERVAL > 0
        assert BlockchainSecurityConfig.MAX_SUPPLY > 0
        assert BlockchainSecurityConfig.SUPPLY_CHECK_INTERVAL > 0
        assert BlockchainSecurityConfig.MEDIAN_TIME_SPAN > 0
        assert BlockchainSecurityConfig.MAX_FUTURE_BLOCK_TIME > 0
        assert BlockchainSecurityConfig.MAX_MONEY > 0

    def test_config_values_reasonable(self):
        """Test that config values are reasonable"""
        assert BlockchainSecurityConfig.MAX_BLOCK_SIZE == 2_000_000
        assert BlockchainSecurityConfig.MAX_SUPPLY == 121_000_000
        assert BlockchainSecurityConfig.MIN_TRANSACTION_AMOUNT == 0.00001


@pytest.mark.security
class TestReorganizationProtection:
    """Test reorganization protection (51% attack mitigation)"""

    def test_init_default_max_depth(self):
        """Test initialization with default max depth"""
        reorg = ReorganizationProtection()
        assert reorg.max_depth == BlockchainSecurityConfig.MAX_REORG_DEPTH

    def test_init_custom_max_depth(self):
        """Test initialization with custom max depth"""
        reorg = ReorganizationProtection(max_depth=50)
        assert reorg.max_depth == 50

    def test_add_checkpoint(self, temp_blockchain_dir):
        """Test adding a checkpoint"""
        checkpoint_file = os.path.join(temp_blockchain_dir, "checkpoints.json")
        reorg = ReorganizationProtection()
        reorg.checkpoint_file = checkpoint_file

        reorg.add_checkpoint(1000, "hash_1000")

        assert 1000 in reorg.checkpoints
        assert reorg.checkpoints[1000] == "hash_1000"

    def test_checkpoints_persisted_to_disk(self, temp_blockchain_dir):
        """Test that checkpoints are saved to disk"""
        checkpoint_file = os.path.join(temp_blockchain_dir, "checkpoints.json")
        reorg = ReorganizationProtection()
        reorg.checkpoint_file = checkpoint_file

        reorg.add_checkpoint(2000, "hash_2000")

        # Verify file exists and contains checkpoint
        assert os.path.exists(checkpoint_file)

        with open(checkpoint_file, 'r') as f:
            data = json.load(f)
            assert "2000" in data
            assert data["2000"] == "hash_2000"

    def test_load_checkpoints_from_disk(self, temp_blockchain_dir):
        """Test loading checkpoints from disk"""
        checkpoint_file = os.path.join(temp_blockchain_dir, "checkpoints.json")

        # Create checkpoint file
        os.makedirs(os.path.dirname(checkpoint_file), exist_ok=True)
        with open(checkpoint_file, 'w') as f:
            json.dump({"3000": "hash_3000"}, f)

        reorg = ReorganizationProtection()
        reorg.checkpoint_file = checkpoint_file
        reorg._load_checkpoints()

        assert 3000 in reorg.checkpoints
        assert reorg.checkpoints[3000] == "hash_3000"

    def test_validate_reorganization_within_limit(self):
        """Test that reorganization within limit is allowed"""
        reorg = ReorganizationProtection(max_depth=100)

        is_valid, msg = reorg.validate_reorganization(current_height=200, fork_point=150)

        assert is_valid is True
        assert msg is None

    def test_reject_reorganization_exceeding_limit(self):
        """Test rejection of reorganization exceeding depth limit"""
        reorg = ReorganizationProtection(max_depth=100)

        is_valid, msg = reorg.validate_reorganization(current_height=200, fork_point=50)

        assert is_valid is False
        assert "too deep" in msg.lower()

    def test_reject_reorganization_past_checkpoint(self):
        """Test rejection of reorganization past checkpoint"""
        reorg = ReorganizationProtection(max_depth=100)
        reorg.add_checkpoint(150, "checkpoint_hash")

        is_valid, msg = reorg.validate_reorganization(current_height=200, fork_point=100)

        assert is_valid is False
        assert "checkpoint" in msg.lower()

    def test_get_checkpoint(self):
        """Test getting checkpoint hash"""
        reorg = ReorganizationProtection()
        reorg.add_checkpoint(100, "hash_100")

        checkpoint_hash = reorg.get_checkpoint(100)

        assert checkpoint_hash == "hash_100"

    def test_get_nonexistent_checkpoint(self):
        """Test getting checkpoint that doesn't exist"""
        reorg = ReorganizationProtection()

        checkpoint_hash = reorg.get_checkpoint(999)

        assert checkpoint_hash is None

    def test_is_checkpoint_block(self):
        """Test checking if block is a checkpoint"""
        reorg = ReorganizationProtection()
        reorg.add_checkpoint(100, "hash_100")

        assert reorg.is_checkpoint_block(100) is True
        assert reorg.is_checkpoint_block(101) is False


@pytest.mark.security
class TestSupplyValidator:
    """Test supply validation (inflation bug protection)"""

    def test_init_default_max_supply(self):
        """Test initialization with default max supply"""
        validator = SupplyValidator()
        assert validator.max_supply == BlockchainSecurityConfig.MAX_SUPPLY

    def test_init_custom_max_supply(self):
        """Test initialization with custom max supply"""
        validator = SupplyValidator(max_supply=100_000_000)
        assert validator.max_supply == 100_000_000

    def test_validate_coinbase_amount_valid(self):
        """Test validation of valid coinbase amount"""
        validator = SupplyValidator()

        is_valid = validator.validate_coinbase_amount(
            block_height=100,
            coinbase_amount=50.0,
            expected_reward=50.0,
            total_fees=0.0
        )

        assert is_valid is True

    def test_validate_coinbase_with_fees(self):
        """Test validation of coinbase amount with fees"""
        validator = SupplyValidator()

        is_valid = validator.validate_coinbase_amount(
            block_height=100,
            coinbase_amount=52.0,
            expected_reward=50.0,
            total_fees=2.0
        )

        assert is_valid is True

    def test_reject_excessive_coinbase_amount(self):
        """Test rejection of excessive coinbase amount"""
        validator = SupplyValidator()

        is_valid = validator.validate_coinbase_amount(
            block_height=100,
            coinbase_amount=100.0,
            expected_reward=50.0,
            total_fees=2.0
        )

        assert is_valid is False

    def test_validate_total_supply_with_blockchain(self, blockchain):
        """Test total supply validation with blockchain instance"""
        validator = SupplyValidator()

        is_valid, total_supply = validator.validate_total_supply(blockchain)

        assert isinstance(is_valid, bool)
        assert isinstance(total_supply, float)

    def test_validate_total_supply_with_float(self):
        """Test total supply validation with direct float value"""
        validator = SupplyValidator()

        is_valid, msg = validator.validate_total_supply(1000000.0)

        assert is_valid is True
        assert "within cap" in msg

    def test_reject_supply_exceeding_cap(self):
        """Test rejection of supply exceeding cap"""
        validator = SupplyValidator(max_supply=1_000_000)

        is_valid, result = validator.validate_total_supply(2_000_000.0)

        assert is_valid is False

    def test_validate_block_reward_valid(self):
        """Test validation of valid block reward"""
        validator = SupplyValidator()

        is_valid, msg = validator.validate_block_reward(reward=50.0, total_fees=2.0)

        assert is_valid is True

    def test_reject_zero_block_reward(self):
        """Test rejection of zero block reward"""
        validator = SupplyValidator()

        is_valid, msg = validator.validate_block_reward(reward=0.0, total_fees=0.0)

        assert is_valid is False
        assert "must be positive" in msg

    def test_reject_negative_block_reward(self):
        """Test rejection of negative block reward"""
        validator = SupplyValidator()

        is_valid, msg = validator.validate_block_reward(reward=-10.0, total_fees=0.0)

        assert is_valid is False


@pytest.mark.security
class TestOverflowProtection:
    """Test integer/float overflow protection"""

    def test_safe_add_valid(self):
        """Test safe addition of valid amounts"""
        protection = OverflowProtection()

        result, is_safe = protection.safe_add(100.0, 200.0)

        assert is_safe is True
        assert result == 300.0

    def test_safe_add_overflow(self):
        """Test detection of addition overflow"""
        protection = OverflowProtection()

        huge_num = float(BlockchainSecurityConfig.MAX_MONEY)
        result, is_safe = protection.safe_add(huge_num, huge_num)

        assert is_safe is False
        assert result is None

    def test_safe_add_exception_handling(self):
        """Test exception handling in safe_add"""
        protection = OverflowProtection()

        # Force exception with invalid input
        result, is_safe = protection.safe_add("invalid", 100.0)

        assert is_safe is False
        assert result is None

    def test_safe_multiply_valid(self):
        """Test safe multiplication of valid amounts"""
        protection = OverflowProtection()

        result, is_safe = protection.safe_multiply(10.0, 20.0)

        assert is_safe is True
        assert result == 200.0

    def test_safe_multiply_overflow(self):
        """Test detection of multiplication overflow"""
        protection = OverflowProtection()

        huge_num = float(BlockchainSecurityConfig.MAX_SUPPLY)
        result, is_safe = protection.safe_multiply(huge_num, huge_num)

        assert is_safe is False
        assert result is None

    def test_safe_multiply_exception_handling(self):
        """Test exception handling in safe_multiply"""
        protection = OverflowProtection()

        result, is_safe = protection.safe_multiply("invalid", 100.0)

        assert is_safe is False
        assert result is None

    def test_validate_amount_valid(self):
        """Test validation of valid amounts"""
        protection = OverflowProtection()

        is_valid, msg = protection.validate_amount(100.0)

        assert is_valid is True

    def test_validate_amount_nan(self):
        """Test detection of NaN amounts"""
        protection = OverflowProtection()

        is_valid, msg = protection.validate_amount(float('nan'))

        assert is_valid is False
        assert "NaN" in msg

    def test_validate_amount_negative(self):
        """Test rejection of negative amounts"""
        protection = OverflowProtection()

        is_valid, msg = protection.validate_amount(-10.0)

        assert is_valid is False
        assert "negative" in msg

    def test_validate_amount_exceeds_max(self):
        """Test rejection of amounts exceeding max supply"""
        protection = OverflowProtection()

        is_valid, msg = protection.validate_amount(BlockchainSecurityConfig.MAX_SUPPLY + 1)

        assert is_valid is False
        assert "exceeds" in msg


@pytest.mark.security
class TestMempoolManager:
    """Test mempool management with size limits"""

    def test_init(self):
        """Test mempool manager initialization"""
        manager = MempoolManager()

        assert manager.max_count == BlockchainSecurityConfig.MAX_MEMPOOL_SIZE
        assert manager.max_bytes == BlockchainSecurityConfig.MAX_MEMPOOL_BYTES
        assert manager.current_bytes == 0

    def test_can_add_transaction_to_empty_mempool(self):
        """Test adding transaction to empty mempool"""
        manager = MempoolManager()

        mock_tx = Mock()
        mock_tx.to_dict.return_value = {"sender": "XAI123", "amount": 10.0}

        can_add, error = manager.can_add_transaction(mock_tx, [])

        assert can_add is True
        assert error is None

    def test_reject_transaction_when_mempool_full(self):
        """Test rejection when mempool count limit reached"""
        manager = MempoolManager()

        mock_tx = Mock()
        mock_tx.to_dict.return_value = {"data": "test"}

        # Create full mempool
        full_mempool = [Mock() for _ in range(BlockchainSecurityConfig.MAX_MEMPOOL_SIZE)]

        can_add, error = manager.can_add_transaction(mock_tx, full_mempool)

        assert can_add is False
        assert "full" in error.lower()

    def test_reject_transaction_when_mempool_bytes_full(self):
        """Test rejection when mempool memory limit reached"""
        manager = MempoolManager()
        manager.current_bytes = BlockchainSecurityConfig.MAX_MEMPOOL_BYTES - 100

        mock_tx = Mock()
        # Create large transaction
        large_data = {"data": "x" * 1000000}
        mock_tx.to_dict.return_value = large_data

        can_add, error = manager.can_add_transaction(mock_tx, [])

        assert can_add is False
        assert "memory" in error.lower()

    def test_add_transaction_updates_bytes(self):
        """Test that adding transaction updates byte count"""
        manager = MempoolManager()

        mock_tx = Mock()
        mock_tx.to_dict.return_value = {"data": "test"}

        initial_bytes = manager.current_bytes
        manager.add_transaction(mock_tx)

        assert manager.current_bytes > initial_bytes

    def test_remove_transaction_updates_bytes(self):
        """Test that removing transaction updates byte count"""
        manager = MempoolManager()

        mock_tx = Mock()
        mock_tx.to_dict.return_value = {"data": "test"}

        manager.add_transaction(mock_tx)
        bytes_after_add = manager.current_bytes

        manager.remove_transaction(mock_tx)

        assert manager.current_bytes < bytes_after_add

    def test_remove_transaction_minimum_zero(self):
        """Test that removing transaction doesn't go below zero"""
        manager = MempoolManager()

        mock_tx = Mock()
        mock_tx.to_dict.return_value = {"data": "test"}

        manager.remove_transaction(mock_tx)

        assert manager.current_bytes == 0

    def test_clear_mempool(self):
        """Test clearing mempool"""
        manager = MempoolManager()
        manager.current_bytes = 1000

        manager.clear()

        assert manager.current_bytes == 0


@pytest.mark.security
class TestBlockSizeValidator:
    """Test block and transaction size validation"""

    def test_validate_transaction_size_valid(self):
        """Test validation of valid transaction size"""
        mock_tx = Mock()
        mock_tx.to_dict.return_value = {"data": "small"}

        is_valid, error = BlockSizeValidator.validate_transaction_size(mock_tx)

        assert is_valid is True
        assert error is None

    def test_reject_oversized_transaction(self):
        """Test rejection of oversized transaction"""
        mock_tx = Mock()
        # Create transaction exceeding max size
        large_data = {"data": "x" * BlockchainSecurityConfig.MAX_TRANSACTION_SIZE}
        mock_tx.to_dict.return_value = large_data

        is_valid, error = BlockSizeValidator.validate_transaction_size(mock_tx)

        assert is_valid is False
        assert "too large" in error.lower()

    def test_validate_block_size_valid(self):
        """Test validation of valid block size"""
        mock_block = Mock()
        mock_block.transactions = []
        mock_block.to_dict.return_value = {"index": 1, "transactions": []}
        mock_block.estimate_size_bytes.return_value = 1024

        is_valid, error = BlockSizeValidator.validate_block_size(mock_block)

        assert is_valid is True
        assert error is None

    def test_reject_block_with_too_many_transactions(self):
        """Test rejection of block with too many transactions"""
        mock_block = Mock()
        mock_block.transactions = [Mock() for _ in range(BlockchainSecurityConfig.MAX_TRANSACTIONS_PER_BLOCK + 1)]
        mock_block.to_dict.return_value = {"index": 1}
        mock_block.estimate_size_bytes.return_value = 1024

        is_valid, error = BlockSizeValidator.validate_block_size(mock_block)

        assert is_valid is False
        assert "too many" in error.lower()

    def test_reject_oversized_block(self):
        """Test rejection of oversized block"""
        mock_block = Mock()
        mock_block.transactions = []
        mock_block.to_dict.return_value = {"index": 1}
        mock_block.estimate_size_bytes.return_value = BlockchainSecurityConfig.MAX_BLOCK_SIZE + 1

        is_valid, error = BlockSizeValidator.validate_block_size(mock_block)

        assert is_valid is False
        assert "too large" in error.lower()


@pytest.mark.security
class TestResourceLimiter:
    """Test resource limiter"""

    def test_validate_transaction_size(self):
        """Test transaction size validation"""
        limiter = ResourceLimiter()

        mock_tx = Mock()
        mock_tx.to_dict.return_value = {"data": "test"}

        is_valid, error = limiter.validate_transaction_size(mock_tx)

        assert is_valid is True

    def test_validate_transaction_size_exception_fallback(self):
        """Test fallback when to_dict fails"""
        limiter = ResourceLimiter()

        mock_tx = Mock()
        mock_tx.to_dict.side_effect = Exception("Error")
        mock_tx.sender = "XAI123"
        mock_tx.recipient = "XAI456"

        # Should not crash
        is_valid, error = limiter.validate_transaction_size(mock_tx)

    def test_validate_block_size(self):
        """Test block size validation"""
        limiter = ResourceLimiter()

        mock_block = Mock()
        mock_block.transactions = []
        mock_block.to_dict.return_value = {"index": 1}
        mock_block.estimate_size_bytes.return_value = 128

        is_valid, error = limiter.validate_block_size(mock_block)

        assert is_valid is True

    def test_can_add_to_mempool_with_space(self):
        """Test mempool slot availability when space exists"""
        limiter = ResourceLimiter()

        can_add = limiter.can_add_to_mempool(current_size=100)

        assert can_add is True

    def test_cannot_add_to_mempool_when_full(self):
        """Test mempool slot unavailable when full"""
        limiter = ResourceLimiter()

        can_add = limiter.can_add_to_mempool(
            current_size=BlockchainSecurityConfig.MAX_MEMPOOL_SIZE
        )

        assert can_add is False


@pytest.mark.security
class TestDustProtection:
    """Test dust attack protection"""

    def test_validate_transaction_amount_valid(self):
        """Test validation of valid transaction amount"""
        is_valid, error = DustProtection.validate_transaction_amount(1.0)

        assert is_valid is True
        assert error is None

    def test_reject_dust_amount(self):
        """Test rejection of dust amount"""
        dust_amount = BlockchainSecurityConfig.MIN_TRANSACTION_AMOUNT / 2

        is_valid, error = DustProtection.validate_transaction_amount(dust_amount)

        assert is_valid is False
        assert "too small" in error.lower()

    def test_validate_utxo_value_valid(self):
        """Test validation of valid UTXO value"""
        is_valid = DustProtection.validate_utxo_value(1.0)

        assert is_valid is True

    def test_reject_dust_utxo(self):
        """Test rejection of dust UTXO"""
        dust_value = BlockchainSecurityConfig.MIN_UTXO_VALUE / 2

        is_valid = DustProtection.validate_utxo_value(dust_value)

        assert is_valid is False


@pytest.mark.security
class TestMedianTimePast:
    """Test median-time-past validation"""

    def test_init_default_span(self):
        """Test initialization with default span"""
        mtp = MedianTimePast()
        assert mtp.span == BlockchainSecurityConfig.MEDIAN_TIME_SPAN

    def test_init_custom_span(self):
        """Test initialization with custom span"""
        mtp = MedianTimePast(span=5)
        assert mtp.span == 5

    def test_get_median_time_empty_chain(self, blockchain):
        """Test median time with empty chain"""
        mtp = MedianTimePast()

        # Clear chain
        blockchain.chain = []

        median = mtp.get_median_time_past(blockchain)

        # Should return current time
        assert median > 0

    def test_get_median_time_with_blocks(self, blockchain):
        """Test median time calculation with blocks"""
        mtp = MedianTimePast()

        wallet = Wallet()

        # Mine several blocks
        for _ in range(11):
            blockchain.mine_pending_transactions(wallet.address)
            time.sleep(0.01)

        median = mtp.get_median_time_past(blockchain)

        assert median > 0
        assert median < time.time()

    def test_get_median_time_even_number_of_blocks(self, blockchain):
        """Test median calculation with even number of blocks"""
        mtp = MedianTimePast(span=10)

        wallet = Wallet()

        for _ in range(10):
            blockchain.mine_pending_transactions(wallet.address)

        median = mtp.get_median_time_past(blockchain)

        assert median > 0

    def test_validate_block_timestamp_valid(self, blockchain):
        """Test validation of valid block timestamp"""
        mtp = MedianTimePast()

        wallet = Wallet()

        # Mine some blocks
        for _ in range(5):
            blockchain.mine_pending_transactions(wallet.address)

        # Create new block with current timestamp
        new_block = blockchain.mine_pending_transactions(wallet.address)

        is_valid, error = mtp.validate_block_timestamp(new_block, blockchain)

        assert is_valid is True

    def test_reject_block_timestamp_before_median(self, blockchain):
        """Test rejection of block timestamp before median"""
        mtp = MedianTimePast()

        wallet = Wallet()

        for _ in range(11):
            blockchain.mine_pending_transactions(wallet.address)

        median = mtp.get_median_time_past(blockchain)

        # Create block with old timestamp
        mock_block = Mock()
        mock_block.timestamp = median - 100

        is_valid, error = mtp.validate_block_timestamp(mock_block, blockchain)

        assert is_valid is False

    def test_reject_block_timestamp_too_far_future(self, blockchain):
        """Test rejection of block timestamp too far in future"""
        mtp = MedianTimePast()

        wallet = Wallet()
        blockchain.mine_pending_transactions(wallet.address)

        # Create block with future timestamp
        mock_block = Mock()
        mock_block.timestamp = time.time() + BlockchainSecurityConfig.MAX_FUTURE_BLOCK_TIME + 100

        is_valid, error = mtp.validate_block_timestamp(mock_block, blockchain)

        assert is_valid is False


@pytest.mark.security
class TestTimeValidator:
    """Test time validator"""

    def test_init(self):
        """Test time validator initialization"""
        validator = TimeValidator()

        assert validator.median_time_span == BlockchainSecurityConfig.MEDIAN_TIME_SPAN
        assert validator.max_future_block_time == BlockchainSecurityConfig.MAX_FUTURE_BLOCK_TIME

    def test_calculate_median_time_past_empty_chain(self):
        """Test median calculation with empty chain"""
        validator = TimeValidator()

        median = validator.calculate_median_time_past([])

        assert median > 0

    def test_calculate_median_time_past_with_blocks(self, blockchain):
        """Test median calculation with blocks"""
        validator = TimeValidator()

        wallet = Wallet()

        for _ in range(11):
            blockchain.mine_pending_transactions(wallet.address)

        median = validator.calculate_median_time_past(blockchain.chain)

        assert median > 0

    def test_validate_block_time_valid(self, blockchain):
        """Test validation of valid block time"""
        validator = TimeValidator()

        wallet = Wallet()
        block = blockchain.mine_pending_transactions(wallet.address)

        is_valid, error = validator.validate_block_time(block, blockchain.chain)

        assert is_valid is True

    def test_reject_block_time_too_far_future(self, blockchain):
        """Test rejection of block time too far in future"""
        validator = TimeValidator()

        mock_block = Mock()
        mock_block.timestamp = time.time() + validator.max_future_block_time + 100

        is_valid, error = validator.validate_block_time(mock_block, blockchain.chain)

        assert is_valid is False
        assert "future" in error.lower()

    def test_reject_block_time_older_than_median(self, blockchain):
        """Test rejection of block time older than median"""
        validator = TimeValidator()

        wallet = Wallet()

        for _ in range(11):
            blockchain.mine_pending_transactions(wallet.address)

        median = validator.calculate_median_time_past(blockchain.chain)

        mock_block = Mock()
        mock_block.timestamp = median - 100

        is_valid, error = validator.validate_block_time(mock_block, blockchain.chain)

        assert is_valid is False
        assert "median" in error.lower()


@pytest.mark.security
class TestBlockchainTimestampEnforcement:
    """Ensure Blockchain enforces MTP + future-drift when adding blocks."""

    @staticmethod
    def _forge_block(previous_block, index: int, timestamp: float) -> Block:
        """Create a synthetic block with deterministic PoW for testing."""
        block = Block(
            index,
            [],
            previous_hash=previous_block.hash,
            difficulty=2,
            timestamp=timestamp,
            nonce=0,
            signature="deadbeef",
            miner_pubkey="cafebabe",
        )
        # Force a deterministic hash that satisfies difficulty constraints
        suffix = hashlib.sha256(f"{index}-{timestamp}".encode()).hexdigest()
        forged_hash = ("0" * block.difficulty) + suffix[block.difficulty :]
        block.hash = forged_hash
        block.header.calculate_hash = lambda: forged_hash
        return block

    def test_add_block_rejects_timestamp_not_past_median(self, tmp_path, monkeypatch):
        """Blocks more recent than previous but older than MTP window should be rejected."""
        blockchain = Blockchain(data_dir=str(tmp_path))
        monkeypatch.setattr(blockchain, "verify_block_signature", lambda header: True)
        base_time = time.time()

        # Populate history with high timestamps so the rolling median stays high.
        span = BlockchainSecurityConfig.MEDIAN_TIME_SPAN
        for offset in range(1, span):
            forged = self._forge_block(blockchain.chain[-1], len(blockchain.chain), base_time + 10_000 + offset)
            blockchain.chain.append(forged)

        # Latest block intentionally has a low timestamp.
        low_block = self._forge_block(blockchain.chain[-1], len(blockchain.chain), base_time)
        blockchain.chain.append(low_block)

        candidate = self._forge_block(blockchain.chain[-1], len(blockchain.chain), base_time + 5)
        result = blockchain.add_block(candidate)

        assert result is False

    def test_add_block_rejects_far_future_timestamp(self, tmp_path, monkeypatch):
        """Blocks more than MAX_FUTURE_BLOCK_TIME seconds in the future must be dropped."""
        blockchain = Blockchain(data_dir=str(tmp_path))
        monkeypatch.setattr(blockchain, "verify_block_signature", lambda header: True)
        future_timestamp = time.time() + BlockchainSecurityConfig.MAX_FUTURE_BLOCK_TIME + 120

        candidate = self._forge_block(blockchain.chain[-1], len(blockchain.chain), future_timestamp)
        result = blockchain.add_block(candidate)

        assert result is False

    def test_add_block_with_valid_timestamp_is_accepted(self, tmp_path, monkeypatch):
        """Blocks respecting MTP and future drift should be accepted."""
        blockchain = Blockchain(data_dir=str(tmp_path))
        monkeypatch.setattr(blockchain, "verify_block_signature", lambda header: True)
        base_time = time.time()

        forged = self._forge_block(blockchain.chain[-1], len(blockchain.chain), base_time + 10)
        result = blockchain.add_block(forged)

        assert result is True
        assert blockchain.chain[-1] is forged

    def test_timestamp_drift_history_tracks_recent_entries(self, tmp_path, monkeypatch):
        """Timestamp drift telemetry records recent additions for diagnostics."""
        blockchain = Blockchain(data_dir=str(tmp_path))
        monkeypatch.setattr(blockchain, "verify_block_signature", lambda header: True)
        base_time = time.time()

        forged = self._forge_block(blockchain.chain[-1], len(blockchain.chain), base_time + 25)
        blockchain.add_block(forged)

        history = blockchain.get_recent_timestamp_drift()
        assert history, "Expected drift history to capture the latest block"
        latest = history[-1]
        assert latest["index"] == forged.index
        assert latest["history_length"] == forged.index
        assert "wall_clock_drift" in latest


@pytest.mark.security
class TestEmergencyGovernanceTimelock:
    """Test emergency governance timelock"""

    def test_init_default_timelock(self):
        """Test initialization with default timelock"""
        timelock = EmergencyGovernanceTimelock()

        assert timelock.emergency_timelock == 144

    def test_init_custom_timelock(self):
        """Test initialization with custom timelock"""
        timelock = EmergencyGovernanceTimelock(emergency_timelock=100)

        assert timelock.emergency_timelock == 100

    def test_schedule_emergency_action(self):
        """Test scheduling emergency action"""
        timelock = EmergencyGovernanceTimelock(emergency_timelock=10)

        timelock.schedule_emergency_action("prop_123", current_block_height=100)

        assert "prop_123" in timelock.pending_emergency_actions
        assert timelock.pending_emergency_actions["prop_123"] == 110

    def test_can_execute_emergency_action_not_scheduled(self):
        """Test that unscheduled action cannot be executed"""
        timelock = EmergencyGovernanceTimelock()

        can_execute, error = timelock.can_execute_emergency_action("prop_999", current_block_height=200)

        assert can_execute is False
        assert "not scheduled" in error.lower()

    def test_can_execute_emergency_action_timelock_active(self):
        """Test that action cannot be executed during timelock"""
        timelock = EmergencyGovernanceTimelock(emergency_timelock=10)

        timelock.schedule_emergency_action("prop_123", current_block_height=100)

        can_execute, error = timelock.can_execute_emergency_action("prop_123", current_block_height=105)

        assert can_execute is False
        assert "timelock active" in error.lower()

    def test_can_execute_emergency_action_after_timelock(self):
        """Test that action can be executed after timelock"""
        timelock = EmergencyGovernanceTimelock(emergency_timelock=10)

        timelock.schedule_emergency_action("prop_123", current_block_height=100)

        can_execute, error = timelock.can_execute_emergency_action("prop_123", current_block_height=110)

        assert can_execute is True
        assert error is None

    def test_cancel_emergency_action(self):
        """Test canceling emergency action"""
        timelock = EmergencyGovernanceTimelock()

        timelock.schedule_emergency_action("prop_123", current_block_height=100)
        assert "prop_123" in timelock.pending_emergency_actions

        timelock.cancel_emergency_action("prop_123")

        assert "prop_123" not in timelock.pending_emergency_actions

    def test_cancel_nonexistent_emergency_action(self):
        """Test canceling nonexistent emergency action"""
        timelock = EmergencyGovernanceTimelock()

        # Should not raise error
        timelock.cancel_emergency_action("prop_999")


@pytest.mark.security
class TestBlockchainSecurityManager:
    """Test unified blockchain security manager"""

    def test_init(self, blockchain):
        """Test security manager initialization"""
        manager = BlockchainSecurityManager(blockchain)

        assert manager.blockchain == blockchain
        assert manager.reorg_protection is not None
        assert manager.supply_validator is not None
        assert manager.overflow_protection is not None
        assert manager.mempool_manager is not None
        assert manager.block_size_validator is not None
        assert manager.dust_protection is not None
        assert manager.median_time_past is not None
        assert manager.emergency_timelock is not None

    def test_validate_new_transaction_valid(self, blockchain):
        """Test validation of valid transaction"""
        manager = BlockchainSecurityManager(blockchain)

        wallet1 = Wallet()
        wallet2 = Wallet()

        blockchain.mine_pending_transactions(wallet1.address)

        tx = blockchain.create_transaction(
            wallet1.address,
            wallet2.address,
            10.0,
            0.24,
            wallet1.private_key,
            wallet1.public_key
        )

        is_valid, error = manager.validate_new_transaction(tx)

    def test_validate_new_transaction_dust(self, blockchain):
        """Test rejection of dust transaction"""
        manager = BlockchainSecurityManager(blockchain)

        wallet1 = Wallet()
        wallet2 = Wallet()

        blockchain.mine_pending_transactions(wallet1.address)

        tx = blockchain.create_transaction(
            wallet1.address,
            wallet2.address,
            BlockchainSecurityConfig.MIN_TRANSACTION_AMOUNT / 2,
            0.0,
            wallet1.private_key,
            wallet1.public_key
        )

        is_valid, error = manager.validate_new_transaction(tx)

        assert is_valid is False

    def test_validate_new_transaction_coinbase_skip_dust(self, blockchain):
        """Test that coinbase transactions skip dust protection"""
        manager = BlockchainSecurityManager(blockchain)

        coinbase_tx = Transaction("COINBASE", "XAI" + "a" * 40, 50.0, 0.0)
        coinbase_tx.inputs = []
        coinbase_tx.outputs = [{"address": "XAI" + "a" * 40, "amount": 50.0}]

        is_valid, error = manager.validate_new_transaction(coinbase_tx)

    def test_validate_new_block_valid(self, blockchain):
        """Test validation of valid block"""
        manager = BlockchainSecurityManager(blockchain)

        wallet = Wallet()
        block = blockchain.mine_pending_transactions(wallet.address)

        is_valid, error = manager.validate_new_block(block)

    def test_add_checkpoint(self, blockchain):
        """Test adding checkpoint"""
        manager = BlockchainSecurityManager(blockchain)

        manager.add_checkpoint(100, "hash_100")

        assert manager.reorg_protection.is_checkpoint_block(100)

    def test_validate_chain_reorganization(self, blockchain):
        """Test chain reorganization validation"""
        manager = BlockchainSecurityManager(blockchain)

        is_valid, error = manager.validate_chain_reorganization(
            current_height=200,
            fork_point=150
        )

    def test_check_total_supply(self, blockchain):
        """Test total supply check"""
        manager = BlockchainSecurityManager(blockchain)

        is_valid, total_supply = manager.check_total_supply()

        assert isinstance(is_valid, bool)
        assert isinstance(total_supply, float)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
