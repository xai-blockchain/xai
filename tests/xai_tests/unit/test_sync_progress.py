"""
Tests for header sync progress API and tracking.

Tests the light client header synchronization progress tracking,
API endpoints, WebSocket broadcasting, and CLI commands.
"""

from __future__ import annotations

import time
import json
from datetime import datetime
from typing import Any
from unittest.mock import Mock, patch, MagicMock

import pytest

from xai.core.p2p.light_client_service import LightClientService, SyncProgress


class MockBlockchain:
    """Mock blockchain for testing."""

    def __init__(self, chain_length: int = 100):
        self.chain = [Mock(index=i) for i in range(chain_length)]
        self.checkpoint_manager = None
        self.pending_transactions = []


class TestSyncProgress:
    """Test SyncProgress dataclass."""

    def test_sync_progress_to_dict(self):
        """Test SyncProgress serialization to dictionary."""
        started_at = datetime.now()
        progress = SyncProgress(
            current_height=50,
            target_height=100,
            sync_percentage=50.0,
            estimated_time_remaining=120,
            sync_state="syncing",
            headers_per_second=2.5,
            started_at=started_at,
            checkpoint_sync_enabled=True,
            checkpoint_height=80,
        )

        result = progress.to_dict()

        assert result["current_height"] == 50
        assert result["target_height"] == 100
        assert result["sync_percentage"] == 50.0
        assert result["estimated_time_remaining"] == 120
        assert result["sync_state"] == "syncing"
        assert result["headers_per_second"] == 2.5
        assert result["started_at"] == started_at.isoformat()
        assert result["checkpoint_sync_enabled"] is True
        assert result["checkpoint_height"] == 80

    def test_sync_progress_to_dict_with_none_eta(self):
        """Test SyncProgress serialization with None ETA."""
        progress = SyncProgress(
            current_height=100,
            target_height=100,
            sync_percentage=100.0,
            estimated_time_remaining=None,
            sync_state="synced",
            headers_per_second=0.0,
            started_at=datetime.now(),
        )

        result = progress.to_dict()

        assert result["estimated_time_remaining"] is None


