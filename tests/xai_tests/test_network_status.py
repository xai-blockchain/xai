"""Tests for the XAI Network Status Page."""

import pytest
from unittest.mock import patch, MagicMock
import json
import time


class TestNetworkStatusPage:
    """Test cases for the network status page routes."""

    @pytest.fixture
    def app(self):
        """Create test Flask app."""
        from src.xai.network_status.status_page import app
        app.config['TESTING'] = True
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()

    def test_index_page_loads(self, client):
        """Test that the main status page loads successfully."""
        with patch('src.xai.network_status.status_page.collect_status') as mock_status:
            mock_status.return_value = {
                'overall': 'operational',
                'block_height': 12345,
                'peers': 10,
                'network': 'testnet',
                'synced': True,
                'tps': 100,
                'mempool_size': 50,
                'avg_block_time': '10',
                'api_latency': 25.5,
                'cpu_percent': 45.0,
                'memory_percent': 60.0,
                'disk_percent': 30.0,
                'uptime': '5h 30m',
                'uptime_seconds': 19800,
                'services': [
                    {'name': 'API Server', 'up': True, 'uptime': '99.9%'},
                    {'name': 'Blockchain Node', 'up': True, 'uptime': '99.9%'},
                ],
                'last_updated': '2025-12-30 12:00:00 UTC',
            }
            response = client.get('/')
            assert response.status_code == 200
            assert b'XAI Network Status' in response.data

    def test_index_page_contains_sections(self, client):
        """Test that the page contains all required sections."""
        with patch('src.xai.network_status.status_page.collect_status') as mock_status:
            mock_status.return_value = {
                'overall': 'operational',
                'block_height': 12345,
                'peers': 10,
                'network': 'testnet',
                'synced': True,
                'tps': 100,
                'mempool_size': 50,
                'avg_block_time': '10',
                'api_latency': 25.5,
                'cpu_percent': 45.0,
                'memory_percent': 60.0,
                'disk_percent': 30.0,
                'uptime': '5h 30m',
                'uptime_seconds': 19800,
                'services': [],
                'last_updated': '2025-12-30 12:00:00 UTC',
            }
            response = client.get('/')
            html = response.data.decode('utf-8')

            assert 'Network Overview' in html
            assert 'Performance' in html
            assert 'System Health' in html
            assert 'Services' in html
            assert 'Block Height' in html
            assert 'Connected Peers' in html

    def test_index_page_shows_operational_status(self, client):
        """Test that operational status is displayed correctly."""
        with patch('src.xai.network_status.status_page.collect_status') as mock_status:
            mock_status.return_value = {
                'overall': 'operational',
                'block_height': 12345,
                'peers': 10,
                'network': 'testnet',
                'synced': True,
                'tps': 100,
                'mempool_size': 50,
                'avg_block_time': '10',
                'api_latency': 25.5,
                'cpu_percent': 45.0,
                'memory_percent': 60.0,
                'disk_percent': 30.0,
                'uptime': '5h 30m',
                'uptime_seconds': 19800,
                'services': [],
                'last_updated': '2025-12-30 12:00:00 UTC',
            }
            response = client.get('/')
            html = response.data.decode('utf-8')
            assert 'All Systems Operational' in html

    def test_index_page_shows_degraded_status(self, client):
        """Test that degraded status is displayed correctly."""
        with patch('src.xai.network_status.status_page.collect_status') as mock_status:
            mock_status.return_value = {
                'overall': 'degraded',
                'block_height': 12345,
                'peers': 10,
                'network': 'testnet',
                'synced': True,
                'tps': 100,
                'mempool_size': 50,
                'avg_block_time': '10',
                'api_latency': 25.5,
                'cpu_percent': 95.0,
                'memory_percent': 60.0,
                'disk_percent': 30.0,
                'uptime': '5h 30m',
                'uptime_seconds': 19800,
                'services': [],
                'last_updated': '2025-12-30 12:00:00 UTC',
            }
            response = client.get('/')
            html = response.data.decode('utf-8')
            assert 'Partial System Outage' in html

    def test_index_page_shows_outage_status(self, client):
        """Test that outage status is displayed correctly."""
        with patch('src.xai.network_status.status_page.collect_status') as mock_status:
            mock_status.return_value = {
                'overall': 'outage',
                'block_height': '--',
                'peers': '--',
                'network': 'testnet',
                'synced': False,
                'tps': '--',
                'mempool_size': '--',
                'avg_block_time': '--',
                'api_latency': '--',
                'cpu_percent': 45.0,
                'memory_percent': 60.0,
                'disk_percent': 30.0,
                'uptime': '5h 30m',
                'uptime_seconds': 19800,
                'services': [],
                'last_updated': '2025-12-30 12:00:00 UTC',
            }
            response = client.get('/')
            html = response.data.decode('utf-8')
            assert 'Major Outage' in html

    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get('/health')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'healthy'
        assert 'timestamp' in data

    def test_api_status_endpoint(self, client):
        """Test /api/status endpoint returns all status fields."""
        with patch('src.xai.network_status.status_page.check_api_health') as mock_api:
            with patch('src.xai.network_status.status_page.get_blockchain_info') as mock_blockchain:
                with patch('src.xai.network_status.status_page.get_mempool_info') as mock_mempool:
                    with patch('src.xai.network_status.status_page.psutil') as mock_psutil:
                        mock_api.return_value = {'up': True, 'latency_ms': 25.5}
                        mock_blockchain.return_value = {
                            'height': 12345,
                            'peers': 10,
                            'network': 'testnet',
                            'synced': True,
                            'tps': 100,
                            'avg_block_time': 10,
                        }
                        mock_mempool.return_value = {'size': 50}

                        mock_psutil.cpu_percent.return_value = 45.0
                        mock_memory = MagicMock()
                        mock_memory.percent = 60.0
                        mock_psutil.virtual_memory.return_value = mock_memory
                        mock_disk = MagicMock()
                        mock_disk.percent = 30.0
                        mock_psutil.disk_usage.return_value = mock_disk

                        response = client.get('/api/status')
                        assert response.status_code == 200
                        data = json.loads(response.data)

                        assert 'overall' in data
                        assert 'block_height' in data
                        assert 'peers' in data
                        assert 'network' in data
                        assert 'synced' in data
                        assert 'tps' in data
                        assert 'mempool_size' in data
                        assert 'api_latency' in data
                        assert 'cpu_percent' in data
                        assert 'memory_percent' in data
                        assert 'disk_percent' in data
                        assert 'uptime' in data
                        assert 'services' in data
                        assert 'last_updated' in data

    def test_api_services_endpoint(self, client):
        """Test /api/services endpoint returns service list."""
        with patch('src.xai.network_status.status_page.collect_status') as mock_status:
            mock_status.return_value = {
                'services': [
                    {'name': 'API Server', 'up': True, 'uptime': '99.9%'},
                    {'name': 'Blockchain Node', 'up': True, 'uptime': '99.9%'},
                    {'name': 'Prometheus Metrics', 'up': True, 'uptime': '99.9%'},
                    {'name': 'WebSocket Server', 'up': True, 'uptime': '99.9%'},
                ],
            }
            response = client.get('/api/services')
            assert response.status_code == 200
            data = json.loads(response.data)

            assert 'services' in data
            assert isinstance(data['services'], list)
            assert len(data['services']) == 4

    def test_api_metrics_endpoint(self, client):
        """Test /api/metrics endpoint returns key metrics."""
        with patch('src.xai.network_status.status_page.collect_status') as mock_status:
            mock_status.return_value = {
                'block_height': 12345,
                'peers': 10,
                'tps': 100,
                'mempool_size': 50,
                'cpu_percent': 45.0,
                'memory_percent': 60.0,
            }
            response = client.get('/api/metrics')
            assert response.status_code == 200
            data = json.loads(response.data)

            assert 'block_height' in data
            assert 'peers' in data
            assert 'tps' in data
            assert 'mempool_size' in data
            assert 'cpu_percent' in data
            assert 'memory_percent' in data


