"""
Comprehensive unit tests for UTXO Storage Backend Abstraction.

Tests UTXOStore, MemoryUTXOStore, LevelDBUTXOStore classes including:
- Core CRUD operations (add, mark_spent, get)
- Address-based queries and balance calculations
- Persistence and recovery (load_from_dict, to_dict)
- Concurrent access patterns with thread safety
- Snapshot digest determinism
- Factory function behavior
- Edge cases and boundary conditions
"""

import hashlib
import json
import os
import shutil
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from xai.core.transactions.utxo_store import (
    LEVELDB_AVAILABLE,
    LevelDBUTXOStore,
    MemoryUTXOStore,
    UTXOStore,
    create_utxo_store,
)


# -----------------------------------------------------------------------------
# Test Fixtures
# -----------------------------------------------------------------------------

@pytest.fixture
def memory_store():
    """Create a fresh MemoryUTXOStore for each test."""
    return MemoryUTXOStore()


@pytest.fixture
def populated_memory_store():
    """Create a MemoryUTXOStore with pre-populated test data."""
    store = MemoryUTXOStore()
    # Add multiple UTXOs for different addresses
    store.add_utxo("addr1", "tx_aaa", 0, 100.0, "script_a")
    store.add_utxo("addr1", "tx_bbb", 0, 50.0, "script_b")
    store.add_utxo("addr1", "tx_ccc", 1, 25.0, "script_c")
    store.add_utxo("addr2", "tx_ddd", 0, 200.0, "script_d")
    store.add_utxo("addr3", "tx_eee", 0, 75.0, "script_e")
    return store


@pytest.fixture
def leveldb_store(tmp_path):
    """Create a LevelDBUTXOStore if plyvel is available, otherwise skip."""
    if not LEVELDB_AVAILABLE:
        pytest.skip("plyvel not installed, skipping LevelDB tests")
    db_path = str(tmp_path / "utxo_test.db")
    store = LevelDBUTXOStore(db_path)
    yield store
    store.close()


@pytest.fixture
def populated_leveldb_store(tmp_path):
    """Create a populated LevelDBUTXOStore if plyvel is available."""
    if not LEVELDB_AVAILABLE:
        pytest.skip("plyvel not installed, skipping LevelDB tests")
    db_path = str(tmp_path / "utxo_test_populated.db")
    store = LevelDBUTXOStore(db_path)
    store.add_utxo("addr1", "tx_aaa", 0, 100.0, "script_a")
    store.add_utxo("addr1", "tx_bbb", 0, 50.0, "script_b")
    store.add_utxo("addr2", "tx_ccc", 0, 200.0, "script_c")
    yield store
    store.close()


# -----------------------------------------------------------------------------
# MemoryUTXOStore Tests
# -----------------------------------------------------------------------------