class TestLightClientServiceSyncTracking:
    """Test light client service sync progress tracking."""

    def test_start_sync_initializes_tracking(self):
        """Test that start_sync initializes progress tracking."""
        blockchain = MockBlockchain(chain_length=10)
        service = LightClientService(blockchain)

        service.start_sync(target_height=100)

        assert service._sync_start_time is not None
        assert service._sync_start_height == 9  # len - 1
        assert service._target_height == 100
        assert service._last_height == 9
        assert len(service._sync_history) == 1

    def test_update_sync_progress_tracks_changes(self):
        """Test that update_sync_progress tracks height changes."""
        blockchain = MockBlockchain(chain_length=10)
        service = LightClientService(blockchain)

        service.start_sync(target_height=100)
        initial_time = service._last_height_update_time

        # Wait a bit and update
        time.sleep(0.1)
        service.update_sync_progress(current_height=20)

        assert service._last_height == 20
        assert service._last_height_update_time > initial_time
        assert len(service._sync_history) == 2

    def test_update_sync_progress_ignores_duplicates(self):
        """Test that duplicate updates don't add to history."""
        blockchain = MockBlockchain(chain_length=10)
        service = LightClientService(blockchain)

        service.start_sync(target_height=100)
        service.update_sync_progress(current_height=20)
        history_length = len(service._sync_history)

        # Update with same height
        service.update_sync_progress(current_height=20)

        assert len(service._sync_history) == history_length

    def test_get_sync_progress_returns_correct_data(self):
        """Test get_sync_progress returns comprehensive data."""
        blockchain = MockBlockchain(chain_length=50)
        service = LightClientService(blockchain)

        service.start_sync(target_height=100)
        service.update_sync_progress(current_height=50)

        progress = service.get_sync_progress()

        # Current height comes from blockchain.chain length
        assert progress.current_height == 49  # len(chain) - 1
        assert progress.target_height == 100
        assert progress.sync_state in ["syncing", "idle"]
        assert isinstance(progress.headers_per_second, float)
        assert isinstance(progress.started_at, datetime)

    def test_sync_percentage_calculation(self):
        """Test sync percentage is calculated correctly."""
        blockchain = MockBlockchain(chain_length=25)
        service = LightClientService(blockchain)

        service.start_sync(target_height=100)
        service._sync_start_height = 0

        progress = service.get_sync_progress()

        # 25 headers out of 100 = 25%
        assert 24.0 <= progress.sync_percentage <= 26.0

    def test_sync_percentage_at_target(self):
        """Test sync percentage at 100% when at target."""
        blockchain = MockBlockchain(chain_length=100)
        service = LightClientService(blockchain)

        service.start_sync(target_height=100)
        service._sync_start_height = 0
        service.update_sync_progress(current_height=100)

        progress = service.get_sync_progress()

        # Should be at or very close to 100%
        assert progress.sync_percentage >= 99.0

    def test_headers_per_second_calculation(self):
        """Test headers per second calculation."""
        blockchain = MockBlockchain(chain_length=0)
        service = LightClientService(blockchain)

        service.start_sync(target_height=100)

        # Simulate progress over time
        now = time.time()
        service._sync_history = [
            (now - 2.0, 0),   # 2 seconds ago, height 0
            (now - 1.0, 50),  # 1 second ago, height 50
            (now, 100),       # now, height 100
        ]

        headers_per_second = service._calculate_headers_per_second()

        # Should be ~50 headers/second (100 headers in 2 seconds)
        assert 40 <= headers_per_second <= 60

    def test_headers_per_second_with_no_history(self):
        """Test headers per second returns 0 with insufficient history."""
        blockchain = MockBlockchain(chain_length=0)
        service = LightClientService(blockchain)

        headers_per_second = service._calculate_headers_per_second()

        assert headers_per_second == 0.0

    def test_sync_state_synced(self):
        """Test sync state is 'synced' when complete."""
        blockchain = MockBlockchain(chain_length=100)
        service = LightClientService(blockchain)

        # Set target to current height to trigger synced state
        service.start_sync(target_height=99)
        service.update_sync_progress(current_height=100)

        progress = service.get_sync_progress()

        assert progress.sync_state == "synced"

    def test_sync_state_syncing(self):
        """Test sync state is 'syncing' when in progress."""
        blockchain = MockBlockchain(chain_length=50)
        service = LightClientService(blockchain)

        service.start_sync(target_height=100)

        # Add sync history to show active progress
        now = time.time()
        service._sync_history = [
            (now - 2.0, 10),
            (now - 1.0, 30),
            (now, 50),
        ]
        service.update_sync_progress(current_height=50)

        progress = service.get_sync_progress()

        assert progress.sync_state == "syncing"

    def test_sync_state_stalled(self):
        """Test sync state is 'stalled' when no progress."""
        blockchain = MockBlockchain(chain_length=50)
        service = LightClientService(blockchain)

        service.start_sync(target_height=100)
        service._last_height_update_time = time.time() - 60  # 60 seconds ago
        service._sync_history = [(time.time() - 60, 50)]

        progress = service.get_sync_progress()

        assert progress.sync_state == "stalled"

    def test_estimated_time_remaining(self):
        """Test ETA calculation."""
        blockchain = MockBlockchain(chain_length=50)
        service = LightClientService(blockchain)

        service.start_sync(target_height=100)

        # Set up sync history showing 10 headers/sec
        now = time.time()
        service._sync_history = [
            (now - 5.0, 0),
            (now, 50),
        ]
        service.update_sync_progress(current_height=50)

        progress = service.get_sync_progress()

        # Remaining: 50 headers at 10 headers/sec = 5 seconds
        assert progress.estimated_time_remaining is not None
        assert 4 <= progress.estimated_time_remaining <= 6

    def test_estimated_time_remaining_when_synced(self):
        """Test ETA is 0 or None when synced."""
        blockchain = MockBlockchain(chain_length=100)
        service = LightClientService(blockchain)

        service.start_sync(target_height=100)
        service.update_sync_progress(current_height=100)

        progress = service.get_sync_progress()

        # Should be None or 0 when synced
        assert progress.estimated_time_remaining is None or progress.estimated_time_remaining == 0

    def test_checkpoint_sync_info_included(self):
        """Test that checkpoint sync info is included."""
        blockchain = MockBlockchain(chain_length=50)

        # Add checkpoint manager
        checkpoint_manager = Mock()
        checkpoint_manager.latest_checkpoint_height = 75
        blockchain.checkpoint_manager = checkpoint_manager

        service = LightClientService(blockchain)
        service.start_sync(target_height=100)

        progress = service.get_sync_progress()

        assert progress.checkpoint_sync_enabled is True
        assert progress.checkpoint_height == 75

    def test_sync_history_limit(self):
        """Test that sync history is limited to 100 entries."""
        blockchain = MockBlockchain(chain_length=0)
        service = LightClientService(blockchain)

        service.start_sync(target_height=200)

        # Add 150 entries
        for i in range(150):
            service.update_sync_progress(current_height=i)

        # Should be limited to 100
        assert len(service._sync_history) == 100


