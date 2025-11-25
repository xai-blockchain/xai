"""
End-to-end test: User mining journey

Complete flow: Node startup -> Mining blocks -> Earning rewards -> Checking balance
"""

import pytest
import time
from xai.core.blockchain import Blockchain
from xai.core.node import BlockchainNode
from xai.core.wallet import Wallet


class TestUserJourneyMining:
    """Test complete user mining journey"""

    def test_user_starts_mining_node(self, e2e_blockchain_dir):
        """User starts a node and begins mining"""
        # User creates wallet for mining rewards
        miner_wallet = Wallet()
        assert miner_wallet.address.startswith("XAI")

        # User initializes blockchain
        blockchain = Blockchain(data_dir=e2e_blockchain_dir)
        assert len(blockchain.chain) == 1  # Genesis block

        # User starts mining
        block = blockchain.mine_pending_transactions(miner_wallet.address)
        assert block is not None
        assert block.index == 1

        # User checks balance
        balance = blockchain.get_balance(miner_wallet.address)
        assert balance > 0, "Miner should have received reward"

    def test_user_continuous_mining_session(self, e2e_blockchain_dir):
        """User mines continuously for extended session"""
        miner_wallet = Wallet()
        blockchain = Blockchain(data_dir=e2e_blockchain_dir)

        # Mine 10 blocks
        initial_balance = 0
        for i in range(10):
            block = blockchain.mine_pending_transactions(miner_wallet.address)
            assert block is not None
            assert block.index == i + 1

        # Check cumulative rewards
        final_balance = blockchain.get_balance(miner_wallet.address)
        assert final_balance > initial_balance
        assert len(blockchain.chain) == 11  # Genesis + 10

    def test_user_mining_with_pending_transactions(self, e2e_blockchain_dir):
        """User mines blocks with pending transactions"""
        miner = Wallet()
        sender = Wallet()
        recipient = Wallet()

        blockchain = Blockchain(data_dir=e2e_blockchain_dir)

        # Fund sender
        blockchain.mine_pending_transactions(sender.address)

        # Create transaction
        tx = blockchain.create_transaction(
            sender.address,
            recipient.address,
            5.0,
            0.5,
            sender.private_key,
            sender.public_key
        )
        blockchain.add_transaction(tx)

        # Mine block with transaction
        block = blockchain.mine_pending_transactions(miner.address)

        # Check results
        assert len(block.transactions) >= 2  # Coinbase + user transaction
        assert blockchain.get_balance(recipient.address) == 5.0
        assert blockchain.get_balance(miner.address) > 0  # Mining reward

    def test_user_observes_block_reward_progression(self, e2e_blockchain_dir):
        """User observes mining rewards over time"""
        miner = Wallet()
        blockchain = Blockchain(data_dir=e2e_blockchain_dir)

        rewards = []
        for _ in range(5):
            balance_before = blockchain.get_balance(miner.address)
            blockchain.mine_pending_transactions(miner.address)
            balance_after = blockchain.get_balance(miner.address)
            reward = balance_after - balance_before
            rewards.append(reward)

        # All rewards should be positive
        assert all(r > 0 for r in rewards)

    def test_user_mining_node_operations(self, e2e_blockchain_dir):
        """User performs various mining node operations"""
        miner = Wallet()
        blockchain = Blockchain(data_dir=e2e_blockchain_dir)

        # Start mining
        for _ in range(3):
            blockchain.mine_pending_transactions(miner.address)

        # Check chain validity
        assert blockchain.validate_chain()

        # Get chain statistics
        chain_height = len(blockchain.chain)
        assert chain_height == 4  # Genesis + 3

        # Get balance
        balance = blockchain.get_balance(miner.address)
        assert balance > 0

        # Get mining stats
        block_count = chain_height - 1
        reward_per_block = blockchain.get_block_reward(1)
        assert balance >= block_count * reward_per_block

    def test_user_mining_with_node_api(self, e2e_blockchain_dir):
        """User interacts with mining through node API"""
        miner_wallet = Wallet()
        blockchain = Blockchain(data_dir=e2e_blockchain_dir)
        node = BlockchainNode(
            blockchain=blockchain,
            port=5000,
            miner_address=miner_wallet.address
        )

        # Mine through blockchain (simulating API call)
        block = blockchain.mine_pending_transactions(node.miner_address)
        assert block is not None

        # Check stats through node
        balance = blockchain.get_balance(node.miner_address)
        assert balance > 0

    def test_user_long_mining_session_10_blocks(self, e2e_blockchain_dir):
        """User conducts extended mining session with 10 blocks"""
        miner = Wallet()
        blockchain = Blockchain(data_dir=e2e_blockchain_dir)

        start_time = time.time()

        # Mine 10 blocks
        for i in range(10):
            block = blockchain.mine_pending_transactions(miner.address)
            assert block is not None

        duration = time.time() - start_time

        # Verify state
        assert len(blockchain.chain) == 11
        assert blockchain.validate_chain()

        balance = blockchain.get_balance(miner.address)
        assert balance > 0

    def test_user_checks_mining_rewards_consistency(self, e2e_blockchain_dir):
        """User verifies mining reward calculations"""
        miner = Wallet()
        blockchain = Blockchain(data_dir=e2e_blockchain_dir)

        # Mine and track rewards
        total_reward = 0
        expected_reward = 0

        for block_num in range(1, 6):
            block = blockchain.mine_pending_transactions(miner.address)
            expected_reward = blockchain.get_block_reward(block_num)
            total_reward += expected_reward

        actual_balance = blockchain.get_balance(miner.address)

        # Actual balance should match expected total (may include bonuses)
        assert actual_balance >= total_reward

    def test_user_mining_multiple_wallets(self, e2e_blockchain_dir):
        """User mines to different wallet addresses"""
        miners = [Wallet() for _ in range(3)]
        blockchain = Blockchain(data_dir=e2e_blockchain_dir)

        # Mine to each wallet in rotation
        for i in range(9):
            miner = miners[i % 3]
            blockchain.mine_pending_transactions(miner.address)

        # Check that rewards distributed
        balances = [blockchain.get_balance(m.address) for m in miners]
        assert all(b > 0 for b in balances)
        # All should have similar rewards
        assert max(balances) - min(balances) <= max(balances) * 0.5

    def test_user_mining_then_transacting(self, e2e_blockchain_dir):
        """User mines rewards then spends them"""
        miner = Wallet()
        recipient = Wallet()
        blockchain = Blockchain(data_dir=e2e_blockchain_dir)

        # Mine 5 blocks
        for _ in range(5):
            blockchain.mine_pending_transactions(miner.address)

        miner_balance = blockchain.get_balance(miner.address)

        # Send some to recipient
        tx = blockchain.create_transaction(
            miner.address,
            recipient.address,
            miner_balance * 0.5,
            1.0,
            miner.private_key,
            miner.public_key
        )
        blockchain.add_transaction(tx)

        # Mine to confirm
        blockchain.mine_pending_transactions(Wallet().address)

        # Check final state
        assert blockchain.get_balance(recipient.address) > 0
        assert blockchain.get_balance(miner.address) < miner_balance


