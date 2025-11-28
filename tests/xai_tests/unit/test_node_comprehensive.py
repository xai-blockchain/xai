"""
Comprehensive unit tests for xai.core.node module.
Tests BlockchainNode class covering all functionality.

Target: 90%+ coverage for node.py
"""

import pytest
import time
import threading
from unittest.mock import Mock, patch, MagicMock, call
from xai.core.node import BlockchainNode
from xai.core.blockchain import Blockchain, Transaction, Block
from xai.core.node_utils import DEFAULT_HOST
from xai.core.config import Config


@pytest.fixture
def embedded_wallet_mocks():
    """Patch wallet/account abstraction dependencies."""
    with patch('xai.core.node.WalletManager') as mock_wallet_cls, \
         patch('xai.core.node.AccountAbstractionManager') as mock_account_cls:
        wallet_instance = Mock(name='WalletManagerInstance')
        account_instance = Mock(name='AccountAbstractionInstance')
        mock_wallet_cls.return_value = wallet_instance
        mock_account_cls.return_value = account_instance
        yield {
            'wallet_manager_cls': mock_wallet_cls,
            'wallet_instance': wallet_instance,
            'account_manager_cls': mock_account_cls,
            'account_instance': account_instance,
        }


@pytest.fixture(autouse=True)
def auto_patch_embedded_wallets(embedded_wallet_mocks):
    """Automatically patch embedded wallet dependencies for every test."""
    yield


@pytest.fixture
def mock_blockchain():
    """Create a mock blockchain instance"""
    blockchain = Mock(spec=Blockchain)
    blockchain.chain = []
    blockchain.pending_transactions = []
    blockchain.difficulty = 4
    blockchain.block_reward = 50.0
    blockchain.get_stats = Mock(return_value={
        'chain_length': 1,
        'pending_transactions': 0,
        'difficulty': 4
    })
    blockchain.get_balance = Mock(return_value=100.0)
    blockchain.get_transaction_history = Mock(return_value=[])
    blockchain.deserialize_chain = Mock(return_value=[Mock(), Mock(), Mock(), Mock()])
    blockchain.replace_chain = Mock(return_value=True)
    return blockchain


@pytest.fixture
def node(mock_blockchain, embedded_wallet_mocks):
    """Create a blockchain node instance for testing"""
    with patch('xai.core.node.MetricsCollector'), \
         patch('xai.core.node.SecurityValidator'), \
         patch('xai.core.node.ConsensusManager') as MockConsensusManager, \
         patch('xai.core.node.setup_security_middleware'), \
         patch('xai.core.node.NodeAPIRoutes'):
        mock_consensus = MockConsensusManager.return_value
        mock_consensus.validate_chain.return_value = (True, None)
        node = BlockchainNode(
            blockchain=mock_blockchain,
            host='127.0.0.1',
            port=5555,
            miner_address='test_miner_address'
        )
        return node


