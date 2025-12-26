"""
Comprehensive tests for StorageManager module.

Tests cover:
- Singleton pattern behavior
- Basic key-value operations (get, set)
- JSON serialization of complex data types
- Database connection and table creation
- Error handling for invalid inputs
- Context manager support
- Cleanup and resource management
"""

import json
import os
import sqlite3
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_db_path():
    """Create a temporary database path for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test_storage.db"
        yield db_path


@pytest.fixture
def storage_manager(temp_db_path):
    """Create a StorageManager instance for testing."""
    from xai.database.storage_manager import StorageManager

    StorageManager._instance = None
    manager = StorageManager(temp_db_path)
    yield manager
    manager.close()


class TestStorageManagerSingleton:
    """Tests for singleton pattern behavior."""

    def test_singleton_returns_same_instance(self, temp_db_path):
        """Test that multiple calls return the same instance."""
        from xai.database.storage_manager import StorageManager

        StorageManager._instance = None

        manager1 = StorageManager(temp_db_path)
        manager2 = StorageManager(temp_db_path)

        assert manager1 is manager2
        manager1.close()

    def test_close_allows_new_instance(self, temp_db_path):
        """Test that closing allows creating a new instance."""
        from xai.database.storage_manager import StorageManager

        StorageManager._instance = None

        manager1 = StorageManager(temp_db_path)
        id1 = id(manager1)
        manager1.close()

        manager2 = StorageManager(temp_db_path)
        assert manager2._initialized is True
        manager2.close()

    def test_init_only_runs_once(self, temp_db_path):
        """Test that initialization only runs once for the singleton."""
        from xai.database.storage_manager import StorageManager

        StorageManager._instance = None

        manager1 = StorageManager(temp_db_path)
        initial_conn = manager1._conn

        manager2 = StorageManager(temp_db_path)
        assert manager2._conn is initial_conn
        manager1.close()


class TestStorageManagerSetOperation:
    """Tests for the set operation."""

    def test_set_string_value(self, storage_manager):
        """Test storing a simple string value."""
        storage_manager.set("test_key", "test_value")
        result = storage_manager.get("test_key")
        assert result == "test_value"

    def test_set_integer_value(self, storage_manager):
        """Test storing an integer value."""
        storage_manager.set("int_key", 42)
        result = storage_manager.get("int_key")
        assert result == 42

    def test_set_float_value(self, storage_manager):
        """Test storing a float value."""
        storage_manager.set("float_key", 3.14159)
        result = storage_manager.get("float_key")
        assert abs(result - 3.14159) < 0.00001

    def test_set_boolean_value(self, storage_manager):
        """Test storing boolean values."""
        storage_manager.set("bool_true", True)
        storage_manager.set("bool_false", False)

        assert storage_manager.get("bool_true") is True
        assert storage_manager.get("bool_false") is False

    def test_set_none_value(self, storage_manager):
        """Test storing None value."""
        storage_manager.set("none_key", None)
        result = storage_manager.get("none_key")
        assert result is None

    def test_set_list_value(self, storage_manager):
        """Test storing a list value."""
        test_list = [1, 2, 3, "four", 5.0]
        storage_manager.set("list_key", test_list)
        result = storage_manager.get("list_key")
        assert result == test_list

    def test_set_dict_value(self, storage_manager):
        """Test storing a dictionary value."""
        test_dict = {"name": "test", "count": 42, "nested": {"a": 1}}
        storage_manager.set("dict_key", test_dict)
        result = storage_manager.get("dict_key")
        assert result == test_dict

    def test_set_complex_nested_structure(self, storage_manager):
        """Test storing complex nested data structures."""
        complex_data = {
            "users": [
                {"id": 1, "name": "Alice", "active": True},
                {"id": 2, "name": "Bob", "active": False},
            ],
            "metadata": {
                "version": "1.0",
                "counts": [10, 20, 30],
            },
        }
        storage_manager.set("complex_key", complex_data)
        result = storage_manager.get("complex_key")
        assert result == complex_data

    def test_set_overwrites_existing_value(self, storage_manager):
        """Test that set overwrites existing values."""
        storage_manager.set("overwrite_key", "original")
        storage_manager.set("overwrite_key", "updated")

        result = storage_manager.get("overwrite_key")
        assert result == "updated"

    def test_set_empty_string_key(self, storage_manager):
        """Test storing with empty string key."""
        storage_manager.set("", "empty_key_value")
        result = storage_manager.get("")
        assert result == "empty_key_value"

    def test_set_unicode_values(self, storage_manager):
        """Test storing unicode values."""
        unicode_data = {"message": "Hello, World!", "emoji": "Test value"}
        storage_manager.set("unicode_key", unicode_data)
        result = storage_manager.get("unicode_key")
        assert result == unicode_data


class TestStorageManagerGetOperation:
    """Tests for the get operation."""

    def test_get_existing_key(self, storage_manager):
        """Test getting an existing key."""
        storage_manager.set("existing_key", "existing_value")
        result = storage_manager.get("existing_key")
        assert result == "existing_value"

    def test_get_nonexistent_key_returns_none(self, storage_manager):
        """Test getting a nonexistent key returns None by default."""
        result = storage_manager.get("nonexistent_key")
        assert result is None

    def test_get_nonexistent_key_returns_default(self, storage_manager):
        """Test getting a nonexistent key returns custom default."""
        result = storage_manager.get("nonexistent_key", default="custom_default")
        assert result == "custom_default"

    def test_get_with_zero_default(self, storage_manager):
        """Test getting with zero as default value."""
        result = storage_manager.get("missing", default=0)
        assert result == 0

    def test_get_with_empty_list_default(self, storage_manager):
        """Test getting with empty list as default value."""
        result = storage_manager.get("missing", default=[])
        assert result == []

    def test_get_with_false_default(self, storage_manager):
        """Test getting with False as default value."""
        result = storage_manager.get("missing", default=False)
        assert result is False


class TestStorageManagerDatabaseOperations:
    """Tests for database-level operations."""

    def test_creates_parent_directories(self):
        """Test that parent directories are created if they don't exist."""
        from xai.database.storage_manager import StorageManager

        with tempfile.TemporaryDirectory() as temp_dir:
            nested_path = Path(temp_dir) / "nested" / "dirs" / "test.db"

            StorageManager._instance = None
            manager = StorageManager(nested_path)

            assert nested_path.parent.exists()
            manager.close()

    def test_creates_table_on_init(self, temp_db_path):
        """Test that key_value_store table is created on initialization."""
        from xai.database.storage_manager import StorageManager

        StorageManager._instance = None
        manager = StorageManager(temp_db_path)

        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='key_value_store'"
        )
        result = cursor.fetchone()
        conn.close()

        assert result is not None
        assert result[0] == "key_value_store"
        manager.close()

    def test_wal_mode_enabled(self, temp_db_path):
        """Test that WAL journal mode is enabled."""
        from xai.database.storage_manager import StorageManager

        StorageManager._instance = None
        manager = StorageManager(temp_db_path)

        cursor = manager._conn.cursor()
        cursor.execute("PRAGMA journal_mode")
        result = cursor.fetchone()

        assert result[0].lower() == "wal"
        manager.close()

    def test_data_persists_across_instances(self, temp_db_path):
        """Test that data persists when reopening database."""
        from xai.database.storage_manager import StorageManager

        StorageManager._instance = None
        manager1 = StorageManager(temp_db_path)
        manager1.set("persist_key", {"data": "persistent"})
        manager1.close()

        StorageManager._instance = None
        manager2 = StorageManager(temp_db_path)
        result = manager2.get("persist_key")

        assert result == {"data": "persistent"}
        manager2.close()


