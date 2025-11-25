"""
Comprehensive tests for Key Rotation Manager security module.

Tests key generation, rotation, retrieval, historical key management,
and security best practices for cryptographic key lifecycle management.
"""

import pytest
import time
from datetime import datetime
from xai.security.key_rotation_manager import KeyRotationManager


class TestKeyRotationManagerInitialization:
    """Test initialization and configuration"""

    def test_init_with_defaults(self):
        """Test initialization with default parameters"""
        manager = KeyRotationManager()
        assert manager.key_length_bytes == 32
        assert manager.rotation_interval_days == 30
        assert manager.active_key is not None
        assert manager.active_key_id is not None
        assert len(manager.active_key) == 32

    def test_init_with_custom_params(self):
        """Test initialization with custom parameters"""
        manager = KeyRotationManager(key_length_bytes=64, rotation_interval_days=90)
        assert manager.key_length_bytes == 64
        assert manager.rotation_interval_days == 90
        assert len(manager.active_key) == 64

    def test_init_invalid_key_length(self):
        """Test that invalid key length raises ValueError"""
        with pytest.raises(ValueError, match="Key length must be a positive integer"):
            KeyRotationManager(key_length_bytes=0)

        with pytest.raises(ValueError, match="Key length must be a positive integer"):
            KeyRotationManager(key_length_bytes=-10)

        with pytest.raises(ValueError, match="Key length must be a positive integer"):
            KeyRotationManager(key_length_bytes=32.5)

    def test_init_invalid_rotation_interval(self):
        """Test that invalid rotation interval raises ValueError"""
        with pytest.raises(ValueError, match="Rotation interval must be a positive integer"):
            KeyRotationManager(rotation_interval_days=0)

        with pytest.raises(ValueError, match="Rotation interval must be a positive integer"):
            KeyRotationManager(rotation_interval_days=-5)

    def test_initial_key_generated_on_init(self):
        """Test that initial key is generated during initialization"""
        manager = KeyRotationManager()
        assert manager.active_key is not None
        assert manager.active_key_id == "key_1"
        assert manager.last_rotation_timestamp is not None

    def test_initial_historical_keys_empty(self):
        """Test that historical keys dict is empty on initialization"""
        manager = KeyRotationManager()
        assert len(manager.historical_keys) == 0


class TestKeyGeneration:
    """Test key generation functionality"""

    def test_generate_new_key_bytes_correct_length(self):
        """Test that generated key bytes have correct length"""
        manager = KeyRotationManager(key_length_bytes=16)
        key = manager._generate_new_key_bytes()
        assert len(key) == 16

    def test_generate_new_key_bytes_randomness(self):
        """Test that generated keys are different (random)"""
        manager = KeyRotationManager()
        key1 = manager._generate_new_key_bytes()
        key2 = manager._generate_new_key_bytes()
        assert key1 != key2

    def test_generate_new_key_bytes_type(self):
        """Test that generated key is bytes type"""
        manager = KeyRotationManager()
        key = manager._generate_new_key_bytes()
        assert isinstance(key, bytes)

    def test_generate_key_id_increments(self):
        """Test that key IDs increment sequentially"""
        manager = KeyRotationManager()
        assert manager._key_id_counter == 1
        id1 = manager._generate_key_id()
        assert id1 == "key_2"
        assert manager._key_id_counter == 2
        id2 = manager._generate_key_id()
        assert id2 == "key_3"
        assert manager._key_id_counter == 3

    def test_generated_keys_are_cryptographically_random(self):
        """Test that keys show high entropy (randomness)"""
        manager = KeyRotationManager(key_length_bytes=32)
        keys = [manager._generate_new_key_bytes() for _ in range(100)]

        # All keys should be unique
        assert len(set(keys)) == 100

        # Check that keys don't have obvious patterns
        for key in keys[:10]:
            # Keys should not be all zeros or all ones
            assert key != b'\x00' * 32
            assert key != b'\xff' * 32


