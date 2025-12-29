"""
Tests for the XAI Performance Dashboard Blueprint.
"""

import time
from unittest.mock import Mock

import pytest
from flask import Flask

from xai.dashboard.performance_dashboard import (
    _calculate_tps,
    _get_block_times,
    _get_historical_metrics,
    performance_bp,
)


@pytest.fixture
def app():
    """Create a Flask test application."""
    app = Flask(__name__)
    app.register_blueprint(performance_bp)
    return app


@pytest.fixture
def client(app):
    """Create a test client."""
    return app.test_client()


@pytest.fixture
def mock_blockchain():
    """Create a mock blockchain for testing."""
    mock = Mock()
    mock.chain = []
    mock._cumulative_tx_count = 0
    mock.get_stats = Mock(return_value={
        "chain_height": 100,
        "pending_transactions_count": 5,
        "orphan_blocks_count": 0,
        "orphan_transactions_count": 0,
        "total_circulating_supply": 1000000,
        "difficulty": 4,
        "mempool_size_bytes": 2048,
        "latest_block_hash": "abc123def456789",
    })
    return mock


@pytest.fixture
def mock_node(mock_blockchain):
    """Create a mock node for testing."""
    mock = Mock()
    mock.blockchain = mock_blockchain
    mock.p2p_manager = Mock()
    mock.p2p_manager.get_peer_count = Mock(return_value=5)
    mock.is_mining = True
    mock.start_time = time.time() - 3600  # 1 hour ago
    return mock


@pytest.fixture
def app_with_context(mock_node, mock_blockchain):
    """Create app with mocked blockchain context."""
    app = Flask(__name__)

    @app.before_request
    def inject_context():
        from flask import g
        g.api_context = {
            "node": mock_node,
            "blockchain": mock_blockchain,
        }

    app.register_blueprint(performance_bp)
    return app


class TestPerformanceDashboardRoutes:
    """Test dashboard route availability."""

    def test_dashboard_home_returns_html(self, client):
        """Test that dashboard home returns HTML."""
        resp = client.get("/dashboard/")
        assert resp.status_code == 200
        assert b"XAI Performance Dashboard" in resp.data

    def test_metrics_current_without_context(self, client):
        """Test current metrics returns 503 without blockchain."""
        resp = client.get("/dashboard/api/metrics/current")
        assert resp.status_code == 503
        data = resp.json
        assert data["success"] is False
        assert "Blockchain not initialized" in data["error"]

    def test_metrics_blocks_without_context(self, client):
        """Test blocks endpoint returns 503 without blockchain."""
        resp = client.get("/dashboard/api/metrics/blocks")
        assert resp.status_code == 503

    def test_metrics_history_without_context(self, client):
        """Test history endpoint returns 503 without blockchain."""
        resp = client.get("/dashboard/api/metrics/history")
        assert resp.status_code == 503

    def test_metrics_summary_without_context(self, client):
        """Test summary endpoint returns 503 without blockchain."""
        resp = client.get("/dashboard/api/metrics/summary")
        assert resp.status_code == 503


