"""
Tests for EVM bytecode caching optimization.

Verifies that contract bytecode is properly cached to avoid redundant
dictionary lookups and hex decoding on every contract call.

This optimization is critical for performance with popular contracts
(DeFi protocols, tokens) that may be called hundreds of times per block.
"""

import time
import pytest
from unittest.mock import MagicMock

from xai.core.vm.evm.executor import EVMBytecodeExecutor
from xai.core.vm.evm.opcodes import Opcode
from xai.core.vm.executor import ExecutionMessage


class TestBytecodeCaching:
    """Tests for bytecode caching functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create a simple contract that returns a constant value
        # PUSH1 0x42, PUSH1 0x00, MSTORE, PUSH1 0x20, PUSH1 0x00, RETURN
        self.simple_code = bytes([
            Opcode.PUSH1, 0x42,  # Push value 0x42
            Opcode.PUSH1, 0x00,  # Push memory offset 0
            Opcode.MSTORE,       # Store to memory
            Opcode.PUSH1, 0x20,  # Push size 32
            Opcode.PUSH1, 0x00,  # Push offset 0
            Opcode.RETURN,       # Return 32 bytes from memory
        ])

        self.contract_address = "0x1234567890123456789012345678901234567890"

        # Create blockchain mock
        self.blockchain = MagicMock()
        self.blockchain.contracts = {
            self.contract_address.upper(): {
                "address": self.contract_address.upper(),
                "code": self.simple_code.hex(),
                "storage": {},
            }
        }
        self.blockchain.get_balance = MagicMock(return_value=1000000)
        self.blockchain.chain = []  # Empty chain for simplicity

        # Create executor
        self.executor = EVMBytecodeExecutor(self.blockchain)

    def test_cache_initially_empty(self):
        """Test that cache starts empty."""
        stats = self.executor.get_cache_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["size"] == 0
        assert stats["max_size"] == 256

    def test_first_access_is_cache_miss(self):
        """Test that first access to contract is a cache miss."""
        code = self.executor._get_contract_code(self.contract_address)

        assert code == self.simple_code
        stats = self.executor.get_cache_stats()
        assert stats["misses"] == 1
        assert stats["hits"] == 0
        assert stats["size"] == 1

    def test_second_access_is_cache_hit(self):
        """Test that second access to same contract is a cache hit."""
        # First access (miss)
        code1 = self.executor._get_contract_code(self.contract_address)

        # Second access (hit)
        code2 = self.executor._get_contract_code(self.contract_address)

        assert code1 == code2 == self.simple_code
        stats = self.executor.get_cache_stats()
        assert stats["misses"] == 1
        assert stats["hits"] == 1
        assert stats["hit_rate"] == 0.5

    def test_cache_hit_rate_increases(self):
        """Test that cache hit rate increases with repeated accesses."""
        # First access (miss)
        self.executor._get_contract_code(self.contract_address)

        # Multiple subsequent accesses (hits)
        for _ in range(99):
            self.executor._get_contract_code(self.contract_address)

        stats = self.executor.get_cache_stats()
        assert stats["misses"] == 1
        assert stats["hits"] == 99
        assert stats["hit_rate"] == 0.99

    def test_cache_handles_nonexistent_contract(self):
        """Test that cache properly handles requests for non-existent contracts."""
        nonexistent = "0xDEADBEEFDEADBEEFDEADBEEFDEADBEEFDEADBEEF"

        # First access
        code1 = self.executor._get_contract_code(nonexistent)
        assert code1 == b""

        # Second access (should still be cached as empty)
        code2 = self.executor._get_contract_code(nonexistent)
        assert code2 == b""

        stats = self.executor.get_cache_stats()
        assert stats["misses"] == 1  # Only one miss
        assert stats["hits"] == 1    # Second access is a hit (cached empty result)

    def test_cache_normalizes_address_case(self):
        """Test that cache treats uppercase and lowercase addresses the same."""
        lowercase = self.contract_address.lower()
        uppercase = self.contract_address.upper()
        mixed = "0x1234567890aBcDeF1234567890AbCdEf12345678"

        # Add mixed case version to blockchain
        self.blockchain.contracts[mixed.upper()] = {
            "code": self.simple_code.hex(),
        }

        # Access with different case variations
        code1 = self.executor._get_contract_code(lowercase)
        code2 = self.executor._get_contract_code(uppercase)
        code3 = self.executor._get_contract_code(mixed)

        # All should return the same code
        assert code1 == code2 == self.simple_code

        # Should only be 2 cache misses (original + mixed), rest are hits
        stats = self.executor.get_cache_stats()
        assert stats["misses"] == 2
        assert stats["hits"] == 1

    def test_cache_eviction_when_full(self):
        """Test that cache evicts oldest entries when reaching size limit."""
        # Set small cache size for testing
        self.executor._cache_max_size = 10

        # Add 15 contracts (exceeds limit)
        for i in range(15):
            addr = f"0x{i:040x}"
            self.blockchain.contracts[addr.upper()] = {
                "code": self.simple_code.hex(),
            }
            self.executor._get_contract_code(addr)

        stats = self.executor.get_cache_stats()
        # Cache should be limited to max_size
        assert stats["size"] <= self.executor._cache_max_size

    def test_invalidate_specific_contract(self):
        """Test that invalidating a specific contract removes it from cache."""
        # Load contract into cache
        self.executor._get_contract_code(self.contract_address)
        assert self.executor.get_cache_stats()["size"] == 1

        # Invalidate it
        self.executor.invalidate_contract_cache(self.contract_address)

        # Cache should be empty for this contract
        assert self.executor.get_cache_stats()["size"] == 0

        # Next access should be a miss
        self.executor._get_contract_code(self.contract_address)
        stats = self.executor.get_cache_stats()
        assert stats["misses"] == 2  # Original miss + miss after invalidation

    def test_invalidate_entire_cache(self):
        """Test that invalidating entire cache clears all entries and stats."""
        # Load multiple contracts into cache
        for i in range(5):
            addr = f"0x{i:040x}"
            self.blockchain.contracts[addr.upper()] = {
                "code": self.simple_code.hex(),
            }
            self.executor._get_contract_code(addr)

        assert self.executor.get_cache_stats()["size"] == 5

        # Invalidate entire cache
        self.executor.invalidate_contract_cache(None)

        # Cache should be completely empty and stats reset
        stats = self.executor.get_cache_stats()
        assert stats["size"] == 0
        assert stats["hits"] == 0
        assert stats["misses"] == 0

    def test_store_contract_invalidates_cache(self):
        """Test that storing a contract invalidates its cache entry."""
        from xai.core.vm.evm.storage import EVMStorage

        # Load contract into cache
        self.executor._get_contract_code(self.contract_address)
        assert self.executor.get_cache_stats()["size"] == 1

        # Deploy new contract at same address (CREATE2 scenario)
        new_code = bytes([Opcode.PUSH1, 0xFF, Opcode.STOP])
        self.executor._store_contract(
            address=self.contract_address,
            code=new_code,
            creator="0x" + "a" * 40,
            storage=EVMStorage(address=self.contract_address),
        )

        # Cache should be invalidated for this address
        # Next access should fetch new code
        code = self.executor._get_contract_code(self.contract_address)
        assert code == new_code

        # Should have had a cache miss after invalidation
        stats = self.executor.get_cache_stats()
        assert stats["misses"] == 2  # Original + after invalidation

    def test_cache_performance_benefit(self):
        """Test that caching provides significant performance improvement."""
        # Deploy a large contract
        large_code = bytes([Opcode.PUSH1] + [i % 256 for i in range(1000)]).ljust(10000, b'\x00')
        large_addr = "0xBEEFBEEFBEEFBEEFBEEFBEEFBEEFBEEFBEEFBEEF"
        self.blockchain.contracts[large_addr.upper()] = {
            "code": large_code.hex(),  # 20KB hex string
        }

        # Time first access (cache miss)
        start = time.perf_counter()
        code1 = self.executor._get_contract_code(large_addr)
        miss_time = time.perf_counter() - start

        # Time subsequent accesses (cache hits)
        hit_times = []
        for _ in range(100):
            start = time.perf_counter()
            code = self.executor._get_contract_code(large_addr)
            hit_times.append(time.perf_counter() - start)

        avg_hit_time = sum(hit_times) / len(hit_times)

        # Cache hits should be significantly faster
        # We expect at least 10x speedup (conservative)
        assert avg_hit_time < miss_time / 10, (
            f"Cache hit ({avg_hit_time:.6f}s) not significantly faster than "
            f"cache miss ({miss_time:.6f}s)"
        )

        # Verify all returned same code
        assert code == code1 == large_code

    def test_cache_with_execution_message(self):
        """Test that cache works properly during actual contract execution."""
        # Create execution message
        message = ExecutionMessage(
            sender="0x" + "a" * 40,
            to=self.contract_address,
            value=0,
            gas_limit=100000,
            data=b"",
            nonce=0,
        )

        # Execute contract multiple times
        for _ in range(10):
            result = self.executor.execute(message)
            assert result.success

        # Should have high cache hit rate
        stats = self.executor.get_cache_stats()
        # First call is miss, rest are hits
        # (may be slightly more due to internal calls)
        assert stats["hits"] >= 9

    def test_cache_with_hex_and_bytes_code(self):
        """Test that cache handles both hex string and bytes code formats."""
        # Contract with hex string code
        hex_addr = "0xABCDABCDABCDABCDABCDABCDABCDABCDABCDABCD"
        self.blockchain.contracts[hex_addr.upper()] = {
            "code": self.simple_code.hex(),  # Hex string
        }

        # Contract with bytes code
        bytes_addr = "0xBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"
        self.blockchain.contracts[bytes_addr.upper()] = {
            "code": self.simple_code,  # Raw bytes
        }

        # Both should work and be cached properly
        code1 = self.executor._get_contract_code(hex_addr)
        code2 = self.executor._get_contract_code(bytes_addr)

        assert code1 == code2 == self.simple_code

        # Both should be cached
        stats = self.executor.get_cache_stats()
        assert stats["size"] == 2
        assert stats["misses"] == 2

        # Second access should hit cache
        code1_again = self.executor._get_contract_code(hex_addr)
        code2_again = self.executor._get_contract_code(bytes_addr)

        assert code1_again == code2_again == self.simple_code
        stats = self.executor.get_cache_stats()
        assert stats["hits"] == 2

    def test_cache_stats_hit_rate_calculation(self):
        """Test that hit rate is calculated correctly."""
        # No accesses yet
        stats = self.executor.get_cache_stats()
        assert stats["hit_rate"] == 0.0

        # One miss
        self.executor._get_contract_code(self.contract_address)
        stats = self.executor.get_cache_stats()
        assert stats["hit_rate"] == 0.0

        # One hit
        self.executor._get_contract_code(self.contract_address)
        stats = self.executor.get_cache_stats()
        assert stats["hit_rate"] == 0.5

        # More hits
        for _ in range(8):
            self.executor._get_contract_code(self.contract_address)

        stats = self.executor.get_cache_stats()
        assert stats["hit_rate"] == 0.9  # 9 hits out of 10 total

    def test_cache_eviction_preserves_hot_contracts(self):
        """Test that FIFO eviction strategy works correctly."""
        # Set small cache for testing
        self.executor._cache_max_size = 10

        # Add contracts sequentially
        addresses = [f"0x{i:040x}" for i in range(15)]
        for addr in addresses:
            self.blockchain.contracts[addr.upper()] = {
                "code": self.simple_code.hex(),
            }
            self.executor._get_contract_code(addr)

        # First 5 should be evicted (FIFO eviction removes first half)
        # Accessing first contract should be a miss
        initial_misses = self.executor.get_cache_stats()["misses"]
        self.executor._get_contract_code(addresses[0])
        assert self.executor.get_cache_stats()["misses"] == initial_misses + 1

        # Later contracts should still be cached (hit)
        initial_hits = self.executor.get_cache_stats()["hits"]
        self.executor._get_contract_code(addresses[14])
        assert self.executor.get_cache_stats()["hits"] == initial_hits + 1


class TestBytecodeCachingBenchmark:
    """Performance benchmarks for bytecode caching."""

    def test_benchmark_100_calls_to_cached_contract(self):
        """
        Benchmark: 100 calls to same contract should complete in <1ms total.

        This is the acceptance criterion from the TODO specification.
        """
        # Setup
        blockchain = MagicMock()
        code = bytes([Opcode.PUSH1, 0x42, Opcode.STOP])
        addr = "0x1111111111111111111111111111111111111111"
        blockchain.contracts = {
            addr.upper(): {
                "code": code.hex(),
            }
        }

        executor = EVMBytecodeExecutor(blockchain)

        # First call to populate cache
        executor._get_contract_code(addr)

        # Benchmark 100 cached calls
        start = time.perf_counter()
        for _ in range(100):
            result = executor._get_contract_code(addr)
        elapsed = time.perf_counter() - start

        # Should complete in under 1ms (0.001s)
        # This is a conservative target - actual performance is much better
        assert elapsed < 0.001, f"100 cached calls took {elapsed*1000:.3f}ms (target: <1ms)"

        # Verify all were cache hits
        stats = executor.get_cache_stats()
        assert stats["hits"] == 100

    def test_benchmark_hex_decode_overhead(self):
        """
        Benchmark: Verify hex decode overhead vs cached access.

        Demonstrates the performance benefit of caching.
        """
        # Create large contract (24KB - max size)
        large_code = bytes(range(256)) * 96  # 24KB
        addr = "0x2222222222222222222222222222222222222222"

        blockchain = MagicMock()
        blockchain.contracts = {
            addr.upper(): {
                "code": large_code.hex(),  # 48KB hex string
            }
        }

        executor = EVMBytecodeExecutor(blockchain)

        # Time uncached access (includes hex decode)
        executor.invalidate_contract_cache(addr)
        start = time.perf_counter()
        code1 = executor._get_contract_code(addr)
        uncached_time = time.perf_counter() - start

        # Time cached access (no hex decode)
        cached_times = []
        for _ in range(100):
            start = time.perf_counter()
            code2 = executor._get_contract_code(addr)
            cached_times.append(time.perf_counter() - start)

        avg_cached_time = sum(cached_times) / len(cached_times)

        # Print performance metrics (for informational purposes)
        print(f"\nBytecode Cache Performance:")
        print(f"  Uncached (with hex decode): {uncached_time*1000000:.2f}µs")
        print(f"  Cached (no hex decode):     {avg_cached_time*1000000:.2f}µs")
        print(f"  Speedup:                    {uncached_time/avg_cached_time:.1f}x")

        # Conservative assertion: cached should be at least 50x faster
        assert avg_cached_time < uncached_time / 50, (
            f"Cache not providing expected speedup: "
            f"{uncached_time/avg_cached_time:.1f}x (target: >50x)"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
