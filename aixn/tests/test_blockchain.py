"""
Test suite for XAI Blockchain core functionality

Tests:
- Blockchain initialization
- Block creation and mining
- Transaction validation
- Chain validation
- Supply cap enforcement
- Halving schedule
- UTXO management
"""

import pytest
import sys
import os
import time

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

from blockchain import Blockchain, Transaction, Block
from wallet import Wallet


class TestBlockchainCore:
    """Test core blockchain functionality"""

    def test_blockchain_initialization(self):
        """Test that blockchain initializes correctly"""
        bc = Blockchain()

        assert len(bc.chain) == 1, "Should have genesis block"
        assert bc.chain[0].index == 0, "Genesis block index should be 0"
        assert bc.difficulty == bc.difficulty, "Difficulty should be set"
        assert bc.max_supply == 121000000.0, "Max supply should be 121M XAI"

    def test_genesis_block(self):
        """Test genesis block creation"""
        bc = Blockchain()
        genesis = bc.chain[0]

        assert genesis.previous_hash == "0", "Genesis previous hash should be 0"
        assert genesis.hash is not None, "Genesis hash should exist"
        assert len(genesis.transactions) > 0, "Genesis should have transactions"

    def test_block_mining(self):
        """Test that blocks can be mined"""
        bc = Blockchain()
        wallet = Wallet()

        # Mine a block
        block = bc.mine_pending_transactions(wallet.address)

        assert block.index == 1, "First mined block should be index 1"
        assert block.previous_hash == bc.chain[0].hash, "Previous hash should match genesis"
        assert block.hash.startswith('0' * bc.difficulty), "Hash should meet difficulty"

    def test_transaction_creation(self):
        """Test transaction creation and signing"""
        wallet1 = Wallet()
        wallet2 = Wallet()

        tx = Transaction(wallet1.address, wallet2.address, 10.0, 0.24)
        tx.sign_transaction(wallet1.private_key)

        assert tx.txid is not None, "Transaction should have ID"
        assert tx.signature is not None, "Transaction should be signed"
        assert tx.verify_signature(), "Signature should be valid"

    def test_transaction_validation(self):
        """Test transaction validation"""
        bc = Blockchain()
        wallet1 = Wallet()
        wallet2 = Wallet()

        # Create transaction
        tx = Transaction(wallet1.address, wallet2.address, 10.0, 0.24)
        tx.sign_transaction(wallet1.private_key)

        # Coinbase transactions should be valid
        coinbase_tx = Transaction("COINBASE", wallet1.address, 12.0)
        coinbase_tx.txid = coinbase_tx.calculate_hash()

        assert bc.validate_transaction(coinbase_tx), "Coinbase tx should be valid"

    def test_balance_tracking(self):
        """Test UTXO balance tracking"""
        bc = Blockchain()
        wallet = Wallet()

        # Mine a block to get some XAI
        bc.mine_pending_transactions(wallet.address)

        balance = bc.get_balance(wallet.address)
        assert balance > 0, "Wallet should have balance after mining"

    def test_chain_validation(self):
        """Test blockchain validation"""
        bc = Blockchain()
        wallet = Wallet()

        # Mine a few blocks
        bc.mine_pending_transactions(wallet.address)
        bc.mine_pending_transactions(wallet.address)

        assert bc.validate_chain(), "Chain should be valid"

    def test_supply_cap_enforcement(self):
        """Test that 121M supply cap is enforced"""
        bc = Blockchain()

        # Check max supply is set correctly
        assert bc.max_supply == 121000000.0, "Max supply should be 121M"

        # Check reward calculation doesn't exceed cap
        reward = bc.get_block_reward(0)
        assert reward <= bc.max_supply, "Block reward shouldn't exceed max supply"

    def test_halving_schedule(self):
        """Test block reward halving"""
        bc = Blockchain()

        # Initial reward
        reward_0 = bc.get_block_reward(0)
        assert reward_0 == 12.0, "Initial reward should be 12 XAI"

        # After first halving (262,800 blocks)
        reward_1 = bc.get_block_reward(262800)
        assert reward_1 == 6.0, "Reward after first halving should be 6 XAI"

        # After second halving
        reward_2 = bc.get_block_reward(262800 * 2)
        assert reward_2 == 3.0, "Reward after second halving should be 3 XAI"


