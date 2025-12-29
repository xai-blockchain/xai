"""
Tests for Sync API Routes.

Tests cover:
- /api/v1/sync/checkpoint/manifest
- /api/v1/sync/checkpoint/{id}/chunks
- /api/v1/sync/checkpoint/{id}/chunk/{n}
- /api/v1/sync/progress
- /api/v1/sync/headers/progress
"""

import pytest
import json
import tempfile
import shutil
from unittest.mock import Mock, MagicMock, patch
from flask import Flask

from xai.core.api_routes.sync import register_sync_routes
from xai.core.p2p.chunked_sync import ChunkedStateSyncService, SnapshotMetadata, SyncProgress
from xai.core.p2p.checkpoint_sync import CheckpointSyncManager
from xai.core.consensus.checkpoint_payload import CheckpointPayload


@pytest.fixture
def temp_storage():
    """Create temporary storage directory."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def chunked_service(temp_storage):
    """Create chunked sync service with sample data."""
    service = ChunkedStateSyncService(
        storage_dir=temp_storage,
        chunk_size=1000,
        enable_compression=False,
    )

    # Create sample snapshot
    data = {
        "utxo_snapshot": {"addr1": 100, "addr2": 200},
        "account_balances": {"addr3": 300},
    }
    serialized = json.dumps(data, sort_keys=True).encode("utf-8")
    import hashlib
    state_hash = hashlib.sha256(serialized).hexdigest()

    payload = CheckpointPayload(
        height=100,
        block_hash="abc123def456",
        state_hash=state_hash,
        data=data,
    )

    service.create_state_snapshot_chunks(height=100, payload=payload)

    return service


@pytest.fixture
def mock_blockchain(chunked_service):
    """Create mock blockchain with chunked sync."""
    blockchain = Mock()
    blockchain.chain = [Mock(index=i) for i in range(50)]

    # Create checkpoint sync manager
    checkpoint_sync = Mock()
    checkpoint_sync.enable_chunked_sync = True
    checkpoint_sync.chunked_service = chunked_service
    checkpoint_sync.list_available_snapshots = Mock(
        return_value=[
            {
                "snapshot_id": "height_100_abc12345",
                "height": 100,
                "total_chunks": 3,
                "total_size": 3000,
            }
        ]
    )
    checkpoint_sync.get_checkpoint_sync_progress = Mock(
        return_value={
            "stage": "idle",
            "bytes_downloaded": 0,
            "total_bytes": 0,
            "download_percentage": 0.0,
            "verification_percentage": 0.0,
            "application_percentage": 0.0,
        }
    )
    checkpoint_sync.get_best_checkpoint_metadata = Mock(
        return_value={"height": 100, "block_hash": "abc123"}
    )

    blockchain.checkpoint_sync_manager = checkpoint_sync
    return blockchain


@pytest.fixture
def mock_node(mock_blockchain):
    """Create mock node."""
    node = Mock()
    node.blockchain = mock_blockchain
    return node


@pytest.fixture
def app(mock_node):
    """Create Flask app with sync routes."""
    app = Flask(__name__)
    app.config["TESTING"] = True

    # Create mock NodeAPI
    node_api = Mock()
    node_api.app = app
    node_api.node = mock_node

    # Register sync routes
    register_sync_routes(node_api)

    return app


class TestCheckpointManifestAPI:
    """Test /api/v1/sync/checkpoint/manifest endpoint."""

    def test_get_latest_snapshot_success(self, app, chunked_service):
        """Test getting latest snapshot manifest."""
        with app.test_client() as client:
            response = client.get("/api/v1/sync/checkpoint/manifest")
            assert response.status_code == 200

            data = json.loads(response.data)
            assert data["status"] == "ok"
            assert "snapshot" in data
            assert data["snapshot"]["height"] == 100

    def test_get_latest_snapshot_no_blockchain(self, app, mock_node):
        """Test error when blockchain not available."""
        mock_node.blockchain = None

        with app.test_client() as client:
            response = client.get("/api/v1/sync/checkpoint/manifest")
            assert response.status_code == 503

            data = json.loads(response.data)
            assert "error" in data

    def test_get_latest_snapshot_chunked_sync_disabled(self, app, mock_blockchain):
        """Test error when chunked sync is disabled."""
        mock_blockchain.checkpoint_sync_manager.enable_chunked_sync = False

        with app.test_client() as client:
            response = client.get("/api/v1/sync/checkpoint/manifest")
            assert response.status_code == 503

            data = json.loads(response.data)
            assert "error" in data

    def test_legacy_route_works(self, app):
        """Test legacy route /sync/snapshot/latest works."""
        with app.test_client() as client:
            response = client.get("/sync/snapshot/latest")
            assert response.status_code == 200


class TestChunkListAPI:
    """Test /api/v1/sync/checkpoint/{id}/chunks endpoint."""

    def test_list_chunks_success(self, app, chunked_service):
        """Test listing chunks for a snapshot."""
        snapshot_id = chunked_service.get_latest_snapshot_id()

        with app.test_client() as client:
            response = client.get(f"/api/v1/sync/checkpoint/{snapshot_id}/chunks")
            assert response.status_code == 200

            data = json.loads(response.data)
            assert data["status"] == "ok"
            assert "chunks" in data
            assert data["total_chunks"] > 0
            assert len(data["chunks"]) == data["total_chunks"]

    def test_list_chunks_not_found(self, app):
        """Test listing chunks for non-existent snapshot."""
        with app.test_client() as client:
            response = client.get("/api/v1/sync/checkpoint/invalid_snapshot/chunks")
            assert response.status_code == 404

            data = json.loads(response.data)
            assert "error" in data

    def test_chunk_has_priority(self, app, chunked_service):
        """Test chunks include priority information."""
        snapshot_id = chunked_service.get_latest_snapshot_id()

        with app.test_client() as client:
            response = client.get(f"/api/v1/sync/checkpoint/{snapshot_id}/chunks")
            data = json.loads(response.data)

            chunk = data["chunks"][0]
            assert "chunk_index" in chunk
            assert "priority" in chunk
            assert "url" in chunk


class TestChunkDownloadAPI:
    """Test /api/v1/sync/checkpoint/{id}/chunk/{n} endpoint."""

    def test_download_chunk_success(self, app, chunked_service):
        """Test downloading a chunk."""
        snapshot_id = chunked_service.get_latest_snapshot_id()

        with app.test_client() as client:
            response = client.get(f"/api/v1/sync/checkpoint/{snapshot_id}/chunk/0")
            assert response.status_code == 200
            assert response.content_type == "application/octet-stream"
            assert "X-Chunk-Index" in response.headers
            assert "X-Total-Chunks" in response.headers
            assert "X-Chunk-Checksum" in response.headers

    def test_download_chunk_not_found(self, app, chunked_service):
        """Test downloading non-existent chunk."""
        snapshot_id = chunked_service.get_latest_snapshot_id()

        with app.test_client() as client:
            response = client.get(f"/api/v1/sync/checkpoint/{snapshot_id}/chunk/999")
            assert response.status_code == 404

    def test_download_chunk_with_range_header(self, app, chunked_service):
        """Test downloading chunk with Range header."""
        snapshot_id = chunked_service.get_latest_snapshot_id()

        with app.test_client() as client:
            response = client.get(
                f"/api/v1/sync/checkpoint/{snapshot_id}/chunk/0",
                headers={"Range": "bytes=0-99"},
            )
            assert response.status_code == 206  # Partial Content
            assert "Content-Range" in response.headers
            assert response.headers["Accept-Ranges"] == "bytes"

    def test_download_chunk_invalid_range(self, app, chunked_service):
        """Test downloading chunk with invalid Range header."""
        snapshot_id = chunked_service.get_latest_snapshot_id()

        with app.test_client() as client:
            response = client.get(
                f"/api/v1/sync/checkpoint/{snapshot_id}/chunk/0",
                headers={"Range": "bytes=999999-999999"},
            )
            assert response.status_code == 416  # Range Not Satisfiable


class TestSyncProgressAPI:
    """Test /api/v1/sync/progress endpoint."""

    def test_get_sync_progress_success(self, app):
        """Test getting sync progress."""
        with app.test_client() as client:
            response = client.get("/api/v1/sync/progress")
            assert response.status_code == 200

            data = json.loads(response.data)
            assert data["status"] == "ok"
            assert "progress" in data
            assert "stage" in data["progress"]
            assert "download_percentage" in data["progress"]

    def test_get_sync_progress_no_blockchain(self, app, mock_node):
        """Test error when blockchain not available."""
        mock_node.blockchain = None

        with app.test_client() as client:
            response = client.get("/api/v1/sync/progress")
            assert response.status_code == 503

    def test_get_sync_progress_no_checkpoint_sync(self, app, mock_blockchain):
        """Test error when checkpoint sync not available."""
        mock_blockchain.checkpoint_sync_manager = None

        with app.test_client() as client:
            response = client.get("/api/v1/sync/progress")
            assert response.status_code == 503


class TestHeaderSyncProgressAPI:
    """Test /api/v1/sync/headers/progress endpoint."""

    def test_get_header_sync_progress_success(self, app):
        """Test getting header sync progress."""
        with app.test_client() as client:
            response = client.get("/api/v1/sync/headers/progress")
            assert response.status_code == 200

            data = json.loads(response.data)
            assert data["status"] == "ok"
            assert "synced_headers" in data
            assert "total_headers" in data
            assert "percentage" in data
            assert "estimated_completion" in data
            assert "is_syncing" in data

    def test_header_sync_progress_calculation(self, app, mock_blockchain):
        """Test header sync progress calculation."""
        # Set chain to 50 blocks, target to 100
        mock_blockchain.chain = [Mock(index=i) for i in range(50)]
        mock_blockchain.checkpoint_sync_manager.get_best_checkpoint_metadata = Mock(
            return_value={"height": 100}
        )

        with app.test_client() as client:
            response = client.get("/api/v1/sync/headers/progress")
            data = json.loads(response.data)

            assert data["synced_headers"] == 50
            assert data["total_headers"] == 100
            assert data["percentage"] == 50.0
            assert data["is_syncing"] is True

    def test_header_sync_complete(self, app, mock_blockchain):
        """Test header sync when complete."""
        # Set chain equal to target
        mock_blockchain.chain = [Mock(index=i) for i in range(100)]
        mock_blockchain.checkpoint_sync_manager.get_best_checkpoint_metadata = Mock(
            return_value={"height": 100}
        )

        with app.test_client() as client:
            response = client.get("/api/v1/sync/headers/progress")
            data = json.loads(response.data)

            assert data["synced_headers"] == 100
            assert data["total_headers"] == 100
            assert data["percentage"] == 100.0
            assert data["is_syncing"] is False

    def test_header_sync_no_blockchain(self, app, mock_node):
        """Test error when blockchain not available."""
        mock_node.blockchain = None

        with app.test_client() as client:
            response = client.get("/api/v1/sync/headers/progress")
            assert response.status_code == 503


class TestResumeSyncAPI:
    """Test /sync/snapshot/resume endpoint."""

    def test_resume_sync_success(self, app, chunked_service):
        """Test resuming sync with existing progress."""
        snapshot_id = chunked_service.get_latest_snapshot_id()

        # Create progress
        progress = SyncProgress(snapshot_id=snapshot_id, total_chunks=3)
        progress.mark_downloaded(0)
        chunked_service.save_sync_progress(progress)

        with app.test_client() as client:
            response = client.post(
                "/sync/snapshot/resume",
                json={"snapshot_id": snapshot_id},
                content_type="application/json",
            )
            assert response.status_code == 200

            data = json.loads(response.data)
            assert data["status"] == "ok"
            assert data["progress_percent"] > 0
            assert len(data["downloaded_chunks"]) > 0

    def test_resume_sync_no_progress(self, app, chunked_service):
        """Test resume with no existing progress."""
        with app.test_client() as client:
            response = client.post(
                "/sync/snapshot/resume",
                json={"snapshot_id": "nonexistent"},
                content_type="application/json",
            )
            assert response.status_code == 404

    def test_resume_sync_missing_snapshot_id(self, app):
        """Test resume without snapshot_id."""
        with app.test_client() as client:
            response = client.post(
                "/sync/snapshot/resume",
                json={},
                content_type="application/json",
            )
            assert response.status_code == 400

            data = json.loads(response.data)
            assert "error" in data


class TestListSnapshotsAPI:
    """Test /sync/snapshots endpoint."""

    def test_list_snapshots_success(self, app):
        """Test listing all snapshots."""
        with app.test_client() as client:
            response = client.get("/sync/snapshots")
            assert response.status_code == 200

            data = json.loads(response.data)
            assert data["status"] == "ok"
            assert "count" in data
            assert "snapshots" in data
            assert data["count"] > 0

    def test_list_snapshots_no_blockchain(self, app, mock_node):
        """Test error when blockchain not available."""
        mock_node.blockchain = None

        with app.test_client() as client:
            response = client.get("/sync/snapshots")
            assert response.status_code == 503


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
