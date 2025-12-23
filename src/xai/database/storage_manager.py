# src/xai/database/storage_manager.py
from __future__ import annotations

"""
Provides a simple, persistent key-value storage layer using SQLite.

This module offers a StorageManager class that abstracts the database interactions,
allowing other parts of the application to store and retrieve data by key
without needing to handle SQL or database connections directly. Values are
serialized to JSON, allowing for the storage of complex data structures.
"""

import json
import sqlite3
from pathlib import Path
from typing import Any

class StorageManager:
    """
    Manages a persistent key-value store backed by a SQLite database.

    This class provides a simple get/set interface for persisting data.
    It handles database connection, cursor management, and data serialization.
    """

    _instance = None

    def __new__(cls, db_path: Path):
        """
        Ensures that only one instance of the StorageManager exists for a given db_path.
        This is a basic implementation of the Singleton pattern.
        """
        # Note: A more robust singleton might be necessary in a multi-threaded context,
        # but this is sufficient for initial implementation.
        if cls._instance is None:
            cls._instance = super(StorageManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, db_path: Path):
        """
        Initializes the StorageManager, creates the database file if it doesn't exist,
        and sets up the necessary tables.

        Args:
            db_path (Path): The path to the SQLite database file. The directory
                            will be created if it does not exist.
        """
        if self._initialized:
            return

        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            self._conn = sqlite3.connect(
                self.db_path, check_same_thread=False, isolation_level="EXCLUSIVE"
            )
            self._conn.execute("PRAGMA journal_mode=WAL;")
            self._conn.execute("PRAGMA synchronous=NORMAL;")
            self._create_table()
            self._initialized = True
        except sqlite3.Error as e:
            # Handle potential initialization errors, e.g., permissions
            print(f"FATAL: Database connection failed: {e}")
            raise

    def _create_table(self):
        """
        Creates the key_value_store table if it does not already exist.
        """
        try:
            with self._conn:
                self._conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS key_value_store (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL
                    )
                    """
                )
        except sqlite3.Error as e:
            print(f"ERROR: Failed to create table: {e}")
            raise

    def set(self, key: str, value: Any):
        """
        Saves or updates a value in the key-value store.

        The value is serialized to a JSON string before storing.

        Args:
            key (str): The unique key for the data.
            value (Any): The Python object to store.
        """
        try:
            value_json = json.dumps(value)
            with self._conn:
                self._conn.execute(
                    """
                    INSERT INTO key_value_store (key, value)
                    VALUES (?, ?)
                    ON CONFLICT(key) DO UPDATE SET value = excluded.value
                    """,
                    (key, value_json),
                )
        except (sqlite3.Error, TypeError) as e:
            # TypeError for objects that can't be JSON serialized
            print(f"ERROR: Failed to set key '{key}': {e}")
            raise

    def get(self, key: str, default: Any | None = None) -> Any:
        """
        Retrieves a value from the key-value store by its key.

        The value is deserialized from a JSON string before being returned.

        Args:
            key (str): The key of the data to retrieve.
            default (Any | None): The value to return if the key is not found.
                                     Defaults to None.

        Returns:
            Any: The deserialized Python object, or the default value if not found.
        """
        try:
            cursor = self._conn.cursor()
            cursor.execute("SELECT value FROM key_value_store WHERE key = ?", (key,))
            row = cursor.fetchone()
            if row:
                return json.loads(row[0])
            return default
        except sqlite3.Error as e:
            print(f"ERROR: Failed to get key '{key}': {e}")
            return default

    def close(self):
        """
        Closes the database connection.
        It's good practice to call this on application shutdown.
        """
        if self._conn:
            self._conn.close()
            StorageManager._instance = None  # Allow re-creation for tests

    def __del__(self):
        """
        Destructor to ensure the connection is closed when the object is garbage collected.
        """
        self.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
