"""
Comprehensive integration tests for network/P2P operations.
Tests multi-node scenarios, network synchronization, and failure recovery.

This file tests:
- Multi-node network formation
- Transaction propagation
- Block propagation
- Chain synchronization
- Network partitioning and recovery
- Peer discovery
- Node failure and recovery
"""

import asyncio
import pytest
import time
import threading
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from xai.core.blockchain import Blockchain, Transaction
from xai.core.wallet import Wallet
from xai.core.p2p.node_p2p import P2PNetworkManager
from xai.core.p2p.peer_discovery import PeerDiscoveryManager


class TestMultiNodeNetwork:
    """Test multi-node network formation and operation"""

    @pytest.fixture
    def blockchains(self):
        """Create multiple blockchain instances"""
        return [Blockchain() for _ in range(3)]

    @pytest.fixture
    def p2p_managers(self, blockchains):
        """Create P2P managers for each blockchain"""
        return [P2PNetworkManager(bc) for bc in blockchains]

    def test_three_node_network_formation(self, p2p_managers):
        """Test forming a 3-node network"""
        # Connect nodes in a mesh
        p2p_managers[0].add_peer("http://node1:5001")
        p2p_managers[0].add_peer("http://node2:5002")
        p2p_managers[1].add_peer("http://node0:5000")
        p2p_managers[1].add_peer("http://node2:5002")
        p2p_managers[2].add_peer("http://node0:5000")
        p2p_managers[2].add_peer("http://node1:5001")

        # Verify all nodes have peers
        assert p2p_managers[0].get_peer_count() == 2
        assert p2p_managers[1].get_peer_count() == 2
        assert p2p_managers[2].get_peer_count() == 2

    def test_peer_removal_from_network(self, p2p_managers):
        """Test removing a peer from the network"""
        # Setup network
        p2p_managers[0].add_peer("http://node1:5001")
        p2p_managers[1].add_peer("http://node0:5000")

        # Remove peer
        p2p_managers[0].remove_peer("http://node1:5001")

        assert p2p_managers[0].get_peer_count() == 0
        assert p2p_managers[1].get_peer_count() == 1  # Other node unaffected


class TestTransactionPropagation:
    """Test transaction propagation across network"""

    @pytest.fixture
    def network_setup(self):
        """Setup a 3-node network"""
        blockchains = [Blockchain() for _ in range(3)]
        p2p_managers = [P2PNetworkManager(bc) for bc in blockchains]

        # Connect in chain: node0 -> node1 -> node2
        p2p_managers[0].add_peer("http://node1:5001")
        p2p_managers[1].add_peer("http://node2:5002")

        return blockchains, p2p_managers

    @patch('xai.core.p2p.node_p2p.requests.post')
    def test_transaction_broadcast_to_peers(self, mock_post, network_setup):
        """Test transaction is broadcast to all peers"""
        blockchains, p2p_managers = network_setup
        mock_post.return_value.status_code = 200

        # Create and broadcast transaction
        tx = Mock(spec=Transaction)
        tx.to_dict = Mock(return_value={"txid": "tx123"})

        p2p_managers[0].broadcast_transaction(tx)

        # Should broadcast to node1
        assert mock_post.called
        assert any('node1' in str(call) for call in mock_post.call_args_list)

    @patch('xai.core.p2p.node_p2p.requests.post')
    def test_transaction_propagation_chain(self, mock_post, network_setup):
        """Test transaction propagates through chain"""
        blockchains, p2p_managers = network_setup
        mock_post.return_value.status_code = 200

        # Create transactions
        tx1 = Mock()
        tx1.to_dict = Mock(return_value={"txid": "tx1"})
        tx2 = Mock()
        tx2.to_dict = Mock(return_value={"txid": "tx2"})

        # Broadcast from different nodes
        p2p_managers[0].broadcast_transaction(tx1)
        p2p_managers[1].broadcast_transaction(tx2)

        # Both should have broadcast
        assert mock_post.call_count >= 2


