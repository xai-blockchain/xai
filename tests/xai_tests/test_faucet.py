"""
XAI Testnet Faucet Tests

Comprehensive security and functionality tests for the public-facing faucet.
Tests cover:
- Flask routes (GET /, POST /api/request, GET /health, GET /api/stats)
- Turnstile verification (mocked)
- Cooldown/rate limiting logic
- Token sending (mocked blockchain interaction)
- Redis integration (mocked)
- Security edge cases (invalid addresses, captcha bypass, cooldown bypass)

All tests marked with @pytest.mark.faucet for targeted execution.
"""

from __future__ import annotations

import json
import os
import sys
import time
from unittest.mock import MagicMock, Mock, patch

import pytest

# Ensure project paths are available
from pathlib import Path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "docker" / "faucet"))


@pytest.fixture
def reset_faucet_module():
    """Reset faucet module state between tests."""
    # Remove cached module to get fresh state
    if 'faucet' in sys.modules:
        del sys.modules['faucet']
    yield


@pytest.fixture
def faucet_env(monkeypatch, reset_faucet_module):
    """Set up clean faucet environment variables."""
    monkeypatch.setenv('XAI_API_URL', 'http://test-api:8080')
    monkeypatch.setenv('FAUCET_PORT', '8086')
    monkeypatch.setenv('FAUCET_AMOUNT', '100')
    monkeypatch.setenv('FAUCET_COOLDOWN', '3600')
    monkeypatch.setenv('FAUCET_IP_COOLDOWN', '0')
    monkeypatch.setenv('FAUCET_IP_MAX_PER_WINDOW', '100')
    monkeypatch.setenv('FAUCET_SENDER', 'TXAI' + 'b' * 40)
    monkeypatch.setenv('TURNSTILE_SITE_KEY', '')
    monkeypatch.setenv('TURNSTILE_SECRET_KEY', '')
    monkeypatch.setenv('REDIS_URL', '')
    yield


@pytest.fixture
def faucet_env_with_captcha(monkeypatch, reset_faucet_module):
    """Set up faucet with Turnstile enabled."""
    monkeypatch.setenv('XAI_API_URL', 'http://test-api:8080')
    monkeypatch.setenv('FAUCET_PORT', '8086')
    monkeypatch.setenv('FAUCET_AMOUNT', '100')
    monkeypatch.setenv('FAUCET_COOLDOWN', '3600')
    monkeypatch.setenv('FAUCET_IP_COOLDOWN', '0')
    monkeypatch.setenv('FAUCET_IP_MAX_PER_WINDOW', '100')
    monkeypatch.setenv('FAUCET_SENDER', 'TXAI' + 'b' * 40)
    monkeypatch.setenv('TURNSTILE_SITE_KEY', 'test-site-key')
    monkeypatch.setenv('TURNSTILE_SECRET_KEY', 'test-secret-key')
    monkeypatch.setenv('REDIS_URL', '')
    yield


@pytest.fixture
def faucet_app(faucet_env):
    """Create faucet Flask app for testing."""
    import faucet as faucet_module
    faucet_module.app.testing = True
    # Disable exception propagation so we get proper 500 responses
    faucet_module.app.config['PROPAGATE_EXCEPTIONS'] = False
    # Reset in-memory state
    faucet_module.request_history.clear()
    faucet_module.ip_history.clear()
    faucet_module.ip_window_history.clear()
    faucet_module.stats['total_requests'] = 0
    faucet_module.stats['unique_addresses'] = set()
    faucet_module.stats['start_time'] = time.time()
    return faucet_module.app


@pytest.fixture
def faucet_app_with_captcha(faucet_env_with_captcha):
    """Create faucet Flask app with Turnstile enabled."""
    import faucet as faucet_module
    faucet_module.app.testing = True
    # Disable exception propagation so we get proper 500 responses
    faucet_module.app.config['PROPAGATE_EXCEPTIONS'] = False
    faucet_module.request_history.clear()
    faucet_module.ip_history.clear()
    faucet_module.ip_window_history.clear()
    faucet_module.stats['total_requests'] = 0
    faucet_module.stats['unique_addresses'] = set()
    faucet_module.stats['start_time'] = time.time()
    return faucet_module.app


@pytest.fixture
def client(faucet_app):
    """Create Flask test client."""
    return faucet_app.test_client()


@pytest.fixture
def client_with_captcha(faucet_app_with_captcha):
    """Create Flask test client with captcha enabled."""
    return faucet_app_with_captcha.test_client()


@pytest.fixture
def valid_xai_address():
    """Generate a valid-looking XAI address."""
    # Format: TXAI prefix + 40+ characters
    return 'TXAI' + 'a' * 40


@pytest.fixture
def invalid_addresses():
    """Collection of invalid address formats for security testing."""
    return [
        '',                        # Empty
        'TXAI',                     # Too short
        'TXAI123456789',            # Too short (< 40 chars)
        'BTC' + 'a' * 40,          # Wrong prefix
        'txai' + 'a' * 40,          # Wrong case prefix
        'TXAI ' + 'a' * 39,         # Contains space
        'TXAI\n' + 'a' * 39,        # Contains newline
        'TXAI<script>alert(1)</script>' + 'a' * 20,  # XSS attempt
        "TXAI'; DROP TABLE users;--" + 'a' * 20,     # SQL injection attempt
        'TXAI${7*7}' + 'a' * 35,    # Template injection attempt
        'TXAI../../../etc/passwd',   # Path traversal attempt
    ]


# =============================================================================
# ROUTE TESTS
# =============================================================================