class TestSyncProgressAPIEndpoints:
    """Test sync progress API endpoints."""

    @pytest.fixture
    def mock_node_api(self):
        """Create mock node API for testing."""
        node_api = Mock()
        node_api.node = Mock()

        # Create mock light client service
        blockchain = MockBlockchain(chain_length=50)
        light_client_service = LightClientService(blockchain)
        light_client_service.start_sync(target_height=100)

        node_api.node.light_client_service = light_client_service

        return node_api

    def test_get_header_sync_status_endpoint(self, mock_node_api):
        """Test GET /api/v1/sync/headers/status endpoint."""
        from xai.core.api_routes.sync import register_sync_routes
        from flask import Flask

        app = Flask(__name__)
        mock_node_api.app = app

        register_sync_routes(mock_node_api)

        with app.test_client() as client:
            response = client.get("/api/v1/sync/headers/status")
            data = json.loads(response.data)

            assert response.status_code == 200
            assert data["status"] == "ok"
            assert "sync_state" in data
            assert "current_height" in data
            assert "target_height" in data
            assert "is_syncing" in data
            assert isinstance(data["is_syncing"], bool)
            assert "checkpoint_sync_enabled" in data

    def test_get_header_sync_progress_endpoint(self, mock_node_api):
        """Test GET /api/v1/sync/headers/progress endpoint."""
        from xai.core.api_routes.sync import register_sync_routes
        from flask import Flask

        app = Flask(__name__)
        mock_node_api.app = app

        register_sync_routes(mock_node_api)

        with app.test_client() as client:
            response = client.get("/api/v1/sync/headers/progress")
            data = json.loads(response.data)

            assert response.status_code == 200
            assert data["status"] == "ok"
            assert "current_height" in data
            assert "target_height" in data
            assert "sync_percentage" in data
            assert "estimated_time_remaining" in data
            assert "headers_per_second" in data
            assert "sync_state" in data
            assert "started_at" in data

    def test_sync_status_endpoint_no_light_client(self):
        """Test status endpoint returns error when light client unavailable."""
        from xai.core.api_routes.sync import register_sync_routes
        from flask import Flask

        node_api = Mock()
        node_api.node = Mock()
        node_api.node.light_client_service = None

        app = Flask(__name__)
        node_api.app = app

        register_sync_routes(node_api)

        with app.test_client() as client:
            response = client.get("/api/v1/sync/headers/status")
            data = json.loads(response.data)

            assert response.status_code == 503
            assert "error" in data

    def test_sync_progress_endpoint_no_light_client(self):
        """Test progress endpoint returns error when light client unavailable."""
        from xai.core.api_routes.sync import register_sync_routes
        from flask import Flask

        node_api = Mock()
        node_api.node = Mock()
        node_api.node.light_client_service = None

        app = Flask(__name__)
        node_api.app = app

        register_sync_routes(node_api)

        with app.test_client() as client:
            response = client.get("/api/v1/sync/headers/progress")
            data = json.loads(response.data)

            assert response.status_code == 503
            assert "error" in data


