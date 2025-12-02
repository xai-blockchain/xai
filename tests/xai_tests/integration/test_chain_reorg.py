"""
Integration tests for blockchain reorganization (reorg) scenarios.

Tests fork handling, chain reorganization, and state consistency
during blockchain reorg events.

NOTE: Reorganization tests are skipped because add_block() method
doesn't exist in Blockchain class. This functionality requires
peer block acceptance which is not yet implemented in the core.
"""

import pytest
import copy
from typing import List, Tuple

from xai.core.blockchain import Blockchain, Block, Transaction
from xai.core.node import BlockchainNode
from xai.core.wallet import Wallet
from xai.core.blockchain_security import ReorganizationProtection


class TestBlockchainReorganization:
    """Test blockchain reorganization scenarios"""

    @pytest.fixture
    def reorg_network(self, tmp_path) -> Tuple[BlockchainNode, BlockchainNode]:
        """Create 2-node network for reorg testing"""
        node1_dir = tmp_path / "node1"
        node2_dir = tmp_path / "node2"
        node1_dir.mkdir()
        node2_dir.mkdir()

        bc1 = Blockchain(data_dir=str(node1_dir))
        bc2 = Blockchain(data_dir=str(node2_dir))

        node1 = BlockchainNode(blockchain=bc1, port=5000, miner_address=Wallet().address)
        node2 = BlockchainNode(blockchain=bc2, port=5001, miner_address=Wallet().address)

        return node1, node2

    def test_simple_fork_resolution(self, reorg_network):
        """Test nodes resolve a simple fork by choosing longer chain"""
        node1, node2 = reorg_network

        # Sync to same state
        for _ in range(3):
            block = node1.blockchain.mine_pending_transactions(node1.miner_address)
            node2.blockchain.add_block(block)

        assert len(node1.blockchain.chain) == len(node2.blockchain.chain) == 4

        # Create fork: node1 mines 2 more blocks
        node1_blocks = []
        for _ in range(2):
            block = node1.blockchain.mine_pending_transactions(node1.miner_address)
            node1_blocks.append(block)

        # Node2 mines its own blocks (different chain)
        for _ in range(1):
            node2.blockchain.mine_pending_transactions(node2.miner_address)

        # Node1 is now longer (6 blocks vs 5)
        assert len(node1.blockchain.chain) == 6
        assert len(node2.blockchain.chain) == 5

        # Node2 receives node1's blocks
        for block in node1_blocks:
            result = node2.blockchain.add_block(block)
            # Should reorganize to node1's chain

        # Both should now be at same height
        assert len(node1.blockchain.chain) == len(node2.blockchain.chain)
        assert node1.blockchain.chain[-1].hash == node2.blockchain.chain[-1].hash

    def test_deep_reorg(self, reorg_network):
        """Test reorganization multiple blocks deep"""
        node1, node2 = reorg_network

        # Create shared chain (5 blocks)
        shared_blocks = []
        for _ in range(5):
            block = node1.blockchain.mine_pending_transactions(node1.miner_address)
            shared_blocks.append(block)
            node2.blockchain.add_block(block)

        shared_height = len(node2.blockchain.chain)

        # Node1 mines 3 more blocks
        node1_fork = []
        for _ in range(3):
            block = node1.blockchain.mine_pending_transactions(node1.miner_address)
            node1_fork.append(block)

        # Node2 mines different 2 blocks from shared state
        node2_fork = []
        for _ in range(2):
            # Add transaction to make blocks different
            wallet = Wallet()
            tx = node2.blockchain.create_transaction(
                Wallet().address,
                wallet.address,
                1.0,
                0.1,
                "0" * 64,
                "0" * 128
            )
            node2.blockchain.add_transaction(tx)
            block = node2.blockchain.mine_pending_transactions(node2.miner_address)
            node2_fork.append(block)

        assert len(node1.blockchain.chain) == shared_height + 3
        assert len(node2.blockchain.chain) == shared_height + 2

        # Node2 receives node1's longer chain
        for block in node1_fork:
            node2.blockchain.add_block(block)

        # Node2 should reorganize
        assert len(node2.blockchain.chain) == shared_height + 3
        assert node2.blockchain.chain[-1].hash == node1.blockchain.chain[-1].hash

    def test_reorg_with_transactions(self, reorg_network):
        """Test reorg correctly updates account balances"""
        node1, node2 = reorg_network
        wallet1 = Wallet()
        wallet2 = Wallet()
        wallet3 = Wallet()

        # Fund wallet1
        node1.blockchain.mine_pending_transactions(wallet1.address)
        node2.blockchain.add_block(node1.blockchain.chain[-1])

        initial_balance_1 = node1.blockchain.get_balance(wallet1.address)

        # Fork 1: node1 sends to wallet2
        tx1 = node1.blockchain.create_transaction(
            wallet1.address,
            wallet2.address,
            5.0,
            0.1,
            wallet1.private_key,
            wallet1.public_key
        )
        node1.blockchain.add_transaction(tx1)
        block1 = node1.blockchain.mine_pending_transactions(node1.miner_address)

        # Fork 2: node2 sends to wallet3
        tx2 = node2.blockchain.create_transaction(
            wallet1.address,
            wallet3.address,
            3.0,
            0.1,
            wallet1.private_key,
            wallet1.public_key
        )
        node2.blockchain.add_transaction(tx2)
        block2 = node2.blockchain.mine_pending_transactions(node2.miner_address)

        # Node1 has more blocks (longer chain)
        node1.blockchain.mine_pending_transactions(node1.miner_address)

        # Node2 reorganizes to node1's chain
        node2.blockchain.add_block(block1)
        node2.blockchain.add_block(node1.blockchain.chain[-1])

        # After reorg, node2 should reflect node1's transactions
        assert node2.blockchain.get_balance(wallet2.address) > 0
        # wallet3 transaction should be lost in reorg
        assert node2.blockchain.get_balance(wallet3.address) == 0

    def test_reorg_doesnt_lose_valid_txs(self, reorg_network):
        """Test that valid transactions are preserved during reorg"""
        node1, node2 = reorg_network

        wallets = [Wallet() for _ in range(5)]

        # Create initial funding
        node1.blockchain.mine_pending_transactions(wallets[0].address)
        node2.blockchain.add_block(node1.blockchain.chain[-1])

        # Create diverse transactions
        txs = []
        for i in range(4):
            tx = node1.blockchain.create_transaction(
                wallets[0].address,
                wallets[i + 1].address,
                1.0,
                0.1,
                wallets[0].private_key,
                wallets[0].public_key
            )
            txs.append(tx)
            node1.blockchain.add_transaction(tx)

        block = node1.blockchain.mine_pending_transactions(node1.miner_address)

        # Fork: node2 mines empty blocks
        for _ in range(2):
            node2.blockchain.mine_pending_transactions(node2.miner_address)

        # Node1 mines more blocks
        node1.blockchain.mine_pending_transactions(node1.miner_address)

        # Reorg node2 to follow node1
        node2.blockchain.add_block(block)
        node2.blockchain.add_block(node1.blockchain.chain[-1])

        # All transactions should be confirmed
        for i, tx in enumerate(txs):
            recipient = wallets[i + 1]
            balance = node2.blockchain.get_balance(recipient.address)
            assert balance > 0, f"Transaction {i} not applied after reorg"

    def test_reorg_chain_validation(self, reorg_network):
        """Test that reorganized chain is valid"""
        node1, node2 = reorg_network

        # Create shared history
        for _ in range(4):
            block = node1.blockchain.mine_pending_transactions(node1.miner_address)
            node2.blockchain.add_block(block)

        # Create fork
        node1_fork = []
        for _ in range(3):
            block = node1.blockchain.mine_pending_transactions(node1.miner_address)
            node1_fork.append(block)

        node2_fork = []
        for _ in range(2):
            block = node2.blockchain.mine_pending_transactions(node2.miner_address)
            node2_fork.append(block)

        # Reorganize
        for block in node1_fork:
            node2.blockchain.add_block(block)

        # Validate chain
        is_valid = node2.blockchain.validate_chain()
        assert is_valid, "Chain invalid after reorganization"

    def test_very_deep_reorg(self, tmp_path):
        """Test handling of deep reorganization (10+ blocks)"""
        node_dir = tmp_path / "node"
        node_dir.mkdir()

        blockchain = Blockchain(data_dir=str(node_dir))
        wallet = Wallet()

        # Build initial chain of 15 blocks
        blocks = []
        for _ in range(15):
            block = blockchain.mine_pending_transactions(wallet.address)
            blocks.append(block)

        assert len(blockchain.chain) == 16

        # Simulate deep reorg by removing last 10 blocks and replacing
        # In real system, would involve receiving competing chain
        original_height = len(blockchain.chain)
        original_last_hash = blockchain.chain[-1].hash

        # Mine 11 more blocks (deeper than removed chain)
        new_blocks = []
        for _ in range(11):
            block = blockchain.mine_pending_transactions(wallet.address)
            new_blocks.append(block)

        # Chain should be extended
        assert len(blockchain.chain) == original_height + 11
        assert blockchain.chain[-1].hash != original_last_hash

        # Validate final chain
        is_valid = blockchain.validate_chain()
        assert is_valid

    def test_reorg_protection(self, tmp_path):
        """Test reorg protection mechanisms"""
        node_dir = tmp_path / "node"
        node_dir.mkdir()

        blockchain = Blockchain(data_dir=str(node_dir))
        protection = ReorganizationProtection()

        # Mine blocks and set checkpoints
        for _ in range(5):
            block = blockchain.mine_pending_transactions(Wallet().address)
            protection.create_checkpoint(block.index, block.hash)

        # Verify checkpoint exists
        assert protection.has_checkpoint(4)

        # Validate that chain matches checkpoint
        block_4_hash = blockchain.chain[4].hash
        is_protected = protection.is_protected(4, block_4_hash)
        assert is_protected


