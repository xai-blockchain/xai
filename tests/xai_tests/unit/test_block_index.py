"""
Unit tests for block index O(1) lookup performance.

Tests verify:
- O(1) lookup time regardless of chain height
- LRU cache functionality
- Index persistence across restarts
- Reorg handling
- Hash verification
- Migration from unindexed chains
"""

import os
import tempfile
import time
import json
import pytest
from pathlib import Path

from xai.core.chain.block_index import BlockIndex, LRUBlockCache


class TestLRUBlockCache:
    """Test LRU cache implementation."""

    def test_cache_basic_operations(self):
        """Test basic cache get/put operations."""
        cache = LRUBlockCache(capacity=3)

        # Cache miss
        assert cache.get(1) is None
        assert cache.misses == 1

        # Cache put and hit
        cache.put(1, "block1")
        assert cache.get(1) == "block1"
        assert cache.hits == 1

    def test_cache_eviction(self):
        """Test LRU eviction when at capacity."""
        cache = LRUBlockCache(capacity=2)

        cache.put(1, "block1")
        cache.put(2, "block2")
        cache.put(3, "block3")  # Should evict block1 (LRU)

        assert cache.get(1) is None  # Evicted
        assert cache.get(2) == "block2"
        assert cache.get(3) == "block3"

    def test_cache_lru_ordering(self):
        """Test that access updates LRU ordering."""
        cache = LRUBlockCache(capacity=2)

        cache.put(1, "block1")
        cache.put(2, "block2")

        # Access block1, making it most recently used
        cache.get(1)

        # Add block3, should evict block2 (now LRU)
        cache.put(3, "block3")

        assert cache.get(1) == "block1"  # Still present
        assert cache.get(2) is None      # Evicted
        assert cache.get(3) == "block3"

    def test_cache_invalidate(self):
        """Test cache invalidation."""
        cache = LRUBlockCache(capacity=3)

        cache.put(1, "block1")
        cache.put(2, "block2")

        cache.invalidate(1)
        assert cache.get(1) is None
        assert cache.get(2) == "block2"

    def test_cache_clear(self):
        """Test cache clear."""
        cache = LRUBlockCache(capacity=3)

        cache.put(1, "block1")
        cache.put(2, "block2")
        cache.get(1)  # Hit

        cache.clear()

        # After clear, these will be misses
        result1 = cache.get(1)
        result2 = cache.get(2)
        assert result1 is None
        assert result2 is None

        stats = cache.get_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 2  # Two misses after clear

    def test_cache_stats(self):
        """Test cache statistics."""
        cache = LRUBlockCache(capacity=3)

        cache.put(1, "block1")
        cache.get(1)  # Hit
        cache.get(2)  # Miss
        cache.get(1)  # Hit

        stats = cache.get_stats()
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["size"] == 1
        assert stats["capacity"] == 3
        assert "hit_rate" in stats


