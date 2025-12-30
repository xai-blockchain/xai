"""Tests for the Validator Management Dashboard."""

import pytest
from unittest.mock import patch, MagicMock
import json
import time


class TestValidatorDashboard:
    """Test cases for the validator dashboard."""

    @pytest.fixture
    def app(self):
        """Create test Flask app."""
        from src.xai.validator_dashboard.validator_ui import app
        app.config['TESTING'] = True
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()

    def test_index_page_loads(self, client):
        """Test that the main page loads successfully."""
        response = client.get('/')
        assert response.status_code == 200
        assert b'Validator Dashboard' in response.data

    def test_index_page_contains_sections(self, client):
        """Test that the page contains all required sections."""
        response = client.get('/')
        html = response.data.decode('utf-8')

        assert 'Node Information' in html
        assert 'System Resources' in html
        assert 'Quick Actions' in html
        assert 'Connected Peers' in html
        assert 'Consensus Performance' in html

    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get('/health')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'healthy'
        assert 'timestamp' in data

    def test_api_status(self, client):
        """Test status API endpoint."""
        response = client.get('/api/status')
        assert response.status_code == 200
        data = json.loads(response.data)

        assert 'validator_address' in data
        assert 'node_version' in data
        assert 'block_height' in data
        assert 'peers' in data
        assert 'cpu_percent' in data
        assert 'memory_percent' in data
        assert 'disk_percent' in data

    def test_api_peers(self, client):
        """Test peers API endpoint."""
        response = client.get('/api/peers')
        assert response.status_code == 200
        data = json.loads(response.data)

        assert 'peers' in data
        assert isinstance(data['peers'], list)

    def test_api_claim_rewards(self, client):
        """Test claim rewards endpoint."""
        response = client.post('/api/claim-rewards')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True

    def test_api_restart(self, client):
        """Test restart endpoint."""
        response = client.post('/api/restart')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True

    def test_api_commission(self, client):
        """Test commission update endpoint."""
        response = client.post('/api/commission?rate=10')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert '10%' in data['message']

    def test_api_unjail(self, client):
        """Test unjail endpoint."""
        response = client.post('/api/unjail')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True


class TestValidatorFunctions:
    """Test helper functions in validator dashboard."""

    def test_format_uptime_seconds(self):
        """Test uptime formatting for seconds."""
        from src.xai.validator_dashboard.validator_ui import format_uptime

        assert format_uptime(30) == "0m"
        assert format_uptime(60) == "1m"

    def test_format_uptime_minutes(self):
        """Test uptime formatting for minutes."""
        from src.xai.validator_dashboard.validator_ui import format_uptime

        assert format_uptime(300) == "5m"
        assert format_uptime(1800) == "30m"

    def test_format_uptime_hours(self):
        """Test uptime formatting for hours."""
        from src.xai.validator_dashboard.validator_ui import format_uptime

        assert "h" in format_uptime(3600)
        assert "h" in format_uptime(7200)

    def test_format_uptime_days(self):
        """Test uptime formatting for days."""
        from src.xai.validator_dashboard.validator_ui import format_uptime

        result = format_uptime(86400)
        assert "d" in result

    def test_get_validator_status_has_system_metrics(self):
        """Test that validator status includes system metrics."""
        from src.xai.validator_dashboard.validator_ui import get_validator_status

        with patch('src.xai.validator_dashboard.validator_ui.requests.get') as mock_get:
            mock_get.side_effect = Exception("API unavailable")
            status = get_validator_status()

            assert 'cpu_percent' in status
            assert 'memory_percent' in status
            assert 'disk_percent' in status
            assert isinstance(status['cpu_percent'], float)
            assert isinstance(status['memory_percent'], float)
            assert isinstance(status['disk_percent'], float)

    def test_get_peers_returns_list(self):
        """Test that get_peers returns a list."""
        from src.xai.validator_dashboard.validator_ui import get_peers

        with patch('src.xai.validator_dashboard.validator_ui.requests.get') as mock_get:
            mock_get.side_effect = Exception("API unavailable")
            peers = get_peers()

            assert isinstance(peers, list)

    def test_get_alerts_detects_high_cpu(self):
        """Test that alerts detect high CPU usage."""
        from src.xai.validator_dashboard.validator_ui import get_alerts, get_validator_status

        with patch('src.xai.validator_dashboard.validator_ui.get_validator_status') as mock_status:
            mock_status.return_value = {
                'missed_blocks_24h': 0,
                'is_jailed': False,
                'cpu_percent': 95.0,
                'disk_percent': 50.0,
            }
            alerts = get_alerts()

            cpu_alert = any('CPU' in a['message'] for a in alerts)
            assert cpu_alert

    def test_get_alerts_detects_jailed_status(self):
        """Test that alerts detect jailed validator."""
        from src.xai.validator_dashboard.validator_ui import get_alerts

        with patch('src.xai.validator_dashboard.validator_ui.get_validator_status') as mock_status:
            mock_status.return_value = {
                'missed_blocks_24h': 0,
                'is_jailed': True,
                'cpu_percent': 50.0,
                'disk_percent': 50.0,
            }
            alerts = get_alerts()

            jail_alert = any('jailed' in a['message'].lower() for a in alerts)
            assert jail_alert

    def test_get_logs_returns_list(self):
        """Test that get_logs returns a list."""
        from src.xai.validator_dashboard.validator_ui import get_logs

        logs = get_logs()
        assert isinstance(logs, list)

        if logs:
            assert 'time' in logs[0]
            assert 'level' in logs[0]
            assert 'message' in logs[0]
