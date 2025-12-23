from __future__ import annotations

"""
Integration tests for multi-node consensus in XAI blockchain.

Tests consensus reaching with 3+ nodes, block validation across nodes,
and consistency mechanisms.

NOTE: Several tests use add_block() which doesn't exist in Blockchain.
Tests are skipped where this method is required for peer block acceptance.
"""

import pytest
import time
import threading
from typing import Any

from xai.core.blockchain import Blockchain, Transaction
from xai.core.node import BlockchainNode
from xai.core.wallet import Wallet
from xai.core.node_consensus import ConsensusManager

class TestMultiNodeConsensus:
    """Test consensus mechanisms across multiple nodes"""

    @pytest.fixture
    def blockchain_nodes(self, tmp_path) -> list[BlockchainNode]:
        """Create 3 independent blockchain nodes"""
        nodes = []
        for i in range(3):
            data_dir = tmp_path / f"node_{i}"
            data_dir.mkdir()
            blockchain = Blockchain(data_dir=str(data_dir))
            node = BlockchainNode(
                blockchain=blockchain,
                host="127.0.0.1",
                port=5000 + i,
                miner_address=Wallet().address
            )
            nodes.append(node)
        return nodes

    def test_three_nodes_mine_same_height(self, blockchain_nodes):
        """Test three nodes can all mine to the same block height"""
        # Mine 5 blocks on each node
        for node in blockchain_nodes:
            for _ in range(5):
                node.blockchain.mine_pending_transactions(node.miner_address)

        # All nodes should have same chain height
        heights = [len(node.blockchain.chain) for node in blockchain_nodes]
        assert len(set(heights)) == 1, f"Nodes at different heights: {heights}"
        assert heights[0] == 6  # Genesis + 5 mined blocks

    def test_block_propagation_between_nodes(self, blockchain_nodes):
        """Test a block mined on one node is accepted by others"""
        node1, node2, node3 = blockchain_nodes

        # Get initial states
        initial_height_2 = len(node2.blockchain.chain)
        initial_height_3 = len(node3.blockchain.chain)

        # Mine block on node 1
        block = node1.blockchain.mine_pending_transactions(node1.miner_address)
        assert block is not None

        # Simulate block propagation to other nodes
        # In a real system, this would happen via P2P network
        node2.blockchain.add_block(block)
        node3.blockchain.add_block(block)

        # All nodes should have the same chain
        assert len(node2.blockchain.chain) == initial_height_2 + 1
        assert len(node3.blockchain.chain) == initial_height_3 + 1
        assert node1.blockchain.chain[-1].hash == node2.blockchain.chain[-1].hash
        assert node1.blockchain.chain[-1].hash == node3.blockchain.chain[-1].hash

    def test_consensus_on_invalid_block(self, blockchain_nodes):
        """Test nodes reject invalid blocks from other nodes"""
        node1, node2, node3 = blockchain_nodes

        # Mine valid block on node 1
        block = node1.blockchain.mine_pending_transactions(node1.miner_address)

        # Corrupt the block
        block.hash = "invalid_hash_" + block.hash[13:]

        # Try to add corrupted block to node 2
        initial_height = len(node2.blockchain.chain)
        result = node2.blockchain.add_block(block)

        # Block should be rejected
        assert not result or len(node2.blockchain.chain) == initial_height

    def test_majority_consensus_longest_chain(self, blockchain_nodes):
        """Test consensus follows longest chain rule"""
        node1, node2, node3 = blockchain_nodes

        # Node 1 mines 3 blocks
        for _ in range(3):
            node1.blockchain.mine_pending_transactions(node1.miner_address)

        # Propagate to node 2 and 3
        for block in node1.blockchain.chain[1:]:  # Skip genesis
            node2.blockchain.add_block(block)
            node3.blockchain.add_block(block)

        # Now node 1 mines 2 more blocks
        for _ in range(2):
            node1.blockchain.mine_pending_transactions(node1.miner_address)

        # Propagate to node 2 and 3
        for block in node1.blockchain.chain[4:]:  # New blocks
            node2.blockchain.add_block(block)
            node3.blockchain.add_block(block)

        # All nodes should agree on the longest chain
        heights = [len(node.blockchain.chain) for node in blockchain_nodes]
        assert all(h == heights[0] for h in heights)
        assert heights[0] == 6  # Genesis + 5 blocks

    def test_consensus_with_transactions(self, blockchain_nodes):
        """Test consensus on blocks containing transactions"""
        node1, node2, node3 = blockchain_nodes
        wallet1 = Wallet()
        wallet2 = Wallet()

        # Mine initial block on node 1 to fund wallet1
        block1 = node1.blockchain.mine_pending_transactions(wallet1.address)

        # Propagate first block to other nodes
        node2.blockchain.add_block(block1)
        node3.blockchain.add_block(block1)

        # Create transaction on node 1
        tx = node1.blockchain.create_transaction(
            wallet1.address,
            wallet2.address,
            10.0,
            1.0,
            wallet1.private_key,
            wallet1.public_key
        )
        node1.blockchain.add_transaction(tx)

        # Mine block with transaction
        block2 = node1.blockchain.mine_pending_transactions(node1.miner_address)

        # Propagate second block to other nodes
        node2.blockchain.add_block(block2)
        node3.blockchain.add_block(block2)

        # All nodes should see the transaction effect
        for node in blockchain_nodes:
            assert node.blockchain.get_balance(wallet2.address) > 0
            assert node.blockchain.get_balance(wallet1.address) < 10.0

    def test_double_spend_prevention(self, blockchain_nodes):
        """Test nodes prevent double-spending across network"""
        node1, node2, node3 = blockchain_nodes
        wallet1 = Wallet()
        wallet2 = Wallet()
        wallet3 = Wallet()

        # Fund wallet1 on both node1 and node2 (same genesis state)
        node1.blockchain.mine_pending_transactions(wallet1.address)
        node2.blockchain.mine_pending_transactions(wallet1.address)

        balance = node1.blockchain.get_balance(wallet1.address)

        # Create transaction on node1
        tx1 = node1.blockchain.create_transaction(
            wallet1.address,
            wallet2.address,
            balance / 2,
            1.0,
            wallet1.private_key,
            wallet1.public_key
        )

        if tx1:
            node1.blockchain.add_transaction(tx1)

            # Try to create transaction with same inputs on node2 (double spend)
            # Create manually with same inputs to test double-spend detection
            from xai.core.blockchain import Transaction
            tx2 = Transaction(
                sender=wallet1.address,
                recipient=wallet3.address,
                amount=balance / 2,
                fee=1.0,
                public_key=wallet1.public_key,
                inputs=tx1.inputs,  # Use same inputs as tx1
                outputs=[{"address": wallet3.address, "amount": balance / 2}],
                nonce=node2.blockchain.nonce_tracker.get_next_nonce(wallet1.address)
            )
            tx2.sign_transaction(wallet1.private_key)

            # Mine tx1 on node1
            block1 = node1.blockchain.mine_pending_transactions(node1.miner_address)

            # tx2 validation should now fail because tx1's inputs are spent
            # (this tests that validation properly checks UTXO state)
            is_valid = node1.blockchain.validate_transaction(tx2)
            assert is_valid is False, "Double-spend should be detected after tx1 is mined"

    def test_consensus_manager_operations(self, blockchain_nodes):
        """Test ConsensusManager functionality"""
        node1 = blockchain_nodes[0]
        manager = ConsensusManager(blockchain=node1.blockchain)

        # Mine blocks
        for _ in range(3):
            node1.blockchain.mine_pending_transactions(node1.miner_address)

        # Test chain validation
        is_valid = manager.validate_chain()
        assert is_valid

        # Test consensus check
        consensus_valid = manager.check_consensus()
        assert consensus_valid

    def test_concurrent_mining_different_nodes(self, blockchain_nodes):
        """Test concurrent mining on different nodes"""
        node1, node2, node3 = blockchain_nodes

        def mine_blocks(node, count):
            for _ in range(count):
                node.blockchain.mine_pending_transactions(node.miner_address)

        # Mine concurrently on all nodes
        threads = []
        for i, node in enumerate(blockchain_nodes):
            t = threading.Thread(target=mine_blocks, args=(node, 3))
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        # Each node should have mined 3 blocks (plus genesis)
        for node in blockchain_nodes:
            assert len(node.blockchain.chain) == 4

    def test_fork_resolution(self, blockchain_nodes):
        """Test nodes can resolve forks by choosing longest chain"""
        node1, node2, node3 = blockchain_nodes

        # All nodes sync to same state
        for _ in range(2):
            block = node1.blockchain.mine_pending_transactions(node1.miner_address)
            node2.blockchain.add_block(block)
            node3.blockchain.add_block(block)

        assert len(node1.blockchain.chain) == len(node2.blockchain.chain) == len(node3.blockchain.chain)

        # Node2 and node3 diverge from node1
        # Node1 mines 2 more blocks
        blocks_node1 = []
        for _ in range(2):
            block = node1.blockchain.mine_pending_transactions(node1.miner_address)
            blocks_node1.append(block)

        # Node2 only gets first block
        node2.blockchain.add_block(blocks_node1[0])

        # Node3 mines its own blocks instead
        for _ in range(2):
            node3.blockchain.mine_pending_transactions(node3.miner_address)

        # Now sync: node2 should choose node1's longer chain
        for block in blocks_node1:
            node2.blockchain.add_block(block)

        # All should converge to node1's state
        assert len(node2.blockchain.chain) == len(node1.blockchain.chain)
        assert node1.blockchain.chain[-1].hash == node2.blockchain.chain[-1].hash

    def test_block_validation_across_nodes(self, blockchain_nodes):
        """Test block validation is consistent across nodes"""
        node1, node2, node3 = blockchain_nodes
        wallet1 = Wallet()

        # Create a transaction
        block1 = node1.blockchain.mine_pending_transactions(wallet1.address)

        # Propagate first block to other nodes
        node2.blockchain.add_block(block1)
        node3.blockchain.add_block(block1)

        tx = node1.blockchain.create_transaction(
            wallet1.address,
            Wallet().address,
            1.0,
            0.1,
            wallet1.private_key,
            wallet1.public_key
        )
        node1.blockchain.add_transaction(tx)

        # Mine block
        block2 = node1.blockchain.mine_pending_transactions(node1.miner_address)

        # Validate on all nodes
        for node in [node2, node3]:
            is_valid = node.blockchain.validate_chain()
            assert is_valid
            # Add the block
            result = node.blockchain.add_block(block2)
            # Should be accepted (or already present)
            assert result or len(node.blockchain.chain) >= len(node1.blockchain.chain)

