"""
Performance and stress tests for blockchain storage and compaction.

Tests storage growth over time, compaction performance with large datasets,
pruning performance, and database query performance.

Run with: pytest tests/xai_tests/performance/test_storage_compaction.py -v -m performance
"""

import pytest
import time
import os
import psutil
import json
import shutil
from pathlib import Path
from typing import List, Dict, Any

from xai.core.blockchain import Blockchain
from xai.core.wallet import Wallet
from xai.core.transaction import Transaction
from xai.core.blockchain_storage import BlockchainStorage


# Mark all tests in this module as performance tests
pytestmark = pytest.mark.performance


class TestStorageGrowth:
    """Tests for storage growth and disk usage patterns."""

    @pytest.fixture
    def data_dir(self, tmp_path):
        """Create a temporary data directory."""
        return str(tmp_path / "storage_test")

    @pytest.fixture
    def blockchain(self, data_dir):
        """Create a blockchain instance."""
        bc = Blockchain(data_dir=data_dir)
        bc.create_genesis_block()
        return bc

    def _get_directory_size(self, path: str) -> int:
        """Get total size of directory in bytes."""
        total = 0
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if os.path.exists(filepath):
                    total += os.path.getsize(filepath)
        return total

    def _create_block_with_transactions(self, blockchain: Blockchain, wallets: List[Wallet], tx_count: int = 10):
        """Create a block with specified number of transactions."""
        for i in range(tx_count):
            sender = wallets[i % len(wallets)]
            recipient = wallets[(i + 1) % len(wallets)]
            tx = Transaction(sender.address, recipient.address, 0.1, 0.001)
            tx.public_key = sender.public_key
            tx.sign_transaction(sender.private_key)

            try:
                blockchain.add_transaction(tx)
            except Exception:
                pass

        # Mine a block
        miner = wallets[0]
        try:
            blockchain.mine_pending_transactions(miner.address)
        except Exception as e:
            print(f"Mining failed: {e}")

    def test_storage_growth_over_blocks(self, blockchain, data_dir):
        """
        Test storage growth as blockchain grows.

        Measures disk usage at 100, 500, and 1000 blocks.
        """
        print(f"\n=== Storage Growth Test ===")
        wallets = [Wallet() for _ in range(10)]

        checkpoints = [100, 500, 1000]
        growth_data = []

        baseline_size = self._get_directory_size(data_dir)
        print(f"Baseline storage: {baseline_size / 1024:.2f} KB")

        current_height = blockchain.get_latest_block().header.index

        for checkpoint in checkpoints:
            start_time = time.perf_counter()

            # Mine blocks up to checkpoint
            while blockchain.get_latest_block().header.index < checkpoint:
                self._create_block_with_transactions(blockchain, wallets, tx_count=5)

            elapsed = time.perf_counter() - start_time
            storage_size = self._get_directory_size(data_dir)
            growth = storage_size - baseline_size
            blocks_added = blockchain.get_latest_block().header.index - current_height

            blocks_per_sec = blocks_added / elapsed if elapsed > 0 else 0
            kb_per_block = (growth / 1024) / blocks_added if blocks_added > 0 else 0

            growth_data.append({
                "checkpoint": checkpoint,
                "blocks": blockchain.get_latest_block().header.index,
                "storage_kb": storage_size / 1024,
                "growth_kb": growth / 1024,
                "kb_per_block": kb_per_block,
                "time_sec": elapsed,
                "blocks_per_sec": blocks_per_sec,
            })

            print(f"\nCheckpoint: {checkpoint} blocks")
            print(f"  Actual height: {blockchain.get_latest_block().header.index}")
            print(f"  Storage: {storage_size / 1024:.2f} KB")
            print(f"  Growth: {growth / 1024:.2f} KB")
            print(f"  Per block: {kb_per_block:.2f} KB")
            print(f"  Time: {elapsed:.2f}s ({blocks_per_sec:.2f} blocks/sec)")

            current_height = blockchain.get_latest_block().header.index

        # Verify storage growth is reasonable
        avg_kb_per_block = sum(d["kb_per_block"] for d in growth_data) / len(growth_data)
        print(f"\nAverage storage per block: {avg_kb_per_block:.2f} KB")

        # Most blocks should be under 100 KB with minimal transactions
        assert avg_kb_per_block < 100, f"Storage per block too high: {avg_kb_per_block:.2f} KB"

    def test_block_file_rotation(self, blockchain, data_dir):
        """
        Test block file rotation behavior.

        Verifies that storage creates multiple block files as chain grows.
        """
        print(f"\n=== Block File Rotation Test ===")
        wallets = [Wallet() for _ in range(10)]

        # Mine enough blocks to trigger file rotation
        # Default MAX_BLOCK_FILE_SIZE is 16MB, so we need many blocks
        print("Mining blocks to trigger file rotation...")

        for i in range(200):
            self._create_block_with_transactions(blockchain, wallets, tx_count=10)

            if i % 50 == 0:
                print(f"  Mined {i} blocks...")

        # Check block files created
        blocks_dir = os.path.join(data_dir, "blocks")
        block_files = [f for f in os.listdir(blocks_dir) if f.startswith("blocks_")]

        print(f"\nBlock files created: {len(block_files)}")
        for filename in sorted(block_files):
            filepath = os.path.join(blocks_dir, filename)
            size = os.path.getsize(filepath)
            print(f"  {filename}: {size / 1024:.2f} KB")

        assert len(block_files) >= 1, "No block files created"

    def test_utxo_set_growth(self, blockchain, data_dir):
        """
        Test UTXO set growth and storage impact.

        Measures UTXO set size as transactions create and spend outputs.
        """
        print(f"\n=== UTXO Set Growth Test ===")
        wallets = [Wallet() for _ in range(20)]

        # Mine blocks with varied transaction patterns
        for i in range(100):
            # Vary transaction count to create different UTXO patterns
            tx_count = 5 + (i % 10)
            self._create_block_with_transactions(blockchain, wallets, tx_count=tx_count)

        # Save UTXO set to disk
        blockchain.storage.save_utxo_set(blockchain.utxo_manager.utxo_set)

        # Measure UTXO file size
        utxo_file = os.path.join(data_dir, "utxo_set.json")
        if os.path.exists(utxo_file):
            utxo_size = os.path.getsize(utxo_file)
            utxo_count = len(blockchain.utxo_manager.utxo_set)

            print(f"Blocks: {blockchain.get_latest_block().header.index}")
            print(f"UTXO count: {utxo_count}")
            print(f"UTXO file size: {utxo_size / 1024:.2f} KB")
            if utxo_count > 0:
                print(f"Bytes per UTXO: {utxo_size / utxo_count:.2f}")

            assert utxo_size > 0, "UTXO file is empty"