class TestBlockPropagation:
    """Test block propagation across network"""

    @pytest.fixture
    def network_setup(self):
        """Setup a network with blockchains"""
        blockchains = [Blockchain() for _ in range(2)]
        p2p_managers = [P2PNetworkManager(bc) for bc in blockchains]

        p2p_managers[0].add_peer("http://node1:5001")
        p2p_managers[1].add_peer("http://node0:5000")

        return blockchains, p2p_managers

    @patch('xai.core.p2p.node_p2p.requests.post')
    def test_block_broadcast(self, mock_post, network_setup):
        """Test block is broadcast to peers"""
        blockchains, p2p_managers = network_setup
        mock_post.return_value.status_code = 200

        # Create mock block
        block = Mock()
        block.to_dict = Mock(return_value={"index": 1, "hash": "blockhash"})

        p2p_managers[0].broadcast_block(block)

        # Verify broadcast occurred
        assert mock_post.called
        call_args = mock_post.call_args_list[0]
        assert '/block/receive' in call_args[0][0]


class TestChainSynchronization:
    """Test blockchain synchronization between nodes"""

    @pytest.fixture
    def network_with_different_chains(self):
        """Setup network with nodes having different chain lengths"""
        # Node 0 has short chain
        bc0 = Blockchain()

        # Node 1 has longer chain
        bc1 = Blockchain()
        miner_wallet = Wallet()
        # Simulate longer chain by adding blocks
        for _ in range(2):
            bc1.pending_transactions.append(
                Transaction("SYSTEM", miner_wallet.address, 50, tx_type="reward")
            )
            bc1.mine_pending_transactions(miner_wallet.address)

        p2p0 = P2PNetworkManager(bc0)
        p2p1 = P2PNetworkManager(bc1)

        p2p0.add_peer("http://node1:5001")
        p2p1.add_peer("http://node0:5000")

        return bc0, bc1, p2p0, p2p1

    @patch('xai.core.p2p.node_p2p.P2PNetworkManager._download_remote_blocks', new_callable=AsyncMock)
    @patch('xai.core.p2p.node_p2p.P2PNetworkManager._collect_peer_chain_summaries', new_callable=AsyncMock)
    def test_sync_adopts_longer_chain(self, mock_collect, mock_download, network_with_different_chains):
        """Test node adopts longer chain from network"""
        bc0, bc1, p2p0, p2p1 = network_with_different_chains

        # Setup mock response from node1 (longer chain)
        longer_chain_data = [block.to_dict() for block in bc1.chain]
        mock_collect.return_value = [{"peer": "http://node1:5001", "total": len(bc1.chain)}]
        mock_download.return_value = longer_chain_data

        # Perform sync
        result = asyncio.run(p2p0.sync_with_network())

        # Should detect longer chain
        assert result is True

    @patch('xai.core.p2p.node_p2p.P2PNetworkManager._collect_peer_chain_summaries', new_callable=AsyncMock)
    def test_sync_keeps_own_chain_if_longest(self, mock_collect):
        """Test node keeps its own chain if it's longest"""
        # Create node with long chain
        bc = Blockchain()
        miner_wallet = Wallet()
        for _ in range(5):
            bc.pending_transactions.append(
                Transaction("SYSTEM", miner_wallet.address, 50, tx_type="reward")
            )
            bc.mine_pending_transactions(miner_wallet.address)

        p2p = P2PNetworkManager(bc)
        p2p.add_peer("http://node1:5001")

        # Mock summaries from peer with shorter chain
        mock_collect.return_value = [{"peer": "http://node1:5001", "total": 2}]

        result = asyncio.run(p2p.sync_with_network())

        # Should not update
        assert result is False