class TestMemoryUTXOStoreBasicOperations:
    """Test basic CRUD operations for MemoryUTXOStore."""

    def test_add_utxo_success(self, memory_store):
        """Test adding a new UTXO returns True."""
        result = memory_store.add_utxo("addr1", "tx_abc", 0, 10.5, "script_pub")
        assert result is True

    def test_add_utxo_duplicate_returns_false(self, memory_store):
        """Test adding duplicate UTXO returns False."""
        memory_store.add_utxo("addr1", "tx_abc", 0, 10.5, "script_pub")
        result = memory_store.add_utxo("addr1", "tx_abc", 0, 10.5, "script_pub")
        assert result is False

    def test_add_utxo_same_txid_different_vout(self, memory_store):
        """Test adding UTXOs with same txid but different vout succeeds."""
        assert memory_store.add_utxo("addr1", "tx_abc", 0, 10.0, "script") is True
        assert memory_store.add_utxo("addr1", "tx_abc", 1, 20.0, "script") is True
        assert memory_store.add_utxo("addr1", "tx_abc", 2, 30.0, "script") is True

    def test_get_utxo_returns_correct_data(self, memory_store):
        """Test get_utxo returns correct UTXO data."""
        memory_store.add_utxo("addr1", "tx_xyz", 5, 42.5, "script_test")
        utxo = memory_store.get_utxo("tx_xyz", 5)

        assert utxo is not None
        assert utxo["txid"] == "tx_xyz"
        assert utxo["vout"] == 5
        assert utxo["amount"] == 42.5
        assert utxo["script_pubkey"] == "script_test"
        assert utxo["address"] == "addr1"
        assert utxo["spent"] is False

    def test_get_utxo_nonexistent_returns_none(self, memory_store):
        """Test get_utxo returns None for non-existent UTXO."""
        assert memory_store.get_utxo("nonexistent", 0) is None

    def test_get_utxo_returns_copy(self, memory_store):
        """Test that get_utxo returns a copy, not a reference."""
        memory_store.add_utxo("addr1", "tx_abc", 0, 10.0, "script")
        utxo1 = memory_store.get_utxo("tx_abc", 0)
        utxo2 = memory_store.get_utxo("tx_abc", 0)

        utxo1["amount"] = 9999.0  # Modify the returned copy
        assert memory_store.get_utxo("tx_abc", 0)["amount"] == 10.0  # Original unchanged
        assert utxo2["amount"] == 10.0  # Other copy unchanged

    def test_mark_spent_success(self, memory_store):
        """Test marking UTXO as spent returns True."""
        memory_store.add_utxo("addr1", "tx_abc", 0, 10.0, "script")
        result = memory_store.mark_spent("tx_abc", 0)
        assert result is True

    def test_mark_spent_nonexistent_returns_false(self, memory_store):
        """Test marking non-existent UTXO as spent returns False."""
        result = memory_store.mark_spent("nonexistent", 0)
        assert result is False

    def test_mark_spent_already_spent_returns_false(self, memory_store):
        """Test marking already spent UTXO returns False."""
        memory_store.add_utxo("addr1", "tx_abc", 0, 10.0, "script")
        memory_store.mark_spent("tx_abc", 0)
        result = memory_store.mark_spent("tx_abc", 0)
        assert result is False

    def test_get_utxo_after_mark_spent_returns_none(self, memory_store):
        """Test get_utxo returns None after UTXO is marked spent."""
        memory_store.add_utxo("addr1", "tx_abc", 0, 10.0, "script")
        memory_store.mark_spent("tx_abc", 0)
        assert memory_store.get_utxo("tx_abc", 0) is None


class TestMemoryUTXOStoreAddressQueries:
    """Test address-based queries for MemoryUTXOStore."""

    def test_get_utxos_for_address_single(self, memory_store):
        """Test getting UTXOs for address with single UTXO."""
        memory_store.add_utxo("addr1", "tx_abc", 0, 10.0, "script")
        utxos = memory_store.get_utxos_for_address("addr1")

        assert len(utxos) == 1
        assert utxos[0]["txid"] == "tx_abc"

    def test_get_utxos_for_address_multiple(self, populated_memory_store):
        """Test getting UTXOs for address with multiple UTXOs."""
        utxos = populated_memory_store.get_utxos_for_address("addr1")
        assert len(utxos) == 3
        txids = {u["txid"] for u in utxos}
        assert txids == {"tx_aaa", "tx_bbb", "tx_ccc"}

    def test_get_utxos_for_address_empty(self, memory_store):
        """Test getting UTXOs for address with no UTXOs."""
        utxos = memory_store.get_utxos_for_address("nonexistent_addr")
        assert utxos == []

    def test_get_utxos_for_address_excludes_spent(self, populated_memory_store):
        """Test that get_utxos_for_address excludes spent UTXOs."""
        populated_memory_store.mark_spent("tx_aaa", 0)
        utxos = populated_memory_store.get_utxos_for_address("addr1")

        assert len(utxos) == 2
        txids = {u["txid"] for u in utxos}
        assert "tx_aaa" not in txids

    def test_get_utxos_for_address_returns_copies(self, memory_store):
        """Test that returned UTXOs are copies."""
        memory_store.add_utxo("addr1", "tx_abc", 0, 10.0, "script")
        utxos = memory_store.get_utxos_for_address("addr1")
        utxos[0]["amount"] = 9999.0

        fresh = memory_store.get_utxos_for_address("addr1")
        assert fresh[0]["amount"] == 10.0

    def test_get_balance_single_utxo(self, memory_store):
        """Test balance calculation with single UTXO."""
        memory_store.add_utxo("addr1", "tx_abc", 0, 42.5, "script")
        assert memory_store.get_balance("addr1") == 42.5

    def test_get_balance_multiple_utxos(self, populated_memory_store):
        """Test balance calculation with multiple UTXOs."""
        # addr1 has 100.0 + 50.0 + 25.0 = 175.0
        assert populated_memory_store.get_balance("addr1") == 175.0

    def test_get_balance_after_spend(self, populated_memory_store):
        """Test balance calculation after spending UTXOs."""
        populated_memory_store.mark_spent("tx_aaa", 0)  # Spend 100.0
        assert populated_memory_store.get_balance("addr1") == 75.0  # 50.0 + 25.0

    def test_get_balance_nonexistent_address(self, memory_store):
        """Test balance for non-existent address is 0."""
        assert memory_store.get_balance("nonexistent") == 0.0

    def test_get_balance_all_spent(self, memory_store):
        """Test balance is 0 when all UTXOs are spent."""
        memory_store.add_utxo("addr1", "tx_abc", 0, 10.0, "script")
        memory_store.mark_spent("tx_abc", 0)
        assert memory_store.get_balance("addr1") == 0.0


