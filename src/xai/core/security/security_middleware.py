"""
XAI Web Wallet Security Middleware

Comprehensive security middleware for Flask applications providing:
- Rate limiting by IP and endpoint
- CSRF token protection
- CORS configuration with whitelist
- Security headers (CSP, X-Frame-Options, etc.)
- Request validation and input sanitization
- Session management with secure cookies
- 2FA preparation (TOTP library integration)
- Request/response logging for security events
"""

from __future__ import annotations

import hashlib
import hmac
import html
import ipaddress
import json
import logging
import re
import secrets
import threading
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Any, Callable
from urllib.parse import urlparse

from flask import Flask, Response, jsonify, request, session

# Security logger
security_logger = logging.getLogger("xai.security.middleware")
security_logger.setLevel(logging.INFO)

# Password hashing - use bcrypt for secure password verification
try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False
    security_logger.warning("bcrypt not available - using PBKDF2 fallback for password hashing")

if not security_logger.handlers:
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s - SECURITY MIDDLEWARE - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    security_logger.addHandler(handler)

class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded."""
    pass

class CSRFTokenInvalid(Exception):
    """Raised when CSRF token is invalid."""
    pass

class SecurityConfig:
    """Configuration for security middleware."""

    # Rate limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = 120
    RATE_LIMIT_WINDOW: int = 60  # seconds
    RATE_LIMIT_BURST: int = 500  # max burst requests

    # CORS
    CORS_ENABLED: bool = True
    CORS_ORIGINS: list[str] = [
        "http://localhost:12030",
        "http://localhost:12001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5000",
        "https://127.0.0.1:3443",
        "https://localhost:3443",
        "https://127.0.0.1:5443",
        "https://localhost:5443",
    ]
    CORS_METHODS: list[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_MAX_AGE: int = 3600

    # CSRF Protection
    CSRF_ENABLED: bool = True
    CSRF_TOKEN_LENGTH: int = 32
    # CSRF Exempt Endpoints - Each exemption requires security justification:
    #
    # Read-only public endpoints (no state modification, safe for GET requests):
    #   - /health: Health check endpoint, read-only status reporting
    #   - /metrics: Prometheus metrics scraping, read-only
    #   - /stats: Public statistics endpoint, read-only
    #   - /blocks: Block data queries, read-only public blockchain data
    #   - /balance: Balance queries by address, read-only public data
    #
    # Authentication-protected endpoints (alternative auth mechanisms):
    #   - /transaction: Uses cryptographic signature verification instead of CSRF
    #                   (transactions require valid private key signature)
    #   - /faucet/claim: Rate-limited by IP, testnet-only, signature-verified
    #
    # Infrastructure endpoints (P2P network operations):
    #   - /peer: P2P peer discovery, authenticated via peer ID/handshake
    #   - /block/receive: P2P block broadcast, validated via consensus rules
    #   - /transaction/receive: P2P tx broadcast, validated via signature
    #
    # Token management endpoint:
    #   - /csrf-token: Required to fetch CSRF tokens (chicken-egg problem)
    CSRF_EXEMPT_ENDPOINTS: list[str] = [
        "/health",           # Read-only: health/liveness probe
        "/metrics",          # Read-only: Prometheus metrics scraping
        "/stats",            # Read-only: public statistics
        "/blocks",           # Read-only: public blockchain data queries
        "/transaction",      # Signature-protected: requires valid crypto signature
        "/balance",          # Read-only: public balance queries
        "/peer",             # P2P-authenticated: peer handshake protocol
        "/faucet/claim",     # Rate-limited + signature: testnet faucet claims
        "/csrf-token",       # Token endpoint: necessary to obtain CSRF tokens
        "/block/receive",    # P2P consensus: validated by block hash/signature
        "/transaction/receive",  # P2P broadcast: validated by tx signature
    ]
    CSRF_EXEMPT_METHODS: list[str] = ["GET", "HEAD", "OPTIONS"]

    # Security Headers
    SECURITY_HEADERS_ENABLED: bool = True
    CONTENT_SECURITY_POLICY: str = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self'; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )

    # Session/Cookie Security
    SESSION_COOKIE_SECURE: bool = True
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SAMESITE: str = "Strict"
    SESSION_COOKIE_NAME: str = "xai_wallet_session"
    SESSION_TIMEOUT: int = 1800  # 30 minutes

    # Input Validation
    MAX_BODY_SIZE: int = 10 * 1024 * 1024  # 10MB
    MAX_HEADER_SIZE: int = 8192  # 8KB
    MAX_URL_LENGTH: int = 2048  # 2KB

    # Endpoint-specific rate limits
    ENDPOINT_LIMITS: dict[str, tuple[int, int]] = {
        "/wallet/create": (5, 3600),  # 5 requests per hour
        "/wallet/send": (20, 60),  # 20 requests per minute
        "/mine": (100, 60),  # 100 requests per minute
        "/transaction": (50, 60),  # 50 requests per minute
    }

    # 2FA Configuration
    TOTP_ENABLED: bool = True
    TOTP_WINDOW: int = 1  # Allow 1 TOTP step drift
    TOTP_PERIOD: int = 30  # 30 second TOTP period

    # Security event thresholds
    SUSPICIOUS_ACTIVITY_THRESHOLD: int = 5  # Failed attempts before blocking
    BLOCK_DURATION: int = 900  # 15 minutes
    TRUST_PROXY_HEADERS: bool = False
    TRUSTED_PROXY_IPS: list[str] = []
    TRUSTED_PROXY_NETWORKS: list[str] = []
    STRICT_SESSION_FINGERPRINTING: bool = True
    SESSION_BIND_USER_AGENT: bool = True
    SESSION_BIND_ACCEPT_LANGUAGE: bool = False

class TokenManager:
    """Manages CSRF tokens and secure session tokens."""

    def __init__(self, secret_key: str | None = None):
        """
        Initialize token manager.

        Args:
            secret_key: Secret key for HMAC operations
        """
        self.secret_key = secret_key or secrets.token_hex(32)
        self.valid_tokens: dict[str, dict[str, Any]] = {}
        self.token_expiry: dict[str, datetime] = {}

    def generate_csrf_token(self, session_id: str) -> str:
        """
        Generate a CSRF token bound to a session.

        Args:
            session_id: Session identifier

        Returns:
            CSRF token
        """
        token = secrets.token_hex(SecurityConfig.CSRF_TOKEN_LENGTH)

        # Store token with binding
        self.valid_tokens[token] = {
            "session_id": session_id,
            "created_at": datetime.now(timezone.utc),
            "used": False,
        }

        # Set expiry (24 hours)
        self.token_expiry[token] = datetime.now(timezone.utc) + timedelta(hours=24)

        return token

    def validate_csrf_token(self, token: str, session_id: str) -> bool:
        """
        Validate CSRF token.

        Args:
            token: Token to validate
            session_id: Session identifier

        Returns:
            True if valid, False otherwise
        """
        if token not in self.valid_tokens:
            return False

        token_data = self.valid_tokens[token]

        # Check session binding
        if token_data["session_id"] != session_id:
            security_logger.warning(
                f"CSRF token session mismatch: {session_id}",
                extra={"event_type": "csrf_mismatch"}
            )
            return False

        # Check expiry
        if datetime.now(timezone.utc) > self.token_expiry.get(token, datetime.now(timezone.utc)):
            return False

        return True

    def revoke_csrf_token(self, token: str) -> None:
        """
        Revoke a CSRF token.

        Args:
            token: Token to revoke
        """
        self.valid_tokens.pop(token, None)
        self.token_expiry.pop(token, None)

    def cleanup_expired_tokens(self) -> None:
        """Remove expired tokens."""
        now = datetime.now(timezone.utc)
        expired_tokens = [
            token for token, expiry in self.token_expiry.items()
            if now > expiry
        ]
        for token in expired_tokens:
            self.revoke_csrf_token(token)

class RateLimiter:
    """Advanced rate limiting with endpoint-specific rules and memory management."""

    # Memory management constants
    MAX_HISTORY_ENTRIES = 50000  # Maximum unique IP:endpoint combinations to track
    MAX_BLOCKED_IPS = 10000  # Maximum blocked IPs to track
    CLEANUP_INTERVAL = 1000  # Run cleanup every N requests
    STALE_ENTRY_AGE = 3600  # Remove entries older than 1 hour (seconds)

    def __init__(self):
        """Initialize rate limiter with memory-safe defaults."""
        self.request_history: dict[str, list[float]] = defaultdict(list)
        self.blocked_ips: dict[str, datetime] = {}
        self.failed_attempts: dict[str, int] = defaultdict(int)
        self._request_count = 0  # Counter for cleanup scheduling
        self._last_access: dict[str, float] = {}  # Track last access time for LRU eviction

    def get_client_ip(self) -> str:
        """Get client IP address from request."""
        if request.environ.get("HTTP_X_FORWARDED_FOR"):
            return request.environ.get("HTTP_X_FORWARDED_FOR").split(",")[0].strip()
        return request.remote_addr or "127.0.0.1"

    def is_blocked(self, client_ip: str) -> bool:
        """Check if client IP is blocked."""
        if client_ip not in self.blocked_ips:
            return False

        if datetime.now(timezone.utc) > self.blocked_ips[client_ip]:
            del self.blocked_ips[client_ip]
            self.failed_attempts[client_ip] = 0
            return False

        return True

    def block_ip(self, client_ip: str) -> None:
        """Block an IP address temporarily."""
        # Enforce max blocked IPs limit with LRU eviction
        if len(self.blocked_ips) >= self.MAX_BLOCKED_IPS:
            self._evict_oldest_blocked_ips(self.MAX_BLOCKED_IPS // 10)

        self.blocked_ips[client_ip] = (
            datetime.now(timezone.utc) + timedelta(seconds=SecurityConfig.BLOCK_DURATION)
        )
        security_logger.warning(f"IP blocked due to suspicious activity: {client_ip}")

    def _evict_oldest_blocked_ips(self, count: int) -> None:
        """Evict the oldest blocked IPs by expiry time."""
        if not self.blocked_ips:
            return
        # Sort by expiry time (oldest first) and remove
        sorted_ips = sorted(self.blocked_ips.items(), key=lambda x: x[1])
        for ip, _ in sorted_ips[:count]:
            del self.blocked_ips[ip]
            self.failed_attempts.pop(ip, None)

    def cleanup_stale_entries(self) -> int:
        """
        Remove stale entries from request history to prevent memory leaks.

        Returns:
            Number of entries removed
        """
        import time
        now = time.time()
        removed = 0

        # Remove entries with no recent requests
        stale_keys = [
            key for key, last_time in self._last_access.items()
            if now - last_time > self.STALE_ENTRY_AGE
        ]
        for key in stale_keys:
            self.request_history.pop(key, None)
            self._last_access.pop(key, None)
            removed += 1

        # Clean expired blocked IPs
        expired_blocks = [
            ip for ip, expiry in self.blocked_ips.items()
            if datetime.now(timezone.utc) > expiry
        ]
        for ip in expired_blocks:
            del self.blocked_ips[ip]
            self.failed_attempts.pop(ip, None)

        # Reset failed attempts for IPs with no recent activity
        stale_ips = [
            ip for ip in self.failed_attempts.keys()
            if not any(ip in key for key in self.request_history.keys())
        ]
        for ip in stale_ips:
            del self.failed_attempts[ip]

        if removed > 0:
            security_logger.debug(f"Rate limiter cleanup: removed {removed} stale entries")

        return removed

    def _enforce_memory_limit(self) -> None:
        """Enforce memory limits using LRU eviction if necessary."""
        import time

        if len(self.request_history) <= self.MAX_HISTORY_ENTRIES:
            return

        # Evict oldest 10% of entries by last access time
        evict_count = max(1, self.MAX_HISTORY_ENTRIES // 10)
        sorted_entries = sorted(self._last_access.items(), key=lambda x: x[1])

        for key, _ in sorted_entries[:evict_count]:
            self.request_history.pop(key, None)
            self._last_access.pop(key, None)

        security_logger.info(
            f"Rate limiter LRU eviction: removed {evict_count} entries, "
            f"current size: {len(self.request_history)}"
        )

    def get_memory_stats(self) -> dict[str, int]:
        """Get memory usage statistics for monitoring."""
        return {
            "history_entries": len(self.request_history),
            "blocked_ips": len(self.blocked_ips),
            "failed_attempts_tracked": len(self.failed_attempts),
            "max_history_entries": self.MAX_HISTORY_ENTRIES,
            "max_blocked_ips": self.MAX_BLOCKED_IPS,
        }

    def check_rate_limit(self, client_ip: str, endpoint: str = "") -> bool:
        """
        Check if request is within rate limits.

        Includes automatic memory management to prevent unbounded growth.

        Args:
            client_ip: Client IP address
            endpoint: API endpoint being accessed

        Returns:
            True if within limit, False if exceeded
        """
        import time

        now = time.time()

        # Periodic cleanup to prevent memory leaks
        self._request_count += 1
        if self._request_count >= self.CLEANUP_INTERVAL:
            self._request_count = 0
            self.cleanup_stale_entries()
            self._enforce_memory_limit()

        # Check if IP is blocked
        if self.is_blocked(client_ip):
            return False

        # Get applicable limit
        if endpoint in SecurityConfig.ENDPOINT_LIMITS:
            max_requests, window = SecurityConfig.ENDPOINT_LIMITS[endpoint]
        else:
            max_requests = SecurityConfig.RATE_LIMIT_REQUESTS
            window = SecurityConfig.RATE_LIMIT_WINDOW

        key = f"{client_ip}:{endpoint}" if endpoint else client_ip

        # Update last access time for LRU tracking
        self._last_access[key] = now

        # Clean old entries for this key
        self.request_history[key] = [
            ts for ts in self.request_history[key]
            if now - ts < window
        ]

        # Check limit
        if len(self.request_history[key]) >= max_requests:
            self.failed_attempts[client_ip] += 1
            if self.failed_attempts[client_ip] >= SecurityConfig.SUSPICIOUS_ACTIVITY_THRESHOLD:
                self.block_ip(client_ip)
            return False

        self.request_history[key].append(now)
        self.failed_attempts[client_ip] = 0
        return True

class InputSanitizer:
    """Sanitizes user input to prevent injection attacks."""

    # Patterns for dangerous content
    DANGEROUS_PATTERNS = [
        r"<script[^>]*>.*?</script>",  # Script tags
        r"javascript:",  # JavaScript protocol
        r"on\w+\s*=",  # Event handlers
        r"<iframe",  # iframes
        r"<embed",  # Embedded content
    ]

    # SQL injection patterns
    SQL_INJECTION_PATTERNS = [
        r"(\bUNION\b.*\bSELECT\b)",
        r"(\bOR\b.*=.*)",
        r"(\bDROP\b|\bDELETE\b|\bINSERT\b|\bUPDATE\b)",
        r"(--|#|;)",
    ]

    @staticmethod
    def sanitize_string(value: str, max_length: int = 1000) -> str:
        """
        Sanitize string input.

        Args:
            value: String to sanitize
            max_length: Maximum allowed length

        Returns:
            Sanitized string
        """
        if not isinstance(value, str):
            raise ValueError("Input must be string")

        if len(value) > max_length:
            raise ValueError(f"Input exceeds maximum length of {max_length}")

        # HTML escape
        value = html.escape(value)

        # Check for dangerous patterns
        for pattern in InputSanitizer.DANGEROUS_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                raise ValueError("Dangerous content detected in input")

        return value

    @staticmethod
    def sanitize_sql_input(value: str) -> str:
        """
        Detect SQL injection attempts.

        Args:
            value: Input to check

        Returns:
            Input if safe

        Raises:
            ValueError: If SQL injection detected
        """
        for pattern in InputSanitizer.SQL_INJECTION_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                raise ValueError("SQL injection pattern detected")

        return value

    @staticmethod
    def sanitize_json(data: dict[str, Any], max_depth: int = 10) -> dict[str, Any]:
        """
        Recursively sanitize JSON data.

        Args:
            data: Dictionary to sanitize
            max_depth: Maximum nesting depth

        Returns:
            Sanitized dictionary

        Raises:
            ValueError: If data exceeds limits
        """
        if max_depth <= 0:
            raise ValueError("JSON nesting too deep")

        if not isinstance(data, dict):
            raise ValueError("Expected dictionary")

        sanitized = {}
        for key, value in data.items():
            # Sanitize key
            key = InputSanitizer.sanitize_string(key, max_length=100)

            # Sanitize value based on type
            if isinstance(value, str):
                sanitized[key] = InputSanitizer.sanitize_string(value)
            elif isinstance(value, dict):
                sanitized[key] = InputSanitizer.sanitize_json(value, max_depth - 1)
            elif isinstance(value, list):
                sanitized[key] = [
                    (InputSanitizer.sanitize_json(item, max_depth - 1)
                     if isinstance(item, dict)
                     else InputSanitizer.sanitize_string(str(item))
                     if isinstance(item, (str, int, float, bool)) else item)
                    for item in value
                ]
            elif isinstance(value, (int, float, bool, type(None))):
                sanitized[key] = value
            else:
                raise ValueError(f"Unsupported type in JSON: {type(value)}")

        return sanitized

class SessionManager:
    """Manages secure user sessions with optional fingerprinting and IP binding."""

    def __init__(self):
        """Initialize session manager."""
        self.active_sessions: dict[str, dict[str, Any]] = {}
        self.session_tokens: dict[str, str] = {}

    @staticmethod
    def _is_trusted_proxy(ip_str: str) -> bool:
        """Return True if the given IP is in the trusted proxy allowlist/ranges."""
        try:
            ip_obj = ipaddress.ip_address(ip_str)
        except ValueError:
            return False
        trusted = set(SecurityConfig.TRUSTED_PROXY_IPS or [])
        if ip_str in trusted:
            return True
        for network in SecurityConfig.TRUSTED_PROXY_NETWORKS or []:
            try:
                if ip_obj in ipaddress.ip_network(network, strict=False):
                    return True
            except ValueError:
                continue
        return False

    @classmethod
    def _resolve_client_ip(cls) -> str:
        """
        Resolve the client IP without trusting spoofable headers unless explicitly allowed.
        """
        remote_ip = request.remote_addr or "127.0.0.1"
        if not SecurityConfig.TRUST_PROXY_HEADERS:
            return remote_ip

        if not cls._is_trusted_proxy(remote_ip):
            return remote_ip

        forwarded_for = request.headers.get("X-Forwarded-For", "")
        if forwarded_for:
            for candidate in forwarded_for.split(","):
                candidate = candidate.strip()
                if not candidate:
                    continue
                try:
                    ipaddress.ip_address(candidate)
                    return candidate
                except ValueError:
                    continue

        real_ip = request.headers.get("X-Real-IP", "").strip()
        if real_ip:
            try:
                ipaddress.ip_address(real_ip)
                return real_ip
            except ValueError:
                pass

        return remote_ip

    def create_session(self, user_id: str, metadata: dict[str, Any] | None = None) -> str:
        """
        Create a new secure session.

        Args:
            user_id: User identifier
            metadata: Optional session metadata

        Returns:
            Session token
        """
        session_token = secrets.token_hex(32)
        user_agent = request.headers.get("User-Agent", "")
        accept_language = request.headers.get("Accept-Language", "")
        session_data = {
            "user_id": user_id,
            "created_at": datetime.now(timezone.utc),
            "last_activity": datetime.now(timezone.utc),
            "ip_address": self._resolve_client_ip(),
            "user_agent": user_agent,
            "accept_language": accept_language,
            "metadata": metadata or {},
        }
        if SecurityConfig.STRICT_SESSION_FINGERPRINTING:
            session_data["fingerprint"] = self._build_fingerprint(
                session_data["ip_address"], user_agent, accept_language
            )

        self.active_sessions[session_token] = session_data
        self.session_tokens[user_id] = session_token

        return session_token

    def validate_session(self, session_token: str) -> tuple[bool, dict[str, Any] | None]:
        """
        Validate a session token.

        Args:
            session_token: Session token to validate

        Returns:
            Tuple of (is_valid, session_data)
        """
        if session_token not in self.active_sessions:
            return False, None

        session_data = self.active_sessions[session_token]

        # Check timeout
        last_activity = session_data["last_activity"]
        if (datetime.now(timezone.utc) - last_activity).total_seconds() > SecurityConfig.SESSION_TIMEOUT:
            self.destroy_session(session_token)
            return False, None

        # Check IP consistency
        current_ip = self._resolve_client_ip()
        if session_data["ip_address"] != current_ip:
            security_logger.warning(
                f"Session IP mismatch: {session_token}",
                extra={"event": "session.ip_mismatch", "expected": session_data["ip_address"], "observed": current_ip},
            )
            return False, None

        if SecurityConfig.STRICT_SESSION_FINGERPRINTING:
            expected = session_data.get("fingerprint")
            observed = self._build_fingerprint(
                current_ip,
                request.headers.get("User-Agent", ""),
                request.headers.get("Accept-Language", ""),
            )
            if expected and expected != observed:
                security_logger.warning(
                    "Session fingerprint mismatch",
                    extra={
                        "event": "session.fingerprint_mismatch",
                        "session_id": session_token,
                    },
                )
                return False, None

        # Update last activity
        session_data["last_activity"] = datetime.now(timezone.utc)

        return True, session_data

    @staticmethod
    def _build_fingerprint(ip_address: str, user_agent: str, accept_language: str) -> str:
        """
        Build a fingerprint for session binding based on configured attributes.
        """
        components = [ip_address]
        if SecurityConfig.SESSION_BIND_USER_AGENT:
            components.append(user_agent or "")
        if SecurityConfig.SESSION_BIND_ACCEPT_LANGUAGE:
            components.append(accept_language or "")
        data = "|".join(components).encode("utf-8")
        return hashlib.sha256(data).hexdigest()

    def destroy_session(self, session_token: str) -> None:
        """
        Destroy a session.

        Args:
            session_token: Session token to destroy
        """
        session_data = self.active_sessions.pop(session_token, None)
        if session_data:
            user_id = session_data.get("user_id")
            if user_id:
                self.session_tokens.pop(user_id, None)

class TOTPManager:
    """
    Two-Factor Authentication using TOTP (Time-based One-Time Password).

    Requires pyotp library:
    - pip install pyotp qrcode
    """

    AVAILABLE = False

    def __init__(self):
        """Initialize TOTP manager."""
        try:
            import pyotp
            self.pyotp = pyotp
            self.AVAILABLE = True
            self.user_secrets: dict[str, str] = {}
            self.user_backup_codes: dict[str, dict[str, Any]] = {}
            security_logger.info("TOTP manager initialized successfully")
        except ImportError:
            security_logger.warning("pyotp not installed - 2FA will be disabled")
            self.AVAILABLE = False
            self.user_backup_codes = {}

    @staticmethod
    def _hash_backup_code(code: str, salt: bytes) -> str:
        """
        Hash a backup code with the provided salt for secure storage.

        Args:
            code: Plaintext backup code
            salt: Per-user salt bytes

        Returns:
            Hex-encoded SHA-256 digest
        """
        digest = hashlib.sha256()
        digest.update(salt)
        digest.update(code.encode("utf-8"))
        return digest.hexdigest()

    def generate_secret(self, user_id: str, issuer: str = "XAI-Wallet") -> dict[str, str]:
        """
        Generate a new TOTP secret for a user.

        Args:
            user_id: User identifier
            issuer: Issuer name for QR code

        Returns:
            Dictionary with secret and provisioning URI
        """
        if not self.AVAILABLE:
            raise RuntimeError("TOTP not available - pyotp not installed")

        totp = self.pyotp.TOTP(self.pyotp.random_base32())
        secret = totp.secret
        self.user_secrets[user_id] = secret

        # Generate provisioning URI for QR code
        provisioning_uri = totp.provisioning_uri(
            name=user_id,
            issuer_name=issuer
        )

        return {
            "secret": secret,
            "uri": provisioning_uri,
        }

    def verify_token(self, user_id: str, token: str) -> bool:
        """
        Verify a TOTP token.

        Args:
            user_id: User identifier
            token: 6-digit token to verify

        Returns:
            True if valid, False otherwise
        """
        if not self.AVAILABLE:
            return False

        secret = self.user_secrets.get(user_id)
        if not secret:
            return False

        totp = self.pyotp.TOTP(secret)
        return totp.verify(token, valid_window=SecurityConfig.TOTP_WINDOW)

    def get_backup_codes(self, user_id: str, count: int = 10) -> list[str]:
        """
        Generate backup codes for account recovery.

        Args:
            user_id: User identifier
            count: Number of codes to generate

        Returns:
            List of backup codes
        """
        if not self.AVAILABLE:
            return []

        codes = [secrets.token_hex(4) for _ in range(count)]
        salt = secrets.token_bytes(16)
        hashed_codes: set[str] = set()
        for code in codes:
            hashed_codes.add(self._hash_backup_code(code, salt))

        self.user_backup_codes[user_id] = {
            "salt": salt,
            "hashes": hashed_codes,
            "generated_at": datetime.now(timezone.utc),
            "used": set(),
        }
        security_logger.info(
            "Generated backup codes",
            extra={
                "event": "totp.backup.generated",
                "user_id": user_id,
                "count": count,
            },
        )
        return codes

    def verify_backup_code(self, user_id: str, code: str) -> bool:
        """
        Verify a previously issued backup code. Codes are single-use.

        Args:
            user_id: User identifier
            code: Backup code provided by the user

        Returns:
            True if the code is valid and unused, False otherwise.
        """
        if not self.AVAILABLE:
            security_logger.warning(
                "Backup code verification attempted while TOTP unavailable",
                extra={"event": "totp.backup.verify_unavailable"},
            )
            return False

        record = self.user_backup_codes.get(user_id)
        if not record:
            security_logger.warning(
                "No backup codes found for user",
                extra={"event": "totp.backup.missing", "user_id": user_id},
            )
            return False

        candidate_hash = self._hash_backup_code(code, record["salt"])
        if candidate_hash not in record["hashes"]:
            security_logger.warning(
                "Invalid backup code attempt",
                extra={"event": "totp.backup.invalid", "user_id": user_id},
            )
            return False

        record["hashes"].remove(candidate_hash)
        record["used"].add(candidate_hash)
        security_logger.info(
            "Backup code accepted",
            extra={"event": "totp.backup.accepted", "user_id": user_id},
        )
        return True

class SecurityMiddleware:
    """
    Main security middleware for Flask applications.

    Combines all security features into a single middleware class.
    """

    def __init__(self, app: Flask, config: SecurityConfig | None = None):
        """
        Initialize security middleware.

        Args:
            app: Flask application instance
            config: Security configuration (uses defaults if None)
        """
        self.app = app
        self.config = config or SecurityConfig()
        self.rate_limiter = RateLimiter()
        self.token_manager = TokenManager(app.secret_key)
        self.session_manager = SessionManager()
        self.input_sanitizer = InputSanitizer()
        self.totp_manager = TOTPManager()

        # Secure credential storage - thread-safe with hashed passwords
        self._credentials_lock = threading.RLock()
        self._credentials: dict[str, str] = {}  # user_id -> hashed_password

        # Set Flask configuration
        self._configure_flask()

        # Register middleware
        self._register_middleware()

        security_logger.info("Security middleware initialized successfully")

    def _configure_flask(self) -> None:
        """Configure Flask for security."""
        self.app.config["SESSION_COOKIE_SECURE"] = self.config.SESSION_COOKIE_SECURE
        self.app.config["SESSION_COOKIE_HTTPONLY"] = self.config.SESSION_COOKIE_HTTPONLY
        self.app.config["SESSION_COOKIE_SAMESITE"] = self.config.SESSION_COOKIE_SAMESITE
        self.app.config["SESSION_COOKIE_NAME"] = self.config.SESSION_COOKIE_NAME
        self.app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(seconds=self.config.SESSION_TIMEOUT)

    def _register_middleware(self) -> None:
        """Register all middleware handlers."""
        self.app.before_request(self._before_request)
        self.app.after_request(self._after_request)
        self.app.errorhandler(RateLimitExceeded)(self._handle_rate_limit)
        self.app.errorhandler(CSRFTokenInvalid)(self._handle_csrf_error)

    def _before_request(self) -> Response | None:
        """Pre-request middleware."""
        # Skip middleware for static files
        if request.path.startswith("/static"):
            return None

        # Check request size
        content_length = request.content_length or 0
        if content_length > self.config.MAX_BODY_SIZE:
            return jsonify({"error": "Request body too large"}), 413

        # Check URL length
        if len(request.path) > self.config.MAX_URL_LENGTH:
            return jsonify({"error": "URL too long"}), 414

        # Rate limiting
        if self.config.RATE_LIMIT_ENABLED:
            client_ip = self.rate_limiter.get_client_ip()
            endpoint = request.path
            if not self.rate_limiter.check_rate_limit(client_ip, endpoint):
                raise RateLimitExceeded("Rate limit exceeded")

        # CSRF validation
        if self.config.CSRF_ENABLED and request.method not in self.config.CSRF_EXEMPT_METHODS:
            if not self._is_csrf_exempt(request.path):
                self._validate_csrf_token()

        return None

    def _after_request(self, response: Response) -> Response:
        """Post-request middleware."""
        # Add security headers
        if self.config.SECURITY_HEADERS_ENABLED:
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
            response.headers["Content-Security-Policy"] = self.config.CONTENT_SECURITY_POLICY
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
            response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        return response

    def _is_csrf_exempt(self, path: str) -> bool:
        """Check if endpoint is CSRF exempt."""
        for exempt_path in self.config.CSRF_EXEMPT_ENDPOINTS:
            if path.startswith(exempt_path):
                return True
        return False

    def _validate_csrf_token(self) -> None:
        """Validate CSRF token from request."""
        # Try to get token from various sources
        token = (
            request.form.get("_csrf_token") or
            request.headers.get("X-CSRF-Token") or
            request.headers.get("X-CSRFToken")
        )

        if not token:
            raise CSRFTokenInvalid("CSRF token missing")

        # Get or create session ID
        session_id = session.get("_session_id")
        if not session_id:
            session_id = secrets.token_hex(16)
            session["_session_id"] = session_id

        # Validate token
        if not self.token_manager.validate_csrf_token(token, session_id):
            raise CSRFTokenInvalid("CSRF token invalid")

    def _handle_rate_limit(self, error: RateLimitExceeded) -> tuple[dict[str, Any], int]:
        """Handle rate limit errors."""
        security_logger.warning(f"Rate limit exceeded: {request.remote_addr}")
        return (
            jsonify({"error": "Rate limit exceeded. Please try again later."}),
            429
        )

    def _handle_csrf_error(self, error: CSRFTokenInvalid) -> tuple[dict[str, Any], int]:
        """Handle CSRF errors."""
        security_logger.warning(f"CSRF error: {str(error)} - {request.remote_addr}")
        return (
            jsonify({"error": "Security validation failed. Please refresh and try again."}),
            403
        )

    def require_auth(self, f: Callable) -> Callable:
        """
        Decorator to require authentication.

        Usage:
            @app.route("/protected")
            @security_middleware.require_auth
            def protected_endpoint():
                return jsonify({"data": "protected"})
        """
        @wraps(f)
        def decorated_function(*args, **kwargs):
            session_token = request.headers.get("Authorization", "").replace("Bearer ", "")
            if not session_token:
                return jsonify({"error": "Authentication required"}), 401

            is_valid, session_data = self.session_manager.validate_session(session_token)
            if not is_valid:
                return jsonify({"error": "Invalid or expired session"}), 401

            # Store session data in request context
            request.session_data = session_data

            return f(*args, **kwargs)

        return decorated_function

    def get_csrf_token_endpoint(self) -> Callable:
        """
        Create endpoint for getting CSRF token.

        Usage:
            app.add_url_rule(
                "/csrf-token",
                "get_csrf_token",
                security_middleware.get_csrf_token_endpoint(),
                methods=["GET"]
            )
        """
        def get_token():
            session_id = session.get("_session_id")
            if not session_id:
                session_id = secrets.token_hex(16)
                session["_session_id"] = session_id

            token = self.token_manager.generate_csrf_token(session_id)
            return jsonify({"csrf_token": token, "session_id": session_id})

        return get_token

    def get_login_endpoint(self) -> Callable:
        """
        Create endpoint for session login.

        Usage:
            app.add_url_rule(
                "/login",
                "login",
                security_middleware.get_login_endpoint(),
                methods=["POST"]
            )
        """
        def login():
            try:
                data = request.get_json() or {}

                # Sanitize input
                user_id = data.get("user_id", "")
                password = data.get("password", "")

                if not user_id or not password:
                    return jsonify({"error": "Missing credentials"}), 400

                # In production, verify credentials against database
                # This is a placeholder
                if not self._verify_credentials(user_id, password):
                    return jsonify({"error": "Invalid credentials"}), 401

                # Create session
                session_token = self.session_manager.create_session(user_id)

                return jsonify({
                    "session_token": session_token,
                    "user_id": user_id,
                    "timeout": self.config.SESSION_TIMEOUT
                }), 200

            except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as e:
                security_logger.error(f"Login error: {str(e)}")
                return jsonify({"error": "Login failed"}), 500

        return login

    def _verify_credentials(self, user_id: str, password: str) -> bool:
        """
        Verify user credentials using secure password hashing.

        Uses bcrypt for password verification with constant-time comparison
        to prevent timing attacks. Falls back to PBKDF2 if bcrypt unavailable.

        Args:
            user_id: User identifier
            password: Password to verify

        Returns:
            True if credentials are valid, False otherwise
        """
        if not user_id or not password:
            security_logger.warning(
                "Authentication attempt with empty credentials",
                extra={"user_id": user_id[:20] if user_id else "empty"}
            )
            return False

        with self._credentials_lock:
            stored_hash = self._credentials.get(user_id)

        if stored_hash is None:
            # Unknown user - perform dummy comparison to prevent timing attacks
            # This ensures the response time is similar whether user exists or not
            if BCRYPT_AVAILABLE:
                try:
                    # Use a pre-computed dummy hash for timing consistency
                    dummy_hash = b"$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.VTtYA2qwp1Rq2S"
                    bcrypt.checkpw(password.encode("utf-8"), dummy_hash)
                except Exception:
                    pass
            else:
                # PBKDF2 dummy verification
                hashlib.pbkdf2_hmac(
                    "sha256",
                    password.encode("utf-8"),
                    b"dummy_salt_for_timing",
                    600000
                )
            security_logger.warning(
                "Authentication attempt for unknown user",
                extra={"user_id": user_id[:20]}
            )
            return False

        # Verify password against stored hash
        try:
            if BCRYPT_AVAILABLE:
                # bcrypt.checkpw is constant-time
                is_valid = bcrypt.checkpw(
                    password.encode("utf-8"),
                    stored_hash.encode("utf-8") if isinstance(stored_hash, str) else stored_hash
                )
            else:
                # PBKDF2 fallback - extract salt from stored hash
                # Format: "pbkdf2:salt_hex:hash_hex"
                parts = stored_hash.split(":")
                if len(parts) != 3 or parts[0] != "pbkdf2":
                    security_logger.error("Corrupted password hash format")
                    return False
                salt = bytes.fromhex(parts[1])
                expected_hash = bytes.fromhex(parts[2])
                computed_hash = hashlib.pbkdf2_hmac(
                    "sha256",
                    password.encode("utf-8"),
                    salt,
                    600000
                )
                # Constant-time comparison
                is_valid = hmac.compare_digest(computed_hash, expected_hash)

            if is_valid:
                security_logger.info(
                    "Successful authentication",
                    extra={"user_id": user_id[:20]}
                )
            else:
                security_logger.warning(
                    "Failed authentication attempt - invalid password",
                    extra={"user_id": user_id[:20]}
                )
            return is_valid

        except Exception as e:
            security_logger.error(
                f"Password verification error: {type(e).__name__}",
                extra={"user_id": user_id[:20]}
            )
            return False

    def register_user(self, user_id: str, password: str) -> bool:
        """
        Register a new user with securely hashed password.

        Uses bcrypt (12 rounds) or PBKDF2 (600K iterations) for password hashing.

        Args:
            user_id: User identifier (must be unique)
            password: Plain text password to hash and store

        Returns:
            True if registration successful, False if user already exists

        Raises:
            ValueError: If user_id or password is empty or invalid
        """
        if not user_id or not isinstance(user_id, str):
            raise ValueError("user_id must be a non-empty string")
        if not password or not isinstance(password, str):
            raise ValueError("password must be a non-empty string")
        if len(password) < 8:
            raise ValueError("password must be at least 8 characters")
        if len(password) > 128:
            raise ValueError("password must not exceed 128 characters")

        with self._credentials_lock:
            if user_id in self._credentials:
                security_logger.warning(
                    "Registration attempt for existing user",
                    extra={"user_id": user_id[:20]}
                )
                return False

            # Hash password
            if BCRYPT_AVAILABLE:
                # bcrypt with 12 rounds (secure default)
                password_hash = bcrypt.hashpw(
                    password.encode("utf-8"),
                    bcrypt.gensalt(rounds=12)
                ).decode("utf-8")
            else:
                # PBKDF2 fallback with 600K iterations
                salt = secrets.token_bytes(32)
                hash_bytes = hashlib.pbkdf2_hmac(
                    "sha256",
                    password.encode("utf-8"),
                    salt,
                    600000
                )
                password_hash = f"pbkdf2:{salt.hex()}:{hash_bytes.hex()}"

            self._credentials[user_id] = password_hash
            security_logger.info(
                "User registered successfully",
                extra={"user_id": user_id[:20]}
            )
            return True

    def change_password(self, user_id: str, old_password: str, new_password: str) -> bool:
        """
        Change a user's password after verifying the old password.

        Args:
            user_id: User identifier
            old_password: Current password for verification
            new_password: New password to set

        Returns:
            True if password changed successfully, False otherwise
        """
        if not self._verify_credentials(user_id, old_password):
            return False

        if not new_password or len(new_password) < 8:
            raise ValueError("New password must be at least 8 characters")
        if len(new_password) > 128:
            raise ValueError("New password must not exceed 128 characters")

        with self._credentials_lock:
            if BCRYPT_AVAILABLE:
                password_hash = bcrypt.hashpw(
                    new_password.encode("utf-8"),
                    bcrypt.gensalt(rounds=12)
                ).decode("utf-8")
            else:
                salt = secrets.token_bytes(32)
                hash_bytes = hashlib.pbkdf2_hmac(
                    "sha256",
                    new_password.encode("utf-8"),
                    salt,
                    600000
                )
                password_hash = f"pbkdf2:{salt.hex()}:{hash_bytes.hex()}"

            self._credentials[user_id] = password_hash
            security_logger.info(
                "Password changed successfully",
                extra={"user_id": user_id[:20]}
            )
            return True

def setup_security_middleware(
    app: Flask,
    config: SecurityConfig | None = None,
    enable_cors: bool = True,
) -> SecurityMiddleware:
    """
    Setup security middleware for a Flask application.

    Args:
        app: Flask application instance
        config: Security configuration
        enable_cors: Whether to enable CORS

    Returns:
        SecurityMiddleware instance
    """
    middleware = SecurityMiddleware(app, config)

    # Setup CORS if enabled
    if enable_cors:
        try:
            from flask_cors import CORS
            CORS(
                app,
                origins=config.CORS_ORIGINS if config else SecurityConfig.CORS_ORIGINS,
                methods=config.CORS_METHODS if config else SecurityConfig.CORS_METHODS,
                allow_headers=["Content-Type", "X-CSRF-Token"],
                supports_credentials=config.CORS_ALLOW_CREDENTIALS if config else True,
                max_age=config.CORS_MAX_AGE if config else 3600,
            )
        except ImportError:
            security_logger.warning("flask-cors not installed - CORS not configured")

    # Setup CSRF token endpoint
    app.add_url_rule(
        "/csrf-token",
        "get_csrf_token",
        middleware.get_csrf_token_endpoint(),
        methods=["GET"]
    )

    # Setup login endpoint
    app.add_url_rule(
        "/login",
        "login",
        middleware.get_login_endpoint(),
        methods=["POST"]
    )

    return middleware
