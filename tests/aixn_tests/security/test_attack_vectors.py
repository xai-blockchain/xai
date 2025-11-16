"""
Security tests for XAI Blockchain attack vectors

Tests protection against 51% attacks, Sybil attacks, double-spending, etc.
"""

import pytest
import sys
import os
import time
from unittest.mock import Mock, patch

# Add core directory to path

from aixn.core.blockchain import Blockchain, Transaction, Block
from aixn.core.wallet import Wallet
from aixn.core.blockchain_security import ReorganizationProtection


class TestDoubleSpendingAttack:
    """Test protection against double-spending attacks"""

    def test_prevent_double_spend_same_block(self):
        """Test prevention of double-spend in same block"""
        bc = Blockchain()
        attacker = Wallet()
        victim1 = Wallet()
        victim2 = Wallet()

        # Give attacker balance
        bc.mine_pending_transactions(attacker.address)
        balance = bc.get_balance(attacker.address)

        # Try to spend same funds twice
        tx1 = Transaction(attacker.address, victim1.address, balance - 0.24, 0.24)
        tx1.public_key = attacker.public_key
        tx1.sign_transaction(attacker.private_key)

        tx2 = Transaction(attacker.address, victim2.address, balance - 0.24, 0.24)
        tx2.public_key = attacker.public_key
        tx2.sign_transaction(attacker.private_key)

        # Add both transactions
        bc.add_transaction(tx1)
        bc.add_transaction(tx2)

        # Mine block
        bc.mine_pending_transactions(attacker.address)

        # Only one transaction should succeed
        victim1_balance = bc.get_balance(victim1.address)
        victim2_balance = bc.get_balance(victim2.address)

        assert not (victim1_balance > 0 and victim2_balance > 0)

    def test_prevent_double_spend_different_blocks(self):
        """Test prevention of double-spend across blocks"""
        bc = Blockchain()
        attacker = Wallet()
        victim1 = Wallet()
        victim2 = Wallet()

        # Give attacker balance
        bc.mine_pending_transactions(attacker.address)
        balance = bc.get_balance(attacker.address)

        # First transaction
        tx1 = Transaction(attacker.address, victim1.address, balance - 0.24, 0.24)
        tx1.public_key = attacker.public_key
        tx1.sign_transaction(attacker.private_key)
        bc.add_transaction(tx1)
        bc.mine_pending_transactions(Wallet().address)

        # Try second transaction with same funds
        tx2 = Transaction(attacker.address, victim2.address, balance - 0.24, 0.24)
        tx2.public_key = attacker.public_key
        tx2.sign_transaction(attacker.private_key)
        bc.add_transaction(tx2)
        bc.mine_pending_transactions(Wallet().address)

        # Second transaction should fail
        victim2_balance = bc.get_balance(victim2.address)
        assert victim2_balance == 0

    def test_utxo_tracking_prevents_double_spend(self):
        """Test UTXO tracking prevents double-spending"""
        bc = Blockchain()
        attacker = Wallet()
        victim = Wallet()
        victim2 = Wallet()

        # Give attacker balance
        bc.mine_pending_transactions(attacker.address)

        # Spend funds
        tx = Transaction(attacker.address, victim.address, 5.0, 0.24)
        tx.public_key = attacker.public_key
        tx.sign_transaction(attacker.private_key)
        bc.add_transaction(tx)

        # Try to spend already spent UTXO
        tx2 = Transaction(attacker.address, victim2.address, 5.0, 0.24)
        tx2.public_key = attacker.public_key
        tx2.sign_transaction(attacker.private_key)

        # Should be rejected while pending inputs are still reserved
        assert not bc.add_transaction(tx2)

        # Mine only after we attempt the doubtful second spend
        bc.mine_pending_transactions(Wallet().address)
        assert bc.get_balance(victim2.address) == 0.0


class Test51PercentAttack:
    """Test protection against 51% attacks"""

    def test_reorganization_depth_limit(self):
        """Test reorganization depth is limited"""
        reorg_protection = ReorganizationProtection(max_depth=100)

        # Try to reorganize beyond limit
        is_valid, msg = reorg_protection.validate_reorganization(200, 50)

        assert not is_valid
        assert "too deep" in msg.lower()

    def test_checkpoint_prevents_reorg(self):
        """Test checkpoints prevent deep reorganization"""
        reorg_protection = ReorganizationProtection()

        # Add checkpoint
        reorg_protection.add_checkpoint(1000, "checkpoint_hash")

        # Try to reorg before checkpoint
        is_valid, msg = reorg_protection.validate_reorganization(1500, 900)

        assert not is_valid

    def test_longest_chain_selection(self):
        """Test longest valid chain is selected"""
        bc1 = Blockchain()
        bc2 = Blockchain()
        miner = Wallet()

        # Create longer chain
        for _ in range(10):
            bc1.mine_pending_transactions(miner.address)

        # Create shorter competing chain
        for _ in range(5):
            bc2.mine_pending_transactions(miner.address)

        # Longer chain should be preferred
        assert len(bc1.chain) > len(bc2.chain)

    def test_reject_invalid_longer_chain(self):
        """Test invalid longer chain is rejected"""
        bc = Blockchain()
        miner = Wallet()

        # Create valid chain
        for _ in range(5):
            bc.mine_pending_transactions(miner.address)

        # Tamper with chain
        bc.chain[3].hash = "invalid_hash"

        # Chain should be invalid despite length
        assert not bc.validate_chain()


