"""
Integration tests for XAI Mining workflow

Tests complete mining workflow including transactions, rewards, and blockchain state
"""

import pytest
import sys
import os
import time

# Add core directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "core"))

from blockchain import Blockchain, Transaction
from wallet import Wallet


class TestMiningWorkflow:
    """Test complete mining workflow"""

    def test_mine_empty_block(self):
        """Test mining block with no transactions"""
        bc = Blockchain()
        wallet = Wallet()

        initial_height = len(bc.chain)
        block = bc.mine_pending_transactions(wallet.address)

        assert len(bc.chain) == initial_height + 1
        assert bc.validate_chain()
        assert bc.get_balance(wallet.address) > 0

    def test_mine_block_with_transactions(self):
        """Test mining block with pending transactions"""
        bc = Blockchain()
        miner = Wallet()
        sender = Wallet()
        recipient = Wallet()

        # Give sender some balance
        bc.mine_pending_transactions(sender.address)

        # Create transaction
        tx = Transaction(sender.address, recipient.address, 5.0, 0.24)
        tx.public_key = sender.public_key
        tx.sign_transaction(sender.private_key)
        bc.add_transaction(tx)

        # Mine block
        initial_height = len(bc.chain)
        block = bc.mine_pending_transactions(miner.address)

        assert len(bc.chain) == initial_height + 1
        assert bc.get_balance(recipient.address) > 0
        assert bc.validate_chain()

    def test_mining_reward_distribution(self):
        """Test mining rewards are correctly distributed"""
        bc = Blockchain()
        miner = Wallet()

        # Mine multiple blocks
        rewards = []
        for i in range(3):
            balance_before = bc.get_balance(miner.address)
            bc.mine_pending_transactions(miner.address)
            balance_after = bc.get_balance(miner.address)

            reward = balance_after - balance_before
            rewards.append(reward)

        # All rewards should be consistent (same height)
        assert all(r == rewards[0] for r in rewards)

    def test_transaction_fees_to_miner(self):
        """Test transaction fees go to miner"""
        bc = Blockchain()
        miner = Wallet()
        sender = Wallet()
        recipient = Wallet()

        # Give sender balance
        bc.mine_pending_transactions(sender.address)

        # Create transaction with fee
        tx = Transaction(sender.address, recipient.address, 5.0, 0.5)
        tx.public_key = sender.public_key
        tx.sign_transaction(sender.private_key)
        bc.add_transaction(tx)

        # Mine block
        miner_balance_before = bc.get_balance(miner.address)
        bc.mine_pending_transactions(miner.address)
        miner_balance_after = bc.get_balance(miner.address)

        # Miner should receive block reward + fees
        expected_reward = bc.get_block_reward(len(bc.chain) - 1) + 0.5
        actual_reward = miner_balance_after - miner_balance_before

        assert abs(actual_reward - expected_reward) < 0.01

    def test_multiple_transactions_in_block(self):
        """Test mining block with multiple transactions"""
        bc = Blockchain()
        miner = Wallet()
        sender = Wallet()
        recipients = [Wallet() for _ in range(3)]

        # Give sender balance
        bc.mine_pending_transactions(sender.address)
        bc.mine_pending_transactions(sender.address)
        bc.mine_pending_transactions(sender.address)

        # Create multiple transactions
        for recipient in recipients:
            tx = Transaction(sender.address, recipient.address, 1.0, 0.1)
            tx.public_key = sender.public_key
            tx.sign_transaction(sender.private_key)
            bc.add_transaction(tx)

        # Mine block
        block = bc.mine_pending_transactions(miner.address)

        # All recipients should have balance
        for recipient in recipients:
            assert bc.get_balance(recipient.address) == 1.0

    def test_consecutive_mining(self):
        """Test consecutive block mining"""
        bc = Blockchain()
        miner = Wallet()

        initial_height = len(bc.chain)

        # Mine 5 blocks consecutively
        for i in range(5):
            block = bc.mine_pending_transactions(miner.address)
            assert block.index == initial_height + i
            assert block.miner == miner.address

        assert len(bc.chain) == initial_height + 5
        assert bc.validate_chain()


