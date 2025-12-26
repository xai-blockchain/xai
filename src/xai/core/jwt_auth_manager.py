# Manager Consolidation: This module provides a standalone JWT/API auth manager.
# For production API authentication, use:
#     from xai.core.api_auth import APIAuthManager, JWTAuthManager
#
# This module is kept for standalone JWT authentication scenarios.

from __future__ import annotations

"""
XAI Blockchain - JWT Authentication and API Key Manager

Comprehensive authentication system with:
- JWT token generation and validation
- API key management and validation
- Role-based access control (RBAC)
- Token refresh mechanism
- Secure key storage
- Audit logging
- Automatic JWT blacklist cleanup
"""

import atexit
import hashlib
import hmac
import logging
import secrets
import threading
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from functools import wraps

import jwt
from flask import jsonify, request

security_logger = logging.getLogger('xai.security')

class UserRole(Enum):
    """User roles for RBAC"""
    ADMIN = "admin"
    GOVERNANCE = "governance"
    MINING = "mining"
    USER = "user"
    PUBLIC = "public"

class APIKeyScope(Enum):
    """Scopes for API keys"""
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"
    MINING = "mining"
    GOVERNANCE = "governance"

@dataclass
class TokenClaims:
    """JWT token claims"""
    user_id: str
    username: str
    role: UserRole
    iat: datetime  # Issued at
    exp: datetime  # Expiration
    nbf: datetime  # Not before
    jti: str  # JWT ID (for revocation)

    def to_dict(self) -> Dict:
        """Convert to dictionary for JWT encoding"""
        return {
            'user_id': self.user_id,
            'username': self.username,
            'role': self.role.value,
            'iat': self.iat.timestamp(),
            'exp': self.exp.timestamp(),
            'nbf': self.nbf.timestamp(),
            'jti': self.jti,
        }

@dataclass
class APIKey:
    """API Key representation"""
    key_id: str
    key_hash: str  # SHA256 hash of the actual key
    user_id: str
    name: str
    scopes: list[APIKeyScope]
    created_at: datetime
    expires_at: datetime | None
    last_used: datetime | None
    is_active: bool
    rate_limit_per_hour: int | None