class TestNodeInitialization:
    """Test node initialization"""

    def test_node_init_with_blockchain(self, mock_blockchain):
        """Test node initializes with provided blockchain"""
        with patch('xai.core.node.MetricsCollector'), \
             patch('xai.core.node.SecurityValidator'), \
             patch('xai.core.node.ConsensusManager'), \
             patch('xai.core.node.setup_security_middleware'), \
             patch('xai.core.node.NodeAPIRoutes'):
            node = BlockchainNode(blockchain=mock_blockchain, host='0.0.0.0', port=8545)
            assert node.blockchain is mock_blockchain
            assert node.host == '0.0.0.0'
            assert node.port == 8545

    def test_node_init_without_blockchain(self):
        """Test node creates new blockchain if none provided"""
        with patch('xai.core.node.Blockchain') as MockBlockchain, \
             patch('xai.core.node.MetricsCollector'), \
             patch('xai.core.node.SecurityValidator'), \
             patch('xai.core.node.ConsensusManager'), \
             patch('xai.core.node.setup_security_middleware'), \
             patch('xai.core.node.NodeAPIRoutes'):
            node = BlockchainNode()
            MockBlockchain.assert_called_once()

    def test_node_init_default_parameters(self):
        """Test node initialization with default parameters"""
        with patch('xai.core.node.Blockchain'), \
             patch('xai.core.node.MetricsCollector'), \
             patch('xai.core.node.SecurityValidator'), \
             patch('xai.core.node.ConsensusManager'), \
             patch('xai.core.node.setup_security_middleware'), \
             patch('xai.core.node.NodeAPIRoutes'):
            node = BlockchainNode()
            assert node.host == DEFAULT_HOST
            assert node.port == 8545
            assert node.is_mining is False
            assert len(node.peers) == 0

    def test_node_init_custom_miner_address(self, mock_blockchain):
        """Test node initialization with custom miner address"""
        with patch('xai.core.node.MetricsCollector'), \
             patch('xai.core.node.SecurityValidator'), \
             patch('xai.core.node.ConsensusManager'), \
             patch('xai.core.node.setup_security_middleware'), \
             patch('xai.core.node.NodeAPIRoutes'):
            custom_address = 'custom_miner_xyz'
            node = BlockchainNode(blockchain=mock_blockchain, miner_address=custom_address)
            assert node.miner_address == custom_address

    def test_node_init_flask_app(self, node):
        """Test Flask app is initialized"""
        assert node.app is not None
        assert hasattr(node.app, 'secret_key')

    def test_node_init_managers(self, node):
        """Test all managers are initialized"""
        assert hasattr(node, 'metrics_collector')
        assert hasattr(node, 'consensus_manager')
        assert hasattr(node, 'validator')


class TestOptionalFeatures:
    """Test optional feature initialization"""

    def test_optional_features_disabled(self, node):
        """Test optional features when disabled"""
        assert node.fee_optimizer is None
        assert node.fraud_detector is None

    @patch('xai.core.node.ALGO_FEATURES_ENABLED', True)
    def test_optional_features_enabled(self, mock_blockchain):
        """Test optional features when enabled"""
        with patch('xai.core.node.MetricsCollector'), \
             patch('xai.core.node.SecurityValidator'), \
             patch('xai.core.node.ConsensusManager'), \
             patch('xai.core.node.setup_security_middleware'), \
             patch('xai.core.node.NodeAPIRoutes'), \
             patch('xai.core.algo_fee_optimizer.FeeOptimizer') as MockFeeOptimizer, \
             patch('xai.core.fraud_detection.FraudDetector') as MockFraudDetector:
            node = BlockchainNode(blockchain=mock_blockchain)
            MockFeeOptimizer.assert_called_once()
            MockFraudDetector.assert_called_once()


class TestEmbeddedWalletInitialization:
    """Test embedded wallet/account abstraction initialization."""

    def test_embedded_wallet_managers_initialized(self, node, embedded_wallet_mocks):
        """Node should initialize wallet and account abstraction managers."""
        assert node.account_abstraction is embedded_wallet_mocks['account_instance']
        embedded_wallet_mocks['wallet_manager_cls'].assert_called_once()
        embedded_wallet_mocks['account_manager_cls'].assert_called_once_with(
            wallet_manager=embedded_wallet_mocks['wallet_instance'],
            storage_path=getattr(Config, 'EMBEDDED_WALLET_DIR', None),
        )

    def test_embedded_wallet_init_failure(self, mock_blockchain, embedded_wallet_mocks):
        """Node should disable embedded wallets gracefully if initialization fails."""
        embedded_wallet_mocks['account_manager_cls'].side_effect = RuntimeError('init failed')
        with patch('xai.core.node.MetricsCollector'), \
             patch('xai.core.node.SecurityValidator'), \
             patch('xai.core.node.ConsensusManager') as MockConsensusManager, \
             patch('xai.core.node.setup_security_middleware'), \
             patch('xai.core.node.NodeAPIRoutes'):
            mock_consensus = MockConsensusManager.return_value
            mock_consensus.validate_chain.return_value = (True, None)
            test_node = BlockchainNode(blockchain=mock_blockchain)

        assert test_node.account_abstraction is None


