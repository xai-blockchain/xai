from __future__ import annotations

"""
XAI Blockchain - Anonymous Rate Limiting

Rate limiting using cryptographic hashing for privacy.
"""

import hashlib
import time
from collections import defaultdict
from datetime import datetime, timezone

class AnonymousRateLimiter:
    """
    Privacy-focused rate limiter using hashed tokens.
    """

    def __init__(self):
        # Request counts: {hashed_token: [(timestamp, endpoint), ...]}
        self.request_log = defaultdict(list)

        # Rate limits: {endpoint: (max_requests, time_window_seconds)}
        self.limits = {
            "/faucet/claim": (10, 86400),  # 10 per day
            "/mine": (100, 3600),  # 100 per hour
            "/send": (100, 3600),  # 100 per hour
            "/balance": (1000, 3600),  # 1000 per hour
            "/claim-wallet": (5, 86400),  # 5 per day
            "/admin/withdrawals/telemetry": (30, 60),  # 30 per minute
            "default": (200, 3600),  # 200 per hour for unlisted endpoints
        }

        # Cleanup old entries every 5 minutes
        self.last_cleanup = time.time()
        self.cleanup_interval = 300  # 5 minutes

    def _get_anonymous_token(self, request_data: str, salt: str = "XAI_ANON") -> str:
        """
        Generate anonymous tracking token

        Uses SHA256 hash of request data + salt.
        This allows rate limiting without storing identifying information.

        Args:
            request_data: Request identifier (could be anything)
            salt: Salt for hashing

        Returns:
            str: Anonymous hash token
        """
        # Hash the request data with salt
        data = f"{request_data}:{salt}".encode("utf-8")
        token = hashlib.sha256(data).hexdigest()[:16]  # Use first 16 chars
        return token

    def _cleanup_old_requests(self):
        """
        Remove expired request records

        This prevents memory growth and protects privacy
        by not keeping old data.
        """
        current_time = time.time()

        # Only cleanup periodically
        if current_time - self.last_cleanup < self.cleanup_interval:
            return

        # Remove requests older than 24 hours
        cutoff_time = current_time - 86400

        for token in list(self.request_log.keys()):
            # Filter out old requests
            self.request_log[token] = [
                (ts, endpoint) for ts, endpoint in self.request_log[token] if ts > cutoff_time
            ]

            # Remove empty entries
            if not self.request_log[token]:
                del self.request_log[token]

        self.last_cleanup = current_time

    def check_rate_limit(
        self, request_identifier: str, endpoint: str
    ) -> tuple[bool, str | None]:
        """
        Check if request is within rate limits

        Args:
            request_identifier: Anonymous identifier for this requester
            endpoint: API endpoint being accessed

        Returns:
            tuple[bool, str | None]: (allowed, error_message)
                - allowed: True if request is allowed
                - error_message: Error message if denied, None if allowed
        """
        # Cleanup old data periodically
        self._cleanup_old_requests()

        # Get anonymous token
        token = self._get_anonymous_token(request_identifier)

        # Get rate limit for this endpoint
        if endpoint in self.limits:
            max_requests, time_window = self.limits[endpoint]
        else:
            max_requests, time_window = self.limits["default"]

        # Get current time
        current_time = time.time()
        window_start = current_time - time_window

        # Count requests in time window
        recent_requests = [
            ts for ts, ep in self.request_log[token] if ts > window_start and ep == endpoint
        ]

        # Check if limit exceeded
        if len(recent_requests) >= max_requests:
            # Calculate when limit resets
            oldest_request = min(recent_requests)
            reset_time = oldest_request + time_window
            wait_seconds = int(reset_time - current_time)

            error_msg = f"Rate limit exceeded. Try again in {wait_seconds} seconds."
            return False, error_msg

        # Record this request
        self.request_log[token].append((current_time, endpoint))

        return True, None

    def get_remaining_requests(self, request_identifier: str, endpoint: str) -> int:
        """
        Get number of remaining requests in current window

        Args:
            request_identifier: Anonymous identifier
            endpoint: API endpoint

        Returns:
            int: Number of requests remaining
        """
        token = self._get_anonymous_token(request_identifier)

        # Get rate limit
        if endpoint in self.limits:
            max_requests, time_window = self.limits[endpoint]
        else:
            max_requests, time_window = self.limits["default"]

        # Count recent requests
        current_time = time.time()
        window_start = current_time - time_window

        recent_requests = [
            ts for ts, ep in self.request_log[token] if ts > window_start and ep == endpoint
        ]

        remaining = max_requests - len(recent_requests)
        return max(0, remaining)

    def set_custom_limit(self, endpoint: str, max_requests: int, time_window: int):
        """
        Set custom rate limit for an endpoint

        Args:
            endpoint: Endpoint path
            max_requests: Maximum number of requests
            time_window: Time window in seconds
        """
        self.limits[endpoint] = (max_requests, time_window)

    def get_stats(self) -> dict:
        """
        Get anonymous rate limiting statistics

        Returns:
            dict: Anonymous statistics (no personal data!)
        """
        # Count active tokens (not actual users, just active rate limit buckets)
        active_tokens = len(self.request_log)

        # Total requests tracked
        total_requests = sum(len(requests) for requests in self.request_log.values())

        return {
            "active_rate_limit_tokens": active_tokens,
            "total_tracked_requests": total_requests,
            "configured_limits": {
                endpoint: f"{max_req} per {window}s"
                for endpoint, (max_req, window) in self.limits.items()
            },
            "note": "All tracking is anonymous via hashed tokens",
        }

# Global rate limiter instance
_global_rate_limiter = None

def get_rate_limiter() -> AnonymousRateLimiter:
    """
    Get global rate limiter instance

    Returns:
        AnonymousRateLimiter: Global rate limiter
    """
    global _global_rate_limiter
    if _global_rate_limiter is None:
        _global_rate_limiter = AnonymousRateLimiter()
    return _global_rate_limiter

def check_rate_limit(request_identifier: str, endpoint: str) -> tuple[bool, str | None]:
    """
    Convenience function to check rate limit

    Args:
        request_identifier: Anonymous identifier
        endpoint: Endpoint being accessed

    Returns:
        tuple[bool, str | None]: (allowed, error_message)
    """
    limiter = get_rate_limiter()
    return limiter.check_rate_limit(request_identifier, endpoint)
