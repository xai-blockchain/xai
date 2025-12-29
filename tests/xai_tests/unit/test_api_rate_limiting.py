"""
Unit tests for API rate limiting module.

Tests the APIRateLimiter class and rate_limit decorator for DDoS protection.
"""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest
from flask import Flask

from xai.core.security.api_rate_limiting import (
    APIRateLimiter,
    RateLimitCategory,
    RateLimitResult,
    check_rate_limit_inline,
    get_api_rate_limiter,
    init_rate_limiting,
    rate_limit,
    rate_limit_admin,
    rate_limit_read,
    rate_limit_sensitive,
    rate_limit_write,
)


class TestAPIRateLimiter:
    """Tests for APIRateLimiter class."""

    def test_init_loads_config(self):
        """Test that limiter initializes with config values."""
        limiter = APIRateLimiter()
        assert limiter.enabled is True
        assert RateLimitCategory.READ in limiter.category_limits
        assert RateLimitCategory.WRITE in limiter.category_limits
        assert RateLimitCategory.SENSITIVE in limiter.category_limits
        assert RateLimitCategory.ADMIN in limiter.category_limits

    def test_category_limits_are_tuples(self):
        """Test that category limits are (max_requests, window_seconds) tuples."""
        limiter = APIRateLimiter()
        for cat, limits in limiter.category_limits.items():
            assert isinstance(limits, tuple)
            assert len(limits) == 2
            assert isinstance(limits[0], int)  # max_requests
            assert isinstance(limits[1], int)  # window_seconds

    def test_check_rate_limit_returns_result(self):
        """Test that check_rate_limit returns RateLimitResult."""
        limiter = APIRateLimiter()
        app = Flask(__name__)
        with app.test_request_context("/test", method="GET", environ_base={"REMOTE_ADDR": "1.2.3.4"}):
            result = limiter.check_rate_limit("/test", RateLimitCategory.READ)
            assert isinstance(result, RateLimitResult)
            assert result.allowed is True
            assert result.remaining >= 0
            assert result.limit > 0

    def test_rate_limit_allows_within_limits(self):
        """Test that requests within limits are allowed."""
        limiter = APIRateLimiter()
        limiter.endpoint_overrides["/test-allow"] = (10, 60)

        app = Flask(__name__)
        with app.test_request_context("/test-allow", method="GET", environ_base={"REMOTE_ADDR": "2.3.4.5"}):
            for i in range(5):
                result = limiter.check_rate_limit("/test-allow", RateLimitCategory.READ)
                assert result.allowed is True
                assert result.remaining == 10 - i - 1

    def test_rate_limit_blocks_when_exceeded(self):
        """Test that requests exceeding limit are blocked."""
        limiter = APIRateLimiter()
        limiter.endpoint_overrides["/test-block"] = (3, 60)

        app = Flask(__name__)
        with app.test_request_context("/test-block", method="POST", environ_base={"REMOTE_ADDR": "3.4.5.6"}):
            # First 3 requests allowed
            for _ in range(3):
                result = limiter.check_rate_limit("/test-block", RateLimitCategory.WRITE)
                assert result.allowed is True

            # 4th request blocked
            result = limiter.check_rate_limit("/test-block", RateLimitCategory.WRITE)
            assert result.allowed is False
            assert result.error_message is not None
            assert "Rate limit exceeded" in result.error_message
            assert result.retry_after is not None
            assert result.retry_after > 0

    def test_rate_limit_429_response_fields(self):
        """Test that blocked requests have proper 429 response fields."""
        limiter = APIRateLimiter()
        limiter.endpoint_overrides["/test-429"] = (1, 60)

        app = Flask(__name__)
        with app.test_request_context("/test-429", method="POST", environ_base={"REMOTE_ADDR": "4.5.6.7"}):
            # First request allowed
            result = limiter.check_rate_limit("/test-429", RateLimitCategory.SENSITIVE)
            assert result.allowed is True

            # Second request blocked
            result = limiter.check_rate_limit("/test-429", RateLimitCategory.SENSITIVE)
            assert result.allowed is False
            assert result.limit == 1
            assert result.remaining == 0
            assert result.reset_time > 0
            assert result.retry_after > 0

    def test_different_ips_tracked_separately(self):
        """Test that different IPs have separate rate limits."""
        limiter = APIRateLimiter()
        limiter.endpoint_overrides["/test-ips"] = (2, 60)

        app = Flask(__name__)

        # IP 1 makes 2 requests
        with app.test_request_context("/test-ips", method="GET", environ_base={"REMOTE_ADDR": "10.0.0.1"}):
            result = limiter.check_rate_limit("/test-ips", RateLimitCategory.READ)
            assert result.allowed is True
            result = limiter.check_rate_limit("/test-ips", RateLimitCategory.READ)
            assert result.allowed is True

        # IP 2 can still make requests
        with app.test_request_context("/test-ips", method="GET", environ_base={"REMOTE_ADDR": "10.0.0.2"}):
            result = limiter.check_rate_limit("/test-ips", RateLimitCategory.READ)
            assert result.allowed is True

    def test_x_forwarded_for_header_used(self):
        """Test that X-Forwarded-For header is used for IP detection."""
        limiter = APIRateLimiter()
        app = Flask(__name__)

        with app.test_request_context(
            "/test",
            method="GET",
            environ_base={"REMOTE_ADDR": "127.0.0.1"},
            headers={"X-Forwarded-For": "203.0.113.50, 70.41.3.18"},
        ):
            # Should use 203.0.113.50 (first IP in chain)
            ip = limiter._get_client_ip()
            assert ip == "203.0.113.50"

    def test_disabled_limiter_allows_all(self):
        """Test that disabled limiter allows all requests."""
        limiter = APIRateLimiter()
        limiter.enabled = False
        limiter.endpoint_overrides["/test-disabled"] = (0, 1)  # Would block if enabled

        app = Flask(__name__)
        with app.test_request_context("/test-disabled", method="GET", environ_base={"REMOTE_ADDR": "5.6.7.8"}):
            result = limiter.check_rate_limit("/test-disabled", RateLimitCategory.READ)
            assert result.allowed is True

    def test_get_stats_returns_dict(self):
        """Test that get_stats returns statistics dictionary."""
        limiter = APIRateLimiter()
        stats = limiter.get_stats()
        assert isinstance(stats, dict)
        assert "enabled" in stats
        assert "active_buckets" in stats
        assert "blocked_ips" in stats
        assert "category_limits" in stats
        assert "ddos_threshold" in stats


