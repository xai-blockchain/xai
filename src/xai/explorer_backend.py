"""
XAI Block Explorer - Production-Grade Backend
Advanced analytics, search, and real-time capabilities
"""

from __future__ import annotations

import csv
import json
import logging
import os
import sqlite3
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field, asdict
from enum import Enum

import requests
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sock import Sock

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ==================== DATA MODELS ====================

class SearchType(Enum):
    """Types of searchable items"""
    BLOCK_HEIGHT = "block_height"
    BLOCK_HASH = "block_hash"
    TRANSACTION_ID = "transaction_id"
    ADDRESS = "address"
    UNKNOWN = "unknown"


@dataclass
class SearchResult:
    """Search result data"""
    type: SearchType
    item_id: str
    data: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)


@dataclass
class AddressLabel:
    """Address labeling system"""
    address: str
    label: str
    category: str  # exchange, pool, whale, contract, etc.
    description: str = ""
    created_at: float = field(default_factory=time.time)


@dataclass
class CachedMetric:
    """Cached metric data"""
    timestamp: float
    data: Dict[str, Any]
    ttl: int = 300  # 5 minutes default


# ==================== DATABASE MIGRATION MANAGER ====================

class DatabaseMigrationManager:
    """Schema versioning and migrations for production database evolution"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.current_version = 0
        self._init_migration_table()

    def _init_migration_table(self):
        """Create migration tracking table"""
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                applied_at REAL NOT NULL,
                description TEXT,
                rollback_sql TEXT
            )
        """)
        self.conn.commit()

        # Get current version
        cursor.execute("SELECT MAX(version) FROM schema_version")
        result = cursor.fetchone()
        self.current_version = result[0] if result[0] else 0
        logger.info(f"Current database schema version: {self.current_version}")

    def apply_migration(self, version: int, description: str,
                       sql: str, rollback_sql: str) -> bool:
        """Apply a database migration with rollback support"""
        if version <= self.current_version:
            logger.debug(f"Migration v{version} already applied")
            return True

        try:
            cursor = self.conn.cursor()

            # Execute migration
            cursor.executescript(sql)

            # Record migration
            cursor.execute("""
                INSERT INTO schema_version (version, applied_at, description, rollback_sql)
                VALUES (?, ?, ?, ?)
            """, (version, time.time(), description, rollback_sql))

            self.conn.commit()
            self.current_version = version

            logger.info(f"Applied migration v{version}: {description}")
            return True

        except sqlite3.DatabaseError as e:
            self.conn.rollback()
            logger.error(
                "Migration v%s failed: %s",
                version,
                e,
                extra={"event": "explorer_backend.migration_failed", "version": version},
            )
            return False

    def rollback_migration(self, version: int) -> bool:
        """Rollback a specific migration"""
        if version > self.current_version:
            logger.error(f"Cannot rollback v{version} (current: {self.current_version})")
            return False

        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT rollback_sql FROM schema_version
            WHERE version = ?
        """, (version,))

        result = cursor.fetchone()
        if not result or not result[0]:
            logger.error(f"No rollback SQL for v{version}")
            return False

        try:
            cursor.executescript(result[0])
            cursor.execute("DELETE FROM schema_version WHERE version = ?", (version,))
            self.conn.commit()

            self.current_version = version - 1
            logger.info(f"Rolled back migration v{version}")
            return True

        except sqlite3.DatabaseError as e:
            self.conn.rollback()
            logger.error(
                "Rollback v%s failed: %s",
                version,
                e,
                extra={"event": "explorer_backend.rollback_failed", "version": version},
            )
            return False

    def get_migration_history(self) -> List[Dict]:
        """Get complete migration history"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT version, applied_at, description
            FROM schema_version
            ORDER BY version
        """)

        return [
            {
                "version": row[0],
                "applied_at": row[1],
                "description": row[2]
            }
            for row in cursor.fetchall()
        ]


# Define migrations for automatic application
MIGRATIONS = [
    {
        "version": 1,
        "description": "Add blocks cache table",
        "sql": """
            CREATE TABLE IF NOT EXISTS blocks_cache (
                block_height INTEGER PRIMARY KEY,
                block_hash TEXT NOT NULL,
                block_data TEXT NOT NULL,
                cached_at REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_blocks_hash ON blocks_cache(block_hash);
        """,
        "rollback": "DROP TABLE IF EXISTS blocks_cache;"
    },
    {
        "version": 2,
        "description": "Add transactions index",
        "sql": """
            CREATE TABLE IF NOT EXISTS transactions_index (
                txid TEXT PRIMARY KEY,
                block_height INTEGER NOT NULL,
                sender TEXT,
                recipient TEXT,
                amount REAL,
                timestamp REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_tx_sender ON transactions_index(sender);
            CREATE INDEX IF NOT EXISTS idx_tx_recipient ON transactions_index(recipient);
            CREATE INDEX IF NOT EXISTS idx_tx_timestamp ON transactions_index(timestamp);
        """,
        "rollback": "DROP TABLE IF EXISTS transactions_index;"
    },
    {
        "version": 3,
        "description": "Add mempool monitoring table",
        "sql": """
            CREATE TABLE IF NOT EXISTS mempool_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                pending_count INTEGER NOT NULL,
                size_mb REAL NOT NULL,
                average_fee REAL NOT NULL,
                total_fees REAL NOT NULL,
                oldest_tx_age REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_mempool_timestamp ON mempool_history(timestamp);
        """,
        "rollback": "DROP TABLE IF EXISTS mempool_history;"
    }
]


# ==================== DATABASE MANAGEMENT ====================

class ExplorerDatabase:
    """SQLite database for explorer data with indexing and migrations"""

    def __init__(self, db_path: str = ":memory:"):
        """Initialize database"""
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        self.lock = threading.RLock()
        self._init_database()
        self._apply_migrations()

    def _init_database(self) -> None:
        """Initialize database schema"""
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            cursor = self.conn.cursor()

            # Search history table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS search_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query TEXT NOT NULL,
                    search_type TEXT NOT NULL,
                    user_id TEXT,
                    timestamp REAL NOT NULL,
                    result_found BOOLEAN DEFAULT 0
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_search_query ON search_history(query)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_search_timestamp ON search_history(timestamp)")

            # Address labels table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS address_labels (
                    address TEXT PRIMARY KEY,
                    label TEXT NOT NULL,
                    category TEXT NOT NULL,
                    description TEXT,
                    created_at REAL NOT NULL
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_address_label ON address_labels(label)")

            # Analytics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS analytics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_type TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    value REAL NOT NULL,
                    data TEXT
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_metric_type ON analytics(metric_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_metric_timestamp ON analytics(timestamp)")

            # Block explorer cache
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS explorer_cache (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    ttl REAL NOT NULL
                )
            """)

            self.conn.commit()
            logger.info("Database initialized successfully")
        except sqlite3.DatabaseError as e:
            logger.error(
                "Database initialization error: %s",
                e,
                extra={"event": "explorer_backend.db_init_failed"},
            )
            raise

    def _apply_migrations(self) -> None:
        """Apply all pending database migrations"""
        if self.db_path == ":memory:":
            logger.debug("Skipping migrations for in-memory database")
            return

        try:
            migrator = DatabaseMigrationManager(self.db_path)

            for migration in MIGRATIONS:
                migrator.apply_migration(
                    migration["version"],
                    migration["description"],
                    migration["sql"],
                    migration["rollback"]
                )
        except (sqlite3.DatabaseError, RuntimeError) as e:
            logger.error(
                "Migration application error: %s",
                e,
                extra={"event": "explorer_backend.migration_apply_failed"},
            )

    def add_search(self, query: str, search_type: str, result_found: bool, user_id: str = "anonymous") -> None:
        """Record search query"""
        try:
            with self.lock:
                cursor = self.conn.cursor()
                cursor.execute("""
                    INSERT INTO search_history (query, search_type, user_id, timestamp, result_found)
                    VALUES (?, ?, ?, ?, ?)
                """, (query, search_type, user_id, time.time(), int(result_found)))
                self.conn.commit()
        except sqlite3.DatabaseError as e:
            logger.error(
                "Error recording search: %s",
                e,
                extra={"event": "explorer_backend.search_record_failed"},
            )

    def get_recent_searches(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent searches"""
        try:
            with self.lock:
                cursor = self.conn.cursor()
                cursor.execute("""
                    SELECT query, search_type, timestamp
                    FROM search_history
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (limit,))
                return [
                    {"query": row[0], "type": row[1], "timestamp": row[2]}
                    for row in cursor.fetchall()
                ]
        except sqlite3.DatabaseError as e:
            logger.error(
                "Error fetching recent searches: %s",
                e,
                extra={"event": "explorer_backend.search_fetch_failed"},
            )
            return []

    def add_address_label(self, label: AddressLabel) -> None:
        """Add address label"""
        try:
            with self.lock:
                cursor = self.conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO address_labels (address, label, category, description, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (label.address, label.label, label.category, label.description, label.created_at))
                self.conn.commit()
        except sqlite3.DatabaseError as e:
            logger.error(
                "Error adding label: %s",
                e,
                extra={"event": "explorer_backend.label_add_failed"},
            )

    def get_address_label(self, address: str) -> Optional[AddressLabel]:
        """Get address label"""
        try:
            with self.lock:
                cursor = self.conn.cursor()
                cursor.execute("""
                    SELECT address, label, category, description, created_at
                    FROM address_labels
                    WHERE address = ?
                """, (address,))
                row = cursor.fetchone()
                if row:
                    return AddressLabel(*row)
        except sqlite3.DatabaseError as e:
            logger.error(
                "Error fetching label: %s",
                e,
                extra={"event": "explorer_backend.label_fetch_failed"},
            )
        return None

    def record_metric(self, metric_type: str, value: float, data: Optional[Dict] = None) -> None:
        """Record analytics metric"""
        try:
            with self.lock:
                cursor = self.conn.cursor()
                cursor.execute("""
                    INSERT INTO analytics (metric_type, timestamp, value, data)
                    VALUES (?, ?, ?, ?)
                """, (metric_type, time.time(), value, json.dumps(data) if data else None))
                self.conn.commit()
        except sqlite3.DatabaseError as e:
            logger.error(
                "Error recording metric: %s",
                e,
                extra={"event": "explorer_backend.metric_record_failed"},
            )

    def get_metrics(self, metric_type: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Get metrics for time period"""
        try:
            with self.lock:
                cursor = self.conn.cursor()
                cutoff_time = time.time() - (hours * 3600)
                cursor.execute("""
                    SELECT timestamp, value, data
                    FROM analytics
                    WHERE metric_type = ? AND timestamp > ?
                    ORDER BY timestamp ASC
                """, (metric_type, cutoff_time))
                return [
                    {"timestamp": row[0], "value": row[1], "data": json.loads(row[2]) if row[2] else None}
                    for row in cursor.fetchall()
                ]
        except sqlite3.DatabaseError as e:
            logger.error(
                "Error fetching metrics: %s",
                e,
                extra={"event": "explorer_backend.metric_fetch_failed"},
            )
            return []

    def set_cache(self, key: str, value: str, ttl: int = 300) -> None:
        """Set cache value"""
        try:
            with self.lock:
                cursor = self.conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO explorer_cache (key, value, ttl)
                    VALUES (?, ?, ?)
                """, (key, value, time.time() + ttl))
                self.conn.commit()
        except sqlite3.DatabaseError as e:
            logger.error(
                "Error setting cache: %s",
                e,
                extra={"event": "explorer_backend.cache_set_failed"},
            )

    def get_cache(self, key: str) -> Optional[str]:
        """Get cache value"""
        try:
            with self.lock:
                cursor = self.conn.cursor()
                cursor.execute("""
                    SELECT value FROM explorer_cache
                    WHERE key = ? AND ttl > ?
                """, (key, time.time()))
                row = cursor.fetchone()
                return row[0] if row else None
        except sqlite3.DatabaseError as e:
            logger.error(
                "Error getting cache: %s",
                e,
                extra={"event": "explorer_backend.cache_get_failed"},
            )
        return None


# ==================== ANALYTICS ENGINE ====================

class AnalyticsEngine:
    """Real-time analytics and metrics collection"""

    def __init__(self, node_url: str, db: ExplorerDatabase):
        """Initialize analytics engine"""
        self.node_url = node_url
        self.db = db
        self.metrics_cache: Dict[str, CachedMetric] = {}
        self.lock = threading.RLock()

        # Time-series data for recent metrics
        self.hashrate_history: deque = deque(maxlen=1440)  # 24 hours at 1-minute intervals
        self.tx_volume_history: deque = deque(maxlen=1440)
        self.active_addresses: Set[str] = set()
        self.mempool_sizes: deque = deque(maxlen=1440)

    def get_network_hashrate(self) -> Dict[str, Any]:
        """Calculate network hashrate"""
        cache_key = "hashrate"
        cached = self.db.get_cache(cache_key)
        if cached:
            return json.loads(cached)

        try:
            stats = self._fetch_stats()
            if not stats:
                return {"error": "Unable to fetch stats"}

            current_height = stats.get("total_blocks", 0)
            difficulty = stats.get("difficulty", 0)

            # Estimate hashrate from difficulty and block time
            avg_block_time = 60  # seconds (adjustable)
            estimated_hashrate = difficulty / avg_block_time if difficulty > 0 else 0

            result = {
                "hashrate": estimated_hashrate,
                "difficulty": difficulty,
                "block_height": current_height,
                "unit": "hashes/second",
                "timestamp": time.time()
            }

            self.db.set_cache(cache_key, json.dumps(result))
            self.db.record_metric("hashrate", estimated_hashrate)
            return result
        except (TypeError, ValueError, KeyError) as e:
            logger.error(
                "Error calculating hashrate: %s",
                e,
                extra={"event": "explorer_backend.hashrate_calc_failed"},
            )
            return {"error": str(e)}
        except requests.RequestException as e:
            logger.error(
                "Error fetching stats for hashrate: %s",
                e,
                extra={"event": "explorer_backend.hashrate_fetch_failed"},
            )
            return {"error": str(e)}

    def get_transaction_volume(self, period: str = "24h") -> Dict[str, Any]:
        """Get transaction volume metrics"""
        cache_key = f"tx_volume_{period}"
        cached = self.db.get_cache(cache_key)
        if cached:
            return json.loads(cached)

        try:
            hours_map = {"24h": 24, "7d": 168, "30d": 720}
            hours = hours_map.get(period, 24)

            blocks_data = self._fetch_blocks()
            if not blocks_data:
                return {"error": "Unable to fetch blocks"}

            blocks = blocks_data.get("blocks", [])
            recent_cutoff = time.time() - (hours * 3600)

            tx_count = 0
            unique_txs = set()
            fees_collected = 0.0

            for block in blocks:
                if block.get("timestamp", 0) > recent_cutoff:
                    block_txs = block.get("transactions", [])
                    tx_count += len(block_txs)
                    for tx in block_txs:
                        unique_txs.add(tx.get("txid", ""))
                        fees_collected += float(tx.get("fee", 0))

            avg_tx_per_block = tx_count / len(blocks) if blocks else 0

            result = {
                "period": period,
                "total_transactions": tx_count,
                "unique_transactions": len(unique_txs),
                "average_tx_per_block": avg_tx_per_block,
                "total_fees_collected": fees_collected,
                "timestamp": time.time()
            }

            self.db.set_cache(cache_key, json.dumps(result))
            self.db.record_metric(f"tx_volume_{period}", tx_count, result)
            return result
        except (TypeError, ValueError, KeyError) as e:
            logger.error(
                "Error calculating transaction volume: %s",
                e,
                extra={"event": "explorer_backend.tx_volume_calc_failed"},
            )
            return {"error": str(e)}
        except requests.RequestException as e:
            logger.error(
                "Error fetching blocks for tx volume: %s",
                e,
                extra={"event": "explorer_backend.tx_volume_fetch_failed"},
            )
            return {"error": str(e)}

    def get_active_addresses(self) -> Dict[str, Any]:
        """Get count of active addresses"""
        cache_key = "active_addresses"
        cached = self.db.get_cache(cache_key)
        if cached:
            return json.loads(cached)

        try:
            blocks_data = self._fetch_blocks()
            if not blocks_data:
                return {"error": "Unable to fetch blocks"}

            blocks = blocks_data.get("blocks", [])
            addresses: Set[str] = set()

            for block in blocks:
                for tx in block.get("transactions", []):
                    if tx.get("sender"):
                        addresses.add(tx["sender"])
                    if tx.get("recipient"):
                        addresses.add(tx["recipient"])

            result = {
                "total_unique_addresses": len(addresses),
                "timestamp": time.time()
            }

            self.db.set_cache(cache_key, json.dumps(result))
            self.db.record_metric("active_addresses", len(addresses))
            return result
        except (TypeError, ValueError, KeyError) as e:
            logger.error(
                "Error calculating active addresses: %s",
                e,
                extra={"event": "explorer_backend.active_addresses_calc_failed"},
            )
            return {"error": str(e)}
        except requests.RequestException as e:
            logger.error(
                "Error fetching blocks for active addresses: %s",
                e,
                extra={"event": "explorer_backend.active_addresses_fetch_failed"},
            )
            return {"error": str(e)}

    def get_average_block_time(self) -> Dict[str, Any]:
        """Calculate average block time"""
        cache_key = "avg_block_time"
        cached = self.db.get_cache(cache_key)
        if cached:
            return json.loads(cached)

        try:
            blocks_data = self._fetch_blocks()
            if not blocks_data:
                return {"error": "Unable to fetch blocks"}

            blocks = sorted(
                blocks_data.get("blocks", []),
                key=lambda b: b.get("timestamp", 0)
            )

            if len(blocks) < 2:
                return {"error": "Insufficient blocks for calculation"}

            block_times = []
            for i in range(1, len(blocks)):
                time_diff = blocks[i].get("timestamp", 0) - blocks[i-1].get("timestamp", 0)
                if time_diff > 0:
                    block_times.append(time_diff)

            avg_block_time = sum(block_times) / len(block_times) if block_times else 0

            result = {
                "average_block_time_seconds": avg_block_time,
                "blocks_sampled": len(block_times),
                "timestamp": time.time()
            }

            self.db.set_cache(cache_key, json.dumps(result))
            self.db.record_metric("avg_block_time", avg_block_time)
            return result
        except (TypeError, ValueError, KeyError) as e:
            logger.error(
                "Error calculating average block time: %s",
                e,
                extra={"event": "explorer_backend.avg_block_time_calc_failed"},
            )
            return {"error": str(e)}
        except requests.RequestException as e:
            logger.error(
                "Error fetching blocks for avg block time: %s",
                e,
                extra={"event": "explorer_backend.avg_block_time_fetch_failed"},
            )
            return {"error": str(e)}

    def get_mempool_size(self) -> Dict[str, Any]:
        """Get pending transactions (mempool) size"""
        cache_key = "mempool_size"
        cached = self.db.get_cache(cache_key)
        if cached:
            return json.loads(cached)

        try:
            response = requests.get(f"{self.node_url}/transactions", timeout=5)
            response.raise_for_status()
            data = response.json()

            pending_count = data.get("count", 0)
            transactions = data.get("transactions", [])

            total_value = 0.0
            total_fees = 0.0
            for tx in transactions:
                total_value += float(tx.get("amount", 0))
                total_fees += float(tx.get("fee", 0))

            result = {
                "pending_transactions": pending_count,
                "total_value": total_value,
                "total_fees": total_fees,
                "avg_fee": total_fees / pending_count if pending_count > 0 else 0,
                "timestamp": time.time()
            }

            self.db.set_cache(cache_key, json.dumps(result))
            self.db.record_metric("mempool_size", pending_count, result)
            return result
        except requests.RequestException as e:
            logger.error(
                "Error getting mempool size from node: %s",
                e,
                extra={"event": "explorer_backend.mempool_fetch_failed"},
            )
            return {"error": str(e)}
        except (TypeError, ValueError, KeyError) as e:
            logger.error(
                "Error parsing mempool response: %s",
                e,
                extra={"event": "explorer_backend.mempool_parse_failed"},
            )
            return {"error": str(e)}

    def get_network_difficulty(self) -> Dict[str, Any]:
        """Get network difficulty trend"""
        try:
            stats = self._fetch_stats()
            if not stats:
                return {"error": "Unable to fetch stats"}

            difficulty = stats.get("difficulty", 0)

            result = {
                "current_difficulty": difficulty,
                "timestamp": time.time()
            }

            self.db.record_metric("network_difficulty", difficulty)
            return result
        except (TypeError, ValueError, KeyError) as e:
            logger.error(
                "Error getting difficulty: %s",
                e,
                extra={"event": "explorer_backend.difficulty_parse_failed"},
            )
            return {"error": str(e)}
        except requests.RequestException as e:
            logger.error(
                "Error fetching difficulty from node: %s",
                e,
                extra={"event": "explorer_backend.difficulty_fetch_failed"},
            )
            return {"error": str(e)}

    def _fetch_stats(self) -> Optional[Dict[str, Any]]:
        """Fetch stats from node"""
        try:
            response = requests.get(f"{self.node_url}/stats", timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(
                "Error fetching stats: %s",
                e,
                extra={"event": "explorer_backend.stats_fetch_failed"},
            )
            return None
        except (ValueError, json.JSONDecodeError) as e:
            logger.error(
                "Error decoding stats JSON: %s",
                e,
                extra={"event": "explorer_backend.stats_decode_failed"},
            )
            return None

    def _fetch_blocks(self, limit: int = 100, offset: int = 0) -> Optional[Dict[str, Any]]:
        """Fetch blocks from node"""
        try:
            response = requests.get(
                f"{self.node_url}/blocks?limit={limit}&offset={offset}",
                timeout=5
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(
                "Error fetching blocks: %s",
                e,
                extra={"event": "explorer_backend.blocks_fetch_failed"},
            )
            return None
        except (ValueError, json.JSONDecodeError) as e:
            logger.error(
                "Error decoding blocks JSON: %s",
                e,
                extra={"event": "explorer_backend.blocks_decode_failed"},
            )
            return None


# ==================== SEARCH ENGINE ====================

class SearchEngine:
    """Advanced search with autocomplete and history"""

    def __init__(self, node_url: str, db: ExplorerDatabase):
        """Initialize search engine"""
        self.node_url = node_url
        self.db = db
        self.recent_searches: deque = deque(maxlen=100)

    def search(self, query: str, user_id: str = "anonymous") -> Dict[str, Any]:
        """Perform search and determine type"""
        query = query.strip()
        search_type = self._identify_search_type(query)

        result = {
            "query": query,
            "type": search_type.value,
            "results": None,
            "timestamp": time.time()
        }

        try:
            if search_type == SearchType.BLOCK_HEIGHT:
                result["results"] = self._search_block_height(int(query))
            elif search_type == SearchType.BLOCK_HASH:
                result["results"] = self._search_block_hash(query)
            elif search_type == SearchType.TRANSACTION_ID:
                result["results"] = self._search_transaction(query)
            elif search_type == SearchType.ADDRESS:
                result["results"] = self._search_address(query)

            # Record search
            found = result["results"] is not None
            self.db.add_search(query, search_type.value, found, user_id)

            result["found"] = found
        except requests.RequestException as e:
            logger.error(
                "Search error (network): %s",
                e,
                extra={"event": "explorer_backend.search_network_failed"},
            )
            result["error"] = str(e)
        except (ValueError, TypeError) as e:
            logger.error(
                "Search error (input/parse): %s",
                e,
                extra={"event": "explorer_backend.search_parse_failed"},
            )
            result["error"] = str(e)

        return result

    def get_autocomplete_suggestions(self, prefix: str, limit: int = 10) -> List[str]:
        """Get autocomplete suggestions from recent searches"""
        try:
            recent = self.db.get_recent_searches(limit * 2)
            suggestions = [
                item["query"] for item in recent
                if item["query"].startswith(prefix)
            ]
            return suggestions[:limit]
        except (ValueError, TypeError) as e:
            logger.error(
                "Autocomplete error: %s",
                e,
                extra={"event": "explorer_backend.autocomplete_failed"},
            )
            return []

    def get_recent_searches(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent searches"""
        return self.db.get_recent_searches(limit)

    def _identify_search_type(self, query: str) -> SearchType:
        """Identify search query type"""
        if query.isdigit():
            return SearchType.BLOCK_HEIGHT

        if len(query) == 64 and all(c in '0123456789abcdefABCDEF' for c in query):
            return SearchType.BLOCK_HASH

        if (query.startswith("XAI") or query.startswith("TXAI")) and len(query) > 10:
            return SearchType.ADDRESS

        if len(query) == 64:  # Assume transaction ID
            return SearchType.TRANSACTION_ID

        return SearchType.UNKNOWN

    def _search_block_height(self, height: int) -> Optional[Dict[str, Any]]:
        """Search by block height"""
        try:
            response = requests.get(f"{self.node_url}/blocks/{height}", timeout=5)
            if response.status_code == 200:
                return response.json()
        except requests.RequestException as e:
            logger.error(
                "Block search error: %s",
                e,
                extra={"event": "explorer_backend.search_block_failed"},
            )
        return None

    def _search_block_hash(self, block_hash: str) -> Optional[Dict[str, Any]]:
        """Search by block hash"""
        try:
            blocks_response = requests.get(f"{self.node_url}/blocks?limit=1000", timeout=5)
            if blocks_response.status_code == 200:
                blocks = blocks_response.json().get("blocks", [])
                for block in blocks:
                    if block.get("hash") == block_hash or block.get("previous_hash") == block_hash:
                        return block
        except requests.RequestException as e:
            logger.error(
                "Hash search error: %s",
                e,
                extra={"event": "explorer_backend.search_hash_failed"},
            )
        return None

    def _search_transaction(self, txid: str) -> Optional[Dict[str, Any]]:
        """Search by transaction ID"""
        try:
            response = requests.get(f"{self.node_url}/transaction/{txid}", timeout=5)
            if response.status_code == 200:
                return response.json()
        except requests.RequestException as e:
            logger.error(
                "Transaction search error: %s",
                e,
                extra={"event": "explorer_backend.search_tx_failed"},
            )
        return None

    def _search_address(self, address: str) -> Optional[Dict[str, Any]]:
        """Search by address"""
        try:
            balance_response = requests.get(f"{self.node_url}/balance/{address}", timeout=5)
            history_response = requests.get(f"{self.node_url}/history/{address}", timeout=5)

            if balance_response.status_code == 200:
                balance_data = balance_response.json()
                history_data = history_response.json() if history_response.status_code == 200 else {}

                return {
                    "address": address,
                    "balance": balance_data.get("balance", 0),
                    "transactions": history_data.get("transactions", []),
                    "transaction_count": len(history_data.get("transactions", []))
                }
        except requests.RequestException as e:
            logger.error(
                "Address search error: %s",
                e,
                extra={"event": "explorer_backend.search_address_failed"},
            )
        return None


# ==================== RICH LIST MANAGER ====================

class RichListManager:
    """Manage top address holders"""

    def __init__(self, node_url: str, db: ExplorerDatabase):
        """Initialize rich list manager"""
        self.node_url = node_url
        self.db = db
        self.rich_list_cache: Optional[List[Dict[str, Any]]] = None
        self.cache_timestamp: float = 0

    def get_rich_list(self, limit: int = 100, refresh: bool = False) -> List[Dict[str, Any]]:
        """Get top address holders"""
        cache_key = f"rich_list_{limit}"

        if not refresh:
            cached = self.db.get_cache(cache_key)
            if cached:
                return json.loads(cached)

        try:
            rich_list = self._calculate_rich_list(limit)

            if rich_list:
                self.db.set_cache(cache_key, json.dumps(rich_list), ttl=600)  # Cache for 10 minutes
                self.db.record_metric("richlist_top_holder", rich_list[0]["balance"])

            return rich_list
        except (TypeError, ValueError, KeyError) as e:
            logger.error(
                "Rich list error (calc): %s",
                e,
                extra={"event": "explorer_backend.richlist_calc_failed"},
            )
            return []
        except requests.RequestException as e:
            logger.error(
                "Rich list error (fetch): %s",
                e,
                extra={"event": "explorer_backend.richlist_fetch_failed"},
            )
            return []

    def _calculate_rich_list(self, limit: int) -> List[Dict[str, Any]]:
        """Calculate rich list from blockchain"""
        try:
            blocks_response = requests.get(f"{self.node_url}/blocks?limit=10000", timeout=10)
            blocks_response.raise_for_status()
            blocks = blocks_response.json().get("blocks", [])

            # Aggregate all transactions
            address_balances: Dict[str, float] = defaultdict(float)

            for block in blocks:
                for tx in block.get("transactions", []):
                    # Handle sender
                    if tx.get("sender") and tx.get("sender") != "COINBASE":
                        address_balances[tx["sender"]] -= float(tx.get("amount", 0))
                        address_balances[tx["sender"]] -= float(tx.get("fee", 0))

                    # Handle recipient
                    if tx.get("recipient"):
                        address_balances[tx["recipient"]] += float(tx.get("amount", 0))

            # Sort by balance
            sorted_addresses = sorted(
                address_balances.items(),
                key=lambda x: x[1],
                reverse=True
            )

            # Build rich list with labels
            rich_list = []
            for rank, (address, balance) in enumerate(sorted_addresses[:limit], 1):
                label_data = self.db.get_address_label(address)
                rich_list.append({
                    "rank": rank,
                    "address": address,
                    "balance": balance,
                    "label": label_data.label if label_data else None,
                    "category": label_data.category if label_data else None,
                    "percentage_of_supply": (balance / sum(dict(address_balances).values())) * 100 if sum(address_balances.values()) > 0 else 0
                })

            return rich_list
        except (TypeError, ValueError, KeyError, ZeroDivisionError) as e:
            logger.error(
                "Error calculating rich list: %s",
                e,
                extra={"event": "explorer_backend.richlist_calc_failed"},
            )
            return []
        except requests.RequestException as e:
            logger.error(
                "Error fetching blocks for rich list: %s",
                e,
                extra={"event": "explorer_backend.richlist_fetch_failed"},
            )
            return []


# ==================== CSV EXPORT ====================

class ExportManager:
    """Handle data exports"""

    def __init__(self, node_url: str):
        """Initialize export manager"""
        self.node_url = node_url

    def export_transactions_csv(self, address: str) -> Optional[str]:
        """Export address transactions as CSV"""
        try:
            history_response = requests.get(f"{self.node_url}/history/{address}", timeout=5)
            if history_response.status_code != 200:
                return None

            transactions = history_response.json().get("transactions", [])

            # Build CSV
            csv_lines = ["txid,timestamp,from,to,amount,fee,type"]

            for tx in transactions:
                timestamp = datetime.fromtimestamp(tx.get("timestamp", 0)).isoformat()
                txid = tx.get("txid", "")
                sender = tx.get("sender", "")
                recipient = tx.get("recipient", "")
                amount = tx.get("amount", 0)
                fee = tx.get("fee", 0)
                tx_type = tx.get("type", "transfer")

                csv_lines.append(
                    f'{txid},"{timestamp}",{sender},{recipient},{amount},{fee},{tx_type}'
                )

            return "\n".join(csv_lines)
        except (ValueError, KeyError, TypeError) as e:
            logger.error(
                "Export error (formatting): %s",
                e,
                extra={"event": "explorer_backend.export_format_failed"},
            )
            return None
        except requests.RequestException as e:
            logger.error(
                "Export error (fetch): %s",
                e,
                extra={"event": "explorer_backend.export_fetch_failed"},
            )
            return None


# ==================== ADDRESS LABELING MANAGER ====================

class AddressLabelingManager:
    """Address labeling with CSV import/export and search capabilities"""

    def __init__(self, db: ExplorerDatabase):
        self.db = db

    def import_from_csv(self, csv_path: str) -> Tuple[int, int]:
        """Import address labels from CSV file

        CSV format: address,label,category,description,verified
        Example: XAI123abc,Binance Hot Wallet,exchange,Official exchange wallet,true

        Returns: (imported_count, error_count)
        """
        import csv

        imported = 0
        errors = 0

        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)

                for row in reader:
                    try:
                        # Validate required fields
                        if not row.get('address') or not row.get('label'):
                            logger.warning(f"Skipping row with missing address/label")
                            errors += 1
                            continue

                        label = AddressLabel(
                            address=row['address'],
                            label=row['label'],
                            category=row.get('category', 'other'),
                            description=row.get('description', ''),
                        )

                        self.db.add_address_label(label)
                        imported += 1

                    except (ValueError, KeyError) as e:
                        logger.error(
                            "Failed to import label: %s",
                            e,
                            extra={"event": "explorer_backend.label_import_failed"},
                        )
                        errors += 1

            logger.info(f"CSV import complete: {imported} imported, {errors} errors")
            return imported, errors

        except (OSError, csv.Error, UnicodeDecodeError) as e:
            logger.error(
                "Failed to read CSV: %s",
                e,
                extra={"event": "explorer_backend.label_csv_read_failed"},
            )
            return 0, 0

    def export_to_csv(self, csv_path: str) -> int:
        """Export all labels to CSV file

        Returns: Number of labels exported
        """
        import csv

        # Get all labels from DB
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT address, label, category, description, created_at FROM address_labels")
        labels = cursor.fetchall()

        try:
            with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['address', 'label', 'category', 'description', 'created_at'])

                for label in labels:
                    writer.writerow(label)

            logger.info(f"Exported {len(labels)} labels to CSV")
            return len(labels)

        except (OSError, csv.Error) as e:
            logger.error(
                "CSV export error: %s",
                e,
                extra={"event": "explorer_backend.label_csv_export_failed"},
            )
            return 0

    def search_labels(self, query: str) -> List[AddressLabel]:
        """Search labels by name or address"""
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT address, label, category, description, created_at
            FROM address_labels
            WHERE label LIKE ? OR address LIKE ?
            LIMIT 100
        """, (f"%{query}%", f"%{query}%"))

        return [AddressLabel(*row) for row in cursor.fetchall()]

    def get_labels_by_category(self, category: str) -> List[AddressLabel]:
        """Get all labels in a specific category"""
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT address, label, category, description, created_at
            FROM address_labels
            WHERE category = ?
            ORDER BY label
        """, (category,))

        return [AddressLabel(*row) for row in cursor.fetchall()]

    def get_all_categories(self) -> List[str]:
        """Get list of all label categories"""
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT DISTINCT category FROM address_labels
            ORDER BY category
        """)

        return [row[0] for row in cursor.fetchall()]


# ==================== MEMPOOL MONITOR ====================

class MempoolMonitor:
    """Real-time mempool monitoring with historical tracking"""

    def __init__(self, node_url: str, db: ExplorerDatabase):
        self.node_url = node_url
        self.db = db
        self.history = deque(maxlen=1440)  # 24 hours at 1-minute intervals
        self.monitoring = True
        self.monitor_thread: Optional[threading.Thread] = None

        # Start monitoring thread
        self._start_monitoring()

    def _start_monitoring(self):
        """Start background monitoring thread"""
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Mempool monitoring started")

    def _monitor_loop(self):
        """Background monitoring loop"""
        while self.monitoring:
            try:
                metrics = self.get_mempool_metrics()
                if "error" not in metrics:
                    self.history.append(metrics)

                    # Store in database for long-term history
                    self._store_metrics(metrics)

            except requests.RequestException as e:
                logger.error(
                    "Mempool monitoring error (network): %s",
                    e,
                    extra={"event": "explorer_backend.mempool_monitor_fetch_failed"},
                )
            except (TypeError, ValueError, KeyError) as e:
                logger.error(
                    "Mempool monitoring error (parse): %s",
                    e,
                    extra={"event": "explorer_backend.mempool_monitor_parse_failed"},
                )

            time.sleep(10)  # Update every 10 seconds

    def _store_metrics(self, metrics: Dict[str, Any]):
        """Store metrics in database"""
        try:
            with self.db.lock:
                cursor = self.db.conn.cursor()
                cursor.execute("""
                    INSERT INTO mempool_history
                    (timestamp, pending_count, size_mb, average_fee, total_fees, oldest_tx_age)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    metrics["timestamp"],
                    metrics["pending_count"],
                    metrics["size_mb"],
                    metrics["average_fee"],
                    metrics["total_fees"],
                    metrics["oldest_tx_age"]
                ))
                self.db.conn.commit()
        except sqlite3.DatabaseError as e:
            logger.error(
                "Failed to store mempool metrics: %s",
                e,
                extra={"event": "explorer_backend.mempool_metrics_store_failed"},
            )

    def get_mempool_metrics(self) -> Dict[str, Any]:
        """Get current mempool metrics"""
        try:
            response = requests.get(f"{self.node_url}/transactions", timeout=5)
            data = response.json()

            transactions = data.get("transactions", [])
            pending_count = len(transactions)

            # Calculate size
            size_bytes = len(json.dumps(transactions).encode())
            size_mb = size_bytes / (1024 * 1024)

            # Calculate fees
            total_fees = sum(float(tx.get("fee", 0)) for tx in transactions)
            avg_fee = total_fees / pending_count if pending_count > 0 else 0

            # Find oldest transaction
            oldest_age = 0
            if transactions:
                oldest_timestamp = min(tx.get("timestamp", time.time()) for tx in transactions)
                oldest_age = time.time() - oldest_timestamp

            return {
                "pending_count": pending_count,
                "size_mb": round(size_mb, 3),
                "average_fee": round(avg_fee, 8),
                "total_fees": round(total_fees, 8),
                "oldest_tx_age": round(oldest_age, 2),
                "timestamp": time.time()
            }

        except requests.RequestException as e:
            logger.error(
                "Failed to get mempool metrics (fetch): %s",
                e,
                extra={"event": "explorer_backend.mempool_metrics_fetch_failed"},
            )
            return {
                "pending_count": 0,
                "size_mb": 0,
                "average_fee": 0,
                "total_fees": 0,
                "oldest_tx_age": 0,
                "timestamp": time.time(),
                "error": str(e)
            }
        except (TypeError, ValueError, KeyError, json.JSONDecodeError) as e:
            logger.error(
                "Failed to get mempool metrics (parse): %s",
                e,
                extra={"event": "explorer_backend.mempool_metrics_parse_failed"},
            )
            return {
                "pending_count": 0,
                "size_mb": 0,
                "average_fee": 0,
                "total_fees": 0,
                "oldest_tx_age": 0,
                "timestamp": time.time(),
                "error": str(e)
            }

    def get_mempool_chart_data(self, hours: int = 24) -> List[Dict]:
        """Get historical mempool data for charting"""
        cutoff_time = time.time() - (hours * 3600)

        # Get from in-memory history first
        recent_data = [
            m for m in self.history
            if m["timestamp"] > cutoff_time
        ]

        # If not enough data, get from database
        if len(recent_data) < 10:
            try:
                with self.db.lock:
                    cursor = self.db.conn.cursor()
                    cursor.execute("""
                        SELECT timestamp, pending_count, size_mb, average_fee, total_fees, oldest_tx_age
                        FROM mempool_history
                        WHERE timestamp > ?
                        ORDER BY timestamp ASC
                    """, (cutoff_time,))

                    db_data = [
                        {
                            "timestamp": row[0],
                            "pending_count": row[1],
                            "size_mb": row[2],
                            "average_fee": row[3],
                            "total_fees": row[4],
                            "oldest_tx_age": row[5]
                        }
                        for row in cursor.fetchall()
                    ]

                    return db_data
            except sqlite3.DatabaseError as e:
                logger.error(
                    "Failed to get mempool history from DB: %s",
                    e,
                    extra={"event": "explorer_backend.mempool_history_db_failed"},
                )

        return recent_data

    def get_mempool_stats(self) -> Dict[str, Any]:
        """Get aggregate mempool statistics"""
        try:
            current = self.get_mempool_metrics()
            history = self.get_mempool_chart_data(24)

            if not history:
                return current

            avg_pending = sum(h["pending_count"] for h in history) / len(history)
            max_pending = max(h["pending_count"] for h in history)
            avg_fee = sum(h["average_fee"] for h in history) / len(history)

            return {
                "current": current,
                "24h_average_pending": round(avg_pending, 2),
                "24h_max_pending": max_pending,
                "24h_average_fee": round(avg_fee, 8),
                "data_points": len(history)
            }

        except (TypeError, ValueError, KeyError) as e:
            logger.error(
                "Failed to get mempool stats: %s",
                e,
                extra={"event": "explorer_backend.mempool_stats_calc_failed"},
            )
            return {"error": str(e)}

    def stop(self):
        """Stop monitoring thread"""
        self.monitoring = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
        logger.info("Mempool monitoring stopped")


# ==================== FLASK APP ====================

app = Flask(__name__)
CORS(app)
sock = Sock(app)

# Initialize components
NODE_URL = os.getenv("XAI_NODE_URL", "http://localhost:8545")
DB_PATH = os.getenv("EXPLORER_DB_PATH", ":memory:")

db = ExplorerDatabase(DB_PATH)
analytics = AnalyticsEngine(NODE_URL, db)
search_engine = SearchEngine(NODE_URL, db)
rich_list = RichListManager(NODE_URL, db)
export_manager = ExportManager(NODE_URL)
address_labeler = AddressLabelingManager(db)
mempool_monitor = MempoolMonitor(NODE_URL, db)

# WebSocket connections for real-time updates
ws_clients: Set[Any] = set()
ws_lock = threading.RLock()


# ==================== ANALYTICS ENDPOINTS ====================

@app.route("/api/analytics/hashrate", methods=["GET"])
def get_hashrate_endpoint():
    """Get network hashrate"""
    return jsonify(analytics.get_network_hashrate())


@app.route("/api/analytics/tx-volume", methods=["GET"])
def get_tx_volume_endpoint():
    """Get transaction volume"""
    period = request.args.get("period", "24h")
    return jsonify(analytics.get_transaction_volume(period))


@app.route("/api/analytics/active-addresses", methods=["GET"])
def get_active_addresses_endpoint():
    """Get active addresses count"""
    return jsonify(analytics.get_active_addresses())


@app.route("/api/analytics/block-time", methods=["GET"])
def get_block_time_endpoint():
    """Get average block time"""
    return jsonify(analytics.get_average_block_time())


@app.route("/api/analytics/mempool", methods=["GET"])
def get_mempool_endpoint():
    """Get mempool size"""
    return jsonify(analytics.get_mempool_size())


@app.route("/api/analytics/difficulty", methods=["GET"])
def get_difficulty_endpoint():
    """Get network difficulty"""
    return jsonify(analytics.get_network_difficulty())


@app.route("/api/analytics/dashboard", methods=["GET"])
def get_analytics_dashboard():
    """Get all analytics for dashboard"""
    return jsonify({
        "hashrate": analytics.get_network_hashrate(),
        "transaction_volume": analytics.get_transaction_volume(),
        "active_addresses": analytics.get_active_addresses(),
        "average_block_time": analytics.get_average_block_time(),
        "mempool": analytics.get_mempool_size(),
        "difficulty": analytics.get_network_difficulty(),
        "timestamp": time.time()
    })


# ==================== SEARCH ENDPOINTS ====================

@app.route("/api/search", methods=["POST"])
def search_endpoint():
    """Advanced search endpoint"""
    data = request.json or {}
    query = data.get("query", "").strip()
    user_id = data.get("user_id", "anonymous")

    if not query:
        return jsonify({"error": "Query required"}), 400

    return jsonify(search_engine.search(query, user_id))


@app.route("/api/search/autocomplete", methods=["GET"])
def autocomplete_endpoint():
    """Get autocomplete suggestions"""
    prefix = request.args.get("prefix", "").strip()
    limit = request.args.get("limit", 10, type=int)

    if not prefix:
        return jsonify({"suggestions": []})

    return jsonify({
        "suggestions": search_engine.get_autocomplete_suggestions(prefix, limit)
    })


@app.route("/api/search/recent", methods=["GET"])
def recent_searches_endpoint():
    """Get recent searches"""
    limit = request.args.get("limit", 10, type=int)
    return jsonify({
        "recent": search_engine.get_recent_searches(limit)
    })


# ==================== RICH LIST ENDPOINTS ====================

@app.route("/api/richlist", methods=["GET"])
def richlist_endpoint():
    """Get top address holders"""
    limit = request.args.get("limit", 100, type=int)
    limit = min(limit, 1000)  # Cap at 1000

    return jsonify({
        "richlist": rich_list.get_rich_list(limit)
    })


@app.route("/api/richlist/refresh", methods=["POST"])
def richlist_refresh_endpoint():
    """Force refresh rich list"""
    limit = request.args.get("limit", 100, type=int)
    limit = min(limit, 1000)

    return jsonify({
        "richlist": rich_list.get_rich_list(limit, refresh=True)
    })


# ==================== ADDRESS LABELING ====================

@app.route("/api/address/<address>/label", methods=["GET"])
def get_address_label(address):
    """Get address label"""
    label = db.get_address_label(address)
    if label:
        return jsonify(asdict(label))
    return jsonify({"label": None})


@app.route("/api/address/<address>/label", methods=["POST"])
def set_address_label(address):
    """Set address label (admin endpoint)"""
    # In production, this should have authentication
    data = request.json or {}

    if not data.get("label"):
        return jsonify({"error": "Label required"}), 400

    label = AddressLabel(
        address=address,
        label=data["label"],
        category=data.get("category", "other"),
        description=data.get("description", "")
    )

    db.add_address_label(label)
    return jsonify({"success": True, "label": asdict(label)})


# ==================== EXPORT ENDPOINTS ====================

@app.route("/api/export/transactions/<address>", methods=["GET"])
def export_transactions(address):
    """Export address transactions as CSV"""
    csv_data = export_manager.export_transactions_csv(address)
    if csv_data:
        return csv_data, 200, {
            "Content-Type": "text/csv",
            "Content-Disposition": f"attachment; filename=transactions_{address}.csv"
        }
    return jsonify({"error": "Unable to export"}), 404


# ==================== WEBSOCKET REAL-TIME UPDATES ====================

@sock.route("/api/ws/updates")
def websocket_updates(ws):
    """WebSocket endpoint for real-time updates"""
    with ws_lock:
        ws_clients.add(ws)

    logger.info(f"WebSocket client connected. Total: {len(ws_clients)}")

    try:
        while True:
            # Receive heartbeat
            data = ws.receive()
            if data == "ping":
                ws.send("pong")
    except (ConnectionResetError, OSError, RuntimeError) as e:
        logger.error(
            "WebSocket error: %s",
            e,
            extra={"event": "explorer_backend.websocket_error"},
        )
    finally:
        with ws_lock:
            ws_clients.discard(ws)
        logger.info(f"WebSocket client disconnected. Total: {len(ws_clients)}")


def broadcast_update(update_type: str, data: Dict[str, Any]) -> None:
    """Broadcast update to all WebSocket clients"""
    message = json.dumps({
        "type": update_type,
        "data": data,
        "timestamp": time.time()
    })

    with ws_lock:
        for client in list(ws_clients):
            try:
                client.send(message)
            except (ConnectionResetError, OSError, RuntimeError) as e:
                logger.error(
                    "Broadcast error: %s",
                    e,
                    extra={"event": "explorer_backend.broadcast_error"},
                )
                ws_clients.discard(client)


# ==================== METRICS ENDPOINTS ====================

@app.route("/api/metrics/<metric_type>", methods=["GET"])
def get_metric_history(metric_type):
    """Get metric history"""
    hours = request.args.get("hours", 24, type=int)
    metrics = db.get_metrics(metric_type, hours)
    return jsonify({
        "metric_type": metric_type,
        "period_hours": hours,
        "data": metrics
    })


# ==================== ADDRESS LABELING ENDPOINTS ====================

@app.route("/api/labels/import", methods=["POST"])
def import_labels():
    """Import labels from CSV file (admin endpoint)"""
    # In production, add authentication/authorization
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']
    if not file.filename.endswith('.csv'):
        return jsonify({"error": "File must be CSV"}), 400

    # Save temporarily
    import tempfile
    with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.csv') as f:
        file.save(f.name)
        csv_path = f.name

    try:
        imported, errors = address_labeler.import_from_csv(csv_path)
        os.unlink(csv_path)

        return jsonify({
            "success": True,
            "imported": imported,
            "errors": errors
        })
    except (OSError, csv.Error, UnicodeDecodeError) as e:
        if os.path.exists(csv_path):
            os.unlink(csv_path)
        return jsonify({"error": str(e)}), 500


@app.route("/api/labels/export", methods=["GET"])
def export_labels():
    """Export all labels to CSV"""
    import tempfile

    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
        csv_path = f.name

    try:
        count = address_labeler.export_to_csv(csv_path)

        with open(csv_path, 'r') as f:
            csv_data = f.read()

        os.unlink(csv_path)

        return csv_data, 200, {
            "Content-Type": "text/csv",
            "Content-Disposition": "attachment; filename=address_labels.csv"
        }
    except (OSError, csv.Error) as e:
        if os.path.exists(csv_path):
            os.unlink(csv_path)
        return jsonify({"error": str(e)}), 500


@app.route("/api/labels/search", methods=["GET"])
def search_labels_endpoint():
    """Search address labels"""
    query = request.args.get("q", "")
    if not query:
        return jsonify({"error": "Query parameter 'q' required"}), 400

    results = address_labeler.search_labels(query)
    return jsonify({
        "query": query,
        "results": [asdict(label) for label in results],
        "count": len(results)
    })


@app.route("/api/labels/categories", methods=["GET"])
def get_label_categories():
    """Get all label categories"""
    categories = address_labeler.get_all_categories()
    return jsonify({
        "categories": categories
    })


@app.route("/api/labels/category/<category>", methods=["GET"])
def get_labels_by_category_endpoint(category):
    """Get labels by category"""
    labels = address_labeler.get_labels_by_category(category)
    return jsonify({
        "category": category,
        "labels": [asdict(label) for label in labels],
        "count": len(labels)
    })


# ==================== MEMPOOL MONITORING ENDPOINTS ====================

@app.route("/api/mempool", methods=["GET"])
def get_mempool_metrics_endpoint():
    """Get current mempool metrics"""
    return jsonify(mempool_monitor.get_mempool_metrics())


@app.route("/api/mempool/chart", methods=["GET"])
def get_mempool_chart_endpoint():
    """Get mempool history for charting"""
    hours = request.args.get("hours", 24, type=int)
    hours = min(hours, 168)  # Max 7 days

    return jsonify({
        "hours": hours,
        "data": mempool_monitor.get_mempool_chart_data(hours)
    })


@app.route("/api/mempool/stats", methods=["GET"])
def get_mempool_stats_endpoint():
    """Get aggregate mempool statistics"""
    return jsonify(mempool_monitor.get_mempool_stats())


# ==================== HEALTH CHECK ====================

@app.route("/health", methods=["GET"])
def health_check():
    """Health check"""
    try:
        response = requests.get(f"{NODE_URL}/health", timeout=5)
        node_status = response.status_code == 200
    except (requests.RequestException, Exception) as e:
        logger.debug(f"Health check failed: {e}")
        node_status = False

    return jsonify({
        "status": "healthy" if node_status else "degraded",
        "explorer": "running",
        "node": "connected" if node_status else "disconnected",
        "timestamp": time.time()
    }), (200 if node_status else 503)


# ==================== INFO ENDPOINT ====================

@app.route("/", methods=["GET"])
def explorer_info():
    """Explorer information"""
    return jsonify({
        "name": "XAI Block Explorer",
        "version": "2.0.0",
        "features": {
            "advanced_search": True,
            "analytics": True,
            "rich_list": True,
            "address_labels": True,
            "csv_export": True,
            "websocket_updates": True,
            "address_labeling": True
        },
        "endpoints": {
            "analytics": "/api/analytics/*",
            "search": "/api/search",
            "richlist": "/api/richlist",
            "export": "/api/export/*",
            "websocket": "/api/ws/updates"
        },
        "node_url": NODE_URL,
        "timestamp": time.time()
    })


if __name__ == "__main__":
    port = int(os.getenv("EXPLORER_PORT", 8082))
    logger.info(f"Starting XAI Block Explorer on port {port}")
    logger.info(f"Node URL: {NODE_URL}")
    logger.info(f"Database: {DB_PATH}")

    # Security fix: Use environment variable with secure default (127.0.0.1)
    host = os.getenv("EXPLORER_BACKEND_HOST", "127.0.0.1")
    app.run(host=host, port=port, debug=False, threaded=True)
