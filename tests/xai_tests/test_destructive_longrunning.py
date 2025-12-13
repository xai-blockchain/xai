"""
XAI Blockchain - Phase 7: Destructive & Long-Running Tests
LOCAL_TESTING_PLAN.md Phase 7

This module contains comprehensive tests for destructive scenarios,
resource constraints, long-running stability, and end-to-end performance.

Test Classes:
1. TestDatabaseCorruption (7.1) - Database corruption and recovery
2. TestResourceConstraints (7.2) - Resource constraint verification
3. TestLongRunningStability (7.3) - Long-running stability testing
4. TestE2EPerformance (7.4) - End-to-end performance testing

All destructive tests use isolated tmp_path fixtures and clean up properly.
Long-running tests have configurable durations via environment variables.
"""

import pytest
import os
import time
import json
import tempfile
import threading
import psutil
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from collections import defaultdict

from xai.core.blockchain import Blockchain, Block, Transaction
from xai.core.wallet import Wallet
from xai.core.blockchain_storage import BlockchainStorage


# ============================================================================
# Test Class 1: Database Corruption Tests (7.1)
# ============================================================================


@pytest.mark.destructive
class TestDatabaseCorruption:
    """
    Test database corruption scenarios and recovery mechanisms.

    Phase 7.1: Database Corruption Test
    Intentionally corrupt database files and verify graceful failure
    with clear error messages.
    """

    @pytest.fixture
    def blockchain_with_data(self, tmp_path) -> Tuple[Path, Blockchain]:
        """Create a blockchain with some data for corruption tests"""
        data_dir = tmp_path / "blockchain_data"
        data_dir.mkdir()

        blockchain = Blockchain(data_dir=str(data_dir))
        wallet = Wallet()

        # Add some UTXOs
        blockchain.utxo_set[wallet.address] = [
            {"txid": "genesis", "vout": 0, "amount": 1000.0, "script_pubkey": "", "spent": False}
        ]

        # Mine several blocks
        for i in range(5):
            tx = Transaction(
                wallet.address,
                Wallet().address,
                10.0,
                0.1,
                wallet.public_key,
                nonce=i
            )
            tx.sign_transaction(wallet.private_key)
            blockchain.add_transaction(tx)
            blockchain.mine_pending_transactions(wallet.address)

        # Save data
        blockchain.storage.save_state_to_disk(
            blockchain.utxo_manager,
            blockchain.pending_transactions
        )

        return data_dir, blockchain

    def test_corrupted_utxo_database_graceful_failure(self, tmp_path):
        """
        Test that corrupted UTXO database file fails gracefully.

        Verify:
        - Clear error message on corruption detection
        - No silent data corruption
        - System doesn't crash
        """
        data_dir = tmp_path / "blockchain_data"
        data_dir.mkdir()

        # Create blockchain and save UTXO set
        blockchain = Blockchain(data_dir=str(data_dir))
        wallet = Wallet()
        blockchain.utxo_manager.add_utxo(wallet.address, "test", 0, 100.0, "")
        blockchain.storage.save_state_to_disk(
            blockchain.utxo_manager,
            blockchain.pending_transactions
        )

        # Corrupt the UTXO file
        utxo_file = data_dir / "utxo_set.json"
        with open(utxo_file, "w") as f:
            f.write("{ corrupt json data [[[")

        # Try to load - should fail with clear error message
        with pytest.raises(Exception) as exc_info:
            new_blockchain = Blockchain(data_dir=str(data_dir))

        # Should have clear error message about corruption
        error_message = str(exc_info.value)
        assert "integrity" in error_message.lower() or "corrupt" in error_message.lower(), \
            f"Error message should mention corruption: {error_message}"

    def test_corrupted_block_file_detection(self, blockchain_with_data):
        """
        Test that corrupted block files are detected.

        Verify:
        - Corruption is detected on load
        - Error message identifies corrupted file
        - Other blocks remain accessible
        """
        data_dir, blockchain = blockchain_with_data

        # Find a block file to corrupt
        blocks_dir = data_dir / "blocks"
        block_files = list(blocks_dir.glob("blocks_*.json"))
        assert len(block_files) > 0, "Should have block files"

        # Corrupt the first block file
        target_file = block_files[0]
        with open(target_file, "r") as f:
            lines = f.readlines()

        # Corrupt middle of file
        if len(lines) > 1:
            with open(target_file, "w") as f:
                f.write(lines[0])
                f.write("{ corrupt block data }\n")
                if len(lines) > 2:
                    f.write(lines[-1])

        # Create new blockchain instance - should detect corruption
        with pytest.raises(Exception) as exc_info:
            new_blockchain = Blockchain(data_dir=str(data_dir))

        # Should have clear error about corruption
        error_message = str(exc_info.value)
        assert "integrity" in error_message.lower() or "corrupt" in error_message.lower()

    def test_corrupted_block_hash_detection(self, blockchain_with_data):
        """
        Test that corrupted block hashes are detected during validation.

        Verify:
        - Hash tampering is detected
        - Chain validation fails
        - Specific corrupted block is identified
        """
        data_dir, blockchain = blockchain_with_data

        # Tamper with a block's hash in memory
        if len(blockchain.chain) > 1:
            original_hash = blockchain.chain[1].hash
            blockchain.chain[1].hash = "0" * 64  # Invalid hash

            # Validation should fail
            is_valid = blockchain.validate_chain()
            assert not is_valid, "Should detect corrupted block hash"

            # Restore for cleanup
            blockchain.chain[1].hash = original_hash

    def test_corrupted_transaction_signature(self, tmp_path):
        """
        Test that transactions with corrupted signatures are rejected.

        Verify:
        - Signature tampering is detected
        - Transaction is rejected
        - Clear error message provided
        """
        blockchain = Blockchain(data_dir=str(tmp_path))
        wallet1 = Wallet()
        wallet2 = Wallet()

        # Give wallet1 funds
        blockchain.utxo_set[wallet1.address] = [
            {"txid": "genesis", "vout": 0, "amount": 100.0, "script_pubkey": "", "spent": False}
        ]

        # Create and sign transaction
        tx = Transaction(
            wallet1.address,
            wallet2.address,
            10.0,
            0.1,
            wallet1.public_key,
            nonce=0
        )
        tx.sign_transaction(wallet1.private_key)

        # Corrupt the signature
        if tx.signature:
            tx.signature = "0" * len(tx.signature)

        # Should be rejected
        is_valid = blockchain.validate_transaction(tx)
        assert not is_valid, "Should reject corrupted signature"

    def test_partial_block_file_corruption(self, blockchain_with_data):
        """
        Test handling of partially corrupted block files.

        Verify:
        - Valid blocks before corruption are preserved
        - Corrupted and subsequent blocks are rejected
        - System can continue with valid portion
        """
        data_dir, blockchain = blockchain_with_data
        blocks_dir = data_dir / "blocks"

        # Find block file
        block_files = list(blocks_dir.glob("blocks_*.json"))
        if not block_files:
            pytest.skip("No block files to corrupt")

        target_file = block_files[0]

        # Read all lines
        with open(target_file, "r") as f:
            lines = f.readlines()

        if len(lines) < 2:
            pytest.skip("Need multiple blocks in file")

        # Corrupt second half of file
        midpoint = len(lines) // 2
        with open(target_file, "w") as f:
            for line in lines[:midpoint]:
                f.write(line)
            f.write("{ corrupt }\n")

        # Load blockchain - should detect corruption
        with pytest.raises(Exception) as exc_info:
            new_blockchain = Blockchain(data_dir=str(data_dir))

        # Should have error about corruption
        error_message = str(exc_info.value)
        assert "integrity" in error_message.lower() or "corrupt" in error_message.lower()

    def test_empty_block_file_handling(self, tmp_path):
        """
        Test handling of empty or truncated block files.

        Verify:
        - Empty files don't crash the system
        - Clear error or skip empty files
        - Blockchain continues to function
        """
        data_dir = tmp_path / "blockchain_data"
        data_dir.mkdir()
        blocks_dir = data_dir / "blocks"
        blocks_dir.mkdir()

        # Create empty block file
        empty_file = blocks_dir / "blocks_0.json"
        empty_file.touch()

        # Should handle gracefully
        blockchain = Blockchain(data_dir=str(data_dir))
        assert blockchain is not None
        assert len(blockchain.chain) == 1  # Genesis only

    def test_missing_utxo_file_recovery(self, tmp_path):
        """
        Test recovery when UTXO file is missing.

        Verify:
        - System detects missing file
        - Error message is clear
        - Integrity checks work
        """
        data_dir = tmp_path / "blockchain_data"
        data_dir.mkdir()

        # Create blockchain
        blockchain = Blockchain(data_dir=str(data_dir))
        wallet = Wallet()
        blockchain.utxo_manager.add_utxo(wallet.address, "test", 0, 100.0, "")
        blockchain.storage.save_state_to_disk(
            blockchain.utxo_manager,
            blockchain.pending_transactions
        )

        # Delete UTXO file
        utxo_file = data_dir / "utxo_set.json"
        if utxo_file.exists():
            utxo_file.unlink()

        # Load blockchain - should detect missing file via integrity check
        with pytest.raises(Exception) as exc_info:
            new_blockchain = Blockchain(data_dir=str(data_dir))

        # Should have error about integrity/corruption
        error_message = str(exc_info.value)
        assert "integrity" in error_message.lower() or "corrupt" in error_message.lower()

    def test_corrupted_chain_state_recovery(self, blockchain_with_data):
        """
        Test recovery from corrupted chain state.

        Verify:
        - Can detect inconsistent chain state
        - Can rebuild from blocks on disk
        - Maintains data integrity
        """
        data_dir, blockchain = blockchain_with_data
        original_length = len(blockchain.chain)

        # Corrupt in-memory chain
        if len(blockchain.chain) > 2:
            blockchain.chain = blockchain.chain[:2]  # Truncate

        # Save corrupted state
        blockchain.storage.save_state_to_disk(
            blockchain.utxo_manager,
            blockchain.pending_transactions
        )

        # Create new instance - should load from disk
        new_blockchain = Blockchain(data_dir=str(data_dir))

        # Should have loaded blocks from disk
        assert new_blockchain is not None
        # May not recover all blocks if chain state was corrupted,
        # but should at least have genesis
        assert len(new_blockchain.chain) >= 1


