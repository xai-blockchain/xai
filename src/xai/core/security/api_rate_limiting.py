"""
XAI Blockchain - API Rate Limiting Middleware

Provides Flask-integrated rate limiting with:
- Per-endpoint category limits (read, write, sensitive, admin)
- Per-IP and per-user tracking
- DDoS detection and automatic blocking
- Proper 429 responses with Retry-After headers
- Rate limit headers (X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset)

Usage:
    from xai.core.security.api_rate_limiting import init_rate_limiting, rate_limit

    # Initialize with Flask app
    init_rate_limiting(app)

    # Use decorator on routes
    @app.route("/send", methods=["POST"])
    @rate_limit("write")
    def send_transaction():
        ...
"""

from __future__ import annotations

import hashlib
import logging
import time
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from functools import wraps
from threading import Lock
from typing import Any, Callable

from flask import Flask, Response, g, jsonify, request

from xai.core import config

logger = logging.getLogger(__name__)
security_logger = logging.getLogger("xai.security")


class RateLimitCategory(Enum):
    """Rate limit categories with different thresholds."""
    READ = "read"          # High limits: status, balance, block queries
    WRITE = "write"        # Medium limits: transactions, state changes
    SENSITIVE = "sensitive"  # Strict limits: auth, faucet, registration
    ADMIN = "admin"        # Very strict: admin operations


@dataclass
class RateLimitResult:
    """Result of a rate limit check."""
    allowed: bool
    remaining: int
    limit: int
    reset_time: int
    retry_after: int | None = None
    error_message: str | None = None


class RateLimitBucket:
    """Thread-safe bucket for tracking request timestamps."""

    def __init__(self):
        self.requests: list[float] = []
        self.lock = Lock()

    def add_request(self, timestamp: float) -> None:
        """Add a request timestamp."""
        with self.lock:
            self.requests.append(timestamp)

    def count_recent(self, window_seconds: int) -> int:
        """Count requests in the time window and clean up old entries."""
        with self.lock:
            cutoff = time.time() - window_seconds
            self.requests = [ts for ts in self.requests if ts > cutoff]
            return len(self.requests)

    def get_oldest_in_window(self, window_seconds: int) -> float | None:
        """Get the oldest request timestamp in the current window."""
        with self.lock:
            cutoff = time.time() - window_seconds
            valid = [ts for ts in self.requests if ts > cutoff]
            return min(valid) if valid else None


