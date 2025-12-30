"""Tests for the Staking Dashboard UI."""

import pytest
from unittest.mock import patch, MagicMock
from decimal import Decimal
import json


class TestStakingDashboard:
    """Test cases for the staking dashboard."""

    @pytest.fixture
    def app(self):
        """Create test Flask app."""
        from src.xai.staking_dashboard.staking_dashboard import app
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
        assert b'XAI Staking' in response.data

    def test_index_page_contains_sections(self, client):
        """Test that the page contains all required sections."""
        response = client.get('/')
        html = response.data.decode('utf-8')

        assert 'Total Staked' in html
        assert 'Annual Yield' in html
        assert 'Active Validators' in html
        assert 'Your Stake' in html

    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get('/health')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'healthy'
        assert 'timestamp' in data

    def test_api_staking_info(self, client):
        """Test staking info API endpoint."""
        response = client.get('/api/staking/info')
        assert response.status_code == 200
        data = json.loads(response.data)

        assert 'total_staked' in data
        assert 'apy' in data
        assert 'unbonding_period_formatted' in data

    def test_api_validators(self, client):
        """Test validators API endpoint."""
        response = client.get('/api/staking/validators')
        assert response.status_code == 200
        data = json.loads(response.data)

        assert 'validators' in data
        assert isinstance(data['validators'], list)

    def test_api_delegations_empty_address(self, client):
        """Test delegations endpoint with empty address."""
        response = client.get('/api/staking/delegations/')
        # Should handle gracefully - Flask may return 404 for empty path
        assert response.status_code in [200, 404]

    def test_api_rewards_with_address(self, client):
        """Test rewards endpoint with address."""
        response = client.get('/api/staking/rewards/XAI1test123')
        assert response.status_code == 200
        data = json.loads(response.data)

        assert 'address' in data
        assert 'total_rewards' in data

    def test_api_delegate_missing_fields(self, client):
        """Test delegate endpoint with missing fields."""
        response = client.post('/api/staking/delegate',
                               data=json.dumps({}),
                               content_type='application/json')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False

    def test_api_delegate_with_data(self, client):
        """Test delegate endpoint with proper data."""
        with patch('src.xai.staking_dashboard.staking_dashboard.api_post') as mock_post:
            mock_post.return_value = {
                'status_code': 200,
                'data': {'tx_hash': 'txhash123', 'success': True}
            }

            delegate_data = {
                'address': 'XAI1test123',
                'validator': 'XAI1validator123',
                'amount': 1000000000000000000
            }
            response = client.post('/api/staking/delegate',
                                   data=json.dumps(delegate_data),
                                   content_type='application/json')
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True

    def test_api_undelegate_missing_fields(self, client):
        """Test undelegate endpoint with missing fields."""
        response = client.post('/api/staking/undelegate',
                               data=json.dumps({'address': 'test'}),
                               content_type='application/json')
        assert response.status_code == 400

    def test_api_claim_rewards_missing_fields(self, client):
        """Test claim rewards endpoint with missing fields."""
        response = client.post('/api/staking/claim-rewards',
                               data=json.dumps({'address': 'test'}),
                               content_type='application/json')
        assert response.status_code == 400

    def test_api_claim_all_missing_address(self, client):
        """Test claim all endpoint with missing address."""
        response = client.post('/api/staking/claim-all',
                               data=json.dumps({}),
                               content_type='application/json')
        assert response.status_code == 400


class TestStakingFunctions:
    """Test helper functions in staking dashboard."""

    def test_format_token_amount_zero(self):
        """Test formatting zero amount."""
        from src.xai.staking_dashboard.staking_dashboard import format_token_amount

        assert format_token_amount(0) == "0"

    def test_format_token_amount_small(self):
        """Test formatting small amounts."""
        from src.xai.staking_dashboard.staking_dashboard import format_token_amount

        # 1 token (10^18 wei)
        result = format_token_amount(10**18)
        assert "1" in result

    def test_format_token_amount_thousands(self):
        """Test formatting thousands."""
        from src.xai.staking_dashboard.staking_dashboard import format_token_amount

        # 5000 tokens
        result = format_token_amount(5000 * 10**18)
        assert "K" in result

    def test_format_token_amount_millions(self):
        """Test formatting millions."""
        from src.xai.staking_dashboard.staking_dashboard import format_token_amount

        # 5 million tokens
        result = format_token_amount(5000000 * 10**18)
        assert "M" in result

    def test_format_percentage(self):
        """Test percentage formatting."""
        from src.xai.staking_dashboard.staking_dashboard import format_percentage

        assert format_percentage(500) == "5.00%"
        assert format_percentage(1000) == "10.00%"
        assert format_percentage(100) == "1.00%"

    def test_format_duration_minutes(self):
        """Test duration formatting for minutes."""
        from src.xai.staking_dashboard.staking_dashboard import format_duration

        assert format_duration(300) == "5m"
        assert format_duration(1800) == "30m"

    def test_format_duration_hours(self):
        """Test duration formatting for hours."""
        from src.xai.staking_dashboard.staking_dashboard import format_duration

        result = format_duration(3600)
        assert "1h" in result

        result = format_duration(7200)
        assert "2h" in result

    def test_format_duration_days(self):
        """Test duration formatting for days."""
        from src.xai.staking_dashboard.staking_dashboard import format_duration

        # 21 days
        result = format_duration(21 * 24 * 3600)
        assert "21d" in result

    def test_format_timestamp_zero(self):
        """Test timestamp formatting for zero."""
        from src.xai.staking_dashboard.staking_dashboard import format_timestamp

        assert format_timestamp(0) == "N/A"

    def test_format_timestamp_valid(self):
        """Test timestamp formatting for valid timestamp."""
        from src.xai.staking_dashboard.staking_dashboard import format_timestamp
        import time

        result = format_timestamp(time.time())
        assert result != "N/A"
        assert "-" in result  # Date format

    def test_get_staking_stats_returns_defaults(self):
        """Test that stats return defaults when API unavailable."""
        from src.xai.staking_dashboard.staking_dashboard import get_staking_stats

        with patch('src.xai.staking_dashboard.staking_dashboard.api_get') as mock_get:
            mock_get.return_value = {}
            stats = get_staking_stats()

            assert 'total_staked' in stats
            assert 'apy' in stats
            assert 'unbonding_period_formatted' in stats

    def test_get_validators_returns_list(self):
        """Test that get_validators returns a list."""
        from src.xai.staking_dashboard.staking_dashboard import get_validators

        with patch('src.xai.staking_dashboard.staking_dashboard.api_get') as mock_get:
            mock_get.return_value = {}
            validators = get_validators()

            assert isinstance(validators, list)

    def test_get_user_staking_info_empty_address(self):
        """Test user staking info with empty address."""
        from src.xai.staking_dashboard.staking_dashboard import get_user_staking_info

        info = get_user_staking_info("")

        assert info['address'] == ""
        assert info['total_staked'] == 0
        assert info['delegations'] == []

    def test_get_staking_history_empty_address(self):
        """Test staking history with empty address."""
        from src.xai.staking_dashboard.staking_dashboard import get_staking_history

        history = get_staking_history("")
        assert history == []