class TestNetworkPartitioning:
    """Test network behavior under partitioning"""

    @pytest.fixture
    def partitioned_network(self):
        """Create a network that can be partitioned"""
        blockchains = [Blockchain() for _ in range(4)]
        p2p_managers = [P2PNetworkManager(bc) for bc in blockchains]

        # Initial full mesh
        for i, mgr in enumerate(p2p_managers):
            for j in range(len(p2p_managers)):
                if i != j:
                    mgr.add_peer(f"http://node{j}:500{j}")

        return blockchains, p2p_managers

    def test_network_partition_creation(self, partitioned_network):
        """Test creating a network partition"""
        blockchains, p2p_managers = partitioned_network

        # Partition into two groups: [0,1] and [2,3]
        # Remove connections between groups
        p2p_managers[0].remove_peer("http://node2:5002")
        p2p_managers[0].remove_peer("http://node3:5003")
        p2p_managers[1].remove_peer("http://node2:5002")
        p2p_managers[1].remove_peer("http://node3:5003")
        p2p_managers[2].remove_peer("http://node0:5000")
        p2p_managers[2].remove_peer("http://node1:5001")
        p2p_managers[3].remove_peer("http://node0:5000")
        p2p_managers[3].remove_peer("http://node1:5001")

        # Verify partition
        assert p2p_managers[0].get_peer_count() == 1  # Only node1
        assert p2p_managers[2].get_peer_count() == 1  # Only node3

    def test_network_partition_healing(self, partitioned_network):
        """Test healing a network partition"""
        blockchains, p2p_managers = partitioned_network

        # Create partition
        p2p_managers[0].remove_peer("http://node2:5002")
        p2p_managers[2].remove_peer("http://node0:5000")

        # Heal partition
        p2p_managers[0].add_peer("http://node2:5002")
        p2p_managers[2].add_peer("http://node0:5000")

        # Verify healed
        assert "http://node2:5002" in p2p_managers[0].peers
        assert "http://node0:5000" in p2p_managers[2].peers


class TestPeerDiscoveryIntegration:
    """Test peer discovery in network context"""

    @patch('xai.core.p2p.peer_discovery.PeerDiscoveryProtocol.ping_peer')
    @patch('xai.core.p2p.peer_discovery.PeerDiscoveryProtocol.send_get_peers_request')
    def test_bootstrap_and_connect(self, mock_get_peers, mock_ping):
        """Test bootstrap and connection to discovered peers"""
        mock_ping.return_value = (True, 0.5)
        mock_get_peers.return_value = [
            'http://peer1:5000',
            'http://peer2:5000'
        ]

        manager = PeerDiscoveryManager(
            network_type="testnet",
            my_url="http://my-node:5000",
            max_peers=10
        )

        discovered = manager.bootstrap_network()

        # Should discover peers from bootstrap nodes
        assert discovered > 0
        assert len(manager.known_peers) > 0

    @patch('xai.core.p2p.peer_discovery.PeerDiscoveryProtocol.ping_peer')
    def test_connect_to_discovered_peers(self, mock_ping):
        """Test connecting to discovered peers"""
        mock_ping.return_value = (True, 0.5)

        manager = PeerDiscoveryManager(max_peers=5)

        # Manually add some known peers
        from xai.core.p2p.peer_discovery import PeerInfo
        for i in range(3):
            peer = PeerInfo(f"http://peer{i}:5000")
            manager.known_peers[peer.url] = peer

        # Connect to them
        connected = manager.connect_to_best_peers(count=2)

        assert len(connected) <= 2
        assert len(manager.connected_peers) <= 2


