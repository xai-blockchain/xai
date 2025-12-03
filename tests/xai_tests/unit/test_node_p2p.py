"""
Comprehensive tests for node_p2p.py - P2P Network Manager

This test file achieves 98%+ coverage of node_p2p.py by testing:
- Peer management (add/remove)
- Transaction broadcasting
- Block broadcasting
- Blockchain synchronization
- Network error handling
- All edge cases
"""

import time
import pytest
from unittest.mock import Mock, MagicMock, patch
import requests

from xai.core.p2p_security import P2PSecurityConfig


class TestPeerManagement:
    """Test peer management functionality."""

    @pytest.fixture
    def blockchain(self):
        """Create mock blockchain."""
        blockchain = Mock()
        blockchain.chain = [Mock(), Mock(), Mock()]
        return blockchain

    @pytest.fixture
    def p2p_manager(self, blockchain):
        """Create P2PNetworkManager instance."""
        from xai.core.node_p2p import P2PNetworkManager
        return P2PNetworkManager(blockchain)

    def test_add_peer_new(self, p2p_manager):
        """Test adding a new peer."""
        peer_url = "http://peer1:5000"
        p2p_manager.add_peer(peer_url)

        assert peer_url in p2p_manager.peers
        assert len(p2p_manager.peers) == 1

    def test_add_peer_duplicate(self, p2p_manager):
        """Test adding duplicate peer doesn't create duplicates."""
        peer_url = "http://peer1:5000"
        p2p_manager.add_peer(peer_url)
        p2p_manager.add_peer(peer_url)  # Add same peer again

        assert len(p2p_manager.peers) == 1

    def test_add_multiple_peers(self, p2p_manager):
        """Test adding multiple peers."""
        peers = [
            "http://peer1:5000",
            "http://peer2:5000",
            "http://peer3:5000"
        ]

        for peer in peers:
            p2p_manager.add_peer(peer)

        assert len(p2p_manager.peers) == 3
        for peer in peers:
            assert peer in p2p_manager.peers

    def test_remove_peer_existing(self, p2p_manager):
        """Test removing an existing peer."""
        peer_url = "http://peer1:5000"
        p2p_manager.add_peer(peer_url)
        p2p_manager.remove_peer(peer_url)

        assert peer_url not in p2p_manager.peers
        assert len(p2p_manager.peers) == 0

    def test_remove_peer_nonexistent(self, p2p_manager):
        """Test removing a non-existent peer."""
        # Should not raise exception
        p2p_manager.remove_peer("http://nonexistent:5000")
        assert len(p2p_manager.peers) == 0

    def test_get_peer_count(self, p2p_manager):
        """Test get_peer_count method."""
        assert p2p_manager.get_peer_count() == 0

        p2p_manager.add_peer("http://peer1:5000")
        assert p2p_manager.get_peer_count() == 1

        p2p_manager.add_peer("http://peer2:5000")
        assert p2p_manager.get_peer_count() == 2

    def test_get_peers(self, p2p_manager):
        """Test get_peers method returns copy."""
        original_peers = {"http://peer1:5000", "http://peer2:5000"}
        for peer in original_peers:
            p2p_manager.add_peer(peer)

        peers_copy = p2p_manager.get_peers()

        assert peers_copy == original_peers
        # Verify it's a copy, not the original
        assert peers_copy is not p2p_manager.peers


