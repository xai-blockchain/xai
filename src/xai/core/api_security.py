"""
API security helpers for rate limiting and validated payloads across all HTTP endpoints.
"""

from collections import defaultdict
from time import time
from typing import Dict

from flask import request
from xai.core.security_validation import ValidationError, validate_api_request

from xai.core.config import Config


class RateLimitExceeded(ValidationError):
    """Raise when a client exceeds the configured rate limits."""

    pass


class SimpleRateLimiter:
    """Basic sliding-window rate limiter keyed by IP/identifier."""

    def __init__(self, max_requests: int = 120, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.calls: Dict[str, list[float]] = defaultdict(list)

    def allow(self, key: str) -> bool:
        now = time()
        window_start = now - self.window_seconds
        timestamps = self.calls[key]
        # keep only recent entries
        self.calls[key] = [ts for ts in timestamps if ts > window_start]
        if len(self.calls[key]) >= self.max_requests:
            return False
        self.calls[key].append(now)
        return True


class APISecurityManager:
    """Wraps rate limiting and request validation for Flask apps."""

    def __init__(self):
        self.rate_limiter = SimpleRateLimiter(Config.API_RATE_LIMIT, Config.API_RATE_WINDOW_SECONDS)
        self.max_json_bytes = Config.API_MAX_JSON_BYTES

    def enforce_request(self):
        """Run validations before each request."""
        client_ip = request.headers.get("X-Forwarded-For") or request.remote_addr or "127.0.0.1"
        client_ip = client_ip.split(",")[0].strip()

        if not self.rate_limiter.allow(client_ip):
            raise RateLimitExceeded("Rate limit exceeded; slow down and try again")

        payload_length = request.content_length or 0
        if payload_length > self.max_json_bytes:
            raise ValidationError(f"Request too large (maximum {self.max_json_bytes} bytes)")

        data = request.get_json(silent=True)
        if data is not None:
            validate_api_request(data, max_size=self.max_json_bytes)
