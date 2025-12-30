"""
Checkpoint Encryption Module

Provides encryption for checkpoint UTXO data at rest.
Uses Fernet (AES-128-CBC + HMAC-SHA256) for authenticated encryption.

SECURITY: This provides defense-in-depth for checkpoint data which contains
complete UTXO snapshots exposing all address balances. While full disk encryption
(FDE) is recommended for production deployments, this adds application-level
protection.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import zlib
from typing import Any

try:
    from cryptography.fernet import Fernet, InvalidToken
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    FERNET_AVAILABLE = True
except ImportError:
    Fernet = None  # type: ignore
    InvalidToken = None  # type: ignore
    FERNET_AVAILABLE = False

logger = logging.getLogger(__name__)


class CheckpointEncryption:
    """Handles encryption/decryption of checkpoint UTXO data."""

    # Environment variable for encryption key
    ENV_KEY = "XAI_CHECKPOINT_ENCRYPTION_KEY"

    def __init__(self, encryption_key: str | None = None, enable_encryption: bool = True):
        """
        Initialize checkpoint encryption.

        Args:
            encryption_key: Base64-encoded Fernet key (or loaded from env)
            enable_encryption: Enable encryption (default: True)
        """
        self._enable = enable_encryption and FERNET_AVAILABLE
        self._fernet: Any = None

        if self._enable:
            self._init_key(encryption_key)

    def _init_key(self, provided_key: str | None = None) -> None:
        """Initialize encryption key from env or provided key."""
        if not FERNET_AVAILABLE:
            logger.warning("cryptography library not available, checkpoint encryption disabled")
            self._enable = False
            return

        key = provided_key or os.environ.get(self.ENV_KEY)

        if not key:
            # Auto-generate key for development, warn user
            key = Fernet.generate_key().decode("utf-8")
            logger.warning(
                "No checkpoint encryption key configured. Generated ephemeral key. "
                "For production, set %s environment variable.",
                self.ENV_KEY,
            )

        try:
            key_bytes = key.encode() if isinstance(key, str) else key
            self._fernet = Fernet(key_bytes)
            logger.info("Checkpoint encryption initialized")
        except (ValueError, TypeError) as e:
            logger.error("Failed to initialize checkpoint encryption: %s", e)
            self._enable = False

    @staticmethod
    def generate_key() -> str:
        """Generate a new Fernet encryption key.

        Returns:
            Base64-encoded Fernet key
        """
        if not FERNET_AVAILABLE:
            raise RuntimeError("cryptography library not available")
        return Fernet.generate_key().decode("utf-8")

    @staticmethod
    def derive_key_from_passphrase(passphrase: str, salt: bytes | None = None) -> str:
        """Derive a Fernet key from a passphrase using PBKDF2.

        Args:
            passphrase: User-provided passphrase
            salt: Optional salt (default: XAI-specific salt)

        Returns:
            Base64-encoded Fernet key
        """
        if not FERNET_AVAILABLE:
            raise RuntimeError("cryptography library not available")

        if salt is None:
            salt = b"xai_checkpoint_encryption_v1"

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,  # OWASP recommended (2023)
            backend=default_backend(),
        )

        key_material = kdf.derive(passphrase.encode("utf-8"))
        return base64.urlsafe_b64encode(key_material).decode("utf-8")

    @property
    def is_enabled(self) -> bool:
        """Check if encryption is enabled."""
        return self._enable and self._fernet is not None

    def encrypt_utxo_snapshot(self, utxo_data: dict[str, Any]) -> dict[str, Any]:
        """
        Encrypt UTXO snapshot data.

        Args:
            utxo_data: UTXO snapshot dictionary

        Returns:
            Dictionary with encrypted UTXO data or original if encryption disabled
        """
        if not self.is_enabled:
            return utxo_data

        try:
            # Serialize to JSON
            json_data = json.dumps(utxo_data, sort_keys=True)

            # Compress before encryption (reduces ciphertext size)
            compressed = zlib.compress(json_data.encode("utf-8"), level=6)

            # Encrypt
            encrypted = self._fernet.encrypt(compressed)

            return {
                "_encrypted": True,
                "_version": 1,
                "_data": encrypted.decode("utf-8"),
            }
        except (ValueError, TypeError, RuntimeError) as e:
            logger.error("Failed to encrypt UTXO snapshot: %s", e)
            return utxo_data

    def decrypt_utxo_snapshot(self, encrypted_data: dict[str, Any]) -> dict[str, Any]:
        """
        Decrypt UTXO snapshot data.

        Args:
            encrypted_data: Encrypted UTXO data dictionary

        Returns:
            Decrypted UTXO snapshot or the input if not encrypted
        """
        # Check if data is encrypted
        if not encrypted_data.get("_encrypted"):
            return encrypted_data

        if not self.is_enabled:
            raise ValueError("Checkpoint contains encrypted data but encryption is disabled")

        try:
            ciphertext = encrypted_data["_data"].encode("utf-8")

            # Decrypt
            compressed = self._fernet.decrypt(ciphertext)

            # Decompress
            json_data = zlib.decompress(compressed).decode("utf-8")

            # Parse JSON
            return json.loads(json_data)
        except (InvalidToken if InvalidToken else Exception) as e:
            raise ValueError(f"Failed to decrypt UTXO snapshot: {e}") from e
        except (zlib.error, json.JSONDecodeError) as e:
            raise ValueError(f"Failed to decompress/parse UTXO snapshot: {e}") from e


# Global singleton instance
_checkpoint_encryption: CheckpointEncryption | None = None


def get_checkpoint_encryption() -> CheckpointEncryption:
    """Get the global checkpoint encryption instance."""
    global _checkpoint_encryption
    if _checkpoint_encryption is None:
        _checkpoint_encryption = CheckpointEncryption()
    return _checkpoint_encryption


def encrypt_utxo_snapshot(utxo_data: dict[str, Any]) -> dict[str, Any]:
    """Convenience function to encrypt UTXO snapshot."""
    return get_checkpoint_encryption().encrypt_utxo_snapshot(utxo_data)


def decrypt_utxo_snapshot(encrypted_data: dict[str, Any]) -> dict[str, Any]:
    """Convenience function to decrypt UTXO snapshot."""
    return get_checkpoint_encryption().decrypt_utxo_snapshot(encrypted_data)