class JWTAuthManager:
    """
    Manages JWT token generation, validation, and revocation with automatic cleanup.
    """

    # Minimum entropy requirements for JWT secrets (128 bits = 16 bytes = 32 hex chars)
    MIN_SECRET_ENTROPY_BYTES = 16

    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        token_expiration_hours: int = 24,
        refresh_token_expiration_days: int = 30,
        cleanup_enabled: bool = True,
        cleanup_interval_seconds: int = 900,
    ):
        """
        Initialize JWT authentication manager.

        Args:
            secret_key: Secret key for signing tokens (minimum 128 bits entropy)
            algorithm: JWT algorithm (HS256, RS256, etc.)
            token_expiration_hours: Access token expiration in hours
            refresh_token_expiration_days: Refresh token expiration in days
            cleanup_enabled: Enable automatic blacklist cleanup (default: True)
            cleanup_interval_seconds: Cleanup interval in seconds (default: 900 = 15 minutes)

        Raises:
            ValueError: If secret_key has insufficient entropy (< 128 bits)
        """
        # Validate secret key entropy
        if len(secret_key) < self.MIN_SECRET_ENTROPY_BYTES * 2:  # Hex encoding doubles length
            security_logger.warning(
                f"JWT secret key has insufficient entropy: {len(secret_key)} chars < {self.MIN_SECRET_ENTROPY_BYTES * 2} minimum"
            )
            raise ValueError(
                f"JWT secret key must be at least {self.MIN_SECRET_ENTROPY_BYTES * 2} characters "
                f"(128 bits entropy). Got {len(secret_key)} characters."
            )
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.token_expiration = timedelta(hours=token_expiration_hours)
        self.refresh_token_expiration = timedelta(days=refresh_token_expiration_days)

        # Token revocation list (for logout)
        self.revoked_tokens: dict[str, datetime] = {}

        # Active sessions
        self.active_sessions: dict[str, Dict] = {}

        # Background cleanup configuration
        self._cleanup_enabled = cleanup_enabled
        self._cleanup_interval = cleanup_interval_seconds
        self._cleanup_thread: threading.Thread | None = None
        self._cleanup_stop_event = threading.Event()
        self._revoked_tokens_lock = threading.RLock()  # Thread-safe access to revoked_tokens

        # Start background cleanup if enabled
        if self._cleanup_enabled:
            self._start_cleanup_thread()

        # Register cleanup on exit
        atexit.register(self._shutdown_cleanup)

    def generate_token(
        self,
        user_id: str,
        username: str,
        role: UserRole,
        additional_claims: Dict | None = None,
    ) -> str:
        """
        Generate a JWT access token.

        Args:
            user_id: User ID
            username: Username
            role: User role
            additional_claims: Additional claims to include

        Returns:
            str: Encoded JWT token
        """
        now = datetime.now(timezone.utc)
        exp = now + self.token_expiration
        nbf = now

        claims = TokenClaims(
            user_id=user_id,
            username=username,
            role=role,
            iat=now,
            exp=exp,
            nbf=nbf,
            jti=secrets.token_hex(16),  # JWT ID for revocation
        )

        token_dict = claims.to_dict()

        # Add additional claims
        if additional_claims:
            token_dict.update(additional_claims)

        try:
            token = jwt.encode(token_dict, self.secret_key, algorithm=self.algorithm)
            security_logger.info(f"Token generated for user {user_id}")
            return token
        except (ValueError, TypeError, KeyError) as e:
            security_logger.error(f"Error generating token: {str(e)}", extra={"error_type": type(e).__name__})
            raise

    def validate_token(self, token: str) -> tuple[bool, Dict | None, str | None]:
        """
        Validate JWT token with explicit expiration verification.

        Security features:
        - Explicit expiration verification (verify_exp=True)
        - Clock skew tolerance (30 seconds)
        - Required claims validation (exp, iat, jti)
        - Signature verification
        - Revocation list checking (thread-safe)

        Args:
            token: JWT token to validate

        Returns:
            tuple[bool, Dict | None, str | None]: (valid, claims, error_message)
        """
        try:
            # Decode token with explicit security options
            claims = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={
                    "verify_signature": True,  # Verify signature
                    "verify_exp": True,  # CRITICAL: Verify expiration
                    "verify_iat": True,  # Verify issued-at time
                    "require": ["exp", "iat", "jti"],  # Required claims
                },
                leeway=30  # 30 seconds clock skew tolerance
            )

            # Check if token is revoked (thread-safe)
            jti = claims.get('jti')
            with self._revoked_tokens_lock:
                is_revoked = jti in self.revoked_tokens

            if is_revoked:
                security_logger.warning(f"Revoked token access attempt: {jti}")
                return False, None, "Token has been revoked"

            return True, claims, None

        except jwt.ExpiredSignatureError:
            security_logger.warning("Expired token access attempt")
            return False, None, "Token has expired"
        except jwt.InvalidTokenError as e:
            security_logger.warning(f"Invalid token: {str(e)}")
            return False, None, f"Invalid token: {str(e)}"
        except (ValueError, TypeError, KeyError, AttributeError) as e:
            security_logger.error(f"Error validating token: {str(e)}", extra={"error_type": type(e).__name__})
            return False, None, "Token validation failed"

    def refresh_token(self, token: str) -> tuple[bool, str | None, str | None]:
        """
        Generate a new access token from a valid token.

        Args:
            token: Current valid JWT token

        Returns:
            tuple[bool, str | None, str | None]: (success, new_token, error_message)
        """
        valid, claims, error = self.validate_token(token)
        if not valid:
            return False, None, error

        # Generate new token with same claims
        new_token = self.generate_token(
            user_id=claims['user_id'],
            username=claims['username'],
            role=UserRole(claims['role']),
        )

        return True, new_token, None

    def revoke_token(self, token: str) -> bool:
        """
        Revoke a token (add to revocation list).

        Note: verify_exp=False is intentionally used here because we need to
        decode and revoke even expired tokens to extract their JTI and expiration
        for proper blacklist management.

        Thread-safe operation.

        Args:
            token: JWT token to revoke

        Returns:
            bool: Success status
        """
        try:
            # Intentionally skip expiration check - we need to revoke expired tokens too
            claims = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"verify_exp": False},  # Intentional: allow revoking expired tokens
            )

            jti = claims.get('jti')
            exp = datetime.fromtimestamp(claims['exp'], tz=timezone.utc)

            if jti:
                with self._revoked_tokens_lock:
                    self.revoked_tokens[jti] = exp
                security_logger.info(f"Token revoked: {jti}")
                return True

        except (ValueError, KeyError, TypeError) as e:
            security_logger.error(f"Error revoking token: {str(e)}", extra={"error_type": type(e).__name__})

        return False

    def cleanup_revoked_tokens(self) -> int:
        """
        Remove expired entries from revocation list.

        Thread-safe operation that prevents memory growth from accumulating
        expired tokens.

        Returns:
            int: Number of entries removed
        """
        now = datetime.now(timezone.utc)

        with self._revoked_tokens_lock:
            expired = [jti for jti, exp in self.revoked_tokens.items() if exp < now]

            for jti in expired:
                del self.revoked_tokens[jti]

            remaining = len(self.revoked_tokens)

        # Log cleanup statistics
        if expired:
            security_logger.info(
                f"JWT blacklist cleanup: removed {len(expired)} expired tokens, {remaining} remaining"
            )

        return len(expired)

    def _start_cleanup_thread(self) -> None:
        """Start background thread for automatic blacklist cleanup.

        The thread runs as a daemon and performs periodic cleanup of expired tokens.
        """
        if self._cleanup_thread is not None and self._cleanup_thread.is_alive():
            security_logger.warning("Cleanup thread already running")
            return

        self._cleanup_stop_event.clear()
        self._cleanup_thread = threading.Thread(
            target=self._cleanup_worker,
            name="JWT-Blacklist-Cleanup",
            daemon=True
        )
        self._cleanup_thread.start()
        security_logger.info(
            f"JWT blacklist cleanup thread started (interval: {self._cleanup_interval} seconds)"
        )

    def _cleanup_worker(self) -> None:
        """Background worker that periodically cleans up expired blacklist entries.

        Runs in a daemon thread and stops when _cleanup_stop_event is set.
        """
        while not self._cleanup_stop_event.is_set():
            # Wait for cleanup interval or stop event
            if self._cleanup_stop_event.wait(timeout=self._cleanup_interval):
                # Stop event was set
                break

            # Perform cleanup
            try:
                removed = self.cleanup_revoked_tokens()
                security_logger.debug(
                    f"Background cleanup completed: {removed} tokens removed"
                )
            except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as e:
                security_logger.error(
                    f"Error during background cleanup: {type(e).__name__}",
                    extra={"event": "jwt_auth.cleanup_error", "error": str(e)}
                )

        security_logger.info("JWT blacklist cleanup thread stopped")

    def _shutdown_cleanup(self) -> None:
        """Stop the cleanup thread gracefully.

        Called automatically via atexit registration.
        """
        if self._cleanup_thread is not None and self._cleanup_thread.is_alive():
            security_logger.info("Shutting down JWT blacklist cleanup thread...")
            self._cleanup_stop_event.set()
            self._cleanup_thread.join(timeout=5)
            if self._cleanup_thread.is_alive():
                security_logger.warning("Cleanup thread did not stop within timeout")

    def stop_cleanup(self) -> None:
        """Manually stop the background cleanup thread.

        Useful for testing or manual control.
        """
        self._shutdown_cleanup()

    def get_blacklist_size(self) -> int:
        """Get current size of revocation blacklist.

        Thread-safe operation.

        Returns:
            int: Number of tokens in revocation list
        """
        with self._revoked_tokens_lock:
            return len(self.revoked_tokens)

