"""
Flask Secret Key Manager
Secure persistence and retrieval of Flask secret keys.

Implements:
- Environment variable fallback (XAI_SECRET_KEY)
- Persistent storage in ~/.xai/.secret_key
- Automatic generation with secure defaults
- Proper file permissions (0600)
- Security warnings for auto-generated keys
"""

from __future__ import annotations

import logging
import os
import secrets
from pathlib import Path

logger = logging.getLogger(__name__)

class FlaskSecretManager:
    """Manages Flask secret key persistence and security."""

    def __init__(self, data_dir: str | None = None):
        """
        Initialize secret key manager.

        Args:
            data_dir: Base directory for data storage (default: ~/.xai)
        """
        if data_dir is None:
            data_dir = os.path.expanduser("~/.xai")

        self.data_dir = Path(data_dir)
        self.secret_key_path = self.data_dir / ".secret_key"

        # Ensure data directory exists
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def get_secret_key(self) -> str:
        """
        Get or generate Flask secret key with proper persistence.

        Priority order:
        1. XAI_SECRET_KEY environment variable
        2. Existing .secret_key file
        3. Generate new key and persist to file

        Returns:
            64-character hex secret key

        Raises:
            PermissionError: If unable to set secure file permissions
            IOError: If unable to read/write secret key file
        """
        # Check environment variable first
        env_key = os.environ.get("XAI_SECRET_KEY")
        if env_key:
            logger.info("Using Flask secret key from XAI_SECRET_KEY environment variable")
            return env_key

        # Check for existing secret key file
        if self.secret_key_path.exists():
            try:
                secret_key = self._read_secret_key()
                logger.info("Loaded Flask secret key from %s", self.secret_key_path)
                return secret_key
            except Exception as e:
                logger.warning(
                    "Failed to read secret key from %s: %s. Generating new key.",
                    self.secret_key_path,
                    e
                )

        # Generate new secret key
        secret_key = self._generate_secret_key()

        # Persist to file
        try:
            self._write_secret_key(secret_key)
            logger.warning(
                "Generated new Flask secret key and saved to %s. "
                "For production, set XAI_SECRET_KEY environment variable instead.",
                self.secret_key_path
            )
        except Exception as e:
            logger.error(
                "Failed to persist secret key to %s: %s. "
                "Secret key will be lost on restart!",
                self.secret_key_path,
                e
            )

        return secret_key

    def _generate_secret_key(self) -> str:
        """
        Generate a cryptographically secure secret key.

        Uses secrets.token_hex(32) for 256-bit security.

        Returns:
            64-character hex string
        """
        return secrets.token_hex(32)

    def _read_secret_key(self) -> str:
        """
        Read secret key from file.

        Returns:
            Secret key string

        Raises:
            IOError: If file cannot be read
            ValueError: If file contains invalid data
        """
        with open(self.secret_key_path, 'r', encoding='utf-8') as f:
            secret_key = f.read().strip()

        if not secret_key:
            raise ValueError("Secret key file is empty")

        # Validate hex format (should be 64 chars)
        if len(secret_key) < 32:
            raise ValueError(f"Secret key too short: {len(secret_key)} chars")

        return secret_key

    def _write_secret_key(self, secret_key: str) -> None:
        """
        Write secret key to file with secure permissions.

        Args:
            secret_key: Secret key to persist

        Raises:
            IOError: If file cannot be written
            PermissionError: If permissions cannot be set
        """
        # Write secret key
        with open(self.secret_key_path, 'w', encoding='utf-8') as f:
            f.write(secret_key)

        # Set secure permissions (owner read/write only)
        os.chmod(self.secret_key_path, 0o600)

        logger.info("Secret key saved to %s with permissions 0600", self.secret_key_path)

    def rotate_secret_key(self) -> str:
        """
        Generate and persist a new secret key.

        WARNING: This will invalidate all existing sessions.

        Returns:
            New secret key

        Raises:
            IOError: If unable to write new key
        """
        logger.warning("Rotating Flask secret key - all sessions will be invalidated")

        new_key = self._generate_secret_key()
        self._write_secret_key(new_key)

        return new_key

def get_flask_secret_key(data_dir: str | None = None) -> str:
    """
    Convenience function to get Flask secret key.

    Args:
        data_dir: Base directory for data storage (default: ~/.xai)

    Returns:
        Flask secret key string

    Example:
        >>> secret_key = get_flask_secret_key()
        >>> app.secret_key = secret_key
    """
    manager = FlaskSecretManager(data_dir=data_dir)
    return manager.get_secret_key()
