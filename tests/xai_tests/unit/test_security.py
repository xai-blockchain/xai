"""
Unit tests for XAI Security modules

Tests blockchain security, validation, and protection mechanisms
"""

import pytest
import sys
import os
import time
from decimal import Decimal

# Add core directory to path

from xai.core.security.blockchain_security import (
    BlockchainSecurityConfig,
    ReorganizationProtection,
    SupplyValidator,
    ResourceLimiter,
    TimeValidator,
    OverflowProtection,
)
from xai.core.blockchain import Blockchain, Transaction, Block
from xai.core.wallet import Wallet


class TestSecurityConfiguration:
    """Test security configuration constants"""

    def test_block_size_limits(self, tmp_path):
        """Test block size limits are defined"""
        assert BlockchainSecurityConfig.MAX_BLOCK_SIZE > 0
        assert BlockchainSecurityConfig.MAX_TRANSACTION_SIZE > 0
        assert BlockchainSecurityConfig.MAX_TRANSACTIONS_PER_BLOCK > 0

    def test_mempool_limits(self, tmp_path):
        """Test mempool limits are defined"""
        assert BlockchainSecurityConfig.MAX_MEMPOOL_SIZE > 0
        assert BlockchainSecurityConfig.MAX_MEMPOOL_BYTES > 0

    def test_dust_protection(self, tmp_path):
        """Test dust protection limits"""
        assert BlockchainSecurityConfig.MIN_TRANSACTION_AMOUNT > 0
        assert BlockchainSecurityConfig.MIN_UTXO_VALUE > 0

    def test_reorg_protection(self, tmp_path):
        """Test reorganization protection limits"""
        assert BlockchainSecurityConfig.MAX_REORG_DEPTH > 0
        assert BlockchainSecurityConfig.CHECKPOINT_INTERVAL > 0

    def test_supply_validation(self, tmp_path):
        """Test supply validation constants"""
        assert BlockchainSecurityConfig.MAX_SUPPLY == 121_000_000
        assert BlockchainSecurityConfig.SUPPLY_CHECK_INTERVAL > 0


class TestReorganizationProtection:
    """Test protection against 51% attacks"""

    def test_create_reorg_protection(self, tmp_path):
        """Test creating reorganization protection"""
        reorg_protection = ReorganizationProtection()

        assert reorg_protection.max_depth == BlockchainSecurityConfig.MAX_REORG_DEPTH
        assert isinstance(reorg_protection.checkpoints, dict)

    def test_add_checkpoint(self, tmp_path):
        """Test adding checkpoints"""
        reorg_protection = ReorganizationProtection()

        reorg_protection.add_checkpoint(1000, "abc123")

        assert 1000 in reorg_protection.checkpoints
        assert reorg_protection.checkpoints[1000] == "abc123"

    def test_validate_allowed_reorg(self, tmp_path):
        """Test validation of allowed reorganization"""
        reorg_protection = ReorganizationProtection(max_depth=100)

        # Reorg within limit should be allowed
        is_valid, msg = reorg_protection.validate_reorganization(200, 150)

        assert is_valid

    def test_reject_deep_reorg(self, tmp_path):
        """Test rejection of deep reorganization"""
        reorg_protection = ReorganizationProtection(max_depth=100)

        # Reorg beyond limit should be rejected
        is_valid, msg = reorg_protection.validate_reorganization(200, 50)

        assert not is_valid
        assert "too deep" in msg.lower()

    def test_checkpoint_prevents_reorg(self, tmp_path):
        """Test checkpoint prevents reorganization"""
        reorg_protection = ReorganizationProtection()

        # Add checkpoint
        reorg_protection.add_checkpoint(100, "checkpoint_hash")

        # Try to reorg before checkpoint
        is_valid, msg = reorg_protection.validate_reorganization(200, 90)

        assert not is_valid