class APIKeyManager:
    """
    Manages API keys for programmatic access.
    """

    def __init__(self):
        """Initialize API key manager"""
        # API keys: {key_id: APIKey}
        self.api_keys: dict[str, APIKey] = {}

        # User API keys: {user_id: [key_id1, key_id2, ...]}
        self.user_keys: dict[str, list[str]] = {}

        # Actual keys (stored separately for security): {key_hash: key}
        # In production, these should be in a secure vault
        self._key_store: dict[str, str] = {}

    def generate_api_key(
        self,
        user_id: str,
        name: str,
        scopes: list[APIKeyScope],
        expiration_days: int | None = 90,
        rate_limit_per_hour: int | None = 1000,
    ) -> tuple[str, APIKey]:
        """
        Generate a new API key.

        Args:
            user_id: User ID
            name: Key name
            scopes: List of scopes
            expiration_days: Days until expiration (None = no expiration)
            rate_limit_per_hour: Rate limit per hour

        Returns:
            tuple[str, APIKey]: (actual_key, key_metadata)
        """
        # Generate actual key
        actual_key = f"xai_{secrets.token_urlsafe(32)}"

        # Create key hash
        key_hash = hashlib.sha256(actual_key.encode()).hexdigest()

        # Create key ID
        key_id = secrets.token_hex(16)

        # Calculate expiration
        expires_at = None
        if expiration_days:
            expires_at = datetime.now(timezone.utc) + timedelta(days=expiration_days)

        # Create API key object
        api_key = APIKey(
            key_id=key_id,
            key_hash=key_hash,
            user_id=user_id,
            name=name,
            scopes=scopes,
            created_at=datetime.now(timezone.utc),
            expires_at=expires_at,
            last_used=None,
            is_active=True,
            rate_limit_per_hour=rate_limit_per_hour,
        )

        # Store key
        self.api_keys[key_id] = api_key
        self._key_store[key_hash] = actual_key

        # Track user's keys
        if user_id not in self.user_keys:
            self.user_keys[user_id] = []
        self.user_keys[user_id].append(key_id)

        security_logger.info(f"API key generated for user {user_id}: {name}")

        return actual_key, api_key

    def validate_api_key(self, api_key: str) -> tuple[bool, APIKey | None, str | None]:
        """
        Validate an API key.

        Args:
            api_key: API key to validate

        Returns:
            tuple[bool, APIKey | None, str | None]: (valid, key_info, error_message)
        """
        try:
            # Hash the provided key
            key_hash = hashlib.sha256(api_key.encode()).hexdigest()

            # Find key using constant-time comparison to prevent timing attacks
            for key_id, key_info in self.api_keys.items():
                if hmac.compare_digest(key_info.key_hash, key_hash):
                    # Check if active
                    if not key_info.is_active:
                        return False, None, "API key is inactive"

                    # Check if expired
                    if key_info.expires_at and key_info.expires_at < datetime.now(timezone.utc):
                        return False, None, "API key has expired"

                    # Update last used
                    key_info.last_used = datetime.now(timezone.utc)

                    return True, key_info, None

            return False, None, "Invalid API key"

        except (ValueError, KeyError, AttributeError, TypeError) as e:
            security_logger.error(f"Error validating API key: {str(e)}", extra={"error_type": type(e).__name__})
            return False, None, "API key validation failed"

    def revoke_api_key(self, user_id: str, key_id: str) -> bool:
        """
        Revoke an API key.

        Args:
            user_id: User ID
            key_id: Key ID to revoke

        Returns:
            bool: Success status
        """
        if key_id not in self.api_keys:
            return False

        key_info = self.api_keys[key_id]

        # Verify ownership
        if key_info.user_id != user_id:
            security_logger.warning(f"Unauthorized revocation attempt: {user_id} vs {key_info.user_id}")
            return False

        key_info.is_active = False
        security_logger.info(f"API key revoked: {key_id}")

        return True

    def get_user_keys(self, user_id: str) -> list[APIKey]:
        """
        Get all API keys for a user.

        Args:
            user_id: User ID

        Returns:
            list[APIKey]: List of user's API keys
        """
        key_ids = self.user_keys.get(user_id, [])
        return [self.api_keys[kid] for kid in key_ids if kid in self.api_keys]

    def check_rate_limit(self, api_key: str) -> tuple[bool, str | None]:
        """
        Check if API key is within rate limits.

        Args:
            api_key: API key to check

        Returns:
            tuple[bool, str | None]: (allowed, error_message)
        """
        valid, key_info, error = self.validate_api_key(api_key)
        if not valid:
            return False, error

        # Check rate limit
        if key_info.rate_limit_per_hour:
            # In a real implementation, this would track actual request counts
            pass

        return True, None

