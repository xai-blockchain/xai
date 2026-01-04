"""
Tests for blockchain storage compression feature.

Tests verify:
- Compression of old blocks (>1000 blocks from tip)
- Transparent decompression on read
- Disk space savings (~70%)
- Compression threshold logic
- Performance of compressed block access
"""

import gzip
import json
import os
import tempfile
import time
import pytest
from pathlib import Path

from xai.core.chain.blockchain_storage import BlockchainStorage, COMPRESSION_THRESHOLD
from xai.core.blockchain import Block, Transaction
from xai.core.chain.block_header import BlockHeader


def create_test_block(index: int, previous_hash: str = "0" * 64) -> Block:
    """Create a test block."""
    header = BlockHeader(
        index=index,
        previous_hash=previous_hash,
        merkle_root=f"{index:064x}",
        timestamp=time.time(),
        difficulty=4,
        nonce=0,
        version=1,
    )
    # Calculate hash
    header.hash = header.calculate_hash()

    # Create a test transaction with valid XAI addresses
    tx = Transaction(
        sender="XAI" + "0" * 60,
        recipient="XAI" + "1" * 60,
        amount=100,
        fee=1,
        public_key="0" * 128,
        tx_type="transfer",
    )
    tx.txid = f"tx{index}"
    tx.signature = "0" * 128

    return Block(header, [tx])