class TestSupplyValidator:
    """Test supply cap validation"""

    def test_create_supply_validator(self, tmp_path):
        """Test creating supply validator"""
        validator = SupplyValidator()

        assert validator.max_supply == 121_000_000

    def test_validate_supply_under_cap(self, tmp_path):
        """Test validation when supply is under cap"""
        validator = SupplyValidator()

        is_valid, msg = validator.validate_total_supply(100_000_000)

        assert is_valid

    def test_reject_supply_over_cap(self, tmp_path):
        """Test rejection when supply exceeds cap"""
        validator = SupplyValidator()

        is_valid, msg = validator.validate_total_supply(122_000_000)

        assert not is_valid
        assert "exceeds" in msg.lower()

    def test_validate_block_reward(self, tmp_path):
        """Test block reward validation"""
        validator = SupplyValidator()

        # Normal reward should be valid
        is_valid, msg = validator.validate_block_reward(12.0, 0)

        assert is_valid

    def test_reject_excessive_reward(self, tmp_path):
        """Test rejection of excessive block reward"""
        validator = SupplyValidator()

        # Excessive reward should be rejected
        is_valid, msg = validator.validate_block_reward(1_000_000, 0)

        assert not is_valid


class TestResourceLimiter:
    """Test resource exhaustion protection"""

    def test_create_resource_limiter(self, tmp_path):
        """Test creating resource limiter"""
        limiter = ResourceLimiter()

        assert limiter.max_mempool_size == BlockchainSecurityConfig.MAX_MEMPOOL_SIZE

    def test_validate_transaction_size(self, tmp_path):
        """Test transaction size validation"""
        limiter = ResourceLimiter()
        wallet1 = Wallet()
        wallet2 = Wallet()

        tx = Transaction(wallet1.address, wallet2.address, 10.0, 0.24)

        is_valid, msg = limiter.validate_transaction_size(tx)

        assert is_valid

    def test_reject_oversized_transaction(self, tmp_path):
        """Test rejection of oversized transaction"""
        limiter = ResourceLimiter()

        # Create mock oversized transaction
        class OversizedTx:
            def __init__(self):
                self.sender = "X" * 1000000
                self.recipient = "Y" * 1000000
                self.amount = 1.0

        tx = OversizedTx()

        is_valid, msg = limiter.validate_transaction_size(tx)

        assert not is_valid

    def test_validate_block_size(self, tmp_path):
        """Test block size validation"""
        limiter = ResourceLimiter()
        bc = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        block = bc.mine_pending_transactions(wallet.address)

        is_valid, msg = limiter.validate_block_size(block)

        assert is_valid

    def test_mempool_limit_enforcement(self, tmp_path):
        """Test mempool size limit enforcement"""
        limiter = ResourceLimiter()

        # Should allow adding when under limit
        can_add = limiter.can_add_to_mempool(100)

        assert can_add


class TestDustProtection:
    """Test protection against dust attacks"""

    def test_minimum_transaction_amount(self, tmp_path):
        """Test minimum transaction amount"""
        min_amount = BlockchainSecurityConfig.MIN_TRANSACTION_AMOUNT

        assert min_amount == 0.00001

    def test_reject_dust_transaction(self, tmp_path):
        """Test rejection of dust transactions"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet1 = Wallet()
        wallet2 = Wallet()

        # Give wallet1 balance
        bc.mine_pending_transactions(wallet1.address)

        # Try to send dust amount
        tx = bc.create_transaction(
            wallet1.address, wallet2.address, 0.000001, 0.0, wallet1.private_key, wallet1.public_key
        )

        # Should be rejected as dust
        assert not bc.validate_transaction(tx)

    def test_accept_valid_amount(self, tmp_path):
        """Test acceptance of valid transaction amounts"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet1 = Wallet()
        wallet2 = Wallet()

        bc.mine_pending_transactions(wallet1.address)

        # Send valid amount (above dust threshold 0.00001)
        tx = bc.create_transaction(
            wallet1.address, wallet2.address, 0.001, 0.24, wallet1.private_key, wallet1.public_key
        )

        assert bc.validate_transaction(tx)