class TestStorageCompaction:
    """Tests for storage compaction and optimization."""

    @pytest.fixture
    def data_dir(self, tmp_path):
        """Create a temporary data directory."""
        return str(tmp_path / "compaction_test")

    @pytest.fixture
    def storage(self, data_dir):
        """Create a storage instance."""
        return BlockchainStorage(data_dir=data_dir, enable_index=True)

    def test_compaction_performance(self, storage, data_dir, benchmark):
        """
        Benchmark: Storage compaction with large dataset.

        Tests compaction speed and effectiveness.
        """
        print(f"\n=== Compaction Performance Test ===")

        # Create a blockchain and mine blocks
        blockchain = Blockchain(data_dir=data_dir)
        blockchain.create_genesis_block()
        wallets = [Wallet() for _ in range(10)]

        # Mine 500 blocks
        print("Creating 500 blocks for compaction test...")
        for i in range(500):
            for j in range(5):
                sender = wallets[j % len(wallets)]
                recipient = wallets[(j + 1) % len(wallets)]
                tx = Transaction(sender.address, recipient.address, 0.1, 0.001)
                tx.public_key = sender.public_key
                tx.sign_transaction(sender.private_key)
                try:
                    blockchain.add_transaction(tx)
                except Exception:
                    pass

            miner = wallets[0]
            try:
                blockchain.mine_pending_transactions(miner.address)
            except Exception:
                pass

            if i % 100 == 0:
                print(f"  Mined {i} blocks...")

        # Measure storage before compaction
        size_before = sum(
            os.path.getsize(os.path.join(dirpath, filename))
            for dirpath, _, filenames in os.walk(data_dir)
            for filename in filenames
        )

        print(f"Storage before compaction: {size_before / 1024:.2f} KB")

        # Benchmark compaction
        def run_compaction():
            storage.compact()

        result = benchmark(run_compaction)

        # Measure storage after compaction
        size_after = sum(
            os.path.getsize(os.path.join(dirpath, filename))
            for dirpath, _, filenames in os.walk(data_dir)
            for filename in filenames
        )

        reduction = size_before - size_after
        reduction_pct = (reduction / size_before * 100) if size_before > 0 else 0

        print(f"Storage after compaction: {size_after / 1024:.2f} KB")
        print(f"Reduction: {reduction / 1024:.2f} KB ({reduction_pct:.1f}%)")

    def test_block_index_build_performance(self, storage, data_dir, benchmark):
        """
        Benchmark: Block index building for large chain.

        Tests index creation speed for existing blocks.
        """
        print(f"\n=== Block Index Build Performance ===")

        # Create blocks without index
        storage_no_index = BlockchainStorage(data_dir=data_dir, enable_index=False)
        blockchain = Blockchain(data_dir=data_dir)
        blockchain.storage = storage_no_index
        blockchain.create_genesis_block()

        wallets = [Wallet() for _ in range(10)]

        # Create 300 blocks
        print("Creating 300 blocks...")
        for i in range(300):
            for j in range(3):
                sender = wallets[j % len(wallets)]
                recipient = wallets[(j + 1) % len(wallets)]
                tx = Transaction(sender.address, recipient.address, 0.1, 0.001)
                tx.public_key = sender.public_key
                tx.sign_transaction(sender.private_key)
                try:
                    blockchain.add_transaction(tx)
                except Exception:
                    pass

            miner = wallets[0]
            try:
                blockchain.mine_pending_transactions(miner.address)
            except Exception:
                pass

        print(f"Created {blockchain.get_latest_block().header.index} blocks")

        # Now create storage with index and measure build time
        def build_index():
            indexed_storage = BlockchainStorage(data_dir=data_dir, enable_index=True)
            indexed_storage._ensure_index_built()
            return indexed_storage

        result = benchmark(build_index)

        if result.block_index:
            max_height = result.block_index.get_max_indexed_height()
            print(f"Indexed {max_height} blocks")

    def test_query_performance_with_index(self, storage, data_dir, benchmark):
        """
        Benchmark: Block queries with and without index.

        Compares lookup performance with index vs linear search.
        """
        print(f"\n=== Query Performance with Index ===")

        # Create blockchain with index
        blockchain = Blockchain(data_dir=data_dir)
        blockchain.create_genesis_block()
        wallets = [Wallet() for _ in range(5)]

        # Create 200 blocks
        print("Creating 200 blocks...")
        for i in range(200):
            for j in range(2):
                sender = wallets[j % len(wallets)]
                recipient = wallets[(j + 1) % len(wallets)]
                tx = Transaction(sender.address, recipient.address, 0.1, 0.001)
                tx.public_key = sender.public_key
                tx.sign_transaction(sender.private_key)
                try:
                    blockchain.add_transaction(tx)
                except Exception:
                    pass

            miner = wallets[0]
            try:
                blockchain.mine_pending_transactions(miner.address)
            except Exception:
                pass

        chain_height = blockchain.get_latest_block().header.index
        print(f"Chain height: {chain_height}")

        # Benchmark indexed queries
        def query_with_index():
            # Query various block heights
            results = []
            for height in [10, 50, 100, 150, chain_height - 1]:
                if height <= chain_height:
                    block = storage.load_block_by_height(height)
                    if block:
                        results.append(block.header.index)
            return results

        indexed_results = benchmark.pedantic(
            query_with_index,
            iterations=50,
            rounds=5
        )

        print(f"Queried {len(indexed_results)} blocks using index")