class TestWebSocketSyncBroadcast:
    """Test WebSocket sync progress broadcasting."""

    def test_header_sync_progress_broadcast_structure(self):
        """Test that header sync progress messages have correct structure."""
        from xai.core.api.api_websocket import WebSocketAPIHandler
        from flask import Flask

        app = Flask(__name__)
        mock_node = Mock()
        mock_node.blockchain = Mock()
        mock_node.blockchain.get_stats = Mock(return_value={})

        # Create light client service with progress
        blockchain = MockBlockchain(chain_length=50)
        light_client_service = LightClientService(blockchain)
        light_client_service.start_sync(target_height=100)

        # Simulate active syncing
        now = time.time()
        light_client_service._sync_history = [
            (now - 2.0, 10),
            (now - 1.0, 30),
            (now, 50),
        ]
        light_client_service.update_sync_progress(current_height=50)

        mock_node.light_client_service = light_client_service

        with patch('xai.core.api_websocket.Sock'):
            handler = WebSocketAPIHandler(mock_node, app)

            # Mock broadcast_ws to capture messages
            broadcast_messages = []

            def capture_broadcast(message):
                broadcast_messages.append(message)

            handler.broadcast_ws = capture_broadcast

            # Manually trigger sync progress broadcast
            sync_progress = light_client_service.get_sync_progress()
            progress_dict = sync_progress.to_dict()

            if progress_dict["sync_state"] in ["syncing", "stalled"]:
                handler.broadcast_ws({
                    "channel": "sync",
                    "type": "header_sync_progress",
                    "data": {
                        "current_height": progress_dict["current_height"],
                        "target_height": progress_dict["target_height"],
                        "sync_percentage": progress_dict["sync_percentage"],
                        "estimated_time_remaining": progress_dict["estimated_time_remaining"],
                        "headers_per_second": progress_dict["headers_per_second"],
                        "sync_state": progress_dict["sync_state"],
                        "started_at": progress_dict["started_at"],
                    }
                })

            # Verify broadcast was called with correct data
            assert len(broadcast_messages) == 1
            message = broadcast_messages[0]
            assert message["channel"] == "sync"
            assert message["type"] == "header_sync_progress"
            assert "data" in message
            # Current height is blockchain.chain length - 1
            assert message["data"]["current_height"] == 49
            assert message["data"]["target_height"] == 100
            assert message["data"]["sync_state"] == "syncing"
            assert "headers_per_second" in message["data"]
            assert "started_at" in message["data"]


class TestSyncCLICommand:
    """Test sync CLI command."""

    @pytest.fixture
    def mock_client(self):
        """Create mock XAI client."""
        client = Mock()
        client.get_sync_status.return_value = {
            "status": "ok",
            "sync_state": "syncing",
            "current_height": 50,
            "target_height": 100,
            "is_syncing": True,
            "checkpoint_sync_enabled": False,
            "checkpoint_height": None,
        }
        client.get_sync_progress.return_value = {
            "status": "ok",
            "current_height": 50,
            "target_height": 100,
            "sync_percentage": 50.0,
            "estimated_time_remaining": 120,
            "headers_per_second": 2.5,
            "sync_state": "syncing",
            "started_at": datetime.now().isoformat(),
            "checkpoint_sync_enabled": False,
            "checkpoint_height": None,
        }
        return client

    def test_sync_status_command_basic(self, mock_client):
        """Test basic sync status command."""
        from xai.cli.enhanced_cli import cli
        from click.testing import CliRunner

        runner = CliRunner()

        with patch("xai.cli.enhanced_cli.XAIClient", return_value=mock_client):
            result = runner.invoke(cli, ["sync", "status"])

            # Should succeed
            assert result.exit_code == 0

    def test_sync_status_command_json_output(self, mock_client):
        """Test sync status command with JSON output."""
        from xai.cli.enhanced_cli import cli
        from click.testing import CliRunner

        runner = CliRunner()

        with patch("xai.cli.enhanced_cli.XAIClient", return_value=mock_client):
            result = runner.invoke(cli, ["--json-output", "sync", "status"])

            assert result.exit_code == 0
            data = json.loads(result.output)
            assert "status" in data
            assert "progress" in data

    def test_sync_status_command_shows_correct_state(self, mock_client):
        """Test that CLI correctly displays sync state."""
        from xai.cli.enhanced_cli import cli
        from click.testing import CliRunner

        runner = CliRunner()

        # Test syncing state
        with patch("xai.cli.enhanced_cli.XAIClient", return_value=mock_client):
            result = runner.invoke(cli, ["sync", "status"])
            assert result.exit_code == 0
            # Output should contain sync-related info
            assert any(keyword in result.output.lower() for keyword in ["sync", "height", "progress"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
