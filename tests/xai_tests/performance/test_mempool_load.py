"""
Performance and stress tests for mempool under high load.

Tests mempool behavior with 10,000+ pending transactions, high insertion rates,
eviction performance, memory usage tracking, and transaction retrieval performance.

Run with: pytest tests/xai_tests/performance/test_mempool_load.py -v -m performance
"""

import pytest
import time
import psutil
import os
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

from xai.core.blockchain import Blockchain
from xai.core.wallet import Wallet
from xai.core.transaction import Transaction


# Mark all tests in this module as performance tests
pytestmark = pytest.mark.performance


class TestMempoolLoad:
    """Stress tests for mempool with large transaction volumes."""

    @pytest.fixture
    def blockchain(self, tmp_path):
        """Create a blockchain instance for testing."""
        bc = Blockchain(data_dir=str(tmp_path / "blockchain"))
        bc.create_genesis_block()
        return bc

    @pytest.fixture
    def wallets(self):
        """Create a pool of wallets for generating transactions."""
        return [Wallet() for _ in range(100)]

    def _create_transaction(self, sender: Wallet, recipient: Wallet, amount: float, fee: float = 0.01) -> Transaction:
        """Helper to create and sign a transaction."""
        tx = Transaction(sender.address, recipient.address, amount, fee)
        tx.public_key = sender.public_key
        tx.sign_transaction(sender.private_key)
        return tx

    def _get_memory_usage(self) -> Dict[str, float]:
        """Get current process memory usage in MB."""
        process = psutil.Process(os.getpid())
        mem_info = process.memory_info()
        return {
            "rss_mb": mem_info.rss / (1024 * 1024),
            "vms_mb": mem_info.vms / (1024 * 1024),
        }

    def test_mempool_10k_transactions_insertion(self, blockchain, wallets, benchmark):
        """
        Benchmark: Insert 10,000 transactions into mempool.

        Measures:
        - Insertion throughput (tx/sec)
        - Average insertion time
        - Memory growth
        - Final mempool size
        """
        def insert_10k_transactions():
            # Create 10,000 transactions
            transactions = []
            for i in range(10000):
                sender = wallets[i % 100]
                recipient = wallets[(i + 1) % 100]
                tx = self._create_transaction(sender, recipient, 0.1, 0.001)
                transactions.append(tx)

            # Insert all transactions
            mem_before = self._get_memory_usage()
            start = time.perf_counter()

            for tx in transactions:
                try:
                    blockchain.add_transaction(tx)
                except Exception:
                    # Some transactions may fail validation (e.g., insufficient balance)
                    pass

            elapsed = time.perf_counter() - start
            mem_after = self._get_memory_usage()

            return {
                "elapsed": elapsed,
                "count": len(blockchain.pending_transactions),
                "memory_growth_mb": mem_after["rss_mb"] - mem_before["rss_mb"],
            }

        result = benchmark(insert_10k_transactions)

        # Verify performance expectations
        assert result["count"] > 0, "No transactions were added to mempool"
        txs_per_sec = result["count"] / result["elapsed"]

        print(f"\n=== Mempool 10k Insertion Performance ===")
        print(f"Transactions added: {result['count']}")
        print(f"Total time: {result['elapsed']:.2f}s")
        print(f"Throughput: {txs_per_sec:.2f} tx/sec")
        print(f"Memory growth: {result['memory_growth_mb']:.2f} MB")
        print(f"Avg time per tx: {(result['elapsed'] / result['count']) * 1000:.2f} ms")

        # Performance baseline: should handle at least 100 tx/sec
        assert txs_per_sec > 100, f"Insertion too slow: {txs_per_sec:.2f} tx/sec"

    def test_mempool_high_insertion_rate(self, blockchain, wallets):
        """
        Test mempool under sustained high insertion rate.

        Simulates 1000 tx/sec insertion rate for 10 seconds.
        """
        target_rate = 1000  # tx/sec
        duration = 10  # seconds
        batch_size = 100
        batch_interval = batch_size / target_rate  # seconds between batches

        total_added = 0
        total_rejected = 0
        start_time = time.perf_counter()
        mem_samples = []

        print(f"\n=== High Insertion Rate Test ===")
        print(f"Target rate: {target_rate} tx/sec")
        print(f"Duration: {duration} seconds")

        while time.perf_counter() - start_time < duration:
            batch_start = time.perf_counter()

            # Create and insert a batch
            for i in range(batch_size):
                sender = wallets[i % 100]
                recipient = wallets[(i + 1) % 100]
                tx = self._create_transaction(sender, recipient, 0.01, 0.0001)

                try:
                    blockchain.add_transaction(tx)
                    total_added += 1
                except Exception:
                    total_rejected += 1

            # Sample memory usage
            mem_samples.append(self._get_memory_usage()["rss_mb"])

            # Rate limiting: sleep to maintain target rate
            elapsed = time.perf_counter() - batch_start
            if elapsed < batch_interval:
                time.sleep(batch_interval - elapsed)

        actual_duration = time.perf_counter() - start_time
        actual_rate = total_added / actual_duration
        mempool_size = len(blockchain.pending_transactions)

        print(f"Actual duration: {actual_duration:.2f}s")
        print(f"Transactions added: {total_added}")
        print(f"Transactions rejected: {total_rejected}")
        print(f"Actual rate: {actual_rate:.2f} tx/sec")
        print(f"Final mempool size: {mempool_size}")
        print(f"Memory: min={min(mem_samples):.2f}MB, max={max(mem_samples):.2f}MB")

        # Should achieve at least 80% of target rate
        assert actual_rate > target_rate * 0.8, f"Rate too low: {actual_rate:.2f} tx/sec"

    def test_mempool_eviction_performance(self, blockchain, wallets, benchmark):
        """
        Benchmark: Mempool eviction under size pressure.

        Fill mempool beyond capacity and measure eviction performance.
        """
        # Set a low mempool size limit for testing
        original_max = blockchain._mempool_max_size
        blockchain._mempool_max_size = 1000

        def fill_and_evict():
            # Fill mempool to capacity
            for i in range(1500):
                sender = wallets[i % 100]
                recipient = wallets[(i + 1) % 100]
                # Vary fees to test priority-based eviction
                fee = 0.0001 + (i % 10) * 0.00001
                tx = self._create_transaction(sender, recipient, 0.01, fee)

                try:
                    blockchain.add_transaction(tx)
                except Exception:
                    pass

            return len(blockchain.pending_transactions)

        result = benchmark(fill_and_evict)
        blockchain._mempool_max_size = original_max  # Restore

        print(f"\n=== Mempool Eviction Performance ===")
        print(f"Final mempool size: {result}")
        print(f"Evictions triggered: {result < 1500}")

        # Should maintain size limit
        assert result <= 1000, f"Eviction failed: {result} transactions remain"

    def test_mempool_concurrent_access(self, blockchain, wallets):
        """
        Test mempool thread safety under concurrent access.

        Multiple threads adding, removing, and querying transactions simultaneously.
        """
        num_threads = 10
        txs_per_thread = 100

        def worker(thread_id: int) -> Dict[str, int]:
            added = 0
            failed = 0

            for i in range(txs_per_thread):
                sender = wallets[(thread_id + i) % 100]
                recipient = wallets[(thread_id + i + 1) % 100]
                tx = self._create_transaction(sender, recipient, 0.01, 0.0001)

                try:
                    blockchain.add_transaction(tx)
                    added += 1
                except Exception:
                    failed += 1

                # Periodically query mempool
                if i % 10 == 0:
                    _ = len(blockchain.pending_transactions)

            return {"added": added, "failed": failed}

        print(f"\n=== Concurrent Access Test ===")
        print(f"Threads: {num_threads}")
        print(f"Transactions per thread: {txs_per_thread}")

        start = time.perf_counter()
        total_added = 0
        total_failed = 0

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker, i) for i in range(num_threads)]

            for future in as_completed(futures):
                result = future.result()
                total_added += result["added"]
                total_failed += result["failed"]

        elapsed = time.perf_counter() - start
        final_size = len(blockchain.pending_transactions)

        print(f"Time elapsed: {elapsed:.2f}s")
        print(f"Total added: {total_added}")
        print(f"Total failed: {total_failed}")
        print(f"Final mempool size: {final_size}")
        print(f"Throughput: {total_added / elapsed:.2f} tx/sec")

        # Verify no crashes and reasonable throughput
        assert total_added > 0, "No transactions added"
        assert total_added / elapsed > 50, "Concurrent throughput too low"

    def test_mempool_retrieval_performance(self, blockchain, wallets, benchmark):
        """
        Benchmark: Transaction retrieval from large mempool.

        Measures query performance with 5000+ transactions.
        """
        # Fill mempool with 5000 transactions
        print(f"\n=== Mempool Retrieval Performance ===")
        print("Filling mempool with 5000 transactions...")

        for i in range(5000):
            sender = wallets[i % 100]
            recipient = wallets[(i + 1) % 100]
            tx = self._create_transaction(sender, recipient, 0.01, 0.001)

            try:
                blockchain.add_transaction(tx)
            except Exception:
                pass

        mempool_size = len(blockchain.pending_transactions)
        print(f"Mempool size: {mempool_size}")

        def query_operations():
            # Test different query patterns

            # 1. Get all pending transactions
            all_txs = blockchain.pending_transactions[:]

            # 2. Filter by sender (simulate address-specific queries)
            target_address = wallets[0].address
            sender_txs = [tx for tx in blockchain.pending_transactions if tx.sender == target_address]

            # 3. Get transactions above fee threshold
            high_fee_txs = [tx for tx in blockchain.pending_transactions if tx.fee > 0.0005]

            return {
                "all_count": len(all_txs),
                "sender_count": len(sender_txs),
                "high_fee_count": len(high_fee_txs),
            }

        result = benchmark(query_operations)

        print(f"Query results:")
        print(f"  All transactions: {result['all_count']}")
        print(f"  Sender-specific: {result['sender_count']}")
        print(f"  High-fee txs: {result['high_fee_count']}")

    def test_mempool_memory_scaling(self, blockchain, wallets):
        """
        Test memory usage growth as mempool scales.

        Measures memory at 1k, 5k, and 10k transactions.
        """
        print(f"\n=== Mempool Memory Scaling ===")

        checkpoints = [1000, 5000, 10000]
        memory_data = []

        mem_baseline = self._get_memory_usage()["rss_mb"]
        print(f"Baseline memory: {mem_baseline:.2f} MB")

        tx_count = 0
        for checkpoint in checkpoints:
            # Add transactions up to checkpoint
            while tx_count < checkpoint:
                sender = wallets[tx_count % 100]
                recipient = wallets[(tx_count + 1) % 100]
                tx = self._create_transaction(sender, recipient, 0.01, 0.0001)

                try:
                    blockchain.add_transaction(tx)
                    tx_count += 1
                except Exception:
                    tx_count += 1  # Count attempts even if failed

            mem_current = self._get_memory_usage()["rss_mb"]
            mem_growth = mem_current - mem_baseline
            mempool_size = len(blockchain.pending_transactions)
            mem_per_tx = mem_growth / mempool_size if mempool_size > 0 else 0

            memory_data.append({
                "checkpoint": checkpoint,
                "mempool_size": mempool_size,
                "memory_mb": mem_current,
                "growth_mb": mem_growth,
                "mb_per_tx": mem_per_tx,
            })

            print(f"\nCheckpoint: {checkpoint} transactions")
            print(f"  Actual mempool size: {mempool_size}")
            print(f"  Memory: {mem_current:.2f} MB")
            print(f"  Growth: {mem_growth:.2f} MB")
            print(f"  Per transaction: {mem_per_tx * 1024:.2f} KB")

        # Verify memory growth is reasonable (< 100 KB per transaction on average)
        avg_mem_per_tx = sum(d["mb_per_tx"] for d in memory_data) / len(memory_data)
        print(f"\nAverage memory per transaction: {avg_mem_per_tx * 1024:.2f} KB")
        assert avg_mem_per_tx < 0.1, f"Memory usage too high: {avg_mem_per_tx * 1024:.2f} KB/tx"

    def test_mempool_fee_based_prioritization(self, blockchain, wallets, benchmark):
        """
        Benchmark: Fee-based transaction selection.

        Tests performance of selecting top transactions by fee from large mempool.
        """
        # Fill mempool with transactions of varying fees
        print(f"\n=== Fee-Based Prioritization Performance ===")
        print("Filling mempool with varying-fee transactions...")

        for i in range(5000):
            sender = wallets[i % 100]
            recipient = wallets[(i + 1) % 100]
            # Create diverse fee distribution
            fee = 0.0001 + (i % 1000) * 0.00001
            tx = self._create_transaction(sender, recipient, 0.01, fee)

            try:
                blockchain.add_transaction(tx)
            except Exception:
                pass

        print(f"Mempool size: {len(blockchain.pending_transactions)}")

        def select_top_by_fee(count: int = 100):
            """Select top N transactions by fee."""
            # Sort by fee descending
            sorted_txs = sorted(
                blockchain.pending_transactions,
                key=lambda tx: tx.fee,
                reverse=True
            )
            return sorted_txs[:count]

        result = benchmark.pedantic(
            lambda: select_top_by_fee(100),
            iterations=100,
            rounds=5
        )

        print(f"Selected {len(result)} transactions")
        if result:
            print(f"Top fee: {result[0].fee}")
            print(f"100th fee: {result[-1].fee if len(result) >= 100 else result[-1].fee}")

    def test_mempool_expiration_performance(self, blockchain, wallets, benchmark):
        """
        Benchmark: Transaction expiration and pruning.

        Tests performance of removing expired transactions from large mempool.
        """
        # Set short expiration for testing
        original_max_age = blockchain._mempool_max_age_seconds
        blockchain._mempool_max_age_seconds = 60  # 1 minute

        # Add old transactions (timestamp in past)
        print(f"\n=== Expiration Performance ===")
        current_time = time.time()

        for i in range(3000):
            sender = wallets[i % 100]
            recipient = wallets[(i + 1) % 100]
            tx = self._create_transaction(sender, recipient, 0.01, 0.0001)
            # Make half the transactions "expired"
            if i < 1500:
                tx.timestamp = current_time - 120  # 2 minutes old
            else:
                tx.timestamp = current_time - 30   # 30 seconds old

            try:
                blockchain.add_transaction(tx, skip_timestamp_validation=True)
            except Exception:
                pass

        initial_size = len(blockchain.pending_transactions)
        print(f"Initial mempool size: {initial_size}")

        def prune_expired():
            """Trigger mempool pruning."""
            removed = blockchain._prune_expired_mempool(current_time)
            return removed

        result = benchmark(prune_expired)
        blockchain._mempool_max_age_seconds = original_max_age  # Restore

        final_size = len(blockchain.pending_transactions)

        print(f"Removed: {result} transactions")
        print(f"Final mempool size: {final_size}")

        # Should have removed approximately half the transactions
        assert result > 0, "No transactions were pruned"
        assert final_size < initial_size, "Mempool size did not decrease"


