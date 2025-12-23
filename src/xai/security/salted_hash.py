from __future__ import annotations

import hashlib
import logging

from src.xai.security.csprng import CSPRNG

logger = logging.getLogger(__name__)

class SaltedHashManager:
    def __init__(self, salt_length_bytes: int = 16):
        if not isinstance(salt_length_bytes, int) or salt_length_bytes <= 0:
            raise ValueError("Salt length must be a positive integer.")
        self.salt_length_bytes = salt_length_bytes
        self.csprng = CSPRNG()
        logger.info(
            "SaltedHashManager initialized",
            extra={"event": "salted_hash.init", "salt_bytes": self.salt_length_bytes},
        )

    def _generate_salt(self) -> bytes:
        """Generates a cryptographically secure random salt."""
        return self.csprng.generate_bytes(self.salt_length_bytes)

    def hash_with_salt(self, data: str) -> tuple[str, str]:
        """
        Hashes the given data with a newly generated unique salt.
        Returns the salted hash (hex string) and the salt (hex string).
        """
        if not isinstance(data, str):
            raise TypeError("Data to hash must be a string.")

        salt = self._generate_salt()
        salted_data = salt + data.encode("utf-8")
        hashed_data = hashlib.sha256(salted_data).hexdigest()

        return hashed_data, salt.hex()

    def verify_hash(self, data: str, stored_hash: str, stored_salt: str) -> bool:
        """
        Verifies if the given data, when salted with the stored salt, matches the stored hash.
        """
        if (
            not isinstance(data, str)
            or not isinstance(stored_hash, str)
            or not isinstance(stored_salt, str)
        ):
            raise TypeError("All inputs must be strings.")

        try:
            salt_bytes = bytes.fromhex(stored_salt)
        except ValueError:
            raise ValueError("Stored salt is not a valid hex string.")

        salted_data = salt_bytes + data.encode("utf-8")
        computed_hash = hashlib.sha256(salted_data).hexdigest()

        return computed_hash == stored_hash

# Example usage is intentionally omitted in production modules.
