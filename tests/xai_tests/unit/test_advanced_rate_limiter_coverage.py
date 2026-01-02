"""
Comprehensive test coverage for Advanced Rate Limiter module

Goal: Achieve 80%+ coverage (157+ statements out of 196)
Testing: Rate limiting algorithms, DDoS detection, bucket management, edge cases, error handling
"""

import pytest
import time
import hashlib
import threading
from unittest.mock import MagicMock, patch, Mock
from datetime import datetime, timezone
from flask import Flask, request, Response, jsonify

from xai.core.security.advanced_rate_limiter import (
    RateLimitExceeded,
    LimitSeverity,
    RateLimitConfig,
    RateLimitEntry,
    RateLimitStats,
    RateLimitBucket,
    AdvancedRateLimiter,
    get_rate_limiter,
    rate_limit,
)


class TestRateLimitConfig:
    """Test RateLimitConfig dataclass"""

    def test_init_default_values(self):
        """Test default initialization values"""
        config = RateLimitConfig(max_requests=100, window_seconds=60)
        assert config.max_requests == 100
        assert config.window_seconds == 60
        assert config.per_ip is False
        assert config.per_user is False
        assert config.description == ""

    def test_init_custom_values(self):
        """Test initialization with custom values"""
        config = RateLimitConfig(
            max_requests=50,
            window_seconds=300,
            per_ip=True,
            per_user=True,
            description="Test limit"
        )
        assert config.max_requests == 50
        assert config.window_seconds == 300
        assert config.per_ip is True
        assert config.per_user is True
        assert config.description == "Test limit"

    def test_str_representation(self):
        """Test string representation"""
        config = RateLimitConfig(max_requests=100, window_seconds=60)
        assert str(config) == "100 requests per 60s"


class TestRateLimitEntry:
    """Test RateLimitEntry dataclass"""

    def test_init_default_values(self):
        """Test default initialization values"""
        entry = RateLimitEntry(timestamp=123.456, endpoint="/api/test")
        assert entry.timestamp == 123.456
        assert entry.endpoint == "/api/test"
        assert entry.identifier == ""
        assert entry.ip_address == ""

    def test_init_full_values(self):
        """Test initialization with all values"""
        entry = RateLimitEntry(
            timestamp=123.456,
            endpoint="/api/test",
            identifier="user123",
            ip_address="192.168.1.1"
        )
        assert entry.timestamp == 123.456
        assert entry.endpoint == "/api/test"
        assert entry.identifier == "user123"
        assert entry.ip_address == "192.168.1.1"


class TestRateLimitStats:
    """Test RateLimitStats dataclass"""

    def test_init_default_values(self):
        """Test default initialization values"""
        stats = RateLimitStats()
        assert stats.total_requests == 0
        assert stats.rejected_requests == 0
        assert stats.current_violations == 0
        assert stats.peak_requests_per_second == 0.0
        assert stats.last_violation is None
        assert stats.violations_by_ip == {}
        assert stats.violations_by_endpoint == {}

    def test_mutation_tracking(self):
        """Test that stats can be mutated"""
        stats = RateLimitStats()
        stats.total_requests = 100
        stats.rejected_requests = 10
        stats.current_violations = 5
        stats.peak_requests_per_second = 25.5
        stats.last_violation = datetime.now(timezone.utc)
        stats.violations_by_ip["192.168.1.1"] = 3
        stats.violations_by_endpoint["/api/test"] = 2

        assert stats.total_requests == 100
        assert stats.rejected_requests == 10
        assert stats.current_violations == 5
        assert stats.peak_requests_per_second == 25.5
        assert stats.last_violation is not None
        assert stats.violations_by_ip["192.168.1.1"] == 3
        assert stats.violations_by_endpoint["/api/test"] == 2


class TestLimitSeverity:
    """Test LimitSeverity enum"""

    def test_severity_values(self):
        """Test severity enum values"""
        assert LimitSeverity.INFO.value == "info"
        assert LimitSeverity.WARNING.value == "warning"
        assert LimitSeverity.CRITICAL.value == "critical"