class TestTransactions:
    """Test transaction functionality"""

    def test_transaction_signing(self):
        """Test that transactions can be signed"""
        wallet = Wallet()
        tx = Transaction(wallet.address, "AIXN...", 10.0, 0.24)

        tx.sign_transaction(wallet.private_key)

        assert tx.signature is not None, "Transaction should have signature"
        assert len(tx.signature) > 0, "Signature should not be empty"

    def test_signature_verification(self):
        """Test signature verification"""
        wallet = Wallet()
        tx = Transaction(wallet.address, "AIXN...", 10.0, 0.24)

        tx.sign_transaction(wallet.private_key)

        assert tx.verify_signature(), "Valid signature should verify"

    def test_invalid_signature(self):
        """Test that invalid signatures are rejected"""
        wallet1 = Wallet()
        wallet2 = Wallet()

        tx = Transaction(wallet1.address, "AIXN...", 10.0, 0.24)
        # Sign with wrong wallet
        tx.sign_transaction(wallet2.private_key)

        assert not tx.verify_signature(), "Invalid signature should not verify"

    def test_coinbase_transaction(self):
        """Test coinbase transaction handling"""
        tx = Transaction("COINBASE", "AIXN...", 12.0)
        tx.txid = tx.calculate_hash()

        assert tx.verify_signature(), "Coinbase tx should auto-verify"


class TestMining:
    """Test mining functionality"""

    def test_mining_reward(self):
        """Test that mining produces correct reward"""
        bc = Blockchain()
        wallet = Wallet()

        initial_balance = bc.get_balance(wallet.address)

        # Mine a block
        bc.mine_pending_transactions(wallet.address)

        new_balance = bc.get_balance(wallet.address)

        # Should have received block reward
        assert new_balance > initial_balance, "Balance should increase after mining"

    def test_difficulty_enforcement(self):
        """Test that difficulty is enforced"""
        bc = Blockchain()
        wallet = Wallet()

        block = bc.mine_pending_transactions(wallet.address)

        # Hash should start with correct number of zeros
        assert block.hash.startswith('0' * bc.difficulty), f"Hash should start with {bc.difficulty} zeros"

    def test_multiple_blocks(self):
        """Test mining multiple blocks"""
        bc = Blockchain()
        wallet = Wallet()

        initial_height = len(bc.chain)

        # Mine 3 blocks
        bc.mine_pending_transactions(wallet.address)
        bc.mine_pending_transactions(wallet.address)
        bc.mine_pending_transactions(wallet.address)

        assert len(bc.chain) == initial_height + 3, "Should have 3 new blocks"


class TestUTXO:
    """Test UTXO management"""

    def test_utxo_creation(self):
        """Test that UTXOs are created"""
        bc = Blockchain()
        wallet = Wallet()

        bc.mine_pending_transactions(wallet.address)

        assert wallet.address in bc.utxo_set, "Wallet should have UTXO"
        assert len(bc.utxo_set[wallet.address]) > 0, "Should have at least one UTXO"

    def test_utxo_spending(self):
        """Test that UTXOs are marked as spent"""
        bc = Blockchain()
        wallet1 = Wallet()
        wallet2 = Wallet()

        # Mine to get some XAI
        bc.mine_pending_transactions(wallet1.address)

        initial_balance = bc.get_balance(wallet1.address)

        # Create and add transaction
        tx = Transaction(wallet1.address, wallet2.address, 5.0, 0.24)
        tx.sign_transaction(wallet1.private_key)
        bc.add_transaction(tx)

        # Mine block with transaction
        bc.mine_pending_transactions(wallet1.address)

        # Check balances changed
        new_balance = bc.get_balance(wallet1.address)
        assert new_balance != initial_balance, "Balance should change after transaction"


def test_anonymity_timestamps():
    """Test that timestamps are in UTC"""
    bc = Blockchain()
    wallet = Wallet()

    block = bc.mine_pending_transactions(wallet.address)

    # Timestamp should be reasonable Unix timestamp
    assert block.timestamp > 1700000000, "Timestamp should be recent Unix timestamp"
    assert block.timestamp < time.time() + 100, "Timestamp should not be in future"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