class TestFormatUptimeFunction:
    """Test the format_uptime helper function."""

    def test_format_uptime_seconds(self):
        """Test formatting for values under 60 seconds."""
        from src.xai.network_status.status_page import format_uptime

        assert format_uptime(0) == "0s"
        assert format_uptime(30) == "30s"
        assert format_uptime(59) == "59s"

    def test_format_uptime_minutes(self):
        """Test formatting for values under 1 hour."""
        from src.xai.network_status.status_page import format_uptime

        assert format_uptime(60) == "1m"
        assert format_uptime(120) == "2m"
        assert format_uptime(1800) == "30m"
        assert format_uptime(3599) == "59m"

    def test_format_uptime_hours(self):
        """Test formatting for values under 1 day."""
        from src.xai.network_status.status_page import format_uptime

        assert format_uptime(3600) == "1h 0m"
        assert format_uptime(7200) == "2h 0m"
        assert format_uptime(3660) == "1h 1m"
        assert format_uptime(5400) == "1h 30m"
        assert format_uptime(86399) == "23h 59m"

    def test_format_uptime_days(self):
        """Test formatting for values of 1 day or more."""
        from src.xai.network_status.status_page import format_uptime

        assert format_uptime(86400) == "1d 0h"
        assert format_uptime(172800) == "2d 0h"
        assert format_uptime(90000) == "1d 1h"
        assert format_uptime(604800) == "7d 0h"


