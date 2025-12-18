"""
Tests for sync progress tracking in light client and checkpoint sync.

Tests the complete sync progress API including:
- Light client header sync progress
- Checkpoint sync progress tracking
- API endpoints for sync status
- WebSocket events for sync progress
"""

import time
import json
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch
import pytest

from xai.core.light_client_service import LightClientService, SyncProgress
from xai.core.checkpoint_sync import CheckpointSyncManager
from xai.core.checkpoint_payload import CheckpointPayload


class TestLightClientSyncProgress:
    """Test suite for light client sync progress tracking."""

    def test_sync_progress_initialization(self):
        """Test that sync progress tracking initializes correctly."""
        blockchain = Mock()
        blockchain.chain = [Mock(index=i) for i in range(10)]

        service = LightClientService(blockchain)

        # Should initialize with default values
        assert service._sync_start_time is None
        assert service._sync_start_height == 0
        assert service._last_height == 0
        assert service._target_height == 0
        assert len(service._sync_history) == 0

    def test_start_sync(self):
        """Test starting sync progress tracking."""
        blockchain = Mock()
        blockchain.chain = [Mock(index=i) for i in range(10)]

        service = LightClientService(blockchain)
        service.start_sync(target_height=100)

        # Verify sync tracking started
        assert service._sync_start_time is not None
        assert service._sync_start_height == 9  # len(chain) - 1
        assert service._target_height == 100
        assert len(service._sync_history) == 1

    def test_update_sync_progress(self):
        """Test updating sync progress as blocks are received."""
        blockchain = Mock()
        blockchain.chain = [Mock(index=i) for i in range(10)]

        service = LightClientService(blockchain)
        service.start_sync(target_height=100)

        # Simulate receiving new blocks
        service.update_sync_progress(20)
        assert service._last_height == 20
        assert len(service._sync_history) == 2

        service.update_sync_progress(30)
        assert service._last_height == 30
        assert len(service._sync_history) == 3

        # Should not add duplicate entries
        service.update_sync_progress(30)
        assert len(service._sync_history) == 3

    def test_get_sync_progress_syncing(self):
        """Test getting sync progress while actively syncing."""
        blockchain = Mock()
        blockchain.chain = [Mock(index=i) for i in range(50)]

        service = LightClientService(blockchain)
        service.start_sync(target_height=100)

        # Simulate some progress
        service.update_sync_progress(50)
        time.sleep(0.1)
        service.update_sync_progress(60)

        progress = service.get_sync_progress()

        assert isinstance(progress, SyncProgress)
        assert progress.current_height == 49  # len(chain) - 1
        assert progress.target_height == 100
        assert 0 <= progress.sync_percentage <= 100
        assert progress.sync_state in ["syncing", "idle"]
        assert progress.headers_per_second >= 0
        assert isinstance(progress.started_at, datetime)

    def test_get_sync_progress_synced(self):
        """Test getting sync progress when fully synced."""
        blockchain = Mock()
        blockchain.chain = [Mock(index=i) for i in range(100)]
        blockchain.checkpoint_manager = None

        service = LightClientService(blockchain)
        service.start_sync(target_height=100)

        # Simulate reaching target
        service._sync_start_height = 0
        service._last_height = 99
        service.update_sync_progress(99)

        progress = service.get_sync_progress()

        assert progress.current_height == 99
        assert progress.target_height == 100
        # Should be very close to 100% or at synced state
        assert progress.sync_state == "synced" or progress.sync_percentage >= 99.0

    def test_get_sync_progress_stalled(self):
        """Test detecting stalled sync state."""
        blockchain = Mock()
        blockchain.chain = [Mock(index=i) for i in range(50)]
        blockchain.checkpoint_manager = None

        service = LightClientService(blockchain)
        service.start_sync(target_height=100)
        service._last_height = 50
        service.update_sync_progress(50)

        # Simulate stall by setting last update time far in past
        service._last_height_update_time = time.time() - 60  # 60 seconds ago
        # Clear history to ensure low headers_per_second
        service._sync_history = [(time.time() - 60, 50)]

        progress = service.get_sync_progress()

        # Should detect stalled state
        assert progress.sync_state in ["stalled", "idle"]
        assert progress.headers_per_second < 0.1

    def test_calculate_headers_per_second(self):
        """Test headers per second calculation."""
        blockchain = Mock()
        blockchain.chain = [Mock(index=i) for i in range(10)]

        service = LightClientService(blockchain)
        service.start_sync(target_height=100)

        # Simulate sync progress
        start_time = time.time()
        service._sync_history = [
            (start_time, 10),
            (start_time + 1, 20),
            (start_time + 2, 30),
        ]

        headers_per_sec = service._calculate_headers_per_second()

        # Should calculate approximately 10 headers/sec
        assert 8.0 <= headers_per_sec <= 12.0

    def test_determine_sync_state(self):
        """Test sync state determination logic."""
        blockchain = Mock()
        blockchain.chain = []

        service = LightClientService(blockchain)
        service._target_height = 100

        # Test synced state
        state = service._determine_sync_state(100, 100.0, 5.0)
        assert state == "synced"

        # Test syncing state (not at target, has positive speed)
        service._target_height = 100
        state = service._determine_sync_state(50, 50.0, 10.0)
        assert state == "syncing"

        # Test stalled state
        service._last_height_update_time = time.time() - 60
        state = service._determine_sync_state(50, 50.0, 0.0)
        assert state == "stalled"

        # Test idle state
        service._last_height_update_time = time.time()
        state = service._determine_sync_state(50, 50.0, 0.0)
        assert state == "idle"

    def test_sync_progress_to_dict(self):
        """Test SyncProgress serialization to dictionary."""
        progress = SyncProgress(
            current_height=50,
            target_height=100,
            sync_percentage=50.0,
            estimated_time_remaining=60,
            sync_state="syncing",
            headers_per_second=10.5,
            started_at=datetime(2024, 1, 1, 12, 0, 0),
            checkpoint_sync_enabled=True,
            checkpoint_height=30,
        )

        data = progress.to_dict()

        assert data["current_height"] == 50
        assert data["target_height"] == 100
        assert data["sync_percentage"] == 50.0
        assert data["estimated_time_remaining"] == 60
        assert data["sync_state"] == "syncing"
        assert data["headers_per_second"] == 10.5
        assert data["started_at"] == "2024-01-01T12:00:00"
        assert data["checkpoint_sync_enabled"] is True
        assert data["checkpoint_height"] == 30

    def test_checkpoint_sync_info_included(self):
        """Test that checkpoint sync info is included in progress."""
        blockchain = Mock()
        blockchain.chain = [Mock(index=i) for i in range(10)]

        # Mock checkpoint manager
        checkpoint_manager = Mock()
        checkpoint_manager.latest_checkpoint_height = 50
        blockchain.checkpoint_manager = checkpoint_manager

        service = LightClientService(blockchain)
        service.start_sync(target_height=100)

        progress = service.get_sync_progress()

        assert progress.checkpoint_sync_enabled is True
        assert progress.checkpoint_height == 50