class TestMemoryUTXOStoreStats:
    """Test statistics tracking for MemoryUTXOStore."""

    def test_get_stats_empty(self, memory_store):
        """Test stats for empty store."""
        stats = memory_store.get_stats()
        assert stats["total_utxos"] == 0
        assert stats["total_value"] == 0.0
        assert stats["backend"] == "memory"

    def test_get_stats_after_adds(self, populated_memory_store):
        """Test stats after adding UTXOs."""
        stats = populated_memory_store.get_stats()
        # 5 UTXOs: 100 + 50 + 25 + 200 + 75 = 450
        assert stats["total_utxos"] == 5
        assert stats["total_value"] == 450.0

    def test_get_stats_after_spend(self, populated_memory_store):
        """Test stats are updated after spending."""
        populated_memory_store.mark_spent("tx_aaa", 0)  # 100.0
        stats = populated_memory_store.get_stats()
        assert stats["total_utxos"] == 4
        assert stats["total_value"] == 350.0

    def test_stats_total_utxos_never_negative(self, memory_store):
        """Test that total_utxos never goes negative."""
        memory_store.add_utxo("addr1", "tx_abc", 0, 10.0, "script")
        memory_store.mark_spent("tx_abc", 0)
        # Try to mark spent again (should fail, but ensure no underflow)
        memory_store.mark_spent("tx_abc", 0)
        stats = memory_store.get_stats()
        assert stats["total_utxos"] >= 0


class TestMemoryUTXOStoreSnapshotDigest:
    """Test deterministic snapshot digests for MemoryUTXOStore."""

    def test_snapshot_digest_empty(self, memory_store):
        """Test snapshot digest for empty store."""
        digest = memory_store.snapshot_digest()
        # Empty payload should hash to SHA256 of empty string
        expected = hashlib.sha256(b"").hexdigest()
        assert digest == expected

    def test_snapshot_digest_deterministic(self, memory_store):
        """Test that snapshot digest is deterministic."""
        memory_store.add_utxo("addr1", "tx_abc", 0, 10.0, "script")
        memory_store.add_utxo("addr2", "tx_def", 1, 20.0, "script2")

        digest1 = memory_store.snapshot_digest()
        digest2 = memory_store.snapshot_digest()
        assert digest1 == digest2

    def test_snapshot_digest_order_independent(self):
        """Test that digest is the same regardless of insertion order."""
        store1 = MemoryUTXOStore()
        store1.add_utxo("addr1", "tx_abc", 0, 10.0, "script")
        store1.add_utxo("addr2", "tx_def", 0, 20.0, "script")

        store2 = MemoryUTXOStore()
        store2.add_utxo("addr2", "tx_def", 0, 20.0, "script")
        store2.add_utxo("addr1", "tx_abc", 0, 10.0, "script")

        assert store1.snapshot_digest() == store2.snapshot_digest()

    def test_snapshot_digest_changes_with_state(self, memory_store):
        """Test that digest changes when state changes."""
        memory_store.add_utxo("addr1", "tx_abc", 0, 10.0, "script")
        digest1 = memory_store.snapshot_digest()

        memory_store.add_utxo("addr2", "tx_def", 0, 20.0, "script")
        digest2 = memory_store.snapshot_digest()

        assert digest1 != digest2

    def test_snapshot_digest_includes_spent_status(self, memory_store):
        """Test that digest reflects spent status."""
        memory_store.add_utxo("addr1", "tx_abc", 0, 10.0, "script")
        digest1 = memory_store.snapshot_digest()

        memory_store.mark_spent("tx_abc", 0)
        digest2 = memory_store.snapshot_digest()

        assert digest1 != digest2


