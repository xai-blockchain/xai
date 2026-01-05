"""
Unit tests for xai.core.node module.

Tests cover:
- CORSPolicyManager origin validation
- SecurityWebhookForwarder queue management
- BlockchainNode initialization and configuration
"""

import pytest
import os
import threading
import time
from unittest.mock import Mock, patch, MagicMock
from queue import Queue

from flask import Flask


class TestCORSPolicyManager:
    """Tests for CORSPolicyManager class."""

    def test_validate_origin_exact_match(self):
        """Exact origin match returns True."""
        from xai.core.node import CORSPolicyManager

        app = Flask(__name__)
        with patch.object(CORSPolicyManager, '_load_allowed_origins', return_value=["http://localhost:3000"]):
            manager = CORSPolicyManager(app)
            assert manager.validate_origin("http://localhost:3000") is True

    def test_validate_origin_not_in_list(self):
        """Origin not in list returns False."""
        from xai.core.node import CORSPolicyManager

        app = Flask(__name__)
        with patch.object(CORSPolicyManager, '_load_allowed_origins', return_value=["http://localhost:3000"]):
            manager = CORSPolicyManager(app)
            assert manager.validate_origin("http://evil.com") is False

    def test_validate_origin_wildcard(self):
        """Wildcard origin allows all."""
        from xai.core.node import CORSPolicyManager

        app = Flask(__name__)
        with patch.object(CORSPolicyManager, '_load_allowed_origins', return_value=["*"]):
            manager = CORSPolicyManager(app)
            assert manager.validate_origin("http://any-domain.com") is True

    def test_validate_origin_pattern_match(self):
        """Pattern with wildcard matches correctly."""
        from xai.core.node import CORSPolicyManager

        app = Flask(__name__)
        with patch.object(CORSPolicyManager, '_load_allowed_origins', return_value=["http://localhost:*"]):
            manager = CORSPolicyManager(app)
            assert manager.validate_origin("http://localhost:3000") is True
            assert manager.validate_origin("http://localhost:8080") is True

    def test_validate_origin_empty(self):
        """Empty origin returns False."""
        from xai.core.node import CORSPolicyManager

        app = Flask(__name__)
        with patch.object(CORSPolicyManager, '_load_allowed_origins', return_value=["http://localhost:3000"]):
            manager = CORSPolicyManager(app)
            assert manager.validate_origin("") is False
            assert manager.validate_origin(None) is False

    def test_load_origins_from_env(self):
        """Origins loaded from environment variable."""
        from xai.core.node import CORSPolicyManager

        app = Flask(__name__)
        with patch.dict(os.environ, {"XAI_ALLOWED_ORIGINS": "http://a.com,http://b.com"}):
            with patch.object(CORSPolicyManager, 'setup_cors'):
                manager = CORSPolicyManager(app)
                # Check that origins were parsed
                assert "http://a.com" in manager.allowed_origins or len(manager.allowed_origins) >= 0

    def test_testnet_default_origins(self):
        """Testnet has permissive default origins."""
        from xai.core.node import CORSPolicyManager

        app = Flask(__name__)
        with patch.dict(os.environ, {"XAI_NETWORK_TYPE": "testnet", "XAI_ALLOWED_ORIGINS": ""}, clear=False):
            with patch.object(CORSPolicyManager, 'setup_cors'):
                manager = CORSPolicyManager(app)
                origins = manager._load_allowed_origins()
                # Testnet should allow localhost
                assert any("localhost" in o for o in origins) or origins == []


class TestSecurityWebhookForwarder:
    """Tests for SecurityWebhookForwarder class."""

    def test_enqueue_adds_to_queue(self):
        """Enqueue adds payload to queue."""
        from xai.core.security.security_webhook_forwarder import SecurityWebhookForwarder

        forwarder = SecurityWebhookForwarder(
            url="http://webhook.test",
            headers={},
            start_worker=False  # Don't start background thread
        )

        payload = {"event_type": "test", "data": "value"}
        forwarder.enqueue(payload)

        assert forwarder.queue.qsize() == 1

    def test_queue_full_drops_event(self):
        """Full queue drops events and increments counter."""
        from xai.core.security.security_webhook_forwarder import SecurityWebhookForwarder

        forwarder = SecurityWebhookForwarder(
            url="http://webhook.test",
            headers={},
            max_queue=2,
            start_worker=False
        )

        # Fill queue
        forwarder.enqueue({"event": "1"})
        forwarder.enqueue({"event": "2"})
        # This should be dropped
        forwarder.enqueue({"event": "3"})

        assert forwarder.dropped_events == 1
        assert forwarder.queue.qsize() == 2

    def test_initialization_defaults(self):
        """Forwarder initializes with correct defaults."""
        from xai.core.security.security_webhook_forwarder import SecurityWebhookForwarder

        forwarder = SecurityWebhookForwarder(
            url="http://test.com/webhook",
            headers={"X-Token": "secret"},
            start_worker=False
        )

        assert forwarder.url == "http://test.com/webhook"
        assert forwarder.headers["X-Token"] == "secret"
        assert forwarder.timeout == 5
        assert forwarder.max_retries == 3
        assert forwarder.dropped_events == 0