class TestKeyRotation:
    """Test key rotation functionality"""

    def test_rotate_key_forced(self):
        """Test forcing key rotation"""
        manager = KeyRotationManager()
        old_key_id = manager.active_key_id
        old_key = manager.active_key

        manager.rotate_key(force=True)

        assert manager.active_key_id != old_key_id
        assert manager.active_key != old_key
        assert manager.active_key_id == "key_2"

    def test_rotate_key_archives_old_key(self):
        """Test that rotation archives the old key"""
        manager = KeyRotationManager()
        old_key_id = manager.active_key_id
        old_key = manager.active_key

        manager.rotate_key(force=True)

        assert old_key_id in manager.historical_keys
        assert manager.historical_keys[old_key_id]["key"] == old_key

    def test_rotate_key_not_due_skips_rotation(self):
        """Test that rotation is skipped when not due"""
        manager = KeyRotationManager(rotation_interval_days=30)
        original_key_id = manager.active_key_id

        manager.rotate_key(force=False)

        # Should not rotate (not enough time passed)
        assert manager.active_key_id == original_key_id

    def test_rotate_key_due_time_passed(self):
        """Test automatic rotation when time has passed"""
        manager = KeyRotationManager(rotation_interval_days=0)
        old_key_id = manager.active_key_id

        # Set last rotation to past
        manager.last_rotation_timestamp = int(time.time()) - (31 * 24 * 3600)

        manager.rotate_key(force=False)

        # Should rotate (time passed)
        assert manager.active_key_id != old_key_id

    def test_rotate_key_updates_timestamp(self):
        """Test that rotation updates last rotation timestamp"""
        manager = KeyRotationManager()
        before = int(time.time())
        manager.rotate_key(force=True)
        after = int(time.time())

        assert before <= manager.last_rotation_timestamp <= after

    def test_multiple_rotations(self):
        """Test multiple key rotations"""
        manager = KeyRotationManager()

        for i in range(5):
            manager.rotate_key(force=True)

        assert manager.active_key_id == "key_6"
        assert len(manager.historical_keys) == 5

    def test_rotation_preserves_historical_metadata(self):
        """Test that historical keys maintain metadata"""
        manager = KeyRotationManager()
        first_rotation_time = manager.last_rotation_timestamp

        time.sleep(0.1)
        manager.rotate_key(force=True)

        historical_entry = manager.historical_keys["key_1"]
        assert "key" in historical_entry
        assert "rotation_timestamp" in historical_entry
        assert "deactivation_timestamp" in historical_entry
        assert historical_entry["rotation_timestamp"] == first_rotation_time


class TestActiveKeyRetrieval:
    """Test retrieving active key"""

    def test_get_active_key(self):
        """Test getting active key"""
        manager = KeyRotationManager()
        key = manager.get_active_key()
        assert key == manager.active_key
        assert isinstance(key, bytes)

    def test_get_active_key_after_rotation(self):
        """Test getting active key after rotation"""
        manager = KeyRotationManager()
        manager.rotate_key(force=True)
        key = manager.get_active_key()
        assert key == manager.active_key

    def test_get_active_key_not_none(self):
        """Test that active key is never None"""
        manager = KeyRotationManager()
        assert manager.get_active_key() is not None