class TestBlockchainStorageCompression:
    """Test blockchain storage compression feature."""

    def test_compression_threshold_logic(self):
        """Test that compression threshold is correctly evaluated."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = BlockchainStorage(data_dir=tmpdir)

            # Save blocks 0-1100
            num_blocks = 1100
            for i in range(num_blocks):
                block = create_test_block(i)
                storage._save_block_to_disk(block)

            # Latest index is 1099
            latest = storage._get_latest_block_index()
            assert latest == 1099

            # Block 0 should be compressed (1099 - 0 = 1099 >= 1000)
            assert storage._should_compress_block(0) is True

            # Block 99 should be compressed (1099 - 99 = 1000 >= 1000)
            assert storage._should_compress_block(99) is True

            # Block 100 should NOT be compressed (1099 - 100 = 999 < 1000)
            assert storage._should_compress_block(100) is False

            # Block 1099 (latest) should NOT be compressed
            assert storage._should_compress_block(1099) is False

            storage.close()

    def test_compress_old_blocks(self):
        """Test compression of old blocks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = BlockchainStorage(data_dir=tmpdir)

            # Save 1200 blocks
            num_blocks = 1200
            for i in range(num_blocks):
                block = create_test_block(i)
                storage._save_block_to_disk(block)

            # Compress old blocks
            compressed_count = storage.compress_old_blocks()

            # Should compress blocks 0-199 (200 blocks total)
            # Because 1199 - 199 = 1000 (threshold)
            assert compressed_count == 200

            # Verify compressed files exist
            for i in range(200):
                compressed_path = os.path.join(
                    tmpdir, "blocks", f"block_{i}.json.gz"
                )
                assert os.path.exists(compressed_path), f"Block {i} not compressed"

            # Verify recent blocks NOT compressed
            for i in range(200, num_blocks):
                compressed_path = os.path.join(
                    tmpdir, "blocks", f"block_{i}.json.gz"
                )
                assert not os.path.exists(
                    compressed_path
                ), f"Block {i} should not be compressed"

            storage.close()

    def test_transparent_decompression(self):
        """Test that compressed blocks are transparently decompressed on read."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = BlockchainStorage(data_dir=tmpdir)

            # Save 1200 blocks
            num_blocks = 1200
            for i in range(num_blocks):
                block = create_test_block(i)
                storage._save_block_to_disk(block)

            # Compress old blocks
            storage.compress_old_blocks()

            # Load compressed blocks (should work transparently)
            for i in range(0, 200, 10):  # Sample every 10th block
                loaded_block = storage.load_block_from_disk(i)
                assert loaded_block is not None
                assert loaded_block.header.index == i

            # Load uncompressed blocks
            for i in range(200, num_blocks, 50):  # Sample every 50th block
                loaded_block = storage.load_block_from_disk(i)
                assert loaded_block is not None
                assert loaded_block.header.index == i

            storage.close()

    def test_disk_space_savings(self):
        """Test that compression achieves ~70% disk space savings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = BlockchainStorage(data_dir=tmpdir)

            # Create 100 blocks for accurate measurement
            num_blocks = 100
            for i in range(num_blocks):
                block = create_test_block(i)
                storage._save_block_to_disk(block)

            # Calculate size of uncompressed blocks
            uncompressed_size = 0
            block_files = [
                f
                for f in os.listdir(os.path.join(tmpdir, "blocks"))
                if f.startswith("blocks_") and f.endswith(".json")
            ]
            for bf in block_files:
                path = os.path.join(tmpdir, "blocks", bf)
                uncompressed_size += os.path.getsize(path)

            # Force compress all blocks
            storage.compress_old_blocks(force=True)

            # Calculate size of compressed blocks
            compressed_size = 0
            for i in range(num_blocks):
                compressed_path = os.path.join(
                    tmpdir, "blocks", f"block_{i}.json.gz"
                )
                if os.path.exists(compressed_path):
                    compressed_size += os.path.getsize(compressed_path)

            # Calculate savings
            savings_percent = (
                (uncompressed_size - compressed_size) / uncompressed_size * 100
            )

            print(f"\nCompression statistics:")
            print(f"  Uncompressed: {uncompressed_size:,} bytes")
            print(f"  Compressed:   {compressed_size:,} bytes")
            print(f"  Savings:      {savings_percent:.1f}%")

            # Verify at least 50% savings (conservative, typically ~70%)
            assert savings_percent >= 50.0, f"Compression savings too low: {savings_percent:.1f}%"

            # Verify not more than 90% (sanity check)
            assert savings_percent <= 90.0, f"Compression savings suspiciously high: {savings_percent:.1f}%"

            storage.close()

    def test_compression_idempotent(self):
        """Test that running compression multiple times is safe."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = BlockchainStorage(data_dir=tmpdir)

            # Save 1200 blocks
            for i in range(1200):
                block = create_test_block(i)
                storage._save_block_to_disk(block)

            # Run compression
            count1 = storage.compress_old_blocks()
            assert count1 == 200

            # Run compression again - should skip already compressed
            count2 = storage.compress_old_blocks()
            assert count2 == 0, "Second compression should skip existing files"

            # Verify blocks are still loadable
            for i in range(0, 200, 20):
                block = storage.load_block_from_disk(i)
                assert block is not None
                assert block.header.index == i

            storage.close()

    def test_compressed_block_file_format(self):
        """Test that compressed blocks are valid gzip files with correct JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = BlockchainStorage(data_dir=tmpdir)

            # Create test block
            test_block = create_test_block(42)
            storage._save_block_to_disk(test_block)

            # Manually compress it
            block_data = test_block.to_dict()
            compressed_path = os.path.join(tmpdir, "blocks", "block_42.json.gz")

            with gzip.open(compressed_path, "wt", encoding="utf-8") as f:
                json.dump(block_data, f)

            # Load using storage - should decompress transparently
            loaded_block = storage.load_block_from_disk(42)
            assert loaded_block is not None
            assert loaded_block.header.index == 42

            # Verify it's actually compressed
            assert os.path.exists(compressed_path)

            # Manually verify gzip format
            with gzip.open(compressed_path, "rt", encoding="utf-8") as f:
                decompressed_data = json.loads(f.read())
                # Support both nested header format and flattened format
                if "header" in decompressed_data and decompressed_data["header"]:
                    assert decompressed_data["header"]["index"] == 42
                else:
                    assert decompressed_data["index"] == 42

            storage.close()

    def test_compression_with_disabled_index(self):
        """Test compression works even without block index."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = BlockchainStorage(data_dir=tmpdir, enable_index=False)

            # Save 1200 blocks
            for i in range(1200):
                block = create_test_block(i)
                storage._save_block_to_disk(block)

            # Compress old blocks
            compressed_count = storage.compress_old_blocks()
            assert compressed_count == 200

            # Load compressed blocks (should fall back to sequential scan)
            block_0 = storage.load_block_from_disk(0)
            assert block_0 is not None
            assert block_0.header.index == 0

            storage.close()

    def test_performance_compressed_blocks(self):
        """Test that accessing compressed blocks has acceptable performance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = BlockchainStorage(data_dir=tmpdir)

            # Save 1200 blocks
            for i in range(1200):
                block = create_test_block(i)
                storage._save_block_to_disk(block)

            # Compress old blocks
            storage.compress_old_blocks()

            # Measure access time for compressed blocks
            compressed_times = []
            for i in range(0, 100, 10):  # Sample 10 compressed blocks
                start = time.perf_counter()
                block = storage.load_block_from_disk(i)
                elapsed = (time.perf_counter() - start) * 1000  # ms
                compressed_times.append(elapsed)
                assert block is not None

            # Measure access time for uncompressed blocks
            uncompressed_times = []
            for i in range(1100, 1200, 10):  # Sample 10 uncompressed blocks
                start = time.perf_counter()
                block = storage.load_block_from_disk(i)
                elapsed = (time.perf_counter() - start) * 1000  # ms
                uncompressed_times.append(elapsed)
                assert block is not None

            avg_compressed = sum(compressed_times) / len(compressed_times)
            avg_uncompressed = sum(uncompressed_times) / len(uncompressed_times)

            print(f"\nAccess performance:")
            print(f"  Compressed:   {avg_compressed:.3f}ms")
            print(f"  Uncompressed: {avg_uncompressed:.3f}ms")

            # Compressed should still be reasonably fast (<50ms)
            assert avg_compressed < 50.0, f"Compressed access too slow: {avg_compressed:.3f}ms"

            storage.close()

    def test_force_compression(self):
        """Test force compression of all blocks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = BlockchainStorage(data_dir=tmpdir)

            # Save only 100 blocks (all recent)
            num_blocks = 100
            for i in range(num_blocks):
                block = create_test_block(i)
                storage._save_block_to_disk(block)

            # Normal compression should compress 0 blocks
            count_normal = storage.compress_old_blocks(force=False)
            assert count_normal == 0

            # Force compression should compress all
            count_force = storage.compress_old_blocks(force=True)
            assert count_force == num_blocks

            # Verify all blocks compressed
            for i in range(num_blocks):
                compressed_path = os.path.join(
                    tmpdir, "blocks", f"block_{i}.json.gz"
                )
                assert os.path.exists(compressed_path)

            storage.close()

    def test_get_block_file_path(self):
        """Test helper method for getting block file paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = BlockchainStorage(data_dir=tmpdir)

            # Test with no files existing
            path = storage._get_block_file_path(42, compressed=False)
            assert path.endswith("block_42.json")

            # Create compressed file
            compressed_path = os.path.join(tmpdir, "blocks", "block_42.json.gz")
            os.makedirs(os.path.dirname(compressed_path), exist_ok=True)
            with gzip.open(compressed_path, "wt") as f:
                f.write("{}")

            # Should return compressed path
            path = storage._get_block_file_path(42, compressed=False)
            assert path == compressed_path

            # Create uncompressed file
            uncompressed_path = os.path.join(tmpdir, "blocks", "block_43.json")
            with open(uncompressed_path, "w") as f:
                f.write("{}")

            # Should return uncompressed path
            path = storage._get_block_file_path(43, compressed=False)
            assert path == uncompressed_path

            storage.close()

    def test_compression_error_handling(self):
        """Test that compression handles errors gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = BlockchainStorage(data_dir=tmpdir)

            # Create some valid blocks first
            for i in range(5):
                block = create_test_block(i)
                storage._save_block_to_disk(block)

            # Create a corrupt block file with mixed valid/invalid JSON
            blocks_dir = os.path.join(tmpdir, "blocks")
            corrupt_file = os.path.join(blocks_dir, "blocks_99.json")

            with open(corrupt_file, "w") as f:
                f.write("{\n")  # Invalid JSON - should be skipped
                f.write('{"header": {"index": 100}, "transactions": []}\n')  # Valid JSON
                f.write("not json\n")  # Invalid JSON - should be skipped

            # Compression should handle errors and continue
            compressed_count = storage.compress_old_blocks(force=True)

            # Should have compressed the 5 valid blocks + 1 from corrupt file
            assert compressed_count >= 5

            storage.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