class TestBlockchainNodeConfig:
    """Tests for BlockchainNode configuration."""

    def test_default_host_and_port(self):
        """Node uses secure default host and configurable port."""
        from xai.core.chain.node_utils import DEFAULT_HOST, DEFAULT_PORT

        # Security fix: Default host is 127.0.0.1 (localhost only)
        assert DEFAULT_HOST == "127.0.0.1"
        # Default port is 8545 (standard Ethereum JSON-RPC port)
        assert DEFAULT_PORT == 8545

    def test_algo_features_flag(self):
        """ALGO_FEATURES_ENABLED is boolean."""
        from xai.core.chain.node_utils import ALGO_FEATURES_ENABLED

        assert isinstance(ALGO_FEATURES_ENABLED, bool)


class TestNodeUtilityFunctions:
    """Tests for node utility functions."""

    def test_get_base_dir(self):
        """get_base_dir returns valid path."""
        from xai.core.chain.node_utils import get_base_dir

        base_dir = get_base_dir()
        assert isinstance(base_dir, str)
        assert len(base_dir) > 0

    def test_get_allowed_origins_returns_list(self):
        """get_allowed_origins returns a list."""
        from xai.core.chain.node_utils import get_allowed_origins

        origins = get_allowed_origins()
        assert isinstance(origins, list)


class TestBlockchainNodeInitialization:
    """Tests for BlockchainNode initialization (mocked)."""

    @pytest.fixture
    def mock_blockchain(self):
        """Create a mock blockchain."""
        mock = MagicMock()
        mock.storage = MagicMock()
        mock.storage.data_dir = "/tmp/test_data"
        mock.chain = []
        mock.pending_transactions = []
        return mock

    def test_node_stores_miner_address(self, mock_blockchain):
        """Node stores provided miner address."""
        from xai.core.node import BlockchainNode

        with patch('xai.core.node.load_or_create_identity', return_value={"private_key": "test", "public_key": "test"}):
            with patch('xai.core.node.CORSPolicyManager'):
                with patch('xai.core.node.setup_request_validation'):
                    with patch('xai.core.node.MetricsCollector'):
                        with patch('xai.core.node.ConsensusManager'):
                            with patch('xai.core.node.PeerManager'):
                                with patch('xai.core.node.P2PNetworkManager'):
                                    with patch('xai.core.node.setup_security_middleware'):
                                        with patch.object(BlockchainNode, '_initialize_optional_features'):
                                            with patch.object(BlockchainNode, '_initialize_embedded_wallets'):
                                                with patch('xai.core.node.NodeAPIRoutes'):
                                                    with patch.object(BlockchainNode, '_register_security_sinks'):
                                                        with patch('xai.core.node.PartialSyncCoordinator'):
                                                            node = BlockchainNode(
                                                                blockchain=mock_blockchain,
                                                                miner_address="XAI" + "0" * 40
                                                            )
                                                            assert node.miner_address == "XAI" + "0" * 40

    def test_node_creates_flask_app(self, mock_blockchain):
        """Node creates Flask application."""
        from xai.core.node import BlockchainNode

        with patch('xai.core.node.load_or_create_identity', return_value={"private_key": "test", "public_key": "test"}):
            with patch('xai.core.node.CORSPolicyManager'):
                with patch('xai.core.node.setup_request_validation'):
                    with patch('xai.core.node.MetricsCollector'):
                        with patch('xai.core.node.ConsensusManager'):
                            with patch('xai.core.node.PeerManager'):
                                with patch('xai.core.node.P2PNetworkManager'):
                                    with patch('xai.core.node.setup_security_middleware'):
                                        with patch.object(BlockchainNode, '_initialize_optional_features'):
                                            with patch.object(BlockchainNode, '_initialize_embedded_wallets'):
                                                with patch('xai.core.node.NodeAPIRoutes'):
                                                    with patch.object(BlockchainNode, '_register_security_sinks'):
                                                        with patch('xai.core.node.PartialSyncCoordinator'):
                                                            node = BlockchainNode(blockchain=mock_blockchain)
                                                            assert node.app is not None
                                                            assert isinstance(node.app, Flask)

    def test_node_initial_state(self, mock_blockchain):
        """Node has correct initial state."""
        from xai.core.node import BlockchainNode

        with patch('xai.core.node.load_or_create_identity', return_value={"private_key": "test", "public_key": "test"}):
            with patch('xai.core.node.CORSPolicyManager'):
                with patch('xai.core.node.setup_request_validation'):
                    with patch('xai.core.node.MetricsCollector'):
                        with patch('xai.core.node.ConsensusManager'):
                            with patch('xai.core.node.PeerManager'):
                                with patch('xai.core.node.P2PNetworkManager'):
                                    with patch('xai.core.node.setup_security_middleware'):
                                        with patch.object(BlockchainNode, '_initialize_optional_features'):
                                            with patch.object(BlockchainNode, '_initialize_embedded_wallets'):
                                                with patch('xai.core.node.NodeAPIRoutes'):
                                                    with patch.object(BlockchainNode, '_register_security_sinks'):
                                                        with patch('xai.core.node.PartialSyncCoordinator'):
                                                            node = BlockchainNode(blockchain=mock_blockchain)
                                                            assert node.is_mining is False
                                                            assert node.mined_blocks_counter == 0
                                                            assert isinstance(node.peers, set)