class TestCheckpointSyncProgress:
    """Test suite for checkpoint sync progress tracking."""

    @pytest.fixture
    def mock_blockchain(self):
        """Create properly mocked blockchain for checkpoint sync tests."""
        blockchain = Mock()
        blockchain.checkpoint_manager = Mock()
        blockchain.base_dir = "/tmp/test"

        # Mock config with proper return values
        config = Mock()
        config.CHECKPOINT_QUORUM = 3
        config.TRUSTED_CHECKPOINT_PUBKEYS = []
        config.CHECKPOINT_MIN_PEERS = 2
        config.CHECKPOINT_REQUEST_RATE_SECONDS = 30
        blockchain.config = config

        return blockchain

    def test_checkpoint_sync_progress_initialization(self, mock_blockchain):
        """Test checkpoint sync progress initializes correctly."""
        sync_manager = CheckpointSyncManager(mock_blockchain)

        progress = sync_manager.get_checkpoint_sync_progress()

        assert progress["stage"] == "idle"
        assert progress["bytes_downloaded"] == 0
        assert progress["total_bytes"] == 0
        assert progress["download_percentage"] == 0.0
        assert progress["verification_percentage"] == 0.0
        assert progress["application_percentage"] == 0.0

    def test_progress_callback(self, mock_blockchain):
        """Test that progress callbacks are invoked."""
        sync_manager = CheckpointSyncManager(mock_blockchain)

        callback_data = []

        def progress_callback(data):
            callback_data.append(data)

        sync_manager.set_progress_callback(progress_callback)

        # Update progress
        sync_manager._update_progress({"stage": "downloading", "bytes_downloaded": 1000})

        assert len(callback_data) == 1
        assert callback_data[0]["stage"] == "downloading"
        assert callback_data[0]["bytes_downloaded"] == 1000

    def test_progress_tracking_during_sync(self, mock_blockchain):
        """Test progress tracking during checkpoint sync."""
        sync_manager = CheckpointSyncManager(mock_blockchain)

        # Mock the fetch/validate/apply process
        with patch.object(sync_manager, 'get_best_checkpoint_metadata', return_value=None):
            with patch.object(sync_manager, 'request_checkpoint_from_peers', return_value=None):
                result = sync_manager.fetch_validate_apply()

        # Should update progress even on failure
        progress = sync_manager.get_checkpoint_sync_progress()
        # Progress should be reset on failure
        assert progress["stage"] == "idle"

    def test_progress_reset_on_failure(self, mock_blockchain):
        """Test that progress is reset on sync failure."""
        sync_manager = CheckpointSyncManager(mock_blockchain)

        # Set some progress
        sync_manager._update_progress({
            "stage": "downloading",
            "bytes_downloaded": 5000,
            "download_percentage": 50.0
        })

        # Reset progress
        sync_manager._reset_progress()

        progress = sync_manager.get_checkpoint_sync_progress()
        assert progress["stage"] == "idle"
        assert progress["bytes_downloaded"] == 0
        assert progress["download_percentage"] == 0.0