class TestNodeFailureRecovery:
    """Test network behavior when nodes fail"""

    @pytest.fixture
    def network_setup(self):
        """Setup a 3-node network"""
        blockchains = [Blockchain() for _ in range(3)]
        p2p_managers = [P2PNetworkManager(bc) for bc in blockchains]

        # Connect nodes
        for i, mgr in enumerate(p2p_managers):
            for j in range(len(p2p_managers)):
                if i != j:
                    mgr.add_peer(f"http://node{j}:500{j}")

        return blockchains, p2p_managers

    @patch('xai.core.p2p.node_p2p.P2PNetworkManager._get_peer_api_endpoints', return_value=[])
    @patch('xai.core.p2p.node_p2p.P2PNetworkManager._dispatch_async')
    @patch('xai.core.p2p.node_p2p.requests.post')
    def test_broadcast_continues_on_node_failure(
        self,
        mock_post,
        _mock_dispatch,
        _mock_endpoints,
        network_setup,
    ):
        """Test broadcasting continues when some nodes fail"""
        blockchains, p2p_managers = network_setup
        peer_endpoints = p2p_managers[0]._get_peer_api_endpoints()
        if not peer_endpoints:
            peer_endpoints = p2p_managers[0]._http_peers_snapshot()

        # Simulate one node failing
        def post_side_effect(*args, **kwargs):
            if 'node1' in args[0]:
                raise Exception("Node failed")
            return Mock(status_code=200)

        mock_post.side_effect = post_side_effect

        tx = Mock()
        tx.to_dict = Mock(return_value={"txid": "tx1"})

        # Should complete despite one failure
        p2p_managers[0].broadcast_transaction(tx)

        # Should have attempted all peers
        assert mock_post.call_count == len(peer_endpoints)

    def test_peer_removal_after_timeout(self):
        """Test peer is removed after timeout"""
        manager = PeerDiscoveryManager()

        from xai.core.p2p.peer_discovery import PeerInfo
        import time

        # Add peer with old last_seen
        peer = PeerInfo('http://old-peer:5000')
        peer.last_seen = time.time() - 5000  # 5000 seconds ago
        manager.known_peers['http://old-peer:5000'] = peer
        manager.connected_peers.add('http://old-peer:5000')

        # Remove dead peers
        removed = manager.remove_dead_peers(timeout=3600)

        assert removed == 1
        assert 'http://old-peer:5000' not in manager.known_peers