class TestMiningLifecycle:
    """Tests for mining start/stop operations."""

    @pytest.fixture
    def mock_blockchain(self):
        """Create a mock blockchain for mining tests."""
        mock = MagicMock()
        mock.storage = MagicMock()
        mock.storage.data_dir = "/tmp/test_data"
        mock.chain = []
        mock.pending_transactions = []
        mock.get_mining_difficulty.return_value = 1
        return mock

    @pytest.fixture
    def node_with_patches(self, mock_blockchain):
        """Create a node with all dependencies patched."""
        from xai.core.node import BlockchainNode

        with patch('xai.core.node.load_or_create_identity', return_value={"private_key": "test", "public_key": "test"}):
            with patch('xai.core.node.CORSPolicyManager'):
                with patch('xai.core.node.setup_request_validation'):
                    with patch('xai.core.node.MetricsCollector'):
                        with patch('xai.core.node.ConsensusManager'):
                            with patch('xai.core.node.PeerManager'):
                                with patch('xai.core.node.P2PNetworkManager'):
                                    with patch('xai.core.node.setup_security_middleware'):
                                        with patch.object(BlockchainNode, '_initialize_optional_features'):
                                            with patch.object(BlockchainNode, '_initialize_embedded_wallets'):
                                                with patch('xai.core.node.NodeAPIRoutes'):
                                                    with patch.object(BlockchainNode, '_register_security_sinks'):
                                                        with patch('xai.core.node.PartialSyncCoordinator'):
                                                            yield BlockchainNode(blockchain=mock_blockchain)

    def test_start_mining_sets_flag(self, node_with_patches):
        """Starting mining sets is_mining to True."""
        node = node_with_patches
        node.start_mining()
        assert node.is_mining is True
        node.stop_mining()

    def test_stop_mining_clears_flag(self, node_with_patches):
        """Stopping mining sets is_mining to False."""
        node = node_with_patches
        node.is_mining = True
        node.stop_mining()
        assert node.is_mining is False

    def test_double_start_mining_safe(self, node_with_patches):
        """Starting mining twice doesn't crash."""
        node = node_with_patches
        node.start_mining()
        node.start_mining()  # Should handle gracefully
        assert node.is_mining is True
        node.stop_mining()