class TestMiningRewards:
    """Test mining reward calculations"""

    def test_initial_reward_correct(self):
        """Test initial mining reward"""
        bc = Blockchain()
        miner = Wallet()

        initial_balance = bc.get_balance(miner.address)
        bc.mine_pending_transactions(miner.address)
        new_balance = bc.get_balance(miner.address)

        reward = new_balance - initial_balance
        assert reward == 12.0

    def test_reward_consistency(self):
        """Test rewards are consistent at same height"""
        bc = Blockchain()
        miner1 = Wallet()
        miner2 = Wallet()

        # Mine with first miner
        bc.mine_pending_transactions(miner1.address)
        reward1 = bc.get_balance(miner1.address)

        # Mine with second miner
        bc.mine_pending_transactions(miner2.address)
        reward2 = bc.get_balance(miner2.address)

        # Rewards should be same (same height range)
        assert reward1 == reward2

    def test_reward_halving_integration(self):
        """Test reward halving at correct intervals"""
        bc = Blockchain()
        miner = Wallet()

        # Test reward at block 0
        reward_0 = bc.get_block_reward(0)
        assert reward_0 == 12.0

        # Test reward after halving
        reward_halved = bc.get_block_reward(262800)
        assert reward_halved == 6.0

    def test_cumulative_rewards(self):
        """Test cumulative mining rewards"""
        bc = Blockchain()
        miner = Wallet()

        # Mine 5 blocks
        for _ in range(5):
            bc.mine_pending_transactions(miner.address)

        total_balance = bc.get_balance(miner.address)
        expected_total = 12.0 * 5

        assert total_balance == expected_total


class TestMiningWithTransactions:
    """Test mining with various transaction scenarios"""

    def test_transaction_confirmation(self):
        """Test transactions get confirmed in blocks"""
        bc = Blockchain()
        miner = Wallet()
        sender = Wallet()
        recipient = Wallet()

        # Give sender balance
        bc.mine_pending_transactions(sender.address)

        # Create transaction
        tx = Transaction(sender.address, recipient.address, 5.0, 0.24)
        tx.public_key = sender.public_key
        tx.sign_transaction(sender.private_key)
        bc.add_transaction(tx)

        # Transaction should be pending
        assert len(bc.pending_transactions) > 0

        # Mine block
        bc.mine_pending_transactions(miner.address)

        # Transaction should be confirmed
        assert len(bc.pending_transactions) == 0
        assert bc.get_balance(recipient.address) == 5.0

    def test_invalid_transaction_rejection(self):
        """Test invalid transactions are not included in blocks"""
        bc = Blockchain()
        miner = Wallet()
        sender = Wallet()
        recipient = Wallet()

        # Create transaction without balance
        tx = Transaction(sender.address, recipient.address, 100.0, 0.24)
        tx.public_key = sender.public_key
        tx.sign_transaction(sender.private_key)
        bc.add_transaction(tx)

        # Mine block
        bc.mine_pending_transactions(miner.address)

        # Invalid transaction should not be included
        assert bc.get_balance(recipient.address) == 0

    def test_multiple_senders_one_block(self):
        """Test multiple senders in one block"""
        bc = Blockchain()
        miner = Wallet()
        senders = [Wallet() for _ in range(3)]
        recipient = Wallet()

        # Give all senders balance
        for sender in senders:
            bc.mine_pending_transactions(sender.address)

        # Create transactions from all senders
        for sender in senders:
            tx = Transaction(sender.address, recipient.address, 2.0, 0.1)
            tx.public_key = sender.public_key
            tx.sign_transaction(sender.private_key)
            bc.add_transaction(tx)

        # Mine block
        bc.mine_pending_transactions(miner.address)

        # Recipient should receive all amounts
        assert bc.get_balance(recipient.address) == 6.0

    def test_chain_transaction_flow(self):
        """Test transaction flow through chain"""
        bc = Blockchain()
        miner = Wallet()
        wallet1 = Wallet()
        wallet2 = Wallet()
        wallet3 = Wallet()

        # Initial mining
        bc.mine_pending_transactions(wallet1.address)

        # wallet1 -> wallet2
        tx1 = Transaction(wallet1.address, wallet2.address, 5.0, 0.1)
        tx1.public_key = wallet1.public_key
        tx1.sign_transaction(wallet1.private_key)
        bc.add_transaction(tx1)
        bc.mine_pending_transactions(miner.address)

        # wallet2 -> wallet3
        tx2 = Transaction(wallet2.address, wallet3.address, 3.0, 0.1)
        tx2.public_key = wallet2.public_key
        tx2.sign_transaction(wallet2.private_key)
        bc.add_transaction(tx2)
        bc.mine_pending_transactions(miner.address)

        # Verify final balances
        # With the new UTXO tracking audit, wallet2's original 5 XAI is consumed, so balance resets
        assert bc.get_balance(wallet2.address) == 1.9  # 5 - 3 - 0.1 fee
        assert bc.get_balance(wallet3.address) == 3.0


