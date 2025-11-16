from cryptography.hazmat.primitives import osrandom
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional


class KeyRotationManager:
    def __init__(self, key_length_bytes: int = 32, rotation_interval_days: int = 30):
        if not isinstance(key_length_bytes, int) or key_length_bytes <= 0:
            raise ValueError("Key length must be a positive integer.")
        if not isinstance(rotation_interval_days, int) or rotation_interval_days <= 0:
            raise ValueError("Rotation interval must be a positive integer.")

        self.key_length_bytes = key_length_bytes
        self.rotation_interval_days = rotation_interval_days
        self.active_key: Optional[bytes] = None
        self.active_key_id: Optional[str] = None
        self.last_rotation_timestamp: Optional[int] = None
        # Stores historical keys: {key_id: {"key": bytes, "rotation_timestamp": int, "deactivation_timestamp": int}}
        self.historical_keys: Dict[str, Dict[str, Any]] = {}
        self._key_id_counter = 0

        # Initialize with a first key
        self._generate_new_key()

    def _generate_new_key_bytes(self) -> bytes:
        """Simulates secure generation of a new cryptographic key."""
        return osrandom.urandom(self.key_length_bytes)

    def _generate_key_id(self) -> str:
        self._key_id_counter += 1
        return f"key_{self._key_id_counter}"

    def _generate_new_key(self):
        """Generates a new key and sets it as active."""
        new_key = self._generate_new_key_bytes()
        new_key_id = self._generate_key_id()
        current_timestamp = int(time.time())

        if self.active_key:
            # Move current active key to historical
            self.historical_keys[self.active_key_id] = {
                "key": self.active_key,
                "rotation_timestamp": self.last_rotation_timestamp,
                "deactivation_timestamp": current_timestamp,
            }
            print(f"Archived old key: {self.active_key_id}")

        self.active_key = new_key
        self.active_key_id = new_key_id
        self.last_rotation_timestamp = current_timestamp
        print(
            f"New active key generated: {self.active_key_id} at {datetime.fromtimestamp(current_timestamp)}"
        )

    def rotate_key(self, force: bool = False):
        """
        Rotates the active key if the rotation interval has passed or if forced.
        """
        current_timestamp = int(time.time())
        if force or (
            self.last_rotation_timestamp is None
            or (current_timestamp - self.last_rotation_timestamp)
            >= (self.rotation_interval_days * 24 * 3600)
        ):
            print(f"Initiating key rotation...")
            self._generate_new_key()
        else:
            next_rotation_time = self.last_rotation_timestamp + (
                self.rotation_interval_days * 24 * 3600
            )
            print(
                f"Key rotation not due yet. Next rotation scheduled for: {datetime.fromtimestamp(next_rotation_time)}"
            )

    def get_active_key(self) -> bytes:
        """Returns the current active key."""
        if not self.active_key:
            raise RuntimeError("No active key available. Initialize KeyRotationManager first.")
        return self.active_key

    def get_key_by_id(self, key_id: str) -> Optional[bytes]:
        """Retrieves a key (active or historical) by its ID."""
        if key_id == self.active_key_id:
            return self.active_key

        historical_entry = self.historical_keys.get(key_id)
        if historical_entry:
            return historical_entry["key"]
        return None

    def get_historical_keys(self) -> Dict[str, Dict[str, Any]]:
        """Returns all historical keys."""
        return self.historical_keys


# Example Usage (for testing purposes)
if __name__ == "__main__":
    # Set a short rotation interval for demonstration
    manager = KeyRotationManager(rotation_interval_days=1)  # Rotate every day

    print(f"Initial active key ID: {manager.active_key_id}")
    print(f"Last rotation: {datetime.fromtimestamp(manager.last_rotation_timestamp)}")

    print("\n--- Attempting rotation before due ---")
    manager.rotate_key()
    print(f"Active key ID: {manager.active_key_id}")

    print("\n--- Forcing rotation ---")
    manager.rotate_key(force=True)
    print(f"Active key ID: {manager.active_key_id}")
    print(f"Historical keys: {manager.get_historical_keys()}")

    # Simulate passage of time for automated rotation
    print("\n--- Simulating time passage for automated rotation ---")
    time.sleep(2)  # Simulate 2 days passing (since interval is 1 day)
    manager.rotate_key()
    print(f"Active key ID: {manager.active_key_id}")
    print(f"Historical keys: {manager.get_historical_keys()}")

    # Retrieve a historical key
    first_key_id = list(manager.historical_keys.keys())[0]
    retrieved_key = manager.get_key_by_id(first_key_id)
    print(f"\nRetrieved historical key {first_key_id}: {retrieved_key}")
    print(f"Current active key: {manager.get_active_key()}")