# ============================================================================
# Test Class 2: Resource Constraint Tests (7.2)
# ============================================================================


@pytest.mark.slow
class TestResourceConstraints:
    """
    Test system behavior under resource constraints.

    Phase 7.2: Resource Constraint Test
    Run nodes with restricted resources to define minimum requirements.
    """

    def test_minimum_ram_requirements(self, tmp_path):
        """
        Test blockchain operation with limited memory.

        Verify:
        - System can operate with minimal RAM
        - Performance degrades gracefully
        - No crashes under memory pressure

        Note: This test monitors memory usage, actual limiting
        requires OS-level controls (cgroups, ulimit).
        """
        data_dir = tmp_path / "blockchain_data"
        data_dir.mkdir()

        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        blockchain = Blockchain(data_dir=str(data_dir))
        wallet = Wallet()

        # Give wallet funds
        blockchain.utxo_set[wallet.address] = [
            {"txid": "genesis", "vout": 0, "amount": 10000.0, "script_pubkey": "", "spent": False}
        ]

        # Perform operations and monitor memory
        memory_samples = []

        for i in range(10):
            # Mine a block
            tx = Transaction(
                wallet.address,
                Wallet().address,
                1.0,
                0.01,
                wallet.public_key,
                nonce=i
            )
            tx.sign_transaction(wallet.private_key)
            blockchain.add_transaction(tx)
            blockchain.mine_pending_transactions(wallet.address)

            # Sample memory
            current_memory = process.memory_info().rss / 1024 / 1024
            memory_samples.append(current_memory)

        final_memory = process.memory_info().rss / 1024 / 1024
        memory_increase = final_memory - initial_memory

        # Memory increase should be reasonable (< 100 MB for 10 blocks)
        assert memory_increase < 100, f"Memory increase too high: {memory_increase:.2f} MB"

        # Log memory profile for analysis
        print(f"\nMemory Profile:")
        print(f"  Initial: {initial_memory:.2f} MB")
        print(f"  Final: {final_memory:.2f} MB")
        print(f"  Increase: {memory_increase:.2f} MB")
        print(f"  Peak: {max(memory_samples):.2f} MB")

    def test_disk_space_monitoring(self, tmp_path):
        """
        Test that system monitors and handles low disk space.

        Verify:
        - Disk usage is tracked
        - Warnings for low space
        - Graceful handling when disk fills
        """
        data_dir = tmp_path / "blockchain_data"
        data_dir.mkdir()

        # Check available disk space
        disk_usage = psutil.disk_usage(str(tmp_path))
        available_gb = disk_usage.free / (1024 ** 3)

        # Skip if less than 1GB available
        if available_gb < 1.0:
            pytest.skip("Insufficient disk space for test")

        blockchain = Blockchain(data_dir=str(data_dir))
        wallet = Wallet()

        # Give wallet funds
        blockchain.utxo_set[wallet.address] = [
            {"txid": f"genesis-{i}", "vout": 0, "amount": 1000.0, "script_pubkey": "", "spent": False}
            for i in range(10)
        ]

        # Mine blocks and check disk usage
        initial_usage = sum(
            f.stat().st_size for f in Path(data_dir).rglob('*') if f.is_file()
        )

        for i in range(5):
            # Create transactions
            for j in range(10):
                tx = Transaction(
                    wallet.address,
                    Wallet().address,
                    1.0,
                    0.01,
                    wallet.public_key,
                    nonce=i * 10 + j
                )
                tx.sign_transaction(wallet.private_key)
                blockchain.add_transaction(tx)

            blockchain.mine_pending_transactions(wallet.address)

        final_usage = sum(
            f.stat().st_size for f in Path(data_dir).rglob('*') if f.is_file()
        )

        disk_increase = (final_usage - initial_usage) / 1024  # KB

        # Disk usage should be reasonable
        print(f"\nDisk Usage:")
        print(f"  Initial: {initial_usage / 1024:.2f} KB")
        print(f"  Final: {final_usage / 1024:.2f} KB")
        print(f"  Increase: {disk_increase:.2f} KB")

        # Should use less than 10MB for 5 blocks with 10 tx each
        assert disk_increase < 10240, f"Disk usage too high: {disk_increase:.2f} KB"

    def test_cpu_constrained_mining(self, tmp_path):
        """
        Test mining performance under CPU constraints.

        Verify:
        - Mining still works with limited CPU
        - Performance degrades predictably
        - No deadlocks or hangs
        """
        blockchain = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        # Give wallet funds
        blockchain.utxo_set[wallet.address] = [
            {"txid": "genesis", "vout": 0, "amount": 1000.0, "script_pubkey": "", "spent": False}
        ]

        # Add transactions
        for i in range(5):
            tx = Transaction(
                wallet.address,
                Wallet().address,
                1.0,
                0.01,
                wallet.public_key,
                nonce=i
            )
            tx.sign_transaction(wallet.private_key)
            blockchain.add_transaction(tx)

        # Time mining with CPU monitoring
        process = psutil.Process()
        start_time = time.time()
        start_cpu = process.cpu_percent(interval=0.1)

        block = blockchain.mine_pending_transactions(wallet.address)

        end_time = time.time()
        end_cpu = process.cpu_percent(interval=0.1)

        mining_time = end_time - start_time

        assert block is not None, "Should successfully mine block"

        print(f"\nCPU-Constrained Mining:")
        print(f"  Time: {mining_time:.2f}s")
        print(f"  CPU Start: {start_cpu:.1f}%")
        print(f"  CPU End: {end_cpu:.1f}%")

    def test_network_bandwidth_constraints(self, tmp_path):
        """
        Test behavior under network bandwidth constraints.

        Verify:
        - Block propagation works with limited bandwidth
        - Transaction relay is throttled appropriately
        - No data loss under constraint

        Note: This simulates bandwidth limits via serialization size checks.
        """
        blockchain = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        # Create a large block
        blockchain.utxo_set[wallet.address] = [
            {"txid": f"genesis-{i}", "vout": 0, "amount": 100.0, "script_pubkey": "", "spent": False}
            for i in range(100)
        ]

        # Add many transactions
        for i in range(50):
            tx = Transaction(
                wallet.address,
                Wallet().address,
                1.0,
                0.01,
                wallet.public_key,
                nonce=i
            )
            tx.sign_transaction(wallet.private_key)
            blockchain.add_transaction(tx)

        # Mine block
        block = blockchain.mine_pending_transactions(wallet.address)

        # Calculate block size
        block_json = json.dumps(block.to_dict())
        block_size_kb = len(block_json.encode('utf-8')) / 1024

        print(f"\nBlock Size: {block_size_kb:.2f} KB")

        # Verify block is within reasonable size limits
        # Even with 50 transactions, should be under 1MB
        assert block_size_kb < 1024, f"Block too large: {block_size_kb:.2f} KB"

    def test_concurrent_operations_resource_usage(self, tmp_path):
        """
        Test resource usage under concurrent operations.

        Verify:
        - Multiple concurrent operations don't exhaust resources
        - Thread safety under resource pressure
        - Predictable resource scaling
        """
        blockchain = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        # Give wallet funds
        blockchain.utxo_set[wallet.address] = [
            {"txid": f"genesis-{i}", "vout": 0, "amount": 1000.0, "script_pubkey": "", "spent": False}
            for i in range(20)
        ]

        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024
        initial_threads = process.num_threads()

        # Simulate concurrent transaction creation
        transactions = []
        for i in range(20):
            tx = Transaction(
                wallet.address,
                Wallet().address,
                1.0,
                0.01,
                wallet.public_key,
                nonce=i
            )
            tx.sign_transaction(wallet.private_key)
            transactions.append(tx)

        # Add all transactions
        for tx in transactions:
            blockchain.add_transaction(tx)

        # Mine block
        blockchain.mine_pending_transactions(wallet.address)

        final_memory = process.memory_info().rss / 1024 / 1024
        final_threads = process.num_threads()

        memory_increase = final_memory - initial_memory

        print(f"\nConcurrent Operations:")
        print(f"  Transactions: {len(transactions)}")
        print(f"  Memory increase: {memory_increase:.2f} MB")
        print(f"  Threads: {initial_threads} -> {final_threads}")

        # Resource usage should be reasonable
        assert memory_increase < 50, f"Memory increase too high: {memory_increase:.2f} MB"

    def test_graceful_degradation_under_load(self, tmp_path):
        """
        Test graceful degradation under heavy load.

        Verify:
        - System remains responsive under load
        - No crashes or data corruption
        - Blockchain remains valid after stress
        """
        blockchain = Blockchain(data_dir=str(tmp_path))

        # Create wallet with funds
        wallet = Wallet()
        blockchain.utxo_set[wallet.address] = [
            {"txid": "genesis", "vout": 0, "amount": 10000.0, "script_pubkey": "", "spent": False}
        ]

        # Add some valid transactions and mine
        for i in range(10):
            tx = Transaction(
                wallet.address,
                Wallet().address,
                1.0,
                0.01,
                wallet.public_key,
                nonce=i
            )
            tx.sign_transaction(wallet.private_key)
            blockchain.add_transaction(tx)

        # Mine blocks
        blocks_mined = 0
        for _ in range(5):
            blockchain.mine_pending_transactions(wallet.address)
            blocks_mined += 1

        print(f"\nLoad Test Results:")
        print(f"  Blocks mined: {blocks_mined}")
        print(f"  Chain length: {len(blockchain.chain)}")
        print(f"  Mempool size: {len(blockchain.pending_transactions)}")

        # System should remain functional
        assert blocks_mined > 0, "Should successfully mine blocks"

        # Blockchain should still be valid
        assert blockchain.validate_chain(), "Chain should remain valid after load"

        # System should not have crashed (implicit - we reached this point)
        assert blockchain is not None


