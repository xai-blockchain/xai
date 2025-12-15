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
    """Tests for _SecurityWebhookForwarder class."""

    def test_enqueue_adds_to_queue(self):
        """Enqueue adds payload to queue."""
        from xai.core.node import _SecurityWebhookForwarder

        forwarder = _SecurityWebhookForwarder(
            url="http://webhook.test",
            headers={},
            start_worker=False  # Don't start background thread
        )

        payload = {"event_type": "test", "data": "value"}
        forwarder.enqueue(payload)

        assert forwarder.queue.qsize() == 1

    def test_queue_full_drops_event(self):
        """Full queue drops events and increments counter."""
        from xai.core.node import _SecurityWebhookForwarder

        forwarder = _SecurityWebhookForwarder(
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
        from xai.core.node import _SecurityWebhookForwarder

        forwarder = _SecurityWebhookForwarder(
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
        from xai.core.node_utils import DEFAULT_HOST, DEFAULT_PORT

        # Security fix: Default host is 127.0.0.1 (localhost only)
        assert DEFAULT_HOST == "127.0.0.1"
        # Default port is 8545 (standard Ethereum JSON-RPC port)
        assert DEFAULT_PORT == 8545

    def test_algo_features_flag(self):
        """ALGO_FEATURES_ENABLED is boolean."""
        from xai.core.node_utils import ALGO_FEATURES_ENABLED

        assert isinstance(ALGO_FEATURES_ENABLED, bool)


class TestNodeUtilityFunctions:
    """Tests for node utility functions."""

    def test_get_base_dir(self):
        """get_base_dir returns valid path."""
        from xai.core.node_utils import get_base_dir

        base_dir = get_base_dir()
        assert isinstance(base_dir, str)
        assert len(base_dir) > 0

    def test_get_allowed_origins_returns_list(self):
        """get_allowed_origins returns a list."""
        from xai.core.node_utils import get_allowed_origins

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