class TestMempoolStatistics:
    """Tests for mempool statistics and monitoring."""

    @pytest.fixture
    def blockchain(self, tmp_path):
        """Create a blockchain instance for testing."""
        bc = Blockchain(data_dir=str(tmp_path / "blockchain"))
        bc.create_genesis_block()
        return bc

    def test_mempool_statistics_calculation(self, blockchain, benchmark):
        """
        Benchmark: Mempool statistics calculation.

        Tests performance of calculating comprehensive mempool stats.
        """
        # Create transactions with varied properties
        wallets = [Wallet() for _ in range(50)]

        for i in range(1000):
            sender = wallets[i % 50]
            recipient = wallets[(i + 1) % 50]
            fee = 0.0001 + (i % 100) * 0.00001
            tx = Transaction(sender.address, recipient.address, 0.01, fee)
            tx.public_key = sender.public_key
            tx.sign_transaction(sender.private_key)

            try:
                blockchain.add_transaction(tx)
            except Exception:
                pass

        print(f"\n=== Mempool Statistics Performance ===")
        print(f"Mempool size: {len(blockchain.pending_transactions)}")

        def calculate_stats():
            """Calculate comprehensive mempool statistics."""
            txs = blockchain.pending_transactions

            if not txs:
                return {}

            fees = [tx.fee for tx in txs]
            amounts = [tx.amount for tx in txs]

            stats = {
                "count": len(txs),
                "total_fees": sum(fees),
                "avg_fee": sum(fees) / len(fees),
                "min_fee": min(fees),
                "max_fee": max(fees),
                "total_amount": sum(amounts),
                "unique_senders": len(set(tx.sender for tx in txs)),
            }

            return stats

        result = benchmark(calculate_stats)

        print(f"Statistics calculated:")
        for key, value in result.items():
            print(f"  {key}: {value}")


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v", "-m", "performance", "--benchmark-only"])