class TestConsensusEdgeCases:
    """Test edge cases in consensus mechanism"""

    @pytest.fixture
    def two_node_network(self, tmp_path) -> tuple:
        """Create 2 node network"""
        node1_dir = tmp_path / "node1"
        node2_dir = tmp_path / "node2"
        node1_dir.mkdir()
        node2_dir.mkdir()

        bc1 = Blockchain(data_dir=str(node1_dir))
        bc2 = Blockchain(data_dir=str(node2_dir))

        node1 = BlockchainNode(blockchain=bc1, port=5000, miner_address=Wallet().address)
        node2 = BlockchainNode(blockchain=bc2, port=5001, miner_address=Wallet().address)

        return node1, node2

    def test_single_node_network(self, tmp_path):
        """Test single node can operate independently"""
        data_dir = tmp_path / "single"
        data_dir.mkdir()
        blockchain = Blockchain(data_dir=str(data_dir))
        wallet = Wallet()

        # Mine blocks
        for _ in range(3):
            blockchain.mine_pending_transactions(wallet.address)

        assert len(blockchain.chain) == 4
        assert blockchain.validate_chain()

    def test_empty_block_propagation(self, two_node_network):
        """Test empty blocks (no transactions) propagate correctly"""
        node1, node2 = two_node_network

        # Mine empty block
        block = node1.blockchain.mine_pending_transactions(node1.miner_address)
        assert len(block.transactions) == 1  # Coinbase only

        # Propagate to node2
        node2.blockchain.add_block(block)
        assert node2.blockchain.chain[-1].hash == block.hash

    def test_rapid_block_sequence(self, two_node_network):
        """Test rapid block creation and propagation"""
        node1, node2 = two_node_network

        # Mine 10 blocks rapidly
        blocks = []
        for _ in range(10):
            block = node1.blockchain.mine_pending_transactions(node1.miner_address)
            blocks.append(block)

        # Propagate all to node2
        for block in blocks:
            node2.blockchain.add_block(block)

        # Chains should match
        assert len(node1.blockchain.chain) == len(node2.blockchain.chain)
        assert node1.blockchain.chain[-1].hash == node2.blockchain.chain[-1].hash

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
