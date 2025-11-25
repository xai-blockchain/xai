import hashlib
from src.xai.security.csprng import CSPRNG
from typing import Tuple


class SaltedHashManager:
    def __init__(self, salt_length_bytes: int = 16):
        if not isinstance(salt_length_bytes, int) or salt_length_bytes <= 0:
            raise ValueError("Salt length must be a positive integer.")
        self.salt_length_bytes = salt_length_bytes
        self.csprng = CSPRNG()
        print(f"SaltedHashManager initialized with salt length: {self.salt_length_bytes} bytes.")

    def _generate_salt(self) -> bytes:
        """Generates a cryptographically secure random salt."""
        return self.csprng.generate_bytes(self.salt_length_bytes)

    def hash_with_salt(self, data: str) -> Tuple[str, str]:
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


# Example Usage (for testing purposes)
if __name__ == "__main__":
    hash_manager = SaltedHashManager(salt_length_bytes=16)

    user_password = "mySuperSecretPassword123!"
    another_password = "mySuperSecretPassword123!"  # Same password
    different_password = "aDifferentPassword456"

    print("\n--- Hashing Passwords with Unique Salts ---")
    hash1, salt1 = hash_manager.hash_with_salt(user_password)
    print(f"Password: '{user_password}'")
    print(f"Salt 1: {salt1}")
    print(f"Hash 1: {hash1}")

    hash2, salt2 = hash_manager.hash_with_salt(another_password)
    print(f"\nPassword: '{another_password}' (same as above)")
    print(f"Salt 2: {salt2}")
    print(f"Hash 2: {hash2}")
    print(f"Are hash1 and hash2 different (expected True)? {hash1 != hash2}")

    hash3, salt3 = hash_manager.hash_with_salt(different_password)
    print(f"\nPassword: '{different_password}'")
    print(f"Salt 3: {salt3}")
    print(f"Hash 3: {hash3}")

    print("\n--- Verifying Hashes ---")
    # Correct verification
    is_valid_1 = hash_manager.verify_hash(user_password, hash1, salt1)
    print(f"Verify '{user_password}' against Hash 1 (expected True): {is_valid_1}")

    # Verify same password with its own salt
    is_valid_2 = hash_manager.verify_hash(another_password, hash2, salt2)
    print(f"Verify '{another_password}' against Hash 2 (expected True): {is_valid_2}")

    # Incorrect verification (wrong password)
    is_invalid_1 = hash_manager.verify_hash("wrong_password", hash1, salt1)
    print(f"Verify 'wrong_password' against Hash 1 (expected False): {is_invalid_1}")

    # Incorrect verification (wrong salt)
    is_invalid_2 = hash_manager.verify_hash(
        user_password, hash1, salt2
    )  # Using salt from another_password
    print(
        f"Verify '{user_password}' against Hash 1 with wrong salt (expected False): {is_invalid_2}"
    )