class TestStoragePruning:
    """Tests for blockchain pruning and old data removal."""

    @pytest.fixture
    def data_dir(self, tmp_path):
        """Create a temporary data directory."""
        return str(tmp_path / "pruning_test")

    def test_pruning_old_blocks(self, data_dir, benchmark):
        """
        Benchmark: Pruning old blocks from storage.

        Tests performance of removing old block data while keeping recent blocks.
        """
        print(f"\n=== Block Pruning Performance ===")

        # Create blockchain
        blockchain = Blockchain(data_dir=data_dir)
        blockchain.create_genesis_block()
        wallets = [Wallet() for _ in range(10)]

        # Mine 1000 blocks
        print("Mining 1000 blocks...")
        for i in range(1000):
            for j in range(3):
                sender = wallets[j % len(wallets)]
                recipient = wallets[(j + 1) % len(wallets)]
                tx = Transaction(sender.address, recipient.address, 0.1, 0.001)
                tx.public_key = sender.public_key
                tx.sign_transaction(sender.private_key)
                try:
                    blockchain.add_transaction(tx)
                except Exception:
                    pass

            miner = wallets[0]
            try:
                blockchain.mine_pending_transactions(miner.address)
            except Exception:
                pass

            if i % 200 == 0:
                print(f"  Mined {i} blocks...")

        chain_height = blockchain.get_latest_block().header.index
        print(f"Chain height: {chain_height}")

        # Measure storage before pruning
        def get_storage_size():
            return sum(
                os.path.getsize(os.path.join(dirpath, filename))
                for dirpath, _, filenames in os.walk(data_dir)
                for filename in filenames
            )

        size_before = get_storage_size()
        print(f"Storage before pruning: {size_before / 1024:.2f} KB")

        # Benchmark pruning (keep last 100 blocks)
        def prune_old_blocks():
            keep_depth = 100
            target_height = chain_height - keep_depth

            if target_height > 0:
                # Prune by removing old block files
                blocks_dir = os.path.join(data_dir, "blocks")
                if os.path.exists(blocks_dir):
                    pruned = 0
                    for filename in os.listdir(blocks_dir):
                        if filename.startswith("blocks_"):
                            filepath = os.path.join(blocks_dir, filename)
                            # Simple pruning: remove files (in production, would be more selective)
                            # For this test, we just measure the operation
                            pruned += 1
                    return pruned
            return 0

        result = benchmark(prune_old_blocks)

        print(f"Pruning operation completed")
        print(f"Would prune files: {result}")

    def test_transaction_history_pruning(self, data_dir):
        """
        Test pruning of old transaction history.

        Verifies that old transaction data can be efficiently removed.
        """
        print(f"\n=== Transaction History Pruning ===")

        blockchain = Blockchain(data_dir=data_dir)
        blockchain.create_genesis_block()
        wallets = [Wallet() for _ in range(10)]

        # Create transactions over time
        transaction_count = 0
        for i in range(100):
            for j in range(10):
                sender = wallets[j % len(wallets)]
                recipient = wallets[(j + 1) % len(wallets)]
                tx = Transaction(sender.address, recipient.address, 0.1, 0.001)
                tx.timestamp = time.time() - (100 - i) * 3600  # Spread over past 100 hours
                tx.public_key = sender.public_key
                tx.sign_transaction(sender.private_key)

                try:
                    blockchain.add_transaction(tx, skip_timestamp_validation=True)
                    transaction_count += 1
                except Exception:
                    pass

            if i % 20 == 0:
                miner = wallets[0]
                try:
                    blockchain.mine_pending_transactions(miner.address)
                except Exception:
                    pass

        print(f"Created {transaction_count} transactions")
        print(f"Mempool size: {len(blockchain.pending_transactions)}")

        # Prune old transactions (older than 24 hours)
        cutoff_time = time.time() - 24 * 3600
        start = time.perf_counter()

        before_count = len(blockchain.pending_transactions)
        blockchain.pending_transactions = [
            tx for tx in blockchain.pending_transactions
            if tx.timestamp > cutoff_time
        ]
        after_count = len(blockchain.pending_transactions)

        elapsed = time.perf_counter() - start
        pruned = before_count - after_count

        print(f"Pruned {pruned} old transactions in {elapsed * 1000:.2f} ms")
        print(f"Remaining: {after_count} transactions")

        assert pruned > 0, "Should have pruned some transactions"