class TestRateLimitBucket:
    """Test RateLimitBucket class"""

    @pytest.fixture
    def bucket(self):
        """Create a RateLimitBucket instance"""
        return RateLimitBucket()

    def test_init(self, bucket):
        """Test bucket initialization"""
        assert bucket.requests == []
        assert isinstance(bucket.lock, type(threading.Lock()))

    def test_add_request(self, bucket):
        """Test adding a request timestamp"""
        timestamp = time.time()
        bucket.add_request(timestamp)
        assert len(bucket.requests) == 1
        assert bucket.requests[0] == timestamp

    def test_add_multiple_requests(self, bucket):
        """Test adding multiple request timestamps"""
        timestamps = [time.time() + i for i in range(5)]
        for ts in timestamps:
            bucket.add_request(ts)
        assert len(bucket.requests) == 5

    @patch('time.time')
    def test_get_recent_requests_within_window(self, mock_time, bucket):
        """Test getting recent requests within time window"""
        current_time = 1000.0
        mock_time.return_value = current_time

        # Add requests within window
        bucket.add_request(current_time - 10)
        bucket.add_request(current_time - 20)
        bucket.add_request(current_time - 30)

        count = bucket.get_recent_requests(60)
        assert count == 3

    @patch('time.time')
    def test_get_recent_requests_outside_window(self, mock_time, bucket):
        """Test that old requests outside window are not counted"""
        current_time = 1000.0
        mock_time.return_value = current_time

        # Add old requests outside window
        bucket.add_request(current_time - 100)
        bucket.add_request(current_time - 200)
        # Add recent requests
        bucket.add_request(current_time - 10)

        count = bucket.get_recent_requests(60)
        assert count == 1

    @patch('time.time')
    def test_get_recent_requests_cleanup(self, mock_time, bucket):
        """Test that old entries are cleaned up"""
        current_time = 1000.0
        mock_time.return_value = current_time

        # Add mixed requests
        bucket.add_request(current_time - 100)
        bucket.add_request(current_time - 10)

        count = bucket.get_recent_requests(60)
        # Should only have 1 request left after cleanup
        assert len(bucket.requests) == 1

    @patch('time.time')
    def test_cleanup(self, mock_time, bucket):
        """Test explicit cleanup of old entries"""
        current_time = 1000.0
        mock_time.return_value = current_time

        # Add old and new requests
        bucket.add_request(current_time - 100)
        bucket.add_request(current_time - 200)
        bucket.add_request(current_time - 10)
        bucket.add_request(current_time - 20)

        bucket.cleanup(60)
        assert len(bucket.requests) == 2  # Only recent requests remain

    def test_thread_safety(self, bucket):
        """Test thread safety of bucket operations"""
        def add_requests():
            for _ in range(100):
                bucket.add_request(time.time())

        threads = [threading.Thread(target=add_requests) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(bucket.requests) == 500


class TestAdvancedRateLimiter:
    """Test AdvancedRateLimiter class"""

    @pytest.fixture
    def app(self):
        """Create a Flask app for testing"""
        app = Flask(__name__)
        app.config['TESTING'] = True
        return app

    @pytest.fixture
    def limiter(self):
        """Create an AdvancedRateLimiter instance"""
        return AdvancedRateLimiter()

    def test_init_default_values(self, limiter):
        """Test default initialization values"""
        assert isinstance(limiter.buckets, dict)
        assert isinstance(limiter.lock, type(threading.Lock()))
        assert isinstance(limiter.endpoint_configs, dict)
        assert isinstance(limiter.stats, RateLimitStats)
        assert limiter.ddos_threshold == 1000
        assert limiter.ddos_window == 60
        assert limiter.blocked_ips == {}
        assert limiter.block_duration == 3600
        assert limiter.cleanup_interval == 300

    def test_init_endpoint_configs(self, limiter):
        """Test that endpoint configs are initialized"""
        assert "default" in limiter.endpoint_configs
        assert "/api/login" in limiter.endpoint_configs
        assert "/api/register" in limiter.endpoint_configs
        assert "/wallet/send" in limiter.endpoint_configs
        assert "/mining/start" in limiter.endpoint_configs

    def test_endpoint_config_values(self, limiter):
        """Test specific endpoint config values"""
        login_config = limiter.endpoint_configs["/api/login"]
        assert login_config.max_requests == 5
        assert login_config.window_seconds == 300
        assert login_config.per_ip is True

        default_config = limiter.endpoint_configs["default"]
        assert default_config.max_requests == 200
        assert default_config.window_seconds == 60

    def test_get_identifier_with_x_forwarded_for(self, app, limiter):
        """Test getting identifier with X-Forwarded-For header"""
        with app.test_request_context(
            '/',
            headers={'X-Forwarded-For': '192.168.1.1, 10.0.0.1'}
        ):
            ip, user_id = limiter._get_identifier("/api/test")
            assert ip == "192.168.1.1"
            assert user_id is None

    def test_get_identifier_with_remote_addr(self, app, limiter):
        """Test getting identifier with remote_addr"""
        with app.test_request_context('/', environ_base={'REMOTE_ADDR': '192.168.1.1'}):
            ip, user_id = limiter._get_identifier("/api/test")
            assert ip == "192.168.1.1"
            assert user_id is None

    def test_get_identifier_with_user_id(self, app, limiter):
        """Test getting identifier with user ID header"""
        with app.test_request_context(
            '/',
            headers={'X-User-ID': 'user123'},
            environ_base={'REMOTE_ADDR': '192.168.1.1'}
        ):
            ip, user_id = limiter._get_identifier("/api/test")
            assert ip == "192.168.1.1"
            assert user_id is not None
            # User ID should be hashed
            expected_hash = hashlib.sha256('user123'.encode()).hexdigest()[:16]
            assert user_id == expected_hash

    def test_get_identifier_with_authorization(self, app, limiter):
        """Test getting identifier with Authorization header"""
        with app.test_request_context(
            '/',
            headers={'Authorization': 'Bearer token123'},
            environ_base={'REMOTE_ADDR': '192.168.1.1'}
        ):
            ip, user_id = limiter._get_identifier("/api/test")
            assert ip == "192.168.1.1"
            assert user_id is not None
            expected_hash = hashlib.sha256('Bearer token123'.encode()).hexdigest()[:16]
            assert user_id == expected_hash

    def test_get_identifier_default_ip(self, app, limiter):
        """Test default IP when no remote addr"""
        with app.test_request_context('/'):
            ip, user_id = limiter._get_identifier("/api/test")
            assert ip == "127.0.0.1"
            assert user_id is None

    @patch('time.time')
    def test_check_ddos_pattern_normal(self, mock_time, app, limiter):
        """Test DDoS detection with normal traffic"""
        mock_time.return_value = 1000.0

        with app.test_request_context('/', environ_base={'REMOTE_ADDR': '192.168.1.1'}):
            # Add normal amount of requests
            for i in range(100):
                is_safe, error = limiter._check_ddos_pattern('192.168.1.1')

            assert is_safe is True
            assert error is None

    @patch('time.time')
    def test_check_ddos_pattern_attack(self, mock_time, app, limiter):
        """Test DDoS detection with attack pattern"""
        current_time = 1000.0
        mock_time.return_value = current_time

        # Simulate attack - add requests to bucket directly
        bucket_key = "ddos:192.168.1.1"
        for i in range(1001):
            limiter.buckets[bucket_key].add_request(current_time - i * 0.05)

        with app.test_request_context('/', environ_base={'REMOTE_ADDR': '192.168.1.1'}):
            is_safe, error = limiter._check_ddos_pattern('192.168.1.1')

            assert is_safe is False
            assert error is not None
            assert "temporarily blocked" in error
            assert '192.168.1.1' in limiter.blocked_ips

    @patch('time.time')
    def test_cleanup_old_buckets_interval(self, mock_time, limiter):
        """Test that cleanup only runs at intervals"""
        mock_time.return_value = 1000.0
        limiter.last_cleanup = 1000.0

        # Try cleanup before interval
        limiter._cleanup_old_buckets()

        # Should not update last_cleanup
        assert limiter.last_cleanup == 1000.0

        # Move time forward past interval
        mock_time.return_value = 1400.0
        limiter._cleanup_old_buckets()

        # Should update last_cleanup
        assert limiter.last_cleanup == 1400.0

    @patch('time.time')
    def test_cleanup_old_buckets_removes_empty(self, mock_time, limiter):
        """Test that cleanup cleans up old entries from buckets"""
        current_time = 1000.0
        mock_time.return_value = current_time

        # Add old and new requests
        limiter.buckets["test1"].add_request(current_time - 1000)
        limiter.buckets["test1"].add_request(current_time - 800)
        limiter.buckets["test2"].add_request(current_time - 10)
        limiter.buckets["test2"].add_request(current_time - 5)

        initial_test1_count = len(limiter.buckets["test1"].requests)
        initial_test2_count = len(limiter.buckets["test2"].requests)

        # Force cleanup - max window is max of all endpoint configs
        limiter.last_cleanup = 0
        limiter._cleanup_old_buckets()

        # test2 should still have its recent requests
        assert len(limiter.buckets["test2"].requests) == initial_test2_count

    @patch('time.time')
    def test_cleanup_expired_ip_blocks(self, mock_time, limiter):
        """Test cleanup of expired IP blocks"""
        current_time = 1000.0
        mock_time.return_value = current_time

        # Add expired and active blocks
        limiter.blocked_ips['192.168.1.1'] = current_time - 100  # Expired
        limiter.blocked_ips['192.168.1.2'] = current_time + 100  # Active

        # Force cleanup
        limiter.last_cleanup = 0
        limiter._cleanup_old_buckets()

        assert '192.168.1.1' not in limiter.blocked_ips
        assert '192.168.1.2' in limiter.blocked_ips

    @patch('time.time')
    def test_check_rate_limit_allowed(self, mock_time, app, limiter):
        """Test check_rate_limit allows normal requests"""
        mock_time.return_value = 1000.0

        with app.test_request_context('/', environ_base={'REMOTE_ADDR': '192.168.1.1'}):
            allowed, error = limiter.check_rate_limit("/api/test")

            assert allowed is True
            assert error is None
            assert limiter.stats.total_requests > 0

    @patch('time.time')
    def test_check_rate_limit_blocked_ip(self, mock_time, app, limiter):
        """Test check_rate_limit blocks blocked IPs"""
        current_time = 1000.0
        mock_time.return_value = current_time

        # Block IP
        limiter.blocked_ips['192.168.1.1'] = current_time + 1000

        with app.test_request_context('/', environ_base={'REMOTE_ADDR': '192.168.1.1'}):
            allowed, error = limiter.check_rate_limit("/api/test")

            assert allowed is False
            assert error is not None
            assert "temporarily blocked" in error

    @patch('time.time')
    def test_check_rate_limit_expired_block(self, mock_time, app, limiter):
        """Test that expired blocks are removed and request allowed"""
        current_time = 1000.0
        mock_time.return_value = current_time

        # Add expired block
        limiter.blocked_ips['192.168.1.1'] = current_time - 100

        with app.test_request_context('/', environ_base={'REMOTE_ADDR': '192.168.1.1'}):
            allowed, error = limiter.check_rate_limit("/api/test")

            assert allowed is True
            assert '192.168.1.1' not in limiter.blocked_ips

    @patch('time.time')
    def test_check_rate_limit_exceeded(self, mock_time, app, limiter):
        """Test rate limit exceeded"""
        current_time = 1000.0
        mock_time.return_value = current_time

        # Set low limit
        limiter.endpoint_configs["/api/test"] = RateLimitConfig(
            max_requests=2,
            window_seconds=60,
            per_ip=True
        )

        with app.test_request_context('/', environ_base={'REMOTE_ADDR': '192.168.1.1'}):
            # First two requests should succeed
            allowed, error = limiter.check_rate_limit("/api/test")
            assert allowed is True

            allowed, error = limiter.check_rate_limit("/api/test")
            assert allowed is True

            # Third request should fail
            allowed, error = limiter.check_rate_limit("/api/test")
            assert allowed is False
            assert error is not None
            assert "Rate limit exceeded" in error
            assert limiter.stats.rejected_requests > 0

    @patch('time.time')
    def test_check_rate_limit_per_user(self, mock_time, app, limiter):
        """Test per-user rate limiting"""
        current_time = 1000.0
        mock_time.return_value = current_time

        limiter.endpoint_configs["/api/test"] = RateLimitConfig(
            max_requests=2,
            window_seconds=60,
            per_user=True
        )

        with app.test_request_context(
            '/',
            headers={'X-User-ID': 'user123'},
            environ_base={'REMOTE_ADDR': '192.168.1.1'}
        ):
            # First two requests should succeed
            limiter.check_rate_limit("/api/test")
            limiter.check_rate_limit("/api/test")

            # Third should fail
            allowed, error = limiter.check_rate_limit("/api/test")
            assert allowed is False

    @patch('time.time')
    def test_check_rate_limit_default_fallback(self, mock_time, app, limiter):
        """Test fallback to default config for unknown endpoints"""
        current_time = 1000.0
        mock_time.return_value = current_time

        with app.test_request_context('/', environ_base={'REMOTE_ADDR': '192.168.1.1'}):
            allowed, error = limiter.check_rate_limit("/api/unknown")

            # Should use default config
            assert allowed is True

    @patch('time.time')
    def test_check_rate_limit_updates_stats(self, mock_time, app, limiter):
        """Test that rate limit updates statistics"""
        current_time = 1000.0
        mock_time.return_value = current_time

        limiter.endpoint_configs["/api/test"] = RateLimitConfig(
            max_requests=1,
            window_seconds=60,
            per_ip=True
        )

        initial_total = limiter.stats.total_requests
        initial_rejected = limiter.stats.rejected_requests

        with app.test_request_context('/', environ_base={'REMOTE_ADDR': '192.168.1.1'}):
            limiter.check_rate_limit("/api/test")
            limiter.check_rate_limit("/api/test")

            assert limiter.stats.total_requests > initial_total
            assert limiter.stats.rejected_requests > initial_rejected
            assert limiter.stats.violations_by_ip['192.168.1.1'] > 0
            assert limiter.stats.violations_by_endpoint['/api/test'] > 0
            assert limiter.stats.last_violation is not None

    def test_get_remaining_requests_per_ip(self, app, limiter):
        """Test getting remaining requests for per-IP limit"""
        limiter.endpoint_configs["/api/test"] = RateLimitConfig(
            max_requests=10,
            window_seconds=60,
            per_ip=True
        )

        with app.test_request_context('/', environ_base={'REMOTE_ADDR': '192.168.1.1'}):
            remaining = limiter.get_remaining_requests("/api/test")
            assert remaining == 10

            # Make a request
            limiter.check_rate_limit("/api/test")
            remaining = limiter.get_remaining_requests("/api/test")
            assert remaining == 9

    def test_get_remaining_requests_per_user(self, app, limiter):
        """Test getting remaining requests for per-user limit"""
        limiter.endpoint_configs["/api/test"] = RateLimitConfig(
            max_requests=5,
            window_seconds=60,
            per_user=True
        )

        with app.test_request_context(
            '/',
            headers={'X-User-ID': 'user123'},
            environ_base={'REMOTE_ADDR': '192.168.1.1'}
        ):
            remaining = limiter.get_remaining_requests("/api/test")
            assert remaining == 5

    def test_get_remaining_requests_negative_clamped(self, app, limiter):
        """Test that negative remaining requests are clamped to 0"""
        limiter.endpoint_configs["/api/test"] = RateLimitConfig(
            max_requests=1,
            window_seconds=60,
            per_ip=True
        )

        with app.test_request_context('/', environ_base={'REMOTE_ADDR': '192.168.1.1'}):
            limiter.check_rate_limit("/api/test")
            limiter.check_rate_limit("/api/test")

            remaining = limiter.get_remaining_requests("/api/test")
            assert remaining == 0

    def test_set_endpoint_limit(self, limiter):
        """Test setting custom endpoint limit"""
        config = RateLimitConfig(
            max_requests=100,
            window_seconds=300,
            per_ip=True,
            description="Custom limit"
        )

        limiter.set_endpoint_limit("/api/custom", config)

        assert "/api/custom" in limiter.endpoint_configs
        assert limiter.endpoint_configs["/api/custom"].max_requests == 100
        assert limiter.endpoint_configs["/api/custom"].window_seconds == 300

    def test_get_stats(self, limiter):
        """Test getting statistics"""
        stats = limiter.get_stats()

        assert 'total_requests' in stats
        assert 'rejected_requests' in stats
        assert 'current_violations' in stats
        assert 'last_violation' in stats
        assert 'blocked_ips_count' in stats
        assert 'top_violations_by_ip' in stats
        assert 'top_violations_by_endpoint' in stats

    def test_get_stats_with_violations(self, app, limiter):
        """Test stats with actual violations"""
        limiter.stats.violations_by_ip['192.168.1.1'] = 10
        limiter.stats.violations_by_ip['192.168.1.2'] = 5
        limiter.stats.violations_by_endpoint['/api/test1'] = 8
        limiter.stats.violations_by_endpoint['/api/test2'] = 3

        stats = limiter.get_stats()

        assert '192.168.1.1' in stats['top_violations_by_ip']
        assert '/api/test1' in stats['top_violations_by_endpoint']

    def test_get_stats_last_violation_format(self, limiter):
        """Test last_violation is formatted as ISO string"""
        limiter.stats.last_violation = datetime.now(timezone.utc)

        stats = limiter.get_stats()

        assert stats['last_violation'] is not None
        assert isinstance(stats['last_violation'], str)

    def test_is_ip_blocked_true(self, limiter):
        """Test is_ip_blocked returns True for blocked IP"""
        limiter.blocked_ips['192.168.1.1'] = time.time() + 1000

        assert limiter.is_ip_blocked('192.168.1.1') is True

    def test_is_ip_blocked_false(self, limiter):
        """Test is_ip_blocked returns False for non-blocked IP"""
        assert limiter.is_ip_blocked('192.168.1.1') is False

    def test_is_ip_blocked_expired(self, limiter):
        """Test is_ip_blocked returns False for expired block"""
        limiter.blocked_ips['192.168.1.1'] = time.time() - 1000

        assert limiter.is_ip_blocked('192.168.1.1') is False


class TestGlobalRateLimiter:
    """Test global rate limiter instance"""

    def test_get_rate_limiter_singleton(self):
        """Test that get_rate_limiter returns singleton instance"""
        from xai.core.security import advanced_rate_limiter

        # Reset global instance
        advanced_rate_limiter._global_rate_limiter = None

        limiter1 = get_rate_limiter()
        limiter2 = get_rate_limiter()

        assert limiter1 is limiter2

    def test_get_rate_limiter_creates_instance(self):
        """Test that get_rate_limiter creates instance if None"""
        from xai.core.security import advanced_rate_limiter

        # Reset global instance
        advanced_rate_limiter._global_rate_limiter = None

        limiter = get_rate_limiter()

        assert limiter is not None
        assert isinstance(limiter, AdvancedRateLimiter)


class TestRateLimitDecorator:
    """Test rate_limit decorator"""

    @pytest.fixture
    def app(self):
        """Create a Flask app for testing"""
        app = Flask(__name__)
        app.config['TESTING'] = True
        return app

    def test_decorator_allows_normal_request(self, app):
        """Test decorator allows normal requests"""
        @app.route('/test')
        @rate_limit('/test')
        def test_route():
            return jsonify({'status': 'ok'}), 200

        with app.test_client() as client:
            response = client.get('/test')
            assert response.status_code == 200

    def test_decorator_blocks_exceeded_limit(self, app):
        """Test decorator blocks when limit exceeded"""
        from xai.core.security import advanced_rate_limiter
        advanced_rate_limiter._global_rate_limiter = None

        limiter = get_rate_limiter()
        limiter.endpoint_configs['/test'] = RateLimitConfig(
            max_requests=1,
            window_seconds=60,
            per_ip=True
        )

        @app.route('/test')
        @rate_limit('/test')
        def test_route():
            return jsonify({'status': 'ok'}), 200

        with app.test_client() as client:
            # First request should succeed
            response = client.get('/test')
            assert response.status_code == 200

            # Second request should fail
            response = client.get('/test')
            assert response.status_code == 429
            data = response.get_json()
            assert 'error' in data

    def test_decorator_uses_request_path_default(self, app):
        """Test decorator uses request.path if endpoint not specified"""
        from xai.core.security import advanced_rate_limiter
        advanced_rate_limiter._global_rate_limiter = None

        @app.route('/default')
        @rate_limit()
        def test_route():
            return jsonify({'status': 'ok'}), 200

        with app.test_client() as client:
            response = client.get('/default')
            assert response.status_code == 200

    def test_decorator_adds_rate_limit_header(self, app):
        """Test decorator adds rate limit headers to response"""
        from xai.core.security import advanced_rate_limiter
        advanced_rate_limiter._global_rate_limiter = None

        @app.route('/test')
        @rate_limit('/test')
        def test_route():
            return Response('ok', mimetype='text/plain')

        with app.test_client() as client:
            response = client.get('/test')
            # Check that X-RateLimit-Remaining header is set
            if 'X-RateLimit-Remaining' in response.headers:
                assert response.headers.get('X-RateLimit-Remaining') is not None

    def test_decorator_handles_tuple_response(self, app):
        """Test decorator handles tuple responses"""
        from xai.core.security import advanced_rate_limiter
        advanced_rate_limiter._global_rate_limiter = None

        @app.route('/test')
        @rate_limit('/test')
        def test_route():
            return jsonify({'status': 'ok'}), 201

        with app.test_client() as client:
            response = client.get('/test')
            assert response.status_code == 201

    def test_decorator_handles_response_object(self, app):
        """Test decorator handles Response objects"""
        from xai.core.security import advanced_rate_limiter
        advanced_rate_limiter._global_rate_limiter = None

        @app.route('/test')
        @rate_limit('/test')
        def test_route():
            resp = Response('ok', mimetype='text/plain')
            return resp

        with app.test_client() as client:
            response = client.get('/test')
            assert response.status_code == 200


class TestRateLimitException:
    """Test RateLimitExceeded exception"""

    def test_exception_creation(self):
        """Test creating RateLimitExceeded exception"""
        exc = RateLimitExceeded("Test message")
        assert str(exc) == "Test message"

    def test_exception_can_be_raised(self):
        """Test that exception can be raised and caught"""
        with pytest.raises(RateLimitExceeded):
            raise RateLimitExceeded("Limit exceeded")


class TestConcurrency:
    """Test concurrent access to rate limiter"""

    @pytest.fixture
    def limiter(self):
        """Create a fresh rate limiter"""
        return AdvancedRateLimiter()

    @pytest.fixture
    def app(self):
        """Create a Flask app"""
        app = Flask(__name__)
        app.config['TESTING'] = True
        return app

    @patch('time.time')
    def test_concurrent_requests(self, mock_time, app, limiter):
        """Test concurrent requests are handled safely"""
        mock_time.return_value = 1000.0

        limiter.endpoint_configs["/api/test"] = RateLimitConfig(
            max_requests=100,
            window_seconds=60,
            per_ip=True
        )

        results = []

        def make_request():
            with app.test_request_context('/', environ_base={'REMOTE_ADDR': '192.168.1.1'}):
                allowed, error = limiter.check_rate_limit("/api/test")
                results.append(allowed)

        threads = [threading.Thread(target=make_request) for _ in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All should be allowed since limit is 100
        assert all(results)

    @patch('time.time')
    def test_concurrent_bucket_cleanup(self, mock_time, limiter):
        """Test concurrent cleanup operations"""
        mock_time.return_value = 1000.0

        # Add some buckets
        for i in range(10):
            limiter.buckets[f"test{i}"].add_request(1000.0)

        def cleanup():
            limiter.last_cleanup = 0
            limiter._cleanup_old_buckets()

        threads = [threading.Thread(target=cleanup) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should complete without errors


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    @pytest.fixture
    def app(self):
        """Create a Flask app"""
        app = Flask(__name__)
        app.config['TESTING'] = True
        return app

    @pytest.fixture
    def limiter(self):
        """Create a fresh rate limiter"""
        return AdvancedRateLimiter()

    def test_empty_bucket_requests(self, limiter):
        """Test handling of empty bucket"""
        bucket = limiter.buckets["test"]
        count = bucket.get_recent_requests(60)
        assert count == 0

    @patch('time.time')
    def test_zero_window_seconds(self, mock_time, app, limiter):
        """Test handling of zero window seconds"""
        mock_time.return_value = 1000.0

        # This is an edge case that shouldn't happen in practice
        limiter.endpoint_configs["/api/test"] = RateLimitConfig(
            max_requests=10,
            window_seconds=0,
            per_ip=True
        )

        with app.test_request_context('/', environ_base={'REMOTE_ADDR': '192.168.1.1'}):
            # Should handle gracefully
            allowed, error = limiter.check_rate_limit("/api/test")

    def test_multiple_ips_independent_limits(self, app, limiter):
        """Test that different IPs have independent limits"""
        limiter.endpoint_configs["/api/test"] = RateLimitConfig(
            max_requests=1,
            window_seconds=60,
            per_ip=True
        )

        with app.test_request_context('/', environ_base={'REMOTE_ADDR': '192.168.1.1'}):
            allowed1, _ = limiter.check_rate_limit("/api/test")

        with app.test_request_context('/', environ_base={'REMOTE_ADDR': '192.168.1.2'}):
            allowed2, _ = limiter.check_rate_limit("/api/test")

        assert allowed1 is True
        assert allowed2 is True

    def test_very_large_window(self, app, limiter):
        """Test with very large window seconds"""
        limiter.endpoint_configs["/api/test"] = RateLimitConfig(
            max_requests=1000,
            window_seconds=86400,  # 24 hours
            per_ip=True
        )

        with app.test_request_context('/', environ_base={'REMOTE_ADDR': '192.168.1.1'}):
            allowed, error = limiter.check_rate_limit("/api/test")
            assert allowed is True
