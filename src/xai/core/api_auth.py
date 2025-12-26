"""API authentication helper for protecting sensitive endpoints with rotation support.

Manager Consolidation Note:
- JWTAuthManager in this module is the primary implementation for API-integrated JWT auth
- For standalone JWT authentication, see also: xai.core.jwt_auth_manager.JWTAuthManager
- Both provide similar functionality; this one integrates with Flask request handling
"""

from __future__ import annotations

import atexit
import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import threading
import time
from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Any

from flask import Request

try:
    import jwt
except ImportError:
    jwt = None  # type: ignore

try:
    from cryptography.fernet import Fernet, InvalidToken
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
except ImportError:
    Fernet = None  # type: ignore
    InvalidToken = None  # type: ignore

from xai.core.config import Config
from xai.core.security_validation import log_security_event

logger = logging.getLogger(__name__)

class APIKeyStore:
    """Persistent API key storage with auditing metadata and expiration."""

    def __init__(
        self,
        path: str,
        default_ttl_days: int = 90,
        max_ttl_days: int = 365,
        allow_permanent: bool = False,
    ) -> None:
        self.path = path
        self._audit_path = f"{path}.log"
        self._keys: dict[str, dict[str, Any]] = {}
        self._default_ttl_seconds = max(default_ttl_days, 1) * 86400
        self._max_ttl_seconds = max(max_ttl_days, default_ttl_days) * 86400
        self._allow_permanent = allow_permanent
        self._load()

    @staticmethod
    def _hash_key(key: str) -> str:
        return hashlib.sha256(key.encode("utf-8")).hexdigest()

    def _load(self) -> None:
        """Load persisted API key metadata from disk, hydrating audit fields."""
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as handle:
                    data = json.load(handle)
                    if isinstance(data, dict):
                        self._keys = data
                    else:
                        self._keys = {}
            except (OSError, json.JSONDecodeError):
                self._keys = {}
        self._hydrate_metadata()

    def _persist(self) -> None:
        """Persist API key store atomically to disk."""
        directory = os.path.dirname(self.path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        tmp_path = f"{self.path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as handle:
            json.dump(self._keys, handle, indent=2)
        os.replace(tmp_path, self.path)

    def list_keys(self) -> dict[str, dict[str, Any]]:
        """Return all keys with computed expiration/expired fields."""
        now = time.time()
        result: dict[str, dict[str, Any]] = {}
        for key_id, metadata in self._keys.items():
            copied = dict(metadata)
            copied["expired"] = self._is_expired(metadata, now)
            result[key_id] = copied
        return result

    @property
    def audit_log_path(self) -> str:
        return self._audit_path

    def issue_key(
        self,
        label: str = "",
        scope: str = "user",
        plaintext: str | None = None,
        ttl_seconds: int | None = None,
        permanent: bool = False,
    ) -> tuple[str, str]:
        new_key = plaintext or secrets.token_hex(32)
        key_id = self._hash_key(new_key)
        created = time.time()
        expires_at = self._compute_expires_at(created, ttl_seconds, permanent)
        self._keys[key_id] = {
            "label": label,
            "created": created,
            "scope": scope,
            "expires_at": expires_at,
            "permanent": expires_at is None,
        }
        self._persist()
        self._log_event(
            "issue",
            key_id,
            {
                "label": label,
                "scope": scope,
                "expires_at": expires_at,
                "permanent": expires_at is None,
            },
        )
        return new_key, key_id

    def revoke_key(self, key_id: str) -> bool:
        if key_id in self._keys:
            del self._keys[key_id]
            self._persist()
            self._log_event("revoke", key_id)
            return True
        return False

    def rotate_key(
        self,
        key_id: str,
        label: str = "",
        scope: str = "user",
        ttl_seconds: int | None = None,
        permanent: bool = False,
    ) -> tuple[str, str]:
        """
        Rotate a key by revoking the old key and issuing a new one with the same label/scope.
        Returns plaintext and new key_id.
        """
        if key_id in self._keys:
            self.revoke_key(key_id)
        plaintext, new_id = self.issue_key(label=label, scope=scope, ttl_seconds=ttl_seconds, permanent=permanent)
        self._log_event(
            "rotate",
            new_id,
            {
                "replaced": key_id,
                "scope": scope,
                "expires_at": self._keys.get(new_id, {}).get("expires_at"),
                "permanent": self._keys.get(new_id, {}).get("permanent"),
            },
        )
        return plaintext, new_id

    def _log_event(self, action: str, key_id: str, extra: dict[str, Any] | None = None) -> None:
        """Append an audit log entry to the JSONL audit file and emit security event."""
        event = {
            "timestamp": time.time(),
            "action": action,
            "key_id": key_id,
        }
        if extra:
            event.update(extra)
        directory = os.path.dirname(self._audit_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(self._audit_path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(event) + "\n")
        self._emit_security_log(event)

    def get_events(self, limit: int = 100) -> list[dict[str, Any]]:
        """Return the most recent audit events (default 100)."""
        if not os.path.exists(self._audit_path):
            return []
        events: list[dict[str, Any]] = []
        with open(self._audit_path, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return events[-limit:]

    def _emit_security_log(self, event: dict[str, Any]) -> None:
        """Emit a structured security event for API key changes."""
        try:
            payload = {
                "action": event.get("action"),
                "key_id": event.get("key_id"),
                "scope": event.get("scope", "unknown"),
                "label": event.get("label", ""),
                "timestamp": event.get("timestamp"),
                "expires_at": event.get("expires_at"),
                "permanent": event.get("permanent", False),
            }
            severity = "WARNING" if event.get("action") == "revoke" else "INFO"
            log_security_event("api_key_audit", payload, severity=severity)
        except (RuntimeError, ValueError, TypeError, KeyError) as exc:
            # Never let logging issues break key management, but log for debugging
            logger.debug(
                "Security log emission failed: %s",
                type(exc).__name__,
                extra={"event": "api_auth.emit_log_failed", "error": str(exc)}
            )
            return

    def _hydrate_metadata(self) -> None:
        """Ensure keys loaded from disk contain expiration metadata."""
        changed = False
        now = time.time()
        for metadata in self._keys.values():
            created = metadata.get("created")
            if not isinstance(created, (int, float)):
                created = now
                metadata["created"] = created
                changed = True
            if "expires_at" not in metadata:
                metadata["expires_at"] = self._compute_expires_at(created, None, metadata.get("permanent", False))
                changed = True
            if metadata.get("expires_at") is None and not self._allow_permanent:
                metadata["expires_at"] = self._compute_expires_at(created, None, False)
                metadata["permanent"] = False
                changed = True
            if "permanent" not in metadata:
                metadata["permanent"] = metadata.get("expires_at") is None
                changed = True
        if changed:
            self._persist()

    def _compute_expires_at(
        self, created: float, ttl_seconds: int | None, permanent: bool
    ) -> float | None:
        """Compute an expiration timestamp or None for permanent keys."""
        if permanent:
            if not self._allow_permanent:
                raise ValueError("Permanent API keys are disabled by configuration")
            return None
        ttl = self._default_ttl_seconds if ttl_seconds is None else int(ttl_seconds)
        if ttl <= 0:
            raise ValueError("ttl_seconds must be positive")
        ttl = min(ttl, self._max_ttl_seconds)
        return created + ttl

    @staticmethod
    def _is_expired(metadata: dict[str, Any], now: float | None = None) -> bool:
        """Return True if the provided metadata has elapsed expiration."""
        expires_at = metadata.get("expires_at")
        if expires_at is None:
            return False
        try:
            expiry = float(expires_at)
        except (TypeError, ValueError):
            return True
        return (now or time.time()) >= expiry

class APIAuthManager:
    """API key authentication + rotation helper."""

    def __init__(
        self,
        required: bool = False,
        allowed_keys: list[str] | None = None,
        store: APIKeyStore | None = None,
        admin_keys: list[str] | None = None,
        operator_keys: list[str] | None = None,
        auditor_keys: list[str] | None = None,
    ) -> None:
        """
        Initialize API authentication manager with optional manual and persisted keys.

        Args:
            required: If True, reject requests without a valid API key.
            allowed_keys: Manual user-scope keys (plaintext) to permit.
            store: Persistent APIKeyStore for issued/rotated keys.
            admin_keys: Manual admin-scope keys (plaintext).
            operator_keys: Manual operator-scope keys (plaintext).
            auditor_keys: Manual auditor-scope keys (plaintext).
        """
        def _parse(keys: list[str] | None) -> list[str]:
            return [key.strip() for key in (keys or []) if key.strip()]

        manual_users = _parse(allowed_keys)
        manual_admins = _parse(admin_keys)
        manual_operators = _parse(operator_keys)
        manual_auditors = _parse(auditor_keys)

        manual_user_hashes = {self._hash_key(key) for key in manual_users}
        self._manual_admin_hashes = {self._hash_key(key) for key in manual_admins}
        self._manual_operator_hashes = {self._hash_key(key) for key in manual_operators}
        self._manual_auditor_hashes = {self._hash_key(key) for key in manual_auditors}
        self._manual_hashes = (
            manual_user_hashes
            | self._manual_admin_hashes
            | self._manual_operator_hashes
            | self._manual_auditor_hashes
        )
        self._manual_scope_map = {}
        for hashed in manual_user_hashes:
            self._manual_scope_map[hashed] = "user"
        for hashed in self._manual_operator_hashes:
            self._manual_scope_map[hashed] = "operator"
        for hashed in self._manual_auditor_hashes:
            self._manual_scope_map[hashed] = "auditor"
        for hashed in self._manual_admin_hashes:
            self._manual_scope_map[hashed] = "admin"
        self._store = store
        self._store_metadata: dict[str, dict[str, Any]] = store.list_keys() if store else {}
        self._store_hash_set = set(self._store_metadata.keys()) if store else set()
        self._store_admin_hashes = {
            key_id for key_id, meta in self._store_metadata.items() if meta.get("scope") == "admin"
        }
        self._store_operator_hashes = {
            key_id for key_id, meta in self._store_metadata.items() if meta.get("scope") == "operator"
        }
        self._store_auditor_hashes = {
            key_id for key_id, meta in self._store_metadata.items() if meta.get("scope") == "auditor"
        }
        self._required = required

    @classmethod
    def from_config(cls, store: APIKeyStore | None = None) -> "APIAuthManager":
        """Construct manager from Config settings and optional store."""
        return cls(
            required=getattr(Config, "API_AUTH_REQUIRED", False),
            allowed_keys=list(getattr(Config, "API_AUTH_KEYS", [])),
            admin_keys=list(getattr(Config, "API_ADMIN_KEYS", [])),
            operator_keys=list(getattr(Config, "API_OPERATOR_KEYS", [])),
            auditor_keys=list(getattr(Config, "API_AUDITOR_KEYS", [])),
            store=store,
        )

    @staticmethod
    def _hash_key(key: str) -> str:
        return hashlib.sha256(key.encode("utf-8")).hexdigest()

    def is_enabled(self) -> bool:
        """Return True if API auth is required/enabled."""
        return self._required

    def _extract_key(self, request: Request) -> str | None:
        """Extract API key from headers or query parameters."""
        header_key = request.headers.get("X-API-Key")
        if header_key:
            return header_key.strip()

        auth_header = request.headers.get("Authorization", "").strip()
        if auth_header.lower().startswith("bearer "):
            return auth_header.split(" ", 1)[1].strip()

        arg_key = request.args.get("api_key")
        if arg_key:
            return arg_key.strip()

        return None

    def authorize(self, request: Request) -> tuple[bool, str | None]:
        """Authorize request using default scope rules."""
        if not self.is_enabled():
            return True, None

        key = self._extract_key(request)
        if not key:
            return False, "API key missing or invalid"

        hashed = self._hash_key(key)
        if hashed in self._manual_hashes:
            return True, None
        if hashed in self._store_hash_set:
            active, reason = self._is_store_key_active(hashed)
            if active:
                return True, None
            return False, reason
        return False, "API key missing or invalid"

    def authorize_admin(self, request: Request) -> tuple[bool, str | None]:
        """Authorize request as admin using admin token sources."""
        key = self._extract_admin_token(request)
        if not key:
            return False, "Admin token missing"
        hashed = self._hash_key(key)
        if hashed in self._manual_admin_hashes or hashed in self._store_admin_hashes:
            if hashed in self._store_admin_hashes and hashed not in self._manual_admin_hashes:
                active, reason = self._is_store_key_active(hashed)
                if not active:
                    return False, reason or "Admin token expired"
            return True, None
        return False, "Admin token invalid"

    def authorize_with_scope(self, request: Request) -> tuple[bool, str | None, str | None]:
        """
        Authorize request and return the resolved scope.

        Returns:
            (allowed, scope, reason)
        """
        # Admin token takes precedence and maps to admin scope
        admin_token = self._extract_admin_token(request)
        if admin_token:
            hashed = self._hash_key(admin_token)
            if hashed in self._manual_admin_hashes or hashed in self._store_admin_hashes:
                if hashed in self._store_admin_hashes and hashed not in self._manual_admin_hashes:
                    active, reason = self._is_store_key_active(hashed)
                    if not active:
                        return False, None, reason
                return True, "admin", None
            return False, None, "Admin token invalid"

        if not self.is_enabled():
            return True, None, None

        api_key = self._extract_key(request)
        if not api_key:
            return False, None, "API key missing or invalid"

        hashed = self._hash_key(api_key)
        if hashed in self._manual_hashes:
            return True, self._manual_scope_map.get(hashed, "user"), None
        if hashed in self._store_hash_set:
            active, reason = self._is_store_key_active(hashed)
            if not active:
                return False, None, reason
            meta = self._store_metadata.get(hashed, {})
            scope = meta.get("scope", "user")
            return True, scope, None
        return False, None, "API key missing or invalid"

    def authorize_scope(self, request: Request, allowed_scopes: set[str]) -> tuple[bool, str | None, str | None]:
        """
        Authorize with scope enforcement.

        Returns:
            (allowed, scope, reason)
        """
        allowed_scopes_normalized = {scope.lower() for scope in allowed_scopes}
        ok, scope, reason = self.authorize_with_scope(request)
        if not ok:
            return False, scope, reason
        if scope is None:
            return True, None, None
        scope_normalized = scope.lower()
        if "admin" in allowed_scopes_normalized and scope_normalized == "admin":
            return True, scope, None
        if scope_normalized in allowed_scopes_normalized:
            return True, scope, None
        return False, scope, "Forbidden: insufficient scope"

    def refresh_from_store(self) -> None:
        """Reload store metadata to reflect newly issued/rotated/revoked keys."""
        if self._store:
            self._store_metadata = self._store.list_keys()
            self._store_hash_set = set(self._store_metadata.keys())
            self._store_admin_hashes = {
                key_id for key_id, meta in self._store_metadata.items() if meta.get("scope") == "admin"
            }
            self._store_operator_hashes = {
                key_id for key_id, meta in self._store_metadata.items() if meta.get("scope") == "operator"
            }
            self._store_auditor_hashes = {
                key_id for key_id, meta in self._store_metadata.items() if meta.get("scope") == "auditor"
            }

    def list_key_metadata(self) -> dict[str, Any]:
        """Return summary metadata for manual and stored keys."""
        return {
            "manual_keys": len(self._manual_hashes),
            "manual_admin_keys": len(self._manual_admin_hashes),
            "store": self._store_metadata if self._store else {},
        }

    def issue_key(
        self,
        label: str = "",
        scope: str = "user",
        ttl_seconds: int | None = None,
        permanent: bool = False,
    ) -> tuple[str, str]:
        """Issue a new key via the persistent store."""
        if not self._store:
            raise ValueError("API key store not configured")
        plaintext, key_id = self._store.issue_key(label=label, scope=scope, ttl_seconds=ttl_seconds, permanent=permanent)
        self.refresh_from_store()
        return plaintext, key_id

    def revoke_key(self, key_id: str) -> bool:
        """Revoke a key by ID and refresh store metadata."""
        if not self._store:
            raise ValueError("API key store not configured")
        removed = self._store.revoke_key(key_id)
        self.refresh_from_store()
        return removed

    def rotate_key(
        self,
        key_id: str,
        label: str = "",
        scope: str = "user",
        ttl_seconds: int | None = None,
        permanent: bool = False,
    ) -> tuple[str, str]:
        """Rotate a key via the store and emit rotation security event."""
        if not self._store:
            raise ValueError("API key store not configured")
        new_plain, new_id = self._store.rotate_key(
            key_id, label=label, scope=scope, ttl_seconds=ttl_seconds, permanent=permanent
        )
        self.refresh_from_store()
        try:
            severity = "WARNING" if scope == "admin" else "INFO"
            log_security_event(
                "api_key_rotated",
                {"old_key_id": key_id, "new_key_id": new_id, "scope": scope, "label": label},
                severity=severity,
            )
        except (RuntimeError, ValueError, TypeError, KeyError) as e:
            logger.debug(
                "Failed to log key rotation event: %s",
                type(e).__name__,
                extra={"event": "api_auth.rotation_log_failed", "error": str(e)}
            )
        return new_plain, new_id

    def _extract_admin_token(self, request: Request) -> str | None:
        """Extract admin token from custom header or Authorization prefix."""
        token = request.headers.get("X-Admin-Token")
        if token:
            return token.strip()
        auth = request.headers.get("Authorization", "").strip()
        if auth.lower().startswith("admin "):
            return auth.split(" ", 1)[1].strip()
        return None

    def _is_store_key_active(self, key_id: str) -> tuple[bool, str | None]:
        """
        Determine if a stored key is still valid based on expiration metadata.
        """
        if key_id not in self._store_metadata:
            return False, "API key missing or invalid"

        metadata = self._store_metadata[key_id]
        expires_at = metadata.get("expires_at")
        if expires_at is None:
            return True, None

        try:
            expiry = float(expires_at)
        except (TypeError, ValueError):
            expiry = 0.0

        if time.time() >= expiry:
            try:
                log_security_event(
                    "api_key_expired_attempt",
                    {
                        "key_id": key_id,
                        "scope": metadata.get("scope", "unknown"),
                        "label": metadata.get("label", ""),
                        "expired_at": expires_at,
                    },
                    severity="WARNING",
                )
            except (RuntimeError, ValueError, TypeError, KeyError):
                logger.debug(
                    "Failed to emit api_key_expired_attempt event",
                    extra={"event": "api_auth.expiration_log_failed", "key_id": key_id},
                )
            return False, "API key expired"

        return True, None

class JWTAuthManager:
    """JWT-based authentication with token expiry, refresh, and blacklist.

    Implements Task 64: JWT Token Expiry with production-grade security features.
    Includes automatic background cleanup of expired blacklist entries to prevent memory growth.
    """

    def __init__(
        self,
        secret_key: str,
        token_expiry_hours: int = 1,
        refresh_expiry_days: int = 30,
        algorithm: str = "HS256",
        clock_skew_seconds: int = 30,
        cleanup_enabled: bool = True,
        cleanup_interval_seconds: int = 900
    ):
        """Initialize JWT authentication manager.

        Args:
            secret_key: Secret key for signing JWT tokens
            token_expiry_hours: Access token expiry in hours (default: 1)
            refresh_expiry_days: Refresh token expiry in days (default: 30)
            algorithm: JWT signing algorithm (default: HS256)
            clock_skew_seconds: Clock skew tolerance in seconds (default: 30)
            cleanup_enabled: Enable automatic blacklist cleanup (default: True)
            cleanup_interval_seconds: Cleanup interval in seconds (default: 900 = 15 minutes)
        """
        if not jwt:
            raise ImportError("PyJWT library is required for JWT authentication")

        self.secret_key = secret_key
        self.token_expiry = timedelta(hours=token_expiry_hours)
        self.refresh_expiry = timedelta(days=refresh_expiry_days)
        self.algorithm = algorithm
        self.clock_skew = timedelta(seconds=clock_skew_seconds)
        self.blacklist: set[str] = set()

        # Background cleanup configuration
        self._cleanup_enabled = cleanup_enabled
        self._cleanup_interval = cleanup_interval_seconds
        self._cleanup_thread: threading.Thread | None = None
        self._cleanup_stop_event = threading.Event()
        self._blacklist_lock = threading.RLock()  # Thread-safe access to blacklist

        # Start background cleanup if enabled
        if self._cleanup_enabled:
            self._start_cleanup_thread()

        # Register cleanup on exit
        atexit.register(self._shutdown_cleanup)

    def generate_token(self, user_id: str, scope: str = "user") -> tuple[str, str]:
        """Generate access token and refresh token.

        Args:
            user_id: User identifier
            scope: Token scope (user, admin, etc.)

        Returns:
            Tuple of (access_token, refresh_token)
        """
        now = datetime.now(timezone.utc)

        # Access token (short-lived)
        access_payload = {
            "sub": user_id,  # Standard JWT "subject" claim
            "user_id": user_id,  # For backward compatibility
            "scope": scope,
            "exp": now + self.token_expiry,
            "iat": now,
            "type": "access"
        }
        access_token = jwt.encode(access_payload, self.secret_key, algorithm=self.algorithm)

        # Refresh token (long-lived)
        refresh_payload = {
            "sub": user_id,  # Standard JWT "subject" claim
            "user_id": user_id,  # For backward compatibility
            "scope": scope,
            "exp": now + self.refresh_expiry,
            "iat": now,
            "type": "refresh"
        }
        refresh_token = jwt.encode(refresh_payload, self.secret_key, algorithm=self.algorithm)

        # Log token generation
        log_security_event("jwt_token_generated", {
            "user_id": user_id,
            "scope": scope,
            "timestamp": now.isoformat()
        }, severity="INFO")

        return access_token, refresh_token

    def validate_token(self, token: str, remote_addr: str | None = None) -> tuple[bool, dict[str, Any] | None, str | None]:
        """Validate JWT token with expiration check.

        Security features:
        - Explicit expiration verification (verify_exp=True)
        - Clock skew tolerance to handle minor time drift
        - Required claims validation (exp, sub, iat)
        - Signature verification
        - Blacklist checking for revoked tokens
        - Thread-safe blacklist access

        Args:
            token: JWT token to validate
            remote_addr: Remote IP address for security logging (optional)

        Returns:
            Tuple of (is_valid, payload, error_message)
        """
        # Check blacklist first (fast path for revoked tokens) - thread-safe
        with self._blacklist_lock:
            is_blacklisted = token in self.blacklist

        if is_blacklisted:
            log_security_event(
                "jwt_revoked_token_attempt",
                {
                    "remote_addr": remote_addr or "unknown",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                severity="WARNING"
            )
            return False, None, "Token has been revoked"

        try:
            # Decode with explicit security options
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={
                    "verify_signature": True,  # Verify HMAC signature
                    "verify_exp": True,  # CRITICAL: Verify expiration
                    "verify_iat": True,  # Verify issued-at time
                    "require": ["exp", "sub", "iat"],  # Required claims
                },
                leeway=self.clock_skew  # Clock skew tolerance (default: 30 seconds)
            )

            return True, payload, None

        except jwt.ExpiredSignatureError:
            # Token has expired - log security event
            log_security_event(
                "jwt_expired_token_attempt",
                {
                    "remote_addr": remote_addr or "unknown",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                severity="WARNING"
            )
            return False, None, "Token has expired"

        except jwt.InvalidTokenError as e:
            # Invalid token (malformed, wrong signature, missing claims, etc.)
            log_security_event(
                "jwt_invalid_token_attempt",
                {
                    "remote_addr": remote_addr or "unknown",
                    "error": str(e),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                severity="WARNING"
            )
            return False, None, f"Invalid token: {str(e)}"

        except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as e:
            # Unexpected error - log for investigation
            logger.error(
                "Unexpected JWT validation error: %s",
                type(e).__name__,
                extra={
                    "event": "api_auth.jwt_validation_error",
                    "error": str(e),
                    "remote_addr": remote_addr or "unknown"
                }
            )
            return False, None, "Token validation error"

    def refresh_access_token(self, refresh_token: str) -> tuple[bool, str | None, str | None]:
        """Exchange refresh token for new access token.

        Args:
            refresh_token: Valid refresh token

        Returns:
            Tuple of (success, new_access_token, error_message)
        """
        valid, payload, error = self.validate_token(refresh_token)

        if not valid:
            return False, None, error or "Invalid refresh token"

        # Verify it's a refresh token
        if payload and payload.get("type") != "refresh":
            return False, None, "Not a refresh token"

        # Generate new access token
        if payload:
            user_id = payload.get("user_id")
            scope = payload.get("scope", "user")
            access_token, _ = self.generate_token(user_id, scope)

            log_security_event(
                "jwt_token_refreshed",
                {
                    "user_id": user_id,
                    "scope": scope,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
                severity="INFO",
            )

            return True, access_token, None

        return False, None, "Invalid token payload"

    def revoke_token(self, token: str) -> None:
        """Add token to blacklist (logout).

        Note: verify_exp=False is intentionally used here because we need to
        decode and revoke even expired tokens to extract user info for audit logging.

        Thread-safe operation.

        Args:
            token: JWT token to revoke
        """
        with self._blacklist_lock:
            self.blacklist.add(token)

        # Try to extract user info for logging (skip expiration check - intentional)
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"verify_exp": False}  # Intentional: allow revoking expired tokens
            )
            user_id = payload.get("user_id", "unknown")
            log_security_event(
                "jwt_token_revoked",
                {
                    "user_id": user_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
                severity="WARNING",
            )
        except (jwt.PyJWTError, ValueError, TypeError, KeyError) as e:
            # Log decode failure but still proceed with revocation
            logger.debug(
                "Could not decode token for revocation logging: %s",
                type(e).__name__,
                extra={"event": "api_auth.jwt_revoke_decode_failed"}
            )

    def cleanup_expired_tokens(self) -> int:
        """Remove expired tokens from blacklist.

        Thread-safe operation that checks each blacklisted token and removes if expired.
        This prevents memory growth from accumulating expired tokens.

        Returns:
            Number of tokens removed
        """
        removed = 0
        expired_tokens = set()

        # Create a snapshot of blacklist to iterate over (thread-safe)
        with self._blacklist_lock:
            blacklist_snapshot = set(self.blacklist)
            blacklist_size_before = len(self.blacklist)

        # Check each token for expiration (outside lock to avoid blocking)
        for token in blacklist_snapshot:
            try:
                # Explicitly verify expiration to identify expired tokens
                jwt.decode(
                    token,
                    self.secret_key,
                    algorithms=[self.algorithm],
                    options={"verify_exp": True}  # Explicit: we want ExpiredSignatureError
                )
            except jwt.ExpiredSignatureError:
                # Token is expired, can be removed
                expired_tokens.add(token)
                removed += 1
            except (jwt.PyJWTError, OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as e:
                # Any other error (invalid token, decode error), keep in blacklist to be safe
                logger.debug(
                    "Token cleanup check failed: %s - keeping in blacklist",
                    type(e).__name__,
                    extra={"event": "api_auth.jwt_cleanup_check_failed"}
                )

        # Remove expired tokens from blacklist (thread-safe)
        with self._blacklist_lock:
            self.blacklist -= expired_tokens
            blacklist_size_after = len(self.blacklist)

        # Log cleanup statistics
        if removed > 0:
            logger.info(
                "JWT blacklist cleanup: removed %d expired tokens, %d remaining",
                removed,
                blacklist_size_after
            )
            log_security_event(
                "jwt_blacklist_cleanup",
                {
                    "removed_count": removed,
                    "remaining_count": blacklist_size_after,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
                severity="INFO",
            )

        return removed

    def extract_token_from_request(self, request: Request) -> str | None:
        """Extract JWT token from Flask request.

        Checks Authorization header with Bearer scheme.

        Args:
            request: Flask request object

        Returns:
            JWT token string or None
        """
        auth_header = request.headers.get("Authorization", "").strip()
        if auth_header.lower().startswith("bearer "):
            return auth_header.split(" ", 1)[1].strip()
        return None

    def authorize_request(self, request: Request, required_scope: str | None = None) -> tuple[bool, dict[str, Any] | None, str | None]:
        """Authorize Flask request with JWT token.

        Args:
            request: Flask request object
            required_scope: Required scope for authorization (optional)

        Returns:
            Tuple of (is_authorized, payload, error_message)
        """
        token = self.extract_token_from_request(request)

        if not token:
            return False, None, "No JWT token provided"

        # Extract remote address for security logging
        remote_addr = request.remote_addr if hasattr(request, 'remote_addr') else None

        valid, payload, error = self.validate_token(token, remote_addr=remote_addr)

        if not valid:
            return False, None, error

        # Check scope if required
        if required_scope and payload:
            token_scope = payload.get("scope")
            if token_scope != required_scope:
                log_security_event(
                    "jwt_insufficient_permissions",
                    {
                        "remote_addr": remote_addr or "unknown",
                        "required_scope": required_scope,
                        "token_scope": token_scope,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    },
                    severity="WARNING"
                )
                return False, None, f"Insufficient permissions. Required: {required_scope}"

        return True, payload, None

    def get_blacklist_size(self) -> int:
        """Get current blacklist size.

        Thread-safe operation.

        Returns:
            Number of tokens in blacklist
        """
        with self._blacklist_lock:
            return len(self.blacklist)

    def _start_cleanup_thread(self) -> None:
        """Start background thread for automatic blacklist cleanup.

        The thread runs as a daemon and performs periodic cleanup of expired tokens.
        """
        if self._cleanup_thread is not None and self._cleanup_thread.is_alive():
            logger.warning("Cleanup thread already running")
            return

        self._cleanup_stop_event.clear()
        self._cleanup_thread = threading.Thread(
            target=self._cleanup_worker,
            name="JWT-Blacklist-Cleanup",
            daemon=True
        )
        self._cleanup_thread.start()
        logger.info(
            "JWT blacklist cleanup thread started (interval: %d seconds)",
            self._cleanup_interval
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
                removed = self.cleanup_expired_tokens()
                logger.debug(
                    "Background cleanup completed: %d tokens removed",
                    removed
                )
            except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as e:
                logger.error(
                    "Error during background cleanup: %s",
                    type(e).__name__,
                    extra={"event": "api_auth.cleanup_error", "error": str(e)}
                )

        logger.info("JWT blacklist cleanup thread stopped")

    def _shutdown_cleanup(self) -> None:
        """Stop the cleanup thread gracefully.

        Called automatically via atexit registration.
        """
        if self._cleanup_thread is not None and self._cleanup_thread.is_alive():
            logger.info("Shutting down JWT blacklist cleanup thread...")
            self._cleanup_stop_event.set()
            self._cleanup_thread.join(timeout=5)
            if self._cleanup_thread.is_alive():
                logger.warning("Cleanup thread did not stop within timeout")

    def stop_cleanup(self) -> None:
        """Manually stop the background cleanup thread.

        Useful for testing or manual control.
        """
        self._shutdown_cleanup()
