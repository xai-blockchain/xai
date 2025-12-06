"""
Comprehensive tests for mempool lazy deletion optimization.

Tests the O(1) amortized lazy deletion pattern that prevents expensive
heap rebuilds on transaction removal. Includes performance benchmarks.
"""

import time
import pytest
from xai.network.mempool_manager import MempoolManager


class TestMempoolLazyDeletion:
    """Tests for lazy deletion optimization in mempool"""

    def test_lazy_deletion_marks_transaction_without_heap_rebuild(self):
        """Test that removal marks transaction as deleted without immediate heap rebuild"""
        mempool = MempoolManager(
            max_transactions=100,
            eviction_policy="lowest_fee"
        )

        # Add transactions
        tx_ids = []
        for i in range(10):
            result = mempool.add_transaction(f"tx_{i}", fee=float(i))
            tx_ids.append(result["tx_id"])

        initial_heap_size = len(mempool.transaction_queue)
        assert initial_heap_size == 10

        # Remove a transaction
        mempool.remove_transaction(tx_ids[5])

        # Heap size should not immediately change (lazy deletion)
        assert len(mempool.transaction_queue) == initial_heap_size
        assert tx_ids[5] in mempool._deleted_tx_ids
        assert tx_ids[5] not in mempool.pending_transactions

    def test_pop_lowest_fee_skips_deleted_entries(self):
        """Test that popping lowest fee skips lazy-deleted entries"""
        mempool = MempoolManager(
            max_transactions=100,
            eviction_policy="lowest_fee"
        )

        # Add transactions with known fees
        result1 = mempool.add_transaction("tx_low", fee=1.0)
        result2 = mempool.add_transaction("tx_mid", fee=5.0)
        result3 = mempool.add_transaction("tx_high", fee=10.0)

        # Remove the lowest fee transaction
        mempool.remove_transaction(result1["tx_id"])

        # Pop lowest fee should skip deleted tx_1 and return tx_2
        entry = mempool._pop_lowest_fee_transaction()
        assert entry is not None
        assert entry[2] == result2["tx_id"]
        assert entry[0] == 5.0

    def test_compaction_triggers_at_threshold(self):
        """Test heap compaction when deleted entries exceed threshold"""
        mempool = MempoolManager(
            max_transactions=100,
            eviction_policy="lowest_fee"
        )
        mempool._compaction_threshold = 0.5  # 50% threshold

        # Add 100 transactions
        tx_ids = []
        for i in range(100):
            result = mempool.add_transaction(f"tx_{i}", fee=float(i))
            tx_ids.append(result["tx_id"])

        assert len(mempool.transaction_queue) == 100

        # Remove 51 transactions (>50% threshold)
        for i in range(51):
            mempool.remove_transaction(tx_ids[i])

        # Check that deleted entries were tracked
        assert len(mempool._deleted_tx_ids) == 0  # Cleared after compaction
        # Heap should be compacted to ~49 entries
        assert len(mempool.transaction_queue) < 55  # Allow some margin

    def test_batch_removal_efficiency(self):
        """Test batch removal is more efficient than individual removals"""
        mempool = MempoolManager(
            max_transactions=1000,
            eviction_policy="lowest_fee"
        )

        # Add 500 transactions
        tx_ids = []
        for i in range(500):
            result = mempool.add_transaction(f"tx_{i}", fee=float(i))
            tx_ids.append(result["tx_id"])

        # Batch remove 250 transactions
        to_remove = tx_ids[:250]
        mempool.batch_remove_transactions(to_remove)

        # Verify all removed
        for tx_id in to_remove:
            assert tx_id not in mempool.pending_transactions

        # Verify remaining transactions intact
        assert len(mempool.pending_transactions) == 250

    def test_heap_statistics_accuracy(self):
        """Test heap statistics provide accurate metrics"""
        mempool = MempoolManager(
            max_transactions=100,
            eviction_policy="lowest_fee"
        )

        # Add transactions
        tx_ids = []
        for i in range(50):
            result = mempool.add_transaction(f"tx_{i}", fee=float(i))
            tx_ids.append(result["tx_id"])

        stats = mempool.get_heap_statistics()
        assert stats["heap_size"] == 50
        assert stats["deleted_entries"] == 0
        assert stats["valid_transactions"] == 50
        assert stats["heap_efficiency"] == 1.0

        # Remove 10 transactions
        for i in range(10):
            mempool.remove_transaction(tx_ids[i])

        stats = mempool.get_heap_statistics()
        assert stats["deleted_entries"] == 10
        assert stats["valid_transactions"] == 40
        assert stats["heap_efficiency"] == 0.8  # (50-10)/50

    def test_eviction_with_lazy_deleted_entries(self):
        """Test eviction correctly skips lazy-deleted entries"""
        mempool = MempoolManager(
            max_transactions=5,
            eviction_policy="lowest_fee"
        )

        # Add 5 transactions
        tx_ids = []
        for i in range(5):
            result = mempool.add_transaction(f"tx_{i}", fee=float(i + 1))
            tx_ids.append(result["tx_id"])

        # Verify all 5 are in mempool
        assert len(mempool.pending_transactions) == 5

        # Remove the lowest 2 (fees 1.0, 2.0) - this brings us to 3 transactions
        mempool.remove_transaction(tx_ids[0])
        mempool.remove_transaction(tx_ids[1])

        assert len(mempool.pending_transactions) == 3

        # Add a new transaction - should fit without eviction since we have 3/5
        result = mempool.add_transaction("tx_new", fee=10.0)

        # tx_0 and tx_1 should be removed
        assert tx_ids[0] not in mempool.pending_transactions
        assert tx_ids[1] not in mempool.pending_transactions
        # tx_2, tx_3, tx_4 should remain (fees 3.0, 4.0, 5.0)
        assert tx_ids[2] in mempool.pending_transactions
        assert tx_ids[3] in mempool.pending_transactions
        assert tx_ids[4] in mempool.pending_transactions
        # New transaction should be added
        assert result["tx_id"] in mempool.pending_transactions
        assert len(mempool.pending_transactions) == 4  # 3 old + 1 new

        # Now add 2 more to trigger eviction (will evict lowest fee which is tx_2 at 3.0)
        result2 = mempool.add_transaction("tx_new2", fee=15.0)
        assert len(mempool.pending_transactions) == 5

        result3 = mempool.add_transaction("tx_new3", fee=20.0)
        # Should evict tx_2 (fee 3.0 is lowest remaining)
        assert tx_ids[2] not in mempool.pending_transactions
        assert len(mempool.pending_transactions) == 5

    def test_expired_transactions_use_lazy_deletion(self):
        """Test expired transaction removal uses lazy deletion"""
        mempool = MempoolManager(
            max_transactions=100,
            eviction_policy="lowest_fee",
            transaction_expiry_seconds=1  # 1 second for testing
        )

        # Add transactions
        tx_ids = []
        for i in range(10):
            result = mempool.add_transaction(f"tx_{i}", fee=float(i))
            tx_ids.append(result["tx_id"])

        initial_heap_size = len(mempool.transaction_queue)

        # Wait for expiry
        time.sleep(1.1)

        # Force expiry check
        mempool.last_expiry_check = 0
        expired_count = mempool.remove_expired_transactions()

        assert expired_count == 10
        assert len(mempool.pending_transactions) == 0
        # Heap may be compacted or contain deleted entries
        assert len(mempool._deleted_tx_ids) <= initial_heap_size

    def test_fifo_policy_not_affected_by_lazy_deletion(self):
        """Test FIFO policy works correctly (doesn't use heap)"""
        mempool = MempoolManager(
            max_transactions=5,
            eviction_policy="fifo"
        )

        # Add transactions
        tx_ids = []
        for i in range(5):
            result = mempool.add_transaction(f"tx_{i}", fee=float(i))
            tx_ids.append(result["tx_id"])

        # Remove transaction
        mempool.remove_transaction(tx_ids[2])

        # FIFO doesn't use heap, so no deleted set
        assert len(mempool._deleted_tx_ids) == 0
        assert tx_ids[2] not in mempool.pending_transactions

    def test_performance_benchmark_10k_mempool_removal(self):
        """Benchmark: 10,000 tx mempool, removal should be <1ms"""
        mempool = MempoolManager(
            max_transactions=15000,
            eviction_policy="lowest_fee"
        )

        # Add 10,000 transactions
        tx_ids = []
        for i in range(10000):
            result = mempool.add_transaction(f"tx_{i}", fee=float(i))
            tx_ids.append(result["tx_id"])

        # Benchmark single removal
        start_time = time.perf_counter()
        mempool.remove_transaction(tx_ids[5000])
        end_time = time.perf_counter()

        removal_time_ms = (end_time - start_time) * 1000

        # Should be <1ms (typically <<1ms with lazy deletion)
        assert removal_time_ms < 1.0, f"Removal took {removal_time_ms:.3f}ms, expected <1ms"

        print(f"10k mempool removal: {removal_time_ms:.3f}ms")

    def test_performance_benchmark_batch_removal(self):
        """Benchmark: Batch removal of 1000 transactions from 10k mempool"""
        mempool = MempoolManager(
            max_transactions=15000,
            eviction_policy="lowest_fee"
        )

        # Add 10,000 transactions
        tx_ids = []
        for i in range(10000):
            result = mempool.add_transaction(f"tx_{i}", fee=float(i))
            tx_ids.append(result["tx_id"])

        # Benchmark batch removal of 1000 transactions
        to_remove = tx_ids[:1000]
        start_time = time.perf_counter()
        mempool.batch_remove_transactions(to_remove)
        end_time = time.perf_counter()

        batch_removal_time_ms = (end_time - start_time) * 1000

        # Should be very fast (typically <50ms for 1000 removals)
        assert batch_removal_time_ms < 100.0, \
            f"Batch removal took {batch_removal_time_ms:.3f}ms, expected <100ms"

        print(f"Batch removal of 1000 txs: {batch_removal_time_ms:.3f}ms")

    def test_compaction_maintains_heap_property(self):
        """Test that compaction maintains min-heap property"""
        mempool = MempoolManager(
            max_transactions=100,
            eviction_policy="lowest_fee"
        )

        # Add transactions
        tx_ids = []
        for i in range(50):
            result = mempool.add_transaction(f"tx_{i}", fee=float(i))
            tx_ids.append(result["tx_id"])

        # Remove half to trigger compaction
        for i in range(26):
            mempool.remove_transaction(tx_ids[i])

        # Verify heap property: parent <= children
        heap = mempool.transaction_queue
        for i in range(len(heap)):
            left_child = 2 * i + 1
            right_child = 2 * i + 2

            if left_child < len(heap):
                assert heap[i][0] <= heap[left_child][0], "Min-heap property violated (left)"

            if right_child < len(heap):
                assert heap[i][0] <= heap[right_child][0], "Min-heap property violated (right)"

    def test_multiple_compactions_dont_cause_issues(self):
        """Test that multiple compaction cycles work correctly"""
        mempool = MempoolManager(
            max_transactions=200,
            eviction_policy="lowest_fee"
        )
        mempool._compaction_threshold = 0.4  # Lower threshold for more frequent compactions

        # Cycle: add, remove, add, remove
        for cycle in range(3):
            # Add 50 transactions
            tx_ids = []
            for i in range(50):
                result = mempool.add_transaction(f"tx_cycle{cycle}_{i}", fee=float(i))
                tx_ids.append(result["tx_id"])

            # Remove 30 (triggers compaction at 60% deleted)
            for i in range(30):
                mempool.remove_transaction(tx_ids[i])

        # Verify mempool is consistent
        stats = mempool.get_heap_statistics()
        assert stats["valid_transactions"] == len(mempool.pending_transactions)
        assert len(mempool.pending_transactions) == 60  # 3 cycles * 20 remaining

    def test_lazy_deletion_with_double_spend_protection(self):
        """Test lazy deletion properly frees UTXOs for double-spend tracking"""
        mempool = MempoolManager(
            max_transactions=100,
            eviction_policy="lowest_fee"
        )

        # Add transaction with specific UTXOs
        inputs = [{"txid": "a" * 64, "vout": 0}]
        result1 = mempool.add_transaction("tx_1", fee=1.0, inputs=inputs)

        # Verify UTXO is tracked
        utxo_key = f"{'a' * 64}:0"
        assert utxo_key in mempool.spent_utxos

        # Remove transaction
        mempool.remove_transaction(result1["tx_id"])

        # UTXO should be freed
        assert utxo_key not in mempool.spent_utxos

        # Should be able to add new transaction with same UTXO
        result2 = mempool.add_transaction("tx_2", fee=2.0, inputs=inputs)
        assert result2["success"] is True
        assert utxo_key in mempool.spent_utxos


