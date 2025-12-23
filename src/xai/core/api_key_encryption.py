"""
API Key Encryption Module

Provides Fernet-based encryption for reversible API key storage with key rotation support.
This module enhances APIKeyStore to support encrypted storage instead of one-way hashing.

Security Features:
- Fernet symmetric encryption (AES-128-CBC + HMAC-SHA256)
- Multi-version key support for rotation
- Constant-time comparison for key validation
- Secure key derivation from secrets
- No plaintext logging

Key Rotation Process:
1. Generate new encryption key (version N+1)
2. Set XAI_API_KEY_ENCRYPTION_KEY_VN+1=<old_key>
3. Set XAI_API_KEY_ENCRYPTION_KEY=<new_key>
4. Restart node - old keys still decrypt, new keys use new encryption
5. Migrate old keys to new encryption version (optional)
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import os
import secrets
from typing import Any

try:
    from cryptography.fernet import Fernet, InvalidToken
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
except ImportError:
    Fernet = None  # type: ignore
    InvalidToken = None  # type: ignore

logger = logging.getLogger(__name__)

class APIKeyEncryptionManager:
    """Manages Fernet encryption for API keys with versioning and rotation support."""

    def __init__(
        self,
        encryption_key: str | None = None,
        enable_encryption: bool = True,
    ) -> None:
        """Initialize encryption manager.

        Args:
            encryption_key: Base64-encoded Fernet key (or will be loaded from env)
            enable_encryption: Enable Fernet encryption (default: True)
        """
        self._enable_encryption = enable_encryption and Fernet is not None
        self._encryption_keys: list[tuple[int, Any]] = []  # [(version, Fernet), ...]
        self._current_encryption_version = 1

        if self._enable_encryption:
            self._init_encryption_keys(encryption_key)

    def _init_encryption_keys(self, provided_key: str | None = None) -> None:
        """Initialize encryption keys from environment or provided key.

        Supports multiple keys for rotation:
        - XAI_API_KEY_ENCRYPTION_KEY: Current key (version 1)
        - XAI_API_KEY_ENCRYPTION_KEY_V2, V3, etc.: Rotated keys
        """
        if Fernet is None:
            logger.warning("cryptography library not available, encryption disabled")
            self._enable_encryption = False
            return

        # Load current encryption key (version 1)
        current_key = provided_key or os.environ.get("XAI_API_KEY_ENCRYPTION_KEY")

        if not current_key:
            # Generate new key and warn user to save it
            current_key = Fernet.generate_key().decode("utf-8")
            logger.warning(
                "No encryption key provided, generated new key. "
                "Save this key to XAI_API_KEY_ENCRYPTION_KEY env var: %s",
                current_key[:16] + "..." + current_key[-8:],  # Partial display for logging
            )

        try:
            # Add current key (version 1)
            key_bytes = current_key.encode() if isinstance(current_key, str) else current_key
            self._encryption_keys.append((1, Fernet(key_bytes)))
            self._current_encryption_version = 1
            logger.info("Initialized API key encryption (version 1)")

            # Load rotated keys for backward compatibility (v2-v10)
            for i in range(2, 11):
                old_key = os.environ.get(f"XAI_API_KEY_ENCRYPTION_KEY_V{i}")
                if old_key:
                    try:
                        self._encryption_keys.append((i, Fernet(old_key.encode())))
                        logger.info("Loaded encryption key version %d for rotation support", i)
                    except (ValueError, TypeError) as e:
                        logger.error("Invalid encryption key v%d: %s", i, e)

        except (ValueError, TypeError) as e:
            logger.error("Failed to initialize encryption: %s", e)
            self._enable_encryption = False

    @staticmethod
    def generate_key() -> str:
        """Generate a new Fernet encryption key.

        Returns:
            Base64-encoded Fernet key
        """
        if Fernet is None:
            raise RuntimeError("cryptography library not available")
        return Fernet.generate_key().decode("utf-8")

    @staticmethod
    def derive_key_from_secret(secret: str, salt: bytes | None = None) -> str:
        """Derive a Fernet key from a secret using PBKDF2.

        Args:
            secret: User-provided secret (passphrase)
            salt: Optional salt (default: XAI-specific salt)

        Returns:
            Base64-encoded Fernet key
        """
        if Fernet is None:
            raise RuntimeError("cryptography library not available")

        if salt is None:
            salt = b"xai_api_key_encryption_salt_v1"

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,  # 256 bits
            salt=salt,
            iterations=480000,  # OWASP recommended (2023)
            backend=default_backend(),
        )

        key_material = kdf.derive(secret.encode("utf-8"))
        return base64.urlsafe_b64encode(key_material).decode("utf-8")

    def is_enabled(self) -> bool:
        """Check if encryption is enabled."""
        return self._enable_encryption

    def encrypt(self, plaintext: str, version: int | None = None) -> str:
        """Encrypt plaintext using Fernet with versioning.

        Args:
            plaintext: API key to encrypt
            version: Encryption version to use (default: current version)

        Returns:
            Encrypted data in format "version:ciphertext"
        """
        if not self._enable_encryption or not self._encryption_keys:
            raise ValueError("Encryption not available")

        use_version = version or self._current_encryption_version
        fernet = None

        for ver, f in self._encryption_keys:
            if ver == use_version:
                fernet = f
                break

        if fernet is None:
            raise ValueError(f"Encryption key version {use_version} not found")

        encrypted = fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")
        return f"{use_version}:{encrypted}"

    def decrypt(self, encrypted_data: str) -> str | None:
        """Decrypt ciphertext, trying all available key versions.

        Args:
            encrypted_data: Encrypted data in format "version:ciphertext" or "ciphertext"

        Returns:
            Decrypted plaintext or None if decryption fails
        """
        if not self._enable_encryption or not self._encryption_keys:
            return None

        # Parse version prefix
        if ":" in encrypted_data:
            version_str, ciphertext = encrypted_data.split(":", 1)
            try:
                requested_version = int(version_str)
            except ValueError:
                # Colon but not version:data format, treat as legacy
                requested_version = None
                ciphertext = encrypted_data
        else:
            # No version prefix, try all keys
            requested_version = None
            ciphertext = encrypted_data

        # Try requested version first, then all versions
        versions_to_try: list[int] = []
        if requested_version:
            versions_to_try.append(requested_version)

        # Add all other versions
        for v, _ in self._encryption_keys:
            if v not in versions_to_try:
                versions_to_try.append(v)

        # Attempt decryption with each version
        for version in versions_to_try:
            for ver, fernet in self._encryption_keys:
                if ver == version:
                    try:
                        decrypted = fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
                        return decrypted
                    except (InvalidToken, ValueError, TypeError, AttributeError):
                        # Try next version
                        continue
                    except Exception as e:
                        logger.debug("Decryption failed with key v%d: %s", version, type(e).__name__)
                        continue

        # All versions failed
        logger.error("Failed to decrypt API key with any available key version")
        return None

    def re_encrypt(self, encrypted_data: str, target_version: int | None = None) -> str | None:
        """Re-encrypt data with a different key version (for migration).

        Args:
            encrypted_data: Currently encrypted data
            target_version: Target encryption version (default: current version)

        Returns:
            Re-encrypted data or None if decryption fails
        """
        # Decrypt with old key
        plaintext = self.decrypt(encrypted_data)
        if plaintext is None:
            return None

        # Encrypt with new key
        use_version = target_version or self._current_encryption_version
        return self.encrypt(plaintext, version=use_version)

    def get_current_version(self) -> int:
        """Get current encryption version."""
        return self._current_encryption_version

    def get_available_versions(self) -> list[int]:
        """Get list of available encryption key versions."""
        return [v for v, _ in self._encryption_keys]

    @staticmethod
    def constant_time_compare(a: str, b: str) -> bool:
        """Constant-time string comparison to prevent timing attacks.

        Args:
            a: First string
            b: Second string

        Returns:
            True if strings are equal
        """
        return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))

    @staticmethod
    def hash_key(key: str) -> str:
        """Generate SHA256 hash of API key (for legacy compatibility).

        Args:
            key: API key to hash

        Returns:
            SHA256 hexdigest
        """
        return hashlib.sha256(key.encode("utf-8")).hexdigest()