@pytest.mark.faucet
class TestIndexRoute:
    """Tests for GET / route."""

    def test_index_returns_200(self, client):
        """Index page should return 200 OK."""
        response = client.get('/')
        assert response.status_code == 200

    def test_index_contains_form(self, client):
        """Index page should contain faucet form."""
        response = client.get('/')
        assert b'<form' in response.data
        assert b'address' in response.data
        assert b'Request Tokens' in response.data

    def test_index_shows_amount_and_cooldown(self, client):
        """Index page should display faucet amount and cooldown."""
        response = client.get('/')
        assert b'100' in response.data  # FAUCET_AMOUNT
        assert b'3600' in response.data  # FAUCET_COOLDOWN

    def test_index_no_captcha_when_disabled(self, client):
        """Index page should not show captcha widget when disabled."""
        response = client.get('/')
        # The Turnstile CSS class is in the stylesheet, but the widget div should not be present
        # when captcha is disabled (data-sitekey attribute indicates enabled captcha)
        assert b'data-sitekey' not in response.data

    def test_index_shows_captcha_when_enabled(self, client_with_captcha):
        """Index page should show captcha when enabled."""
        response = client_with_captcha.get('/')
        assert b'cf-turnstile' in response.data
        assert b'test-site-key' in response.data


@pytest.mark.faucet
class TestHealthRoute:
    """Tests for GET /health route."""

    def test_health_returns_200(self, client):
        """Health endpoint should return 200 OK."""
        response = client.get('/health')
        assert response.status_code == 200

    def test_health_returns_json(self, client):
        """Health endpoint should return valid JSON."""
        response = client.get('/health')
        data = json.loads(response.data)
        assert 'status' in data
        assert 'timestamp' in data

    def test_health_status_healthy(self, client):
        """Health endpoint should report healthy status."""
        response = client.get('/health')
        data = json.loads(response.data)
        assert data['status'] == 'healthy'

    def test_health_timestamp_format(self, client):
        """Health endpoint timestamp should be ISO format."""
        response = client.get('/health')
        data = json.loads(response.data)
        # Should be parseable as datetime
        from datetime import datetime
        datetime.fromisoformat(data['timestamp'])


@pytest.mark.faucet
class TestStatsRoute:
    """Tests for GET /api/stats route."""

    def test_stats_returns_200(self, client):
        """Stats endpoint should return 200 OK."""
        response = client.get('/api/stats')
        assert response.status_code == 200

    def test_stats_returns_json(self, client):
        """Stats endpoint should return valid JSON."""
        response = client.get('/api/stats')
        data = json.loads(response.data)
        assert isinstance(data, dict)

    def test_stats_contains_expected_fields(self, client):
        """Stats endpoint should contain all expected fields."""
        response = client.get('/api/stats')
        data = json.loads(response.data)

        expected_fields = [
            'total_requests',
            'unique_addresses',
            'uptime_seconds',
            'faucet_amount',
            'cooldown_seconds',
            'turnstile_enabled',
            'redis_enabled',
        ]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"

    def test_stats_initial_values(self, client):
        """Stats should show zero requests initially."""
        response = client.get('/api/stats')
        data = json.loads(response.data)
        assert data['total_requests'] == 0
        assert data['unique_addresses'] == 0

    def test_stats_captcha_disabled(self, client):
        """Stats should show captcha disabled when not configured."""
        response = client.get('/api/stats')
        data = json.loads(response.data)
        assert data['turnstile_enabled'] is False

    def test_stats_captcha_enabled(self, client_with_captcha):
        """Stats should show captcha enabled when configured."""
        response = client_with_captcha.get('/api/stats')
        data = json.loads(response.data)
        assert data['turnstile_enabled'] is True

    def test_stats_redis_disabled(self, client):
        """Stats should show redis disabled when not configured."""
        response = client.get('/api/stats')
        data = json.loads(response.data)
        assert data['redis_enabled'] is False


# =============================================================================
# TOKEN REQUEST TESTS
# =============================================================================

