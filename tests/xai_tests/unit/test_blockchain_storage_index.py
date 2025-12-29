"""
Integration tests for blockchain storage with block indexing.

Tests verify:
- Indexed vs non-indexed performance comparison
- Migration from unindexed to indexed chains
- Index consistency during saves
- Reorg handling in storage
- Cache effectiveness
"""

import os
import tempfile
import time
import json
import pytest
from pathlib import Path

from xai.core.chain.blockchain_storage import BlockchainStorage
from xai.core.blockchain import Block, Transaction
from xai.core.chain.block_header import BlockHeader


def create_test_block(index: int, previous_hash: str = "0" * 64) -> Block:
    """Create a test block."""
    header = BlockHeader(
        index=index,
        previous_hash=previous_hash,
        merkle_root="merkle" + str(index),
        timestamp=time.time(),
        difficulty=4,
        nonce=0,
        version=1,
    )
    # Calculate hash
    header.hash = header.calculate_hash()

    # Create a test transaction with valid XAI addresses
    tx = Transaction(
        sender="XAI" + "0" * 60,  # Valid XAI address format
        recipient="XAI" + "1" * 60,  # Valid XAI address format
        amount=100,
        fee=1,
        public_key="0" * 128,  # Valid hex pubkey
        tx_type="transfer",
    )
    tx.txid = f"tx{index}"
    tx.signature = "0" * 128  # Valid hex signature

    return Block(header, [tx])