class TestMemoryUTXOStorePersistence:
    """Test serialization and deserialization for MemoryUTXOStore."""

    def test_to_dict_empty(self, memory_store):
        """Test to_dict for empty store."""
        data = memory_store.to_dict()
        assert data == {}

    def test_to_dict_with_data(self, populated_memory_store):
        """Test to_dict exports all UTXOs."""
        data = populated_memory_store.to_dict()

        assert "addr1" in data
        assert "addr2" in data
        assert "addr3" in data
        assert len(data["addr1"]) == 3
        assert len(data["addr2"]) == 1

    def test_load_from_dict_empty(self, memory_store):
        """Test load_from_dict with empty data."""
        memory_store.add_utxo("addr1", "tx_abc", 0, 10.0, "script")
        memory_store.load_from_dict({})

        assert memory_store.get_stats()["total_utxos"] == 0

    def test_load_from_dict_restores_state(self, memory_store):
        """Test load_from_dict restores full state."""
        data = {
            "addr1": [
                {"txid": "tx_aaa", "vout": 0, "amount": 100.0, "script_pubkey": "s1", "spent": False},
                {"txid": "tx_bbb", "vout": 0, "amount": 50.0, "script_pubkey": "s2", "spent": True},
            ],
            "addr2": [
                {"txid": "tx_ccc", "vout": 0, "amount": 200.0, "script_pubkey": "s3", "spent": False},
            ],
        }
        memory_store.load_from_dict(data)

        # Only unspent UTXOs should be counted
        stats = memory_store.get_stats()
        assert stats["total_utxos"] == 2  # tx_aaa and tx_ccc (tx_bbb is spent)
        assert stats["total_value"] == 300.0

        # Can retrieve unspent
        assert memory_store.get_utxo("tx_aaa", 0) is not None
        assert memory_store.get_utxo("tx_ccc", 0) is not None

        # Cannot retrieve spent
        assert memory_store.get_utxo("tx_bbb", 0) is None

    def test_round_trip_preserves_state(self, populated_memory_store):
        """Test that export and import preserves state."""
        original_digest = populated_memory_store.snapshot_digest()
        data = populated_memory_store.to_dict()

        new_store = MemoryUTXOStore()
        new_store.load_from_dict(data)

        assert new_store.snapshot_digest() == original_digest

    def test_load_from_dict_clears_previous_state(self, populated_memory_store):
        """Test that load_from_dict clears existing state first."""
        new_data = {
            "new_addr": [
                {"txid": "tx_new", "vout": 0, "amount": 10.0, "script_pubkey": "s", "spent": False}
            ]
        }
        populated_memory_store.load_from_dict(new_data)

        # Old data should be gone
        assert populated_memory_store.get_utxo("tx_aaa", 0) is None
        assert populated_memory_store.get_balance("addr1") == 0.0

        # New data should be present
        assert populated_memory_store.get_utxo("tx_new", 0) is not None


class TestMemoryUTXOStoreClear:
    """Test clear operation for MemoryUTXOStore."""

    def test_clear_removes_all_utxos(self, populated_memory_store):
        """Test clear removes all UTXOs."""
        populated_memory_store.clear()

        assert populated_memory_store.get_stats()["total_utxos"] == 0
        assert populated_memory_store.get_stats()["total_value"] == 0.0
        assert populated_memory_store.get_utxo("tx_aaa", 0) is None

    def test_clear_allows_fresh_adds(self, populated_memory_store):
        """Test that clear allows adding new UTXOs."""
        populated_memory_store.clear()
        result = populated_memory_store.add_utxo("new_addr", "tx_new", 0, 100.0, "s")

        assert result is True
        assert populated_memory_store.get_utxo("tx_new", 0) is not None