class TestMiningOperations:
    """Test mining functionality"""

    def test_start_mining(self, node):
        """Test starting mining"""
        assert node.is_mining is False
        node.start_mining()
        assert node.is_mining is True
        assert node.mining_thread is not None
        assert node.mining_thread.daemon is True
        node.stop_mining()

    def test_start_mining_already_active(self, node, capsys):
        """Test starting mining when already active"""
        node.start_mining()
        node.start_mining()  # Try starting again
        captured = capsys.readouterr()
        assert '[WARN] Mining already active' in captured.out
        node.stop_mining()

    def test_stop_mining(self, node):
        """Test stopping mining"""
        node.start_mining()
        time.sleep(0.1)  # Let thread start
        node.stop_mining()
        assert node.is_mining is False

    def test_stop_mining_not_active(self, node, capsys):
        """Test stopping mining when not active"""
        node.stop_mining()
        captured = capsys.readouterr()
        assert '[WARN] Mining not active' in captured.out

    def test_mine_continuously_with_transactions(self, node):
        """Test continuous mining with pending transactions"""
        # Setup mock
        mock_block = Mock(spec=Block)
        mock_block.index = 1
        mock_block.hash = '0000abc123'
        node.blockchain.mine_pending_transactions = Mock(return_value=mock_block)

        # Create a transaction
        mock_tx = Mock(spec=Transaction)
        node.blockchain.pending_transactions = [mock_tx]

        # Start mining
        node.start_mining()
        time.sleep(0.2)  # Let it mine
        node.stop_mining()

        # Verify mining was called
        assert node.blockchain.mine_pending_transactions.called

    def test_mine_continuously_no_transactions(self, node):
        """Test continuous mining with no transactions"""
        node.blockchain.pending_transactions = []
        node.blockchain.mine_pending_transactions = Mock()

        node.start_mining()
        time.sleep(0.2)
        node.stop_mining()

        # Should not mine when no transactions
        assert not node.blockchain.mine_pending_transactions.called

    def test_mine_continuously_handles_errors(self, node, capsys):
        """Test mining continues despite errors"""
        node.blockchain.pending_transactions = [Mock()]
        node.blockchain.mine_pending_transactions = Mock(side_effect=Exception('Mining error'))

        node.start_mining()
        time.sleep(0.2)
        node.stop_mining()

        captured = capsys.readouterr()
        assert '[ERROR] Mining error' in captured.out


class TestPeerManagement:
    """Test P2P peer management"""

    def test_add_peer(self, node):
        """Test adding a peer"""
        peer_url = 'http://peer1.local:5000'
        node.add_peer(peer_url)
        assert peer_url in node.peers
        assert len(node.peers) == 1

    def test_add_duplicate_peer(self, node):
        """Test adding duplicate peer only adds once"""
        peer_url = 'http://peer1.local:5000'
        node.add_peer(peer_url)
        node.add_peer(peer_url)
        assert len(node.peers) == 1

    def test_add_multiple_peers(self, node):
        """Test adding multiple peers"""
        peers = [
            'http://peer1.local:5000',
            'http://peer2.local:5000',
            'http://peer3.local:5000'
        ]
        for peer in peers:
            node.add_peer(peer)
        assert len(node.peers) == 3
        assert all(peer in node.peers for peer in peers)


