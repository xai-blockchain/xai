"""
Integration tests for Mining API endpoints.

Tests all mining-related API endpoints including:
- Start/stop mining endpoints
- Mining status endpoints
- Mining statistics and metrics
- Error handling and validation
"""

import pytest
import json
import time
from unittest.mock import Mock, patch, MagicMock
from flask import Flask
from xai.core.api_mining import MiningAPIHandler
from xai.core.blockchain import Blockchain
from xai.core.wallet import Wallet


@pytest.fixture
def mock_node():
    """Create a mock blockchain node for testing."""
    node = Mock()
    node.blockchain = Mock(spec=Blockchain)
    node.blockchain.difficulty = 4
    node.blockchain.block_reward = 50
    node.blockchain.pending_transactions = []
    node.is_mining = False
    return node


@pytest.fixture
def flask_app():
    """Create a Flask app for testing."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    return app


@pytest.fixture
def mock_broadcast():
    """Create a mock WebSocket broadcast callback."""
    return Mock()


@pytest.fixture
def mining_handler(mock_node, flask_app, mock_broadcast):
    """Create a MiningAPIHandler instance for testing."""
    handler = MiningAPIHandler(mock_node, flask_app, mock_broadcast)
    return handler


@pytest.fixture
def test_client(flask_app):
    """Create a test client for the Flask app."""
    return flask_app.test_client()


class TestMiningStartEndpoint:
    """Test mining start endpoint (/mining/start)."""

    def test_start_mining_success(self, test_client, mining_handler, mock_broadcast):
        """Test successful mining start."""
        response = test_client.post(
            '/mining/start',
            json={
                'miner_address': 'test_miner_123',
                'threads': 2,
                'intensity': 'medium'
            }
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['message'] == 'Mining started'
        assert data['miner_address'] == 'test_miner_123'
        assert data['threads'] == 2
        assert data['intensity'] == 'medium'
        assert 'expected_hashrate' in data

        # Verify WebSocket broadcast was called
        mock_broadcast.assert_called()
        call_args = mock_broadcast.call_args[0][0]
        assert call_args['channel'] == 'mining'
        assert call_args['event'] == 'started'

    def test_start_mining_without_address(self, test_client, mining_handler):
        """Test mining start without miner address."""
        response = test_client.post(
            '/mining/start',
            json={
                'threads': 2,
                'intensity': 'medium'
            }
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'miner_address required' in data['error']

    def test_start_mining_invalid_intensity(self, test_client, mining_handler):
        """Test mining start with invalid intensity level."""
        response = test_client.post(
            '/mining/start',
            json={
                'miner_address': 'test_miner_123',
                'threads': 2,
                'intensity': 'ultra_high'  # Invalid intensity
            }
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'intensity must be low, medium, or high' in data['error']

    def test_start_mining_already_active(self, test_client, mining_handler):
        """Test starting mining when already active for address."""
        # Start mining first time
        test_client.post(
            '/mining/start',
            json={
                'miner_address': 'test_miner_123',
                'threads': 2,
                'intensity': 'medium'
            }
        )

        # Try to start again with same address
        response = test_client.post(
            '/mining/start',
            json={
                'miner_address': 'test_miner_123',
                'threads': 1,
                'intensity': 'low'
            }
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'Mining already active' in data['error']

    def test_start_mining_low_intensity(self, test_client, mining_handler):
        """Test mining start with low intensity."""
        response = test_client.post(
            '/mining/start',
            json={
                'miner_address': 'test_miner_low',
                'threads': 1,
                'intensity': 'low'
            }
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['intensity'] == 'low'

    def test_start_mining_high_intensity(self, test_client, mining_handler):
        """Test mining start with high intensity."""
        response = test_client.post(
            '/mining/start',
            json={
                'miner_address': 'test_miner_high',
                'threads': 4,
                'intensity': 'high'
            }
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['intensity'] == 'high'
        assert data['threads'] == 4

    def test_start_mining_default_threads(self, test_client, mining_handler):
        """Test mining start with default thread count."""
        response = test_client.post(
            '/mining/start',
            json={
                'miner_address': 'test_miner_default',
                'intensity': 'medium'
            }
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['threads'] == 1  # Default value


class TestMiningStopEndpoint:
    """Test mining stop endpoint (/mining/stop)."""

    def test_stop_mining_success(self, test_client, mining_handler, mock_broadcast):
        """Test successful mining stop."""
        # Start mining first
        test_client.post(
            '/mining/start',
            json={
                'miner_address': 'test_miner_123',
                'threads': 2,
                'intensity': 'medium'
            }
        )

        # Stop mining
        response = test_client.post(
            '/mining/stop',
            json={'miner_address': 'test_miner_123'}
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['message'] == 'Mining stopped'
        assert 'total_blocks_mined' in data
        assert 'total_xai_earned' in data
        assert 'mining_duration' in data

    def test_stop_mining_not_active(self, test_client, mining_handler):
        """Test stopping mining when not active."""
        response = test_client.post(
            '/mining/stop',
            json={'miner_address': 'test_miner_nonexistent'}
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'No active mining' in data['error']

    def test_stop_mining_without_address(self, test_client, mining_handler):
        """Test stopping mining without address."""
        response = test_client.post(
            '/mining/stop',
            json={}
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_stop_mining_broadcasts_event(self, test_client, mining_handler, mock_broadcast):
        """Test that stopping mining broadcasts WebSocket event."""
        # Start mining
        test_client.post(
            '/mining/start',
            json={
                'miner_address': 'test_miner_123',
                'threads': 2,
                'intensity': 'medium'
            }
        )

        # Reset mock to clear previous calls
        mock_broadcast.reset_mock()

        # Stop mining
        test_client.post(
            '/mining/stop',
            json={'miner_address': 'test_miner_123'}
        )

        # Verify broadcast
        mock_broadcast.assert_called()
        call_args = mock_broadcast.call_args[0][0]
        assert call_args['channel'] == 'mining'
        assert call_args['event'] == 'stopped'

    def test_stop_mining_clears_thread_state(self, test_client, mining_handler):
        """Test that stopping mining clears internal thread state."""
        miner_addr = 'test_miner_cleanup'

        # Start mining
        test_client.post(
            '/mining/start',
            json={
                'miner_address': miner_addr,
                'threads': 2,
                'intensity': 'medium'
            }
        )

        assert miner_addr in mining_handler.mining_threads

        # Stop mining
        test_client.post(
            '/mining/stop',
            json={'miner_address': miner_addr}
        )

        assert miner_addr not in mining_handler.mining_threads


class TestMiningStatusEndpoint:
    """Test mining status endpoint (/mining/status)."""

    def test_get_status_not_mining(self, test_client, mining_handler):
        """Test getting status when not mining."""
        response = test_client.get(
            '/mining/status',
            query_string={'address': 'test_miner_123'}
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['is_mining'] is False
        assert data['miner_address'] == 'test_miner_123'

    def test_get_status_while_mining(self, test_client, mining_handler):
        """Test getting status while mining."""
        # Start mining
        test_client.post(
            '/mining/start',
            json={
                'miner_address': 'test_miner_123',
                'threads': 2,
                'intensity': 'medium'
            }
        )

        # Get status
        response = test_client.get(
            '/mining/status',
            query_string={'address': 'test_miner_123'}
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['is_mining'] is True
        assert data['miner_address'] == 'test_miner_123'
        assert data['threads'] == 2
        assert data['intensity'] == 'medium'
        assert 'hashrate' in data
        assert 'avg_hashrate' in data
        assert 'blocks_mined_today' in data
        assert 'xai_earned_today' in data
        assert 'shares_submitted' in data
        assert 'shares_accepted' in data
        assert 'acceptance_rate' in data
        assert 'current_difficulty' in data
        assert 'uptime' in data

    def test_get_status_without_address(self, test_client, mining_handler):
        """Test getting status without address parameter."""
        response = test_client.get('/mining/status')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'address parameter required' in data['error']

    def test_get_status_acceptance_rate(self, test_client, mining_handler):
        """Test that acceptance rate is calculated correctly."""
        miner_addr = 'test_miner_rate'

        # Start mining
        test_client.post(
            '/mining/start',
            json={
                'miner_address': miner_addr,
                'threads': 2,
                'intensity': 'medium'
            }
        )

        # Update stats manually for testing
        mining_handler.mining_stats[miner_addr]['shares_submitted'] = 100
        mining_handler.mining_stats[miner_addr]['shares_accepted'] = 95

        response = test_client.get(
            '/mining/status',
            query_string={'address': miner_addr}
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['acceptance_rate'] == 95.0

    def test_get_status_hashrate_history(self, test_client, mining_handler):
        """Test that hashrate history is used for average calculation."""
        miner_addr = 'test_miner_hashrate'

        # Start mining
        test_client.post(
            '/mining/start',
            json={
                'miner_address': miner_addr,
                'threads': 2,
                'intensity': 'medium'
            }
        )

        # Add hashrate history
        hashrates = [100, 110, 105, 115, 108]
        mining_handler.mining_stats[miner_addr]['hashrate_history'] = hashrates

        response = test_client.get(
            '/mining/status',
            query_string={'address': miner_addr}
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        # Check that avg_hashrate is present
        assert 'avg_hashrate' in data


class TestMiningStatistics:
    """Test mining statistics tracking."""

    def test_mining_stats_initialized(self, test_client, mining_handler):
        """Test that mining stats are initialized on start."""
        miner_addr = 'test_miner_stats'

        test_client.post(
            '/mining/start',
            json={
                'miner_address': miner_addr,
                'threads': 1,
                'intensity': 'low'
            }
        )

        assert miner_addr in mining_handler.mining_stats
        stats = mining_handler.mining_stats[miner_addr]
        assert 'started_at' in stats
        assert stats['blocks_mined'] == 0
        assert stats['xai_earned'] == 0
        assert stats['shares_submitted'] == 0
        assert stats['shares_accepted'] == 0
        assert 'hashrate_history' in stats

    def test_mining_thread_info_stored(self, test_client, mining_handler):
        """Test that mining thread info is stored correctly."""
        miner_addr = 'test_miner_thread'

        test_client.post(
            '/mining/start',
            json={
                'miner_address': miner_addr,
                'threads': 3,
                'intensity': 'high'
            }
        )

        assert miner_addr in mining_handler.mining_threads
        thread_info = mining_handler.mining_threads[miner_addr]
        assert thread_info['threads'] == 3
        assert thread_info['intensity'] == 'high'
        assert 'started_at' in thread_info
        assert 'thread' in thread_info


class TestMiningValidation:
    """Test mining input validation."""

    def test_validate_intensity_levels(self, test_client, mining_handler):
        """Test that only valid intensity levels are accepted."""
        valid_intensities = ['low', 'medium', 'high']

        for intensity in valid_intensities:
            response = test_client.post(
                '/mining/start',
                json={
                    'miner_address': f'test_miner_{intensity}',
                    'threads': 1,
                    'intensity': intensity
                }
            )
            assert response.status_code == 200

    def test_reject_invalid_intensity(self, test_client, mining_handler):
        """Test that invalid intensity levels are rejected."""
        invalid_intensities = ['extreme', 'none', '', 'MEDIUM', 123, None]

        for intensity in invalid_intensities:
            response = test_client.post(
                '/mining/start',
                json={
                    'miner_address': 'test_miner_invalid',
                    'threads': 1,
                    'intensity': intensity
                }
            )
            assert response.status_code == 400


class TestMiningWebSocketBroadcast:
    """Test WebSocket broadcast functionality."""

    def test_broadcast_on_mining_start(self, test_client, mining_handler, mock_broadcast):
        """Test that starting mining broadcasts to WebSocket."""
        test_client.post(
            '/mining/start',
            json={
                'miner_address': 'test_miner_ws',
                'threads': 2,
                'intensity': 'medium'
            }
        )

        assert mock_broadcast.called
        call_data = mock_broadcast.call_args[0][0]
        assert call_data['channel'] == 'mining'
        assert call_data['event'] == 'started'
        assert 'data' in call_data

    def test_broadcast_on_mining_stop(self, test_client, mining_handler, mock_broadcast):
        """Test that stopping mining broadcasts to WebSocket."""
        # Start first
        test_client.post(
            '/mining/start',
            json={
                'miner_address': 'test_miner_ws',
                'threads': 2,
                'intensity': 'medium'
            }
        )

        mock_broadcast.reset_mock()

        # Stop
        test_client.post(
            '/mining/stop',
            json={'miner_address': 'test_miner_ws'}
        )

        assert mock_broadcast.called
        call_data = mock_broadcast.call_args[0][0]
        assert call_data['channel'] == 'mining'
        assert call_data['event'] == 'stopped'


class TestMiningErrorHandling:
    """Test error handling in mining operations."""

    def test_missing_request_body(self, test_client, mining_handler):
        """Test handling of missing request body."""
        response = test_client.post('/mining/start')
        assert response.status_code in [400, 415]  # Bad request or unsupported media type

    def test_malformed_json(self, test_client, mining_handler):
        """Test handling of malformed JSON."""
        response = test_client.post(
            '/mining/start',
            data='{"invalid json',
            content_type='application/json'
        )
        assert response.status_code in [400, 415]

    def test_empty_miner_address(self, test_client, mining_handler):
        """Test handling of empty miner address."""
        response = test_client.post(
            '/mining/start',
            json={
                'miner_address': '',
                'threads': 1,
                'intensity': 'low'
            }
        )
        assert response.status_code == 400


class TestMiningMultipleMiners:
    """Test mining with multiple miners."""

    def test_multiple_miners_can_mine(self, test_client, mining_handler):
        """Test that multiple miners can mine simultaneously."""
        miners = ['miner_1', 'miner_2', 'miner_3']

        for miner in miners:
            response = test_client.post(
                '/mining/start',
                json={
                    'miner_address': miner,
                    'threads': 1,
                    'intensity': 'low'
                }
            )
            assert response.status_code == 200

        # Verify all are mining
        assert len(mining_handler.mining_threads) == 3

    def test_each_miner_has_separate_stats(self, test_client, mining_handler):
        """Test that each miner has separate statistics."""
        miners = ['miner_a', 'miner_b']

        for miner in miners:
            test_client.post(
                '/mining/start',
                json={
                    'miner_address': miner,
                    'threads': 1,
                    'intensity': 'low'
                }
            )

        # Verify separate stats
        assert 'miner_a' in mining_handler.mining_stats
        assert 'miner_b' in mining_handler.mining_stats
        assert mining_handler.mining_stats['miner_a'] is not mining_handler.mining_stats['miner_b']


class TestMiningDifficulty:
    """Test mining difficulty queries."""

    def test_status_includes_current_difficulty(self, test_client, mining_handler):
        """Test that status includes current blockchain difficulty."""
        # Start mining
        test_client.post(
            '/mining/start',
            json={
                'miner_address': 'test_miner_diff',
                'threads': 1,
                'intensity': 'low'
            }
        )

        response = test_client.get(
            '/mining/status',
            query_string={'address': 'test_miner_diff'}
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'current_difficulty' in data
        assert data['current_difficulty'] == 4  # From mock


class TestMiningUptime:
    """Test mining uptime tracking."""

    def test_uptime_increases(self, test_client, mining_handler):
        """Test that uptime increases over time."""
        miner_addr = 'test_miner_uptime'

        # Start mining
        test_client.post(
            '/mining/start',
            json={
                'miner_address': miner_addr,
                'threads': 1,
                'intensity': 'low'
            }
        )

        # Get initial uptime
        response1 = test_client.get(
            '/mining/status',
            query_string={'address': miner_addr}
        )
        uptime1 = json.loads(response1.data)['uptime']

        # Wait a bit
        time.sleep(0.1)

        # Get uptime again
        response2 = test_client.get(
            '/mining/status',
            query_string={'address': miner_addr}
        )
        uptime2 = json.loads(response2.data)['uptime']

        assert uptime2 > uptime1