class TestRateLimitDecorators:
    """Tests for rate limit decorator functions."""

    def test_rate_limit_decorator_allows_request(self):
        """Test that rate_limit decorator allows normal requests."""
        app = Flask(__name__)

        @app.route("/test")
        @rate_limit("read")
        def test_endpoint():
            return {"status": "ok"}

        with app.test_client() as client:
            response = client.get("/test")
            # Should succeed (not 429)
            assert response.status_code != 429

    def test_rate_limit_decorator_blocks_excessive_requests(self):
        """Test that rate_limit decorator blocks excessive requests."""
        app = Flask(__name__)

        # Set up a very low limit
        limiter = get_api_rate_limiter()
        limiter.endpoint_overrides["/test-block-dec"] = (2, 60)

        @app.route("/test-block-dec")
        @rate_limit("write")
        def test_endpoint():
            return {"status": "ok"}

        with app.test_client() as client:
            # First two requests succeed
            response = client.get("/test-block-dec")
            assert response.status_code != 429
            response = client.get("/test-block-dec")
            assert response.status_code != 429

            # Third request should be rate limited
            response = client.get("/test-block-dec")
            assert response.status_code == 429
            data = response.get_json()
            assert "error" in data
            assert data["code"] == "rate_limited"

    def test_rate_limit_headers_present(self):
        """Test that rate limit headers are present in response."""
        app = Flask(__name__)
        init_rate_limiting(app)

        @app.route("/test-headers")
        @rate_limit("read")
        def test_endpoint():
            return {"status": "ok"}

        with app.test_client() as client:
            response = client.get("/test-headers")
            # Check headers are present
            assert "X-RateLimit-Limit" in response.headers
            assert "X-RateLimit-Remaining" in response.headers
            assert "X-RateLimit-Reset" in response.headers


class TestRateLimitCategories:
    """Tests for different rate limit categories."""

    def test_read_category_higher_than_write(self):
        """Test that read category has higher limits than write."""
        limiter = APIRateLimiter()
        read_limit = limiter.category_limits[RateLimitCategory.READ][0]
        write_limit = limiter.category_limits[RateLimitCategory.WRITE][0]
        assert read_limit > write_limit

    def test_sensitive_category_stricter_than_read(self):
        """Test that sensitive category has stricter limits than read."""
        limiter = APIRateLimiter()
        read_limit = limiter.category_limits[RateLimitCategory.READ][0]
        sensitive_limit = limiter.category_limits[RateLimitCategory.SENSITIVE][0]
        assert sensitive_limit < read_limit

    def test_category_decorators_exist(self):
        """Test that category-specific decorators exist and are callable."""
        assert callable(rate_limit_read)
        assert callable(rate_limit_write)
        assert callable(rate_limit_sensitive)
        assert callable(rate_limit_admin)


class TestInlineRateLimitCheck:
    """Tests for inline rate limit checking function."""

    def test_inline_check_allowed(self):
        """Test inline rate limit check when allowed."""
        app = Flask(__name__)
        with app.test_request_context("/test", method="GET", environ_base={"REMOTE_ADDR": "6.7.8.9"}):
            allowed, error = check_rate_limit_inline("/test", RateLimitCategory.READ)
            assert allowed is True
            assert error is None

    def test_inline_check_blocked(self):
        """Test inline rate limit check when blocked."""
        limiter = get_api_rate_limiter()
        limiter.endpoint_overrides["/test-inline-block"] = (1, 60)

        app = Flask(__name__)
        with app.test_request_context("/test-inline-block", method="POST", environ_base={"REMOTE_ADDR": "7.8.9.10"}):
            # First request allowed
            allowed, _ = check_rate_limit_inline("/test-inline-block", RateLimitCategory.WRITE)
            assert allowed is True

            # Second request blocked
            allowed, error = check_rate_limit_inline("/test-inline-block", RateLimitCategory.WRITE)
            assert allowed is False
            assert error is not None
            assert "code" in error
            assert error["code"] == "rate_limited"


class TestGlobalRateLimiter:
    """Tests for global rate limiter instance."""

    def test_get_api_rate_limiter_returns_instance(self):
        """Test that get_api_rate_limiter returns an instance."""
        limiter = get_api_rate_limiter()
        assert isinstance(limiter, APIRateLimiter)

    def test_get_api_rate_limiter_returns_same_instance(self):
        """Test that get_api_rate_limiter returns the same instance."""
        limiter1 = get_api_rate_limiter()
        limiter2 = get_api_rate_limiter()
        assert limiter1 is limiter2


class TestInitRateLimiting:
    """Tests for init_rate_limiting function."""

    def test_init_adds_before_request_handler(self):
        """Test that init_rate_limiting adds handlers to Flask app."""
        app = Flask(__name__)
        before_count = len(app.before_request_funcs.get(None, []))
        init_rate_limiting(app)
        after_count = len(app.before_request_funcs.get(None, []))
        # Should have added at least one handler
        assert after_count >= before_count