class TestTransactionBroadcasting:
    """Test transaction broadcasting"""

    @patch('xai.core.node_p2p.requests.post')
    def test_broadcast_transaction_success(self, mock_post, node):
        """Test successful transaction broadcast"""
        node.add_peer('http://peer1.local:5000')
        node.add_peer('http://peer2.local:5000')

        mock_tx = Mock(spec=Transaction)
        mock_tx.to_dict = Mock(return_value={'sender': 'Alice', 'recipient': 'Bob', 'amount': 10})

        node.broadcast_transaction(mock_tx)

        assert mock_post.call_count == 2
        mock_post.assert_any_call(
            'http://peer1.local:5000/transaction/receive',
            json={'sender': 'Alice', 'recipient': 'Bob', 'amount': 10},
            timeout=2
        )

    @patch('xai.core.node_p2p.requests.post')
    def test_broadcast_transaction_handles_failures(self, mock_post, node):
        """Test broadcast continues despite peer failures"""
        node.add_peer('http://peer1.local:5000')
        node.add_peer('http://peer2.local:5000')

        # First peer fails, second succeeds
        mock_post.side_effect = [Exception('Connection error'), Mock()]

        mock_tx = Mock(spec=Transaction)
        mock_tx.to_dict = Mock(return_value={})

        # Should not raise exception
        node.broadcast_transaction(mock_tx)
        assert mock_post.call_count == 2


class TestBlockBroadcasting:
    """Test block broadcasting"""

    @patch('xai.core.node_p2p.requests.post')
    def test_broadcast_block_success(self, mock_post, node):
        """Test successful block broadcast"""
        node.add_peer('http://peer1.local:5000')

        mock_block = Mock(spec=Block)
        mock_block.to_dict = Mock(return_value={'index': 1, 'hash': 'abc123'})

        node.broadcast_block(mock_block)

        mock_post.assert_called_once_with(
            'http://peer1.local:5000/block/receive',
            json={'index': 1, 'hash': 'abc123'},
            timeout=2
        )

    @patch('xai.core.node_p2p.requests.post')
    def test_broadcast_block_handles_failures(self, mock_post, node):
        """Test broadcast handles peer failures"""
        node.add_peer('http://peer1.local:5000')
        mock_post.side_effect = Exception('Network error')

        mock_block = Mock(spec=Block)
        mock_block.to_dict = Mock(return_value={})

        # Should not raise exception
        node.broadcast_block(mock_block)


class TestNetworkSync:
    """Test blockchain synchronization"""

    @patch('xai.core.node_p2p.requests.get')
    def test_sync_with_network_no_peers(self, mock_get, node):
        """Test sync with no peers"""
        result = node.sync_with_network()
        assert result is False
        mock_get.assert_not_called()

    @patch('xai.core.node_p2p.requests.get')
    def test_sync_with_network_shorter_chain(self, mock_get, node):
        """Test sync when peer has shorter chain"""
        node.add_peer('http://peer1.local:5000')
        node.blockchain.chain = [Mock(), Mock(), Mock()]  # 3 blocks

        # Peer response with shorter chain
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = Mock(return_value={'total': 2, 'blocks': []})
        mock_get.return_value = mock_response

        result = node.sync_with_network()
        assert result is False

    @patch('xai.core.node_p2p.requests.get')
    def test_sync_with_network_longer_chain(self, mock_get, node):
        """Test sync when peer has longer chain"""
        node.add_peer('http://peer1.local:5000')
        node.blockchain.chain = [Mock()]  # 1 block

        # First response: chain length
        response1 = Mock()
        response1.status_code = 200
        response1.json = Mock(return_value={'total': 3})

        # Second response: full chain
        response2 = Mock()
        response2.status_code = 200
        response2.json = Mock(return_value={
            'blocks': [
                {'index': 0, 'hash': 'genesis'},
                {'index': 1, 'hash': 'block1'},
                {'index': 2, 'hash': 'block2'}
            ]
        })

        mock_get.side_effect = [response1, response2]

        result = node.sync_with_network()
        assert result is True

    @patch('xai.core.node_p2p.requests.get')
    def test_sync_handles_peer_errors(self, mock_get, node):
        """Test sync handles peer connection errors"""
        node.add_peer('http://peer1.local:5000')
        node.add_peer('http://peer2.local:5000')

        mock_get.side_effect = Exception('Connection timeout')

        result = node.sync_with_network()
        assert result is False


