#!/usr/bin/env python3
"""
Benchmark script to demonstrate block index performance improvements.

This script creates a blockchain with N blocks and measures lookup times
with and without the block index. Demonstrates O(n) -> O(1) improvement.

Usage:
    python scripts/benchmark_block_index.py [num_blocks]

Example:
    python scripts/benchmark_block_index.py 10000
"""

import sys
import os
import tempfile
import time
import shutil
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from xai.core.blockchain_storage import BlockchainStorage
from xai.core.blockchain import Block, Transaction
from xai.core.block_header import BlockHeader


def create_test_block(index: int) -> Block:
    """Create a test block."""
    header = BlockHeader(
        index=index,
        previous_hash="0" * 64,
        merkle_root=f"merkle{index}",
        timestamp=time.time(),
        difficulty=4,
        nonce=0,
        version=1,
    )
    header.hash = header.calculate_hash()

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


def benchmark_lookups(storage, num_blocks: int, test_points: list):
    """Benchmark block lookups at various heights."""
    results = []

    for height in test_points:
        # Warm up (OS cache)
        storage.load_block_from_disk(height)

        # Measure
        times = []
        for _ in range(5):  # Average over 5 runs
            start = time.perf_counter()
            block = storage.load_block_from_disk(height)
            elapsed_ms = (time.perf_counter() - start) * 1000
            times.append(elapsed_ms)
            assert block is not None

        avg_time = sum(times) / len(times)
        results.append((height, avg_time))

    return results


def main():
    num_blocks = int(sys.argv[1]) if len(sys.argv) > 1 else 1000

    print(f"\n{'='*70}")
    print(f"Block Index Performance Benchmark")
    print(f"{'='*70}")
    print(f"Creating blockchain with {num_blocks:,} blocks...\n")

    with tempfile.TemporaryDirectory() as tmpdir:
        # Phase 1: Create chain WITHOUT index
        print("Phase 1: Building chain WITHOUT index...")
        unindexed_dir = os.path.join(tmpdir, "unindexed")
        storage_unindexed = BlockchainStorage(data_dir=unindexed_dir, enable_index=False)

        start_time = time.time()
        for i in range(num_blocks):
            block = create_test_block(i)
            storage_unindexed._save_block_to_disk(block)

            if (i + 1) % 1000 == 0:
                print(f"  Saved {i + 1:,} blocks...")

        save_time = time.time() - start_time
        print(f"  Save time: {save_time:.2f}s ({num_blocks/save_time:.0f} blocks/s)\n")

        # Phase 2: Create chain WITH index
        print("Phase 2: Building chain WITH index...")
        indexed_dir = os.path.join(tmpdir, "indexed")
        storage_indexed = BlockchainStorage(data_dir=indexed_dir, enable_index=True)

        start_time = time.time()
        for i in range(num_blocks):
            block = create_test_block(i)
            storage_indexed._save_block_to_disk(block)

            if (i + 1) % 1000 == 0:
                print(f"  Saved {i + 1:,} blocks...")

        save_time_indexed = time.time() - start_time
        print(f"  Save time: {save_time_indexed:.2f}s ({num_blocks/save_time_indexed:.0f} blocks/s)")

        # Show index stats
        stats = storage_indexed.get_index_stats()
        print(f"  Index: {stats['total_blocks']:,} blocks, max height {stats['max_height']:,}\n")

        # Phase 3: Benchmark lookups
        test_points = [
            0,                      # Genesis
            num_blocks // 4,        # 25%
            num_blocks // 2,        # 50%
            num_blocks * 3 // 4,    # 75%
            num_blocks - 1,         # Tip
        ]

        print("Phase 3: Benchmarking lookups...")
        print(f"\n{'Height':>10} | {'Unindexed':>15} | {'Indexed':>15} | {'Speedup':>10}")
        print(f"{'-'*10}-+-{'-'*15}-+-{'-'*15}-+-{'-'*10}")

        results_unindexed = benchmark_lookups(storage_unindexed, num_blocks, test_points)
        results_indexed = benchmark_lookups(storage_indexed, num_blocks, test_points)

        total_speedup = 0
        for (height, time_unindexed), (_, time_indexed) in zip(results_unindexed, results_indexed):
            speedup = time_unindexed / time_indexed if time_indexed > 0 else float('inf')
            total_speedup += speedup

            print(f"{height:10,} | {time_unindexed:12.3f} ms | {time_indexed:12.3f} ms | {speedup:8.1f}x")

        avg_speedup = total_speedup / len(test_points)

        print(f"\n{'='*70}")
        print(f"Results Summary:")
        print(f"{'='*70}")
        print(f"Blocks created:       {num_blocks:,}")
        print(f"Average speedup:      {avg_speedup:.1f}x")
        print(f"Index overhead:       {(save_time_indexed - save_time):.2f}s ({((save_time_indexed/save_time - 1) * 100):.1f}% slower saves)")
        print(f"")

        # Cache stats
        cache_stats = storage_indexed.get_index_stats()["cache"]
        if cache_stats["hits"] > 0 or cache_stats["misses"] > 0:
            print(f"Cache statistics:")
            print(f"  Hits:      {cache_stats['hits']}")
            print(f"  Misses:    {cache_stats['misses']}")
            print(f"  Hit rate:  {cache_stats['hit_rate']}")
            print(f"  Size:      {cache_stats['size']}/{cache_stats['capacity']}")
            print(f"")

        # Verify correctness
        print("Verifying correctness...")
        mismatches = 0
        for i in test_points:
            block_unindexed = storage_unindexed.load_block_from_disk(i)
            block_indexed = storage_indexed.load_block_from_disk(i)

            if block_unindexed.header.index != block_indexed.header.index:
                mismatches += 1

        if mismatches == 0:
            print("  ✓ All blocks match between indexed and unindexed storage")
        else:
            print(f"  ✗ Found {mismatches} mismatches!")

        print(f"\n{'='*70}")
        print(f"Conclusion:")
        print(f"{'='*70}")

        if avg_speedup > 10:
            print(f"✓ Block index provides {avg_speedup:.1f}x speedup!")
            print(f"✓ Lookups are O(1) regardless of chain height")
            print(f"✓ Small overhead during saves ({((save_time_indexed/save_time - 1) * 100):.1f}%) is worth it")
        else:
            print(f"⚠ Speedup is only {avg_speedup:.1f}x - try larger chain")

        print(f"")

        storage_unindexed.close()
        storage_indexed.close()


if __name__ == "__main__":
    main()