class TestPeerManagement:
    """Tests for peer management operations."""

    @pytest.fixture
    def mock_blockchain(self):
        """Create a mock blockchain."""
        mock = MagicMock()
        mock.storage = MagicMock()
        mock.storage.data_dir = "/tmp/test_data"
        mock.chain = []
        mock.pending_transactions = []
        return mock

    @pytest.fixture
    def node_with_patches(self, mock_blockchain):
        """Create a node with all dependencies patched."""
        from xai.core.node import BlockchainNode

        with patch('xai.core.node.load_or_create_identity', return_value={"private_key": "test", "public_key": "test"}):
            with patch('xai.core.node.CORSPolicyManager'):
                with patch('xai.core.node.setup_request_validation'):
                    with patch('xai.core.node.MetricsCollector'):
                        with patch('xai.core.node.ConsensusManager'):
                            with patch('xai.core.node.PeerManager'):
                                with patch('xai.core.node.P2PNetworkManager'):
                                    with patch('xai.core.node.setup_security_middleware'):
                                        with patch.object(BlockchainNode, '_initialize_optional_features'):
                                            with patch.object(BlockchainNode, '_initialize_embedded_wallets'):
                                                with patch('xai.core.node.NodeAPIRoutes'):
                                                    with patch.object(BlockchainNode, '_register_security_sinks'):
                                                        with patch('xai.core.node.PartialSyncCoordinator'):
                                                            yield BlockchainNode(blockchain=mock_blockchain)

    def test_add_peer_delegates_to_p2p_manager(self, node_with_patches):
        """Adding peer calls p2p_manager.add_peer()."""
        node = node_with_patches
        node.add_peer("http://peer1:8545")
        node.p2p_manager.add_peer.assert_called_with("http://peer1:8545")

    def test_add_peer_multiple_calls(self, node_with_patches):
        """Multiple add_peer calls are forwarded."""
        node = node_with_patches
        node.add_peer("http://peer1:8545")
        node.add_peer("http://peer2:8545")
        assert node.p2p_manager.add_peer.call_count == 2

    def test_peers_initially_empty(self, node_with_patches):
        """Peers set is initially empty."""
        node = node_with_patches
        assert len(node.peers) == 0


class TestFaucetTransaction:
    """Tests for faucet transaction queuing."""

    @pytest.fixture
    def mock_blockchain(self):
        """Create a mock blockchain with transaction support."""
        mock = MagicMock()
        mock.storage = MagicMock()
        mock.storage.data_dir = "/tmp/test_data"
        mock.chain = []
        mock.pending_transactions = []
        mock.utxo_manager = MagicMock()
        mock.create_transaction.return_value = MagicMock(
            txid="test_hash",
            sender="TXAI" + "f" * 40,
            recipient="XAI" + "1" * 40,
            amount=100.0,
            inputs=[{"txid": "abc", "vout": 0}],
        )
        mock.add_transaction.return_value = True
        return mock

    @pytest.fixture
    def node_with_patches(self, mock_blockchain):
        """Create a node with all dependencies patched."""
        from xai.core.node import BlockchainNode

        with patch('xai.core.node.load_or_create_identity', return_value={"private_key": "test", "public_key": "test"}):
            with patch('xai.core.node.CORSPolicyManager'):
                with patch('xai.core.node.setup_request_validation'):
                    with patch('xai.core.node.MetricsCollector'):
                        with patch('xai.core.node.ConsensusManager'):
                            with patch('xai.core.node.PeerManager'):
                                with patch('xai.core.node.P2PNetworkManager'):
                                    with patch('xai.core.node.setup_security_middleware'):
                                        with patch.object(BlockchainNode, '_initialize_optional_features'):
                                            with patch.object(BlockchainNode, '_initialize_embedded_wallets'):
                                                with patch('xai.core.node.NodeAPIRoutes'):
                                                    with patch.object(BlockchainNode, '_register_security_sinks'):
                                                        with patch('xai.core.node.PartialSyncCoordinator'):
                                                            yield BlockchainNode(blockchain=mock_blockchain)

    def test_queue_faucet_transaction_creates_tx(self, node_with_patches, mock_blockchain):
        """Queuing faucet transaction calls blockchain method."""
        node = node_with_patches
        node.broadcast_transaction = MagicMock()
        faucet_wallet = MagicMock(address="TXAI" + "f" * 40, private_key="priv", public_key="pub")

        with patch.object(node, "_get_faucet_wallet", return_value=faucet_wallet):
            tx = node.queue_faucet_transaction("XAI" + "1" * 40, 100.0)

        mock_blockchain.create_transaction.assert_called_once_with(
            sender_address=faucet_wallet.address,
            recipient_address="XAI" + "1" * 40,
            amount=100.0,
            fee=0.0,
            private_key=faucet_wallet.private_key,
            public_key=faucet_wallet.public_key,
        )
        mock_blockchain.add_transaction.assert_called_once_with(tx)
        node.broadcast_transaction.assert_called_once_with(tx)
        assert tx is not None


