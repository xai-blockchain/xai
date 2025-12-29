from __future__ import annotations

"""
XAI Blockchain - Advanced Rate Limiter

Sophisticated rate limiting implementation with:
- Per-IP rate limiting
- Per-user rate limiting (for authenticated requests)
- Endpoint-specific limits
- Sliding window algorithm
- DDoS detection
- Graceful degradation under load
- Distributed rate limiting support (Redis-ready)
"""

import hashlib
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from functools import wraps
from threading import Lock
from typing import Callable

from flask import Response, jsonify, request

security_logger = logging.getLogger('xai.security')

class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded"""
    pass

class LimitSeverity(Enum):
    """Severity levels for rate limit violations"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

@dataclass
class RateLimitConfig:
    """Configuration for a rate limit"""
    max_requests: int
    window_seconds: int
    per_ip: bool = False
    per_user: bool = False
    description: str = ""

    def __str__(self):
        return f"{self.max_requests} requests per {self.window_seconds}s"

@dataclass
class RateLimitEntry:
    """Entry in the rate limit log"""
    timestamp: float
    endpoint: str
    identifier: str = ""
    ip_address: str = ""

@dataclass
class RateLimitStats:
    """Statistics for rate limiting"""
    total_requests: int = 0
    rejected_requests: int = 0
    current_violations: int = 0
    peak_requests_per_second: float = 0.0
    last_violation: datetime | None = None
    violations_by_ip: dict[str, int] = field(default_factory=dict)
    violations_by_endpoint: dict[str, int] = field(default_factory=dict)

class RateLimitBucket:
    """Thread-safe bucket for tracking request timestamps"""

    def __init__(self):
        self.requests: list[float] = []
        self.lock = Lock()

    def add_request(self, timestamp: float) -> None:
        """Add a request timestamp"""
        with self.lock:
            self.requests.append(timestamp)

    def get_recent_requests(self, window_seconds: int) -> int:
        """Get count of requests in the recent time window"""
        with self.lock:
            cutoff = time.time() - window_seconds
            count = sum(1 for ts in self.requests if ts > cutoff)
            # Clean up old entries
            self.requests = [ts for ts in self.requests if ts > cutoff]
            return count

    def cleanup(self, window_seconds: int) -> None:
        """Remove old entries outside the window"""
        with self.lock:
            cutoff = time.time() - window_seconds
            self.requests = [ts for ts in self.requests if ts > cutoff]

