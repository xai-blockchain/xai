import hashlib
import logging
from typing import Tuple

from src.xai.security.csprng import CSPRNG

logger = logging.getLogger(__name__)

class KeyStretchingManager:
    def __init__(self, salt_length_bytes: int = 16, iterations: int = 100000):
        if not isinstance(salt_length_bytes, int) or salt_length_bytes <= 0:
            raise ValueError("Salt length must be a positive integer.")
        if not isinstance(iterations, int) or iterations <= 0:
            raise ValueError("Iterations must be a positive integer.")

        self.salt_length_bytes = salt_length_bytes
        self.iterations = iterations
        self.csprng = CSPRNG()
        logger.info(
            "KeyStretchingManager initialized",
            extra={
                "event": "key_stretching.init",
                "salt_bytes": self.salt_length_bytes,
                "iterations": self.iterations,
            },
        )

    def _generate_salt(self) -> bytes:
        """Generates a cryptographically secure random salt."""
        return self.csprng.generate_bytes(self.salt_length_bytes)

    def derive_key(self, password: str, salt: bytes = None) -> Tuple[bytes, bytes, int]:
        """
        Derives a cryptographic key from a password using PBKDF2.
        If no salt is provided, a new one is generated.
        Returns the derived key, the salt used, and the iteration count.
        """
        if not isinstance(password, str):
            raise TypeError("Password must be a string.")

        if salt is None:
            salt = self._generate_salt()

        derived_key = hashlib.pbkdf2_hmac(
            "sha256",  # Hash algorithm
            password.encode("utf-8"),  # Password as bytes
            salt,  # Salt as bytes
            self.iterations,  # Number of iterations
            dklen=32,  # Desired length of the derived key (e.g., 32 bytes for 256-bit key)
        )

        return derived_key, salt, self.iterations

    def verify_key(
        self, password: str, stored_derived_key: bytes, stored_salt: bytes, stored_iterations: int
    ) -> bool:
        """
        Verifies if a given password matches a stored derived key using the provided salt and iterations.
        """
        if not isinstance(password, str):
            raise TypeError("Password must be a string.")
        if (
            not isinstance(stored_derived_key, bytes)
            or not isinstance(stored_salt, bytes)
            or not isinstance(stored_iterations, int)
        ):
            raise TypeError("Stored key, salt, and iterations must be of correct types.")

        computed_derived_key = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            stored_salt,
            stored_iterations,
            dklen=len(stored_derived_key),  # Ensure derived key length matches stored
        )

        return computed_derived_key == stored_derived_key


# Example usage is intentionally omitted in production modules.
