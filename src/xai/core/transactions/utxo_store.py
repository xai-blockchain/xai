"""
XAI Blockchain - UTXO Storage Backend Abstraction

Provides pluggable storage backends for the UTXO set:
- MemoryUTXOStore: In-memory dict-based storage (default, JSON-serializable)
- LevelDBUTXOStore: High-performance LevelDB storage for production

The adapter pattern allows switching backends without changing UTXOManager API.

Usage:
    # Use memory backend (default)
    store = MemoryUTXOStore()

    # Use LevelDB backend
    store = LevelDBUTXOStore("/path/to/utxo.db")

    # Pass to UTXOManager
    manager = UTXOManager(store=store)
"""

from __future__ import annotations

import json
import hashlib
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from threading import RLock
from typing import Any, Iterator

# LevelDB is optional - graceful fallback to memory
try:
    import plyvel
    LEVELDB_AVAILABLE = True
except ImportError:
    plyvel = None  # type: ignore
    LEVELDB_AVAILABLE = False


class UTXOStore(ABC):
    """Abstract interface for UTXO storage backends."""

    @abstractmethod
    def add_utxo(
        self,
        address: str,
        txid: str,
        vout: int,
        amount: float,
        script_pubkey: str,
    ) -> bool:
        """Add a UTXO to storage. Returns True if added, False if duplicate."""
        ...

    @abstractmethod
    def mark_spent(self, txid: str, vout: int) -> bool:
        """Mark a UTXO as spent. Returns True if found and marked."""
        ...

    @abstractmethod
    def get_utxo(self, txid: str, vout: int) -> dict[str, Any] | None:
        """Get a specific UTXO by txid:vout. Returns None if not found."""
        ...

    @abstractmethod
    def get_utxos_for_address(self, address: str) -> list[dict[str, Any]]:
        """Get all unspent UTXOs for an address."""
        ...

    @abstractmethod
    def get_balance(self, address: str) -> float:
        """Get total balance for an address."""
        ...

    @abstractmethod
    def get_stats(self) -> dict[str, Any]:
        """Get storage statistics (total_utxos, total_value)."""
        ...

    @abstractmethod
    def snapshot_digest(self) -> str:
        """Generate deterministic hash of UTXO state."""
        ...

    @abstractmethod
    def to_dict(self) -> dict[str, Any]:
        """Export entire UTXO set as dict (for checkpoints)."""
        ...

    @abstractmethod
    def load_from_dict(self, data: dict[str, Any]) -> None:
        """Load UTXO set from dict (for restore)."""
        ...

    @abstractmethod
    def clear(self) -> None:
        """Clear all UTXOs."""
        ...


