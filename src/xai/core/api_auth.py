"""API authentication helper for protecting sensitive endpoints with rotation support."""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import time
from typing import Dict, Optional, Tuple, Any, List, Set
from datetime import datetime, timedelta, timezone
from collections import deque

import logging

from flask import Request

try:
    import jwt
except ImportError:
    jwt = None  # type: ignore

from xai.core.config import Config
from xai.core.security_validation import log_security_event

logger = logging.getLogger(__name__)


class APIKeyStore:
    """Persistent API key storage with auditing metadata."""

    def __init__(self, path: str) -> None:
        self.path = path
        self._audit_path = f"{path}.log"
        self._keys: Dict[str, Dict[str, Any]] = {}
        self._load()

    @staticmethod
    def _hash_key(key: str) -> str:
        return hashlib.sha256(key.encode("utf-8")).hexdigest()

    def _load(self) -> None:
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

    def _persist(self) -> None:
        directory = os.path.dirname(self.path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        tmp_path = f"{self.path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as handle:
            json.dump(self._keys, handle, indent=2)
        os.replace(tmp_path, self.path)

    def list_keys(self) -> Dict[str, Dict[str, Any]]:
        return dict(self._keys)

    @property
    def audit_log_path(self) -> str:
        return self._audit_path

    def issue_key(self, label: str = "", scope: str = "user", plaintext: Optional[str] = None) -> Tuple[str, str]:
        new_key = plaintext or secrets.token_hex(32)
        key_id = self._hash_key(new_key)
        self._keys[key_id] = {"label": label, "created": time.time(), "scope": scope}
        self._persist()
        self._log_event("issue", key_id, {"label": label, "scope": scope})
        return new_key, key_id

    def revoke_key(self, key_id: str) -> bool:
        if key_id in self._keys:
            del self._keys[key_id]
            self._persist()
            self._log_event("revoke", key_id)
            return True
        return False

    def rotate_key(self, key_id: str, label: str = "", scope: str = "user") -> Tuple[str, str]:
        """
        Rotate a key by revoking the old key and issuing a new one with the same label/scope.
        Returns plaintext and new key_id.
        """
        if key_id in self._keys:
            self.revoke_key(key_id)
        plaintext, new_id = self.issue_key(label=label, scope=scope)
        self._log_event("rotate", new_id, {"replaced": key_id})
        return plaintext, new_id

    def _log_event(self, action: str, key_id: str, extra: Optional[Dict[str, Any]] = None) -> None:
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

    def get_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        if not os.path.exists(self._audit_path):
            return []
        events: List[Dict[str, Any]] = []
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

    def _emit_security_log(self, event: Dict[str, Any]) -> None:
        try:
            payload = {
                "action": event.get("action"),
                "key_id": event.get("key_id"),
                "scope": event.get("scope", "unknown"),
                "label": event.get("label", ""),
                "timestamp": event.get("timestamp"),
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


class APIAuthManager:
    """API key authentication + rotation helper."""

    def __init__(
        self,
        required: bool = False,
        allowed_keys: Optional[List[str]] = None,
        store: Optional[APIKeyStore] = None,
        admin_keys: Optional[List[str]] = None,
    ) -> None:
        manual_users = [key.strip() for key in (allowed_keys or []) if key.strip()]
        manual_admins = [key.strip() for key in (admin_keys or []) if key.strip()]
        self._manual_admin_hashes = {self._hash_key(key) for key in manual_admins}
        self._manual_hashes = {self._hash_key(key) for key in manual_users} | self._manual_admin_hashes
        self._store = store
        self._store_metadata: Dict[str, Dict[str, Any]] = store.list_keys() if store else {}
        self._store_hash_set = set(self._store_metadata.keys()) if store else set()
        self._store_admin_hashes = {
            key_id for key_id, meta in self._store_metadata.items() if meta.get("scope") == "admin"
        }
        self._required = required

    @classmethod
    def from_config(cls, store: Optional[APIKeyStore] = None) -> "APIAuthManager":
        return cls(
            required=getattr(Config, "API_AUTH_REQUIRED", False),
            allowed_keys=list(getattr(Config, "API_AUTH_KEYS", [])),
            admin_keys=list(getattr(Config, "API_ADMIN_KEYS", [])),
            store=store,
        )

    @staticmethod
    def _hash_key(key: str) -> str:
        return hashlib.sha256(key.encode("utf-8")).hexdigest()

    def is_enabled(self) -> bool:
        return self._required

    def _extract_key(self, request: Request) -> Optional[str]:
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

    def authorize(self, request: Request) -> Tuple[bool, Optional[str]]:
        if not self.is_enabled():
            return True, None

        key = self._extract_key(request)
        if not key:
            return False, "API key missing or invalid"

        hashed = self._hash_key(key)
        if hashed in self._manual_hashes or hashed in self._store_hash_set:
            return True, None
        return False, "API key missing or invalid"

    def authorize_admin(self, request: Request) -> Tuple[bool, Optional[str]]:
        key = self._extract_admin_token(request)
        if not key:
            return False, "Admin token missing"
        hashed = self._hash_key(key)
        if hashed in self._manual_admin_hashes or hashed in self._store_admin_hashes:
            return True, None
        return False, "Admin token invalid"

    def refresh_from_store(self) -> None:
        if self._store:
            self._store_metadata = self._store.list_keys()
            self._store_hash_set = set(self._store_metadata.keys())
            self._store_admin_hashes = {
                key_id for key_id, meta in self._store_metadata.items() if meta.get("scope") == "admin"
            }

    def list_key_metadata(self) -> Dict[str, Any]:
        return {
            "manual_keys": len(self._manual_hashes),
            "manual_admin_keys": len(self._manual_admin_hashes),
            "store": self._store_metadata if self._store else {},
        }

    def issue_key(self, label: str = "", scope: str = "user") -> Tuple[str, str]:
        if not self._store:
            raise ValueError("API key store not configured")
        plaintext, key_id = self._store.issue_key(label=label, scope=scope)
        self.refresh_from_store()
        return plaintext, key_id

    def revoke_key(self, key_id: str) -> bool:
        if not self._store:
            raise ValueError("API key store not configured")
        removed = self._store.revoke_key(key_id)
        self.refresh_from_store()
        return removed

    def rotate_key(self, key_id: str, label: str = "", scope: str = "user") -> Tuple[str, str]:
        if not self._store:
            raise ValueError("API key store not configured")
        new_plain, new_id = self._store.rotate_key(key_id, label=label, scope=scope)
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

    def _extract_admin_token(self, request: Request) -> Optional[str]:
        token = request.headers.get("X-Admin-Token")
        if token:
            return token.strip()
        auth = request.headers.get("Authorization", "").strip()
        if auth.lower().startswith("admin "):
            return auth.split(" ", 1)[1].strip()
        return None


class JWTAuthManager:
    """JWT-based authentication with token expiry, refresh, and blacklist.

    Implements Task 64: JWT Token Expiry with production-grade security features.
    """

    def __init__(
        self,
        secret_key: str,
        token_expiry_hours: int = 1,
        refresh_expiry_days: int = 30,
        algorithm: str = "HS256",
        clock_skew_seconds: int = 30
    ):
        """Initialize JWT authentication manager.

        Args:
            secret_key: Secret key for signing JWT tokens
            token_expiry_hours: Access token expiry in hours (default: 1)
            refresh_expiry_days: Refresh token expiry in days (default: 30)
            algorithm: JWT signing algorithm (default: HS256)
            clock_skew_seconds: Clock skew tolerance in seconds (default: 30)
        """
        if not jwt:
            raise ImportError("PyJWT library is required for JWT authentication")

        self.secret_key = secret_key
        self.token_expiry = timedelta(hours=token_expiry_hours)
        self.refresh_expiry = timedelta(days=refresh_expiry_days)
        self.algorithm = algorithm
        self.clock_skew = timedelta(seconds=clock_skew_seconds)
        self.blacklist: Set[str] = set()

    def generate_token(self, user_id: str, scope: str = "user") -> Tuple[str, str]:
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

    def validate_token(self, token: str, remote_addr: Optional[str] = None) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Validate JWT token with expiration check.

        Security features:
        - Explicit expiration verification (verify_exp=True)
        - Clock skew tolerance to handle minor time drift
        - Required claims validation (exp, sub, iat)
        - Signature verification
        - Blacklist checking for revoked tokens

        Args:
            token: JWT token to validate
            remote_addr: Remote IP address for security logging (optional)

        Returns:
            Tuple of (is_valid, payload, error_message)
        """
        # Check blacklist first (fast path for revoked tokens)
        if token in self.blacklist:
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

    def refresh_access_token(self, refresh_token: str) -> Tuple[bool, Optional[str], Optional[str]]:
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

        Args:
            token: JWT token to revoke
        """
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

        In production, use Redis with TTL or scheduled cleanup.
        For now, we check each blacklisted token and remove if expired.

        Returns:
            Number of tokens removed
        """
        removed = 0
        expired_tokens = set()

        for token in self.blacklist:
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
            except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as e:
                # Any other error (invalid token, decode error), keep in blacklist to be safe
                logger.debug(
                    "Token cleanup check failed: %s - keeping in blacklist",
                    type(e).__name__,
                    extra={"event": "api_auth.jwt_cleanup_check_failed"}
                )

        self.blacklist -= expired_tokens

        if removed > 0:
            log_security_event(
                "jwt_blacklist_cleanup",
                {
                    "removed_count": removed,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
                severity="INFO",
            )

        return removed

    def extract_token_from_request(self, request: Request) -> Optional[str]:
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

    def authorize_request(self, request: Request, required_scope: Optional[str] = None) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
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

        Returns:
            Number of tokens in blacklist
        """
        return len(self.blacklist)
