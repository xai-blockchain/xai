"""
Comprehensive tests for UTXOManager thread safety

Tests concurrent UTXO additions, concurrent spends, race conditions,
deadlock prevention, and thread-safe operations.
"""

import pytest
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from xai.core.utxo_manager import UTXOManager


class TestUTXOManagerThreadSafety:
    """Tests for UTXOManager thread safety"""

    def test_concurrent_utxo_additions(self):
        """Test concurrent UTXO additions are thread-safe"""
        utxo_mgr = UTXOManager()
        num_threads = 10
        additions_per_thread = 100

        def add_utxos(thread_id):
            """Add UTXOs from a thread"""
            for i in range(additions_per_thread):
                utxo_mgr.add_utxo(
                    f"address_{thread_id}",
                    f"tx_{thread_id}_{i}",
                    i,
                    10.0,
                    "script"
                )

        # Run concurrent additions
        threads = []
        for i in range(num_threads):
            t = threading.Thread(target=add_utxos, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Verify all UTXOs were added
        expected_total = num_threads * additions_per_thread
        assert utxo_mgr.total_utxos == expected_total

    def test_concurrent_utxo_spends(self):
        """Test concurrent UTXO spends are thread-safe"""
        utxo_mgr = UTXOManager()
        address = "test_address"

        # Add UTXOs
        for i in range(100):
            utxo_mgr.add_utxo(address, f"tx_{i}", 0, 10.0, "script")

        spent_count = 0
        lock = threading.Lock()

        def spend_utxo(tx_id):
            """Spend a UTXO from a thread"""
            nonlocal spent_count
            result = utxo_mgr.mark_utxo_spent(address, tx_id, 0)
            if result:
                with lock:
                    spent_count += 1

        # Run concurrent spends
        threads = []
        for i in range(100):
            t = threading.Thread(target=spend_utxo, args=(f"tx_{i}",))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # All should be spent
        assert spent_count == 100

    def test_concurrent_add_and_spend(self):
        """Test concurrent additions and spends don't cause race conditions"""
        utxo_mgr = UTXOManager()
        address = "test_address"

        results = {'added': 0, 'spent': 0}
        lock = threading.Lock()

        def add_utxos():
            """Add UTXOs"""
            for i in range(50):
                utxo_mgr.add_utxo(address, f"tx_add_{i}", 0, 10.0, "script")
                with lock:
                    results['added'] += 1
                time.sleep(0.001)  # Small delay

        def spend_utxos():
            """Spend UTXOs"""
            time.sleep(0.01)  # Let some be added first
            for i in range(30):
                if utxo_mgr.mark_utxo_spent(address, f"tx_add_{i}", 0):
                    with lock:
                        results['spent'] += 1
                time.sleep(0.001)

        # Run concurrent operations
        t1 = threading.Thread(target=add_utxos)
        t2 = threading.Thread(target=spend_utxos)

        t1.start()
        t2.start()

        t1.join()
        t2.join()

        # Verify operations completed
        assert results['added'] == 50
        assert results['spent'] <= 30  # At most 30 (may be less if timing issue)

    def test_race_condition_prevention(self):
        """Test race conditions are prevented by locking"""
        utxo_mgr = UTXOManager()
        address = "test_address"

        # Add a UTXO
        utxo_mgr.add_utxo(address, "tx_race", 0, 10.0, "script")

        spend_results = []

        def try_spend():
            """Try to spend the same UTXO"""
            result = utxo_mgr.mark_utxo_spent(address, "tx_race", 0)
            spend_results.append(result)

        # Multiple threads try to spend same UTXO
        threads = []
        for _ in range(10):
            t = threading.Thread(target=try_spend)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Only one should succeed
        successful_spends = sum(1 for r in spend_results if r)
        assert successful_spends == 1

    def test_no_deadlock_concurrent_operations(self):
        """Test no deadlocks occur with concurrent operations"""
        utxo_mgr = UTXOManager()

        def mixed_operations(thread_id):
            """Perform mixed operations"""
            for i in range(20):
                # Add UTXO
                utxo_mgr.add_utxo(
                    f"addr_{thread_id}",
                    f"tx_{thread_id}_{i}",
                    0,
                    10.0,
                    "script"
                )

                # Query UTXOs
                utxos = utxo_mgr.get_utxos_for_address(f"addr_{thread_id}")

                # Spend some
                if i % 2 == 0 and i > 0:
                    utxo_mgr.mark_utxo_spent(
                        f"addr_{thread_id}",
                        f"tx_{thread_id}_{i-1}",
                        0
                    )

        # Run many concurrent operations
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(mixed_operations, i) for i in range(10)]

            # Wait for all to complete (with timeout to detect deadlock)
            for future in as_completed(futures, timeout=30):
                future.result()

        # If we get here, no deadlock occurred
        assert True

    def test_concurrent_balance_queries(self):
        """Test concurrent balance queries are thread-safe"""
        utxo_mgr = UTXOManager()
        address = "test_address"

        # Add UTXOs
        for i in range(100):
            utxo_mgr.add_utxo(address, f"tx_{i}", 0, 1.0, "script")

        balances = []

        def get_balance():
            """Get balance"""
            utxos = utxo_mgr.get_utxos_for_address(address)
            balance = sum(u['amount'] for u in utxos)
            balances.append(balance)

        # Query balance concurrently
        threads = []
        for _ in range(20):
            t = threading.Thread(target=get_balance)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # All queries should return same balance (if no concurrent modifications)
        assert all(b == balances[0] for b in balances)

    def test_concurrent_utxo_queries_and_modifications(self):
        """Test queries don't interfere with modifications"""
        utxo_mgr = UTXOManager()
        address = "test_address"

        # Pre-populate
        for i in range(50):
            utxo_mgr.add_utxo(address, f"tx_{i}", 0, 10.0, "script")

        query_count = 0
        modify_count = 0
        lock = threading.Lock()

        def query_utxos():
            """Query UTXOs"""
            nonlocal query_count
            for _ in range(100):
                utxo_mgr.get_utxos_for_address(address)
                with lock:
                    query_count += 1
                time.sleep(0.001)

        def modify_utxos():
            """Modify UTXOs"""
            nonlocal modify_count
            for i in range(50, 100):
                utxo_mgr.add_utxo(address, f"tx_{i}", 0, 10.0, "script")
                with lock:
                    modify_count += 1
                time.sleep(0.001)

        # Run concurrent queries and modifications
        t1 = threading.Thread(target=query_utxos)
        t2 = threading.Thread(target=modify_utxos)

        t1.start()
        t2.start()

        t1.join()
        t2.join()

        # Both should complete without errors
        assert query_count == 100
        assert modify_count == 50

    def test_thread_safe_total_value_tracking(self):
        """Test total_value is correctly tracked with concurrent operations"""
        utxo_mgr = UTXOManager()

        def add_and_spend(thread_id):
            """Add UTXOs and spend some"""
            address = f"addr_{thread_id}"

            # Add 10 UTXOs of 10.0 each
            for i in range(10):
                utxo_mgr.add_utxo(address, f"tx_{thread_id}_{i}", 0, 10.0, "script")

            # Spend 5 of them
            for i in range(5):
                utxo_mgr.mark_utxo_spent(address, f"tx_{thread_id}_{i}", 0)

        # Run with multiple threads
        threads = []
        for i in range(10):
            t = threading.Thread(target=add_and_spend, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Each thread: adds 100.0, spends 50.0 = net 50.0
        # 10 threads = 500.0 total
        expected_value = 10 * 10 * 10.0 - 10 * 5 * 10.0
        assert abs(utxo_mgr.total_value - expected_value) < 0.01
