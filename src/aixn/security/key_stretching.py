import hashlib
import os
from src.aixn.security.csprng import CSPRNG
from typing import Tuple


class KeyStretchingManager:
    def __init__(self, salt_length_bytes: int = 16, iterations: int = 100000):
        if not isinstance(salt_length_bytes, int) or salt_length_bytes <= 0:
            raise ValueError("Salt length must be a positive integer.")
        if not isinstance(iterations, int) or iterations <= 0:
            raise ValueError("Iterations must be a positive integer.")

        self.salt_length_bytes = salt_length_bytes
        self.iterations = iterations
        self.csprng = CSPRNG()
        print(
            f"KeyStretchingManager initialized with salt length: {self.salt_length_bytes} bytes, iterations: {self.iterations}."
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


# Example Usage (for testing purposes)
if __name__ == "__main__":
    key_stretcher = KeyStretchingManager(salt_length_bytes=16, iterations=150000)

    user_password = "mySecretPassword123!"

    print("\n--- Deriving Key ---")
    derived_key, salt, iterations = key_stretcher.derive_key(user_password)
    print(f"Password: '{user_password}'")
    print(f"Derived Key (hex): {derived_key.hex()}")
    print(f"Salt (hex): {salt.hex()}")
    print(f"Iterations: {iterations}")

    print("\n--- Verifying Key ---")
    # Correct verification
    is_valid_1 = key_stretcher.verify_key(user_password, derived_key, salt, iterations)
    print(f"Verify '{user_password}' (expected True): {is_valid_1}")

    # Incorrect password
    is_invalid_1 = key_stretcher.verify_key("wrong_password", derived_key, salt, iterations)
    print(f"Verify 'wrong_password' (expected False): {is_invalid_1}")

    # Different salt (even with same password, derived key will be different)
    derived_key_2, salt_2, iterations_2 = key_stretcher.derive_key(user_password)
    is_invalid_2 = key_stretcher.verify_key(
        user_password, derived_key_2, salt, iterations
    )  # Using wrong salt
    print(f"Verify '{user_password}' with wrong salt (expected False): {is_invalid_2}")