class TestMemoryUTXOStoreConcurrency:
    """Test thread safety for MemoryUTXOStore."""

    def test_concurrent_adds_no_duplicates(self, memory_store):
        """Test that concurrent adds don't create duplicates."""
        results = []

        def add_utxo():
            result = memory_store.add_utxo("addr", "tx_same", 0, 10.0, "script")
            results.append(result)

        threads = [threading.Thread(target=add_utxo) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Exactly one should succeed
        assert sum(results) == 1
        assert memory_store.get_stats()["total_utxos"] == 1

    def test_concurrent_add_and_spend(self, memory_store):
        """Test concurrent add and spend operations."""
        # Pre-add UTXOs
        for i in range(100):
            memory_store.add_utxo(f"addr{i}", f"tx_{i}", 0, 10.0, "script")

        errors = []

        def spend_random(start, end):
            for i in range(start, end):
                try:
                    memory_store.mark_spent(f"tx_{i}", 0)
                except Exception as e:
                    errors.append(e)

        def add_more(start):
            for i in range(start, start + 50):
                try:
                    memory_store.add_utxo(f"addr_new{i}", f"tx_new_{i}", 0, 5.0, "s")
                except Exception as e:
                    errors.append(e)

        threads = [
            threading.Thread(target=spend_random, args=(0, 50)),
            threading.Thread(target=spend_random, args=(50, 100)),
            threading.Thread(target=add_more, args=(200,)),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0

    def test_concurrent_reads_consistent(self, populated_memory_store):
        """Test that concurrent reads are consistent."""
        results = []

        def read_balance():
            for _ in range(100):
                balance = populated_memory_store.get_balance("addr1")
                results.append(balance)

        threads = [threading.Thread(target=read_balance) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All reads should return the same value
        assert all(r == 175.0 for r in results)

    def test_concurrent_get_stats(self, memory_store):
        """Test get_stats during concurrent modifications."""
        errors = []

        def add_utxos():
            for i in range(50):
                try:
                    memory_store.add_utxo(f"addr_{i}", f"tx_{i}", 0, 10.0, "s")
                except Exception as e:
                    errors.append(e)

        def check_stats():
            for _ in range(50):
                try:
                    stats = memory_store.get_stats()
                    # Stats should always be consistent
                    assert stats["total_utxos"] >= 0
                    assert stats["total_value"] >= 0.0
                except Exception as e:
                    errors.append(e)

        threads = [
            threading.Thread(target=add_utxos),
            threading.Thread(target=check_stats),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0


class TestMemoryUTXOStoreEdgeCases:
    """Test edge cases and boundary conditions for MemoryUTXOStore."""

    def test_zero_amount_utxo(self, memory_store):
        """Test handling of zero amount UTXO."""
        result = memory_store.add_utxo("addr", "tx", 0, 0.0, "script")
        assert result is True
        utxo = memory_store.get_utxo("tx", 0)
        assert utxo["amount"] == 0.0

    def test_very_large_amount(self, memory_store):
        """Test handling of very large amounts."""
        large_amount = 21_000_000_000_000.0  # 21 trillion
        result = memory_store.add_utxo("addr", "tx", 0, large_amount, "script")
        assert result is True
        assert memory_store.get_balance("addr") == large_amount

    def test_float_precision(self, memory_store):
        """Test float precision handling."""
        memory_store.add_utxo("addr", "tx1", 0, 0.00000001, "s")
        memory_store.add_utxo("addr", "tx2", 0, 0.00000002, "s")
        balance = memory_store.get_balance("addr")
        assert abs(balance - 0.00000003) < 1e-12

    def test_empty_address(self, memory_store):
        """Test handling of empty address string."""
        result = memory_store.add_utxo("", "tx", 0, 10.0, "script")
        assert result is True
        assert memory_store.get_balance("") == 10.0

    def test_special_characters_in_txid(self, memory_store):
        """Test handling of special characters in txid."""
        txid = "tx_abc123!@#$%^&*()_+-=[]{}|;':\",./<>?"
        result = memory_store.add_utxo("addr", txid, 0, 10.0, "script")
        assert result is True
        assert memory_store.get_utxo(txid, 0) is not None

    def test_very_large_vout(self, memory_store):
        """Test handling of very large vout index."""
        result = memory_store.add_utxo("addr", "tx", 2**31 - 1, 10.0, "script")
        assert result is True
        assert memory_store.get_utxo("tx", 2**31 - 1) is not None

    def test_many_utxos_single_address(self, memory_store):
        """Test handling of many UTXOs for a single address."""
        for i in range(1000):
            memory_store.add_utxo("addr", f"tx_{i}", 0, 1.0, "script")

        utxos = memory_store.get_utxos_for_address("addr")
        assert len(utxos) == 1000
        assert memory_store.get_balance("addr") == 1000.0


# -----------------------------------------------------------------------------
# LevelDBUTXOStore Tests (Conditional on plyvel availability)
# -----------------------------------------------------------------------------

@pytest.mark.skipif(not LEVELDB_AVAILABLE, reason="plyvel not installed")
class TestLevelDBUTXOStoreBasicOperations:
    """Test basic CRUD operations for LevelDBUTXOStore."""

    def test_add_utxo_success(self, leveldb_store):
        """Test adding a new UTXO returns True."""
        result = leveldb_store.add_utxo("addr1", "tx_abc", 0, 10.5, "script_pub")
        assert result is True

    def test_add_utxo_duplicate_returns_false(self, leveldb_store):
        """Test adding duplicate UTXO returns False."""
        leveldb_store.add_utxo("addr1", "tx_abc", 0, 10.5, "script_pub")
        result = leveldb_store.add_utxo("addr1", "tx_abc", 0, 10.5, "script_pub")
        assert result is False

    def test_get_utxo_returns_correct_data(self, leveldb_store):
        """Test get_utxo returns correct UTXO data."""
        leveldb_store.add_utxo("addr1", "tx_xyz", 5, 42.5, "script_test")
        utxo = leveldb_store.get_utxo("tx_xyz", 5)

        assert utxo is not None
        assert utxo["txid"] == "tx_xyz"
        assert utxo["vout"] == 5
        assert utxo["amount"] == 42.5

    def test_mark_spent_success(self, leveldb_store):
        """Test marking UTXO as spent returns True."""
        leveldb_store.add_utxo("addr1", "tx_abc", 0, 10.0, "script")
        result = leveldb_store.mark_spent("tx_abc", 0)
        assert result is True

    def test_mark_spent_removes_from_queries(self, leveldb_store):
        """Test that marking spent removes UTXO from queries."""
        leveldb_store.add_utxo("addr1", "tx_abc", 0, 10.0, "script")
        leveldb_store.mark_spent("tx_abc", 0)

        assert leveldb_store.get_utxo("tx_abc", 0) is None
        assert leveldb_store.get_utxos_for_address("addr1") == []
        assert leveldb_store.get_balance("addr1") == 0.0


@pytest.mark.skipif(not LEVELDB_AVAILABLE, reason="plyvel not installed")
class TestLevelDBUTXOStoreAddressQueries:
    """Test address-based queries for LevelDBUTXOStore."""

    def test_get_utxos_for_address(self, populated_leveldb_store):
        """Test getting UTXOs for address."""
        utxos = populated_leveldb_store.get_utxos_for_address("addr1")
        assert len(utxos) == 2

    def test_get_balance(self, populated_leveldb_store):
        """Test balance calculation."""
        assert populated_leveldb_store.get_balance("addr1") == 150.0  # 100 + 50
        assert populated_leveldb_store.get_balance("addr2") == 200.0


@pytest.mark.skipif(not LEVELDB_AVAILABLE, reason="plyvel not installed")
class TestLevelDBUTXOStorePersistence:
    """Test persistence operations for LevelDBUTXOStore."""

    def test_persistence_across_close_reopen(self, tmp_path):
        """Test data persists after close and reopen."""
        db_path = str(tmp_path / "persist_test.db")

        # Create and populate
        store1 = LevelDBUTXOStore(db_path)
        store1.add_utxo("addr1", "tx_abc", 0, 100.0, "script")
        store1.add_utxo("addr2", "tx_def", 0, 200.0, "script")
        digest1 = store1.snapshot_digest()
        store1.close()

        # Reopen and verify
        store2 = LevelDBUTXOStore(db_path)
        assert store2.get_utxo("tx_abc", 0) is not None
        assert store2.get_balance("addr1") == 100.0
        assert store2.snapshot_digest() == digest1
        store2.close()

    def test_stats_persist_across_close_reopen(self, tmp_path):
        """Test that stats are persisted and restored."""
        db_path = str(tmp_path / "stats_test.db")

        store1 = LevelDBUTXOStore(db_path)
        store1.add_utxo("addr1", "tx1", 0, 100.0, "s")
        store1.add_utxo("addr1", "tx2", 0, 50.0, "s")
        store1.close()

        store2 = LevelDBUTXOStore(db_path)
        stats = store2.get_stats()
        assert stats["total_utxos"] == 2
        assert stats["total_value"] == 150.0
        store2.close()

    def test_to_dict_and_load_from_dict(self, leveldb_store):
        """Test export and import functionality."""
        leveldb_store.add_utxo("addr1", "tx1", 0, 100.0, "s")
        leveldb_store.add_utxo("addr2", "tx2", 0, 200.0, "s")

        data = leveldb_store.to_dict()
        assert "addr1" in data
        assert "addr2" in data

        leveldb_store.clear()
        leveldb_store.load_from_dict(data)

        assert leveldb_store.get_utxo("tx1", 0) is not None
        assert leveldb_store.get_balance("addr1") == 100.0


@pytest.mark.skipif(not LEVELDB_AVAILABLE, reason="plyvel not installed")
class TestLevelDBUTXOStoreClear:
    """Test clear operation for LevelDBUTXOStore."""

    def test_clear_removes_all_data(self, populated_leveldb_store):
        """Test clear removes all UTXOs from database."""
        populated_leveldb_store.clear()

        stats = populated_leveldb_store.get_stats()
        assert stats["total_utxos"] == 0
        assert stats["total_value"] == 0.0
        assert populated_leveldb_store.get_utxo("tx_aaa", 0) is None


@pytest.mark.skipif(not LEVELDB_AVAILABLE, reason="plyvel not installed")
class TestLevelDBUTXOStoreStats:
    """Test statistics for LevelDBUTXOStore."""

    def test_get_stats_includes_backend_info(self, leveldb_store):
        """Test stats include backend and path info."""
        stats = leveldb_store.get_stats()
        assert stats["backend"] == "leveldb"
        assert "db_path" in stats


@pytest.mark.skipif(not LEVELDB_AVAILABLE, reason="plyvel not installed")
class TestLevelDBUTXOStoreErrorHandling:
    """Test error handling for LevelDBUTXOStore."""

    def test_import_error_without_plyvel(self):
        """Test that ImportError is raised when plyvel not available."""
        with patch("xai.core.transactions.utxo_store.LEVELDB_AVAILABLE", False):
            with patch("xai.core.transactions.utxo_store.plyvel", None):
                # Re-import to get new behavior
                from importlib import reload
                import xai.core.transactions.utxo_store as store_module

                # The class should raise ImportError on instantiation
                # when LEVELDB_AVAILABLE is False
                original_available = store_module.LEVELDB_AVAILABLE
                store_module.LEVELDB_AVAILABLE = False

                try:
                    with pytest.raises(ImportError):
                        LevelDBUTXOStore("/tmp/test.db")
                finally:
                    store_module.LEVELDB_AVAILABLE = original_available


# -----------------------------------------------------------------------------
# Factory Function Tests
# -----------------------------------------------------------------------------

class TestCreateUTXOStore:
    """Test the create_utxo_store factory function."""

    def test_create_memory_store_default(self):
        """Test creating memory store (default)."""
        store = create_utxo_store()
        assert isinstance(store, MemoryUTXOStore)

    def test_create_memory_store_explicit(self):
        """Test creating memory store explicitly."""
        store = create_utxo_store(backend="memory")
        assert isinstance(store, MemoryUTXOStore)

    def test_create_unknown_backend_raises(self):
        """Test that unknown backend raises ValueError."""
        with pytest.raises(ValueError, match="Unknown backend"):
            create_utxo_store(backend="unknown")

    def test_create_leveldb_without_path_raises(self):
        """Test that leveldb without db_path raises ValueError."""
        with pytest.raises(ValueError, match="db_path required"):
            create_utxo_store(backend="leveldb")

    @pytest.mark.skipif(not LEVELDB_AVAILABLE, reason="plyvel not installed")
    def test_create_leveldb_store(self, tmp_path):
        """Test creating LevelDB store."""
        db_path = str(tmp_path / "factory_test.db")
        store = create_utxo_store(backend="leveldb", db_path=db_path)
        assert isinstance(store, LevelDBUTXOStore)
        store.close()


# -----------------------------------------------------------------------------
# Integration Tests
# -----------------------------------------------------------------------------

class TestUTXOStoreIntegration:
    """Integration tests that test realistic usage patterns."""

    def test_transaction_lifecycle(self, memory_store):
        """Test complete lifecycle: add UTXOs, spend, verify balance."""
        # Initial funding
        memory_store.add_utxo("alice", "coinbase_1", 0, 1000.0, "script")
        assert memory_store.get_balance("alice") == 1000.0

        # Alice sends to Bob
        memory_store.mark_spent("coinbase_1", 0)
        memory_store.add_utxo("bob", "tx_a2b", 0, 900.0, "script")
        memory_store.add_utxo("alice", "tx_a2b", 1, 100.0, "script")  # Change

        assert memory_store.get_balance("alice") == 100.0
        assert memory_store.get_balance("bob") == 900.0

        # Bob sends to Carol
        memory_store.mark_spent("tx_a2b", 0)
        memory_store.add_utxo("carol", "tx_b2c", 0, 800.0, "script")
        memory_store.add_utxo("bob", "tx_b2c", 1, 100.0, "script")  # Change

        assert memory_store.get_balance("bob") == 100.0
        assert memory_store.get_balance("carol") == 800.0

    def test_checkpoint_and_restore(self, memory_store):
        """Test checkpoint (to_dict) and restore (load_from_dict) workflow."""
        # Build up state
        memory_store.add_utxo("addr1", "tx1", 0, 100.0, "s")
        memory_store.add_utxo("addr2", "tx2", 0, 200.0, "s")
        memory_store.mark_spent("tx1", 0)

        # Checkpoint
        checkpoint = memory_store.to_dict()
        original_digest = memory_store.snapshot_digest()

        # Make more changes
        memory_store.add_utxo("addr3", "tx3", 0, 300.0, "s")

        # Restore to checkpoint
        memory_store.load_from_dict(checkpoint)

        # Verify state is restored
        assert memory_store.snapshot_digest() == original_digest
        assert memory_store.get_utxo("tx3", 0) is None  # tx3 should be gone

    def test_high_volume_operations(self, memory_store):
        """Test performance with high volume of operations."""
        # Add many UTXOs
        for i in range(5000):
            memory_store.add_utxo(f"addr_{i % 100}", f"tx_{i}", 0, 1.0, "s")

        assert memory_store.get_stats()["total_utxos"] == 5000

        # Spend half
        for i in range(0, 5000, 2):
            memory_store.mark_spent(f"tx_{i}", 0)

        assert memory_store.get_stats()["total_utxos"] == 2500

        # Verify balances are consistent
        total_balance = sum(memory_store.get_balance(f"addr_{i}") for i in range(100))
        assert total_balance == 2500.0

    def test_concurrent_transaction_simulation(self, memory_store):
        """Simulate concurrent transaction processing."""
        # Setup initial state
        for i in range(100):
            memory_store.add_utxo("treasury", f"initial_{i}", 0, 1000.0, "s")

        errors = []
        completed = {"count": 0}
        lock = threading.Lock()

        def process_payment(payment_id):
            try:
                # Try to spend a UTXO
                spent = memory_store.mark_spent(f"initial_{payment_id}", 0)
                if spent:
                    # Create new outputs
                    memory_store.add_utxo(f"recipient_{payment_id}", f"payment_{payment_id}", 0, 900.0, "s")
                    memory_store.add_utxo("treasury", f"payment_{payment_id}", 1, 100.0, "s")
                    with lock:
                        completed["count"] += 1
            except Exception as e:
                errors.append(e)

        # Process payments concurrently
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(process_payment, i) for i in range(100)]
            for f in as_completed(futures):
                f.result()

        assert len(errors) == 0
        assert completed["count"] == 100
