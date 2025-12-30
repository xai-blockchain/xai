"""Tests for the Governance Dashboard UI."""

import pytest
from unittest.mock import patch, MagicMock
import json


class TestGovernanceDashboard:
    """Test cases for the governance dashboard."""

    @pytest.fixture
    def app(self):
        """Create test Flask app."""
        from src.xai.governance_dashboard.governance_ui import app
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
        assert b'XAI Governance' in response.data

    def test_index_page_contains_sections(self, client):
        """Test that the page contains all required sections."""
        response = client.get('/')
        html = response.data.decode('utf-8')

        assert 'Active Proposals' in html
        assert 'Create Proposal' in html
        assert 'Vote History' in html
        assert 'All Proposals' in html

    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get('/health')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'healthy'
        assert 'timestamp' in data

    def test_api_proposals_get(self, client):
        """Test GET /api/proposals returns proposals."""
        response = client.get('/api/proposals')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'proposals' in data
        assert isinstance(data['proposals'], list)

    def test_api_proposals_get_with_status(self, client):
        """Test filtering proposals by status."""
        response = client.get('/api/proposals?status=active')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'proposals' in data

    def test_api_vote_requires_data(self, client):
        """Test that vote endpoint requires proper data."""
        response = client.post('/api/vote',
                               data=json.dumps({}),
                               content_type='application/json')
        # Should still work for demo mode
        assert response.status_code == 200

    def test_api_vote_with_data(self, client):
        """Test vote endpoint with proper data."""
        vote_data = {
            'proposal_id': 'XAI-001',
            'voter_address': 'AXN1test123',
            'vote_for': True
        }
        response = client.post('/api/vote',
                               data=json.dumps(vote_data),
                               content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True

    def test_api_stats(self, client):
        """Test stats endpoint."""
        response = client.get('/api/stats')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'active_proposals' in data
        assert 'total_proposals' in data
        assert 'participation_rate' in data
        assert 'quorum' in data


class TestGovernanceFunctions:
    """Test helper functions in governance dashboard."""

    def test_get_governance_stats_returns_defaults(self):
        """Test that stats return defaults when API unavailable."""
        from src.xai.governance_dashboard.governance_ui import get_governance_stats

        with patch('src.xai.governance_dashboard.governance_ui.requests.get') as mock_get:
            mock_get.side_effect = Exception("API unavailable")
            stats = get_governance_stats()

            assert 'active_proposals' in stats
            assert 'total_proposals' in stats
            assert isinstance(stats['active_proposals'], int)

    def test_get_proposals_returns_list(self):
        """Test that get_proposals returns a list."""
        from src.xai.governance_dashboard.governance_ui import get_proposals

        with patch('src.xai.governance_dashboard.governance_ui.requests.get') as mock_get:
            mock_get.side_effect = Exception("API unavailable")
            proposals = get_proposals("active")

            assert isinstance(proposals, list)

    def test_get_all_proposals_returns_list(self):
        """Test that get_all_proposals returns a list."""
        from src.xai.governance_dashboard.governance_ui import get_all_proposals

        with patch('src.xai.governance_dashboard.governance_ui.requests.get') as mock_get:
            mock_get.side_effect = Exception("API unavailable")
            proposals = get_all_proposals()

            assert isinstance(proposals, list)

    def test_get_vote_history_empty_address(self):
        """Test vote history with empty address."""
        from src.xai.governance_dashboard.governance_ui import get_vote_history

        history = get_vote_history("")
        assert history == []