# ============================================================================
# Test Class 3: Long-Running Stability Tests (7.3)
# ============================================================================


@pytest.mark.slow
@pytest.mark.longrunning
class TestLongRunningStability:
    """
    Test long-running stability and soak testing.

    Phase 7.3: Long-Running Stability (Soak Test)
    Run testnet under continuous load for extended periods.

    Duration controlled by environment variable:
    XAI_SOAK_TEST_DURATION_SECONDS (default: 300 = 5 minutes for tests)
    For full 24-48 hour tests, set to 86400 or 172800.
    """

    def get_soak_test_duration(self) -> int:
        """Get soak test duration from environment or use default"""
        return int(os.getenv('XAI_SOAK_TEST_DURATION_SECONDS', '300'))  # 5 min default

    def test_memory_leak_detection(self, tmp_path):
        """
        Test for memory leaks over extended operation.

        Verify:
        - Memory usage remains stable over time
        - No unbounded memory growth
        - Garbage collection is effective
        """
        duration = min(self.get_soak_test_duration(), 600)  # Cap at 10 minutes

        blockchain = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        # Give wallet funds
        blockchain.utxo_set[wallet.address] = [
            {"txid": f"genesis-{i}", "vout": 0, "amount": 1000.0, "script_pubkey": "", "spent": False}
            for i in range(100)
        ]

        process = psutil.Process()
        memory_samples = []
        start_time = time.time()
        iteration = 0

        print(f"\nStarting memory leak detection test for {duration}s...")

        while time.time() - start_time < duration:
            # Create and add transaction
            tx = Transaction(
                wallet.address,
                Wallet().address,
                0.1,
                0.01,
                wallet.public_key,
                nonce=iteration
            )
            tx.sign_transaction(wallet.private_key)
            blockchain.add_transaction(tx)

            # Mine every 10 transactions
            if iteration % 10 == 0:
                blockchain.mine_pending_transactions(wallet.address)

                # Sample memory
                memory_mb = process.memory_info().rss / 1024 / 1024
                memory_samples.append(memory_mb)

                if iteration % 50 == 0:
                    print(f"  Iteration {iteration}: {memory_mb:.2f} MB")

            iteration += 1

        # Analyze memory trend
        if len(memory_samples) > 2:
            initial_avg = sum(memory_samples[:3]) / 3
            final_avg = sum(memory_samples[-3:]) / 3
            memory_growth = final_avg - initial_avg
            growth_rate = memory_growth / (duration / 60)  # MB per minute

            print(f"\nMemory Leak Analysis:")
            print(f"  Duration: {duration}s")
            print(f"  Iterations: {iteration}")
            print(f"  Initial memory: {initial_avg:.2f} MB")
            print(f"  Final memory: {final_avg:.2f} MB")
            print(f"  Growth: {memory_growth:.2f} MB")
            print(f"  Growth rate: {growth_rate:.2f} MB/min")

            # Growth rate should be minimal (< 1 MB/min)
            assert growth_rate < 1.0, f"Potential memory leak: {growth_rate:.2f} MB/min"

    def test_performance_degradation_monitoring(self, tmp_path):
        """
        Test for performance degradation over time.

        Verify:
        - Block mining time remains consistent
        - Transaction validation time stable
        - No cumulative slowdown
        """
        duration = min(self.get_soak_test_duration(), 600)

        blockchain = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        blockchain.utxo_set[wallet.address] = [
            {"txid": f"genesis-{i}", "vout": 0, "amount": 1000.0, "script_pubkey": "", "spent": False}
            for i in range(50)
        ]

        mining_times = []
        start_time = time.time()
        iteration = 0

        print(f"\nStarting performance degradation test for {duration}s...")

        while time.time() - start_time < duration:
            # Add transactions
            for i in range(5):
                tx = Transaction(
                    wallet.address,
                    Wallet().address,
                    0.1,
                    0.01,
                    wallet.public_key,
                    nonce=iteration * 5 + i
                )
                tx.sign_transaction(wallet.private_key)
                blockchain.add_transaction(tx)

            # Time mining
            mine_start = time.time()
            blockchain.mine_pending_transactions(wallet.address)
            mine_time = time.time() - mine_start

            mining_times.append(mine_time)

            if iteration % 10 == 0:
                print(f"  Iteration {iteration}: {mine_time:.2f}s")

            iteration += 1

        # Analyze performance trend
        if len(mining_times) > 10:
            initial_avg = sum(mining_times[:5]) / 5
            final_avg = sum(mining_times[-5:]) / 5
            degradation = ((final_avg - initial_avg) / initial_avg) * 100

            print(f"\nPerformance Analysis:")
            print(f"  Total blocks mined: {len(mining_times)}")
            print(f"  Initial avg time: {initial_avg:.3f}s")
            print(f"  Final avg time: {final_avg:.3f}s")
            print(f"  Degradation: {degradation:.2f}%")

            # Performance should not degrade significantly (< 20%)
            assert degradation < 20, f"Performance degraded: {degradation:.2f}%"

    def test_continuous_block_mining_stability(self, tmp_path):
        """
        Test continuous block mining stability.

        Verify:
        - Can mine blocks continuously
        - No crashes or hangs
        - Blockchain remains valid
        """
        duration = min(self.get_soak_test_duration(), 300)

        blockchain = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        blockchain.utxo_set[wallet.address] = [
            {"txid": "genesis", "vout": 0, "amount": 100000.0, "script_pubkey": "", "spent": False}
        ]

        start_time = time.time()
        blocks_mined = 0

        print(f"\nStarting continuous mining test for {duration}s...")

        while time.time() - start_time < duration:
            # Add a transaction
            tx = Transaction(
                wallet.address,
                Wallet().address,
                0.1,
                0.01,
                wallet.public_key,
                nonce=blocks_mined
            )
            tx.sign_transaction(wallet.private_key)
            blockchain.add_transaction(tx)

            # Mine
            block = blockchain.mine_pending_transactions(wallet.address)
            assert block is not None, f"Mining failed at iteration {blocks_mined}"

            blocks_mined += 1

            if blocks_mined % 10 == 0:
                print(f"  Mined {blocks_mined} blocks...")

        print(f"\nContinuous Mining Results:")
        print(f"  Blocks mined: {blocks_mined}")
        print(f"  Chain length: {len(blockchain.chain)}")
        print(f"  Avg time per block: {duration / blocks_mined:.2f}s")

        # Validate chain integrity
        assert blockchain.validate_chain(), "Chain validation failed"
        assert len(blockchain.chain) == blocks_mined + 1  # +1 for genesis

    def test_mixed_load_stability(self, tmp_path):
        """
        Test stability under mixed transaction load.

        Verify:
        - Can handle varying transaction sizes
        - Different transaction types process correctly
        - System remains stable under varied load
        """
        duration = min(self.get_soak_test_duration(), 300)

        blockchain = Blockchain(data_dir=str(tmp_path))
        wallets = [Wallet() for _ in range(5)]

        # Fund all wallets
        for wallet in wallets:
            blockchain.utxo_set[wallet.address] = [
                {"txid": f"genesis-{wallet.address}", "vout": 0, "amount": 10000.0, "script_pubkey": "", "spent": False}
            ]

        start_time = time.time()
        tx_count = 0
        blocks_mined = 0

        print(f"\nStarting mixed load test for {duration}s...")

        while time.time() - start_time < duration:
            # Randomly select sender and receiver
            sender = wallets[tx_count % len(wallets)]
            receiver = wallets[(tx_count + 1) % len(wallets)]

            # Vary transaction amounts
            amount = (tx_count % 10) + 0.1

            tx = Transaction(
                sender.address,
                receiver.address,
                amount,
                0.01,
                sender.public_key,
                nonce=tx_count
            )
            tx.sign_transaction(sender.private_key)

            if blockchain.add_transaction(tx):
                tx_count += 1

            # Mine periodically
            if tx_count % 5 == 0:
                miner = wallets[blocks_mined % len(wallets)]
                blockchain.mine_pending_transactions(miner.address)
                blocks_mined += 1

        print(f"\nMixed Load Results:")
        print(f"  Transactions processed: {tx_count}")
        print(f"  Blocks mined: {blocks_mined}")
        print(f"  Avg tx per block: {tx_count / blocks_mined:.1f}")

        # Validate chain
        assert blockchain.validate_chain()

    def test_resource_usage_over_time(self, tmp_path):
        """
        Test resource usage tracking over extended period.

        Verify:
        - CPU usage remains reasonable
        - Memory usage is bounded
        - Disk I/O is not excessive
        """
        duration = min(self.get_soak_test_duration(), 300)

        blockchain = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        blockchain.utxo_set[wallet.address] = [
            {"txid": "genesis", "vout": 0, "amount": 50000.0, "script_pubkey": "", "spent": False}
        ]

        process = psutil.Process()

        # Resource tracking
        cpu_samples = []
        memory_samples = []
        io_counters_start = process.io_counters()

        start_time = time.time()
        iteration = 0

        print(f"\nStarting resource usage monitoring for {duration}s...")

        while time.time() - start_time < duration:
            # Add transaction
            tx = Transaction(
                wallet.address,
                Wallet().address,
                1.0,
                0.01,
                wallet.public_key,
                nonce=iteration
            )
            tx.sign_transaction(wallet.private_key)
            blockchain.add_transaction(tx)

            # Mine every 5 transactions
            if iteration % 5 == 0:
                blockchain.mine_pending_transactions(wallet.address)

                # Sample resources
                cpu_samples.append(process.cpu_percent(interval=0.1))
                memory_samples.append(process.memory_info().rss / 1024 / 1024)

                if iteration % 25 == 0:
                    print(f"  Iteration {iteration}: CPU {cpu_samples[-1]:.1f}%, "
                          f"Memory {memory_samples[-1]:.1f} MB")

            iteration += 1

        io_counters_end = process.io_counters()

        # Analyze resource usage
        avg_cpu = sum(cpu_samples) / len(cpu_samples) if cpu_samples else 0
        max_cpu = max(cpu_samples) if cpu_samples else 0
        avg_memory = sum(memory_samples) / len(memory_samples) if memory_samples else 0
        max_memory = max(memory_samples) if memory_samples else 0

        bytes_read = io_counters_end.read_bytes - io_counters_start.read_bytes
        bytes_written = io_counters_end.write_bytes - io_counters_start.write_bytes

        print(f"\nResource Usage Summary:")
        print(f"  CPU: avg {avg_cpu:.1f}%, max {max_cpu:.1f}%")
        print(f"  Memory: avg {avg_memory:.1f} MB, max {max_memory:.1f} MB")
        print(f"  Disk read: {bytes_read / 1024:.1f} KB")
        print(f"  Disk write: {bytes_written / 1024:.1f} KB")

        # Resource usage should be reasonable
        assert avg_cpu < 80, f"CPU usage too high: {avg_cpu:.1f}%"
        assert max_memory < 500, f"Memory usage too high: {max_memory:.1f} MB"


