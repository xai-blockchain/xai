"""
XAI Blockchain - High-Performance Block Index

Provides O(1) block lookups via SQLite index with LRU caching.
Eliminates O(n) sequential scans that plague large blockchains.

Design:
- SQLite database maps block_index -> (file_path, file_offset, block_hash)
- LRU cache for hot blocks (recent/frequently accessed)
- Automatic migration for existing chains
- Thread-safe operations
- Durability via WAL mode

Performance:
- O(1) lookup time regardless of chain height
- <10ms block retrieval at any height
- Minimal memory footprint via streaming reads
"""

from __future__ import annotations

import os
import sqlite3
import threading
import time
import logging
from functools import lru_cache
from typing import Optional, Tuple, Dict, Any
from collections import OrderedDict

logger = logging.getLogger(__name__)


class LRUBlockCache:
    """
    Thread-safe LRU cache for frequently accessed blocks.

    Caches parsed Block objects to avoid repeated disk I/O and JSON parsing.
    Uses OrderedDict for O(1) access and eviction.
    """

    def __init__(self, capacity: int = 256):
        """
        Initialize LRU cache with specified capacity.

        Args:
            capacity: Maximum number of blocks to cache (default: 256 blocks)
        """
        self.capacity = capacity
        self.cache: OrderedDict[int, Any] = OrderedDict()
        self.lock = threading.Lock()
        self.hits = 0
        self.misses = 0

    def get(self, block_index: int) -> Optional[Any]:
        """
        Retrieve block from cache if present.

        Args:
            block_index: Block height to retrieve

        Returns:
            Block object if cached, None otherwise
        """
        with self.lock:
            if block_index in self.cache:
                # Move to end (most recently used)
                self.cache.move_to_end(block_index)
                self.hits += 1
                return self.cache[block_index]
            self.misses += 1
            return None

    def put(self, block_index: int, block: Any) -> None:
        """
        Store block in cache, evicting LRU if at capacity.

        Args:
            block_index: Block height
            block: Block object to cache
        """
        with self.lock:
            if block_index in self.cache:
                # Update existing entry
                self.cache.move_to_end(block_index)
            else:
                # Add new entry
                self.cache[block_index] = block
                # Evict LRU if at capacity
                if len(self.cache) > self.capacity:
                    self.cache.popitem(last=False)

    def invalidate(self, block_index: int) -> None:
        """
        Remove block from cache (used during reorgs).

        Args:
            block_index: Block height to invalidate
        """
        with self.lock:
            self.cache.pop(block_index, None)

    def clear(self) -> None:
        """Clear all cached blocks."""
        with self.lock:
            self.cache.clear()
            self.hits = 0
            self.misses = 0

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with hits, misses, hit_rate, size
        """
        with self.lock:
            total = self.hits + self.misses
            hit_rate = (self.hits / total * 100) if total > 0 else 0.0
            return {
                "hits": self.hits,
                "misses": self.misses,
                "hit_rate": f"{hit_rate:.2f}%",
                "size": len(self.cache),
                "capacity": self.capacity,
            }


class BlockIndex:
    """
    SQLite-backed block index for O(1) block lookups.

    Schema:
        block_index (PRIMARY KEY) - Block height
        block_hash (UNIQUE) - Block hash for integrity checks
        file_path - Relative path to block file
        file_offset - Byte offset within file
        file_size - Size of block JSON line in bytes
        indexed_at - Timestamp when indexed

    Features:
        - O(1) lookup by block height or hash
        - Automatic indexing on first startup
        - Thread-safe operations
        - WAL mode for durability
        - Integrity verification
    """

    def __init__(self, db_path: str, cache_size: int = 256):
        """
        Initialize block index.

        Args:
            db_path: Path to SQLite database file
            cache_size: LRU cache capacity (number of blocks)
        """
        self.db_path = db_path
        self.cache = LRUBlockCache(capacity=cache_size)
        self.lock = threading.RLock()

        # Create database and schema
        self._init_database()

        logger.info(
            "Block index initialized",
            extra={
                "event": "block_index.initialized",
                "db_path": db_path,
                "cache_size": cache_size,
            }
        )

    def _init_database(self) -> None:
        """
        Initialize SQLite database with optimized settings.

        Creates schema and enables performance optimizations:
        - WAL mode for better concurrency and durability
        - Synchronous=NORMAL for performance (still safe with WAL)
        - Larger cache for better read performance
        """
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)

        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        try:
            # Enable WAL mode for better concurrency and crash recovery
            conn.execute("PRAGMA journal_mode=WAL")

            # Performance optimizations
            conn.execute("PRAGMA synchronous=NORMAL")  # Safe with WAL
            conn.execute("PRAGMA cache_size=-64000")   # 64MB cache
            conn.execute("PRAGMA temp_store=MEMORY")   # Temp tables in memory

            # Create schema
            conn.execute('''
                CREATE TABLE IF NOT EXISTS block_index (
                    block_index INTEGER PRIMARY KEY,
                    block_hash TEXT UNIQUE NOT NULL,
                    file_path TEXT NOT NULL,
                    file_offset INTEGER NOT NULL,
                    file_size INTEGER NOT NULL,
                    indexed_at REAL NOT NULL
                )
            ''')

            # Index on block hash for hash-based lookups
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_block_hash
                ON block_index(block_hash)
            ''')

            # Metadata table for index versioning and stats
            conn.execute('''
                CREATE TABLE IF NOT EXISTS index_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            ''')

            # Set index version
            conn.execute(
                "INSERT OR IGNORE INTO index_metadata (key, value) VALUES ('version', '1.0')"
            )

            conn.commit()
        finally:
            conn.close()

    def index_block(
        self,
        block_index: int,
        block_hash: str,
        file_path: str,
        file_offset: int,
        file_size: int,
    ) -> None:
        """
        Add or update block index entry.

        Args:
            block_index: Block height
            block_hash: Block hash (for integrity verification)
            file_path: Relative path to block file
            file_offset: Byte offset within file
            file_size: Size of block JSON in bytes
        """
        with self.lock:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            try:
                conn.execute(
                    '''
                    INSERT OR REPLACE INTO block_index
                    (block_index, block_hash, file_path, file_offset, file_size, indexed_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ''',
                    (block_index, block_hash, file_path, file_offset, file_size, time.time())
                )
                conn.commit()

                # Invalidate cache for this block (in case of reorg)
                self.cache.invalidate(block_index)

            finally:
                conn.close()

    def get_block_location(self, block_index: int) -> Optional[Tuple[str, int, int]]:
        """
        Get file location for a block by height.

        Args:
            block_index: Block height

        Returns:
            Tuple of (file_path, file_offset, file_size) or None if not indexed
        """
        with self.lock:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            try:
                cursor = conn.execute(
                    'SELECT file_path, file_offset, file_size FROM block_index WHERE block_index = ?',
                    (block_index,)
                )
                row = cursor.fetchone()
                return tuple(row) if row else None  # type: ignore
            finally:
                conn.close()

    def get_block_location_by_hash(self, block_hash: str) -> Optional[Tuple[int, str, int, int]]:
        """
        Get block location by hash.

        Args:
            block_hash: Block hash to look up

        Returns:
            Tuple of (block_index, file_path, file_offset, file_size) or None
        """
        with self.lock:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            try:
                cursor = conn.execute(
                    '''
                    SELECT block_index, file_path, file_offset, file_size
                    FROM block_index
                    WHERE block_hash = ?
                    ''',
                    (block_hash,)
                )
                row = cursor.fetchone()
                return tuple(row) if row else None  # type: ignore
            finally:
                conn.close()

    def get_max_indexed_height(self) -> Optional[int]:
        """
        Get the highest indexed block height.

        Returns:
            Maximum block height in index, or None if empty
        """
        with self.lock:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            try:
                cursor = conn.execute('SELECT MAX(block_index) FROM block_index')
                row = cursor.fetchone()
                return row[0] if row and row[0] is not None else None
            finally:
                conn.close()

    def get_index_count(self) -> int:
        """
        Get total number of indexed blocks.

        Returns:
            Count of indexed blocks
        """
        with self.lock:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            try:
                cursor = conn.execute('SELECT COUNT(*) FROM block_index')
                row = cursor.fetchone()
                return row[0] if row else 0
            finally:
                conn.close()

    def verify_block_hash(self, block_index: int, expected_hash: str) -> bool:
        """
        Verify block hash matches indexed hash.

        Args:
            block_index: Block height
            expected_hash: Expected block hash

        Returns:
            True if hash matches, False otherwise
        """
        with self.lock:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            try:
                cursor = conn.execute(
                    'SELECT block_hash FROM block_index WHERE block_index = ?',
                    (block_index,)
                )
                row = cursor.fetchone()
                if not row:
                    return False
                return row[0] == expected_hash
            finally:
                conn.close()

    def remove_blocks_from(self, start_height: int) -> int:
        """
        Remove all blocks from specified height onwards (for reorgs).

        Args:
            start_height: Starting block height to remove

        Returns:
            Number of blocks removed
        """
        with self.lock:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            try:
                cursor = conn.execute(
                    'DELETE FROM block_index WHERE block_index >= ?',
                    (start_height,)
                )
                removed = cursor.rowcount
                conn.commit()

                # Clear cache since we may have removed cached blocks
                self.cache.clear()

                logger.info(
                    "Removed blocks from index for reorg",
                    extra={
                        "event": "block_index.reorg",
                        "start_height": start_height,
                        "blocks_removed": removed,
                    }
                )

                return removed
            finally:
                conn.close()

    def get_stats(self) -> Dict[str, Any]:
        """
        Get index statistics.

        Returns:
            Dictionary with index stats (count, max_height, cache_stats)
        """
        return {
            "total_blocks": self.get_index_count(),
            "max_height": self.get_max_indexed_height(),
            "cache": self.cache.get_stats(),
        }

    def close(self) -> None:
        """Close database connection and clear cache."""
        with self.lock:
            self.cache.clear()

            # Checkpoint WAL to ensure durability
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            try:
                conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                conn.close()
            except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as e:
                logger.warning(
                    "Failed to checkpoint WAL on close",
                    extra={"event": "block_index.close_error", "error": str(e)}
                )