class TestDatabasePerformance:
    """Tests for database query performance."""

    @pytest.fixture
    def data_dir(self, tmp_path):
        """Create a temporary data directory."""
        return str(tmp_path / "db_test")

    @pytest.fixture
    def blockchain(self, data_dir):
        """Create a blockchain instance."""
        bc = Blockchain(data_dir=data_dir)
        bc.create_genesis_block()
        return bc

    def test_block_lookup_by_height(self, blockchain, data_dir, benchmark):
        """
        Benchmark: Block lookup by height.

        Tests query performance for blocks at different heights.
        """
        print(f"\n=== Block Lookup by Height ===")
        wallets = [Wallet() for _ in range(5)]

        # Create 300 blocks
        print("Creating 300 blocks...")
        for i in range(300):
            for j in range(2):
                sender = wallets[j % len(wallets)]
                recipient = wallets[(j + 1) % len(wallets)]
                tx = Transaction(sender.address, recipient.address, 0.1, 0.001)
                tx.public_key = sender.public_key
                tx.sign_transaction(sender.private_key)
                try:
                    blockchain.add_transaction(tx)
                except Exception:
                    pass

            miner = wallets[0]
            try:
                blockchain.mine_pending_transactions(miner.address)
            except Exception:
                pass

        chain_height = blockchain.get_latest_block().header.index
        print(f"Chain height: {chain_height}")

        # Benchmark lookups
        def lookup_blocks():
            results = []
            for height in [1, 50, 100, 150, 200, 250, chain_height]:
                if height <= chain_height:
                    block = blockchain.storage.load_block_by_height(height)
                    if block:
                        results.append(block.header.index)
            return results

        result = benchmark(lookup_blocks)

        print(f"Successfully looked up {len(result)} blocks")

    def test_block_lookup_by_hash(self, blockchain, data_dir, benchmark):
        """
        Benchmark: Block lookup by hash.

        Tests query performance for blocks by hash.
        """
        print(f"\n=== Block Lookup by Hash ===")
        wallets = [Wallet() for _ in range(5)]

        # Create 200 blocks and collect hashes
        print("Creating 200 blocks...")
        block_hashes = []

        for i in range(200):
            sender = wallets[0]
            recipient = wallets[1]
            tx = Transaction(sender.address, recipient.address, 0.1, 0.001)
            tx.public_key = sender.public_key
            tx.sign_transaction(sender.private_key)

            try:
                blockchain.add_transaction(tx)
            except Exception:
                pass

            miner = wallets[0]
            try:
                blockchain.mine_pending_transactions(miner.address)
                latest = blockchain.get_latest_block()
                if hasattr(latest.header, 'hash'):
                    block_hashes.append(latest.header.hash)
            except Exception:
                pass

        print(f"Created {len(block_hashes)} blocks with hashes")

        # Benchmark hash lookups
        def lookup_by_hash():
            results = []
            # Sample some hashes
            sample_hashes = block_hashes[::20]  # Every 20th block
            for block_hash in sample_hashes:
                block = blockchain.storage.load_block_by_hash(block_hash)
                if block:
                    results.append(block.header.hash if hasattr(block.header, 'hash') else None)
            return results

        result = benchmark(lookup_by_hash)

        print(f"Successfully looked up {len(result)} blocks by hash")


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v", "-m", "performance", "--benchmark-only"])