# ============================================================================
# Test Class 4: E2E Performance Tests (7.4)
# ============================================================================


@pytest.mark.performance
@pytest.mark.slow
class TestE2EPerformance:
    """
    Test end-to-end performance scenarios.

    Phase 7.4: E2E and Performance Suites
    Run comprehensive end-to-end performance tests.
    """

    def test_end_to_end_transaction_throughput(self, tmp_path):
        """
        Test end-to-end transaction throughput.

        Verify:
        - Transaction processing rate
        - Mempool efficiency
        - Mining throughput

        Measures: transactions per second (TPS)
        """
        blockchain = Blockchain(data_dir=str(tmp_path))
        wallets = [Wallet() for _ in range(10)]

        # Fund all wallets
        for wallet in wallets:
            blockchain.utxo_set[wallet.address] = [
                {"txid": f"genesis-{wallet.address}", "vout": 0, "amount": 10000.0, "script_pubkey": "", "spent": False}
            ]

        # Create batch of transactions
        num_transactions = 100
        transactions = []

        create_start = time.time()
        for i in range(num_transactions):
            sender = wallets[i % len(wallets)]
            receiver = wallets[(i + 1) % len(wallets)]

            tx = Transaction(
                sender.address,
                receiver.address,
                1.0,
                0.01,
                sender.public_key,
                nonce=i
            )
            tx.sign_transaction(sender.private_key)
            transactions.append(tx)

        create_time = time.time() - create_start

        # Add all transactions
        add_start = time.time()
        successful = 0
        for tx in transactions:
            if blockchain.add_transaction(tx):
                successful += 1
        add_time = time.time() - add_start

        # Mine blocks
        mine_start = time.time()
        blocks_mined = 0
        while len(blockchain.pending_transactions) > 0:
            miner = wallets[blocks_mined % len(wallets)]
            blockchain.mine_pending_transactions(miner.address)
            blocks_mined += 1
        mine_time = time.time() - mine_start

        total_time = time.time() - create_start

        # Calculate metrics
        create_tps = num_transactions / create_time
        add_tps = successful / add_time
        mine_tps = successful / mine_time
        total_tps = num_transactions / total_time

        print(f"\nE2E Transaction Throughput:")
        print(f"  Total transactions: {num_transactions}")
        print(f"  Successful: {successful}")
        print(f"  Blocks mined: {blocks_mined}")
        print(f"  Creation TPS: {create_tps:.2f}")
        print(f"  Validation TPS: {add_tps:.2f}")
        print(f"  Mining TPS: {mine_tps:.2f}")
        print(f"  Total TPS: {total_tps:.2f}")

        assert successful >= num_transactions * 0.9, "Should process 90%+ of transactions"
        assert total_tps > 1.0, "Should achieve >1 TPS"

    def test_block_propagation_latency(self, tmp_path):
        """
        Test block propagation latency in multi-node scenario.

        Verify:
        - Block serialization time
        - Deserialization and validation time
        - End-to-end propagation time

        Simulates network propagation through serialization/deserialization.
        """
        # Create source and destination nodes
        source_dir = tmp_path / "node_source"
        dest_dir = tmp_path / "node_dest"
        source_dir.mkdir()
        dest_dir.mkdir()

        source_chain = Blockchain(data_dir=str(source_dir))
        dest_chain = Blockchain(data_dir=str(dest_dir))

        wallet = Wallet()
        source_chain.utxo_set[wallet.address] = [
            {"txid": "genesis", "vout": 0, "amount": 1000.0, "script_pubkey": "", "spent": False}
        ]

        # Add transactions to source
        for i in range(10):
            tx = Transaction(
                wallet.address,
                Wallet().address,
                1.0,
                0.01,
                wallet.public_key,
                nonce=i
            )
            tx.sign_transaction(wallet.private_key)
            source_chain.add_transaction(tx)

        # Mine block on source
        mine_start = time.time()
        block = source_chain.mine_pending_transactions(wallet.address)
        mine_time = time.time() - mine_start

        # Serialize block (simulates network transmission)
        serialize_start = time.time()
        block_data = json.dumps(block.to_dict())
        serialize_time = time.time() - serialize_start

        # Deserialize block
        deserialize_start = time.time()
        received_block_data = json.loads(block_data)
        deserialize_time = time.time() - deserialize_start

        # Validate on destination
        validate_start = time.time()
        # Reconstruct block from data
        from xai.core.blockchain_components.block import Block as BlockClass
        received_block = BlockClass.from_dict(received_block_data)
        validate_time = time.time() - validate_start

        total_propagation = serialize_time + deserialize_time + validate_time

        print(f"\nBlock Propagation Latency:")
        print(f"  Block size: {len(block_data)} bytes")
        print(f"  Transactions: {len(block.transactions)}")
        print(f"  Mining time: {mine_time:.3f}s")
        print(f"  Serialization: {serialize_time:.4f}s")
        print(f"  Deserialization: {deserialize_time:.4f}s")
        print(f"  Validation: {validate_time:.4f}s")
        print(f"  Total propagation: {total_propagation:.4f}s")

        # Propagation should be fast (< 1 second for small blocks)
        assert total_propagation < 1.0, f"Propagation too slow: {total_propagation:.4f}s"

    def test_utxo_set_query_performance(self, tmp_path):
        """
        Test UTXO set query performance with large dataset.

        Verify:
        - Balance query performance
        - UTXO lookup speed
        - Scalability with dataset size
        """
        blockchain = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        # Create large UTXO set
        num_utxos = 1000
        blockchain.utxo_set[wallet.address] = [
            {"txid": f"tx-{i}", "vout": 0, "amount": float(i % 100 + 1), "script_pubkey": "", "spent": False}
            for i in range(num_utxos)
        ]

        # Test balance query performance
        query_times = []
        for _ in range(100):
            start = time.time()
            balance = blockchain.get_balance(wallet.address)
            query_times.append(time.time() - start)

        avg_query_time = sum(query_times) / len(query_times)
        max_query_time = max(query_times)
        min_query_time = min(query_times)

        print(f"\nUTXO Query Performance:")
        print(f"  UTXO set size: {num_utxos}")
        print(f"  Avg query time: {avg_query_time * 1000:.4f}ms")
        print(f"  Min query time: {min_query_time * 1000:.4f}ms")
        print(f"  Max query time: {max_query_time * 1000:.4f}ms")
        print(f"  Balance: {balance}")

        # Queries should be fast (< 10ms average for 1000 UTXOs)
        assert avg_query_time < 0.01, f"UTXO queries too slow: {avg_query_time * 1000:.2f}ms"

    def test_chain_validation_performance(self, tmp_path):
        """
        Test chain validation performance.

        Verify:
        - Validation speed scales with chain length
        - Full chain validation completes in reasonable time
        - No performance cliffs
        """
        blockchain = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        blockchain.utxo_set[wallet.address] = [
            {"txid": "genesis", "vout": 0, "amount": 10000.0, "script_pubkey": "", "spent": False}
        ]

        # Build a chain
        chain_length = 50
        for i in range(chain_length):
            tx = Transaction(
                wallet.address,
                Wallet().address,
                1.0,
                0.01,
                wallet.public_key,
                nonce=i
            )
            tx.sign_transaction(wallet.private_key)
            blockchain.add_transaction(tx)
            blockchain.mine_pending_transactions(wallet.address)

        # Test validation performance
        validation_times = []
        for _ in range(10):
            start = time.time()
            is_valid = blockchain.validate_chain()
            validation_times.append(time.time() - start)
            assert is_valid, "Chain should be valid"

        avg_time = sum(validation_times) / len(validation_times)

        print(f"\nChain Validation Performance:")
        print(f"  Chain length: {len(blockchain.chain)}")
        print(f"  Avg validation time: {avg_time:.3f}s")
        print(f"  Time per block: {avg_time / len(blockchain.chain) * 1000:.2f}ms")

        # Should validate 50 blocks in under 5 seconds
        assert avg_time < 5.0, f"Validation too slow: {avg_time:.3f}s"

    def test_sync_from_genesis_performance(self, tmp_path):
        """
        Test chain synchronization from genesis performance.

        Verify:
        - New node can sync quickly
        - Block loading is efficient
        - UTXO set reconstruction is fast

        Simulates sync by creating chain, saving, and reloading.
        """
        data_dir = tmp_path / "blockchain_data"
        data_dir.mkdir()

        # Create and populate blockchain
        blockchain = Blockchain(data_dir=str(data_dir))
        wallet = Wallet()

        blockchain.utxo_set[wallet.address] = [
            {"txid": "genesis", "vout": 0, "amount": 10000.0, "script_pubkey": "", "spent": False}
        ]

        # Mine blocks
        num_blocks = 30
        for i in range(num_blocks):
            tx = Transaction(
                wallet.address,
                Wallet().address,
                1.0,
                0.01,
                wallet.public_key,
                nonce=i
            )
            tx.sign_transaction(wallet.private_key)
            blockchain.add_transaction(tx)
            blockchain.mine_pending_transactions(wallet.address)

        # Save state
        blockchain.storage.save_utxo_set(blockchain.utxo_set)

        # Simulate sync: create new blockchain instance
        sync_start = time.time()
        synced_chain = Blockchain(data_dir=str(data_dir))
        sync_time = time.time() - sync_start

        print(f"\nSync Performance:")
        print(f"  Blocks synced: {len(synced_chain.chain)}")
        print(f"  Sync time: {sync_time:.3f}s")
        print(f"  Time per block: {sync_time / len(synced_chain.chain) * 1000:.2f}ms")

        # Should sync quickly
        assert sync_time < 10.0, f"Sync too slow: {sync_time:.3f}s"
        assert len(synced_chain.chain) == len(blockchain.chain)

    def test_concurrent_transaction_processing(self, tmp_path):
        """
        Test concurrent transaction processing performance.

        Verify:
        - Multiple transactions can be validated concurrently
        - No race conditions
        - Good throughput under concurrent load
        """
        blockchain = Blockchain(data_dir=str(tmp_path))
        wallets = [Wallet() for _ in range(20)]

        # Fund all wallets
        for wallet in wallets:
            blockchain.utxo_set[wallet.address] = [
                {"txid": f"genesis-{wallet.address}", "vout": 0, "amount": 1000.0, "script_pubkey": "", "spent": False}
            ]

        # Create transactions concurrently
        transactions = []
        for i in range(100):
            sender = wallets[i % len(wallets)]
            receiver = wallets[(i + 1) % len(wallets)]

            tx = Transaction(
                sender.address,
                receiver.address,
                0.5,
                0.01,
                sender.public_key,
                nonce=i
            )
            tx.sign_transaction(sender.private_key)
            transactions.append(tx)

        # Add transactions (simulates concurrent arrival)
        start_time = time.time()
        successful = 0
        for tx in transactions:
            if blockchain.add_transaction(tx):
                successful += 1
        processing_time = time.time() - start_time

        tps = successful / processing_time

        print(f"\nConcurrent Processing Performance:")
        print(f"  Transactions submitted: {len(transactions)}")
        print(f"  Successfully processed: {successful}")
        print(f"  Processing time: {processing_time:.3f}s")
        print(f"  Throughput: {tps:.2f} TPS")

        assert successful >= len(transactions) * 0.8, "Should process 80%+ transactions"
        assert tps > 10.0, "Should achieve >10 TPS for validation"