class TestBlockchainStorageIndex:
    """Test blockchain storage with block index."""

    def test_index_enabled_by_default(self):
        """Test that index is enabled by default."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = BlockchainStorage(data_dir=tmpdir)
            assert storage.enable_index is True
            assert storage.block_index is not None
            storage.close()

    def test_index_can_be_disabled(self):
        """Test that index can be disabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = BlockchainStorage(data_dir=tmpdir, enable_index=False)
            assert storage.enable_index is False
            assert storage.block_index is None
            storage.close()

    def test_save_and_load_with_index(self):
        """Test saving and loading blocks with index."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = BlockchainStorage(data_dir=tmpdir)

            # Save blocks
            blocks = [create_test_block(i) for i in range(10)]
            for block in blocks:
                storage._save_block_to_disk(block)

            # Verify index was updated
            stats = storage.get_index_stats()
            assert stats["total_blocks"] == 10
            assert stats["max_height"] == 9

            # Load blocks via index
            for i in range(10):
                loaded = storage.load_block_from_disk(i)
                assert loaded is not None
                assert loaded.header.index == i

            storage.close()

    def test_indexed_vs_unindexed_performance(self):
        """Test performance difference between indexed and unindexed lookups."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create two storage instances: indexed and unindexed
            indexed_storage = BlockchainStorage(
                data_dir=os.path.join(tmpdir, "indexed"),
                enable_index=True
            )
            unindexed_storage = BlockchainStorage(
                data_dir=os.path.join(tmpdir, "unindexed"),
                enable_index=False
            )

            # Save 1000 blocks to both
            num_blocks = 1000
            for i in range(num_blocks):
                block = create_test_block(i)
                indexed_storage._save_block_to_disk(block)
                unindexed_storage._save_block_to_disk(block)

            # Test lookup performance at end of chain
            # (worst case for sequential scan)
            test_index = num_blocks - 1

            # Warm up (to account for OS caching)
            indexed_storage.load_block_from_disk(test_index)
            unindexed_storage.load_block_from_disk(test_index)

            # Measure indexed lookup
            start = time.perf_counter()
            block_indexed = indexed_storage.load_block_from_disk(test_index)
            indexed_time = (time.perf_counter() - start) * 1000  # ms

            # Measure unindexed lookup
            start = time.perf_counter()
            block_unindexed = unindexed_storage.load_block_from_disk(test_index)
            unindexed_time = (time.perf_counter() - start) * 1000  # ms

            # Both should load successfully
            assert block_indexed is not None
            assert block_unindexed is not None

            # Indexed should be MUCH faster
            speedup = unindexed_time / indexed_time if indexed_time > 0 else float('inf')
            print(f"\nPerformance comparison (block {test_index}):")
            print(f"  Indexed:   {indexed_time:.3f}ms")
            print(f"  Unindexed: {unindexed_time:.3f}ms")
            print(f"  Speedup:   {speedup:.1f}x")

            # Indexed should be <10ms
            assert indexed_time < 10.0, f"Indexed lookup too slow: {indexed_time:.3f}ms"

            # At 1000 blocks, indexed should be at least 5x faster
            assert speedup > 5.0, f"Speedup too low: {speedup:.1f}x"

            indexed_storage.close()
            unindexed_storage.close()

    def test_index_migration_on_startup(self):
        """Test automatic index building for existing chain."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Phase 1: Create chain without index
            storage1 = BlockchainStorage(data_dir=tmpdir, enable_index=False)

            for i in range(100):
                block = create_test_block(i)
                storage1._save_block_to_disk(block)

            storage1.close()

            # Verify no index exists
            index_path = os.path.join(tmpdir, "block_index.db")
            assert not os.path.exists(index_path)

            # Phase 2: Reopen with index enabled
            storage2 = BlockchainStorage(data_dir=tmpdir, enable_index=True)

            # Index should be built automatically
            assert os.path.exists(index_path)
            stats = storage2.get_index_stats()
            assert stats["total_blocks"] == 100
            assert stats["max_height"] == 99

            # Verify all blocks can be loaded via index
            for i in range(100):
                block = storage2.load_block_from_disk(i)
                assert block is not None
                assert block.header.index == i

            storage2.close()

    def test_cache_effectiveness(self):
        """Test that LRU cache improves performance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = BlockchainStorage(data_dir=tmpdir)

            # Save blocks
            for i in range(100):
                block = create_test_block(i)
                storage._save_block_to_disk(block)

            # First access - cache miss
            stats_before = storage.get_index_stats()
            storage.load_block_from_disk(50)
            stats_after_miss = storage.get_index_stats()

            assert stats_after_miss["cache"]["misses"] > stats_before["cache"]["misses"]

            # Second access - cache hit
            storage.load_block_from_disk(50)
            stats_after_hit = storage.get_index_stats()

            assert stats_after_hit["cache"]["hits"] > stats_after_miss["cache"]["hits"]

            # Access many blocks to test cache eviction
            for i in range(300):  # More than cache size
                storage.load_block_from_disk(i % 100)

            final_stats = storage.get_index_stats()
            assert final_stats["cache"]["hits"] > 0
            assert final_stats["cache"]["size"] <= 256  # Cache capacity

            storage.close()

    def test_reorg_handling(self):
        """Test that reorgs properly update index."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = BlockchainStorage(data_dir=tmpdir)

            # Save blocks 0-99
            for i in range(100):
                block = create_test_block(i)
                storage._save_block_to_disk(block)

            # Simulate reorg at height 50
            storage.handle_reorg(50)

            # Index should have removed blocks 50-99
            stats = storage.get_index_stats()
            assert stats["total_blocks"] == 50
            assert stats["max_height"] == 49

            # Blocks before fork point should be loadable
            block_49 = storage.load_block_from_disk(49)
            assert block_49 is not None

            # Blocks after fork point should still be in files
            # but index won't find them quickly
            block_50 = storage.load_block_from_disk(50)
            # Will fall back to sequential scan and find it

            storage.close()

    def test_hash_verification_in_index(self):
        """Test that block hashes are correctly stored in index."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = BlockchainStorage(data_dir=tmpdir)

            # Save block with known hash
            block = create_test_block(42)
            block_hash = block.header.hash
            storage._save_block_to_disk(block)

            # Verify hash in index
            assert storage.block_index.verify_block_hash(42, block_hash)
            assert not storage.block_index.verify_block_hash(42, "wrong_hash")

            storage.close()

    def test_load_chain_with_index(self):
        """Test loading entire chain with index present."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = BlockchainStorage(data_dir=tmpdir)

            # Save blocks
            num_blocks = 50
            for i in range(num_blocks):
                block = create_test_block(i, previous_hash=f"prev{i-1}" if i > 0 else "0" * 64)
                storage._save_block_to_disk(block)

            # Load entire chain
            chain = storage.load_chain_from_disk()

            assert len(chain) == num_blocks
            for i, block in enumerate(chain):
                assert block.header.index == i

            storage.close()

    def test_concurrent_index_access(self):
        """Test that index handles concurrent access safely."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = BlockchainStorage(data_dir=tmpdir)

            # Save blocks
            for i in range(100):
                block = create_test_block(i)
                storage._save_block_to_disk(block)

            # Multiple rapid lookups (simulating concurrent access)
            results = []
            for _ in range(100):
                for i in [0, 25, 50, 75, 99]:
                    block = storage.load_block_from_disk(i)
                    results.append(block is not None)

            # All lookups should succeed
            assert all(results)

            storage.close()

    def test_index_stats_reporting(self):
        """Test index statistics reporting."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = BlockchainStorage(data_dir=tmpdir)

            # Save blocks
            for i in range(50):
                block = create_test_block(i)
                storage._save_block_to_disk(block)

            # Access some blocks
            storage.load_block_from_disk(10)
            storage.load_block_from_disk(10)  # Hit
            storage.load_block_from_disk(20)

            stats = storage.get_index_stats()

            assert stats["total_blocks"] == 50
            assert stats["max_height"] == 49
            assert "cache" in stats
            assert stats["cache"]["hits"] >= 1
            assert stats["cache"]["misses"] >= 1

            storage.close()

    def test_fallback_to_sequential_scan(self):
        """Test fallback to sequential scan when index lookup fails."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = BlockchainStorage(data_dir=tmpdir, enable_index=False)

            # Save blocks without index
            for i in range(10):
                block = create_test_block(i)
                storage._save_block_to_disk(block)

            # Should use fallback method
            block = storage.load_block_from_disk(5)
            assert block is not None
            assert block.header.index == 5

            storage.close()

    def test_benchmark_large_chain(self):
        """Benchmark performance with large chain."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = BlockchainStorage(data_dir=tmpdir)

            # Create larger chain
            num_blocks = 5000
            print(f"\nCreating chain with {num_blocks} blocks...")

            save_start = time.time()
            for i in range(num_blocks):
                block = create_test_block(i)
                storage._save_block_to_disk(block)

                if (i + 1) % 1000 == 0:
                    print(f"  Saved {i + 1} blocks...")

            save_time = time.time() - save_start
            print(f"Save time: {save_time:.2f}s ({num_blocks/save_time:.0f} blocks/s)")

            # Test lookups at various heights
            test_heights = [0, num_blocks // 4, num_blocks // 2, num_blocks - 1]

            print("\nLookup performance:")
            for height in test_heights:
                start = time.perf_counter()
                block = storage.load_block_from_disk(height)
                elapsed_ms = (time.perf_counter() - start) * 1000

                assert block is not None
                assert block.header.index == height
                print(f"  Block {height:5d}: {elapsed_ms:.3f}ms")

                # All lookups should be <10ms
                assert elapsed_ms < 10.0, f"Lookup at height {height} too slow: {elapsed_ms:.3f}ms"

            storage.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