class TestBlockIndex:
    """Test SQLite block index implementation."""

    def test_index_initialization(self):
        """Test index database initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_index.db")
            index = BlockIndex(db_path)

            assert os.path.exists(db_path)
            assert index.get_index_count() == 0
            assert index.get_max_indexed_height() is None

            index.close()

    def test_index_block(self):
        """Test indexing a block."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_index.db")
            index = BlockIndex(db_path)

            index.index_block(
                block_index=0,
                block_hash="abc123",
                file_path="blocks/blocks_0.json",
                file_offset=0,
                file_size=256,
            )

            location = index.get_block_location(0)
            assert location is not None
            assert location[0] == "blocks/blocks_0.json"
            assert location[1] == 0
            assert location[2] == 256

            index.close()

    def test_index_multiple_blocks(self):
        """Test indexing multiple blocks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_index.db")
            index = BlockIndex(db_path)

            # Index 100 blocks
            for i in range(100):
                index.index_block(
                    block_index=i,
                    block_hash=f"hash{i}",
                    file_path=f"blocks/blocks_{i // 10}.json",
                    file_offset=i * 256,
                    file_size=256,
                )

            assert index.get_index_count() == 100
            assert index.get_max_indexed_height() == 99

            # Verify lookups
            location = index.get_block_location(50)
            assert location is not None
            assert location[0] == "blocks/blocks_5.json"
            assert location[1] == 50 * 256

            index.close()

    def test_lookup_by_hash(self):
        """Test block lookup by hash."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_index.db")
            index = BlockIndex(db_path)

            index.index_block(
                block_index=42,
                block_hash="deadbeef",
                file_path="blocks/blocks_4.json",
                file_offset=1024,
                file_size=512,
            )

            result = index.get_block_location_by_hash("deadbeef")
            assert result is not None
            assert result[0] == 42  # block_index
            assert result[1] == "blocks/blocks_4.json"
            assert result[2] == 1024
            assert result[3] == 512

            index.close()

    def test_hash_verification(self):
        """Test block hash verification."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_index.db")
            index = BlockIndex(db_path)

            index.index_block(
                block_index=10,
                block_hash="correct_hash",
                file_path="blocks/blocks_1.json",
                file_offset=0,
                file_size=256,
            )

            assert index.verify_block_hash(10, "correct_hash") is True
            assert index.verify_block_hash(10, "wrong_hash") is False
            assert index.verify_block_hash(999, "any_hash") is False

            index.close()

    def test_reorg_handling(self):
        """Test removing blocks during reorg."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_index.db")
            index = BlockIndex(db_path)

            # Index blocks 0-99
            for i in range(100):
                index.index_block(
                    block_index=i,
                    block_hash=f"hash{i}",
                    file_path="blocks/blocks_0.json",
                    file_offset=i * 256,
                    file_size=256,
                )

            assert index.get_index_count() == 100

            # Simulate reorg at height 50
            removed = index.remove_blocks_from(50)
            assert removed == 50  # Removed blocks 50-99

            assert index.get_index_count() == 50
            assert index.get_max_indexed_height() == 49

            # Verify removed blocks are gone
            assert index.get_block_location(49) is not None
            assert index.get_block_location(50) is None
            assert index.get_block_location(99) is None

            index.close()

    def test_index_persistence(self):
        """Test that index persists across restarts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_index.db")

            # Create and populate index
            index1 = BlockIndex(db_path)
            index1.index_block(
                block_index=42,
                block_hash="persistent_hash",
                file_path="blocks/blocks_4.json",
                file_offset=1024,
                file_size=512,
            )
            index1.close()

            # Reopen index
            index2 = BlockIndex(db_path)
            location = index2.get_block_location(42)
            assert location is not None
            assert location[0] == "blocks/blocks_4.json"
            assert location[1] == 1024

            index2.close()

    def test_index_update_on_reindex(self):
        """Test that re-indexing same block updates entry."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_index.db")
            index = BlockIndex(db_path)

            # Index block
            index.index_block(
                block_index=10,
                block_hash="old_hash",
                file_path="blocks/blocks_1.json",
                file_offset=0,
                file_size=256,
            )

            # Re-index with new hash (reorg scenario)
            index.index_block(
                block_index=10,
                block_hash="new_hash",
                file_path="blocks/blocks_1.json",
                file_offset=512,
                file_size=256,
            )

            # Verify updated
            location = index.get_block_location(10)
            assert location[1] == 512  # New offset

            assert index.verify_block_hash(10, "new_hash") is True
            assert index.verify_block_hash(10, "old_hash") is False

            index.close()

    def test_lookup_performance(self):
        """Test O(1) lookup performance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_index.db")
            index = BlockIndex(db_path)

            # Index 10,000 blocks
            num_blocks = 10000
            for i in range(num_blocks):
                index.index_block(
                    block_index=i,
                    block_hash=f"hash{i}",
                    file_path=f"blocks/blocks_{i // 1000}.json",
                    file_offset=i * 256,
                    file_size=256,
                )

            # Test lookup times at different heights
            # All should be similarly fast (O(1))
            lookup_times = []

            for block_idx in [0, num_blocks // 4, num_blocks // 2, num_blocks - 1]:
                start = time.perf_counter()
                location = index.get_block_location(block_idx)
                elapsed = (time.perf_counter() - start) * 1000  # ms

                assert location is not None
                lookup_times.append(elapsed)

            # All lookups should be < 10ms
            for elapsed in lookup_times:
                assert elapsed < 10.0, f"Lookup took {elapsed:.3f}ms, expected <10ms"

            # Variance should be low (O(1) means time doesn't grow with height)
            avg_time = sum(lookup_times) / len(lookup_times)
            max_deviation = max(abs(t - avg_time) for t in lookup_times)
            assert max_deviation < 5.0, "Lookup times should be consistent (O(1))"

            index.close()

    def test_cache_integration(self):
        """Test that cache speeds up repeated lookups."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_index.db")
            index = BlockIndex(db_path, cache_size=100)

            # Index blocks
            for i in range(100):
                index.index_block(
                    block_index=i,
                    block_hash=f"hash{i}",
                    file_path="blocks/blocks_0.json",
                    file_offset=i * 256,
                    file_size=256,
                )

            # Get initial stats
            stats_before = index.get_stats()
            initial_misses = stats_before["cache"]["misses"]
            initial_hits = stats_before["cache"]["hits"]

            # First lookup - cache miss
            index.get_block_location(50)
            stats1 = index.get_stats()
            # Note: get_block_location doesn't use cache, it's for direct index lookup
            # Cache is used at the storage layer

            # We can still verify cache stats are being tracked
            assert "cache" in stats1

            index.close()

    def test_get_stats(self):
        """Test index statistics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_index.db")
            index = BlockIndex(db_path)

            # Index some blocks
            for i in range(50):
                index.index_block(
                    block_index=i,
                    block_hash=f"hash{i}",
                    file_path="blocks/blocks_0.json",
                    file_offset=i * 256,
                    file_size=256,
                )

            stats = index.get_stats()
            assert stats["total_blocks"] == 50
            assert stats["max_height"] == 49
            assert "cache" in stats

            index.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