class MemoryUTXOStore(UTXOStore):
    """
    In-memory UTXO storage using Python dicts.

    Thread-safe with RLock. Suitable for testing and small UTXO sets.
    Can be serialized to JSON for checkpoints.
    """

    def __init__(self) -> None:
        # Primary storage: address -> list of UTXOs
        self._utxo_set: dict[str, list[dict[str, Any]]] = defaultdict(list)
        # Index: "txid:vout" -> (address, utxo_dict) for O(1) lookups
        self._utxo_index: dict[str, tuple[str, dict[str, Any]]] = {}
        self._lock = RLock()
        self._total_utxos = 0
        self._total_value = 0.0

    def add_utxo(
        self,
        address: str,
        txid: str,
        vout: int,
        amount: float,
        script_pubkey: str,
    ) -> bool:
        utxo_key = f"{txid}:{vout}"
        with self._lock:
            if utxo_key in self._utxo_index:
                return False  # Duplicate

            utxo = {
                "txid": txid,
                "vout": vout,
                "amount": amount,
                "script_pubkey": script_pubkey,
                "address": address,
                "spent": False,
            }
            self._utxo_set[address].append(utxo)
            self._utxo_index[utxo_key] = (address, utxo)
            self._total_utxos += 1
            self._total_value += amount
            return True

    def mark_spent(self, txid: str, vout: int) -> bool:
        utxo_key = f"{txid}:{vout}"
        with self._lock:
            if utxo_key not in self._utxo_index:
                return False

            address, utxo = self._utxo_index[utxo_key]
            if utxo["spent"]:
                return False

            utxo["spent"] = True
            self._total_value -= utxo["amount"]
            self._total_utxos = max(0, self._total_utxos - 1)
            del self._utxo_index[utxo_key]
            return True

    def get_utxo(self, txid: str, vout: int) -> dict[str, Any] | None:
        utxo_key = f"{txid}:{vout}"
        with self._lock:
            if utxo_key in self._utxo_index:
                _, utxo = self._utxo_index[utxo_key]
                if not utxo["spent"]:
                    return utxo.copy()
            return None

    def get_utxos_for_address(self, address: str) -> list[dict[str, Any]]:
        with self._lock:
            return [
                utxo.copy() for utxo in self._utxo_set.get(address, [])
                if not utxo["spent"]
            ]

    def get_balance(self, address: str) -> float:
        with self._lock:
            return sum(
                utxo["amount"] for utxo in self._utxo_set.get(address, [])
                if not utxo["spent"]
            )

    def get_stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "total_utxos": self._total_utxos,
                "total_value": self._total_value,
                "backend": "memory",
            }

    def snapshot_digest(self) -> str:
        with self._lock:
            entries = []
            for addr, utxos in self._utxo_set.items():
                for utxo in utxos:
                    entries.append(
                        f"{addr}:{utxo['txid']}:{utxo['vout']}:{utxo['amount']}:{int(utxo.get('spent', False))}"
                    )
            entries.sort()
            payload = "|".join(entries)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        with self._lock:
            return {
                addr: [utxo.copy() for utxo in utxos]
                for addr, utxos in self._utxo_set.items()
            }

    def load_from_dict(self, data: dict[str, Any]) -> None:
        with self._lock:
            self._utxo_set.clear()
            self._utxo_index.clear()
            self._total_utxos = 0
            self._total_value = 0.0

            for address, utxos in data.items():
                for utxo in utxos:
                    self._utxo_set[address].append(utxo)
                    if not utxo.get("spent", False):
                        utxo_key = f"{utxo['txid']}:{utxo['vout']}"
                        self._utxo_index[utxo_key] = (address, utxo)
                        self._total_utxos += 1
                        self._total_value += utxo.get("amount", 0.0)

    def clear(self) -> None:
        with self._lock:
            self._utxo_set.clear()
            self._utxo_index.clear()
            self._total_utxos = 0
            self._total_value = 0.0