class TestTimeValidator:
    """Test time validation and manipulation protection"""

    def test_create_time_validator(self, tmp_path):
        """Test creating time validator"""
        validator = TimeValidator()

        assert validator.median_time_span == 11

    def test_calculate_median_time(self, tmp_path):
        """Test median time calculation"""
        validator = TimeValidator()
        bc = Blockchain(data_dir=str(tmp_path))

        median_time = validator.calculate_median_time_past(bc.chain)

        assert median_time > 0

    def test_validate_block_time(self, tmp_path):
        """Test block timestamp validation"""
        validator = TimeValidator()
        bc = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        block = bc.mine_pending_transactions(wallet.address)

        is_valid, msg = validator.validate_block_time(block, bc.chain)

        assert is_valid

    def test_reject_future_timestamp(self, tmp_path):
        """Test rejection of future timestamps"""
        validator = TimeValidator()

        # Create block with future timestamp
        class FutureBlock:
            def __init__(self):
                self.timestamp = time.time() + 10000  # Far future

        block = FutureBlock()

        is_valid, msg = validator.validate_block_time(block, [])

        assert not is_valid

    def test_reject_past_timestamp(self, tmp_path):
        """Test rejection of timestamps before median"""
        validator = TimeValidator()
        bc = Blockchain(data_dir=str(tmp_path))

        # Mine some blocks
        wallet = Wallet()
        for _ in range(5):
            bc.mine_pending_transactions(wallet.address)

        # Try to create block with old timestamp
        class OldBlock:
            def __init__(self):
                self.timestamp = time.time() - 100000

        block = OldBlock()

        is_valid, msg = validator.validate_block_time(block, bc.chain)

        assert not is_valid


class TestOverflowProtection:
    """Test overflow and inflation bug protection"""

    def test_create_overflow_protection(self, tmp_path):
        """Test creating overflow protection"""
        protection = OverflowProtection()

        assert protection.max_money > 0

    def test_validate_amount_range(self, tmp_path):
        """Test amount range validation"""
        protection = OverflowProtection()

        # Normal amount should be valid
        is_valid, msg = protection.validate_amount(100.0)

        assert is_valid

    def test_reject_negative_amount(self, tmp_path):
        """Test rejection of negative amounts"""
        protection = OverflowProtection()

        is_valid, msg = protection.validate_amount(-10.0)

        assert not is_valid

    def test_reject_overflow_amount(self, tmp_path):
        """Test rejection of overflow amounts"""
        protection = OverflowProtection()

        # Try to create overflow
        is_valid, msg = protection.validate_amount(999_999_999_999_999)

        assert not is_valid

    def test_safe_addition(self, tmp_path):
        """Test safe addition without overflow"""
        protection = OverflowProtection()

        result, is_safe = protection.safe_add(100.0, 200.0)

        assert is_safe
        assert result == 300.0

    def test_detect_overflow_addition(self, tmp_path):
        """Test detection of overflow in addition"""
        protection = OverflowProtection()

        huge_num = 100_000_000_000_000
        result, is_safe = protection.safe_add(huge_num, huge_num)

        assert not is_safe

    def test_safe_multiplication(self, tmp_path):
        """Test safe multiplication"""
        protection = OverflowProtection()

        result, is_safe = protection.safe_multiply(100.0, 10.0)

        assert is_safe
        assert result == 1000.0

    def test_detect_overflow_multiplication(self, tmp_path):
        """Test detection of overflow in multiplication"""
        protection = OverflowProtection()

        huge_num = 10_000_000_000
        result, is_safe = protection.safe_multiply(huge_num, huge_num)

        assert not is_safe


class TestInputValidation:
    """Test input validation and sanitization"""

    def test_validate_address_format(self, tmp_path):
        """Test address format validation"""
        wallet = Wallet()

        # Valid address
        assert wallet.address.startswith("XAI")
        assert len(wallet.address) == 43

    def test_reject_invalid_address(self, tmp_path):
        """Test rejection of invalid addresses"""
        from xai.core.transaction import TransactionValidationError
        bc = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        bc.mine_pending_transactions(wallet.address)

        # Invalid address format - should raise validation error during creation
        with pytest.raises(TransactionValidationError):
            bc.create_transaction(
                wallet.address, "INVALID", 10.0, 0.24, wallet.private_key, wallet.public_key
            )

    def test_validate_amount_precision(self, tmp_path):
        """Test amount precision validation"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet1 = Wallet()
        wallet2 = Wallet()

        bc.mine_pending_transactions(wallet1.address)

        # Valid precision
        tx = bc.create_transaction(
            wallet1.address,
            wallet2.address,
            10.12345678,
            0.24,
            wallet1.private_key,
            wallet1.public_key,
        )

        # Should validate
        bc.validate_transaction(tx)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
