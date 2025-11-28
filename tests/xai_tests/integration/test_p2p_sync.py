"""
Integration tests for P2P sync and fork resolution.
"""

import pytest
import asyncio
from typing import List
from xai.core.node import BlockchainNode
from xai.core.blockchain import Blockchain

@pytest.fixture
async def multi_node_network(tmp_path_factory):
    """
    Creates a network of 3 nodes.
    """
    nodes: List[BlockchainNode] = []
    for i in range(3):
        data_dir = tmp_path_factory.mktemp(f"node_{i}")
        bc = Blockchain(data_dir=str(data_dir))
        node = BlockchainNode(
            blockchain=bc,
            host="127.0.0.1",
            port=18545 + i,
            p2p_port=8765 + i,
            miner_address=f"miner_{i}",
        )
        nodes.append(node)

    # Start the nodes
    for node in nodes:
        asyncio.create_task(node.start_services())

    # Connect the nodes to each other
    for i, node in enumerate(nodes):
        for j, peer_node in enumerate(nodes):
            if i != j:
                node.add_peer(f"ws://127.0.0.1:{8765 + j}")

    yield nodes

    # Shutdown the nodes
    for node in nodes:
        await node.stop_services()


async def test_fork_resolution(multi_node_network):
    """
    Test that the network can resolve a fork.
    """
    nodes = multi_node_network
    
    # Mine some blocks on the first node
    for _ in range(3):
        nodes[0].blockchain.mine_pending_transactions(nodes[0].miner_address, nodes[0].identity)

    # Wait for the other nodes to sync
    await asyncio.sleep(5)
    
    # Create a fork on the second node
    nodes[1].p2p_manager.peers.remove("ws://127.0.0.1:8765")
    nodes[0].p2p_manager.peers.remove("ws://127.0.0.1:8766")
    
    for _ in range(5):
        nodes[1].blockchain.mine_pending_transactions(nodes[1].miner_address, nodes[1].identity)
        
    # Reconnect the nodes
    nodes[1].add_peer("ws://127.0.0.1:8765")
    nodes[0].add_peer("ws://127.0.0.1:8766")
    
    # Wait for the nodes to sync and resolve the fork
    await asyncio.sleep(10)
    
    # Check that all nodes have the same chain
    chain_hashes = ["".join([b.hash for b in node.blockchain.chain]) for node in nodes]
    assert all(hashes == chain_hashes[0] for hashes in chain_hashes)
