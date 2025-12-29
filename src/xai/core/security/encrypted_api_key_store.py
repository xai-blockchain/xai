"""
Encrypted API Key Store

Enhanced version of APIKeyStore with Fernet encryption support for reversible key storage.
Maintains backward compatibility with legacy hashed keys.

Key Features:
- Fernet symmetric encryption for new keys
- Backward compatibility with SHA256-hashed keys
- Multi-version encryption key support for rotation
- Constant-time comparison for key validation
- Migration utility for converting hashed keys to encrypted keys
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import secrets
import time
import uuid
from typing import Any

logger = logging.getLogger(__name__)

try:
    from xai.core.security.api_key_encryption import APIKeyEncryptionManager
except ImportError:
    APIKeyEncryptionManager = None  # type: ignore


class EncryptedAPIKeyStore:
    """
    API key store with Fernet encryption support.

    Storage Format:
    - Legacy keys: SHA256 hash as key_id, no encrypted_key field
    - New keys: UUID as key_id, encrypted_key field contains Fernet-encrypted API key
    """

    def __init__(
        self,
        path: str,
        default_ttl_days: int = 90,
        max_ttl_days: int = 365,
        allow_permanent: bool = False,
        encryption_key: str | None = None,
        enable_encryption: bool = True,
    ) -> None:
        """Initialize encrypted API key store.

        Args:
            path: Path to key storage file
            default_ttl_days: Default TTL for new keys (days)
            max_ttl_days: Maximum allowed TTL (days)
            allow_permanent: Allow permanent (non-expiring) keys
            encryption_key: Encryption key for Fernet (loaded from env if not provided)
            enable_encryption: Enable encryption for new keys (default: True)
        """
        self.path = path
        self._audit_path = f"{path}.log"
        self._keys: dict[str, dict[str, Any]] = {}
        self._default_ttl_seconds = max(default_ttl_days, 1) * 86400
        self._max_ttl_seconds = max(max_ttl_days, default_ttl_days) * 86400
        self._allow_permanent = allow_permanent

        # Initialize encryption manager
        if APIKeyEncryptionManager is None or not enable_encryption:
            self._encryption_mgr = None
            logger.warning("API key encryption disabled (cryptography library not available or disabled)")
        else:
            self._encryption_mgr = APIKeyEncryptionManager(
                encryption_key=encryption_key,
                enable_encryption=enable_encryption,
            )

        # Load existing keys
        self._load()

    @property
    def audit_log_path(self) -> str:
        """Get path to audit log file."""
        return self._audit_path

    @property
    def encryption_enabled(self) -> bool:
        """Check if encryption is enabled."""
        return self._encryption_mgr is not None and self._encryption_mgr.is_enabled()

    # -------------------------------------------------------------------------
    # Key Management
    # -------------------------------------------------------------------------

    def issue_key(
        self,
        label: str = "",
        scope: str = "user",
        plaintext: str | None = None,
        ttl_seconds: int | None = None,
        permanent: bool = False,
        use_encryption: bool | None = None,
    ) -> tuple[str, str]:
        """Issue a new API key.

        Args:
            label: Human-friendly label for tracking
            scope: Key scope (user, admin, operator, auditor)
            plaintext: Use specific API key (for bootstrap/migration)
            ttl_seconds: TTL override in seconds
            permanent: Issue permanent key (if allowed)
            use_encryption: Force encryption on/off (default: auto based on availability)

        Returns:
            Tuple of (plaintext_key, key_id)
        """
        # Generate or use provided key
        new_key = plaintext or secrets.token_hex(32)

        # Determine if encryption should be used
        should_encrypt = use_encryption if use_encryption is not None else self.encryption_enabled

        # Generate key metadata
        created = time.time()
        expires_at = self._compute_expires_at(created, ttl_seconds, permanent)

        if should_encrypt and self._encryption_mgr:
            # Use UUID for encrypted keys
            key_id = str(uuid.uuid4())
            encrypted_key = self._encryption_mgr.encrypt(new_key)

            self._keys[key_id] = {
                "key_id": key_id,
                "label": label,
                "created": created,
                "scope": scope,
                "expires_at": expires_at,
                "permanent": expires_at is None,
                "encrypted_key": encrypted_key,
                "encryption_version": self._encryption_mgr.get_current_version(),
                "storage_type": "encrypted",
            }
        else:
            # Use hash for legacy keys
            key_id = self._hash_key(new_key)

            self._keys[key_id] = {
                "key_id": key_id,
                "label": label,
                "created": created,
                "scope": scope,
                "expires_at": expires_at,
                "permanent": expires_at is None,
                "storage_type": "hashed",
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
                "storage_type": self._keys[key_id]["storage_type"],
            },
        )

        return new_key, key_id

    def revoke_key(self, key_id: str) -> bool:
        """Revoke an API key by ID.

        Args:
            key_id: Key ID to revoke

        Returns:
            True if key was revoked, False if not found
        """
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
        """Rotate a key by revoking the old key and issuing a new one.

        Args:
            key_id: Old key ID to rotate
            label: Label for new key
            scope: Scope for new key
            ttl_seconds: TTL for new key
            permanent: Issue permanent key

        Returns:
            Tuple of (new_plaintext, new_key_id)
        """
        if key_id in self._keys:
            self.revoke_key(key_id)

        plaintext, new_id = self.issue_key(
            label=label,
            scope=scope,
            ttl_seconds=ttl_seconds,
            permanent=permanent,
        )

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

    def validate_key(self, plaintext: str) -> tuple[bool, str | None, dict[str, Any] | None]:
        """Validate an API key and return metadata.

        Args:
            plaintext: API key to validate

        Returns:
            Tuple of (is_valid, key_id, metadata)
        """
        # Try encrypted keys first (faster)
        if self._encryption_mgr:
            for key_id, metadata in self._keys.items():
                if metadata.get("storage_type") == "encrypted":
                    encrypted_key = metadata.get("encrypted_key")
                    if encrypted_key:
                        decrypted = self._encryption_mgr.decrypt(encrypted_key)
                        if decrypted and self._constant_time_compare(decrypted, plaintext):
                            # Check expiration
                            if self._is_expired(metadata):
                                return False, key_id, metadata
                            return True, key_id, metadata

        # Try hashed keys (legacy)
        key_hash = self._hash_key(plaintext)
        if key_hash in self._keys:
            metadata = self._keys[key_hash]
            # Check expiration
            if self._is_expired(metadata):
                return False, key_hash, metadata
            return True, key_hash, metadata

        # Not found
        return False, None, None

    def migrate_to_encrypted(self, plaintext: str) -> tuple[bool, str | None]:
        """Migrate a hashed key to encrypted storage.

        Args:
            plaintext: Plaintext API key to migrate

        Returns:
            Tuple of (success, new_key_id or error_message)
        """
        if not self.encryption_enabled:
            return False, "Encryption not available"

        # Find the hashed key
        key_hash = self._hash_key(plaintext)
        if key_hash not in self._keys:
            return False, "Key not found"

        metadata = self._keys[key_hash]

        # Create new encrypted key with same metadata
        new_key_id = str(uuid.uuid4())
        encrypted_key = self._encryption_mgr.encrypt(plaintext)  # type: ignore

        self._keys[new_key_id] = {
            "key_id": new_key_id,
            "label": metadata.get("label", ""),
            "created": metadata.get("created", time.time()),
            "scope": metadata.get("scope", "user"),
            "expires_at": metadata.get("expires_at"),
            "permanent": metadata.get("permanent", False),
            "encrypted_key": encrypted_key,
            "encryption_version": self._encryption_mgr.get_current_version(),  # type: ignore
            "storage_type": "encrypted",
            "migrated_from": key_hash,
        }

        # Remove old hashed key
        del self._keys[key_hash]
        self._persist()

        self._log_event(
            "migrate",
            new_key_id,
            {
                "from_key_id": key_hash,
                "scope": metadata.get("scope"),
                "storage_type": "encrypted",
            },
        )

        return True, new_key_id

    # -------------------------------------------------------------------------
    # Query Methods
    # -------------------------------------------------------------------------

    def list_keys(self) -> dict[str, dict[str, Any]]:
        """List all keys with computed expiration status.

        Returns:
            Dictionary of key_id -> metadata (without encrypted_key field)
        """
        now = time.time()
        result: dict[str, dict[str, Any]] = {}

        for key_id, metadata in self._keys.items():
            copied = dict(metadata)
            copied["expired"] = self._is_expired(metadata, now)
            # Remove encrypted_key from response for security
            copied.pop("encrypted_key", None)
            result[key_id] = copied

        return result

    def get_key_metadata(self, key_id: str) -> dict[str, Any] | None:
        """Get metadata for a specific key.

        Args:
            key_id: Key ID to lookup

        Returns:
            Key metadata or None if not found
        """
        if key_id not in self._keys:
            return None

        metadata = dict(self._keys[key_id])
        metadata["expired"] = self._is_expired(metadata)
        # Remove encrypted_key from response
        metadata.pop("encrypted_key", None)

        return metadata

    def get_statistics(self) -> dict[str, Any]:
        """Get statistics about key storage.

        Returns:
            Dictionary with storage statistics
        """
        total_keys = len(self._keys)
        encrypted_keys = sum(1 for m in self._keys.values() if m.get("storage_type") == "encrypted")
        hashed_keys = sum(1 for m in self._keys.values() if m.get("storage_type") == "hashed")
        expired_keys = sum(1 for m in self._keys.values() if self._is_expired(m))

        scopes: dict[str, int] = {}
        for metadata in self._keys.values():
            scope = metadata.get("scope", "unknown")
            scopes[scope] = scopes.get(scope, 0) + 1

        return {
            "total_keys": total_keys,
            "encrypted_keys": encrypted_keys,
            "hashed_keys": hashed_keys,
            "expired_keys": expired_keys,
            "active_keys": total_keys - expired_keys,
            "by_scope": scopes,
            "encryption_enabled": self.encryption_enabled,
            "encryption_version": self._encryption_mgr.get_current_version() if self._encryption_mgr else None,
        }

    def get_events(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get recent audit events.

        Args:
            limit: Maximum number of events to return

        Returns:
            List of audit events (most recent last)
        """
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

    # -------------------------------------------------------------------------
    # Internal Methods
    # -------------------------------------------------------------------------

    def _load(self) -> None:
        """Load persisted API keys from disk."""
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as handle:
                    data = json.load(handle)
                    if isinstance(data, dict):
                        self._keys = data
                    else:
                        self._keys = {}
            except (OSError, json.JSONDecodeError) as e:
                logger.error("Failed to load API keys from %s: %s", self.path, e)
                self._keys = {}

        # Hydrate metadata for keys loaded from disk
        self._hydrate_metadata()

    def _persist(self) -> None:
        """Persist API keys atomically to disk."""
        directory = os.path.dirname(self.path)
        if directory:
            os.makedirs(directory, exist_ok=True)

        tmp_path = f"{self.path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as handle:
            json.dump(self._keys, handle, indent=2)

        os.replace(tmp_path, self.path)

    def _hydrate_metadata(self) -> None:
        """Ensure keys loaded from disk contain required metadata fields."""
        changed = False
        now = time.time()

        for key_id, metadata in self._keys.items():
            # Ensure created timestamp
            if "created" not in metadata or not isinstance(metadata["created"], (int, float)):
                metadata["created"] = now
                changed = True

            # Ensure expires_at
            if "expires_at" not in metadata:
                created = metadata.get("created", now)
                metadata["expires_at"] = self._compute_expires_at(
                    created,
                    None,
                    metadata.get("permanent", False),
                )
                changed = True

            # Ensure permanent flag
            if "permanent" not in metadata:
                metadata["permanent"] = metadata.get("expires_at") is None
                changed = True

            # Detect storage type if not specified
            if "storage_type" not in metadata:
                if "encrypted_key" in metadata:
                    metadata["storage_type"] = "encrypted"
                else:
                    metadata["storage_type"] = "hashed"
                changed = True

            # Ensure key_id field
            if "key_id" not in metadata:
                metadata["key_id"] = key_id
                changed = True

        if changed:
            self._persist()

    def _compute_expires_at(
        self,
        created: float,
        ttl_seconds: int | None,
        permanent: bool,
    ) -> float | None:
        """Compute expiration timestamp.

        Args:
            created: Creation timestamp
            ttl_seconds: TTL override in seconds
            permanent: Issue permanent key

        Returns:
            Expiration timestamp or None for permanent keys
        """
        if permanent:
            if not self._allow_permanent:
                raise ValueError("Permanent API keys are disabled")
            return None

        ttl = self._default_ttl_seconds if ttl_seconds is None else int(ttl_seconds)

        if ttl <= 0:
            raise ValueError("TTL must be positive")

        ttl = min(ttl, self._max_ttl_seconds)

        return created + ttl

    @staticmethod
    def _is_expired(metadata: dict[str, Any], now: float | None = None) -> bool:
        """Check if key has expired.

        Args:
            metadata: Key metadata
            now: Current timestamp (default: time.time())

        Returns:
            True if expired
        """
        expires_at = metadata.get("expires_at")
        if expires_at is None:
            return False

        try:
            expiry = float(expires_at)
        except (TypeError, ValueError):
            return True

        return (now or time.time()) >= expiry

    @staticmethod
    def _hash_key(key: str) -> str:
        """Generate SHA256 hash of API key (for legacy compatibility).

        Args:
            key: API key to hash

        Returns:
            SHA256 hexdigest
        """
        return hashlib.sha256(key.encode("utf-8")).hexdigest()

    @staticmethod
    def _constant_time_compare(a: str, b: str) -> bool:
        """Constant-time string comparison to prevent timing attacks.

        Args:
            a: First string
            b: Second string

        Returns:
            True if strings are equal
        """
        return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))

    def _log_event(
        self,
        action: str,
        key_id: str,
        extra: dict[str, Any] | None = None,
    ) -> None:
        """Append audit log entry.

        Args:
            action: Action type (issue, revoke, rotate, migrate)
            key_id: Key ID involved
            extra: Additional metadata
        """
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

        # Emit security event if available
        try:
            from xai.core.security.security_validation import log_security_event

            severity = "WARNING" if action in ("revoke", "rotate") else "INFO"
            log_security_event(f"api_key_{action}", event, severity=severity)
        except (ImportError, RuntimeError, ValueError, TypeError, KeyError):
            # Security logging optional
            pass