class TestSyncProgressAPIEndpoints:
    """Test suite for sync progress API endpoints."""

    @pytest.fixture
    def mock_app(self):
        """Create a mock Flask app for testing."""
        from flask import Flask
        app = Flask(__name__)
        app.config['TESTING'] = True
        return app

    @pytest.fixture
    def mock_node(self):
        """Create a mock blockchain node."""
        node = Mock()
        node.blockchain = Mock()
        node.blockchain.chain = [Mock(index=i) for i in range(50)]
        node.blockchain.pending_transactions = []

        # Mock light client service
        light_client_service = Mock()
        sync_progress = SyncProgress(
            current_height=50,
            target_height=100,
            sync_percentage=50.0,
            estimated_time_remaining=60,
            sync_state="syncing",
            headers_per_second=10.0,
            started_at=datetime.now(),
            checkpoint_sync_enabled=True,
            checkpoint_height=30,
        )
        light_client_service.get_sync_progress.return_value = sync_progress
        node.light_client_service = light_client_service

        return node

    def test_sync_progress_endpoint_success(self, mock_app, mock_node):
        """Test /sync/progress endpoint returns progress data."""
        # Attach app to node
        mock_node.app = mock_app

        with mock_app.test_request_context():
            from xai.core.node_api import NodeAPIRoutes

            routes = NodeAPIRoutes(mock_node)
            routes._setup_core_routes()

            client = mock_app.test_client()
            response = client.get('/sync/progress')

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["success"] is True
            assert "progress" in data
            assert data["progress"]["sync_percentage"] == 50.0
            assert data["progress"]["sync_state"] == "syncing"

    def test_sync_progress_endpoint_service_unavailable(self, mock_app):
        """Test /sync/progress when light client service is unavailable."""
        node = Mock()
        node.app = mock_app
        node.light_client_service = None
        node.blockchain = Mock()
        node.blockchain.chain = []

        with mock_app.test_request_context():
            from xai.core.node_api import NodeAPIRoutes

            routes = NodeAPIRoutes(node)
            routes._setup_core_routes()

            client = mock_app.test_client()
            response = client.get('/sync/progress')

            assert response.status_code == 503
            data = json.loads(response.data)
            assert "error" in data
            assert data["sync_state"] == "unavailable"

    def test_sync_status_endpoint_all_types(self, mock_app, mock_node):
        """Test /sync/status endpoint returns all sync types."""
        # Attach app to node
        mock_node.app = mock_app

        # Add checkpoint sync manager
        sync_coordinator = Mock()
        sync_manager = Mock()
        sync_manager.get_checkpoint_sync_progress.return_value = {
            "stage": "downloading",
            "download_percentage": 30.0
        }
        sync_coordinator.sync_manager = sync_manager
        mock_node.partial_sync_coordinator = sync_coordinator

        with mock_app.test_request_context():
            from xai.core.node_api import NodeAPIRoutes

            routes = NodeAPIRoutes(mock_node)
            routes._setup_core_routes()

            client = mock_app.test_client()
            response = client.get('/sync/status')

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["success"] is True
            assert "sync_status" in data

            status = data["sync_status"]
            assert status["header_sync"]["enabled"] is True
            assert status["checkpoint_sync"]["enabled"] is True
            assert status["state_sync"]["enabled"] is True