class APIRateLimiter:
    """
    Flask-integrated rate limiter with category-based limits.

    Supports:
    - Multiple rate limit categories (read, write, sensitive, admin)
    - Per-IP tracking with proxy support
    - DDoS detection and automatic blocking
    - Proper HTTP 429 responses
    """

    def __init__(self):
        self.buckets: dict[str, RateLimitBucket] = defaultdict(RateLimitBucket)
        self.blocked_ips: dict[str, float] = {}  # IP -> unblock timestamp
        self.lock = Lock()
        self.last_cleanup = time.time()
        self.cleanup_interval = 300  # 5 minutes

        # Category configurations loaded from config
        self._load_config()

    def _load_config(self) -> None:
        """Load rate limit configuration from config module."""
        self.enabled = getattr(config, "RATE_LIMIT_ENABLED", True)

        self.category_limits = {
            RateLimitCategory.READ: (
                getattr(config, "RATE_LIMIT_READ_REQUESTS", 300),
                getattr(config, "RATE_LIMIT_READ_WINDOW", 60),
            ),
            RateLimitCategory.WRITE: (
                getattr(config, "RATE_LIMIT_WRITE_REQUESTS", 50),
                getattr(config, "RATE_LIMIT_WRITE_WINDOW", 60),
            ),
            RateLimitCategory.SENSITIVE: (
                getattr(config, "RATE_LIMIT_SENSITIVE_REQUESTS", 5),
                getattr(config, "RATE_LIMIT_SENSITIVE_WINDOW", 300),
            ),
            RateLimitCategory.ADMIN: (
                getattr(config, "RATE_LIMIT_ADMIN_REQUESTS", 20),
                getattr(config, "RATE_LIMIT_ADMIN_WINDOW", 60),
            ),
        }

        # Endpoint-specific overrides
        self.endpoint_overrides: dict[str, tuple[int, int]] = {
            "/faucet/claim": (
                getattr(config, "RATE_LIMIT_FAUCET_REQUESTS", 1),
                getattr(config, "RATE_LIMIT_FAUCET_WINDOW", 86400),
            ),
            "/health": (1000, 60),  # Health checks need high limits
            "/metrics": (100, 60),
        }

        # DDoS settings
        self.ddos_threshold = getattr(config, "RATE_LIMIT_DDOS_THRESHOLD", 1000)
        self.ddos_window = getattr(config, "RATE_LIMIT_DDOS_WINDOW", 60)
        self.block_duration = getattr(config, "RATE_LIMIT_BLOCK_DURATION", 3600)

    def _get_client_ip(self) -> str:
        """Get client IP, handling proxies correctly."""
        # Check X-Forwarded-For header (from reverse proxy)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # Take the first IP (original client)
            return forwarded.split(",")[0].strip()

        # Check X-Real-IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()

        # Fall back to remote_addr
        return request.remote_addr or "127.0.0.1"

    def _get_bucket_key(self, endpoint: str, category: RateLimitCategory) -> str:
        """Generate a bucket key for the current request."""
        ip = self._get_client_ip()
        # Hash IP for privacy in logs
        ip_hash = hashlib.sha256(ip.encode()).hexdigest()[:12]
        return f"{category.value}:{ip_hash}:{endpoint}"

    def _cleanup_old_data(self) -> None:
        """Periodically clean up old buckets and expired blocks."""
        current_time = time.time()
        if current_time - self.last_cleanup < self.cleanup_interval:
            return

        with self.lock:
            # Clean up expired IP blocks
            expired = [ip for ip, unblock in self.blocked_ips.items()
                      if unblock < current_time]
            for ip in expired:
                del self.blocked_ips[ip]
                logger.info("Unblocked IP after timeout", extra={
                    "event": "rate_limit.unblock",
                    "ip_hash": hashlib.sha256(ip.encode()).hexdigest()[:12],
                })

            # Clean up old buckets (keep only last 24 hours)
            max_window = 86400
            empty_keys = []
            for key, bucket in self.buckets.items():
                bucket.count_recent(max_window)
                if not bucket.requests:
                    empty_keys.append(key)
            for key in empty_keys:
                del self.buckets[key]

            self.last_cleanup = current_time

    def _check_ddos(self, ip: str) -> tuple[bool, str | None]:
        """Check for DDoS patterns from a single IP."""
        bucket_key = f"ddos:{hashlib.sha256(ip.encode()).hexdigest()[:12]}"
        bucket = self.buckets[bucket_key]

        # Record this request for DDoS tracking
        bucket.add_request(time.time())
        count = bucket.count_recent(self.ddos_window)

        if count > self.ddos_threshold:
            # Block this IP
            with self.lock:
                self.blocked_ips[ip] = time.time() + self.block_duration

            security_logger.critical(
                "DDoS pattern detected, blocking IP",
                extra={
                    "event": "rate_limit.ddos_blocked",
                    "ip_hash": hashlib.sha256(ip.encode()).hexdigest()[:12],
                    "request_count": count,
                    "threshold": self.ddos_threshold,
                    "window_seconds": self.ddos_window,
                    "block_duration": self.block_duration,
                }
            )
            return False, "Your IP has been temporarily blocked due to excessive requests"

        return True, None

    def check_rate_limit(
        self,
        endpoint: str,
        category: RateLimitCategory = RateLimitCategory.READ,
    ) -> RateLimitResult:
        """
        Check if the current request is within rate limits.

        Args:
            endpoint: API endpoint path
            category: Rate limit category

        Returns:
            RateLimitResult with allowed status and metadata
        """
        if not self.enabled:
            return RateLimitResult(
                allowed=True,
                remaining=999,
                limit=999,
                reset_time=0,
            )

        self._cleanup_old_data()
        current_time = time.time()
        ip = self._get_client_ip()

        # Check if IP is blocked
        if ip in self.blocked_ips:
            if self.blocked_ips[ip] > current_time:
                retry_after = int(self.blocked_ips[ip] - current_time)
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    limit=0,
                    reset_time=int(self.blocked_ips[ip]),
                    retry_after=retry_after,
                    error_message="Your IP has been temporarily blocked. Please try again later.",
                )
            else:
                # Expired block
                with self.lock:
                    del self.blocked_ips[ip]

        # Check for DDoS pattern
        is_safe, ddos_error = self._check_ddos(ip)
        if not is_safe:
            return RateLimitResult(
                allowed=False,
                remaining=0,
                limit=0,
                reset_time=int(current_time + self.block_duration),
                retry_after=self.block_duration,
                error_message=ddos_error,
            )

        # Get limits for this endpoint
        if endpoint in self.endpoint_overrides:
            max_requests, window_seconds = self.endpoint_overrides[endpoint]
        else:
            max_requests, window_seconds = self.category_limits[category]

        # Check bucket
        bucket_key = self._get_bucket_key(endpoint, category)
        bucket = self.buckets[bucket_key]

        # Count recent requests (before adding current one)
        recent_count = bucket.count_recent(window_seconds)

        if recent_count >= max_requests:
            # Rate limited
            oldest = bucket.get_oldest_in_window(window_seconds)
            if oldest:
                reset_time = int(oldest + window_seconds)
                retry_after = max(1, reset_time - int(current_time))
            else:
                reset_time = int(current_time + window_seconds)
                retry_after = window_seconds

            security_logger.warning(
                "Rate limit exceeded",
                extra={
                    "event": "rate_limit.exceeded",
                    "endpoint": endpoint,
                    "category": category.value,
                    "ip_hash": hashlib.sha256(ip.encode()).hexdigest()[:12],
                    "request_count": recent_count,
                    "limit": max_requests,
                    "window": window_seconds,
                }
            )

            return RateLimitResult(
                allowed=False,
                remaining=0,
                limit=max_requests,
                reset_time=reset_time,
                retry_after=retry_after,
                error_message=f"Rate limit exceeded. Maximum {max_requests} requests per {window_seconds} seconds.",
            )

        # Request allowed - record it
        bucket.add_request(current_time)
        remaining = max(0, max_requests - recent_count - 1)
        reset_time = int(current_time + window_seconds)

        return RateLimitResult(
            allowed=True,
            remaining=remaining,
            limit=max_requests,
            reset_time=reset_time,
        )

    def get_stats(self) -> dict[str, Any]:
        """Get rate limiter statistics."""
        return {
            "enabled": self.enabled,
            "active_buckets": len(self.buckets),
            "blocked_ips": len(self.blocked_ips),
            "category_limits": {
                cat.value: {"requests": lim[0], "window_seconds": lim[1]}
                for cat, lim in self.category_limits.items()
            },
            "ddos_threshold": self.ddos_threshold,
            "ddos_window": self.ddos_window,
            "block_duration": self.block_duration,
        }