class LevelDBUTXOStore(UTXOStore):
    """
    High-performance LevelDB-based UTXO storage.

    Key schema:
    - "utxo:{txid}:{vout}" -> UTXO JSON (primary storage)
    - "addr:{address}:{txid}:{vout}" -> "1" (address index for range scans)
    - "stats:total_utxos" -> count
    - "stats:total_value" -> value

    Thread-safe with RLock. Uses atomic batch writes for consistency.
    """

    def __init__(self, db_path: str, create_if_missing: bool = True) -> None:
        if not LEVELDB_AVAILABLE:
            raise ImportError(
                "plyvel not installed. Install with: pip install plyvel"
            )

        self._db_path = db_path
        self._db = plyvel.DB(db_path, create_if_missing=create_if_missing)
        self._lock = RLock()
        self._load_stats()

    def _load_stats(self) -> None:
        """Load cached stats from DB."""
        try:
            val = self._db.get(b"stats:total_utxos")
            self._total_utxos = int(val.decode()) if val else 0
        except (ValueError, AttributeError):
            self._total_utxos = 0

        try:
            val = self._db.get(b"stats:total_value")
            self._total_value = float(val.decode()) if val else 0.0
        except (ValueError, AttributeError):
            self._total_value = 0.0

    def _save_stats(self, batch: Any) -> None:
        """Save stats to batch write."""
        batch.put(b"stats:total_utxos", str(self._total_utxos).encode())
        batch.put(b"stats:total_value", str(self._total_value).encode())

    def add_utxo(
        self,
        address: str,
        txid: str,
        vout: int,
        amount: float,
        script_pubkey: str,
    ) -> bool:
        utxo_key = f"utxo:{txid}:{vout}".encode()
        addr_key = f"addr:{address}:{txid}:{vout}".encode()

        with self._lock:
            # Check for duplicate
            if self._db.get(utxo_key):
                return False

            utxo = {
                "txid": txid,
                "vout": vout,
                "amount": amount,
                "script_pubkey": script_pubkey,
                "address": address,
                "spent": False,
            }

            # Atomic batch write
            batch = self._db.write_batch()
            batch.put(utxo_key, json.dumps(utxo).encode())
            batch.put(addr_key, b"1")

            self._total_utxos += 1
            self._total_value += amount
            self._save_stats(batch)

            batch.write()
            return True

    def mark_spent(self, txid: str, vout: int) -> bool:
        utxo_key = f"utxo:{txid}:{vout}".encode()

        with self._lock:
            data = self._db.get(utxo_key)
            if not data:
                return False

            utxo = json.loads(data.decode())
            if utxo.get("spent"):
                return False

            # Mark as spent
            utxo["spent"] = True
            address = utxo.get("address", "")
            addr_key = f"addr:{address}:{txid}:{vout}".encode()

            # Atomic batch write
            batch = self._db.write_batch()
            batch.put(utxo_key, json.dumps(utxo).encode())
            batch.delete(addr_key)  # Remove from address index

            self._total_value -= utxo.get("amount", 0.0)
            self._total_utxos = max(0, self._total_utxos - 1)
            self._save_stats(batch)

            batch.write()
            return True

    def get_utxo(self, txid: str, vout: int) -> dict[str, Any] | None:
        utxo_key = f"utxo:{txid}:{vout}".encode()

        with self._lock:
            data = self._db.get(utxo_key)
            if data:
                utxo = json.loads(data.decode())
                if not utxo.get("spent"):
                    return utxo
            return None

    def get_utxos_for_address(self, address: str) -> list[dict[str, Any]]:
        prefix = f"addr:{address}:".encode()
        utxos = []

        with self._lock:
            for key, _ in self._db.iterator(prefix=prefix):
                # Extract txid:vout from key
                parts = key.decode().split(":")
                if len(parts) >= 4:
                    txid = parts[2]
                    vout = int(parts[3])
                    utxo = self.get_utxo(txid, vout)
                    if utxo:
                        utxos.append(utxo)

        return utxos

    def get_balance(self, address: str) -> float:
        return sum(utxo["amount"] for utxo in self.get_utxos_for_address(address))

    def get_stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "total_utxos": self._total_utxos,
                "total_value": self._total_value,
                "backend": "leveldb",
                "db_path": self._db_path,
            }

    def snapshot_digest(self) -> str:
        entries = []
        with self._lock:
            for key, value in self._db.iterator(prefix=b"utxo:"):
                utxo = json.loads(value.decode())
                addr = utxo.get("address", "")
                entries.append(
                    f"{addr}:{utxo['txid']}:{utxo['vout']}:{utxo['amount']}:{int(utxo.get('spent', False))}"
                )
        entries.sort()
        payload = "|".join(entries)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, list[dict]] = defaultdict(list)
        with self._lock:
            for key, value in self._db.iterator(prefix=b"utxo:"):
                utxo = json.loads(value.decode())
                address = utxo.get("address", "unknown")
                result[address].append(utxo)
        return dict(result)

    def load_from_dict(self, data: dict[str, Any]) -> None:
        with self._lock:
            # Clear existing data
            batch = self._db.write_batch()
            for key, _ in self._db.iterator():
                batch.delete(key)
            batch.write()

            # Load new data
            self._total_utxos = 0
            self._total_value = 0.0

            batch = self._db.write_batch()
            for address, utxos in data.items():
                for utxo in utxos:
                    txid = utxo["txid"]
                    vout = utxo["vout"]
                    utxo_key = f"utxo:{txid}:{vout}".encode()

                    # Ensure address is in utxo
                    utxo["address"] = address
                    batch.put(utxo_key, json.dumps(utxo).encode())

                    if not utxo.get("spent", False):
                        addr_key = f"addr:{address}:{txid}:{vout}".encode()
                        batch.put(addr_key, b"1")
                        self._total_utxos += 1
                        self._total_value += utxo.get("amount", 0.0)

            self._save_stats(batch)
            batch.write()

    def clear(self) -> None:
        with self._lock:
            batch = self._db.write_batch()
            for key, _ in self._db.iterator():
                batch.delete(key)
            self._total_utxos = 0
            self._total_value = 0.0
            self._save_stats(batch)
            batch.write()

    def close(self) -> None:
        """Close the database connection."""
        if self._db:
            self._db.close()
            self._db = None

    def __del__(self) -> None:
        self.close()


def create_utxo_store(
    backend: str = "memory",
    db_path: str | None = None,
) -> UTXOStore:
    """
    Factory function to create UTXO storage backend.

    Args:
        backend: "memory" or "leveldb"
        db_path: Path for LevelDB database (required for leveldb backend)

    Returns:
        UTXOStore implementation

    Raises:
        ValueError: If backend is unknown
        ImportError: If leveldb requested but plyvel not installed
    """
    if backend == "memory":
        return MemoryUTXOStore()
    elif backend == "leveldb":
        if db_path is None:
            raise ValueError("db_path required for leveldb backend")
        return LevelDBUTXOStore(db_path)
    else:
        raise ValueError(f"Unknown backend: {backend}. Use 'memory' or 'leveldb'")