class TestSyncProgressWebSocket:
    """Test suite for WebSocket sync progress broadcasting."""

    def test_broadcast_sync_progress(self):
        """Test broadcasting sync progress via WebSocket."""
        from xai.core.api_websocket import WebSocketAPIHandler

        node = Mock()
        app = Mock()

        # Mock Sock
        with patch('xai.core.api_websocket.Sock'):
            handler = WebSocketAPIHandler(node, app)

            # Mock a WebSocket client
            mock_ws = Mock()
            handler.ws_clients = [{"id": "test_client", "ws": mock_ws, "ip": "127.0.0.1"}]
            handler.ws_subscriptions = {"test_client": ["sync"]}

            # Broadcast sync progress
            progress_data = {
                "percentage": 45.5,
                "current": 4550,
                "target": 10000,
                "eta_seconds": 120
            }

            handler.broadcast_sync_progress(progress_data)

            # Verify message was sent
            mock_ws.send.assert_called_once()
            sent_data = json.loads(mock_ws.send.call_args[0][0])

            assert sent_data["channel"] == "sync"
            assert sent_data["type"] == "sync_progress"
            assert sent_data["data"]["percentage"] == 45.5
            assert sent_data["data"]["current"] == 4550

    def test_sync_progress_updater_thread(self):
        """Test that sync progress updater runs in background."""
        from xai.core.api_websocket import WebSocketAPIHandler

        node = Mock()
        node.blockchain = Mock()
        node.blockchain.get_stats.return_value = {}

        # Mock light client service
        light_client_service = Mock()
        sync_progress = SyncProgress(
            current_height=50,
            target_height=100,
            sync_percentage=50.0,
            estimated_time_remaining=60,
            sync_state="syncing",
            headers_per_second=10.0,
            started_at=datetime.now(),
            checkpoint_sync_enabled=False,
            checkpoint_height=None,
        )
        light_client_service.get_sync_progress.return_value = sync_progress
        node.light_client_service = light_client_service

        app = Mock()

        with patch('xai.core.api_websocket.Sock'):
            with patch('xai.core.api_websocket.threading.Thread') as mock_thread:
                handler = WebSocketAPIHandler(node, app)
                handler.start_background_tasks()

                # Verify sync progress thread was started
                assert mock_thread.call_count >= 2  # stats + sync threads
                # One of the threads should be sync_progress_updater
                thread_targets = [call[1]['target'].__name__ for call in mock_thread.call_args_list]
                assert 'sync_progress_updater' in thread_targets


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
