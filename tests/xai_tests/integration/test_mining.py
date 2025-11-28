"""
Integration tests for XAI Mining workflow

Tests complete mining workflow including transactions, rewards, and blockchain state
"""

import pytest
import sys
import os
import time

# Add core directory to path

from xai.core.blockchain import Blockchain, Transaction
from xai.core.wallet import Wallet


class TestMiningWorkflow:
    """Test complete mining workflow"""

    def test_mine_empty_block(self, tmp_path):
        """Test mining block with no transactions"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        initial_height = len(bc.chain)
        block = bc.mine_pending_transactions(wallet.address)

        assert len(bc.chain) == initial_height + 1
        assert bc.validate_chain()
        assert bc.get_balance(wallet.address) > 0

    def test_mine_block_with_transactions(self, tmp_path):
        """Test mining block with pending transactions"""
        bc = Blockchain(data_dir=str(tmp_path))
        miner = Wallet()
        sender = Wallet()
        recipient = Wallet()

        # Give sender some balance
        bc.mine_pending_transactions(sender.address)

        # Create transaction using blockchain helper
        tx = bc.create_transaction(
            sender.address, recipient.address, 5.0, 0.24, sender.private_key, sender.public_key
        )
        bc.add_transaction(tx)

        # Mine block
        initial_height = len(bc.chain)
        block = bc.mine_pending_transactions(miner.address)

        assert len(bc.chain) == initial_height + 1
        assert bc.get_balance(recipient.address) > 0
        assert bc.validate_chain()

    def test_mining_reward_distribution(self, tmp_path):
        """Test mining rewards are correctly distributed"""
        bc = Blockchain(data_dir=str(tmp_path))
        miner = Wallet()

        # Mine multiple blocks
        rewards = []
        for i in range(3):
            balance_before = bc.get_balance(miner.address)
            bc.mine_pending_transactions(miner.address)
            balance_after = bc.get_balance(miner.address)

            reward = balance_after - balance_before
            rewards.append(reward)

        # Rewards should be at least the base reward (may include varying streak bonuses)
        base_reward = bc.get_block_reward(1)
        assert all(r >= base_reward for r in rewards)
        assert all(r <= base_reward * 1.20 for r in rewards)  # Max 20% bonus

    def test_transaction_fees_to_miner(self, tmp_path):
        """Test transaction fees go to miner"""
        bc = Blockchain(data_dir=str(tmp_path))
        miner = Wallet()
        sender = Wallet()
        recipient = Wallet()

        # Give sender balance
        bc.mine_pending_transactions(sender.address)

        # Create transaction with fee
        tx = bc.create_transaction(
            sender.address, recipient.address, 5.0, 0.5, sender.private_key, sender.public_key
        )
        bc.add_transaction(tx)

        # Mine block
        miner_balance_before = bc.get_balance(miner.address)
        bc.mine_pending_transactions(miner.address)
        miner_balance_after = bc.get_balance(miner.address)

        # Miner should receive block reward + fees (may include streak bonus)
        base_expected = bc.get_block_reward(len(bc.chain) - 1) + 0.5
        actual_reward = miner_balance_after - miner_balance_before

        # Actual should be at least base + fees, may include bonus (up to 20%)
        assert actual_reward >= base_expected
        assert actual_reward <= base_expected * 1.20

    def test_multiple_transactions_in_block(self, tmp_path):
        """Test mining block with multiple transactions"""
        bc = Blockchain(data_dir=str(tmp_path))
        miner = Wallet()
        sender = Wallet()
        recipients = [Wallet() for _ in range(3)]

        # Give sender balance
        bc.mine_pending_transactions(sender.address)
        bc.mine_pending_transactions(sender.address)
        bc.mine_pending_transactions(sender.address)

        # Create multiple transactions
        for recipient in recipients:
            tx = bc.create_transaction(
                sender.address, recipient.address, 1.0, 0.1, sender.private_key, sender.public_key
            )
            bc.add_transaction(tx)

        # Mine block
        block = bc.mine_pending_transactions(miner.address)

        # All recipients should have balance
        for recipient in recipients:
            assert bc.get_balance(recipient.address) == 1.0

    def test_consecutive_mining(self, tmp_path):
        """Test consecutive block mining"""
        bc = Blockchain(data_dir=str(tmp_path))
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

    def test_initial_reward_correct(self, tmp_path):
        """Test initial mining reward (base reward is 12.0, may include streak bonus)"""
        bc = Blockchain(data_dir=str(tmp_path))
        miner = Wallet()

        initial_balance = bc.get_balance(miner.address)
        bc.mine_pending_transactions(miner.address)
        new_balance = bc.get_balance(miner.address)

        reward = new_balance - initial_balance
        base_reward = bc.get_block_reward(1)  # Block 1 (genesis is 0)

        # Reward should be at least the base reward, may include streak bonus (up to 20%)
        assert reward >= base_reward
        assert reward <= base_reward * 1.20

    def test_reward_consistency(self, tmp_path):
        """Test rewards are consistent at same height"""
        bc = Blockchain(data_dir=str(tmp_path))
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

    def test_reward_halving_integration(self, tmp_path):
        """Test reward halving at correct intervals"""
        bc = Blockchain(data_dir=str(tmp_path))
        miner = Wallet()

        # Test reward at block 0
        reward_0 = bc.get_block_reward(0)
        assert reward_0 == 12.0

        # Test reward after halving
        reward_halved = bc.get_block_reward(262800)
        assert reward_halved == 6.0

    def test_cumulative_rewards(self, tmp_path):
        """Test cumulative mining rewards"""
        bc = Blockchain(data_dir=str(tmp_path))
        miner = Wallet()

        # Mine 5 blocks
        for _ in range(5):
            bc.mine_pending_transactions(miner.address)

        total_balance = bc.get_balance(miner.address)
        expected_total = 12.0 * 5

        # Account for streak bonuses
        assert total_balance >= expected_total
        assert total_balance <= expected_total * 1.20  # Max 20% bonus


class TestMiningWithTransactions:
    """Test mining with various transaction scenarios"""

    def test_transaction_confirmation(self, tmp_path):
        """Test transactions get confirmed in blocks"""
        bc = Blockchain(data_dir=str(tmp_path))
        miner = Wallet()
        sender = Wallet()
        recipient = Wallet()

        # Give sender balance
        bc.mine_pending_transactions(sender.address)

        # Create transaction
        tx = bc.create_transaction(
            sender.address, recipient.address, 5.0, 0.24, sender.private_key, sender.public_key
        )
        bc.add_transaction(tx)

        # Transaction should be pending
        assert len(bc.pending_transactions) > 0

        # Mine block
        bc.mine_pending_transactions(miner.address)

        # Transaction should be confirmed
        assert len(bc.pending_transactions) == 0
        assert bc.get_balance(recipient.address) == 5.0

    def test_invalid_transaction_rejection(self, tmp_path):
        """Test invalid transactions are not included in blocks"""
        bc = Blockchain(data_dir=str(tmp_path))
        miner = Wallet()
        sender = Wallet()
        recipient = Wallet()

        # Create transaction without balance (will return None)
        tx = bc.create_transaction(
            sender.address, recipient.address, 100.0, 0.24, sender.private_key, sender.public_key
        )

        # Transaction should be None (insufficient funds)
        assert tx is None

        # Mine block
        bc.mine_pending_transactions(miner.address)

        # Recipient should have no balance
        assert bc.get_balance(recipient.address) == 0

    def test_multiple_senders_one_block(self, tmp_path):
        """Test multiple senders in one block"""
        bc = Blockchain(data_dir=str(tmp_path))
        miner = Wallet()
        senders = [Wallet() for _ in range(3)]
        recipient = Wallet()

        # Give all senders balance
        for sender in senders:
            bc.mine_pending_transactions(sender.address)

        # Create transactions from all senders
        for sender in senders:
            tx = bc.create_transaction(
                sender.address, recipient.address, 2.0, 0.1, sender.private_key, sender.public_key
            )
            bc.add_transaction(tx)

        # Mine block
        bc.mine_pending_transactions(miner.address)

        # Recipient should receive all amounts
        assert bc.get_balance(recipient.address) == 6.0

    def test_chain_transaction_flow(self, tmp_path):
        """Test transaction flow through chain"""
        bc = Blockchain(data_dir=str(tmp_path))
        miner = Wallet()
        wallet1 = Wallet()
        wallet2 = Wallet()
        wallet3 = Wallet()

        # Initial mining
        bc.mine_pending_transactions(wallet1.address)

        # wallet1 -> wallet2
        tx1 = bc.create_transaction(
            wallet1.address, wallet2.address, 5.0, 0.1, wallet1.private_key, wallet1.public_key
        )
        bc.add_transaction(tx1)
        bc.mine_pending_transactions(miner.address)

        # wallet2 -> wallet3
        tx2 = bc.create_transaction(
            wallet2.address, wallet3.address, 3.0, 0.1, wallet2.private_key, wallet2.public_key
        )
        bc.add_transaction(tx2)
        bc.mine_pending_transactions(miner.address)

        # Verify final balances
        # With the new UTXO tracking audit, wallet2's original 5 XAI is consumed, so balance resets
        assert bc.get_balance(wallet2.address) == 1.9  # 5 - 3 - 0.1 fee
        assert bc.get_balance(wallet3.address) == 3.0


class TestMiningValidation:
    """Test mining validation"""

    def test_valid_mined_block(self, tmp_path):
        """Test mined blocks are valid"""
        bc = Blockchain(data_dir=str(tmp_path))
        miner = Wallet()

        block = bc.mine_pending_transactions(miner.address)

        # Block should meet difficulty
        assert block.hash.startswith("0" * bc.difficulty)

        # Chain should be valid
        assert bc.validate_chain()

    def test_block_linking_integrity(self, tmp_path):
        """Test blocks maintain chain integrity"""
        bc = Blockchain(data_dir=str(tmp_path))
        miner = Wallet()

        blocks = []
        for _ in range(5):
            block = bc.mine_pending_transactions(miner.address)
            blocks.append(block)

        # Verify linking
        for i in range(1, len(blocks)):
            assert blocks[i].previous_hash == blocks[i - 1].hash

    def test_utxo_consistency(self, tmp_path):
        """Test UTXO set remains consistent"""
        bc = Blockchain(data_dir=str(tmp_path))
        miner = Wallet()
        sender = Wallet()
        recipient = Wallet()

        # Give sender balance
        bc.mine_pending_transactions(sender.address)
        initial_balance = bc.get_balance(sender.address)

        # Send transaction
        tx = bc.create_transaction(
            sender.address, recipient.address, 5.0, 0.24, sender.private_key, sender.public_key
        )
        bc.add_transaction(tx)
        bc.mine_pending_transactions(miner.address)

        # Verify UTXO consistency
        sender_balance = bc.get_balance(sender.address)
        recipient_balance = bc.get_balance(recipient.address)

        assert recipient_balance == 5.0
        assert sender_balance == initial_balance - 5.0 - 0.24


class TestMiningPerformance:
    """Test mining performance characteristics"""

    def test_mining_time_reasonable(self, tmp_path):
        """Test mining completes in reasonable time"""
        bc = Blockchain(data_dir=str(tmp_path))
        miner = Wallet()

        start_time = time.time()
        bc.mine_pending_transactions(miner.address)
        mining_time = time.time() - start_time

        # Mining should complete within 30 seconds with reasonable difficulty
        assert mining_time < 30

    def test_difficulty_affects_time(self, tmp_path):
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
