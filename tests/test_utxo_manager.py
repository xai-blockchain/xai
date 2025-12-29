"""
Test UTXO Manager functionality.

Tests cover:
- UTXO addition and removal
- Balance calculations
- UTXO set consistency
- Thread safety and locking
- Snapshot and restore
- Edge cases and validation
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from xai.core.transactions.utxo_manager import (
    MAX_UTXO_AMOUNT,
    MIN_UTXO_AMOUNT,
    UTXOManager,
    UTXOValidationError,
    get_utxo_manager,
)


class MockTransaction:
    """Mock transaction for testing UTXO processing."""

    def __init__(
        self,
        txid: str,
        sender: str,
        inputs: list[dict[str, Any]],
        outputs: list[dict[str, Any]],
    ):
        self.txid = txid
        self.sender = sender
        self.inputs = inputs
        self.outputs = outputs


@pytest.fixture
def utxo_manager():
    """Create a fresh UTXO manager for each test."""
    manager = UTXOManager()
    yield manager
    manager.reset()


@pytest.fixture
def populated_manager(utxo_manager):
    """Create a UTXO manager with some UTXOs."""
    utxo_manager.add_utxo("XAI_ADDR1", "tx001", 0, 100.0, "P2PKH XAI_ADDR1")
    utxo_manager.add_utxo("XAI_ADDR1", "tx002", 0, 50.0, "P2PKH XAI_ADDR1")
    utxo_manager.add_utxo("XAI_ADDR2", "tx003", 0, 200.0, "P2PKH XAI_ADDR2")
    return utxo_manager


class TestUTXOAddition:
    """Tests for adding UTXOs."""

    def test_add_utxo_basic(self, utxo_manager):
        """Adding a UTXO should update the set correctly."""
        utxo_manager.add_utxo("XAI_ADDR1", "txid001", 0, 100.0, "P2PKH XAI_ADDR1")

        utxos = utxo_manager.get_utxos_for_address("XAI_ADDR1")
        assert len(utxos) == 1
        assert utxos[0]["txid"] == "txid001"
        assert utxos[0]["vout"] == 0
        assert utxos[0]["amount"] == 100.0
        assert utxos[0]["spent"] is False

    def test_add_multiple_utxos_same_address(self, utxo_manager):
        """Multiple UTXOs for same address should accumulate."""
        utxo_manager.add_utxo("XAI_ADDR1", "tx001", 0, 100.0, "P2PKH")
        utxo_manager.add_utxo("XAI_ADDR1", "tx002", 0, 50.0, "P2PKH")
        utxo_manager.add_utxo("XAI_ADDR1", "tx003", 1, 25.0, "P2PKH")

        utxos = utxo_manager.get_utxos_for_address("XAI_ADDR1")
        assert len(utxos) == 3
        assert utxo_manager.get_balance("XAI_ADDR1") == 175.0

    def test_add_utxo_updates_totals(self, utxo_manager):
        """Adding UTXOs should update total counts."""
        utxo_manager.add_utxo("XAI_ADDR1", "tx001", 0, 100.0, "P2PKH")
        utxo_manager.add_utxo("XAI_ADDR2", "tx002", 0, 200.0, "P2PKH")

        assert utxo_manager.total_utxos == 2
        assert utxo_manager.total_value == 300.0

    def test_add_utxo_zero_amount(self, utxo_manager):
        """Adding UTXO with zero amount should work (allow_zero=True)."""
        utxo_manager.add_utxo("XAI_ADDR1", "tx001", 0, 0.0, "P2PKH")

        utxos = utxo_manager.get_utxos_for_address("XAI_ADDR1")
        assert len(utxos) == 1
        assert utxos[0]["amount"] == 0.0

    def test_add_utxo_negative_amount_fails(self, utxo_manager):
        """Adding UTXO with negative amount should raise error."""
        with pytest.raises(UTXOValidationError, match="cannot be negative"):
            utxo_manager.add_utxo("XAI_ADDR1", "tx001", 0, -10.0, "P2PKH")

    def test_add_utxo_exceeds_max_fails(self, utxo_manager):
        """Adding UTXO exceeding max supply should raise error."""
        with pytest.raises(UTXOValidationError, match="exceeds maximum"):
            utxo_manager.add_utxo("XAI_ADDR1", "tx001", 0, MAX_UTXO_AMOUNT + 1, "P2PKH")

    def test_add_utxo_nan_fails(self, utxo_manager):
        """Adding UTXO with NaN amount should raise error."""
        with pytest.raises(UTXOValidationError, match="NaN"):
            utxo_manager.add_utxo("XAI_ADDR1", "tx001", 0, float("nan"), "P2PKH")

    def test_add_utxo_infinity_fails(self, utxo_manager):
        """Adding UTXO with infinite amount should raise error."""
        with pytest.raises(UTXOValidationError, match="infinite"):
            utxo_manager.add_utxo("XAI_ADDR1", "tx001", 0, float("inf"), "P2PKH")

    def test_add_utxo_none_fails(self, utxo_manager):
        """Adding UTXO with None amount should raise error."""
        with pytest.raises(UTXOValidationError, match="cannot be None"):
            utxo_manager.add_utxo("XAI_ADDR1", "tx001", 0, None, "P2PKH")


class TestUTXOSpending:
    """Tests for marking UTXOs as spent."""

    def test_mark_utxo_spent(self, populated_manager):
        """Marking UTXO as spent should update state correctly."""
        result = populated_manager.mark_utxo_spent("XAI_ADDR1", "tx001", 0)

        assert result is True
        utxos = populated_manager.get_utxos_for_address("XAI_ADDR1")
        assert len(utxos) == 1  # Only tx002 remains unspent
        assert utxos[0]["txid"] == "tx002"

    def test_mark_utxo_spent_updates_totals(self, populated_manager):
        """Marking UTXO spent should update totals."""
        initial_total = populated_manager.total_utxos
        initial_value = populated_manager.total_value

        populated_manager.mark_utxo_spent("XAI_ADDR1", "tx001", 0)

        assert populated_manager.total_utxos == initial_total - 1
        assert populated_manager.total_value == initial_value - 100.0

    def test_mark_nonexistent_utxo_returns_false(self, utxo_manager):
        """Marking non-existent UTXO should return False."""
        result = utxo_manager.mark_utxo_spent("XAI_ADDR1", "nonexistent", 0)
        assert result is False

    def test_mark_already_spent_utxo_returns_false(self, populated_manager):
        """Marking already spent UTXO should return False."""
        populated_manager.mark_utxo_spent("XAI_ADDR1", "tx001", 0)
        result = populated_manager.mark_utxo_spent("XAI_ADDR1", "tx001", 0)

        assert result is False

    def test_mark_utxo_wrong_address_returns_false(self, populated_manager):
        """Marking UTXO with wrong address should return False."""
        result = populated_manager.mark_utxo_spent("WRONG_ADDR", "tx001", 0)
        assert result is False


class TestBalanceCalculation:
    """Tests for balance calculation."""

    def test_get_balance_empty_address(self, utxo_manager):
        """Balance for address with no UTXOs should be 0."""
        balance = utxo_manager.get_balance("XAI_NONEXISTENT")
        assert balance == 0.0

    def test_get_balance_single_utxo(self, utxo_manager):
        """Balance should equal single UTXO amount."""
        utxo_manager.add_utxo("XAI_ADDR1", "tx001", 0, 100.0, "P2PKH")
        assert utxo_manager.get_balance("XAI_ADDR1") == 100.0

    def test_get_balance_multiple_utxos(self, populated_manager):
        """Balance should sum all unspent UTXOs."""
        assert populated_manager.get_balance("XAI_ADDR1") == 150.0  # 100 + 50

    def test_get_balance_excludes_spent(self, populated_manager):
        """Balance should exclude spent UTXOs."""
        populated_manager.mark_utxo_spent("XAI_ADDR1", "tx001", 0)
        assert populated_manager.get_balance("XAI_ADDR1") == 50.0


class TestFindSpendableUTXOs:
    """Tests for finding spendable UTXOs."""

    def test_find_exact_amount(self, populated_manager):
        """Should find UTXOs that exactly match required amount."""
        utxos = populated_manager.find_spendable_utxos("XAI_ADDR1", 100.0)

        assert len(utxos) == 1
        assert utxos[0]["amount"] == 100.0

    def test_find_exceeds_amount(self, populated_manager):
        """Should find UTXOs that exceed required amount."""
        utxos = populated_manager.find_spendable_utxos("XAI_ADDR1", 120.0)

        assert len(utxos) == 2
        total = sum(u["amount"] for u in utxos)
        assert total >= 120.0

    def test_find_insufficient_returns_empty(self, populated_manager):
        """Should return empty list if insufficient funds."""
        utxos = populated_manager.find_spendable_utxos("XAI_ADDR1", 1000.0)
        assert utxos == []

    def test_find_from_empty_address_returns_empty(self, utxo_manager):
        """Should return empty list for address with no UTXOs."""
        utxos = utxo_manager.find_spendable_utxos("XAI_NONEXISTENT", 10.0)
        assert utxos == []


class TestUTXOLocking:
    """Tests for pending UTXO locks."""

    def test_lock_utxos(self, populated_manager):
        """Locking UTXOs should prevent them from being returned."""
        utxos = populated_manager.get_utxos_for_address("XAI_ADDR1")
        result = populated_manager.lock_utxos([utxos[0]])

        assert result is True

        # Locked UTXO should be excluded
        available = populated_manager.get_utxos_for_address("XAI_ADDR1")
        assert len(available) == 1

    def test_lock_already_locked_fails(self, populated_manager):
        """Locking already locked UTXO should fail."""
        utxos = populated_manager.get_utxos_for_address("XAI_ADDR1")
        populated_manager.lock_utxos([utxos[0]])

        result = populated_manager.lock_utxos([utxos[0]])
        assert result is False

    def test_unlock_utxos(self, populated_manager):
        """Unlocking UTXOs should make them available again."""
        utxos = populated_manager.get_utxos_for_address("XAI_ADDR1")
        populated_manager.lock_utxos([utxos[0]])
        populated_manager.unlock_utxos([utxos[0]])

        available = populated_manager.get_utxos_for_address("XAI_ADDR1")
        assert len(available) == 2

    def test_unlock_by_keys(self, populated_manager):
        """Unlocking by keys should work."""
        utxos = populated_manager.get_utxos_for_address("XAI_ADDR1")
        populated_manager.lock_utxos([utxos[0]])

        utxo_keys = [(utxos[0]["txid"], utxos[0]["vout"])]
        populated_manager.unlock_utxos_by_keys(utxo_keys)

        available = populated_manager.get_utxos_for_address("XAI_ADDR1")
        assert len(available) == 2

    def test_pending_count(self, populated_manager):
        """Pending count should reflect locked UTXOs."""
        assert populated_manager.get_pending_utxo_count() == 0

        utxos = populated_manager.get_utxos_for_address("XAI_ADDR1")
        populated_manager.lock_utxos(utxos)

        assert populated_manager.get_pending_utxo_count() == 2


class TestTransactionProcessing:
    """Tests for transaction input/output processing."""

    def test_process_transaction_outputs(self, utxo_manager):
        """Processing outputs should create UTXOs."""
        tx = MockTransaction(
            txid="tx001",
            sender="XAI_SENDER",
            inputs=[],
            outputs=[
                {"address": "XAI_RECIPIENT1", "amount": 100.0},
                {"address": "XAI_RECIPIENT2", "amount": 50.0},
            ],
        )

        utxo_manager.process_transaction_outputs(tx)

        assert utxo_manager.get_balance("XAI_RECIPIENT1") == 100.0
        assert utxo_manager.get_balance("XAI_RECIPIENT2") == 50.0

    def test_process_transaction_inputs(self, populated_manager):
        """Processing inputs should mark UTXOs as spent."""
        tx = MockTransaction(
            txid="tx_spend",
            sender="XAI_ADDR1",
            inputs=[{"txid": "tx001", "vout": 0}],
            outputs=[],
        )

        result = populated_manager.process_transaction_inputs(tx)

        assert result is True
        assert populated_manager.get_balance("XAI_ADDR1") == 50.0  # Only tx002 remains

    def test_process_coinbase_skips_inputs(self, utxo_manager):
        """Coinbase transactions should not process inputs."""
        tx = MockTransaction(
            txid="coinbase_tx",
            sender="COINBASE",
            inputs=[{"txid": "nonexistent", "vout": 0}],  # Would fail if processed
            outputs=[],
        )

        result = utxo_manager.process_transaction_inputs(tx)
        assert result is True

    def test_duplicate_input_raises_error(self, populated_manager):
        """Duplicate inputs in transaction should raise error."""
        tx = MockTransaction(
            txid="attack_tx",
            sender="XAI_ADDR1",
            inputs=[
                {"txid": "tx001", "vout": 0},
                {"txid": "tx001", "vout": 0},  # Duplicate!
            ],
            outputs=[],
        )

        with pytest.raises(UTXOValidationError, match="Duplicate input"):
            populated_manager.process_transaction_inputs(tx)


class TestSnapshotRestore:
    """Tests for snapshot and restore functionality."""

    def test_snapshot_captures_state(self, populated_manager):
        """Snapshot should capture complete state."""
        snapshot = populated_manager.snapshot()

        assert "utxo_set" in snapshot
        assert "total_utxos" in snapshot
        assert "total_value" in snapshot
        assert snapshot["total_utxos"] == 3
        assert snapshot["total_value"] == 350.0

    def test_restore_from_snapshot(self, populated_manager):
        """Restore should recreate exact state."""
        snapshot = populated_manager.snapshot()

        # Modify state
        populated_manager.mark_utxo_spent("XAI_ADDR1", "tx001", 0)
        populated_manager.add_utxo("XAI_ADDR3", "tx100", 0, 500.0, "P2PKH")

        # Restore
        populated_manager.restore(snapshot)

        assert populated_manager.total_utxos == 3
        assert populated_manager.total_value == 350.0
        assert populated_manager.get_balance("XAI_ADDR1") == 150.0

    def test_clear_removes_all(self, populated_manager):
        """Clear should remove all UTXOs."""
        populated_manager.clear()

        assert populated_manager.total_utxos == 0
        assert populated_manager.total_value == 0.0
        assert populated_manager.get_balance("XAI_ADDR1") == 0.0


class TestSerialization:
    """Tests for serialization and loading."""

    def test_to_dict(self, populated_manager):
        """to_dict should produce serializable structure."""
        data = populated_manager.to_dict()

        assert "XAI_ADDR1" in data
        assert len(data["XAI_ADDR1"]) == 2
        assert "XAI_ADDR2" in data

    def test_load_utxo_set(self, utxo_manager):
        """load_utxo_set should restore from dict."""
        data = {
            "XAI_ADDR1": [
                {"txid": "tx001", "vout": 0, "amount": 100.0, "script_pubkey": "P2PKH", "spent": False},
                {"txid": "tx002", "vout": 0, "amount": 50.0, "script_pubkey": "P2PKH", "spent": True},
            ]
        }

        utxo_manager.load_utxo_set(data)

        assert utxo_manager.get_balance("XAI_ADDR1") == 100.0  # Only unspent
        assert utxo_manager.total_utxos == 1


class TestConsistencyVerification:
    """Tests for UTXO set consistency checks."""

    def test_verify_consistent_state(self, populated_manager):
        """Consistent state should pass verification."""
        result = populated_manager.verify_utxo_consistency()

        assert result["is_consistent"] is True
        assert result["count_mismatch"] is False
        assert result["value_mismatch"] is False
        assert result["duplicates_found"] == []

    def test_detect_count_mismatch(self, populated_manager):
        """Should detect UTXO count mismatch."""
        # Manually corrupt count
        populated_manager.total_utxos = 999

        result = populated_manager.verify_utxo_consistency()
        assert result["is_consistent"] is False
        assert result["count_mismatch"] is True

    def test_detect_value_mismatch(self, populated_manager):
        """Should detect value mismatch."""
        # Manually corrupt value
        populated_manager.total_value = 9999.0

        result = populated_manager.verify_utxo_consistency()
        assert result["is_consistent"] is False
        assert result["value_mismatch"] is True


class TestMerkleRoot:
    """Tests for Merkle root calculation."""

    def test_merkle_root_deterministic(self, populated_manager):
        """Same state should produce same Merkle root."""
        root1 = populated_manager.calculate_merkle_root()
        root2 = populated_manager.calculate_merkle_root()

        assert root1 == root2
        assert len(root1) == 64  # SHA256 hex

    def test_merkle_root_changes_with_state(self, populated_manager):
        """Different states should produce different Merkle roots."""
        root1 = populated_manager.calculate_merkle_root()
        populated_manager.add_utxo("XAI_ADDR3", "tx100", 0, 10.0, "P2PKH")
        root2 = populated_manager.calculate_merkle_root()

        assert root1 != root2

    def test_merkle_root_empty_set(self, utxo_manager):
        """Empty UTXO set should have valid Merkle root."""
        root = utxo_manager.calculate_merkle_root()
        assert len(root) == 64


class TestSnapshotDigest:
    """Tests for snapshot digest."""

    def test_snapshot_digest_deterministic(self, populated_manager):
        """Same state should produce same digest."""
        digest1 = populated_manager.snapshot_digest()
        digest2 = populated_manager.snapshot_digest()

        assert digest1 == digest2

    def test_snapshot_digest_changes(self, populated_manager):
        """Different states should produce different digests."""
        digest1 = populated_manager.snapshot_digest()
        populated_manager.mark_utxo_spent("XAI_ADDR1", "tx001", 0)
        digest2 = populated_manager.snapshot_digest()

        assert digest1 != digest2


class TestCompaction:
    """Tests for UTXO set compaction."""

    def test_compact_removes_spent(self, populated_manager):
        """Compaction should remove spent UTXOs."""
        populated_manager.mark_utxo_spent("XAI_ADDR1", "tx001", 0)
        populated_manager.mark_utxo_spent("XAI_ADDR1", "tx002", 0)

        removed = populated_manager.compact_utxo_set()

        assert removed == 2

    def test_compact_preserves_unspent(self, populated_manager):
        """Compaction should preserve unspent UTXOs."""
        populated_manager.mark_utxo_spent("XAI_ADDR1", "tx001", 0)
        populated_manager.compact_utxo_set()

        assert populated_manager.get_balance("XAI_ADDR1") == 50.0
        assert populated_manager.get_balance("XAI_ADDR2") == 200.0


class TestGetUnspentOutput:
    """Tests for getting specific UTXOs."""

    def test_get_existing_utxo(self, populated_manager):
        """Should return existing unspent UTXO."""
        utxo = populated_manager.get_unspent_output("tx001", 0)

        assert utxo is not None
        assert utxo["amount"] == 100.0

    def test_get_nonexistent_utxo(self, utxo_manager):
        """Should return None for non-existent UTXO."""
        utxo = utxo_manager.get_unspent_output("nonexistent", 0)
        assert utxo is None

    def test_get_spent_utxo_returns_none(self, populated_manager):
        """Should return None for spent UTXO."""
        populated_manager.mark_utxo_spent("XAI_ADDR1", "tx001", 0)
        utxo = populated_manager.get_unspent_output("tx001", 0)

        assert utxo is None

    def test_get_pending_utxo_excluded(self, populated_manager):
        """Should return None for pending UTXO when exclude_pending=True."""
        utxos = populated_manager.get_utxos_for_address("XAI_ADDR1")
        populated_manager.lock_utxos([utxos[0]])

        result = populated_manager.get_unspent_output("tx001", 0, exclude_pending=True)
        assert result is None

    def test_get_pending_utxo_included(self, populated_manager):
        """Should return pending UTXO when exclude_pending=False."""
        utxos = populated_manager.get_utxos_for_address("XAI_ADDR1")
        populated_manager.lock_utxos([utxos[0]])

        result = populated_manager.get_unspent_output("tx001", 0, exclude_pending=False)
        assert result is not None


class TestStats:
    """Tests for statistics functions."""

    def test_get_stats(self, populated_manager):
        """Should return accurate statistics."""
        stats = populated_manager.get_stats()

        assert stats["total_utxos"] == 3
        assert stats["total_unspent_value"] == 350.0
        assert stats["unique_addresses_with_utxos"] == 2

    def test_get_total_unspent_value(self, populated_manager):
        """Should return total unspent value."""
        assert populated_manager.get_total_unspent_value() == 350.0

    def test_get_unique_addresses_count(self, populated_manager):
        """Should return count of addresses with balance."""
        count = populated_manager.get_unique_addresses_count()
        assert count == 2


class TestGlobalInstance:
    """Tests for global UTXO manager instance."""

    def test_get_utxo_manager_singleton(self):
        """get_utxo_manager should return same instance."""
        # Reset global instance first
        import xai.core.transactions.utxo_manager as um
        um._global_utxo_manager = None

        manager1 = get_utxo_manager()
        manager2 = get_utxo_manager()

        assert manager1 is manager2

        # Clean up
        um._global_utxo_manager = None


class TestThreadSafety:
    """Tests for thread safety of UTXO operations."""

    def test_concurrent_additions(self, utxo_manager):
        """Concurrent additions should be thread-safe."""
        errors = []

        def add_utxos(start_id: int):
            try:
                for i in range(100):
                    utxo_manager.add_utxo(
                        f"XAI_ADDR{start_id}",
                        f"tx{start_id}_{i}",
                        i,
                        1.0,
                        "P2PKH"
                    )
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=add_utxos, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert utxo_manager.total_utxos == 500
        assert utxo_manager.total_value == 500.0

    def test_concurrent_spend_prevents_double_spend(self, utxo_manager):
        """Concurrent spending should not allow double-spend."""
        utxo_manager.add_utxo("XAI_ADDR1", "tx001", 0, 100.0, "P2PKH")

        results = []

        def try_spend():
            result = utxo_manager.mark_utxo_spent("XAI_ADDR1", "tx001", 0)
            results.append(result)

        threads = [threading.Thread(target=try_spend) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Only one thread should succeed
        assert results.count(True) == 1
        assert results.count(False) == 9


class TestEdgeCases:
    """Edge case tests."""

    def test_very_small_amount(self, utxo_manager):
        """Should handle very small amounts."""
        utxo_manager.add_utxo("XAI_ADDR1", "tx001", 0, 0.00000001, "P2PKH")
        assert utxo_manager.get_balance("XAI_ADDR1") == 0.00000001

    def test_max_valid_amount(self, utxo_manager):
        """Should handle maximum valid amount."""
        utxo_manager.add_utxo("XAI_ADDR1", "tx001", 0, MAX_UTXO_AMOUNT, "P2PKH")
        assert utxo_manager.get_balance("XAI_ADDR1") == MAX_UTXO_AMOUNT

    def test_large_vout_index(self, utxo_manager):
        """Should handle large vout indices."""
        utxo_manager.add_utxo("XAI_ADDR1", "tx001", 999999, 10.0, "P2PKH")
        utxo = utxo_manager.get_unspent_output("tx001", 999999)
        assert utxo is not None

    def test_long_txid(self, utxo_manager):
        """Should handle standard length txid."""
        long_txid = "a" * 64  # Standard txid length
        utxo_manager.add_utxo("XAI_ADDR1", long_txid, 0, 10.0, "P2PKH")
        utxo = utxo_manager.get_unspent_output(long_txid, 0)
        assert utxo is not None

    def test_reset_clears_everything(self, populated_manager):
        """Reset should clear all state."""
        populated_manager.reset()

        assert populated_manager.total_utxos == 0
        assert populated_manager.total_value == 0.0
        assert populated_manager.get_pending_utxo_count() == 0
        assert len(populated_manager._utxo_index) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
