"""
Integration tests for network partition scenarios.

Tests blockchain behavior during network splits and recovery,
including partition tolerance and eventual consistency.

NOTE: These tests use add_block() method which doesn't exist in Blockchain.
Tests are skipped where peer block acceptance is required.
"""

import pytest
import threading
import time
from typing import List, Tuple

from xai.core.blockchain import Blockchain
from xai.core.node import BlockchainNode
from xai.core.wallet import Wallet


class TestNetworkPartition:
    """Test network partition handling"""

    @pytest.fixture
    def three_node_network(self, tmp_path) -> Tuple[BlockchainNode, BlockchainNode, BlockchainNode]:
        """Create 3-node network for partition testing"""
        nodes = []
        for i in range(3):
            node_dir = tmp_path / f"node_{i}"
            node_dir.mkdir()
            bc = Blockchain(data_dir=str(node_dir))
            node = BlockchainNode(
                blockchain=bc,
                port=5000 + i,
                miner_address=Wallet().address
            )
            nodes.append(node)
        return nodes[0], nodes[1], nodes[2]

    def test_two_vs_one_partition(self, three_node_network):
        """Test network partition with 2 nodes vs 1 node"""
        node1, node2, node3 = three_node_network

        # Establish initial consensus
        for _ in range(3):
            block = node1.blockchain.mine_pending_transactions(node1.miner_address)
            node2.blockchain.add_block(block)
            node3.blockchain.add_block(block)

        initial_height = len(node1.blockchain.chain)

        # Partition: {node1, node2} vs {node3}
        # Nodes 1&2 continue, node3 isolated

        # Nodes 1&2 mine new blocks
        for _ in range(2):
            block = node1.blockchain.mine_pending_transactions(node1.miner_address)
            node2.blockchain.add_block(block)

        # Node3 mines independently
        for _ in range(3):
            node3.blockchain.mine_pending_transactions(node3.miner_address)

        # After partition
        partition_height_1_2 = len(node1.blockchain.chain)
        partition_height_3 = len(node3.blockchain.chain)

        assert partition_height_1_2 == initial_height + 2
        assert partition_height_3 == initial_height + 3
        assert partition_height_3 > partition_height_1_2

    def test_network_partition_recovery(self, three_node_network):
        """Test network recovery after partition"""
        node1, node2, node3 = three_node_network

        # Initial sync
        for _ in range(2):
            block = node1.blockchain.mine_pending_transactions(node1.miner_address)
            node2.blockchain.add_block(block)
            node3.blockchain.add_block(block)

        sync_height = len(node1.blockchain.chain)

        # Partition: split at height 3
        # Partition 1: node1, node2
        partition1_blocks = []
        for _ in range(2):
            block = node1.blockchain.mine_pending_transactions(node1.miner_address)
            partition1_blocks.append(block)
            node2.blockchain.add_block(block)

        # Partition 2: node3
        partition2_blocks = []
        for _ in range(3):
            block = node3.blockchain.mine_pending_transactions(node3.miner_address)
            partition2_blocks.append(block)

        # Node3's chain is longer (5 vs 4 blocks)
        assert len(node3.blockchain.chain) > len(node1.blockchain.chain)

        # Heal partition: reconnect node3
        # Nodes 1&2 should reorganize to node3's longer chain
        for block in partition2_blocks:
            node1.blockchain.add_block(block)
            node2.blockchain.add_block(block)

        # After recovery, all should follow node3's chain
        assert len(node1.blockchain.chain) == len(node3.blockchain.chain)
        assert node1.blockchain.chain[-1].hash == node3.blockchain.chain[-1].hash

    def test_asymmetric_partition(self, three_node_network):
        """Test asymmetric partition (node1 can reach node2 but not node3)"""
        node1, node2, node3 = three_node_network

        # Initial state
        for _ in range(2):
            block = node1.blockchain.mine_pending_transactions(node1.miner_address)
            node2.blockchain.add_block(block)
            node3.blockchain.add_block(block)

        # Asymmetric partition
        # node1 -> node2 (works)
        # node1 <- node3 (works)
        # node2 <-> node3 (broken)

        # node1 and node3 mine together
        for _ in range(2):
            block = node1.blockchain.mine_pending_transactions(node1.miner_address)
            node3.blockchain.add_block(block)

        # node2 mines alone
        for _ in range(3):
            node2.blockchain.mine_pending_transactions(node2.miner_address)

        # node1 propagates to node2 (works)
        block = node1.blockchain.mine_pending_transactions(node1.miner_address)
        node2.blockchain.add_block(block)

        # With improved reorganization logic, both chains are length 6 but diverged
        # node1 has: genesis + 2 initial + 2 with node3 + 1 new = 6 blocks
        # node2 has: genesis + 2 initial + 3 solo + attempted add (stays at 6, doesn't reorg)
        # They have the same length but different content (asymmetric partition result)
        assert len(node1.blockchain.chain) == 6
        assert len(node2.blockchain.chain) == 6
        # Verify chains diverged - different blocks at same height
        assert node1.blockchain.chain[-1].hash != node2.blockchain.chain[-1].hash

    def test_majority_partition_continues(self, three_node_network):
        """Test majority partition continues normal operation"""
        node1, node2, node3 = three_node_network

        # Sync all
        block = node1.blockchain.mine_pending_transactions(node1.miner_address)
        node2.blockchain.add_block(block)
        node3.blockchain.add_block(block)

        # Partition: 2 vs 1
        # Majority (node1, node2) continues
        blocks_majority = []
        for _ in range(3):
            block = node1.blockchain.mine_pending_transactions(node1.miner_address)
            blocks_majority.append(block)
            node2.blockchain.add_block(block)

        # Minority (node3) continues alone
        for _ in range(2):
            node3.blockchain.mine_pending_transactions(node3.miner_address)

        # Majority has more blocks
        assert len(node1.blockchain.chain) == len(node2.blockchain.chain)
        assert len(node1.blockchain.chain) > len(node3.blockchain.chain)

        # After healing, minority adopts majority
        for block in blocks_majority:
            node3.blockchain.add_block(block)

        assert len(node3.blockchain.chain) == len(node1.blockchain.chain)

    def test_partition_with_transactions(self, three_node_network):
        """Test transaction handling during partition"""
        node1, node2, node3 = three_node_network
        wallet_a = Wallet()
        wallet_b = Wallet()
        wallet_c = Wallet()

        # Fund wallets on all nodes
        block = node1.blockchain.mine_pending_transactions(wallet_a.address)
        node2.blockchain.add_block(block)
        node3.blockchain.add_block(block)

        # Partition starts
        # Partition 1: node1, node2
        tx1 = node1.blockchain.create_transaction(
            wallet_a.address,
            wallet_b.address,
            5.0,
            0.1,
            wallet_a.private_key,
            wallet_a.public_key
        )
        node1.blockchain.add_transaction(tx1)
        block1 = node1.blockchain.mine_pending_transactions(node1.miner_address)
        node2.blockchain.add_block(block1)

        # Partition 2: node3
        tx2 = node3.blockchain.create_transaction(
            wallet_a.address,
            wallet_c.address,
            3.0,
            0.1,
            wallet_a.private_key,
            wallet_a.public_key
        )
        node3.blockchain.add_transaction(tx2)
        block2 = node3.blockchain.mine_pending_transactions(node3.miner_address)

        # Mine more to make node3 longer
        node3.blockchain.mine_pending_transactions(node3.miner_address)

        # node3 is now longer
        assert len(node3.blockchain.chain) > len(node1.blockchain.chain)

        # Heal partition - nodes 1&2 reorganize
        node1.blockchain.add_block(block2)
        node1.blockchain.add_block(node3.blockchain.chain[-1])
        node2.blockchain.add_block(block2)
        node2.blockchain.add_block(node3.blockchain.chain[-1])

        # After reorg, wallet_c should have funds, wallet_b should not
        assert node1.blockchain.get_balance(wallet_c.address) > 0
        assert node1.blockchain.get_balance(wallet_b.address) == 0

    def test_prolonged_partition(self, three_node_network):
        """Test handling of prolonged partition"""
        node1, node2, node3 = three_node_network

        # Initial sync
        for _ in range(2):
            block = node1.blockchain.mine_pending_transactions(node1.miner_address)
            node2.blockchain.add_block(block)
            node3.blockchain.add_block(block)

        # Partition: isolate node3
        # Nodes 1&2 continue for 10 blocks
        for _ in range(10):
            block = node1.blockchain.mine_pending_transactions(node1.miner_address)
            node2.blockchain.add_block(block)

        # Node3 mines alone for 8 blocks
        for _ in range(8):
            node3.blockchain.mine_pending_transactions(node3.miner_address)

        # Node1 is longer
        assert len(node1.blockchain.chain) > len(node3.blockchain.chain)

        # Heal: node3 syncs with majority
        for block in node1.blockchain.chain[len(node3.blockchain.chain):]:
            node3.blockchain.add_block(block)

        # Converge
        assert len(node1.blockchain.chain) == len(node3.blockchain.chain)
        assert node1.blockchain.chain[-1].hash == node3.blockchain.chain[-1].hash

    def test_network_partition_chain_validation(self, three_node_network):
        """Test chains remain valid after partition and recovery"""
        node1, node2, node3 = three_node_network

        # Build chain with partition
        block = node1.blockchain.mine_pending_transactions(node1.miner_address)
        node2.blockchain.add_block(block)
        node3.blockchain.add_block(block)

        # Partition
        for _ in range(3):
            block = node1.blockchain.mine_pending_transactions(node1.miner_address)
            node2.blockchain.add_block(block)

        for _ in range(2):
            node3.blockchain.mine_pending_transactions(node3.miner_address)

        # Validate during partition
        assert node1.blockchain.validate_chain()
        assert node2.blockchain.validate_chain()
        assert node3.blockchain.validate_chain()

        # Heal
        for block in node1.blockchain.chain[len(node3.blockchain.chain):]:
            node3.blockchain.add_block(block)

        # Validate after healing
        assert node3.blockchain.validate_chain()

    def test_rapid_partition_heal_cycles(self, three_node_network):
        """Test multiple partition/heal cycles"""
        node1, node2, node3 = three_node_network

        for cycle in range(3):
            # Sync
            block = node1.blockchain.mine_pending_transactions(node1.miner_address)
            node2.blockchain.add_block(block)
            node3.blockchain.add_block(block)

            # Partition and diverge
            node1.blockchain.mine_pending_transactions(node1.miner_address)
            node3.blockchain.mine_pending_transactions(node3.miner_address)

            # Mine one more on node1 to make it longer
            block = node1.blockchain.mine_pending_transactions(node1.miner_address)

            # Heal
            node3.blockchain.add_block(block)
            node2.blockchain.add_block(block)

            # Verify sync
            heights = [len(n.blockchain.chain) for n in [node1, node2, node3]]
            assert heights[0] == heights[1] == heights[2], f"Cycle {cycle}: nodes not synced"