class TestMiningValidation:
    """Test mining validation"""

    def test_valid_mined_block(self):
        """Test mined blocks are valid"""
        bc = Blockchain()
        miner = Wallet()

        block = bc.mine_pending_transactions(miner.address)

        # Block should meet difficulty
        assert block.hash.startswith("0" * bc.difficulty)

        # Chain should be valid
        assert bc.validate_chain()

    def test_block_linking_integrity(self):
        """Test blocks maintain chain integrity"""
        bc = Blockchain()
        miner = Wallet()

        blocks = []
        for _ in range(5):
            block = bc.mine_pending_transactions(miner.address)
            blocks.append(block)

        # Verify linking
        for i in range(1, len(blocks)):
            assert blocks[i].previous_hash == blocks[i - 1].hash

    def test_utxo_consistency(self):
        """Test UTXO set remains consistent"""
        bc = Blockchain()
        miner = Wallet()
        sender = Wallet()
        recipient = Wallet()

        # Give sender balance
        bc.mine_pending_transactions(sender.address)
        initial_balance = bc.get_balance(sender.address)

        # Send transaction
        tx = Transaction(sender.address, recipient.address, 5.0, 0.24)
        tx.public_key = sender.public_key
        tx.sign_transaction(sender.private_key)
        bc.add_transaction(tx)
        bc.mine_pending_transactions(miner.address)

        # Verify UTXO consistency
        sender_balance = bc.get_balance(sender.address)
        recipient_balance = bc.get_balance(recipient.address)

        assert recipient_balance == 5.0
        assert sender_balance == initial_balance - 5.0 - 0.24


class TestMiningPerformance:
    """Test mining performance characteristics"""

    def test_mining_time_reasonable(self):
        """Test mining completes in reasonable time"""
        bc = Blockchain()
        miner = Wallet()

        start_time = time.time()
        bc.mine_pending_transactions(miner.address)
        mining_time = time.time() - start_time

        # Mining should complete within 30 seconds with reasonable difficulty
        assert mining_time < 30

    def test_difficulty_affects_time(self):
        """Test difficulty affects mining time"""
        bc1 = Blockchain()
        bc1.difficulty = 2

        bc2 = Blockchain()
        bc2.difficulty = 3

        miner = Wallet()

        start1 = time.time()
        bc1.mine_pending_transactions(miner.address)
        time1 = time.time() - start1

        start2 = time.time()
        bc2.mine_pending_transactions(miner.address)
        time2 = time.time() - start2

        # Higher difficulty should generally take longer
        # (not guaranteed due to randomness, but usually true)
        assert time2 >= time1 * 0.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