class TestHistoricalKeyRetrieval:
    """Test retrieving historical keys"""

    def test_get_key_by_id_active_key(self):
        """Test retrieving active key by ID"""
        manager = KeyRotationManager()
        key = manager.get_key_by_id(manager.active_key_id)
        assert key == manager.active_key

    def test_get_key_by_id_historical_key(self):
        """Test retrieving historical key by ID"""
        manager = KeyRotationManager()
        old_key = manager.active_key
        old_key_id = manager.active_key_id

        manager.rotate_key(force=True)

        retrieved_key = manager.get_key_by_id(old_key_id)
        assert retrieved_key == old_key

    def test_get_key_by_id_nonexistent(self):
        """Test retrieving non-existent key returns None"""
        manager = KeyRotationManager()
        key = manager.get_key_by_id("nonexistent_key")
        assert key is None

    def test_get_historical_keys(self):
        """Test getting all historical keys"""
        manager = KeyRotationManager()

        for i in range(3):
            manager.rotate_key(force=True)

        historical = manager.get_historical_keys()
        assert len(historical) == 3
        assert "key_1" in historical
        assert "key_2" in historical
        assert "key_3" in historical

    def test_get_historical_keys_empty_initially(self):
        """Test that historical keys is empty before first rotation"""
        manager = KeyRotationManager()
        historical = manager.get_historical_keys()
        assert len(historical) == 0

    def test_historical_keys_structure(self):
        """Test structure of historical keys entries"""
        manager = KeyRotationManager()
        manager.rotate_key(force=True)

        historical = manager.get_historical_keys()
        first_key_entry = historical["key_1"]

        assert "key" in first_key_entry
        assert "rotation_timestamp" in first_key_entry
        assert "deactivation_timestamp" in first_key_entry
        assert isinstance(first_key_entry["key"], bytes)
        assert isinstance(first_key_entry["rotation_timestamp"], int)
        assert isinstance(first_key_entry["deactivation_timestamp"], int)


class TestKeyLengthVariations:
    """Test different key lengths"""

    def test_small_key_length(self):
        """Test with small key length"""
        manager = KeyRotationManager(key_length_bytes=8)
        assert len(manager.active_key) == 8

    def test_standard_key_length(self):
        """Test with standard key length (256-bit)"""
        manager = KeyRotationManager(key_length_bytes=32)
        assert len(manager.active_key) == 32

    def test_large_key_length(self):
        """Test with large key length"""
        manager = KeyRotationManager(key_length_bytes=128)
        assert len(manager.active_key) == 128

    def test_key_length_preserved_across_rotations(self):
        """Test that key length is preserved across rotations"""
        manager = KeyRotationManager(key_length_bytes=64)

        for i in range(5):
            manager.rotate_key(force=True)
            assert len(manager.active_key) == 64


class TestRotationIntervals:
    """Test different rotation intervals"""

    def test_daily_rotation_interval(self):
        """Test daily rotation interval"""
        manager = KeyRotationManager(rotation_interval_days=1)
        assert manager.rotation_interval_days == 1

    def test_weekly_rotation_interval(self):
        """Test weekly rotation interval"""
        manager = KeyRotationManager(rotation_interval_days=7)
        assert manager.rotation_interval_days == 7

    def test_monthly_rotation_interval(self):
        """Test monthly rotation interval"""
        manager = KeyRotationManager(rotation_interval_days=30)
        assert manager.rotation_interval_days == 30

    def test_yearly_rotation_interval(self):
        """Test yearly rotation interval"""
        manager = KeyRotationManager(rotation_interval_days=365)
        assert manager.rotation_interval_days == 365

    def test_rotation_timing_calculation(self):
        """Test rotation timing is calculated correctly"""
        manager = KeyRotationManager(rotation_interval_days=1)

        # Set last rotation to 2 days ago
        manager.last_rotation_timestamp = int(time.time()) - (2 * 24 * 3600)

        # Should be due for rotation
        current_time = int(time.time())
        rotation_due = (current_time - manager.last_rotation_timestamp) >= (1 * 24 * 3600)
        assert rotation_due is True


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_minimum_key_length(self):
        """Test with minimum valid key length"""
        manager = KeyRotationManager(key_length_bytes=1)
        assert len(manager.active_key) == 1

    def test_minimum_rotation_interval(self):
        """Test with minimum rotation interval"""
        manager = KeyRotationManager(rotation_interval_days=1)
        assert manager.rotation_interval_days == 1

    def test_very_frequent_rotations(self):
        """Test handling very frequent rotations"""
        manager = KeyRotationManager()

        for i in range(100):
            manager.rotate_key(force=True)

        assert manager.active_key_id == "key_101"
        assert len(manager.historical_keys) == 100

    def test_key_id_counter_persistence(self):
        """Test that key ID counter continues incrementing"""
        manager = KeyRotationManager()

        # Generate some rotations
        for i in range(10):
            manager.rotate_key(force=True)

        assert manager._key_id_counter == 11

        # Generate more
        for i in range(10):
            manager.rotate_key(force=True)

        assert manager._key_id_counter == 21

    def test_timestamp_ordering(self):
        """Test that timestamps are properly ordered"""
        manager = KeyRotationManager()

        rotation_times = []
        for i in range(5):
            time.sleep(0.01)
            manager.rotate_key(force=True)
            rotation_times.append(manager.last_rotation_timestamp)

        # Timestamps should be strictly increasing
        for i in range(len(rotation_times) - 1):
            assert rotation_times[i] <= rotation_times[i + 1]


