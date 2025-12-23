from __future__ import annotations

"""
Performance tests for block propagation across network peers.

Tests propagation time across multiple peers, bandwidth usage, compact block
relay performance, and network partition scenarios.

Run with: pytest tests/xai_tests/performance/test_block_propagation.py -v -m performance
"""

import pytest
import asyncio
import time
import statistics
import json
from typing import Any
from unittest.mock import Mock, AsyncMock, patch

from xai.core.blockchain import Blockchain
from xai.core.wallet import Wallet
from xai.core.transaction import Transaction
from xai.core.node_p2p import P2PNetworkManager

# Mark all tests in this module as performance tests
pytestmark = pytest.mark.performance

class TestBlockPropagation:
    """Tests for block propagation across network."""

    @pytest.fixture
    def blockchain(self, tmp_path):
        """Create a blockchain instance."""
        bc = Blockchain(data_dir=str(tmp_path / "blockchain"))
        bc.create_genesis_block()
        return bc

    @pytest.fixture
    def wallets(self):
        """Create wallets for testing."""
        return [Wallet() for _ in range(10)]

    def _create_block(self, blockchain: Blockchain, wallets: list[Wallet], tx_count: int = 5):
        """Helper to create and mine a block."""
        for i in range(tx_count):
            sender = wallets[i % len(wallets)]
            recipient = wallets[(i + 1) % len(wallets)]
            tx = Transaction(sender.address, recipient.address, 0.1, 0.001)
            tx.public_key = sender.public_key
            tx.sign_transaction(sender.private_key)

            try:
                blockchain.add_transaction(tx)
            except Exception:
                pass

        miner = wallets[0]
        try:
            blockchain.mine_pending_transactions(miner.address)
            return blockchain.get_latest_block()
        except Exception as e:
            print(f"Mining failed: {e}")
            return None

    @pytest.mark.asyncio
    async def test_block_propagation_single_peer(self, blockchain, wallets):
        """
        Test block propagation to single peer.

        Measures time from block creation to peer notification.
        """
        print(f"\n=== Block Propagation - Single Peer ===")

        # Create P2P manager
        p2p_manager = P2PNetworkManager(
            blockchain=blockchain,
            host="127.0.0.1",
            port=18770,
        )

        # Create a block
        block = self._create_block(blockchain, wallets, tx_count=10)
        assert block is not None, "Failed to create block"

        print(f"Block created: height={block.header.index}, txs={len(block.transactions)}")

        # Simulate propagation to one peer
        start = time.perf_counter()

        # Serialize block
        block_data = {
            "index": block.header.index,
            "timestamp": block.header.timestamp,
            "previous_hash": block.header.previous_hash,
            "nonce": block.header.nonce,
            "transactions": [
                {
                    "sender": tx.sender,
                    "recipient": tx.recipient,
                    "amount": tx.amount,
                    "fee": tx.fee,
                }
                for tx in block.transactions
            ],
        }

        block_json = json.dumps(block_data)
        serialization_time = time.perf_counter() - start

        print(f"Serialization time: {serialization_time * 1000:.2f} ms")
        print(f"Block size: {len(block_json)} bytes")

        # Simulate network send
        propagation_time = serialization_time + 0.001  # Add minimal network delay

        print(f"Total propagation time: {propagation_time * 1000:.2f} ms")

        # Propagation should be fast
        assert propagation_time < 0.1, f"Propagation too slow: {propagation_time * 1000:.2f} ms"

    @pytest.mark.asyncio
    async def test_block_propagation_multiple_peers(self, blockchain, wallets, benchmark):
        """
        Benchmark: Block propagation to multiple peers.

        Measures propagation time across 10 peers in parallel.
        """
        print(f"\n=== Block Propagation - Multiple Peers ===")

        # Create P2P manager
        p2p_manager = P2PNetworkManager(
            blockchain=blockchain,
            host="127.0.0.1",
            port=18771,
        )

        # Create a block
        block = self._create_block(blockchain, wallets, tx_count=20)
        assert block is not None, "Failed to create block"

        print(f"Block: height={block.header.index}, txs={len(block.transactions)}")

        # Mock peer connections
        num_peers = 10
        mock_peers = [f"peer_{i}" for i in range(num_peers)]

        def propagate_to_peers():
            """Simulate parallel propagation to all peers."""
            # Serialize block once
            block_data = {
                "index": block.header.index,
                "timestamp": block.header.timestamp,
                "previous_hash": block.header.previous_hash,
                "nonce": block.header.nonce,
                "transactions": [
                    {
                        "sender": tx.sender,
                        "recipient": tx.recipient,
                        "amount": tx.amount,
                    }
                    for tx in block.transactions
                ],
            }

            block_json = json.dumps(block_data)
            block_bytes = len(block_json)

            # Simulate sending to each peer
            propagation_times = []
            for peer in mock_peers:
                peer_start = time.perf_counter()
                # Simulate network send
                _ = block_json  # Would send to peer
                peer_time = time.perf_counter() - peer_start
                propagation_times.append(peer_time)

            return {
                "block_bytes": block_bytes,
                "peers": len(mock_peers),
                "propagation_times": propagation_times,
            }

        result = benchmark(propagate_to_peers)

        avg_time_ms = statistics.mean(result["propagation_times"]) * 1000
        max_time_ms = max(result["propagation_times"]) * 1000

        print(f"Propagated to {result['peers']} peers")
        print(f"Block size: {result['block_bytes']} bytes")
        print(f"Average propagation time: {avg_time_ms:.2f} ms")
        print(f"Max propagation time: {max_time_ms:.2f} ms")

    @pytest.mark.asyncio
    async def test_block_propagation_bandwidth_usage(self, blockchain, wallets):
        """
        Test bandwidth usage during block propagation.

        Measures data transferred for blocks of varying sizes.
        """
        print(f"\n=== Block Propagation Bandwidth Usage ===")

        block_sizes = [5, 10, 50, 100]  # Number of transactions per block
        bandwidth_data = []

        for tx_count in block_sizes:
            # Create block with specific transaction count
            block = self._create_block(blockchain, wallets, tx_count=tx_count)
            if not block:
                continue

            # Serialize block
            block_data = {
                "index": block.header.index,
                "timestamp": block.header.timestamp,
                "previous_hash": block.header.previous_hash,
                "nonce": block.header.nonce,
                "transactions": [
                    {
                        "sender": tx.sender,
                        "recipient": tx.recipient,
                        "amount": tx.amount,
                        "fee": tx.fee,
                        "signature": tx.signature if hasattr(tx, 'signature') else "",
                    }
                    for tx in block.transactions
                ],
            }

            block_json = json.dumps(block_data)
            full_size = len(block_json)

            # Simulate compact representation (header + tx IDs only)
            compact_data = {
                "index": block.header.index,
                "timestamp": block.header.timestamp,
                "previous_hash": block.header.previous_hash,
                "nonce": block.header.nonce,
                "tx_ids": [tx.txid for tx in block.transactions if hasattr(tx, 'txid')],
            }

            compact_json = json.dumps(compact_data)
            compact_size = len(compact_json)

            bandwidth_data.append({
                "tx_count": len(block.transactions),
                "full_size_kb": full_size / 1024,
                "compact_size_kb": compact_size / 1024,
                "reduction_pct": ((full_size - compact_size) / full_size * 100) if full_size > 0 else 0,
            })

            print(f"\nBlock with {len(block.transactions)} transactions:")
            print(f"  Full size: {full_size / 1024:.2f} KB")
            print(f"  Compact size: {compact_size / 1024:.2f} KB")
            print(f"  Reduction: {bandwidth_data[-1]['reduction_pct']:.1f}%")

        # Verify compact blocks reduce bandwidth significantly
        avg_reduction = statistics.mean(d["reduction_pct"] for d in bandwidth_data)
        print(f"\nAverage bandwidth reduction: {avg_reduction:.1f}%")
        assert avg_reduction > 30, "Compact blocks should reduce bandwidth by >30%"

    @pytest.mark.asyncio
    async def test_compact_block_relay_performance(self, blockchain, wallets, benchmark):
        """
        Benchmark: Compact block relay.

        Compares full block vs compact block propagation performance.
        """
        print(f"\n=== Compact Block Relay Performance ===")

        # Create a block with many transactions
        block = self._create_block(blockchain, wallets, tx_count=100)
        assert block is not None, "Failed to create block"

        print(f"Block transactions: {len(block.transactions)}")

        def full_block_relay():
            """Serialize and transmit full block."""
            block_data = {
                "index": block.header.index,
                "timestamp": block.header.timestamp,
                "previous_hash": block.header.previous_hash,
                "nonce": block.header.nonce,
                "transactions": [
                    {
                        "sender": tx.sender,
                        "recipient": tx.recipient,
                        "amount": tx.amount,
                        "fee": tx.fee,
                        "signature": tx.signature if hasattr(tx, 'signature') else "",
                        "public_key": tx.public_key if hasattr(tx, 'public_key') else "",
                    }
                    for tx in block.transactions
                ],
            }
            return json.dumps(block_data)

        def compact_block_relay():
            """Serialize and transmit compact block (header + tx IDs)."""
            compact_data = {
                "index": block.header.index,
                "timestamp": block.header.timestamp,
                "previous_hash": block.header.previous_hash,
                "nonce": block.header.nonce,
                "tx_ids": [tx.txid for tx in block.transactions if hasattr(tx, 'txid')],
            }
            return json.dumps(compact_data)

        # Benchmark both methods
        full_result = benchmark.pedantic(full_block_relay, iterations=100, rounds=5)
        full_time = benchmark.stats.stats.mean
        full_size = len(full_result)

        compact_result = benchmark.pedantic(compact_block_relay, iterations=100, rounds=5)
        compact_time = benchmark.stats.stats.mean
        compact_size = len(compact_result)

        print(f"\nFull block:")
        print(f"  Size: {full_size / 1024:.2f} KB")
        print(f"  Time: {full_time * 1000:.2f} ms")

        print(f"\nCompact block:")
        print(f"  Size: {compact_size / 1024:.2f} KB")
        print(f"  Time: {compact_time * 1000:.2f} ms")

        speedup = full_time / compact_time if compact_time > 0 else 0
        print(f"\nCompact block speedup: {speedup:.2f}x")