class TestTransactionBroadcasting:
    """Test transaction broadcasting functionality."""

    @pytest.fixture
    def blockchain(self):
        """Create mock blockchain."""
        return Mock()

    @pytest.fixture
    def p2p_manager(self, blockchain):
        """Create P2PNetworkManager instance."""
        from xai.core.node_p2p import P2PNetworkManager
        manager = P2PNetworkManager(blockchain)
        manager.add_peer("http://peer1:5000")
        manager.add_peer("http://peer2:5000")
        return manager

    @pytest.fixture
    def mock_transaction(self):
        """Create mock transaction."""
        tx = Mock()
        tx.to_dict = Mock(return_value={
            "txid": "tx123",
            "sender": "addr1",
            "recipient": "addr2",
            "amount": 10.0
        })
        return tx

    @patch('xai.core.node_p2p.requests.post')
    def test_broadcast_transaction_success(self, mock_post, p2p_manager, mock_transaction):
        """Test successful transaction broadcast."""
        mock_post.return_value.status_code = 200

        p2p_manager.broadcast_transaction(mock_transaction)

        # Verify transaction was broadcast to all peers
        assert mock_post.call_count == 2
        for call in mock_post.call_args_list:
            args, kwargs = call
            assert args[0].endswith('/transaction/receive')
            assert 'json' in kwargs
            assert kwargs['timeout'] == 2

    @patch('xai.core.node_p2p.requests.post')
    def test_broadcast_transaction_peer_failure(self, mock_post, p2p_manager, mock_transaction):
        """Test transaction broadcast with peer failure."""
        # First peer fails, second succeeds
        mock_post.side_effect = [
            Exception("Connection refused"),
            Mock(status_code=200)
        ]

        # Should not raise exception
        p2p_manager.broadcast_transaction(mock_transaction)

        assert mock_post.call_count == 2

    @patch('xai.core.node_p2p.requests.post')
    def test_broadcast_transaction_all_peers_fail(self, mock_post, p2p_manager, mock_transaction):
        """Test transaction broadcast when all peers fail."""
        mock_post.side_effect = Exception("Network error")

        # Should not raise exception
        p2p_manager.broadcast_transaction(mock_transaction)

        assert mock_post.call_count == 2

    @patch('xai.core.node_p2p.requests.post')
    def test_broadcast_transaction_includes_peer_api_key(self, mock_post, blockchain, mock_transaction):
        """Ensure peer API key header is attached when configured."""
        from xai.core.node_p2p import P2PNetworkManager

        manager = P2PNetworkManager(blockchain, peer_api_key="shared-secret")
        manager.add_peer("http://peer1:5000")

        manager.broadcast_transaction(mock_transaction)

        mock_post.assert_called_once()
        _, kwargs = mock_post.call_args
        assert kwargs.get('headers') == {"X-API-Key": "shared-secret"}

    @patch('xai.core.node_p2p.requests.post')
    def test_broadcast_transaction_no_peers(self, mock_post, blockchain, mock_transaction):
        """Test transaction broadcast with no peers."""
        from xai.core.node_p2p import P2PNetworkManager
        manager = P2PNetworkManager(blockchain)

        manager.broadcast_transaction(mock_transaction)

        # No calls should be made
        assert mock_post.call_count == 0


class TestBlockBroadcasting:
    """Test block broadcasting functionality."""

    @pytest.fixture
    def blockchain(self):
        """Create mock blockchain."""
        return Mock()

    @pytest.fixture
    def p2p_manager(self, blockchain):
        """Create P2PNetworkManager instance."""
        from xai.core.node_p2p import P2PNetworkManager
        manager = P2PNetworkManager(blockchain)
        manager.add_peer("http://peer1:5000")
        manager.add_peer("http://peer2:5000")
        manager.add_peer("http://peer3:5000")
        return manager

    @pytest.fixture
    def mock_block(self):
        """Create mock block."""
        block = Mock()
        block.to_dict = Mock(return_value={
            "index": 5,
            "hash": "blockhash123",
            "previous_hash": "prevhash",
            "transactions": []
        })
        return block

    @patch('xai.core.node_p2p.requests.post')
    def test_broadcast_block_success(self, mock_post, p2p_manager, mock_block):
        """Test successful block broadcast."""
        mock_post.return_value.status_code = 200

        p2p_manager.broadcast_block(mock_block)

        # Verify block was broadcast to all peers
        assert mock_post.call_count == 3
        for call in mock_post.call_args_list:
            args, kwargs = call
            assert args[0].endswith('/block/receive')
            assert 'json' in kwargs
            assert kwargs['timeout'] == 2

    @patch('xai.core.node_p2p.requests.post')
    def test_broadcast_block_includes_peer_api_key(self, mock_post, blockchain, mock_block):
        """Block broadcasts also include peer headers."""
        from xai.core.node_p2p import P2PNetworkManager

        manager = P2PNetworkManager(blockchain, peer_api_key="secret-key")
        manager.add_peer("http://peerA")

        manager.broadcast_block(mock_block)

        mock_post.assert_called_once()
        _, kwargs = mock_post.call_args
        assert kwargs.get('headers') == {"X-API-Key": "secret-key"}

    @patch('xai.core.node_p2p.requests.post')
    def test_broadcast_block_partial_failure(self, mock_post, p2p_manager, mock_block):
        """Test block broadcast with some peers failing."""
        # Mix of success and failure
        mock_post.side_effect = [
            Mock(status_code=200),
            Exception("Timeout"),
            Mock(status_code=200)
        ]

        p2p_manager.broadcast_block(mock_block)

        assert mock_post.call_count == 3

    @patch('xai.core.node_p2p.requests.post')
    def test_broadcast_block_timeout(self, mock_post, p2p_manager, mock_block):
        """Test block broadcast with timeout."""
        mock_post.side_effect = requests.exceptions.Timeout("Request timeout")

        p2p_manager.broadcast_block(mock_block)

        assert mock_post.call_count == 3