class TestMempoolPerformanceRegression:
    """Performance regression tests to ensure lazy deletion maintains speed"""

    def test_no_heap_rebuild_on_single_removal(self):
        """Verify no full heap rebuild occurs on single removal"""
        mempool = MempoolManager(
            max_transactions=1000,
            eviction_policy="lowest_fee"
        )

        # Add many transactions
        tx_ids = []
        for i in range(500):
            result = mempool.add_transaction(f"tx_{i}", fee=float(i))
            tx_ids.append(result["tx_id"])

        # Capture heap state
        heap_id_before = id(mempool.transaction_queue)
        heap_size_before = len(mempool.transaction_queue)

        # Remove one transaction
        mempool.remove_transaction(tx_ids[100])

        # Heap object should be same (no rebuild unless compaction threshold hit)
        # Size stays same (lazy deletion)
        assert len(mempool.transaction_queue) == heap_size_before

    def test_compaction_only_when_necessary(self):
        """Test compaction only occurs when threshold exceeded"""
        mempool = MempoolManager(
            max_transactions=1000,
            eviction_policy="lowest_fee"
        )
        mempool._compaction_threshold = 0.6  # 60% threshold

        # Add 100 transactions
        tx_ids = []
        for i in range(100):
            result = mempool.add_transaction(f"tx_{i}", fee=float(i))
            tx_ids.append(result["tx_id"])

        initial_heap_size = len(mempool.transaction_queue)

        # Remove 50 transactions (50% deleted, below threshold)
        for i in range(50):
            mempool.remove_transaction(tx_ids[i])

        # No compaction should have occurred
        assert len(mempool.transaction_queue) == initial_heap_size

        # Remove 11 more (61% deleted, above threshold)
        for i in range(50, 61):
            mempool.remove_transaction(tx_ids[i])

        # Compaction should have occurred
        assert len(mempool.transaction_queue) < initial_heap_size
        assert len(mempool._deleted_tx_ids) == 0  # Cleared after compaction