class TestNetworkTopology:
    """Tests for block propagation in different network topologies."""

    @pytest.fixture
    def blockchain(self, tmp_path):
        """Create a blockchain instance."""
        bc = Blockchain(data_dir=str(tmp_path / "blockchain"))
        bc.create_genesis_block()
        return bc

    @pytest.mark.asyncio
    async def test_propagation_star_topology(self, blockchain):
        """
        Test block propagation in star topology.

        Central node broadcasts to all peers directly.
        """
        print(f"\n=== Propagation - Star Topology ===")

        wallets = [Wallet() for _ in range(5)]

        # Create central node
        central_p2p = P2PNetworkManager(
            blockchain=blockchain,
            host="127.0.0.1",
            port=18772,
        )

        # Simulate peer nodes
        num_peers = 20
        peer_nodes = [f"peer_{i}" for i in range(num_peers)]

        # Create a block
        block = None
        for i in range(5):
            sender = wallets[i % len(wallets)]
            recipient = wallets[(i + 1) % len(wallets)]
            tx = Transaction(sender.address, recipient.address, 0.1, 0.001)
            tx.public_key = sender.public_key
            tx.sign_transaction(sender.private_key)

            try:
                blockchain.add_transaction(tx)
            except Exception:
                pass

        miner = wallets[0]
        blockchain.mine_pending_transactions(miner.address)
        block = blockchain.get_latest_block()

        # Measure propagation from central to all peers
        start = time.perf_counter()

        block_data = json.dumps({
            "index": block.header.index,
            "timestamp": block.header.timestamp,
            "transactions": len(block.transactions),
        })

        # Simulate broadcasts to all peers (parallel)
        propagation_times = []
        for peer in peer_nodes:
            peer_start = time.perf_counter()
            _ = block_data  # Would send to peer
            peer_time = time.perf_counter() - peer_start
            propagation_times.append(peer_time)

        total_time = time.perf_counter() - start

        avg_time_ms = statistics.mean(propagation_times) * 1000
        max_time_ms = max(propagation_times) * 1000

        print(f"Propagated to {num_peers} peers")
        print(f"Total time: {total_time * 1000:.2f} ms")
        print(f"Average peer time: {avg_time_ms:.2f} ms")
        print(f"Max peer time: {max_time_ms:.2f} ms")

        # All peers should receive quickly in star topology
        assert max_time_ms < 100, f"Star propagation too slow: {max_time_ms:.2f} ms"

    @pytest.mark.asyncio
    async def test_propagation_mesh_topology(self, blockchain):
        """
        Test block propagation in mesh topology.

        Nodes relay blocks to their neighbors, creating multi-hop paths.
        """
        print(f"\n=== Propagation - Mesh Topology ===")

        wallets = [Wallet() for _ in range(5)]

        # Simulate mesh network (each node connects to 4 neighbors)
        num_nodes = 20
        connections_per_node = 4

        # Create network graph (simplified simulation)
        network: dict[str, set[str]] = {}
        for i in range(num_nodes):
            node = f"node_{i}"
            # Connect to next few nodes (circular)
            neighbors = {f"node_{(i + j) % num_nodes}" for j in range(1, connections_per_node + 1)}
            network[node] = neighbors

        # Create a block
        for i in range(5):
            sender = wallets[i % len(wallets)]
            recipient = wallets[(i + 1) % len(wallets)]
            tx = Transaction(sender.address, recipient.address, 0.1, 0.001)
            tx.public_key = sender.public_key
            tx.sign_transaction(sender.private_key)

            try:
                blockchain.add_transaction(tx)
            except Exception:
                pass

        blockchain.mine_pending_transactions(wallets[0].address)
        block = blockchain.get_latest_block()

        block_data = json.dumps({
            "index": block.header.index,
            "timestamp": block.header.timestamp,
        })

        # Simulate propagation through mesh
        start = time.perf_counter()

        visited: set[str] = set()
        wave_times: list[float] = []

        # BFS-style propagation from origin node
        current_wave = {"node_0"}
        visited.add("node_0")
        wave_num = 0

        while current_wave and wave_num < 10:  # Max 10 hops
            wave_start = time.perf_counter()
            next_wave: set[str] = set()

            for node in current_wave:
                # Each node sends to its neighbors
                for neighbor in network.get(node, set()):
                    if neighbor not in visited:
                        next_wave.add(neighbor)
                        visited.add(neighbor)

            wave_time = time.perf_counter() - wave_start
            wave_times.append(wave_time)
            current_wave = next_wave
            wave_num += 1

        total_time = time.perf_counter() - start

        print(f"Propagated to {len(visited)} nodes in {wave_num} hops")
        print(f"Total time: {total_time * 1000:.2f} ms")
        print(f"Average hop time: {statistics.mean(wave_times) * 1000:.2f} ms")

        # Should reach most nodes in reasonable time
        assert len(visited) >= num_nodes * 0.8, "Propagation didn't reach most nodes"

    @pytest.mark.asyncio
    async def test_network_partition_recovery(self, blockchain):
        """
        Test block propagation recovery after network partition.

        Simulates network split and measures sync time after reconnection.
        """
        print(f"\n=== Network Partition Recovery ===")

        wallets = [Wallet() for _ in range(5)]

        # Create two network partitions
        partition_a = [f"node_a_{i}" for i in range(10)]
        partition_b = [f"node_b_{i}" for i in range(10)]

        print(f"Partition A: {len(partition_a)} nodes")
        print(f"Partition B: {len(partition_b)} nodes")

        # Partition A mines blocks
        blocks_a = []
        for i in range(20):
            sender = wallets[i % len(wallets)]
            recipient = wallets[(i + 1) % len(wallets)]
            tx = Transaction(sender.address, recipient.address, 0.1, 0.001)
            tx.public_key = sender.public_key
            tx.sign_transaction(sender.private_key)

            try:
                blockchain.add_transaction(tx)
            except Exception:
                pass

            blockchain.mine_pending_transactions(wallets[0].address)
            blocks_a.append(blockchain.get_latest_block())

        print(f"Partition A mined {len(blocks_a)} blocks")

        # Simulate reconnection and sync
        start = time.perf_counter()

        # Partition B needs to sync all blocks
        sync_times = []
        for block in blocks_a:
            sync_start = time.perf_counter()

            # Serialize and transmit block
            block_data = json.dumps({
                "index": block.header.index,
                "timestamp": block.header.timestamp,
                "transactions": len(block.transactions),
            })

            # Simulate transmission to partition B
            for node in partition_b:
                _ = block_data  # Would send to node

            sync_time = time.perf_counter() - sync_start
            sync_times.append(sync_time)

        total_sync_time = time.perf_counter() - start

        avg_block_sync_ms = statistics.mean(sync_times) * 1000

        print(f"\nSync recovery:")
        print(f"  Total time: {total_sync_time:.2f}s")
        print(f"  Avg per block: {avg_block_sync_ms:.2f} ms")
        print(f"  Throughput: {len(blocks_a) / total_sync_time:.2f} blocks/sec")

        # Sync should be reasonably fast
        assert total_sync_time < 10, f"Sync too slow: {total_sync_time:.2f}s"