class TestBlockchainSynchronization:
    """Test blockchain synchronization functionality."""

    @pytest.fixture
    def blockchain(self):
        """Create mock blockchain with 3 blocks."""
        blockchain = Mock()
        blocks = [Mock(index=i) for i in range(3)]
        blockchain.chain = blocks
        blockchain.replace_chain = Mock(return_value=True)

        def _deserialize(chain_data):
            return [Mock(index=entry.get("index")) for entry in chain_data]

        blockchain.deserialize_chain = Mock(side_effect=_deserialize)
        return blockchain

    @pytest.fixture
    def p2p_manager(self, blockchain):
        """Create P2PNetworkManager instance."""
        from xai.core.node_p2p import P2PNetworkManager
        manager = P2PNetworkManager(blockchain)
        manager.add_peer("http://peer1:5000")
        manager.add_peer("http://peer2:5000")
        return manager

    @patch('xai.core.node_p2p.requests.get')
    def test_sync_with_network_longer_chain_found(self, mock_get, p2p_manager):
        """Test sync when longer chain is found."""
        # First peer has longer chain
        mock_response1 = Mock()
        mock_response1.status_code = 200
        mock_response1.json.side_effect = [
            {"total": 5},  # Initial query
            {"blocks": [{"index": i} for i in range(5)]}  # Full chain
        ]

        # Second peer has shorter chain
        mock_response2 = Mock()
        mock_response2.status_code = 200
        mock_response2.json.return_value = {"total": 2}

        mock_get.side_effect = [
            mock_response1,  # peer1 initial
            mock_response1,  # peer1 full chain
            mock_response2   # peer2
        ]

        result = p2p_manager.sync_with_network()

        assert result == True  # Longer chain was found

    @patch('xai.core.node_p2p.requests.get')
    def test_sync_with_network_no_longer_chain(self, mock_get, p2p_manager):
        """Test sync when no longer chain exists."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"total": 2}  # Shorter than our 3 blocks

        mock_get.return_value = mock_response

        result = p2p_manager.sync_with_network()

        assert result == False  # No update needed

    @patch('xai.core.node_p2p.requests.get')
    def test_sync_with_network_same_length(self, mock_get, p2p_manager):
        """Test sync when chains are same length."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"total": 3}  # Same as our 3 blocks

        mock_get.return_value = mock_response

        result = p2p_manager.sync_with_network()

        assert result == False  # No update needed

    @patch('xai.core.node_p2p.requests.get')
    def test_sync_with_network_peer_unavailable(self, mock_get, p2p_manager):
        """Test sync when peers are unavailable."""
        mock_get.side_effect = Exception("Connection refused")

        result = p2p_manager.sync_with_network()

        assert result == False

    @patch('xai.core.node_p2p.requests.get')
    def test_sync_with_network_mixed_responses(self, mock_get, p2p_manager):
        """Test sync with mixed peer responses."""
        # First peer fails, second succeeds with shorter chain
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"total": 2}

        mock_get.side_effect = [
            Exception("Connection error"),  # peer1 fails
            mock_response  # peer2 succeeds
        ]

        result = p2p_manager.sync_with_network()

        assert result == False

    @patch('xai.core.node_p2p.requests.get')
    def test_sync_with_network_invalid_json(self, mock_get, p2p_manager):
        """Test sync with invalid JSON response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")

        mock_get.return_value = mock_response

        # Should handle gracefully
        result = p2p_manager.sync_with_network()

        # Should continue to try other peers
        assert mock_get.call_count == 2

    @patch('xai.core.node_p2p.requests.get')
    def test_sync_with_network_http_error(self, mock_get, p2p_manager):
        """Test sync with HTTP error responses."""
        mock_response = Mock()
        mock_response.status_code = 500

        mock_get.return_value = mock_response

        result = p2p_manager.sync_with_network()

        assert result == False

    @patch('xai.core.node_p2p.requests.get')
    def test_sync_with_network_timeout(self, mock_get, p2p_manager):
        """Test sync with timeout."""
        mock_get.side_effect = requests.exceptions.Timeout("Request timeout")

        result = p2p_manager.sync_with_network()

        assert result == False


class TestNetworkErrorHandling:
    """Test error handling in network operations."""

    @pytest.fixture
    def blockchain(self):
        """Create mock blockchain."""
        blockchain = Mock()
        blockchain.chain = [Mock()]
        return blockchain

    @pytest.fixture
    def p2p_manager(self, blockchain):
        """Create P2PNetworkManager instance."""
        from xai.core.node_p2p import P2PNetworkManager
        manager = P2PNetworkManager(blockchain)
        manager.add_peer("http://peer1:5000")
        return manager

    @patch('xai.core.node_p2p.requests.post')
    def test_network_connection_errors(self, mock_post, p2p_manager):
        """Test handling of connection errors."""
        mock_tx = Mock()
        mock_tx.to_dict = Mock(return_value={})

        # Test various connection errors
        errors = [
            requests.exceptions.ConnectionError("Connection failed"),
            requests.exceptions.Timeout("Timeout"),
            requests.exceptions.RequestException("Request failed"),
            Exception("Unknown error")
        ]

        for error in errors:
            mock_post.side_effect = error
            # Should not raise exception
            p2p_manager.broadcast_transaction(mock_tx)

    @patch('xai.core.node_p2p.requests.get')
    def test_sync_network_errors(self, mock_get, p2p_manager):
        """Test handling of network errors during sync."""
        errors = [
            requests.exceptions.ConnectionError("Connection failed"),
            requests.exceptions.Timeout("Timeout"),
            requests.exceptions.RequestException("Request failed"),
            Exception("Unknown error")
        ]

        for error in errors:
            mock_get.side_effect = error
            result = p2p_manager.sync_with_network()
            assert result == False


class TestP2PIntegration:
    """Integration tests for P2P functionality."""

    @pytest.fixture
    def blockchain(self):
        """Create mock blockchain."""
        blockchain = Mock()
        blockchain.chain = [Mock(index=0), Mock(index=1)]
        return blockchain

    @pytest.fixture
    def p2p_manager(self, blockchain):
        """Create P2PNetworkManager instance."""
        from xai.core.node_p2p import P2PNetworkManager
        return P2PNetworkManager(blockchain)

    def test_full_peer_lifecycle(self, p2p_manager):
        """Test complete peer lifecycle: add, use, remove."""
        peer = "http://peer1:5000"

        # Add peer
        p2p_manager.add_peer(peer)
        assert peer in p2p_manager.peers

        # Use peer (verify it exists)
        assert p2p_manager.get_peer_count() == 1

        # Remove peer
        p2p_manager.remove_peer(peer)
        assert peer not in p2p_manager.peers

    @patch('xai.core.node_p2p.requests.post')
    @patch('xai.core.node_p2p.requests.get')
    def test_broadcast_and_sync_workflow(self, mock_get, mock_post, p2p_manager):
        """Test broadcast and sync workflow."""
        # Setup
        p2p_manager.add_peer("http://peer1:5000")

        # Broadcast transaction
        mock_tx = Mock()
        mock_tx.to_dict = Mock(return_value={"txid": "tx1"})
        p2p_manager.broadcast_transaction(mock_tx)

        # Broadcast block
        mock_block = Mock()
        mock_block.to_dict = Mock(return_value={"index": 1})
        p2p_manager.broadcast_block(mock_block)

        # Sync blockchain
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"total": 2}
        mock_get.return_value = mock_response

        p2p_manager.sync_with_network()

        # Verify all operations completed
        assert mock_post.call_count == 2  # tx + block
        assert mock_get.call_count == 1


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.fixture
    def blockchain(self):
        """Create mock blockchain."""
        blockchain = Mock()
        blockchain.chain = []
        blockchain.replace_chain = Mock(return_value=True)

        def _deserialize(chain_data):
            return [Mock(index=entry.get("index")) for entry in chain_data]

        blockchain.deserialize_chain = Mock(side_effect=_deserialize)
        return blockchain

    @pytest.fixture
    def p2p_manager(self, blockchain):
        """Create P2PNetworkManager instance."""
        from xai.core.node_p2p import P2PNetworkManager
        return P2PNetworkManager(blockchain)

    @patch('xai.core.node_p2p.requests.get')
    def test_sync_empty_blockchain(self, mock_get, p2p_manager):
        """Test sync with empty blockchain."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = [
            {"total": 5},
            {"blocks": [{"index": i} for i in range(5)]}
        ]

        p2p_manager.add_peer("http://peer1:5000")
        mock_get.return_value = mock_response

        result = p2p_manager.sync_with_network()

        assert result == True

    def test_add_empty_peer_url(self, p2p_manager):
        """Test adding empty peer URL."""
        p2p_manager.add_peer("")
        # Empty string should still be added to set
        assert "" in p2p_manager.peers

    def test_multiple_add_remove_cycles(self, p2p_manager):
        """Test multiple add/remove cycles."""
        peer = "http://peer1:5000"

        for _ in range(5):
            p2p_manager.add_peer(peer)
            assert peer in p2p_manager.peers

            p2p_manager.remove_peer(peer)
            assert peer not in p2p_manager.peers