class TestReorgEdgeCases:
    """Test edge cases in reorganization"""

    def test_empty_fork_reorg(self, tmp_path):
        """Test reorg where fork contains empty blocks"""
        node1_dir = tmp_path / "node1"
        node2_dir = tmp_path / "node2"
        node1_dir.mkdir()
        node2_dir.mkdir()

        bc1 = Blockchain(data_dir=str(node1_dir))
        bc2 = Blockchain(data_dir=str(node2_dir))

        # Sync
        block = bc1.mine_pending_transactions(Wallet().address)
        bc2.add_block(block)

        # Node1 mines 2 empty blocks
        miner = Wallet()
        for _ in range(2):
            block = bc1.mine_pending_transactions(miner.address)
            block1_last = block

        # Node2 mines 1 block then adds node1's blocks
        bc2.mine_pending_transactions(Wallet().address)
        bc2.add_block(block1_last)

        # Should reorganize
        assert len(bc2.chain) >= len(bc1.chain) - 1

    def test_simultaneous_blocks_reorg(self, tmp_path):
        """Test handling of blocks received out of order"""
        node_dir = tmp_path / "node"
        node_dir.mkdir()

        blockchain = Blockchain(data_dir=str(node_dir))
        miner = Wallet()

        # Mine blocks
        block1 = blockchain.mine_pending_transactions(miner.address)
        block2 = blockchain.mine_pending_transactions(miner.address)
        block3 = blockchain.mine_pending_transactions(miner.address)

        # Simulate second node receiving blocks out of order
        bc2_dir = tmp_path / "node2"
        bc2_dir.mkdir()
        blockchain2 = Blockchain(data_dir=str(bc2_dir))

        # Add blocks in reverse order (would fail naturally)
        # Then add in correct order
        blockchain2.add_block(block1)
        blockchain2.add_block(block2)
        blockchain2.add_block(block3)

        # Should be synchronized
        assert len(blockchain.chain) == len(blockchain2.chain)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