class TestConcurrentNetworkOperations:
    """Test concurrent network operations"""

    @pytest.fixture
    def network_setup(self):
        """Setup network for concurrent testing"""
        bc = Blockchain()
        p2p = P2PNetworkManager(bc)
        return bc, p2p

    @patch('xai.core.p2p.node_p2p.P2PNetworkManager._get_peer_api_endpoints', return_value=[])
    @patch('xai.core.p2p.node_p2p.P2PNetworkManager._dispatch_async')
    @patch('xai.core.p2p.node_p2p.requests.post')
    def test_concurrent_broadcasts(self, mock_post, _mock_dispatch, _mock_endpoints, network_setup):
        """Test concurrent transaction broadcasts"""
        bc, p2p = network_setup
        p2p.add_peer("http://peer1:5000")
        p2p.add_peer("http://peer2:5000")
        peer_endpoints = p2p._get_peer_api_endpoints()
        if not peer_endpoints:
            peer_endpoints = p2p._http_peers_snapshot()

        mock_post.return_value.status_code = 200

        # Create multiple transactions
        transactions = []
        for i in range(5):
            tx = Mock()
            tx.to_dict = Mock(return_value={"txid": f"tx{i}"})
            transactions.append(tx)

        # Broadcast concurrently
        threads = []
        for tx in transactions:
            t = threading.Thread(target=p2p.broadcast_transaction, args=(tx,))
            threads.append(t)
            t.start()

        # Wait for all to complete
        for t in threads:
            t.join()

        # All should have broadcast
        assert mock_post.call_count >= len(peer_endpoints) * len(transactions)

    def test_concurrent_peer_additions(self, network_setup):
        """Test concurrent peer additions"""
        bc, p2p = network_setup

        def add_peers(start_idx):
            for i in range(start_idx, start_idx + 10):
                p2p.add_peer(f"http://peer{i}:5000")

        threads = []
        for i in range(3):
            t = threading.Thread(target=add_peers, args=(i * 10,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Should have 30 unique peers
        assert p2p.get_peer_count() == 30


class TestNetworkStressScenarios:
    """Test network under stress conditions"""

    @patch('xai.core.p2p.node_p2p.P2PNetworkManager._get_peer_api_endpoints', return_value=[])
    @patch('xai.core.p2p.node_p2p.P2PNetworkManager._dispatch_async')
    @patch('xai.core.p2p.node_p2p.requests.post')
    def test_high_volume_broadcasts(self, mock_post, _mock_dispatch, _mock_endpoints):
        """Test network with high volume of broadcasts"""
        bc = Blockchain()
        p2p = P2PNetworkManager(bc)

        # Add many peers
        for i in range(50):
            p2p.add_peer(f"http://peer{i}:5000")
        peer_endpoints = p2p._get_peer_api_endpoints()
        if not peer_endpoints:
            peer_endpoints = p2p._http_peers_snapshot()

        mock_post.return_value.status_code = 200

        # Broadcast many transactions
        for i in range(100):
            tx = Mock()
            tx.to_dict = Mock(return_value={"txid": f"tx{i}"})
            p2p.broadcast_transaction(tx)

        # Should have attempted all broadcasts
        assert mock_post.call_count == len(peer_endpoints) * 100

    @patch('xai.core.p2p.node_p2p.P2PNetworkManager._collect_peer_chain_summaries', new_callable=AsyncMock)
    def test_sync_with_many_peers(self, mock_collect):
        """Test synchronization with many peers"""
        bc = Blockchain()
        p2p = P2PNetworkManager(bc)

        # Add many peers
        for i in range(20):
            p2p.add_peer(f"http://peer{i}:5000")

        mock_collect.return_value = []

        asyncio.run(p2p.sync_with_network())

        # Should have queried all peers
        assert mock_collect.await_count == 1
        assert len(mock_collect.call_args[0][0]) == 20


class TestNetworkErrorRecovery:
    """Test network error recovery mechanisms"""

    @patch('xai.core.p2p.node_p2p.P2PNetworkManager._get_peer_api_endpoints', return_value=[])
    @patch('xai.core.p2p.node_p2p.P2PNetworkManager._dispatch_async')
    @patch('xai.core.p2p.node_p2p.requests.post')
    def test_retry_after_timeout(self, mock_post, _mock_dispatch, _mock_endpoints):
        """Test operations continue after timeout"""
        bc = Blockchain()
        p2p = P2PNetworkManager(bc)
        p2p.add_peer("http://peer1:5000")

        # First call times out, second succeeds
        mock_post.side_effect = [
            Exception("Timeout"),
            Mock(status_code=200)
        ]

        tx = Mock()
        tx.to_dict = Mock(return_value={"txid": "tx1"})

        # First broadcast (fails)
        p2p.broadcast_transaction(tx)

        # Second broadcast (succeeds)
        p2p.broadcast_transaction(tx)

        assert mock_post.call_count == 2

    @patch('xai.core.p2p.node_p2p.P2PNetworkManager._collect_peer_chain_summaries', new_callable=AsyncMock)
    def test_sync_recovery_after_errors(self, mock_collect):
        """Test sync recovers after errors"""
        bc = Blockchain()
        p2p = P2PNetworkManager(bc)
        p2p.add_peer("http://peer1:5000")

        # First attempt returns no summaries
        mock_collect.return_value = []
        result1 = asyncio.run(p2p.sync_with_network())
        assert result1 is False

        # Second attempt succeeds
        mock_collect.return_value = [{"peer": "http://peer1:5000", "total": len(bc.chain)}]

        result2 = asyncio.run(p2p.sync_with_network())
        # Since chain length is same, no update needed
        assert result2 is False  # But operation completes