class TestOrderMatching:
    """Test exchange order matching"""

    def test_match_orders_buy_order(self, node):
        """Test matching a buy order"""
        # Setup exchange wallet manager
        node.exchange_wallet_manager = Mock()
        node.exchange_wallet_manager.execute_trade = Mock(return_value={'success': True})
        node.exchange_wallet_manager.unlock_from_order = Mock()

        new_order = {
            'order_type': 'buy',
            'price': 0.05,
            'amount': 100,
            'remaining': 100,
            'address': 'buyer_address',
            'base_currency': 'AXN',
            'quote_currency': 'USD'
        }

        all_orders = {
            'buy': [],
            'sell': [{
                'order_type': 'sell',
                'price': 0.04,  # Lower price, should match
                'amount': 50,
                'remaining': 50,
                'status': 'open',
                'address': 'seller_address',
                'base_currency': 'AXN',
                'quote_currency': 'USD'
            }]
        }

        with patch('xai.core.node.get_base_dir', return_value='/tmp/test'), \
             patch('xai.core.node.os.path.exists', return_value=False), \
             patch('xai.core.node.open', create=True) as mock_open, \
             patch('xai.core.node.json.dump'):
            result = node._match_orders(new_order, all_orders)
            assert result is True
            assert new_order['remaining'] == 50  # 100 - 50 matched

    def test_match_orders_no_matches(self, node):
        """Test when no matching orders exist"""
        new_order = {
            'order_type': 'buy',
            'price': 0.03,
            'amount': 100,
            'remaining': 100,
            'address': 'buyer_address'
        }

        all_orders = {
            'buy': [],
            'sell': [{
                'price': 0.05,  # Too expensive
                'remaining': 50,
                'status': 'open'
            }]
        }

        result = node._match_orders(new_order, all_orders)
        assert result is False

    def test_match_orders_handles_errors(self, node):
        """Test order matching handles errors gracefully"""
        new_order = {
            'order_type': 'buy',
            'price': 0.05,
            'amount': 100,
            'remaining': 100
        }

        all_orders = {
            'buy': [],
            'sell': []
        }

        # Should handle missing fields gracefully
        result = node._match_orders(new_order, all_orders)
        assert result is False


class TestNodeControl:
    """Test node startup and control"""

    def test_run_sets_start_time(self, node):
        """Test run() sets start time"""
        with patch.object(node.app, 'run'):
            with patch.object(node, 'start_mining'):
                # Run in a thread to avoid blocking
                thread = threading.Thread(target=lambda: node.run(debug=False))
                thread.daemon = True
                thread.start()
                time.sleep(0.1)

                assert node.start_time > 0

    def test_run_starts_mining(self, node):
        """Test run() starts auto-mining"""
        with patch.object(node.app, 'run'):
            with patch.object(node, 'start_mining') as mock_start:
                thread = threading.Thread(target=lambda: node.run(debug=False))
                thread.daemon = True
                thread.start()
                time.sleep(0.1)

                mock_start.assert_called_once()


class TestNodeIntegration:
    """Integration tests for node functionality"""

    def test_full_lifecycle(self, mock_blockchain):
        """Test complete node lifecycle"""
        with patch('xai.core.node.MetricsCollector'), \
             patch('xai.core.node.SecurityValidator'), \
             patch('xai.core.node.ConsensusManager'), \
             patch('xai.core.node.setup_security_middleware'), \
             patch('xai.core.node.NodeAPIRoutes'):

            # Create node
            node = BlockchainNode(blockchain=mock_blockchain)
            assert node is not None

            # Add peers
            node.add_peer('http://peer1:5000')
            assert len(node.peers) == 1

            # Start mining
            node.start_mining()
            assert node.is_mining is True

            # Stop mining
            time.sleep(0.1)
            node.stop_mining()
            assert node.is_mining is False

    def test_concurrent_operations(self, node):
        """Test node handles concurrent operations"""
        # Add peers concurrently
        def add_peers():
            for i in range(10):
                node.add_peer(f'http://peer{i}:5000')

        threads = [threading.Thread(target=add_peers) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should have 10 unique peers
        assert len(node.peers) == 10