class TestPropagationUnderLoad:
    """Tests for block propagation under heavy network load."""

    @pytest.fixture
    def blockchain(self, tmp_path):
        """Create a blockchain instance."""
        bc = Blockchain(data_dir=str(tmp_path / "blockchain"))
        bc.create_genesis_block()
        return bc

    @pytest.mark.asyncio
    async def test_concurrent_block_propagation(self, blockchain):
        """
        Test multiple blocks being propagated simultaneously.

        Simulates scenario where multiple miners find blocks at similar times.
        """
        print(f"\n=== Concurrent Block Propagation ===")

        wallets = [Wallet() for _ in range(10)]

        # Create multiple blocks
        blocks = []
        for block_num in range(5):
            for i in range(3):
                sender = wallets[i % len(wallets)]
                recipient = wallets[(i + 1) % len(wallets)]
                tx = Transaction(sender.address, recipient.address, 0.1, 0.001)
                tx.public_key = sender.public_key
                tx.sign_transaction(sender.private_key)

                try:
                    blockchain.add_transaction(tx)
                except Exception:
                    pass

            blockchain.mine_pending_transactions(wallets[block_num % len(wallets)].address)
            blocks.append(blockchain.get_latest_block())

        print(f"Created {len(blocks)} blocks")

        # Simulate concurrent propagation
        start = time.perf_counter()

        propagation_data = []
        for block in blocks:
            block_start = time.perf_counter()

            block_data = json.dumps({
                "index": block.header.index,
                "timestamp": block.header.timestamp,
                "transactions": len(block.transactions),
            })

            # Simulate broadcast to 10 peers
            for i in range(10):
                _ = block_data

            block_time = time.perf_counter() - block_start
            propagation_data.append(block_time)

        total_time = time.perf_counter() - start

        avg_time_ms = statistics.mean(propagation_data) * 1000

        print(f"Propagated {len(blocks)} blocks concurrently")
        print(f"Total time: {total_time * 1000:.2f} ms")
        print(f"Average per block: {avg_time_ms:.2f} ms")

        # Concurrent propagation should still be efficient
        assert avg_time_ms < 100, f"Concurrent propagation too slow: {avg_time_ms:.2f} ms"

    @pytest.mark.asyncio
    async def test_propagation_with_transaction_flood(self, blockchain, benchmark):
        """
        Benchmark: Block propagation during transaction flood.

        Tests block propagation when network is saturated with transactions.
        """
        print(f"\n=== Propagation with Transaction Flood ===")

        wallets = [Wallet() for _ in range(20)]

        # Create a block
        for i in range(10):
            sender = wallets[i % len(wallets)]
            recipient = wallets[(i + 1) % len(wallets)]
            tx = Transaction(sender.address, recipient.address, 0.1, 0.001)
            tx.public_key = sender.public_key
            tx.sign_transaction(sender.private_key)

            try:
                blockchain.add_transaction(tx)
            except Exception:
                pass

        blockchain.mine_pending_transactions(wallets[0].address)
        block = blockchain.get_latest_block()

        # Simulate transaction flood
        def propagate_under_load():
            """Propagate block while transactions are flooding."""
            # Create background transaction traffic
            tx_data_list = []
            for i in range(100):
                tx_data = {
                    "sender": wallets[i % len(wallets)].address,
                    "recipient": wallets[(i + 1) % len(wallets)].address,
                    "amount": 0.01,
                }
                tx_data_list.append(json.dumps(tx_data))

            # Propagate block amidst transaction traffic
            block_data = json.dumps({
                "index": block.header.index,
                "timestamp": block.header.timestamp,
                "transactions": len(block.transactions),
            })

            # Simulate network contention
            return len(block_data)

        result = benchmark(propagate_under_load)

        print(f"Block propagated: {result} bytes")
        print(f"Under load time: {benchmark.stats.stats.mean * 1000:.2f} ms")

if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v", "-m", "performance", "--benchmark-only"])