class TestMiningEdgeCases:
    """Test edge cases in mining journey"""

    def test_mining_genesis_block_only(self, e2e_blockchain_dir):
        """Test minimal mining scenario"""
        miner = Wallet()
        blockchain = Blockchain(data_dir=e2e_blockchain_dir)

        assert len(blockchain.chain) == 1
        assert blockchain.validate_chain()

    def test_mining_after_long_idle(self, e2e_blockchain_dir):
        """Test mining after simulated idle period"""
        miner = Wallet()
        blockchain = Blockchain(data_dir=e2e_blockchain_dir)

        # Mine initial block
        blockchain.mine_pending_transactions(miner.address)
        balance_after_first = blockchain.get_balance(miner.address)

        # Simulate idle
        time.sleep(0.1)

        # Resume mining
        blockchain.mine_pending_transactions(miner.address)
        balance_after_second = blockchain.get_balance(miner.address)

        # Balance should increase
        assert balance_after_second > balance_after_first

    def test_mining_with_pending_transactions_accumulation(self, e2e_blockchain_dir):
        """Test mining with accumulating pending transactions"""
        miner = Wallet()
        sender = Wallet()
        blockchain = Blockchain(data_dir=e2e_blockchain_dir)

        # Fund sender
        blockchain.mine_pending_transactions(sender.address)

        # Create multiple pending transactions
        for i in range(5):
            tx = blockchain.create_transaction(
                sender.address,
                Wallet().address,
                0.5,
                0.05,
                sender.private_key,
                sender.public_key
            )
            blockchain.add_transaction(tx)

        # Mine to clear mempool
        block = blockchain.mine_pending_transactions(miner.address)

        # All transactions should be in block
        assert len(block.transactions) >= 5

        # Mempool should be cleared
        assert len(blockchain.pending_transactions) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