class TestStorageManagerErrorHandling:
    """Tests for error handling."""

    def test_set_raises_on_non_serializable(self, storage_manager):
        """Test that set raises error for non-JSON-serializable objects."""
        class NonSerializable:
            pass

        with pytest.raises((TypeError, Exception)):
            storage_manager.set("bad_key", NonSerializable())

    def test_set_handles_circular_reference(self, storage_manager):
        """Test that set handles circular references gracefully."""
        circular = {"self": None}
        circular["self"] = circular

        with pytest.raises((TypeError, ValueError, Exception)):
            storage_manager.set("circular_key", circular)


class TestStorageManagerContextManager:
    """Tests for context manager support."""

    def test_context_manager_enter_returns_self(self, temp_db_path):
        """Test that __enter__ returns the manager instance."""
        from xai.database.storage_manager import StorageManager

        StorageManager._instance = None
        manager = StorageManager(temp_db_path)

        with manager as ctx:
            assert ctx is manager

    def test_context_manager_closes_on_exit(self, temp_db_path):
        """Test that context manager closes connection on exit."""
        from xai.database.storage_manager import StorageManager

        StorageManager._instance = None

        with StorageManager(temp_db_path) as manager:
            manager.set("ctx_key", "ctx_value")

        assert StorageManager._instance is None