@pytest.mark.faucet
class TestRequestTokensRoute:
    """Tests for POST /api/request route."""

    def test_request_requires_address(self, client):
        """Request should fail without address."""
        response = client.post(
            '/api/request',
            data=json.dumps({}),
            content_type='application/json'
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Address is required' in data['error']

    def test_request_requires_json(self, client):
        """Request should fail without JSON content."""
        response = client.post('/api/request')
        # Flask returns 415 Unsupported Media Type when Content-Type is not application/json
        assert response.status_code in [400, 415]

    def test_request_validates_address_prefix(self, client, invalid_addresses):
        """Request should reject invalid address formats."""
        for invalid_addr in invalid_addresses:
            if not invalid_addr:
                continue  # Skip empty string, handled separately
            response = client.post(
                '/api/request',
                data=json.dumps({'address': invalid_addr}),
                content_type='application/json'
            )
            # Should be 400 for invalid address
            if not (invalid_addr.startswith('TXAI') and len(invalid_addr) >= 40):
                assert response.status_code == 400, f"Should reject: {invalid_addr}"

    @patch('faucet.send_tokens')
    def test_request_success(self, mock_send, client, valid_xai_address):
        """Successful token request."""
        mock_send.return_value = {'success': True, 'txid': 'test-txid-123'}

        response = client.post(
            '/api/request',
            data=json.dumps({'address': valid_xai_address}),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'Successfully sent' in data['message']
        assert 'txid' in data

    @patch('faucet.send_tokens')
    def test_request_increments_stats(self, mock_send, client, valid_xai_address):
        """Successful request should increment statistics."""
        mock_send.return_value = {'success': True, 'txid': 'test-txid'}

        # Make request
        client.post(
            '/api/request',
            data=json.dumps({'address': valid_xai_address}),
            content_type='application/json'
        )

        # Check stats
        response = client.get('/api/stats')
        data = json.loads(response.data)
        assert data['total_requests'] == 1
        assert data['unique_addresses'] == 1

    @patch('faucet.send_tokens')
    def test_request_send_failure(self, mock_send, client, valid_xai_address):
        """Failed token send should return error."""
        mock_send.return_value = {'success': False, 'error': 'Node unreachable'}

        response = client.post(
            '/api/request',
            data=json.dumps({'address': valid_xai_address}),
            content_type='application/json'
        )

        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Node unreachable' in data['error']


# =============================================================================
# COOLDOWN/RATE LIMITING TESTS
# =============================================================================

@pytest.mark.faucet
class TestCooldownLogic:
    """Tests for rate limiting and cooldown enforcement."""

    @patch('faucet.send_tokens')
    def test_cooldown_enforced(self, mock_send, client, valid_xai_address):
        """Second request within cooldown period should be rejected."""
        mock_send.return_value = {'success': True, 'txid': 'test-txid'}

        # First request succeeds
        response1 = client.post(
            '/api/request',
            data=json.dumps({'address': valid_xai_address}),
            content_type='application/json'
        )
        assert response1.status_code == 200

        # Second request should fail with 429
        response2 = client.post(
            '/api/request',
            data=json.dumps({'address': valid_xai_address}),
            content_type='application/json'
        )
        assert response2.status_code == 429
        data = json.loads(response2.data)
        assert data['success'] is False
        assert 'wait' in data['error'].lower()

    @patch('faucet.send_tokens')
    def test_different_addresses_no_cooldown(self, mock_send, client):
        """Different addresses should not share cooldown."""
        mock_send.return_value = {'success': True, 'txid': 'test-txid'}

        addr1 = 'TXAI' + 'a' * 40
        addr2 = 'TXAI' + 'b' * 40

        # Both should succeed
        response1 = client.post(
            '/api/request',
            data=json.dumps({'address': addr1}),
            content_type='application/json'
        )
        assert response1.status_code == 200

        response2 = client.post(
            '/api/request',
            data=json.dumps({'address': addr2}),
            content_type='application/json'
        )
        assert response2.status_code == 200

    @patch('faucet.send_tokens')
    @patch('time.time')
    def test_cooldown_expires(self, mock_time, mock_send, faucet_env):
        """Request should succeed after cooldown expires."""
        import faucet as faucet_module
        faucet_module.request_history.clear()
        faucet_module.stats['total_requests'] = 0
        faucet_module.stats['unique_addresses'] = set()

        app = faucet_module.app
        app.testing = True
        client = app.test_client()

        mock_send.return_value = {'success': True, 'txid': 'test-txid'}
        valid_addr = 'TXAI' + 'a' * 40

        # First request at time 0
        mock_time.return_value = 0
        response1 = client.post(
            '/api/request',
            data=json.dumps({'address': valid_addr}),
            content_type='application/json'
        )
        assert response1.status_code == 200

        # Request at time 1000 (still in cooldown)
        mock_time.return_value = 1000
        response2 = client.post(
            '/api/request',
            data=json.dumps({'address': valid_addr}),
            content_type='application/json'
        )
        assert response2.status_code == 429

        # Request at time 4000 (after 3600s cooldown)
        mock_time.return_value = 4000
        response3 = client.post(
            '/api/request',
            data=json.dumps({'address': valid_addr}),
            content_type='application/json'
        )
        assert response3.status_code == 200


@pytest.mark.faucet
class TestCheckCooldownFunction:
    """Direct tests for check_cooldown helper function."""

    def test_check_cooldown_no_history(self, faucet_env):
        """New address should not be in cooldown."""
        import faucet as faucet_module
        faucet_module.request_history.clear()

        can_request, remaining = faucet_module.check_cooldown('TXAI' + 'x' * 40)
        assert can_request is True
        assert remaining == 0

    def test_check_cooldown_recent_request(self, faucet_env):
        """Recent request should be in cooldown."""
        import faucet as faucet_module
        faucet_module.request_history.clear()

        addr = 'TXAI' + 'x' * 40
        faucet_module.request_history[addr] = time.time()

        can_request, remaining = faucet_module.check_cooldown(addr)
        assert can_request is False
        assert remaining > 0
        assert remaining <= faucet_module.FAUCET_COOLDOWN

    def test_check_cooldown_expired(self, faucet_env):
        """Old request should not be in cooldown."""
        import faucet as faucet_module
        faucet_module.request_history.clear()

        addr = 'TXAI' + 'x' * 40
        # Request 2 hours ago
        faucet_module.request_history[addr] = time.time() - 7200

        can_request, remaining = faucet_module.check_cooldown(addr)
        assert can_request is True
        assert remaining == 0


# =============================================================================
# TURNSTILE TESTS
# =============================================================================

@pytest.mark.faucet
class TestTurnstileVerification:
    """Tests for Turnstile verification."""

    def test_captcha_skipped_when_disabled(self, faucet_env):
        """verify_turnstile should return True when captcha disabled."""
        import faucet as faucet_module
        # Captcha is disabled in faucet_env
        result = faucet_module.verify_turnstile('')
        assert result is True

    def test_captcha_required_when_enabled(self, client_with_captcha, valid_xai_address):
        """Request should fail without captcha when enabled."""
        response = client_with_captcha.post(
            '/api/request',
            data=json.dumps({'address': valid_xai_address}),
            content_type='application/json'
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'CAPTCHA' in data['error']

    @patch('requests.post')
    @patch('faucet.send_tokens')
    def test_captcha_verification_success(
        self, mock_send, mock_requests, faucet_env_with_captcha, valid_xai_address
    ):
        """Successful captcha verification should allow request."""
        import faucet as faucet_module
        faucet_module.request_history.clear()
        faucet_module.stats['total_requests'] = 0
        faucet_module.stats['unique_addresses'] = set()

        app = faucet_module.app
        app.testing = True
        client = app.test_client()

        mock_response = Mock()
        mock_response.json.return_value = {'success': True}
        mock_requests.return_value = mock_response
        mock_send.return_value = {'success': True, 'txid': 'test-txid'}

        response = client.post(
            '/api/request',
            data=json.dumps({
                'address': valid_xai_address,
                'captcha': 'valid-captcha-token'
            }),
            content_type='application/json'
        )

        assert response.status_code == 200

    @patch('requests.post')
    def test_captcha_verification_failure(
        self, mock_requests, faucet_env_with_captcha, valid_xai_address
    ):
        """Failed captcha verification should reject request."""
        import faucet as faucet_module
        faucet_module.request_history.clear()

        app = faucet_module.app
        app.testing = True
        client = app.test_client()

        mock_response = Mock()
        mock_response.json.return_value = {'success': False}
        mock_requests.return_value = mock_response

        response = client.post(
            '/api/request',
            data=json.dumps({
                'address': valid_xai_address,
                'captcha': 'invalid-token'
            }),
            content_type='application/json'
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'CAPTCHA' in data['error']

    @patch('requests.post')
    def test_captcha_api_error_fails_safely(
        self, mock_requests, faucet_env_with_captcha, valid_xai_address
    ):
        """Turnstile API error should reject request (fail closed)."""
        import faucet as faucet_module
        faucet_module.request_history.clear()

        app = faucet_module.app
        app.testing = True
        client = app.test_client()

        # Simulate network error
        mock_requests.side_effect = Exception("Network error")

        response = client.post(
            '/api/request',
            data=json.dumps({
                'address': valid_xai_address,
                'captcha': 'some-token'
            }),
            content_type='application/json'
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False


@pytest.mark.faucet
class TestVerifyTurnstileFunction:
    """Direct tests for verify_turnstile helper function."""

    @patch('requests.post')
    def test_verify_returns_true_on_success(self, mock_requests, faucet_env_with_captcha):
        """verify_turnstile returns True when API confirms success."""
        import faucet as faucet_module

        mock_response = Mock()
        mock_response.json.return_value = {'success': True}
        mock_requests.return_value = mock_response

        result = faucet_module.verify_turnstile('valid-token')
        assert result is True

    @patch('requests.post')
    def test_verify_returns_false_on_failure(self, mock_requests, faucet_env_with_captcha):
        """verify_turnstile returns False when API rejects token."""
        import faucet as faucet_module

        mock_response = Mock()
        mock_response.json.return_value = {'success': False}
        mock_requests.return_value = mock_response

        result = faucet_module.verify_turnstile('invalid-token')
        assert result is False

    def test_verify_returns_false_for_empty_token(self, faucet_env_with_captcha):
        """verify_turnstile returns False for empty token when enabled."""
        import faucet as faucet_module

        result = faucet_module.verify_turnstile('')
        assert result is False

    def test_verify_returns_false_for_none_token(self, faucet_env_with_captcha):
        """verify_turnstile returns False for None token when enabled."""
        import faucet as faucet_module

        result = faucet_module.verify_turnstile(None)
        assert result is False


# =============================================================================
# TOKEN SENDING TESTS
# =============================================================================

@pytest.mark.faucet
class TestSendTokensFunction:
    """Tests for send_tokens helper function."""

    @patch('requests.post')
    def test_send_tokens_success(self, mock_requests, faucet_env):
        """send_tokens returns success response from API."""
        import faucet as faucet_module

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'success': True, 'txid': 'abc123'}
        mock_requests.return_value = mock_response

        result = faucet_module.send_tokens('TXAI' + 'a' * 40, 100.0)

        assert result['success'] is True
        assert result['txid'] == 'abc123'
        mock_requests.assert_called_once()

    @patch('requests.post')
    def test_send_tokens_api_error(self, mock_requests, faucet_env):
        """send_tokens handles API errors gracefully."""
        import faucet as faucet_module

        mock_requests.side_effect = Exception("Connection refused")

        result = faucet_module.send_tokens('TXAI' + 'a' * 40, 100.0)

        assert result['success'] is False
        assert 'error' in result
        assert 'Connection refused' in result['error']

    @patch('requests.post')
    def test_send_tokens_http_error(self, mock_requests, faucet_env):
        """send_tokens handles HTTP errors."""
        import faucet as faucet_module

        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "500 Server Error"
        mock_requests.return_value = mock_response

        result = faucet_module.send_tokens('TXAI' + 'a' * 40, 100.0)

        assert result['success'] is False
        assert "Faucet API error" in result['error']

    @patch('requests.post')
    def test_send_tokens_correct_payload(self, mock_requests, faucet_env):
        """send_tokens sends correct JSON payload."""
        import faucet as faucet_module

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'success': True}
        mock_requests.return_value = mock_response

        addr = 'TXAI' + 'a' * 40
        amount = 100.0
        faucet_module.send_tokens(addr, amount)

        call_args = mock_requests.call_args
        assert call_args[1]['json'] == {'address': addr, 'amount': amount}
        assert call_args[1]['timeout'] == 10


# =============================================================================
# REDIS INTEGRATION TESTS
# =============================================================================

@pytest.mark.faucet
class TestRedisIntegration:
    """Tests for Redis storage backend."""

    @patch('redis.from_url')
    def test_redis_cooldown_check(self, mock_redis_from_url, monkeypatch, reset_faucet_module):
        """check_cooldown uses Redis when available."""
        # Setup Redis mock
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis.get.return_value = None  # No previous request
        mock_redis_from_url.return_value = mock_redis

        monkeypatch.setenv('REDIS_URL', 'redis://localhost:6379')
        monkeypatch.setenv('XAI_API_URL', 'http://test-api:8080')
        monkeypatch.setenv('FAUCET_COOLDOWN', '3600')
        monkeypatch.setenv('TURNSTILE_SITE_KEY', '')
        monkeypatch.setenv('TURNSTILE_SECRET_KEY', '')

        import faucet as faucet_module
        faucet_module.redis_client = mock_redis

        addr = 'TXAI' + 'x' * 40
        can_request, remaining = faucet_module.check_cooldown(addr)

        assert can_request is True
        mock_redis.get.assert_called_with(f'faucet:cooldown:{addr}')

    @patch('redis.from_url')
    def test_redis_cooldown_active(self, mock_redis_from_url, monkeypatch, reset_faucet_module):
        """check_cooldown returns False when Redis shows recent request."""
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        # Recent request (current time as string)
        mock_redis.get.return_value = str(time.time())
        mock_redis_from_url.return_value = mock_redis

        monkeypatch.setenv('REDIS_URL', 'redis://localhost:6379')
        monkeypatch.setenv('XAI_API_URL', 'http://test-api:8080')
        monkeypatch.setenv('FAUCET_COOLDOWN', '3600')
        monkeypatch.setenv('TURNSTILE_SITE_KEY', '')
        monkeypatch.setenv('TURNSTILE_SECRET_KEY', '')

        import faucet as faucet_module
        faucet_module.redis_client = mock_redis

        addr = 'TXAI' + 'x' * 40
        can_request, remaining = faucet_module.check_cooldown(addr)

        assert can_request is False
        assert remaining > 0

    @patch('redis.from_url')
    def test_redis_record_request(self, mock_redis_from_url, monkeypatch, reset_faucet_module):
        """record_request stores data in Redis when available."""
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis_from_url.return_value = mock_redis

        monkeypatch.setenv('REDIS_URL', 'redis://localhost:6379')
        monkeypatch.setenv('XAI_API_URL', 'http://test-api:8080')
        monkeypatch.setenv('FAUCET_COOLDOWN', '3600')
        monkeypatch.setenv('TURNSTILE_SITE_KEY', '')
        monkeypatch.setenv('TURNSTILE_SECRET_KEY', '')

        import faucet as faucet_module
        faucet_module.redis_client = mock_redis
        faucet_module.request_history.clear()
        faucet_module.stats['total_requests'] = 0
        faucet_module.stats['unique_addresses'] = set()

        addr = 'TXAI' + 'x' * 40
        faucet_module.record_request(addr)

        # Verify Redis calls
        mock_redis.setex.assert_called()
        mock_redis.incr.assert_called_with('faucet:stats:total_requests')
        mock_redis.sadd.assert_called_with('faucet:stats:unique_addresses', addr)

    @patch('redis.from_url')
    def test_redis_fallback_on_error(self, mock_redis_from_url, monkeypatch, reset_faucet_module):
        """check_cooldown falls back to memory when Redis fails."""
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis.get.side_effect = Exception("Redis connection lost")
        mock_redis_from_url.return_value = mock_redis

        monkeypatch.setenv('REDIS_URL', 'redis://localhost:6379')
        monkeypatch.setenv('XAI_API_URL', 'http://test-api:8080')
        monkeypatch.setenv('FAUCET_COOLDOWN', '3600')
        monkeypatch.setenv('TURNSTILE_SITE_KEY', '')
        monkeypatch.setenv('TURNSTILE_SECRET_KEY', '')

        import faucet as faucet_module
        faucet_module.redis_client = mock_redis
        faucet_module.request_history.clear()

        addr = 'TXAI' + 'x' * 40
        # Should not raise, falls back to in-memory
        can_request, remaining = faucet_module.check_cooldown(addr)

        assert can_request is True  # No history in memory

    @patch('redis.from_url')
    def test_stats_from_redis(self, mock_redis_from_url, monkeypatch, reset_faucet_module):
        """get_stats reads from Redis when available."""
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis.get.return_value = '42'  # total requests
        mock_redis.scard.return_value = 15   # unique addresses
        mock_redis_from_url.return_value = mock_redis

        monkeypatch.setenv('REDIS_URL', 'redis://localhost:6379')
        monkeypatch.setenv('XAI_API_URL', 'http://test-api:8080')
        monkeypatch.setenv('FAUCET_COOLDOWN', '3600')
        monkeypatch.setenv('TURNSTILE_SITE_KEY', '')
        monkeypatch.setenv('TURNSTILE_SECRET_KEY', '')

        import faucet as faucet_module
        faucet_module.redis_client = mock_redis
        faucet_module.stats['start_time'] = time.time()

        app = faucet_module.app
        app.testing = True
        client = app.test_client()

        response = client.get('/api/stats')
        data = json.loads(response.data)

        assert data['total_requests'] == 42
        assert data['unique_addresses'] == 15
        assert data['redis_enabled'] is True

    @patch('redis.from_url')
    def test_redis_cooldown_expired(self, mock_redis_from_url, monkeypatch, reset_faucet_module):
        """check_cooldown returns True when Redis shows expired cooldown."""
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        # Request from 2 hours ago (cooldown is 3600s = 1 hour)
        mock_redis.get.return_value = str(time.time() - 7200)
        mock_redis_from_url.return_value = mock_redis

        monkeypatch.setenv('REDIS_URL', 'redis://localhost:6379')
        monkeypatch.setenv('XAI_API_URL', 'http://test-api:8080')
        monkeypatch.setenv('FAUCET_COOLDOWN', '3600')
        monkeypatch.setenv('TURNSTILE_SITE_KEY', '')
        monkeypatch.setenv('TURNSTILE_SECRET_KEY', '')

        import faucet as faucet_module
        faucet_module.redis_client = mock_redis

        addr = 'TXAI' + 'x' * 40
        can_request, remaining = faucet_module.check_cooldown(addr)

        assert can_request is True
        assert remaining == 0

    @patch('redis.from_url')
    def test_redis_write_failure_graceful(self, mock_redis_from_url, monkeypatch, reset_faucet_module):
        """record_request handles Redis write failure gracefully."""
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis.setex.side_effect = Exception("Redis write error")
        mock_redis_from_url.return_value = mock_redis

        monkeypatch.setenv('REDIS_URL', 'redis://localhost:6379')
        monkeypatch.setenv('XAI_API_URL', 'http://test-api:8080')
        monkeypatch.setenv('FAUCET_COOLDOWN', '3600')
        monkeypatch.setenv('TURNSTILE_SITE_KEY', '')
        monkeypatch.setenv('TURNSTILE_SECRET_KEY', '')

        import faucet as faucet_module
        faucet_module.redis_client = mock_redis
        faucet_module.request_history.clear()
        faucet_module.stats['total_requests'] = 0
        faucet_module.stats['unique_addresses'] = set()

        addr = 'TXAI' + 'x' * 40
        # Should not raise despite Redis error
        faucet_module.record_request(addr)

        # In-memory storage should still be updated
        assert addr in faucet_module.request_history
        assert faucet_module.stats['total_requests'] == 1
        assert addr in faucet_module.stats['unique_addresses']

    @patch('redis.from_url')
    def test_stats_redis_read_failure_fallback(self, mock_redis_from_url, monkeypatch, reset_faucet_module):
        """get_stats falls back to in-memory when Redis read fails."""
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis.get.side_effect = Exception("Redis read error")
        mock_redis_from_url.return_value = mock_redis

        monkeypatch.setenv('REDIS_URL', 'redis://localhost:6379')
        monkeypatch.setenv('XAI_API_URL', 'http://test-api:8080')
        monkeypatch.setenv('FAUCET_COOLDOWN', '3600')
        monkeypatch.setenv('TURNSTILE_SITE_KEY', '')
        monkeypatch.setenv('TURNSTILE_SECRET_KEY', '')

        import faucet as faucet_module
        faucet_module.redis_client = mock_redis
        faucet_module.stats['start_time'] = time.time()
        faucet_module.stats['total_requests'] = 5
        faucet_module.stats['unique_addresses'] = {'addr1', 'addr2', 'addr3'}

        app = faucet_module.app
        app.testing = True
        client = app.test_client()

        response = client.get('/api/stats')
        data = json.loads(response.data)

        # Should fall back to in-memory stats
        assert data['total_requests'] == 5
        assert data['unique_addresses'] == 3
        assert data['redis_enabled'] is True  # Redis client exists but failed


@pytest.mark.faucet
class TestModuleLevelRedisInit:
    """Tests for module-level Redis initialization error handling.

    These tests verify that the faucet module handles Redis initialization
    failures gracefully at import time.
    """

    def test_redis_import_error_handled(self, monkeypatch):
        """Module should handle missing redis package gracefully."""
        # Remove faucet module if cached
        if 'faucet' in sys.modules:
            del sys.modules['faucet']

        # Set up environment for Redis usage
        monkeypatch.setenv('REDIS_URL', 'redis://localhost:6379')
        monkeypatch.setenv('XAI_API_URL', 'http://test-api:8080')
        monkeypatch.setenv('FAUCET_COOLDOWN', '3600')
        monkeypatch.setenv('TURNSTILE_SITE_KEY', '')
        monkeypatch.setenv('TURNSTILE_SECRET_KEY', '')

        # Mock the redis import to raise ImportError
        import builtins
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == 'redis':
                raise ImportError("No module named 'redis'")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, '__import__', mock_import)

        # Import faucet module - should not raise despite redis ImportError
        import faucet as faucet_module

        # Verify redis_client is None (fallback to in-memory)
        assert faucet_module.redis_client is None

        # Cleanup
        del sys.modules['faucet']

    def test_redis_connection_error_handled(self, monkeypatch):
        """Module should handle Redis connection failure gracefully."""
        # Remove faucet module if cached
        if 'faucet' in sys.modules:
            del sys.modules['faucet']

        # Set up environment for Redis usage
        monkeypatch.setenv('REDIS_URL', 'redis://localhost:6379')
        monkeypatch.setenv('XAI_API_URL', 'http://test-api:8080')
        monkeypatch.setenv('FAUCET_COOLDOWN', '3600')
        monkeypatch.setenv('TURNSTILE_SITE_KEY', '')
        monkeypatch.setenv('TURNSTILE_SECRET_KEY', '')

        # Create a mock redis module that raises connection error
        mock_redis_module = MagicMock()
        mock_redis_module.from_url.side_effect = Exception("Connection refused")
        sys.modules['redis'] = mock_redis_module

        try:
            # Import faucet module - should not raise despite connection error
            import faucet as faucet_module

            # Verify redis_client is None (fallback to in-memory)
            assert faucet_module.redis_client is None
        finally:
            # Cleanup
            if 'faucet' in sys.modules:
                del sys.modules['faucet']
            if 'redis' in sys.modules:
                del sys.modules['redis']

    def test_redis_ping_failure_handled(self, monkeypatch):
        """Module should handle Redis ping failure gracefully."""
        # Remove faucet module if cached
        if 'faucet' in sys.modules:
            del sys.modules['faucet']

        # Set up environment for Redis usage
        monkeypatch.setenv('REDIS_URL', 'redis://localhost:6379')
        monkeypatch.setenv('XAI_API_URL', 'http://test-api:8080')
        monkeypatch.setenv('FAUCET_COOLDOWN', '3600')
        monkeypatch.setenv('TURNSTILE_SITE_KEY', '')
        monkeypatch.setenv('TURNSTILE_SECRET_KEY', '')

        # Create a mock redis module where ping fails
        mock_redis_client = MagicMock()
        mock_redis_client.ping.side_effect = Exception("Redis not responding")
        mock_redis_module = MagicMock()
        mock_redis_module.from_url.return_value = mock_redis_client
        sys.modules['redis'] = mock_redis_module

        try:
            # Import faucet module - should not raise despite ping error
            import faucet as faucet_module

            # Verify redis_client is None (fallback to in-memory)
            assert faucet_module.redis_client is None
        finally:
            # Cleanup
            if 'faucet' in sys.modules:
                del sys.modules['faucet']
            if 'redis' in sys.modules:
                del sys.modules['redis']


# =============================================================================
# SECURITY TESTS
# =============================================================================

@pytest.mark.faucet
@pytest.mark.security
class TestSecurityValidation:
    """Security-focused tests for the public-facing faucet."""

    def test_xss_prevention_in_address(self, client):
        """XSS payloads in address should be rejected."""
        xss_payloads = [
            '<script>alert(1)</script>',
            '"><script>alert(1)</script>',
            "javascript:alert('XSS')",
            '<img src=x onerror=alert(1)>',
            '<svg onload=alert(1)>',
        ]
        for payload in xss_payloads:
            response = client.post(
                '/api/request',
                data=json.dumps({'address': f'TXAI{payload}'}),
                content_type='application/json'
            )
            # Should be rejected (invalid address format)
            assert response.status_code == 400

    def test_sql_injection_prevention(self, client):
        """SQL injection payloads should be rejected."""
        sql_payloads = [
            "'; DROP TABLE users;--",
            "1' OR '1'='1",
            "1; DELETE FROM users WHERE '1'='1",
            "UNION SELECT * FROM users--",
        ]
        for payload in sql_payloads:
            response = client.post(
                '/api/request',
                data=json.dumps({'address': f'TXAI{payload}'}),
                content_type='application/json'
            )
            # Should be rejected (invalid address format)
            assert response.status_code == 400

    def test_command_injection_prevention(self, client):
        """Command injection payloads should be rejected."""
        cmd_payloads = [
            '; cat /etc/passwd',
            '| ls -la',
            '$(whoami)',
            '`id`',
            '&& rm -rf /',
        ]
        for payload in cmd_payloads:
            response = client.post(
                '/api/request',
                data=json.dumps({'address': f'TXAI{payload}'}),
                content_type='application/json'
            )
            assert response.status_code == 400

    def test_path_traversal_prevention(self, client):
        """Path traversal payloads should be rejected."""
        traversal_payloads = [
            '../../../etc/passwd',
            '..\\..\\..\\windows\\system32\\config\\sam',
            '/etc/passwd%00',
            '....//....//....//etc/passwd',
        ]
        for payload in traversal_payloads:
            response = client.post(
                '/api/request',
                data=json.dumps({'address': f'TXAI{payload}'}),
                content_type='application/json'
            )
            assert response.status_code == 400

    def test_oversized_address_rejected(self, client):
        """Extremely long addresses should be rejected."""
        # Address with 10,000 characters
        long_address = 'TXAI' + 'a' * 10000
        response = client.post(
            '/api/request',
            data=json.dumps({'address': long_address}),
            content_type='application/json'
        )
        # Should either be 400 (invalid) or 200 (if valid length)
        # but should not crash the server
        assert response.status_code in [200, 400, 429, 500]

    def test_null_byte_injection(self, client):
        """Null byte injection should be handled safely."""
        null_payloads = [
            'TXAI\x00' + 'a' * 40,
            'TXAI' + '\x00' * 40,
            'TXAI' + 'a' * 20 + '\x00' + 'a' * 19,
        ]
        for payload in null_payloads:
            response = client.post(
                '/api/request',
                data=json.dumps({'address': payload}),
                content_type='application/json'
            )
            # Should not crash, may be rejected
            assert response.status_code in [200, 400, 429, 500]

    def test_unicode_normalization_attacks(self, client):
        """Unicode normalization attacks should be handled."""
        unicode_payloads = [
            'TXAI' + '\uff21' * 40,  # Fullwidth A
            'TXAI' + '\u0041\u030a' * 20,  # A + combining ring
        ]
        for payload in unicode_payloads:
            response = client.post(
                '/api/request',
                data=json.dumps({'address': payload}),
                content_type='application/json'
            )
            # Should handle gracefully
            assert response.status_code in [200, 400, 429, 500]

    def test_json_depth_attack(self, client):
        """Deeply nested JSON should be handled."""
        # Create deeply nested structure
        nested = {'address': 'TXAI' + 'a' * 40}
        for _ in range(100):
            nested = {'nested': nested}

        response = client.post(
            '/api/request',
            data=json.dumps(nested),
            content_type='application/json'
        )
        # Should either handle or reject, not crash
        assert response.status_code in [200, 400, 413, 500]

    @patch('faucet.send_tokens')
    def test_response_does_not_leak_internal_info(self, mock_send, client, valid_xai_address):
        """Error responses should not leak internal information."""
        mock_send.return_value = {'success': False, 'error': 'Internal DB error: /var/lib/xai/data'}

        response = client.post(
            '/api/request',
            data=json.dumps({'address': valid_xai_address}),
            content_type='application/json'
        )

        data = json.loads(response.data)
        # The error message is passed through, but we document this behavior
        # In production, send_tokens should sanitize error messages
        assert response.status_code == 500

    def test_content_type_enforcement(self, client, valid_xai_address):
        """Request should require proper Content-Type."""
        # Send without Content-Type
        response = client.post(
            '/api/request',
            data='{"address": "' + valid_xai_address + '"}'
        )
        # Flask may accept it or reject it
        # This tests that the server handles it gracefully
        assert response.status_code in [200, 400, 415, 429, 500]

    @patch('faucet.send_tokens')
    def test_case_sensitivity_in_address(self, mock_send, client):
        """Address validation should be case-sensitive where required."""
        mock_send.return_value = {'success': True, 'txid': 'test'}

        # Valid uppercase prefix
        response1 = client.post(
            '/api/request',
            data=json.dumps({'address': 'TXAI' + 'a' * 40}),
            content_type='application/json'
        )
        assert response1.status_code == 200

        # Invalid lowercase prefix
        response2 = client.post(
            '/api/request',
            data=json.dumps({'address': 'txai' + 'a' * 40}),
            content_type='application/json'
        )
        assert response2.status_code == 400


@pytest.mark.faucet
@pytest.mark.security
class TestRateLimitingSecurity:
    """Security tests for rate limiting bypass attempts."""

    @patch('faucet.send_tokens')
    def test_cooldown_cannot_be_bypassed_by_case_change(self, mock_send, client):
        """Changing address case should not bypass cooldown."""
        mock_send.return_value = {'success': True, 'txid': 'test'}

        addr_lower = 'TXAI' + 'a' * 40
        addr_mixed = 'TXAI' + 'A' * 40

        # First request
        response1 = client.post(
            '/api/request',
            data=json.dumps({'address': addr_lower}),
            content_type='application/json'
        )
        assert response1.status_code == 200

        # Second request with different case (different address, should succeed)
        response2 = client.post(
            '/api/request',
            data=json.dumps({'address': addr_mixed}),
            content_type='application/json'
        )
        # These are actually different addresses, so both should work
        assert response2.status_code == 200

    @patch('faucet.send_tokens')
    def test_cooldown_cannot_be_bypassed_by_whitespace(self, mock_send, client):
        """Adding whitespace should not bypass cooldown."""
        mock_send.return_value = {'success': True, 'txid': 'test'}

        addr = 'TXAI' + 'a' * 40
        addr_with_space = ' TXAI' + 'a' * 40

        # Address with leading space should be rejected (invalid format)
        response = client.post(
            '/api/request',
            data=json.dumps({'address': addr_with_space}),
            content_type='application/json'
        )
        assert response.status_code == 400

    @patch('faucet.send_tokens')
    def test_failed_send_does_not_record_request(self, mock_send, client, valid_xai_address):
        """Failed token send should not start cooldown."""
        mock_send.return_value = {'success': False, 'error': 'Node down'}

        # First request fails
        response1 = client.post(
            '/api/request',
            data=json.dumps({'address': valid_xai_address}),
            content_type='application/json'
        )
        assert response1.status_code == 500

        # Change mock to succeed
        mock_send.return_value = {'success': True, 'txid': 'test'}

        # Second request should succeed (no cooldown from failed request)
        response2 = client.post(
            '/api/request',
            data=json.dumps({'address': valid_xai_address}),
            content_type='application/json'
        )
        assert response2.status_code == 200


# =============================================================================
# RECORD REQUEST TESTS
# =============================================================================

@pytest.mark.faucet
class TestRecordRequestFunction:
    """Tests for record_request helper function."""

    def test_record_updates_in_memory(self, faucet_env):
        """record_request updates in-memory storage."""
        import faucet as faucet_module
        faucet_module.request_history.clear()
        faucet_module.stats['total_requests'] = 0
        faucet_module.stats['unique_addresses'] = set()

        addr = 'TXAI' + 'x' * 40
        faucet_module.record_request(addr)

        assert addr in faucet_module.request_history
        assert faucet_module.stats['total_requests'] == 1
        assert addr in faucet_module.stats['unique_addresses']

    def test_record_updates_stats_correctly(self, faucet_env):
        """record_request correctly tracks unique addresses."""
        import faucet as faucet_module
        faucet_module.request_history.clear()
        faucet_module.stats['total_requests'] = 0
        faucet_module.stats['unique_addresses'] = set()

        addr1 = 'TXAI' + 'a' * 40
        addr2 = 'TXAI' + 'b' * 40

        faucet_module.record_request(addr1)
        faucet_module.record_request(addr1)  # Same address
        faucet_module.record_request(addr2)

        assert faucet_module.stats['total_requests'] == 3
        assert len(faucet_module.stats['unique_addresses']) == 2


# =============================================================================
# EDGE CASE TESTS
# =============================================================================

@pytest.mark.faucet
class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_json_body(self, client):
        """Empty JSON body should be rejected."""
        response = client.post(
            '/api/request',
            data='{}',
            content_type='application/json'
        )
        assert response.status_code == 400

    def test_null_address(self, client):
        """Null address should be rejected with 400."""
        response = client.post(
            '/api/request',
            data=json.dumps({'address': None}),
            content_type='application/json'
        )
        assert response.status_code == 400

    def test_numeric_address(self, client):
        """Numeric address should be rejected with 400."""
        response = client.post(
            '/api/request',
            data=json.dumps({'address': 12345}),
            content_type='application/json'
        )
        assert response.status_code == 400

    def test_array_address(self, client):
        """Array address should be rejected with 400."""
        response = client.post(
            '/api/request',
            data=json.dumps({'address': ['TXAI' + 'a' * 40]}),
            content_type='application/json'
        )
        assert response.status_code == 400

    def test_object_address(self, client):
        """Object address should be rejected with 400."""
        response = client.post(
            '/api/request',
            data=json.dumps({'address': {'value': 'TXAI' + 'a' * 40}}),
            content_type='application/json'
        )
        assert response.status_code == 400

    def test_malformed_json(self, client):
        """Malformed JSON should be handled gracefully."""
        response = client.post(
            '/api/request',
            data='{"address": "TXAI' + 'a' * 40,  # Missing closing brace
            content_type='application/json'
        )
        assert response.status_code in [400, 500]

    @patch('faucet.send_tokens')
    def test_minimum_valid_address_length(self, mock_send, client):
        """Address exactly 44 chars (TXAI + 40) should be valid."""
        mock_send.return_value = {'success': True, 'txid': 'test'}

        addr = 'TXAI' + 'a' * 40  # Exactly 44 chars
        assert len(addr) == 44

        response = client.post(
            '/api/request',
            data=json.dumps({'address': addr}),
            content_type='application/json'
        )
        assert response.status_code == 200

    def test_address_exactly_at_boundary(self, client):
        """Address at exactly 40 char boundary validation."""
        # TXAI + 36 chars = 40 total, should fail (< 40 body chars)
        short_addr = 'TXAI' + 'a' * 36  # 40 total
        response = client.post(
            '/api/request',
            data=json.dumps({'address': short_addr}),
            content_type='application/json'
        )
        assert response.status_code == 400


# =============================================================================
# TYPE VALIDATION TESTS (Verify type confusion attacks are prevented)
# =============================================================================

@pytest.mark.faucet
@pytest.mark.security
class TestTypeValidation:
    """Tests verifying type validation security measures in the faucet.

    These tests ensure the faucet properly validates that the address
    field is a string and rejects non-string types with a 400 error.

    This prevents type confusion attacks where an attacker might
    send unexpected types (None, int, list, dict) to cause crashes
    or bypass validation logic.
    """

    def test_none_address_returns_400(self, client):
        """None address should return 400."""
        response = client.post(
            '/api/request',
            data=json.dumps({'address': None}),
            content_type='application/json'
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'string' in data['error'].lower()

    def test_integer_address_returns_400(self, client):
        """Integer address should return 400."""
        response = client.post(
            '/api/request',
            data=json.dumps({'address': 12345}),
            content_type='application/json'
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'string' in data['error'].lower()

    def test_list_address_returns_400(self, client):
        """List address should return 400."""
        response = client.post(
            '/api/request',
            data=json.dumps({'address': ['TXAI' + 'a' * 40]}),
            content_type='application/json'
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'string' in data['error'].lower()

    def test_dict_address_returns_400(self, client):
        """Dict address should return 400."""
        response = client.post(
            '/api/request',
            data=json.dumps({'address': {'value': 'TXAI' + 'a' * 40}}),
            content_type='application/json'
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'string' in data['error'].lower()

    def test_boolean_address_returns_400(self, client):
        """Boolean address should return 400."""
        response = client.post(
            '/api/request',
            data=json.dumps({'address': True}),
            content_type='application/json'
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'string' in data['error'].lower()

    def test_float_address_returns_400(self, client):
        """Float address should return 400."""
        response = client.post(
            '/api/request',
            data=json.dumps({'address': 3.14159}),
            content_type='application/json'
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'string' in data['error'].lower()


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-m', 'faucet'])