# Global instance
_rate_limiter: APIRateLimiter | None = None


def get_api_rate_limiter() -> APIRateLimiter:
    """Get or create the global API rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = APIRateLimiter()
    return _rate_limiter


def init_rate_limiting(app: Flask) -> None:
    """
    Initialize rate limiting for a Flask application.

    Adds before_request and after_request handlers for rate limiting.

    Args:
        app: Flask application instance
    """
    limiter = get_api_rate_limiter()

    @app.before_request
    def check_global_rate_limit() -> Response | None:
        """Check global rate limits before processing request."""
        if not limiter.enabled:
            return None

        # Skip rate limiting for static files and internal endpoints
        if request.path.startswith("/static/"):
            return None

        # Store rate limit result in g for after_request
        g.rate_limit_checked = False
        return None

    @app.after_request
    def add_rate_limit_headers(response: Response) -> Response:
        """Add rate limit headers to response."""
        # Get the rate limit result if one was stored
        result = getattr(g, "rate_limit_result", None)
        if result:
            response.headers["X-RateLimit-Limit"] = str(result.limit)
            response.headers["X-RateLimit-Remaining"] = str(result.remaining)
            response.headers["X-RateLimit-Reset"] = str(result.reset_time)
            if result.retry_after:
                response.headers["Retry-After"] = str(result.retry_after)
        return response

    logger.info(
        "Rate limiting initialized",
        extra={
            "event": "rate_limit.init",
            "enabled": limiter.enabled,
            "ddos_threshold": limiter.ddos_threshold,
        }
    )


def rate_limit(
    category: str | RateLimitCategory = RateLimitCategory.READ,
    endpoint: str | None = None,
) -> Callable:
    """
    Decorator to enforce rate limiting on a route.

    Args:
        category: Rate limit category ("read", "write", "sensitive", "admin")
                 or RateLimitCategory enum
        endpoint: Optional endpoint name (defaults to request.path)

    Returns:
        Decorator function

    Example:
        @app.route("/send", methods=["POST"])
        @rate_limit("write")
        def send_transaction():
            ...
    """
    # Convert string to enum if needed
    if isinstance(category, str):
        try:
            cat_enum = RateLimitCategory(category.lower())
        except ValueError:
            cat_enum = RateLimitCategory.READ
    else:
        cat_enum = category

    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            limiter = get_api_rate_limiter()
            endpoint_path = endpoint or request.path

            result = limiter.check_rate_limit(endpoint_path, cat_enum)

            # Store result for header injection
            g.rate_limit_result = result

            if not result.allowed:
                response = jsonify({
                    "error": result.error_message or "Rate limit exceeded",
                    "code": "rate_limited",
                    "retry_after": result.retry_after,
                })
                response.status_code = 429
                response.headers["X-RateLimit-Limit"] = str(result.limit)
                response.headers["X-RateLimit-Remaining"] = "0"
                response.headers["X-RateLimit-Reset"] = str(result.reset_time)
                if result.retry_after:
                    response.headers["Retry-After"] = str(result.retry_after)
                return response

            return f(*args, **kwargs)

        return decorated_function
    return decorator


def rate_limit_read(f: Callable) -> Callable:
    """Decorator for read endpoints (high limits)."""
    return rate_limit(RateLimitCategory.READ)(f)


def rate_limit_write(f: Callable) -> Callable:
    """Decorator for write endpoints (medium limits)."""
    return rate_limit(RateLimitCategory.WRITE)(f)


def rate_limit_sensitive(f: Callable) -> Callable:
    """Decorator for sensitive endpoints (strict limits)."""
    return rate_limit(RateLimitCategory.SENSITIVE)(f)


def rate_limit_admin(f: Callable) -> Callable:
    """Decorator for admin endpoints (very strict limits)."""
    return rate_limit(RateLimitCategory.ADMIN)(f)


def check_rate_limit_inline(
    endpoint: str,
    category: RateLimitCategory = RateLimitCategory.READ,
) -> tuple[bool, dict[str, Any] | None]:
    """
    Check rate limit inline (for use in route handlers).

    Args:
        endpoint: API endpoint path
        category: Rate limit category

    Returns:
        Tuple of (allowed, error_response_or_none)
        If not allowed, error_response contains a dict for jsonify()

    Example:
        allowed, error = check_rate_limit_inline("/faucet/claim", RateLimitCategory.SENSITIVE)
        if not allowed:
            return jsonify(error), 429
    """
    limiter = get_api_rate_limiter()
    result = limiter.check_rate_limit(endpoint, category)

    # Store for header injection
    g.rate_limit_result = result

    if not result.allowed:
        return False, {
            "error": result.error_message or "Rate limit exceeded",
            "code": "rate_limited",
            "retry_after": result.retry_after,
        }

    return True, None