class TestPerformanceDashboardWithContext:
    """Test dashboard with mocked blockchain context."""

    def test_current_metrics_returns_data(self, app_with_context, mock_blockchain):
        """Test current metrics with valid blockchain context."""
        with app_with_context.test_client() as client:
            resp = client.get("/dashboard/api/metrics/current")
            assert resp.status_code == 200
            data = resp.json
            assert data["success"] is True
            assert "current" in data
            current = data["current"]
            assert "tps" in current
            assert "chain_height" in current
            assert current["chain_height"] == 100
            assert "peer_count" in current
            assert current["peer_count"] == 5
            assert "mempool" in current
            assert current["mempool"]["pending_count"] == 5
            assert "is_mining" in current
            assert current["is_mining"] is True

    def test_blocks_endpoint_returns_data(self, app_with_context, mock_blockchain):
        """Test blocks endpoint with valid context."""
        # Add mock blocks to chain
        mock_block1 = Mock()
        mock_block1.index = 0
        mock_block1.hash = "genesis_hash_000000"
        mock_block1.timestamp = time.time() - 60
        mock_block1.transactions = []

        mock_block2 = Mock()
        mock_block2.index = 1
        mock_block2.hash = "block1_hash_111111"
        mock_block2.timestamp = time.time() - 30
        mock_block2.transactions = [Mock(), Mock()]

        mock_blockchain.chain = [mock_block1, mock_block2]

        with app_with_context.test_client() as client:
            resp = client.get("/dashboard/api/metrics/blocks?count=10")
            assert resp.status_code == 200
            data = resp.json
            assert data["success"] is True
            assert "blocks" in data
            assert len(data["blocks"]) == 2

    def test_history_endpoint_returns_data(self, app_with_context):
        """Test history endpoint returns correct structure."""
        with app_with_context.test_client() as client:
            resp = client.get("/dashboard/api/metrics/history?hours=1")
            assert resp.status_code == 200
            data = resp.json
            assert data["success"] is True
            assert "history" in data
            history = data["history"]
            assert "tps_avg" in history
            assert "tps_max" in history
            assert "samples" in history

    def test_summary_endpoint_returns_complete_data(self, app_with_context, mock_blockchain):
        """Test summary returns all required sections."""
        with app_with_context.test_client() as client:
            resp = client.get("/dashboard/api/metrics/summary")
            assert resp.status_code == 200
            data = resp.json
            assert data["success"] is True
            assert "chain" in data
            assert "performance" in data
            assert "mempool" in data
            assert "network" in data
            assert "node" in data
            assert "recent_blocks" in data


class TestTPSCalculation:
    """Test TPS calculation logic."""

    def test_calculate_tps_returns_valid_data(self, mock_blockchain):
        """Test TPS calculation returns expected structure."""
        result = _calculate_tps(mock_blockchain)
        assert "timestamp" in result
        assert "tps" in result
        assert "blocks_per_minute" in result
        assert "pending_count" in result
        assert "height" in result
        assert result["height"] == 100

    def test_tps_zero_on_first_call(self, mock_blockchain):
        """Test TPS is zero on first calculation."""
        # Reset global state for clean test
        import xai.dashboard.performance_dashboard as dash
        dash._last_tx_count = 0
        dash._last_sample_time = 0

        result = _calculate_tps(mock_blockchain)
        assert result["tps"] == 0.0


class TestBlockTimes:
    """Test block timing retrieval."""

    def test_get_block_times_empty_chain(self, mock_blockchain):
        """Test with empty chain."""
        mock_blockchain.chain = []
        result = _get_block_times(mock_blockchain, 10)
        assert result == []

    def test_get_block_times_with_blocks(self, mock_blockchain):
        """Test with populated chain."""
        now = time.time()
        blocks = []
        for i in range(5):
            block = Mock()
            block.index = i
            block.hash = f"hash_{i:06d}"
            block.timestamp = now - (5 - i) * 10
            block.transactions = [Mock()] * (i + 1)
            blocks.append(block)

        mock_blockchain.chain = blocks
        result = _get_block_times(mock_blockchain, 10)
        assert len(result) == 5
        assert result[-1]["index"] == 4
        assert result[-1]["tx_count"] == 5


class TestHistoricalMetrics:
    """Test historical metrics aggregation."""

    def test_get_historical_empty(self):
        """Test with no history."""
        import xai.dashboard.performance_dashboard as dash
        dash._tps_history.clear()

        result = _get_historical_metrics(1)
        assert result["tps_avg"] == 0.0
        assert result["samples"] == []

    def test_get_historical_with_data(self):
        """Test with sample data in history."""
        import xai.dashboard.performance_dashboard as dash
        dash._tps_history.clear()

        now = time.time()
        for i in range(10):
            dash._tps_history.append({
                "timestamp": now - (9 - i) * 60,
                "tps": float(i),
                "pending_count": i * 2,
            })

        result = _get_historical_metrics(1)
        assert result["tps_avg"] == 4.5  # Average of 0-9
        assert result["tps_max"] == 9.0
        assert result["tps_min"] == 0.0
        assert len(result["samples"]) > 0