class AdvancedRateLimiter:
    """
    Advanced rate limiter with multiple strategies and DDoS detection.

    Supports:
    - Sliding window rate limiting
    - Per-IP rate limiting
    - Per-user rate limiting
    - Endpoint-specific limits
    - DDoS pattern detection
    - Graceful degradation
    """

    def __init__(self):
        """Initialize the advanced rate limiter"""
        # Bucket storage: {identifier: RateLimitBucket}
        self.buckets: dict[str, RateLimitBucket] = defaultdict(RateLimitBucket)
        self.lock = Lock()

        # TASK 63: Configuration for endpoints with read/write differentiation
        self.endpoint_configs: dict[str, RateLimitConfig] = {
            # Default limits - differentiated by method
            "default": RateLimitConfig(200, 60, per_ip=True),
            "default_read": RateLimitConfig(300, 60, per_ip=True),  # Higher for reads
            "default_write": RateLimitConfig(50, 60, per_ip=True),  # Lower for writes

            # READ endpoints - Higher limits (300-500 req/min)
            "/blocks": RateLimitConfig(500, 60, per_ip=True, description="Block query"),
            "/block/*": RateLimitConfig(500, 60, per_ip=True, description="Specific block"),
            "/transactions": RateLimitConfig(500, 60, per_ip=True, description="Transaction list"),
            "/transaction/*": RateLimitConfig(400, 60, per_ip=True, description="Transaction query"),
            "/balance/*": RateLimitConfig(300, 60, per_ip=True, description="Balance query"),
            "/history/*": RateLimitConfig(200, 60, per_ip=True, description="History query"),
            "/stats": RateLimitConfig(200, 60, per_ip=True, description="Stats query"),
            "/peers": RateLimitConfig(100, 60, per_ip=True, description="Peer list"),
            "/health": RateLimitConfig(1000, 60, per_ip=True, description="Health check"),
            "/metrics": RateLimitConfig(100, 60, per_ip=True, description="Metrics"),

            # WRITE endpoints - Lower limits (10-50 req/min)
            "/send": RateLimitConfig(50, 60, per_user=True, description="Send transaction"),
            "/mine": RateLimitConfig(10, 60, per_user=True, description="Mine block"),
            "/transaction/receive": RateLimitConfig(100, 60, per_ip=True, description="Peer transaction"),
            "/block/receive": RateLimitConfig(50, 60, per_ip=True, description="Peer block"),

            # Sensitive endpoints - Very strict limits (3-10 req/min)
            "/api/login": RateLimitConfig(5, 300, per_ip=True, description="Login attempt"),
            "/api/register": RateLimitConfig(3, 3600, per_ip=True, description="Registration"),
            "/api/password-reset": RateLimitConfig(3, 3600, per_ip=True, description="Password reset"),
            "/faucet/claim": RateLimitConfig(1, 86400, per_ip=True, description="Faucet claim"),

            # Wallet operations - Medium limits (20-50 req/min)
            "/wallet/send": RateLimitConfig(50, 60, per_user=True, description="Wallet send"),
            "/wallet/create": RateLimitConfig(5, 3600, per_ip=True, description="Wallet creation"),

            # Mining operations - High limits for submission (100-1000 req/min)
            "/mining/start": RateLimitConfig(10, 60, per_user=True, description="Start mining"),
            "/mining/stop": RateLimitConfig(10, 60, per_user=True, description="Stop mining"),
            "/mining/submit": RateLimitConfig(1000, 60, per_user=True, description="Submit work"),
            "/auto-mine/start": RateLimitConfig(5, 60, per_user=True, description="Auto-mine start"),
            "/auto-mine/stop": RateLimitConfig(5, 60, per_user=True, description="Auto-mine stop"),

            # Admin/governance - Restricted (5-20 req/min)
            "/governance/vote": RateLimitConfig(20, 60, per_user=True, description="Governance vote"),
            "/admin/*": RateLimitConfig(10, 60, per_user=True, description="Admin operations"),
            "/sync": RateLimitConfig(10, 60, per_ip=True, description="Blockchain sync"),

            # WebSocket - Connection limits
            "/ws": RateLimitConfig(5, 60, per_ip=True, description="WebSocket connection"),

            # Exchange operations - Medium limits
            "/exchange/orders": RateLimitConfig(200, 60, per_ip=True, description="Order book"),
            "/exchange/place-order": RateLimitConfig(50, 60, per_user=True, description="Place order"),
            "/exchange/cancel-order": RateLimitConfig(100, 60, per_user=True, description="Cancel order"),
            "/exchange/deposit": RateLimitConfig(20, 60, per_user=True, description="Deposit"),
            "/exchange/withdraw": RateLimitConfig(10, 60, per_user=True, description="Withdraw"),

            # Gamification endpoints - Medium limits
            "/treasure/claim": RateLimitConfig(10, 60, per_user=True, description="Treasure claim"),
            "/treasure/create": RateLimitConfig(20, 60, per_user=True, description="Treasure create"),
        }

        # Statistics tracking
        self.stats = RateLimitStats()

        # DDoS detection threshold
        self.ddos_threshold = 1000  # requests per minute from single IP
        self.ddos_window = 60

        # Blocked IPs due to DDoS
        self.blocked_ips: dict[str, float] = {}  # {ip: unblock_timestamp}
        self.block_duration = 3600  # 1 hour block

        # Cleanup task (periodic cleanup of old buckets)
        self.last_cleanup = time.time()
        self.cleanup_interval = 300  # 5 minutes

    def _get_identifier(self, endpoint: str) -> tuple[str, str]:
        """
        Get the identifier for rate limiting.

        Args:
            endpoint: API endpoint

        Returns:
            tuple[str, str]: (primary_id, secondary_id) for per_ip and per_user
        """
        # Get IP address (handle proxies)
        ip = request.headers.get('X-Forwarded-For')
        if ip:
            ip = ip.split(',')[0].strip()
        else:
            ip = request.remote_addr or '127.0.0.1'

        # Get user identifier if authenticated
        user_id = request.headers.get('X-User-ID') or request.headers.get('Authorization', '')
        if user_id:
            # Hash the user ID for privacy
            user_id = hashlib.sha256(user_id.encode()).hexdigest()[:16]
        else:
            user_id = None

        return ip, user_id

    def _check_ddos_pattern(self, ip: str) -> tuple[bool, str | None]:
        """
        Detect DDoS patterns from a single IP.

        Args:
            ip: IP address to check

        Returns:
            tuple[bool, str | None]: (is_safe, error_message)
        """
        bucket_key = f"ddos:{ip}"
        bucket = self.buckets[bucket_key]
        recent_count = bucket.get_recent_requests(self.ddos_window)

        if recent_count > self.ddos_threshold:
            # IP is attacking, block it
            self.blocked_ips[ip] = time.time() + self.block_duration
            error = f"IP has been temporarily blocked due to excessive requests"
            security_logger.critical(f"DDoS pattern detected from {ip}: {recent_count} requests in {self.ddos_window}s")
            self.stats.violations_by_ip[ip] = self.stats.violations_by_ip.get(ip, 0) + 1
            return False, error

        return True, None

    def _cleanup_old_buckets(self) -> None:
        """Periodically clean up old buckets"""
        current_time = time.time()
        if current_time - self.last_cleanup < self.cleanup_interval:
            return

        with self.lock:
            # Clean up old buckets
            max_window = max(config.window_seconds for config in self.endpoint_configs.values())
            for key in list(self.buckets.keys()):
                self.buckets[key].cleanup(max_window)
                if not self.buckets[key].requests:
                    del self.buckets[key]

            # Clean up expired IP blocks
            expired_blocks = [ip for ip, unblock_time in self.blocked_ips.items() if unblock_time < current_time]
            for ip in expired_blocks:
                del self.blocked_ips[ip]

            self.last_cleanup = current_time

    def check_rate_limit(self, endpoint: str) -> tuple[bool, str | None]:
        """
        Check if request is allowed under rate limit.

        Args:
            endpoint: API endpoint

        Returns:
            tuple[bool, str | None]: (allowed, error_message)
        """
        # Perform periodic cleanup
        self._cleanup_old_buckets()

        # Get identifiers
        ip, user_id = self._get_identifier(endpoint)

        # Check if IP is blocked
        if ip in self.blocked_ips:
            if self.blocked_ips[ip] > time.time():
                error = "Your IP has been temporarily blocked. Please try again later."
                security_logger.warning(f"Blocked IP attempted access: {ip}")
                return False, error
            else:
                # Unblock expired IPs
                del self.blocked_ips[ip]

        # Check DDoS pattern
        is_safe, error = self._check_ddos_pattern(ip)
        if not is_safe:
            return False, error

        # Get configuration for endpoint
        config = self.endpoint_configs.get(endpoint, self.endpoint_configs["default"])

        current_time = time.time()
        bucket_key = ""
        primary_id = ""

        # Check per-user limit
        if config.per_user and user_id:
            primary_id = user_id
            bucket_key = f"user:{user_id}:{endpoint}"
        # Check per-IP limit
        elif config.per_ip:
            primary_id = ip
            bucket_key = f"ip:{ip}:{endpoint}"
        # Fallback to default
        else:
            primary_id = ip
            bucket_key = f"default:{endpoint}"

        # Get bucket and check limit
        bucket = self.buckets[bucket_key]
        recent_count = bucket.get_recent_requests(config.window_seconds)

        # Add current request
        bucket.add_request(current_time)

        # Check if limit exceeded
        if recent_count >= config.max_requests:
            # Calculate reset time
            oldest_request = min(bucket.requests) if bucket.requests else current_time
            reset_time = oldest_request + config.window_seconds
            wait_seconds = int(max(1, reset_time - current_time))

            error = f"Rate limit exceeded for {endpoint}. Retry after {wait_seconds} seconds."
            security_logger.warning(f"Rate limit exceeded: {bucket_key} ({recent_count}/{config.max_requests})")

            self.stats.rejected_requests += 1
            self.stats.current_violations += 1

            # Track violation
            if config.per_ip:
                self.stats.violations_by_ip[ip] = self.stats.violations_by_ip.get(ip, 0) + 1
            self.stats.violations_by_endpoint[endpoint] = self.stats.violations_by_endpoint.get(endpoint, 0) + 1
            self.stats.last_violation = datetime.now(timezone.utc)

            return False, error

        # Request allowed
        self.stats.total_requests += 1
        return True, None

    def get_remaining_requests(self, endpoint: str) -> int:
        """
        Get remaining requests for current user/IP.

        Args:
            endpoint: API endpoint

        Returns:
            int: Remaining requests in current window
        """
        ip, user_id = self._get_identifier(endpoint)
        config = self.endpoint_configs.get(endpoint, self.endpoint_configs["default"])

        bucket_key = ""
        if config.per_user and user_id:
            bucket_key = f"user:{user_id}:{endpoint}"
        elif config.per_ip:
            bucket_key = f"ip:{ip}:{endpoint}"
        else:
            bucket_key = f"default:{endpoint}"

        bucket = self.buckets[bucket_key]
        recent_count = bucket.get_recent_requests(config.window_seconds)

        return max(0, config.max_requests - recent_count)

    def set_endpoint_limit(self, endpoint: str, config: RateLimitConfig) -> None:
        """
        Set rate limit for specific endpoint.

        Args:
            endpoint: API endpoint path
            config: RateLimitConfig instance
        """
        self.endpoint_configs[endpoint] = config
        security_logger.info(f"Rate limit set for {endpoint}: {config}")

    def get_stats(self) -> Dict:
        """
        Get rate limiter statistics.

        Returns:
            Dict: Statistics dictionary
        """
        return {
            'total_requests': self.stats.total_requests,
            'rejected_requests': self.stats.rejected_requests,
            'current_violations': self.stats.current_violations,
            'last_violation': self.stats.last_violation.isoformat() if self.stats.last_violation else None,
            'blocked_ips_count': len(self.blocked_ips),
            'top_violations_by_ip': dict(sorted(self.stats.violations_by_ip.items(), key=lambda x: x[1], reverse=True)[:10]),
            'top_violations_by_endpoint': dict(sorted(self.stats.violations_by_endpoint.items(), key=lambda x: x[1], reverse=True)[:10]),
        }

    def is_ip_blocked(self, ip: str) -> bool:
        """Check if IP is currently blocked"""
        if ip in self.blocked_ips and self.blocked_ips[ip] > time.time():
            return True
        return False