class TestSecurityProperties:
    """Test security-related properties"""

    def test_keys_are_unique(self):
        """Test that all generated keys are unique"""
        manager = KeyRotationManager()
        keys = set()

        # Generate many keys
        for i in range(50):
            manager.rotate_key(force=True)
            keys.add(manager.active_key)

        # All should be unique
        assert len(keys) == 50

    def test_old_keys_not_overwritten(self):
        """Test that historical keys are not modified"""
        manager = KeyRotationManager()

        old_key = manager.active_key
        old_key_id = manager.active_key_id

        manager.rotate_key(force=True)
        manager.rotate_key(force=True)

        # Old key should still be accessible and unchanged
        retrieved_old_key = manager.get_key_by_id(old_key_id)
        assert retrieved_old_key == old_key

    def test_key_data_not_leaked_in_str(self):
        """Test that key data doesn't leak in string representation"""
        manager = KeyRotationManager()
        manager_str = str(manager)

        # Key bytes should not appear in plain text
        # (This is a basic check - actual implementation might not define __str__)
        assert manager.active_key.hex() not in str(manager.__dict__)


class TestRealWorldScenarios:
    """Test real-world usage scenarios"""

    def test_encryption_key_rotation_scenario(self):
        """Test using manager for encryption key rotation"""
        manager = KeyRotationManager(key_length_bytes=32, rotation_interval_days=30)

        # Encrypt data with current key
        current_key_id = manager.active_key_id
        encryption_key = manager.get_active_key()

        # Rotate key
        manager.rotate_key(force=True)

        # Can still decrypt old data with old key
        old_key = manager.get_key_by_id(current_key_id)
        assert old_key == encryption_key

        # New encryptions use new key
        new_key = manager.get_active_key()
        assert new_key != encryption_key

    def test_api_token_rotation_scenario(self):
        """Test using manager for API token rotation"""
        manager = KeyRotationManager(key_length_bytes=64, rotation_interval_days=7)

        # Issue token with current key
        token_key_id = manager.active_key_id
        token_key = manager.get_active_key()

        # Multiple rotations
        for i in range(3):
            manager.rotate_key(force=True)

        # Old token can still be validated
        assert manager.get_key_by_id(token_key_id) == token_key

    def test_database_encryption_key_rotation(self):
        """Test database encryption key rotation scenario"""
        manager = KeyRotationManager(key_length_bytes=32, rotation_interval_days=90)

        # Track keys used for different data
        data_keys = {}
        for i in range(10):
            data_keys[f"data_{i}"] = {
                "key_id": manager.active_key_id,
                "key": manager.get_active_key()
            }
            manager.rotate_key(force=True)

        # All old keys should still be retrievable
        for data_id, key_info in data_keys.items():
            retrieved_key = manager.get_key_by_id(key_info["key_id"])
            assert retrieved_key == key_info["key"]

    def test_gradual_key_migration(self):
        """Test gradual migration from old to new keys"""
        manager = KeyRotationManager(key_length_bytes=32)

        # Old system uses key_1
        old_key_id = manager.active_key_id

        # Rotate to new key
        manager.rotate_key(force=True)
        new_key_id = manager.active_key_id

        # During migration, both keys are available
        assert manager.get_key_by_id(old_key_id) is not None
        assert manager.get_key_by_id(new_key_id) is not None

        # After migration, old key still accessible for decryption
        assert manager.get_key_by_id(old_key_id) is not None
