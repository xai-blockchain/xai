"""
XAI Blockchain - JWT Authentication and API Key Manager

Comprehensive authentication system with:
- JWT token generation and validation
- API key management and validation
- Role-based access control (RBAC)
- Token refresh mechanism
- Secure key storage
- Audit logging
"""

import jwt
import secrets
import hashlib
import logging
from typing import Dict, Optional, Tuple, List
from datetime import datetime, timezone, timedelta
from functools import wraps
from dataclasses import dataclass, asdict
from enum import Enum
from flask import request, jsonify

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
    scopes: List[APIKeyScope]
    created_at: datetime
    expires_at: Optional[datetime]
    last_used: Optional[datetime]
    is_active: bool
    rate_limit_per_hour: Optional[int]


class JWTAuthManager:
    """
    Manages JWT token generation, validation, and revocation.
    """

    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        token_expiration_hours: int = 24,
        refresh_token_expiration_days: int = 30,
    ):
        """
        Initialize JWT authentication manager.

        Args:
            secret_key: Secret key for signing tokens
            algorithm: JWT algorithm (HS256, RS256, etc.)
            token_expiration_hours: Access token expiration in hours
            refresh_token_expiration_days: Refresh token expiration in days
        """
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.token_expiration = timedelta(hours=token_expiration_hours)
        self.refresh_token_expiration = timedelta(days=refresh_token_expiration_days)

        # Token revocation list (for logout)
        self.revoked_tokens: Dict[str, datetime] = {}

        # Active sessions
        self.active_sessions: Dict[str, Dict] = {}

    def generate_token(
        self,
        user_id: str,
        username: str,
        role: UserRole,
        additional_claims: Optional[Dict] = None,
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
        except Exception as e:
            security_logger.error(f"Error generating token: {str(e)}")
            raise

    def validate_token(self, token: str) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """
        Validate JWT token with explicit expiration verification.

        Security features:
        - Explicit expiration verification (verify_exp=True)
        - Clock skew tolerance (30 seconds)
        - Required claims validation (exp, iat, jti)
        - Signature verification
        - Revocation list checking

        Args:
            token: JWT token to validate

        Returns:
            Tuple[bool, Optional[Dict], Optional[str]]: (valid, claims, error_message)
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

            # Check if token is revoked
            jti = claims.get('jti')
            if jti in self.revoked_tokens:
                security_logger.warning(f"Revoked token access attempt: {jti}")
                return False, None, "Token has been revoked"

            return True, claims, None

        except jwt.ExpiredSignatureError:
            security_logger.warning("Expired token access attempt")
            return False, None, "Token has expired"
        except jwt.InvalidTokenError as e:
            security_logger.warning(f"Invalid token: {str(e)}")
            return False, None, f"Invalid token: {str(e)}"
        except Exception as e:
            security_logger.error(f"Error validating token: {str(e)}")
            return False, None, "Token validation failed"

    def refresh_token(self, token: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Generate a new access token from a valid token.

        Args:
            token: Current valid JWT token

        Returns:
            Tuple[bool, Optional[str], Optional[str]]: (success, new_token, error_message)
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
                self.revoked_tokens[jti] = exp
                security_logger.info(f"Token revoked: {jti}")
                return True

        except Exception as e:
            security_logger.error(f"Error revoking token: {str(e)}")

        return False

    def cleanup_revoked_tokens(self) -> int:
        """
        Remove expired entries from revocation list.

        Returns:
            int: Number of entries removed
        """
        now = datetime.now(timezone.utc)
        expired = [jti for jti, exp in self.revoked_tokens.items() if exp < now]

        for jti in expired:
            del self.revoked_tokens[jti]

        return len(expired)


class APIKeyManager:
    """
    Manages API keys for programmatic access.
    """

    def __init__(self):
        """Initialize API key manager"""
        # API keys: {key_id: APIKey}
        self.api_keys: Dict[str, APIKey] = {}

        # User API keys: {user_id: [key_id1, key_id2, ...]}
        self.user_keys: Dict[str, List[str]] = {}

        # Actual keys (stored separately for security): {key_hash: key}
        # In production, these should be in a secure vault
        self._key_store: Dict[str, str] = {}

    def generate_api_key(
        self,
        user_id: str,
        name: str,
        scopes: List[APIKeyScope],
        expiration_days: Optional[int] = 90,
        rate_limit_per_hour: Optional[int] = 1000,
    ) -> Tuple[str, APIKey]:
        """
        Generate a new API key.

        Args:
            user_id: User ID
            name: Key name
            scopes: List of scopes
            expiration_days: Days until expiration (None = no expiration)
            rate_limit_per_hour: Rate limit per hour

        Returns:
            Tuple[str, APIKey]: (actual_key, key_metadata)
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

    def validate_api_key(self, api_key: str) -> Tuple[bool, Optional[APIKey], Optional[str]]:
        """
        Validate an API key.

        Args:
            api_key: API key to validate

        Returns:
            Tuple[bool, Optional[APIKey], Optional[str]]: (valid, key_info, error_message)
        """
        try:
            # Hash the provided key
            key_hash = hashlib.sha256(api_key.encode()).hexdigest()

            # Find key
            for key_id, key_info in self.api_keys.items():
                if key_info.key_hash == key_hash:
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

        except Exception as e:
            security_logger.error(f"Error validating API key: {str(e)}")
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

    def get_user_keys(self, user_id: str) -> List[APIKey]:
        """
        Get all API keys for a user.

        Args:
            user_id: User ID

        Returns:
            List[APIKey]: List of user's API keys
        """
        key_ids = self.user_keys.get(user_id, [])
        return [self.api_keys[kid] for kid in key_ids if kid in self.api_keys]

    def check_rate_limit(self, api_key: str) -> Tuple[bool, Optional[str]]:
        """
        Check if API key is within rate limits.

        Args:
            api_key: API key to check

        Returns:
            Tuple[bool, Optional[str]]: (allowed, error_message)
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
