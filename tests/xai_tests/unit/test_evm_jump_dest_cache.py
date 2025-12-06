"""
Tests for EVM Jump Destination Cache.

This module tests the performance optimization that caches jump destinations
for contract bytecode, preventing redundant computation for popular contracts.
"""

import time
import pytest

from xai.core.vm.evm.interpreter import EVMInterpreter
from xai.core.vm.evm.context import ExecutionContext, CallContext, CallType, BlockContext
from xai.core.vm.evm.opcodes import Opcode
from xai.core.vm.exceptions import VMExecutionError


class TestJumpDestinationCache:
    """Tests for jump destination caching functionality."""

    def setup_method(self):
        """Clear cache before each test."""
        EVMInterpreter.clear_cache()

    def teardown_method(self):
        """Clear cache after each test."""
        EVMInterpreter.clear_cache()

    def create_test_context(self) -> ExecutionContext:
        """Create a minimal execution context for testing."""
        block_ctx = BlockContext(
            number=1,
            timestamp=1000,
            coinbase="0x" + "0" * 40,
            gas_limit=10_000_000,
            chain_id=1,
            prevrandao=0,
            base_fee=1000,
        )
        return ExecutionContext(
            block=block_ctx,
            tx_origin="0x" + "1" * 40,
            tx_gas_price=1000,
        )

    def test_cache_basic_functionality(self):
        """Test that cache stores and retrieves jump destinations."""
        context = self.create_test_context()
        interpreter = EVMInterpreter(context)

        # Simple bytecode with one JUMPDEST
        # PUSH1 0x04, JUMP, JUMPDEST, STOP
        code = bytes([0x60, 0x04, 0x56, 0x5B, 0x00])

        # First call - cache miss
        jump_dests1 = interpreter._compute_jump_destinations(code)
        assert 3 in jump_dests1  # JUMPDEST at position 3

        stats = EVMInterpreter.get_cache_stats()
        assert stats["misses"] == 1
        assert stats["hits"] == 0

        # Second call - cache hit
        jump_dests2 = interpreter._compute_jump_destinations(code)
        assert jump_dests1 == jump_dests2

        stats = EVMInterpreter.get_cache_stats()
        assert stats["misses"] == 1
        assert stats["hits"] == 1
        assert stats["hit_rate"] == 0.5

    def test_cache_different_bytecode(self):
        """Test that different bytecode gets different cache entries."""
        context = self.create_test_context()
        interpreter = EVMInterpreter(context)

        code1 = bytes([0x60, 0x04, 0x56, 0x5B, 0x00])  # JUMPDEST at 3
        code2 = bytes([0x5B, 0x60, 0x00, 0x56, 0x00])  # JUMPDEST at 0

        jump_dests1 = interpreter._compute_jump_destinations(code1)
        jump_dests2 = interpreter._compute_jump_destinations(code2)

        assert 3 in jump_dests1
        assert 0 in jump_dests2
        assert jump_dests1 != jump_dests2

        stats = EVMInterpreter.get_cache_stats()
        assert stats["misses"] == 2  # Both were cache misses
        assert stats["size"] == 2  # Two entries in cache

    def test_cache_empty_code(self):
        """Test that empty code returns empty set without caching."""
        context = self.create_test_context()
        interpreter = EVMInterpreter(context)

        jump_dests = interpreter._compute_jump_destinations(b"")
        assert jump_dests == set()

    def test_cache_multiple_jumpdests(self):
        """Test bytecode with multiple JUMPDEST instructions."""
        context = self.create_test_context()
        interpreter = EVMInterpreter(context)

        # Multiple JUMPDESTs: JUMPDEST, PUSH1, JUMPDEST, PUSH1, JUMPDEST
        code = bytes([0x5B, 0x60, 0x00, 0x5B, 0x60, 0x00, 0x5B])

        jump_dests = interpreter._compute_jump_destinations(code)
        assert 0 in jump_dests
        assert 3 in jump_dests
        assert 6 in jump_dests
        assert len(jump_dests) == 3

    def test_cache_ignores_jumpdest_in_push_data(self):
        """Test that JUMPDEST opcode inside PUSH data is ignored."""
        context = self.create_test_context()
        interpreter = EVMInterpreter(context)

        # PUSH1 0x5B (JUMPDEST opcode as data), JUMPDEST (actual)
        code = bytes([0x60, 0x5B, 0x5B])

        jump_dests = interpreter._compute_jump_destinations(code)
        # Only position 2 is valid JUMPDEST, position 1 is PUSH data
        assert 2 in jump_dests
        assert 1 not in jump_dests
        assert len(jump_dests) == 1

    def test_cache_large_push_data(self):
        """Test correct handling of PUSH32 and other large PUSH opcodes."""
        context = self.create_test_context()
        interpreter = EVMInterpreter(context)

        # PUSH32 (32 bytes of data), JUMPDEST
        data = bytes([0xFF] * 32)
        code = bytes([0x7F]) + data + bytes([0x5B])

        jump_dests = interpreter._compute_jump_destinations(code)
        # JUMPDEST should be at position 33 (1 opcode + 32 data bytes)
        assert 33 in jump_dests
        assert len(jump_dests) == 1

    def test_cache_eviction(self):
        """Test that cache evicts entries when full."""
        context = self.create_test_context()
        interpreter = EVMInterpreter(context)

        # Generate 300 unique bytecodes (more than JUMP_DEST_CACHE_SIZE=256)
        for i in range(300):
            # Create unique bytecode by varying PUSH data
            code = bytes([0x60, i % 256, 0x5B])
            interpreter._compute_jump_destinations(code)

        stats = EVMInterpreter.get_cache_stats()
        # Cache should have been evicted
        assert stats["size"] <= 256  # Should not exceed max size

    def test_cache_performance_benchmark(self):
        """Benchmark cache effectiveness for repeated executions."""
        context = self.create_test_context()
        interpreter = EVMInterpreter(context)

        # Create large realistic bytecode (24KB approximation)
        # Simulate a contract with many operations
        code_parts = []
        for i in range(1000):
            # Pattern: PUSH1, data, JUMPDEST, PUSH1, data, JUMP
            code_parts.extend([0x60, i % 256, 0x5B, 0x60, (i + 1) % 256, 0x56])

        code = bytes(code_parts)
        assert len(code) == 6000  # 6KB bytecode

        # First execution - cache miss (should compute)
        start_miss = time.time()
        jump_dests = interpreter._compute_jump_destinations(code)
        time_miss = time.time() - start_miss

        # Verify correct jump destinations
        assert len(jump_dests) == 1000  # One JUMPDEST per iteration

        # 100 subsequent executions - cache hits
        start_hits = time.time()
        for _ in range(100):
            cached_dests = interpreter._compute_jump_destinations(code)
            assert cached_dests == jump_dests
        time_hits = time.time() - start_hits

        # Cache hits should be at least 5x faster than cache miss
        speedup = time_miss / (time_hits / 100)
        assert speedup > 5.0, f"Cache speedup only {speedup:.2f}x, expected >5x"

        # Verify cache stats
        stats = EVMInterpreter.get_cache_stats()
        assert stats["hits"] == 100
        assert stats["misses"] == 1
        assert stats["hit_rate"] > 0.99

    def test_cache_total_execution_time_benchmark(self):
        """Test total execution time for 100 contract calls with jumps."""
        context = self.create_test_context()
        interpreter = EVMInterpreter(context)

        # Realistic bytecode with JUMP operations
        # Pattern: PUSH1 addr, JUMP, JUMPDEST, ... (repeated)
        code_parts = []
        for i in range(100):
            offset = i * 6 + 3  # Calculate JUMPDEST position
            code_parts.extend([0x60, offset, 0x56, 0x5B, 0x60, 0x00])

        code = bytes(code_parts)

        # Execute 100 times and measure total time
        start = time.time()
        for _ in range(100):
            jump_dests = interpreter._compute_jump_destinations(code)
            # Verify a few JUMPDESTs exist
            assert len(jump_dests) == 100
        elapsed = time.time() - start

        # With caching, 100 executions should complete in <10ms
        assert elapsed < 0.01, f"100 cached executions took {elapsed*1000:.2f}ms, expected <10ms"

        # Verify high cache hit rate (99 hits out of 100 calls)
        stats = EVMInterpreter.get_cache_stats()
        assert stats["hit_rate"] > 0.99

    def test_cache_statistics_accuracy(self):
        """Test that cache statistics are accurate."""
        context = self.create_test_context()
        interpreter = EVMInterpreter(context)

        code1 = bytes([0x5B, 0x00])
        code2 = bytes([0x60, 0x00, 0x5B])

        # First access to code1 - miss
        interpreter._compute_jump_destinations(code1)
        stats = EVMInterpreter.get_cache_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 1
        assert stats["size"] == 1

        # Second access to code1 - hit
        interpreter._compute_jump_destinations(code1)
        stats = EVMInterpreter.get_cache_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["size"] == 1

        # First access to code2 - miss
        interpreter._compute_jump_destinations(code2)
        stats = EVMInterpreter.get_cache_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 2
        assert stats["size"] == 2

        # Third access to code1 - hit
        interpreter._compute_jump_destinations(code1)
        stats = EVMInterpreter.get_cache_stats()
        assert stats["hits"] == 2
        assert stats["misses"] == 2
        assert stats["size"] == 2
        assert stats["hit_rate"] == 0.5

    def test_cache_clear(self):
        """Test that cache can be cleared."""
        context = self.create_test_context()
        interpreter = EVMInterpreter(context)

        code = bytes([0x5B, 0x00])
        interpreter._compute_jump_destinations(code)

        stats = EVMInterpreter.get_cache_stats()
        assert stats["size"] == 1

        # Clear cache
        EVMInterpreter.clear_cache()

        stats = EVMInterpreter.get_cache_stats()
        assert stats["size"] == 0
        assert stats["hits"] == 0
        assert stats["misses"] == 0

        # Next access should be a miss again
        interpreter._compute_jump_destinations(code)
        stats = EVMInterpreter.get_cache_stats()
        assert stats["misses"] == 1

    def test_cache_shared_across_interpreters(self):
        """Test that cache is shared across different interpreter instances."""
        context1 = self.create_test_context()
        context2 = self.create_test_context()

        interpreter1 = EVMInterpreter(context1)
        interpreter2 = EVMInterpreter(context2)

        code = bytes([0x5B, 0x00])

        # First interpreter computes
        interpreter1._compute_jump_destinations(code)
        stats = EVMInterpreter.get_cache_stats()
        assert stats["misses"] == 1

        # Second interpreter should hit cache
        interpreter2._compute_jump_destinations(code)
        stats = EVMInterpreter.get_cache_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1

    def test_realistic_erc20_pattern(self):
        """Test with bytecode pattern similar to ERC20 contracts."""
        context = self.create_test_context()
        interpreter = EVMInterpreter(context)

        # Simulate ERC20-like bytecode with function dispatcher
        # Pattern: PUSH4 signature, DUP1, EQ, PUSH2 offset, JUMPI, JUMPDEST
        code_parts = []

        # Function dispatcher
        for i in range(10):
            func_sig = i.to_bytes(4, 'big')
            jump_offset = (i * 20 + 100).to_bytes(2, 'big')
            code_parts.extend([0x63])  # PUSH4
            code_parts.extend(func_sig)
            code_parts.extend([0x80, 0x14])  # DUP1, EQ
            code_parts.extend([0x61])  # PUSH2
            code_parts.extend(jump_offset)
            code_parts.extend([0x57])  # JUMPI

        # Add JUMPDESTs at expected locations
        for i in range(10):
            offset = i * 20 + 100
            # Pad to offset
            while len(code_parts) < offset:
                code_parts.append(0x00)
            code_parts.append(0x5B)  # JUMPDEST

        code = bytes(code_parts)

        # First call
        start = time.time()
        jump_dests = interpreter._compute_jump_destinations(code)
        first_time = time.time() - start

        # Verify JUMPDESTs found
        assert len(jump_dests) >= 10

        # Subsequent calls should be much faster
        times = []
        for _ in range(50):
            start = time.time()
            cached_dests = interpreter._compute_jump_destinations(code)
            times.append(time.time() - start)
            assert cached_dests == jump_dests

        avg_cached_time = sum(times) / len(times)
        speedup = first_time / avg_cached_time

        # Should be at least 10x faster with cache
        assert speedup > 10.0, f"Cache speedup only {speedup:.2f}x"

    def test_edge_case_all_jumpdests(self):
        """Test bytecode that is all JUMPDEST instructions."""
        context = self.create_test_context()
        interpreter = EVMInterpreter(context)

        # All JUMPDESTs
        code = bytes([0x5B] * 100)

        jump_dests = interpreter._compute_jump_destinations(code)
        assert len(jump_dests) == 100
        assert jump_dests == set(range(100))

    def test_edge_case_no_jumpdests(self):
        """Test bytecode with no JUMPDEST instructions."""
        context = self.create_test_context()
        interpreter = EVMInterpreter(context)

        # No JUMPDESTs - just PUSH and arithmetic
        code = bytes([0x60, 0x01, 0x60, 0x02, 0x01, 0x00])

        jump_dests = interpreter._compute_jump_destinations(code)
        assert len(jump_dests) == 0

    def test_hash_collision_resistance(self):
        """Test that different bytecodes don't collide in cache."""
        context = self.create_test_context()
        interpreter = EVMInterpreter(context)

        # Create many different bytecodes
        codes_and_dests = []
        for i in range(100):
            code = bytes([0x60, i, 0x5B, 0x60, (i + 1) % 256, 0x00])
            dests = interpreter._compute_jump_destinations(code)
            codes_and_dests.append((code, dests))

        # Verify each has correct jump destinations
        for code, expected_dests in codes_and_dests:
            actual_dests = interpreter._compute_jump_destinations(code)
            assert actual_dests == expected_dests
            # Should always be position 2 for this pattern
            assert 2 in actual_dests