class TestStorageManagerConcurrency:
    """Tests for concurrent access patterns."""

    def test_multiple_sets_sequential(self, storage_manager):
        """Test multiple sequential set operations."""
        for i in range(100):
            storage_manager.set(f"key_{i}", f"value_{i}")

        for i in range(100):
            assert storage_manager.get(f"key_{i}") == f"value_{i}"

    def test_set_then_update_many_keys(self, storage_manager):
        """Test setting and updating many keys."""
        for i in range(50):
            storage_manager.set(f"update_key_{i}", i)

        for i in range(50):
            storage_manager.set(f"update_key_{i}", i * 2)

        for i in range(50):
            assert storage_manager.get(f"update_key_{i}") == i * 2


class TestStorageManagerEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_very_long_key(self, storage_manager):
        """Test storing with a very long key."""
        long_key = "k" * 10000
        storage_manager.set(long_key, "long_key_value")
        result = storage_manager.get(long_key)
        assert result == "long_key_value"

    def test_very_large_value(self, storage_manager):
        """Test storing a very large value."""
        large_value = {"data": "x" * 100000, "numbers": list(range(1000))}
        storage_manager.set("large_key", large_value)
        result = storage_manager.get("large_key")
        assert result == large_value

    def test_special_characters_in_key(self, storage_manager):
        """Test keys with special characters."""
        special_keys = [
            "key/with/slashes",
            "key:with:colons",
            "key.with.dots",
            "key-with-dashes",
            "key_with_underscores",
            "key with spaces",
            "key\twith\ttabs",
        ]

        for key in special_keys:
            storage_manager.set(key, f"value_for_{key}")
            assert storage_manager.get(key) == f"value_for_{key}"

    def test_empty_dict_value(self, storage_manager):
        """Test storing empty dictionary."""
        storage_manager.set("empty_dict", {})
        result = storage_manager.get("empty_dict")
        assert result == {}

    def test_empty_list_value(self, storage_manager):
        """Test storing empty list."""
        storage_manager.set("empty_list", [])
        result = storage_manager.get("empty_list")
        assert result == []

    def test_deeply_nested_structure(self, storage_manager):
        """Test deeply nested data structure."""
        nested = {"level1": {"level2": {"level3": {"level4": {"level5": "deep"}}}}}
        storage_manager.set("deep_key", nested)
        result = storage_manager.get("deep_key")
        assert result["level1"]["level2"]["level3"]["level4"]["level5"] == "deep"

    def test_numeric_keys(self, storage_manager):
        """Test string representations of numeric keys."""
        storage_manager.set("123", "numeric_string_key")
        assert storage_manager.get("123") == "numeric_string_key"

    def test_json_string_value(self, storage_manager):
        """Test storing a JSON string as value."""
        json_string = json.dumps({"inner": "json"})
        storage_manager.set("json_string", json_string)
        result = storage_manager.get("json_string")
        assert result == json_string

    def test_list_of_dicts(self, storage_manager):
        """Test storing list of dictionaries."""
        data = [
            {"id": 1, "name": "first"},
            {"id": 2, "name": "second"},
            {"id": 3, "name": "third"},
        ]
        storage_manager.set("list_of_dicts", data)
        result = storage_manager.get("list_of_dicts")
        assert result == data
        assert len(result) == 3


class TestStorageManagerResourceManagement:
    """Tests for resource management."""

    def test_close_sets_instance_to_none(self, temp_db_path):
        """Test that close sets singleton instance to None."""
        from xai.database.storage_manager import StorageManager

        StorageManager._instance = None
        manager = StorageManager(temp_db_path)

        assert StorageManager._instance is not None
        manager.close()
        assert StorageManager._instance is None

    def test_destructor_closes_connection(self, temp_db_path):
        """Test that destructor closes connection."""
        from xai.database.storage_manager import StorageManager

        StorageManager._instance = None
        manager = StorageManager(temp_db_path)
        manager.set("del_key", "del_value")

        del manager

        StorageManager._instance = None
        manager2 = StorageManager(temp_db_path)
        assert manager2.get("del_key") == "del_value"
        manager2.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