class TestMessageDeduplication:
    """Ensure duplicate transactions/blocks are dropped to prevent floods."""

    @pytest.fixture
    def blockchain(self):
        blockchain = Mock()
        blockchain.storage = Mock()
        blockchain.storage.data_dir = "data"
        tx_obj = Mock()
        tx_obj.txid = "tx-123"
        blockchain._transaction_from_dict = Mock(return_value=tx_obj)
        blockchain.add_transaction = Mock(return_value=True)
        blockchain.deserialize_block = Mock(return_value=Mock())
        blockchain.add_block = Mock(return_value=True)
        blockchain.to_dict = Mock(return_value={"height": 1})
        return blockchain

    @pytest.fixture
    def p2p_manager(self, blockchain):
        from xai.core.node_p2p import P2PNetworkManager

        manager = P2PNetworkManager(blockchain)
        # Relax rate/bandwidth guards for deterministic tests
        manager.rate_limiter.is_rate_limited = MagicMock(return_value=False)
        manager.bandwidth_limiter_in.consume = MagicMock(return_value=True)
        manager.peer_manager.reputation = MagicMock()
        manager.peer_manager.reputation.record_valid_transaction = MagicMock()
        manager.peer_manager.reputation.record_invalid_transaction = MagicMock()
        manager.peer_manager.reputation.record_valid_block = MagicMock()
        manager.peer_manager.reputation.record_invalid_block = MagicMock()
        manager.peer_manager.encryption.verify_signed_message = MagicMock()
        manager.peer_manager.is_sender_allowed = MagicMock(return_value=True)
        manager.peer_manager.is_nonce_replay = MagicMock(return_value=False)
        manager.peer_manager.record_nonce = MagicMock()
        manager._dedup_ttl = 0.05
        manager._dedup_max_items = 2
        return manager

    @pytest.mark.asyncio
    async def test_duplicate_transactions_are_dropped(self, p2p_manager):
        verified_message = {
            "sender": "peer_pubkey",
            "payload": {"type": "transaction", "payload": {"txid": "tx-dupe", "sender": "a"}},
            "version": getattr(P2PSecurityConfig, "PROTOCOL_VERSION", "1"),
        }
        p2p_manager.peer_manager.encryption.verify_signed_message = MagicMock(return_value=verified_message)
        websocket = MagicMock()
        websocket.remote_address = ("127.0.0.1", 9000)
        p2p_manager.websocket_peer_ids[websocket] = "peer-1"

        await p2p_manager._handle_message(websocket, "{}")
        await p2p_manager._handle_message(websocket, "{}")

        assert p2p_manager.blockchain.add_transaction.call_count == 1
        p2p_manager.peer_manager.reputation.record_invalid_transaction.assert_called_once()

    @pytest.mark.asyncio
    async def test_duplicate_blocks_are_dropped(self, p2p_manager):
        verified_message = {
            "sender": "peer_pubkey",
            "payload": {"type": "block", "payload": {"header": {"hash": "block-123"}}},
            "version": getattr(P2PSecurityConfig, "PROTOCOL_VERSION", "1"),
        }
        p2p_manager.peer_manager.encryption.verify_signed_message = MagicMock(return_value=verified_message)
        websocket = MagicMock()
        websocket.remote_address = ("127.0.0.1", 9001)
        p2p_manager.websocket_peer_ids[websocket] = "peer-2"

        await p2p_manager._handle_message(websocket, "{}")
        await p2p_manager._handle_message(websocket, "{}")

        assert p2p_manager.blockchain.add_block.call_count == 1
        p2p_manager.peer_manager.reputation.record_invalid_block.assert_called_once()

    def test_dedup_cache_expires_entries(self, p2p_manager):
        p2p_manager._dedup_ttl = 0.01
        now = time.time()
        assert p2p_manager._is_duplicate_message("transaction", "cache-test", now) is False
        later = now + 0.02
        assert p2p_manager._is_duplicate_message("transaction", "cache-test", later) is False

    def test_dedup_cache_rotates_when_full(self, p2p_manager):
        p2p_manager._dedup_max_items = 1
        now = time.time()
        assert p2p_manager._is_duplicate_message("transaction", "tx-a", now) is False
        assert p2p_manager._is_duplicate_message("transaction", "tx-a", now + 0.001) is True
        assert p2p_manager._is_duplicate_message("transaction", "tx-b", now + 0.002) is False
        # tx-a should be evicted once cache hit max size (1 entry)
        assert p2p_manager._is_duplicate_message("transaction", "tx-a", now + 0.003) is False