# Global instance
_global_rate_limiter = None

def get_rate_limiter() -> AdvancedRateLimiter:
    """Get global rate limiter instance"""
    global _global_rate_limiter
    if _global_rate_limiter is None:
        _global_rate_limiter = AdvancedRateLimiter()
    return _global_rate_limiter

def rate_limit(endpoint: str = None) -> Callable:
    """
    Decorator to enforce rate limiting on a route.

    Args:
        endpoint: Optional endpoint name (defaults to request.path)

    Returns:
        Callable: Decorator function
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            limiter = get_rate_limiter()
            endpoint_path = endpoint or request.path

            allowed, error = limiter.check_rate_limit(endpoint_path)
            if not allowed:
                return jsonify({'error': error}), 429  # Too Many Requests

            # Add rate limit info to response headers
            remaining = limiter.get_remaining_requests(endpoint_path)
            response = f(*args, **kwargs)

            # Handle both tuple and direct responses
            if isinstance(response, tuple):
                resp_data, status_code = response[0], response[1] if len(response) > 1 else 200
                if isinstance(resp_data, Response):
                    response_obj = resp_data
                else:
                    # Convert to response
                    return response
            else:
                response_obj = response

            if isinstance(response_obj, Response):
                response_obj.headers['X-RateLimit-Remaining'] = str(remaining)

            return response

        return decorated_function

    return decorator