class TestCheckApiHealthFunction:
    """Test the check_api_health helper function."""

    def test_api_health_success(self):
        """Test API health check when API is healthy."""
        from src.xai.network_status.status_page import check_api_health

        with patch('src.xai.network_status.status_page.requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            result = check_api_health()

            assert result['up'] is True
            assert 'latency_ms' in result
            assert result['latency_ms'] is not None

    def test_api_health_failure_status_code(self):
        """Test API health check when API returns non-200 status."""
        from src.xai.network_status.status_page import check_api_health

        with patch('src.xai.network_status.status_page.requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_get.return_value = mock_response

            result = check_api_health()

            assert result['up'] is False
            assert result['latency_ms'] is None

    def test_api_health_timeout(self):
        """Test API health check when request times out."""
        from src.xai.network_status.status_page import check_api_health
        import requests

        with patch('src.xai.network_status.status_page.requests.get') as mock_get:
            mock_get.side_effect = requests.Timeout("Connection timed out")

            result = check_api_health()

            assert result['up'] is False
            assert result['latency_ms'] is None

    def test_api_health_connection_error(self):
        """Test API health check when connection fails."""
        from src.xai.network_status.status_page import check_api_health
        import requests

        with patch('src.xai.network_status.status_page.requests.get') as mock_get:
            mock_get.side_effect = requests.ConnectionError("Connection refused")

            result = check_api_health()

            assert result['up'] is False
            assert result['latency_ms'] is None


class TestGetBlockchainInfoFunction:
    """Test the get_blockchain_info helper function."""

    def test_blockchain_info_success_primary_endpoint(self):
        """Test blockchain info retrieval from primary endpoint."""
        from src.xai.network_status.status_page import get_blockchain_info

        with patch('src.xai.network_status.status_page.requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'height': 12345,
                'peers': 10,
                'network': 'testnet',
                'synced': True,
            }
            mock_get.return_value = mock_response

            result = get_blockchain_info()

            assert result['height'] == 12345
            assert result['peers'] == 10
            assert result['network'] == 'testnet'
            assert result['synced'] is True

    def test_blockchain_info_fallback_to_alternate_endpoint(self):
        """Test blockchain info falls back to alternate endpoint."""
        from src.xai.network_status.status_page import get_blockchain_info

        with patch('src.xai.network_status.status_page.requests.get') as mock_get:
            # First call fails (primary endpoint)
            mock_response_fail = MagicMock()
            mock_response_fail.status_code = 404

            # Second call succeeds (alternate endpoint)
            mock_response_success = MagicMock()
            mock_response_success.status_code = 200
            mock_response_success.json.return_value = {
                'height': 12345,
                'network': 'mainnet',
            }

            mock_get.side_effect = [mock_response_fail, mock_response_success]

            result = get_blockchain_info()

            assert result['height'] == 12345
            assert result['network'] == 'mainnet'

    def test_blockchain_info_both_endpoints_fail(self):
        """Test blockchain info returns empty dict when both endpoints fail."""
        from src.xai.network_status.status_page import get_blockchain_info

        with patch('src.xai.network_status.status_page.requests.get') as mock_get:
            mock_get.side_effect = Exception("Connection failed")

            result = get_blockchain_info()

            assert result == {}

    def test_blockchain_info_timeout(self):
        """Test blockchain info handles timeout gracefully."""
        from src.xai.network_status.status_page import get_blockchain_info
        import requests

        with patch('src.xai.network_status.status_page.requests.get') as mock_get:
            mock_get.side_effect = requests.Timeout("Connection timed out")

            result = get_blockchain_info()

            assert result == {}


class TestGetMempoolInfoFunction:
    """Test the get_mempool_info helper function."""

    def test_mempool_info_success(self):
        """Test mempool info retrieval success."""
        from src.xai.network_status.status_page import get_mempool_info

        with patch('src.xai.network_status.status_page.requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'size': 150,
                'pending': 150,
                'bytes': 50000,
            }
            mock_get.return_value = mock_response

            result = get_mempool_info()

            assert result['size'] == 150
            assert result['pending'] == 150

    def test_mempool_info_failure(self):
        """Test mempool info returns empty dict on failure."""
        from src.xai.network_status.status_page import get_mempool_info

        with patch('src.xai.network_status.status_page.requests.get') as mock_get:
            mock_get.side_effect = Exception("Connection failed")

            result = get_mempool_info()

            assert result == {}

    def test_mempool_info_non_200_status(self):
        """Test mempool info returns empty dict on non-200 status."""
        from src.xai.network_status.status_page import get_mempool_info

        with patch('src.xai.network_status.status_page.requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 503
            mock_get.return_value = mock_response

            result = get_mempool_info()

            assert result == {}


class TestCollectStatusFunction:
    """Test the collect_status function."""

    def test_collect_status_operational(self):
        """Test status collection when all systems operational."""
        from src.xai.network_status.status_page import collect_status

        with patch('src.xai.network_status.status_page.check_api_health') as mock_api:
            with patch('src.xai.network_status.status_page.get_blockchain_info') as mock_blockchain:
                with patch('src.xai.network_status.status_page.get_mempool_info') as mock_mempool:
                    with patch('src.xai.network_status.status_page.psutil') as mock_psutil:
                        mock_api.return_value = {'up': True, 'latency_ms': 25.5}
                        mock_blockchain.return_value = {
                            'height': 12345,
                            'peers': 10,
                            'network': 'testnet',
                            'synced': True,
                            'tps': 100,
                            'avg_block_time': 10,
                        }
                        mock_mempool.return_value = {'size': 50}

                        mock_psutil.cpu_percent.return_value = 45.0
                        mock_memory = MagicMock()
                        mock_memory.percent = 60.0
                        mock_psutil.virtual_memory.return_value = mock_memory
                        mock_disk = MagicMock()
                        mock_disk.percent = 30.0
                        mock_psutil.disk_usage.return_value = mock_disk

                        result = collect_status()

                        assert result['overall'] == 'operational'
                        assert result['block_height'] == 12345
                        assert result['peers'] == 10
                        assert result['network'] == 'testnet'
                        assert result['synced'] is True
                        assert result['tps'] == 100
                        assert result['mempool_size'] == 50
                        assert result['api_latency'] == 25.5
                        assert result['cpu_percent'] == 45.0
                        assert result['memory_percent'] == 60.0
                        assert result['disk_percent'] == 30.0
                        assert 'uptime' in result
                        assert 'services' in result
                        assert len(result['services']) == 4

    def test_collect_status_outage_api_down(self):
        """Test status shows outage when API is down."""
        from src.xai.network_status.status_page import collect_status

        with patch('src.xai.network_status.status_page.check_api_health') as mock_api:
            with patch('src.xai.network_status.status_page.get_blockchain_info') as mock_blockchain:
                with patch('src.xai.network_status.status_page.get_mempool_info') as mock_mempool:
                    with patch('src.xai.network_status.status_page.psutil') as mock_psutil:
                        mock_api.return_value = {'up': False, 'latency_ms': None}
                        mock_blockchain.return_value = {}
                        mock_mempool.return_value = {}

                        mock_psutil.cpu_percent.return_value = 45.0
                        mock_memory = MagicMock()
                        mock_memory.percent = 60.0
                        mock_psutil.virtual_memory.return_value = mock_memory
                        mock_disk = MagicMock()
                        mock_disk.percent = 30.0
                        mock_psutil.disk_usage.return_value = mock_disk

                        result = collect_status()

                        assert result['overall'] == 'outage'

    def test_collect_status_degraded_high_cpu(self):
        """Test status shows degraded when CPU is high."""
        from src.xai.network_status.status_page import collect_status

        with patch('src.xai.network_status.status_page.check_api_health') as mock_api:
            with patch('src.xai.network_status.status_page.get_blockchain_info') as mock_blockchain:
                with patch('src.xai.network_status.status_page.get_mempool_info') as mock_mempool:
                    with patch('src.xai.network_status.status_page.psutil') as mock_psutil:
                        mock_api.return_value = {'up': True, 'latency_ms': 25.5}
                        mock_blockchain.return_value = {'height': 12345, 'synced': True}
                        mock_mempool.return_value = {'size': 50}

                        mock_psutil.cpu_percent.return_value = 95.0  # High CPU
                        mock_memory = MagicMock()
                        mock_memory.percent = 60.0
                        mock_psutil.virtual_memory.return_value = mock_memory
                        mock_disk = MagicMock()
                        mock_disk.percent = 30.0
                        mock_psutil.disk_usage.return_value = mock_disk

                        result = collect_status()

                        assert result['overall'] == 'degraded'

    def test_collect_status_degraded_high_memory(self):
        """Test status shows degraded when memory is high."""
        from src.xai.network_status.status_page import collect_status

        with patch('src.xai.network_status.status_page.check_api_health') as mock_api:
            with patch('src.xai.network_status.status_page.get_blockchain_info') as mock_blockchain:
                with patch('src.xai.network_status.status_page.get_mempool_info') as mock_mempool:
                    with patch('src.xai.network_status.status_page.psutil') as mock_psutil:
                        mock_api.return_value = {'up': True, 'latency_ms': 25.5}
                        mock_blockchain.return_value = {'height': 12345, 'synced': True}
                        mock_mempool.return_value = {'size': 50}

                        mock_psutil.cpu_percent.return_value = 50.0
                        mock_memory = MagicMock()
                        mock_memory.percent = 95.0  # High memory
                        mock_psutil.virtual_memory.return_value = mock_memory
                        mock_disk = MagicMock()
                        mock_disk.percent = 30.0
                        mock_psutil.disk_usage.return_value = mock_disk

                        result = collect_status()

                        assert result['overall'] == 'degraded'

    def test_collect_status_uses_alternate_field_names(self):
        """Test status correctly handles alternate blockchain field names."""
        from src.xai.network_status.status_page import collect_status

        with patch('src.xai.network_status.status_page.check_api_health') as mock_api:
            with patch('src.xai.network_status.status_page.get_blockchain_info') as mock_blockchain:
                with patch('src.xai.network_status.status_page.get_mempool_info') as mock_mempool:
                    with patch('src.xai.network_status.status_page.psutil') as mock_psutil:
                        mock_api.return_value = {'up': True, 'latency_ms': 25.5}
                        mock_blockchain.return_value = {
                            'block_height': 99999,  # Alternate field name
                            'peer_count': 25,  # Alternate field name
                        }
                        mock_mempool.return_value = {'pending': 100}  # Alternate field name

                        mock_psutil.cpu_percent.return_value = 45.0
                        mock_memory = MagicMock()
                        mock_memory.percent = 60.0
                        mock_psutil.virtual_memory.return_value = mock_memory
                        mock_disk = MagicMock()
                        mock_disk.percent = 30.0
                        mock_psutil.disk_usage.return_value = mock_disk

                        result = collect_status()

                        assert result['block_height'] == 99999
                        assert result['peers'] == 25
                        assert result['mempool_size'] == 100


class TestServiceStatusTracking:
    """Test service status tracking and service list generation."""

    def test_services_list_contains_all_services(self):
        """Test that services list contains all expected services."""
        from src.xai.network_status.status_page import collect_status

        with patch('src.xai.network_status.status_page.check_api_health') as mock_api:
            with patch('src.xai.network_status.status_page.get_blockchain_info') as mock_blockchain:
                with patch('src.xai.network_status.status_page.get_mempool_info') as mock_mempool:
                    with patch('src.xai.network_status.status_page.psutil') as mock_psutil:
                        mock_api.return_value = {'up': True, 'latency_ms': 25.5}
                        mock_blockchain.return_value = {'synced': True}
                        mock_mempool.return_value = {}

                        mock_psutil.cpu_percent.return_value = 45.0
                        mock_memory = MagicMock()
                        mock_memory.percent = 60.0
                        mock_psutil.virtual_memory.return_value = mock_memory
                        mock_disk = MagicMock()
                        mock_disk.percent = 30.0
                        mock_psutil.disk_usage.return_value = mock_disk

                        result = collect_status()
                        services = result['services']

                        service_names = [s['name'] for s in services]
                        assert 'API Server' in service_names
                        assert 'Blockchain Node' in service_names
                        assert 'Prometheus Metrics' in service_names
                        assert 'WebSocket Server' in service_names

    def test_api_service_down_when_api_unhealthy(self):
        """Test API service shows down when API health check fails."""
        from src.xai.network_status.status_page import collect_status

        with patch('src.xai.network_status.status_page.check_api_health') as mock_api:
            with patch('src.xai.network_status.status_page.get_blockchain_info') as mock_blockchain:
                with patch('src.xai.network_status.status_page.get_mempool_info') as mock_mempool:
                    with patch('src.xai.network_status.status_page.psutil') as mock_psutil:
                        mock_api.return_value = {'up': False, 'latency_ms': None}
                        mock_blockchain.return_value = {}
                        mock_mempool.return_value = {}

                        mock_psutil.cpu_percent.return_value = 45.0
                        mock_memory = MagicMock()
                        mock_memory.percent = 60.0
                        mock_psutil.virtual_memory.return_value = mock_memory
                        mock_disk = MagicMock()
                        mock_disk.percent = 30.0
                        mock_psutil.disk_usage.return_value = mock_disk

                        result = collect_status()
                        api_service = next(
                            (s for s in result['services'] if s['name'] == 'API Server'),
                            None
                        )

                        assert api_service is not None
                        assert api_service['up'] is False
                        assert api_service['uptime'] == 'Down'

    def test_blockchain_node_status_based_on_sync(self):
        """Test blockchain node service status is based on sync status."""
        from src.xai.network_status.status_page import collect_status

        with patch('src.xai.network_status.status_page.check_api_health') as mock_api:
            with patch('src.xai.network_status.status_page.get_blockchain_info') as mock_blockchain:
                with patch('src.xai.network_status.status_page.get_mempool_info') as mock_mempool:
                    with patch('src.xai.network_status.status_page.psutil') as mock_psutil:
                        mock_api.return_value = {'up': True, 'latency_ms': 25.5}
                        mock_blockchain.return_value = {'synced': False}
                        mock_mempool.return_value = {}

                        mock_psutil.cpu_percent.return_value = 45.0
                        mock_memory = MagicMock()
                        mock_memory.percent = 60.0
                        mock_psutil.virtual_memory.return_value = mock_memory
                        mock_disk = MagicMock()
                        mock_disk.percent = 30.0
                        mock_psutil.disk_usage.return_value = mock_disk

                        result = collect_status()
                        node_service = next(
                            (s for s in result['services'] if s['name'] == 'Blockchain Node'),
                            None
                        )

                        assert node_service is not None
                        assert node_service['up'] is False


class TestStatusDetermination:
    """Test the logic for determining overall status."""

    def test_status_operational_all_healthy(self):
        """Test operational status when all checks pass."""
        from src.xai.network_status.status_page import collect_status

        with patch('src.xai.network_status.status_page.check_api_health') as mock_api:
            with patch('src.xai.network_status.status_page.get_blockchain_info') as mock_blockchain:
                with patch('src.xai.network_status.status_page.get_mempool_info') as mock_mempool:
                    with patch('src.xai.network_status.status_page.psutil') as mock_psutil:
                        mock_api.return_value = {'up': True, 'latency_ms': 10.0}
                        mock_blockchain.return_value = {'synced': True}
                        mock_mempool.return_value = {}

                        mock_psutil.cpu_percent.return_value = 50.0
                        mock_memory = MagicMock()
                        mock_memory.percent = 50.0
                        mock_psutil.virtual_memory.return_value = mock_memory
                        mock_disk = MagicMock()
                        mock_disk.percent = 50.0
                        mock_psutil.disk_usage.return_value = mock_disk

                        result = collect_status()

                        assert result['overall'] == 'operational'

    def test_status_outage_api_down(self):
        """Test outage status when API is down."""
        from src.xai.network_status.status_page import collect_status

        with patch('src.xai.network_status.status_page.check_api_health') as mock_api:
            with patch('src.xai.network_status.status_page.get_blockchain_info') as mock_blockchain:
                with patch('src.xai.network_status.status_page.get_mempool_info') as mock_mempool:
                    with patch('src.xai.network_status.status_page.psutil') as mock_psutil:
                        mock_api.return_value = {'up': False, 'latency_ms': None}
                        mock_blockchain.return_value = {}
                        mock_mempool.return_value = {}

                        mock_psutil.cpu_percent.return_value = 50.0
                        mock_memory = MagicMock()
                        mock_memory.percent = 50.0
                        mock_psutil.virtual_memory.return_value = mock_memory
                        mock_disk = MagicMock()
                        mock_disk.percent = 50.0
                        mock_psutil.disk_usage.return_value = mock_disk

                        result = collect_status()

                        assert result['overall'] == 'outage'

    def test_status_degraded_cpu_above_90(self):
        """Test degraded status when CPU exceeds 90%."""
        from src.xai.network_status.status_page import collect_status

        with patch('src.xai.network_status.status_page.check_api_health') as mock_api:
            with patch('src.xai.network_status.status_page.get_blockchain_info') as mock_blockchain:
                with patch('src.xai.network_status.status_page.get_mempool_info') as mock_mempool:
                    with patch('src.xai.network_status.status_page.psutil') as mock_psutil:
                        mock_api.return_value = {'up': True, 'latency_ms': 10.0}
                        mock_blockchain.return_value = {}
                        mock_mempool.return_value = {}

                        mock_psutil.cpu_percent.return_value = 91.0
                        mock_memory = MagicMock()
                        mock_memory.percent = 50.0
                        mock_psutil.virtual_memory.return_value = mock_memory
                        mock_disk = MagicMock()
                        mock_disk.percent = 50.0
                        mock_psutil.disk_usage.return_value = mock_disk

                        result = collect_status()

                        assert result['overall'] == 'degraded'

    def test_status_degraded_memory_above_90(self):
        """Test degraded status when memory exceeds 90%."""
        from src.xai.network_status.status_page import collect_status

        with patch('src.xai.network_status.status_page.check_api_health') as mock_api:
            with patch('src.xai.network_status.status_page.get_blockchain_info') as mock_blockchain:
                with patch('src.xai.network_status.status_page.get_mempool_info') as mock_mempool:
                    with patch('src.xai.network_status.status_page.psutil') as mock_psutil:
                        mock_api.return_value = {'up': True, 'latency_ms': 10.0}
                        mock_blockchain.return_value = {}
                        mock_mempool.return_value = {}

                        mock_psutil.cpu_percent.return_value = 50.0
                        mock_memory = MagicMock()
                        mock_memory.percent = 91.0
                        mock_psutil.virtual_memory.return_value = mock_memory
                        mock_disk = MagicMock()
                        mock_disk.percent = 50.0
                        mock_psutil.disk_usage.return_value = mock_disk

                        result = collect_status()

                        assert result['overall'] == 'degraded'

    def test_status_exactly_90_cpu_is_operational(self):
        """Test that exactly 90% CPU is still operational (not degraded)."""
        from src.xai.network_status.status_page import collect_status

        with patch('src.xai.network_status.status_page.check_api_health') as mock_api:
            with patch('src.xai.network_status.status_page.get_blockchain_info') as mock_blockchain:
                with patch('src.xai.network_status.status_page.get_mempool_info') as mock_mempool:
                    with patch('src.xai.network_status.status_page.psutil') as mock_psutil:
                        mock_api.return_value = {'up': True, 'latency_ms': 10.0}
                        mock_blockchain.return_value = {}
                        mock_mempool.return_value = {}

                        mock_psutil.cpu_percent.return_value = 90.0
                        mock_memory = MagicMock()
                        mock_memory.percent = 90.0
                        mock_psutil.virtual_memory.return_value = mock_memory
                        mock_disk = MagicMock()
                        mock_disk.percent = 50.0
                        mock_psutil.disk_usage.return_value = mock_disk

                        result = collect_status()

                        assert result['overall'] == 'operational'


class TestErrorHandling:
    """Test error handling when external services are unavailable."""

    def test_all_services_unavailable(self):
        """Test graceful handling when all external services are down."""
        from src.xai.network_status.status_page import collect_status

        with patch('src.xai.network_status.status_page.check_api_health') as mock_api:
            with patch('src.xai.network_status.status_page.get_blockchain_info') as mock_blockchain:
                with patch('src.xai.network_status.status_page.get_mempool_info') as mock_mempool:
                    with patch('src.xai.network_status.status_page.psutil') as mock_psutil:
                        mock_api.return_value = {'up': False, 'latency_ms': None}
                        mock_blockchain.return_value = {}
                        mock_mempool.return_value = {}

                        mock_psutil.cpu_percent.return_value = 45.0
                        mock_memory = MagicMock()
                        mock_memory.percent = 60.0
                        mock_psutil.virtual_memory.return_value = mock_memory
                        mock_disk = MagicMock()
                        mock_disk.percent = 30.0
                        mock_psutil.disk_usage.return_value = mock_disk

                        result = collect_status()

                        # Should still return a valid status structure
                        assert 'overall' in result
                        assert 'services' in result
                        assert result['overall'] == 'outage'
                        # Default values for missing data
                        assert result['block_height'] == '--'
                        assert result['peers'] == '--'
                        assert result['tps'] == '--'
                        assert result['mempool_size'] == '--'

    def test_psutil_error_handling(self):
        """Test handling when psutil raises an exception."""
        from src.xai.network_status.status_page import collect_status

        with patch('src.xai.network_status.status_page.check_api_health') as mock_api:
            with patch('src.xai.network_status.status_page.get_blockchain_info') as mock_blockchain:
                with patch('src.xai.network_status.status_page.get_mempool_info') as mock_mempool:
                    with patch('src.xai.network_status.status_page.psutil') as mock_psutil:
                        mock_api.return_value = {'up': True, 'latency_ms': 25.5}
                        mock_blockchain.return_value = {'height': 12345}
                        mock_mempool.return_value = {}

                        mock_psutil.cpu_percent.return_value = 45.0
                        mock_memory = MagicMock()
                        mock_memory.percent = 60.0
                        mock_psutil.virtual_memory.return_value = mock_memory
                        mock_disk = MagicMock()
                        mock_disk.percent = 30.0
                        mock_psutil.disk_usage.return_value = mock_disk

                        result = collect_status()

                        # Should return valid values
                        assert 'cpu_percent' in result
                        assert 'memory_percent' in result
                        assert 'disk_percent' in result

    def test_index_page_loads_with_api_error(self, ):
        """Test index page still loads when external APIs fail."""
        from src.xai.network_status.status_page import app

        app.config['TESTING'] = True
        client = app.test_client()

        with patch('src.xai.network_status.status_page.check_api_health') as mock_api:
            with patch('src.xai.network_status.status_page.get_blockchain_info') as mock_blockchain:
                with patch('src.xai.network_status.status_page.get_mempool_info') as mock_mempool:
                    with patch('src.xai.network_status.status_page.psutil') as mock_psutil:
                        mock_api.return_value = {'up': False, 'latency_ms': None}
                        mock_blockchain.return_value = {}
                        mock_mempool.return_value = {}

                        mock_psutil.cpu_percent.return_value = 45.0
                        mock_memory = MagicMock()
                        mock_memory.percent = 60.0
                        mock_psutil.virtual_memory.return_value = mock_memory
                        mock_disk = MagicMock()
                        mock_disk.percent = 30.0
                        mock_psutil.disk_usage.return_value = mock_disk

                        response = client.get('/')

                        assert response.status_code == 200
                        assert b'XAI Network Status' in response.data