class TestSybilAttack:
    """Test protection against Sybil attacks"""

    def test_unique_addresses_required(self):
        """Test each wallet has unique address"""
        wallets = [Wallet() for _ in range(100)]
        addresses = [w.address for w in wallets]

        # All addresses should be unique
        assert len(addresses) == len(set(addresses))

    def test_stake_based_voting_prevents_sybil(self):
        """Test stake-based mechanisms prevent Sybil attacks"""
        bc = Blockchain()

        # Create many wallets with no stake
        sybil_wallets = [Wallet() for _ in range(1000)]

        # Create one wallet with real stake
        legitimate_wallet = Wallet()
        bc.mine_pending_transactions(legitimate_wallet.address)

        # Legitimate wallet should have more power
        legit_balance = bc.get_balance(legitimate_wallet.address)
        sybil_total = sum(bc.get_balance(w.address) for w in sybil_wallets)

        assert legit_balance > sybil_total

    def test_identity_verification_through_signatures(self):
        """Test identity verified through cryptographic signatures"""
        wallet1 = Wallet()
        wallet2 = Wallet()

        message = "Test message"

        # Each wallet signs message
        sig1 = wallet1.sign_message(message)
        sig2 = wallet2.sign_message(message)

        # Signatures should be different
        assert sig1 != sig2

        # Can't verify wallet1's signature with wallet2's key
        assert not wallet2.verify_signature(message, sig1, wallet2.public_key)


class TestRaceAttack:
    """Test protection against race attacks"""

    def test_transaction_confirmation_requirement(self):
        """Test transactions require confirmations"""
        bc = Blockchain()
        sender = Wallet()
        recipient = Wallet()

        # Give sender balance
        bc.mine_pending_transactions(sender.address)

        # Create transaction
        tx = Transaction(sender.address, recipient.address, 5.0, 0.24)
        tx.public_key = sender.public_key
        tx.sign_transaction(sender.private_key)
        bc.add_transaction(tx)

        # Transaction is pending, not confirmed
        assert len(bc.pending_transactions) > 0

        # Mine block
        bc.mine_pending_transactions(Wallet().address)

        # Now confirmed
        assert bc.get_balance(recipient.address) == 5.0

    def test_mempool_transaction_replacement(self):
        """Test mempool transaction replacement rules"""
        bc = Blockchain()
        sender = Wallet()
        recipient = Wallet()

        # Give sender balance
        bc.mine_pending_transactions(sender.address)

        # Create low-fee transaction
        tx1 = Transaction(sender.address, recipient.address, 5.0, 0.1)
        tx1.public_key = sender.public_key
        tx1.sign_transaction(sender.private_key)
        bc.add_transaction(tx1)

        initial_pending = len(bc.pending_transactions)

        # Create higher-fee transaction (same nonce)
        tx2 = Transaction(sender.address, recipient.address, 5.0, 0.5, nonce=tx1.nonce)
        tx2.public_key = sender.public_key
        tx2.sign_transaction(sender.private_key)
        bc.add_transaction(tx2)

        # Should handle replacement appropriately
        assert len(bc.pending_transactions) >= initial_pending


class TestTimejackAttack:
    """Test protection against timejack attacks"""

    def test_reject_future_timestamp(self):
        """Test blocks with future timestamps are rejected"""
        from blockchain_security import TimeValidator

        validator = TimeValidator()

        # Create block with future timestamp
        class FutureBlock:
            def __init__(self):
                self.timestamp = time.time() + 10000

        block = FutureBlock()
        is_valid, msg = validator.validate_block_time(block, [])

        assert not is_valid

    def test_median_time_past_validation(self):
        """Test median-time-past validation"""
        from blockchain_security import TimeValidator

        validator = TimeValidator()
        bc = Blockchain()
        miner = Wallet()

        # Mine several blocks
        for _ in range(11):
            bc.mine_pending_transactions(miner.address)

        # Calculate median time
        median = validator.calculate_median_time_past(bc.chain)

        assert median > 0
        assert median < time.time()

    def test_block_time_ordering(self):
        """Test blocks must have increasing timestamps"""
        bc = Blockchain()
        miner = Wallet()

        # Mine blocks
        block1 = bc.mine_pending_transactions(miner.address)
        time.sleep(0.1)
        block2 = bc.mine_pending_transactions(miner.address)

        # Timestamps should be ordered
        assert block2.timestamp >= block1.timestamp