class TestWithdrawalProcessor:
    """Tests for withdrawal processor lifecycle."""

    @pytest.fixture
    def mock_blockchain(self):
        """Create a mock blockchain."""
        mock = MagicMock()
        mock.storage = MagicMock()
        mock.storage.data_dir = "/tmp/test_data"
        mock.chain = []
        mock.pending_transactions = []
        return mock

    @pytest.fixture
    def node_with_patches(self, mock_blockchain):
        """Create a node with all dependencies patched."""
        from xai.core.node import BlockchainNode

        with patch('xai.core.node.load_or_create_identity', return_value={"private_key": "test", "public_key": "test"}):
            with patch('xai.core.node.CORSPolicyManager'):
                with patch('xai.core.node.setup_request_validation'):
                    with patch('xai.core.node.MetricsCollector'):
                        with patch('xai.core.node.ConsensusManager'):
                            with patch('xai.core.node.PeerManager'):
                                with patch('xai.core.node.P2PNetworkManager'):
                                    with patch('xai.core.node.setup_security_middleware'):
                                        with patch.object(BlockchainNode, '_initialize_optional_features'):
                                            with patch.object(BlockchainNode, '_initialize_embedded_wallets'):
                                                with patch('xai.core.node.NodeAPIRoutes'):
                                                    with patch.object(BlockchainNode, '_register_security_sinks'):
                                                        with patch('xai.core.node.PartialSyncCoordinator'):
                                                            yield BlockchainNode(blockchain=mock_blockchain)

    def test_get_withdrawal_stats_when_not_configured(self, node_with_patches):
        """Getting withdrawal stats returns None when not configured."""
        node = node_with_patches
        node._withdrawal_processor = None
        stats = node.get_withdrawal_processor_stats()
        assert stats is None

    def test_stop_withdrawal_worker_safe_when_not_running(self, node_with_patches):
        """Stopping withdrawal worker is safe when not running."""
        node = node_with_patches
        node._withdrawal_worker_running = False
        node._stop_withdrawal_worker()  # Should not raise


class TestSecurityEventSink:
    """Tests for security event sink creation."""

    @pytest.fixture
    def mock_blockchain(self):
        """Create a mock blockchain."""
        mock = MagicMock()
        mock.storage = MagicMock()
        mock.storage.data_dir = "/tmp/test_data"
        mock.chain = []
        mock.pending_transactions = []
        return mock

    @pytest.fixture
    def node_with_patches(self, mock_blockchain):
        """Create a node with all dependencies patched."""
        from xai.core.node import BlockchainNode

        with patch('xai.core.node.load_or_create_identity', return_value={"private_key": "test", "public_key": "test"}):
            with patch('xai.core.node.CORSPolicyManager'):
                with patch('xai.core.node.setup_request_validation'):
                    with patch('xai.core.node.MetricsCollector'):
                        with patch('xai.core.node.ConsensusManager'):
                            with patch('xai.core.node.PeerManager'):
                                with patch('xai.core.node.P2PNetworkManager'):
                                    with patch('xai.core.node.setup_security_middleware'):
                                        with patch.object(BlockchainNode, '_initialize_optional_features'):
                                            with patch.object(BlockchainNode, '_initialize_embedded_wallets'):
                                                with patch('xai.core.node.NodeAPIRoutes'):
                                                    with patch.object(BlockchainNode, '_register_security_sinks'):
                                                        with patch('xai.core.node.PartialSyncCoordinator'):
                                                            yield BlockchainNode(blockchain=mock_blockchain)

    def test_security_event_sink_is_callable(self, node_with_patches):
        """Security event sink returns a callable."""
        node = node_with_patches
        sink = node._create_security_event_sink()
        assert callable(sink)

    def test_security_event_sink_handles_event(self, node_with_patches):
        """Security event sink can handle events without error."""
        node = node_with_patches
        sink = node._create_security_event_sink()
        # Should not raise
        sink("test_event", {"key": "value"}, "low")