# Decorator for JWT authentication
def require_jwt(f):
    """Decorator to require JWT authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')

        if not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing or invalid Authorization header'}), 401

        token = auth_header[7:]  # Remove "Bearer " prefix

        # Validate token (use global manager)
        manager = get_jwt_manager()
        valid, claims, error = manager.validate_token(token)

        if not valid:
            return jsonify({'error': error}), 401

        # Add claims to request context
        request.jwt_claims = claims

        return f(*args, **kwargs)

    return decorated_function

# Decorator for API key authentication
def require_api_key(f):
    """Decorator to require API key authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # API key can come from header or query parameter
        api_key = request.headers.get('X-API-Key') or request.args.get('api_key')

        if not api_key:
            return jsonify({'error': 'Missing API key'}), 401

        # Validate key
        api_manager = get_api_key_manager()
        valid, key_info, error = api_manager.validate_api_key(api_key)

        if not valid:
            return jsonify({'error': error}), 401

        # Add key info to request context
        request.api_key_info = key_info

        return f(*args, **kwargs)

    return decorated_function

# Decorator for role-based access control
def require_role(required_role: UserRole):
    """Decorator to require specific user role"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(request, 'jwt_claims'):
                return jsonify({'error': 'Authentication required'}), 401

            user_role = UserRole(request.jwt_claims.get('role'))

            if user_role != required_role:
                return jsonify({'error': f'Requires {required_role.value} role'}), 403

            return f(*args, **kwargs)

        return decorated_function

    return decorator

# Global instances
_jwt_manager = None
_api_key_manager = None

def get_jwt_manager(
    secret_key: str = None,
    algorithm: str = "HS256",
) -> JWTAuthManager:
    """Get global JWT manager instance"""
    global _jwt_manager
    if _jwt_manager is None:
        if not secret_key:
            # Use a default for testing
            secret_key = secrets.token_hex(32)
        _jwt_manager = JWTAuthManager(secret_key, algorithm)
    return _jwt_manager

def get_api_key_manager() -> APIKeyManager:
    """Get global API key manager instance"""
    global _api_key_manager
    if _api_key_manager is None:
        _api_key_manager = APIKeyManager()
    return _api_key_manager