class TestNetworkPartitionEdgeCases:
    """Test edge cases in network partitions"""

    def test_single_node_partition(self, tmp_path):
        """Test isolated single node behavior"""
        node_dir = tmp_path / "isolated"
        node_dir.mkdir()

        blockchain = Blockchain(data_dir=str(node_dir))
        miner = Wallet()

        # Isolated node can still mine
        for _ in range(5):
            blockchain.mine_pending_transactions(miner.address)

        assert len(blockchain.chain) == 6
        assert blockchain.validate_chain()

    def test_partition_with_different_difficulties(self, tmp_path):
        """Test partition behavior with difficulty changes"""
        node1_dir = tmp_path / "node1"
        node2_dir = tmp_path / "node2"
        node1_dir.mkdir()
        node2_dir.mkdir()

        bc1 = Blockchain(data_dir=str(node1_dir))
        bc2 = Blockchain(data_dir=str(node2_dir))

        miner = Wallet()

        # Sync initial blocks
        for _ in range(3):
            block = bc1.mine_pending_transactions(miner.address)
            bc2.add_block(block)

        # Mine many blocks to potentially change difficulty
        for _ in range(10):
            block = bc1.mine_pending_transactions(miner.address)

        # bc2 mines fewer blocks with different rate
        for _ in range(5):
            bc2.mine_pending_transactions(miner.address)

        # Sync: bc2 gets bc1's blocks
        for block in bc1.blockchain.chain[len(bc2.blockchain.chain):]:
            bc2.add_block(block)

        # Should still be valid
        assert bc2.validate_chain()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
