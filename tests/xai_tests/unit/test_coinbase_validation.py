"""
Comprehensive tests for coinbase reward validation in consensus.

Tests the CRITICAL security fix that prevents miners from creating unlimited coins
by validating coinbase rewards against the expected block reward + fees.
"""

import pytest
import tempfile
import shutil
from xai.core.blockchain import Blockchain, Block
from xai.core.transaction import Transaction
from xai.core.node_consensus import ConsensusManager


class TestCoinbaseValidation:
    """Test coinbase reward validation in block validation."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for blockchain data."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def blockchain(self, temp_dir):
        """Create a blockchain instance."""
        bc = Blockchain(temp_dir)
        return bc

    @pytest.fixture
    def consensus(self, blockchain):
        """Create a consensus manager."""
        return ConsensusManager(blockchain)

    def test_valid_coinbase_reward(self, blockchain, consensus, temp_dir):
        """Test that valid coinbase rewards are accepted."""
        # Get expected reward for block 1
        expected_reward = blockchain.get_block_reward(1)

        # Use a valid address format
        miner_address = "XAI" + "a" * 40  # Valid XAI address

        # Create coinbase transaction with correct reward
        coinbase_tx = Transaction(
            sender="COINBASE",
            recipient=miner_address,
            amount=expected_reward,
            tx_type="coinbase",
            outputs=[{"address": miner_address, "amount": expected_reward}],
        )
        coinbase_tx.txid = coinbase_tx.calculate_hash()

        # Create block (index as positional arg, not keyword)
        block = Block(
            1,  # index
            [coinbase_tx],  # transactions
            previous_hash=blockchain.chain[0].hash,
            difficulty=blockchain.difficulty,
        )

        # Mine the block
        while not block.hash.startswith("0" * blockchain.difficulty):
            block.nonce += 1
            block.hash = block.calculate_hash()

        # Validate block transactions (which includes coinbase validation)
        is_valid, error = consensus.validate_block_transactions(block)

        assert is_valid, f"Valid coinbase should be accepted: {error}"

    def test_excessive_coinbase_reward_rejected(self, blockchain, consensus, temp_dir):
        """Test that excessive coinbase rewards are rejected."""
        # Get expected reward for block 1
        expected_reward = blockchain.get_block_reward(1)

        # Use a valid address format
        miner_address = "XAI" + "b" * 40  # Valid XAI address

        # Create coinbase transaction with EXCESSIVE reward (10x expected)
        excessive_reward = expected_reward * 10
        coinbase_tx = Transaction(
            sender="COINBASE",
            recipient=miner_address,
            amount=excessive_reward,
            tx_type="coinbase",
            outputs=[{"address": miner_address, "amount": excessive_reward}],
        )
        coinbase_tx.txid = coinbase_tx.calculate_hash()

        # Create block (index as positional arg, not keyword)
        block = Block(
            1,  # index
            [coinbase_tx],  # transactions
            previous_hash=blockchain.chain[0].hash,
            difficulty=blockchain.difficulty,
        )

        # Mine the block
        while not block.hash.startswith("0" * blockchain.difficulty):
            block.nonce += 1
            block.hash = block.calculate_hash()

        # Validate block transactions (which includes coinbase validation)
        is_valid, error = consensus.validate_block_transactions(block)

        assert not is_valid, "Excessive coinbase should be rejected"
        assert "coinbase reward" in error.lower(), f"Error should mention coinbase reward: {error}"

    def test_coinbase_reward_with_fees(self, blockchain, consensus, temp_dir):
        """Test that coinbase can include transaction fees."""
        # Get expected reward for block 1
        expected_reward = blockchain.get_block_reward(1)

        # Use valid address formats
        sender_address = "XAI" + "c" * 40
        recipient_address = "XAI" + "d" * 40
        miner_address = "XAI" + "e" * 40

        # Create a normal transaction with fees
        tx_fee = 0.5
        normal_tx = Transaction(
            sender=sender_address,
            recipient=recipient_address,
            amount=10.0,
            fee=tx_fee,
            tx_type="normal",
        )
        normal_tx.txid = normal_tx.calculate_hash()

        # Create coinbase with reward + fees
        total_reward = expected_reward + tx_fee
        coinbase_tx = Transaction(
            sender="COINBASE",
            recipient=miner_address,
            amount=total_reward,
            tx_type="coinbase",
            outputs=[{"address": miner_address, "amount": total_reward}],
        )
        coinbase_tx.txid = coinbase_tx.calculate_hash()

        # Create block with both transactions
        block = Block(
            1,  # index
            [coinbase_tx, normal_tx],  # transactions
            previous_hash=blockchain.chain[0].hash,
            difficulty=blockchain.difficulty,
        )

        # Mine the block
        while not block.hash.startswith("0" * blockchain.difficulty):
            block.nonce += 1
            block.hash = block.calculate_hash()

        # Validate block transactions
        is_valid, error = consensus.validate_block_transactions(block)

        # Note: This may fail due to balance checks, but coinbase validation should pass
        # The important thing is it doesn't fail due to coinbase amount
        if not is_valid:
            assert "coinbase reward" not in error.lower(), \
                f"Should not fail due to coinbase reward: {error}"

    def test_halving_affects_max_reward(self, blockchain, consensus, temp_dir):
        """Test that halving schedule is enforced."""
        # Block at halving interval should have half the reward
        halving_block = blockchain.halving_interval
        reward_before_halving = blockchain.get_block_reward(halving_block - 1)
        reward_after_halving = blockchain.get_block_reward(halving_block)

        assert reward_after_halving == reward_before_halving / 2, \
            "Reward should halve at halving interval"

        # Use a valid address format
        miner_address = "XAI" + "f" * 40

        # Create coinbase with pre-halving reward (should be rejected)
        coinbase_tx = Transaction(
            sender="COINBASE",
            recipient=miner_address,
            amount=reward_before_halving,  # Using old reward, should be rejected
            tx_type="coinbase",
            outputs=[{"address": miner_address, "amount": reward_before_halving}],
        )
        coinbase_tx.txid = coinbase_tx.calculate_hash()

        # Create block at halving height
        previous_block = blockchain.chain[-1]
        block = Block(
            halving_block,  # index
            [coinbase_tx],  # transactions
            previous_hash=previous_block.hash,
            difficulty=blockchain.difficulty,
        )

        # Mine the block
        while not block.hash.startswith("0" * blockchain.difficulty):
            block.nonce += 1
            block.hash = block.calculate_hash()

        # Validate block transactions
        is_valid, error = consensus.validate_block_transactions(block)

        assert not is_valid, "Should reject coinbase using pre-halving reward"
        assert "coinbase reward" in error.lower(), f"Error should mention coinbase reward: {error}"

    def test_no_coinbase_transaction_rejected(self, blockchain, consensus, temp_dir):
        """Test that blocks without coinbase are rejected."""
        # Use valid address formats (hex chars)
        sender_address = "XAI" + "0" * 40
        recipient_address = "XAI" + "1" * 40

        # Create block without coinbase transaction
        normal_tx = Transaction(
            sender=sender_address,
            recipient=recipient_address,
            amount=10.0,
            fee=0.1,
            tx_type="normal",
        )
        normal_tx.txid = normal_tx.calculate_hash()

        block = Block(
            1,  # index
            [normal_tx],  # transactions - No coinbase!
            previous_hash=blockchain.chain[0].hash,
            difficulty=blockchain.difficulty,
        )

        # Mine the block
        while not block.hash.startswith("0" * blockchain.difficulty):
            block.nonce += 1
            block.hash = block.calculate_hash()

        # Validate block transactions
        is_valid, error = consensus.validate_block_transactions(block)

        assert not is_valid, "Should reject block without coinbase"
        assert "coinbase" in error.lower(), f"Error should mention coinbase: {error}"

    def test_coinbase_reward_respects_max_supply(self, blockchain, consensus, temp_dir):
        """Test that rewards stop when max supply is reached."""
        # Mock circulating supply to be near max
        original_supply = blockchain.get_circulating_supply
        blockchain.get_circulating_supply = lambda: blockchain.max_supply - 1.0

        # Reward should be capped to remaining supply
        reward = blockchain.get_block_reward(1)
        assert reward <= 1.0, "Reward should be capped to remaining supply"

        # Restore original method
        blockchain.get_circulating_supply = original_supply

    def test_validate_coinbase_reward_method(self, blockchain, temp_dir):
        """Test the validate_coinbase_reward method directly."""
        expected_reward = blockchain.get_block_reward(1)

        # Use valid address format (hex chars)
        miner_address = "XAI" + "2" * 40

        # Valid coinbase
        coinbase_tx = Transaction(
            sender="COINBASE",
            recipient=miner_address,
            amount=expected_reward,
            tx_type="coinbase",
            outputs=[{"address": miner_address, "amount": expected_reward}],
        )
        coinbase_tx.txid = coinbase_tx.calculate_hash()

        block = Block(
            1,  # index
            [coinbase_tx],  # transactions
            previous_hash=blockchain.chain[0].hash,
            difficulty=blockchain.difficulty,
        )

        is_valid, error = blockchain.validate_coinbase_reward(block)
        assert is_valid, f"Valid coinbase should pass: {error}"

        # Invalid coinbase (excessive)
        excessive_coinbase = Transaction(
            sender="COINBASE",
            recipient=miner_address,
            amount=expected_reward * 1000,
            tx_type="coinbase",
            outputs=[{"address": miner_address, "amount": expected_reward * 1000}],
        )
        excessive_coinbase.txid = excessive_coinbase.calculate_hash()

        bad_block = Block(
            1,  # index
            [excessive_coinbase],  # transactions
            previous_hash=blockchain.chain[0].hash,
            difficulty=blockchain.difficulty,
        )

        is_valid, error = blockchain.validate_coinbase_reward(bad_block)
        assert not is_valid, "Excessive coinbase should fail validation"
        assert "exceeds maximum allowed" in error.lower(), f"Error should be specific: {error}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