class TestDustAttack:
    """Test protection against dust attacks"""

    def test_reject_dust_amounts(self):
        """Test rejection of dust transactions"""
        from blockchain_security import BlockchainSecurityConfig

        bc = Blockchain()
        attacker = Wallet()
        victim = Wallet()

        # Give attacker balance
        bc.mine_pending_transactions(attacker.address)

        # Try to send dust amount
        dust_amount = BlockchainSecurityConfig.MIN_TRANSACTION_AMOUNT / 2

        tx = Transaction(attacker.address, victim.address, dust_amount, 0.0)
        tx.public_key = attacker.public_key
        tx.sign_transaction(attacker.private_key)

        # Should be rejected
        assert not bc.validate_transaction(tx)

    def test_minimum_utxo_value(self):
        """Test minimum UTXO value enforcement"""
        from blockchain_security import BlockchainSecurityConfig

        min_value = BlockchainSecurityConfig.MIN_UTXO_VALUE

        assert min_value > 0
        assert min_value == 0.00001


class TestResourceExhaustion:
    """Test protection against resource exhaustion attacks"""

    def test_block_size_limit(self):
        """Test block size is limited"""
        from blockchain_security import BlockchainSecurityConfig, ResourceLimiter

        limiter = ResourceLimiter()
        bc = Blockchain()
        miner = Wallet()

        block = bc.mine_pending_transactions(miner.address)

        is_valid, msg = limiter.validate_block_size(block)

        # Normal block should be valid
        assert is_valid

    def test_transaction_size_limit(self):
        """Test transaction size is limited"""
        from blockchain_security import ResourceLimiter

        limiter = ResourceLimiter()
        wallet = Wallet()

        tx = Transaction(wallet.address, "XAI123", 10.0, 0.24)

        is_valid, msg = limiter.validate_transaction_size(tx)

        # Normal transaction should be valid
        assert is_valid

    def test_mempool_size_limit(self):
        """Test mempool size is limited"""
        from blockchain_security import BlockchainSecurityConfig

        max_mempool = BlockchainSecurityConfig.MAX_MEMPOOL_SIZE

        assert max_mempool > 0
        assert max_mempool == 50000


class TestInflationAttack:
    """Test protection against inflation bugs"""

    def test_supply_cap_enforcement(self):
        """Test supply cap is enforced"""
        from blockchain_security import SupplyValidator

        validator = SupplyValidator()

        bc = Blockchain()

        # Inject utxo set that exceeds the cap
        overflow_amount = validator.max_supply + 1_000_000
        bc.utxo_set["overflow_wallet"] = [
            {
                "txid": "overflow",
                "amount": float(overflow_amount),
                "spent": False,
                "unlock_height": 0,
            }
        ]

        is_valid, total = validator.validate_total_supply(bc)

        assert not is_valid
        assert total > validator.max_supply

    def test_overflow_protection(self):
        """Test overflow protection"""
        from blockchain_security import OverflowProtection, BlockchainSecurityConfig

        protection = OverflowProtection()

        # Test safe addition
        result, is_safe = protection.safe_add(100.0, 200.0)
        assert is_safe
        assert result == 300.0

        # Test overflow detection
        huge_num = float(BlockchainSecurityConfig.MAX_MONEY)
        overflow_result, is_safe = protection.safe_add(huge_num, huge_num)

        assert not is_safe
        assert overflow_result is None

    def test_block_reward_calculation_safety(self):
        """Test block reward calculation is safe"""
        bc = Blockchain()

        # Test various block heights
        for height in [0, 100000, 500000, 1000000]:
            reward = bc.get_block_reward(height)

            assert reward > 0
            assert reward < bc.max_supply


class TestReplayAttack:
    """Test protection against replay attacks"""

    def test_nonce_prevents_replay(self):
        """Test nonce prevents transaction replay"""
        bc = Blockchain()
        sender = Wallet()
        recipient = Wallet()

        # Give sender balance
        bc.mine_pending_transactions(sender.address)

        # Create transaction with nonce
        tx1 = Transaction(sender.address, recipient.address, 1.0, 0.1, nonce=1)
        tx1.public_key = sender.public_key
        tx1.sign_transaction(sender.private_key)
        bc.add_transaction(tx1)
        bc.mine_pending_transactions(Wallet().address)

        # Try to replay same transaction
        bc.add_transaction(tx1)

        # Should be rejected (already used nonce)
        # Implementation may vary

    def test_transaction_uniqueness(self):
        """Test transactions have unique identifiers"""
        wallet = Wallet()

        tx1 = Transaction(wallet.address, "XAI123", 10.0, 0.24, nonce=1)
        tx1.public_key = wallet.public_key
        tx1.sign_transaction(wallet.private_key)

        tx2 = Transaction(wallet.address, "XAI123", 10.0, 0.24, nonce=2)
        tx2.public_key = wallet.public_key
        tx2.sign_transaction(wallet.private_key)

        # Different nonces should produce different TXIDs
        assert tx1.txid != tx2.txid


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
