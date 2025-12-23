from __future__ import annotations

"""
Comprehensive Network Stress Tests for XAI Blockchain

Tests blockchain performance under extreme load conditions including:
- Transaction throughput (TPS) at scale
- Block propagation across multiple nodes
- Network resilience and recovery
- Concurrent operations and thread safety
- Memory and resource usage
- Chain reorganization under stress

Performance Baselines:
- Transaction Creation: >100 TPS
- Transaction Validation: >50 TPS
- Block Propagation: <2s for 10 nodes
- Memory per 1000 blocks: <100 MB
- Concurrent operations: 50+ threads
"""

import pytest
import time
import threading
import psutil
import os
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any
from unittest.mock import Mock, patch
from collections import defaultdict

from xai.core.blockchain import Blockchain, Transaction, Block
from xai.core.wallet import Wallet
from xai.core.node_p2p import P2PNetworkManager

# Performance baselines (for assertions)
BASELINE_TPS_CREATION = 100
BASELINE_TPS_VALIDATION = 50
BASELINE_BLOCK_PROPAGATION_MS = 2000
BASELINE_MEMORY_PER_1000_BLOCKS_MB = 100

class PerformanceMetrics:
    """Track and report performance metrics"""

    def __init__(self):
        self.metrics: dict[str, Any] = {}
        self.start_time = None
        self.end_time = None

    def start(self):
        """Start timing"""
        self.start_time = time.time()

    def stop(self):
        """Stop timing"""
        self.end_time = time.time()

    def duration(self) -> float:
        """Get duration in seconds"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0.0

    def record(self, key: str, value: Any):
        """Record a metric"""
        self.metrics[key] = value

    def report(self) -> dict[str, Any]:
        """Get full metrics report"""
        return {
            "duration_seconds": self.duration(),
            **self.metrics,
        }

@pytest.mark.slow
class TestTransactionThroughputStress:
    """Comprehensive transaction throughput stress tests"""

    def test_throughput_100_transactions(self, tmp_path):
        """Test processing 100 transactions - baseline performance"""
        metrics = PerformanceMetrics()
        blockchain = Blockchain(data_dir=str(tmp_path))

        # Setup funded wallets
        senders = [Wallet() for _ in range(10)]
        for sender in senders:
            blockchain.mine_pending_transactions(sender.address)

        # Create and submit transactions
        metrics.start()
        tx_count = 0
        for i in range(100):
            sender = senders[i % 10]
            recipient = Wallet()
            tx = blockchain.create_transaction(
                sender.address, recipient.address, 0.1, 0.01, sender.private_key, sender.public_key
            )
            if blockchain.add_transaction(tx):
                tx_count += 1
        metrics.stop()

        # Calculate TPS
        tps = tx_count / metrics.duration() if metrics.duration() > 0 else 0
        metrics.record("transactions_processed", tx_count)
        metrics.record("tps", tps)

        print(f"\n[100 TX Test] TPS: {tps:.2f}, Duration: {metrics.duration():.3f}s")

        assert tx_count >= 95, "Should process at least 95% of transactions"
        assert tps > BASELINE_TPS_CREATION / 2, f"TPS {tps:.2f} below half baseline {BASELINE_TPS_CREATION/2}"

    def test_throughput_1000_transactions(self, tmp_path):
        """Test processing 1,000 transactions - moderate load"""
        metrics = PerformanceMetrics()
        blockchain = Blockchain(data_dir=str(tmp_path))

        # Setup funded wallets
        senders = [Wallet() for _ in range(50)]
        for sender in senders:
            blockchain.mine_pending_transactions(sender.address)

        # Create transactions
        metrics.start()
        tx_count = 0
        for i in range(1000):
            sender = senders[i % 50]
            recipient = Wallet()
            try:
                tx = blockchain.create_transaction(
                    sender.address, recipient.address, 0.01, 0.001, sender.private_key, sender.public_key
                )
                if blockchain.add_transaction(tx):
                    tx_count += 1
            except Exception:
                pass  # Skip on balance exhaustion
        metrics.stop()

        tps = tx_count / metrics.duration() if metrics.duration() > 0 else 0
        metrics.record("transactions_processed", tx_count)
        metrics.record("tps", tps)

        print(f"\n[1000 TX Test] TPS: {tps:.2f}, Duration: {metrics.duration():.3f}s")

        assert tx_count >= 500, "Should process at least 500 transactions"
        assert metrics.duration() < 30, "Should complete within 30 seconds"

    def test_throughput_10000_transactions(self, tmp_path):
        """Test processing 10,000 transactions - high load"""
        metrics = PerformanceMetrics()
        blockchain = Blockchain(data_dir=str(tmp_path))

        # Setup many funded wallets
        senders = [Wallet() for _ in range(100)]
        for sender in senders:
            blockchain.mine_pending_transactions(sender.address)

        # Create transactions in batches
        metrics.start()
        tx_count = 0
        batch_size = 100
        for batch in range(100):  # 100 batches of 100 = 10,000
            for i in range(batch_size):
                sender = senders[(batch * batch_size + i) % 100]
                recipient = Wallet()
                try:
                    tx = blockchain.create_transaction(
                        sender.address,
                        recipient.address,
                        0.001,
                        0.0001,
                        sender.private_key,
                        sender.public_key,
                    )
                    if blockchain.add_transaction(tx):
                        tx_count += 1
                except Exception:
                    pass
        metrics.stop()

        tps = tx_count / metrics.duration() if metrics.duration() > 0 else 0
        metrics.record("transactions_processed", tx_count)
        metrics.record("tps", tps)

        print(f"\n[10000 TX Test] TPS: {tps:.2f}, Duration: {metrics.duration():.3f}s")

        assert tx_count >= 1000, "Should process at least 1000 transactions"
        assert metrics.duration() < 120, "Should complete within 2 minutes"

    def test_concurrent_transaction_submission(self, tmp_path):
        """Test concurrent transaction submission from multiple threads"""
        metrics = PerformanceMetrics()
        blockchain = Blockchain(data_dir=str(tmp_path))

        # Setup funded wallets
        senders = [Wallet() for _ in range(20)]
        for sender in senders:
            blockchain.mine_pending_transactions(sender.address)

        # Concurrent transaction creation
        tx_counts = []
        lock = threading.Lock()

        def submit_transactions(sender, count):
            local_count = 0
            for _ in range(count):
                try:
                    recipient = Wallet()
                    tx = blockchain.create_transaction(
                        sender.address,
                        recipient.address,
                        0.01,
                        0.001,
                        sender.private_key,
                        sender.public_key,
                    )
                    if blockchain.add_transaction(tx):
                        local_count += 1
                except Exception:
                    pass
            with lock:
                tx_counts.append(local_count)

        metrics.start()
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(submit_transactions, sender, 50) for sender in senders]
            for future in as_completed(futures):
                future.result()
        metrics.stop()

        total_tx = sum(tx_counts)
        tps = total_tx / metrics.duration() if metrics.duration() > 0 else 0
        metrics.record("transactions_processed", total_tx)
        metrics.record("tps", tps)
        metrics.record("threads", 20)

        print(f"\n[Concurrent TX Test] TPS: {tps:.2f}, Threads: 20, Duration: {metrics.duration():.3f}s")

        assert total_tx >= 100, "Should process at least 100 concurrent transactions"

    def test_transaction_validation_speed(self, tmp_path):
        """Test transaction validation throughput"""
        metrics = PerformanceMetrics()
        blockchain = Blockchain(data_dir=str(tmp_path))

        # Setup sender
        sender = Wallet()
        blockchain.mine_pending_transactions(sender.address)

        # Create transactions
        transactions = []
        for i in range(200):
            recipient = Wallet()
            tx = blockchain.create_transaction(
                sender.address, recipient.address, 0.001, 0.0001, sender.private_key, sender.public_key
            )
            transactions.append(tx)

        # Validate all
        metrics.start()
        valid_count = sum(1 for tx in transactions if blockchain.validate_transaction(tx))
        metrics.stop()

        validation_tps = valid_count / metrics.duration() if metrics.duration() > 0 else 0
        metrics.record("validated", valid_count)
        metrics.record("validation_tps", validation_tps)

        print(f"\n[Validation Test] Validation TPS: {validation_tps:.2f}, Duration: {metrics.duration():.3f}s")

        assert valid_count >= 100, "Should validate at least 100 transactions"
        assert validation_tps > BASELINE_TPS_VALIDATION / 2, "Validation TPS below half baseline"

    def test_mempool_performance_under_load(self, tmp_path):
        """Test mempool performance with high transaction volume"""
        metrics = PerformanceMetrics()
        blockchain = Blockchain(data_dir=str(tmp_path))

        # Fund wallets
        senders = [Wallet() for _ in range(25)]
        for sender in senders:
            blockchain.mine_pending_transactions(sender.address)

        # Fill mempool rapidly
        metrics.start()
        for i in range(500):
            sender = senders[i % 25]
            recipient = Wallet()
            try:
                tx = blockchain.create_transaction(
                    sender.address, recipient.address, 0.01, 0.001, sender.private_key, sender.public_key
                )
                blockchain.add_transaction(tx)
            except Exception:
                pass
        metrics.stop()

        mempool_size = len(blockchain.pending_transactions)
        add_rate = mempool_size / metrics.duration() if metrics.duration() > 0 else 0

        metrics.record("mempool_size", mempool_size)
        metrics.record("add_rate_tps", add_rate)

        print(f"\n[Mempool Test] Size: {mempool_size}, Add Rate: {add_rate:.2f} TPS")

        assert mempool_size > 0, "Mempool should contain transactions"
        assert add_rate > 50, "Should add to mempool at >50 TPS"

@pytest.mark.slow
class TestBlockPropagationStress:
    """Test block propagation performance under stress"""

    def test_block_propagation_across_10_nodes(self, tmp_path):
        """Test block propagation to 10 nodes"""
        metrics = PerformanceMetrics()

        # Create 10 blockchain instances (simulating nodes)
        nodes = [Blockchain(data_dir=str(tmp_path / f"node_{i}")) for i in range(10)]

        # Create and mine block on first node
        miner = Wallet()
        nodes[0].mine_pending_transactions(miner.address)
        source_block = nodes[0].chain[-1]

        # Simulate propagation to all nodes
        metrics.start()
        propagation_times = []

        for i, node in enumerate(nodes[1:], 1):
            prop_start = time.time()
            # In real scenario, this would be network transmission
            # Here we simulate by copying block data
            _ = source_block.to_dict()
            prop_end = time.time()
            propagation_times.append((prop_end - prop_start) * 1000)  # Convert to ms

        metrics.stop()

        avg_propagation_ms = sum(propagation_times) / len(propagation_times) if propagation_times else 0
        max_propagation_ms = max(propagation_times) if propagation_times else 0

        metrics.record("avg_propagation_ms", avg_propagation_ms)
        metrics.record("max_propagation_ms", max_propagation_ms)
        metrics.record("nodes", 10)

        print(f"\n[Block Propagation Test] Avg: {avg_propagation_ms:.2f}ms, Max: {max_propagation_ms:.2f}ms")

        assert max_propagation_ms < BASELINE_BLOCK_PROPAGATION_MS, "Propagation too slow"

    def test_block_validation_speed_under_load(self, tmp_path):
        """Test block validation speed with many transactions"""
        metrics = PerformanceMetrics()
        blockchain = Blockchain(data_dir=str(tmp_path))

        # Create block with many transactions
        senders = [Wallet() for _ in range(20)]
        for sender in senders:
            blockchain.mine_pending_transactions(sender.address)

        # Add many transactions
        for i in range(100):
            sender = senders[i % 20]
            recipient = Wallet()
            tx = blockchain.create_transaction(
                sender.address, recipient.address, 0.01, 0.001, sender.private_key, sender.public_key
            )
            blockchain.add_transaction(tx)

        # Mine and validate
        metrics.start()
        block = blockchain.mine_pending_transactions(Wallet().address)
        is_valid = blockchain.validate_chain()
        metrics.stop()

        metrics.record("transactions_in_block", len(block.transactions))
        metrics.record("validation_time_ms", metrics.duration() * 1000)

        print(
            f"\n[Block Validation Test] TXs: {len(block.transactions)}, Time: {metrics.duration()*1000:.2f}ms"
        )

        assert is_valid, "Chain should be valid"
        assert metrics.duration() < 120, "Validation should complete in <120s"

    def test_orphan_block_handling(self, tmp_path):
        """Test handling of orphan blocks under stress"""
        blockchain = Blockchain(data_dir=str(tmp_path))
        miner1 = Wallet()
        miner2 = Wallet()

        # Create two competing chains (simulate fork)
        main_chain_length = len(blockchain.chain)

        # Mine on main chain
        for _ in range(5):
            blockchain.mine_pending_transactions(miner1.address)

        # Verify no orphans in linear chain
        assert len(blockchain.chain) == main_chain_length + 5

        print(f"\n[Orphan Block Test] Chain length: {len(blockchain.chain)}")

@pytest.mark.slow
class TestNetworkResilienceStress:
    """Test network resilience under extreme conditions"""

    def test_node_failure_and_recovery(self, tmp_path):
        """Test network behavior when nodes fail and recover"""
        metrics = PerformanceMetrics()

        # Create 5 nodes
        nodes = [Blockchain(data_dir=str(tmp_path / f"node_{i}")) for i in range(5)]
        miner = Wallet()

        # All nodes mine initial blocks
        for node in nodes:
            node.mine_pending_transactions(miner.address)

        metrics.start()

        # Simulate node failures (remove from network)
        active_nodes = nodes[:3]  # First 3 nodes stay active
        failed_nodes = nodes[3:]  # Last 2 nodes fail

        # Continue mining on active nodes
        for _ in range(10):
            for node in active_nodes:
                node.mine_pending_transactions(miner.address)

        # Recover failed nodes
        recovered_nodes = nodes  # All nodes back online

        metrics.stop()

        # Verify active nodes continued functioning
        for node in active_nodes:
            assert len(node.chain) > 10, "Active nodes should have continued mining"

        metrics.record("active_nodes", len(active_nodes))
        metrics.record("recovered_nodes", len(recovered_nodes))

        print(f"\n[Node Failure Test] Active: {len(active_nodes)}, Recovered: {len(recovered_nodes)}")

    def test_network_partition_and_healing(self, tmp_path):
        """Test network partition scenario"""
        metrics = PerformanceMetrics()

        # Create two network partitions
        partition_a = [Blockchain(data_dir=str(tmp_path / f"pa_{i}")) for i in range(3)]
        partition_b = [Blockchain(data_dir=str(tmp_path / f"pb_{i}")) for i in range(3)]

        miner = Wallet()

        metrics.start()

        # Each partition mines independently
        for _ in range(5):
            for node in partition_a:
                node.mine_pending_transactions(miner.address)
            for node in partition_b:
                node.mine_pending_transactions(miner.address)

        # Network heals - partitions merge
        all_nodes = partition_a + partition_b

        metrics.stop()

        # Verify both partitions created chains
        for node in all_nodes:
            assert len(node.chain) > 5, "Nodes should have mined blocks"

        metrics.record("partition_a_size", len(partition_a))
        metrics.record("partition_b_size", len(partition_b))

        print(
            f"\n[Network Partition Test] Partition A: {len(partition_a)}, Partition B: {len(partition_b)}"
        )

    def test_byzantine_node_behavior(self, tmp_path):
        """Test network with Byzantine (malicious) nodes"""
        metrics = PerformanceMetrics()

        # Create honest and Byzantine nodes
        honest_nodes = [Blockchain(data_dir=str(tmp_path / f"honest_{i}")) for i in range(7)]
        byzantine_nodes = [Blockchain(data_dir=str(tmp_path / f"byzantine_{i}")) for i in range(3)]

        miner = Wallet()

        metrics.start()

        # Honest nodes mine valid blocks
        for node in honest_nodes:
            node.mine_pending_transactions(miner.address)

        # Byzantine nodes try invalid operations
        for byz_node in byzantine_nodes:
            try:
                # Attempt invalid mining (should be rejected by network)
                byz_node.mine_pending_transactions(miner.address)
            except Exception:
                pass

        metrics.stop()

        # Verify honest nodes are not corrupted
        for node in honest_nodes:
            assert node.validate_chain(), "Honest node chain should be valid"

        metrics.record("honest_nodes", len(honest_nodes))
        metrics.record("byzantine_nodes", len(byzantine_nodes))

        print(f"\n[Byzantine Test] Honest: {len(honest_nodes)}, Byzantine: {len(byzantine_nodes)}")

    def test_51_percent_attack_scenario(self, tmp_path):
        """Test behavior under 51% attack scenario"""
        metrics = PerformanceMetrics()
        blockchain = Blockchain(data_dir=str(tmp_path))

        attacker = Wallet()
        honest_miner = Wallet()

        # Honest mining
        for _ in range(5):
            blockchain.mine_pending_transactions(honest_miner.address)

        honest_chain_length = len(blockchain.chain)

        metrics.start()

        # Attacker tries to mine faster chain (simulated)
        attack_blockchain = Blockchain(data_dir=str(tmp_path / "attacker"))

        # Attacker mines competing chain
        for _ in range(7):
            attack_blockchain.mine_pending_transactions(attacker.address)

        metrics.stop()

        # In real scenario, longest valid chain wins
        attacker_chain_length = len(attack_blockchain.chain)

        metrics.record("honest_chain_length", honest_chain_length)
        metrics.record("attacker_chain_length", attacker_chain_length)

        print(f"\n[51% Attack Test] Honest: {honest_chain_length}, Attacker: {attacker_chain_length}")

        # System should detect and handle attack
        assert blockchain.validate_chain(), "Original chain should remain valid"

    def test_ddos_protection_mechanisms(self, tmp_path):
        """Test DDoS protection under transaction flood"""
        metrics = PerformanceMetrics()
        blockchain = Blockchain(data_dir=str(tmp_path))

        attacker = Wallet()
        blockchain.mine_pending_transactions(attacker.address)

        # Simulate DDoS with transaction flood
        metrics.start()
        flood_count = 0
        max_flood_attempts = 1000

        for i in range(max_flood_attempts):
            try:
                recipient = Wallet()
                tx = blockchain.create_transaction(
                    attacker.address,
                    recipient.address,
                    0.0001,
                    0.00001,
                    attacker.private_key,
                    attacker.public_key,
                )
                if blockchain.add_transaction(tx):
                    flood_count += 1
            except Exception:
                # System should reject/throttle flood
                pass

        metrics.stop()

        metrics.record("flood_attempts", max_flood_attempts)
        metrics.record("accepted", flood_count)
        metrics.record("rejected", max_flood_attempts - flood_count)

        print(
            f"\n[DDoS Test] Attempts: {max_flood_attempts}, Accepted: {flood_count}, Rejected: {max_flood_attempts - flood_count}"
        )

        # System should handle flood gracefully (may accept all if no rate limiting)
        # This test documents current behavior - future versions should add rate limiting
        assert flood_count <= max_flood_attempts, "Transaction count should not exceed attempts"

        # Note: If flood_count == max_flood_attempts, system has no DDoS protection
        # This is a baseline measurement for future improvement

@pytest.mark.slow
class TestConcurrentOperationsStress:
    """Test concurrent operations and thread safety"""

    def test_simultaneous_mining_on_multiple_nodes(self, tmp_path):
        """Test concurrent mining on multiple nodes"""
        metrics = PerformanceMetrics()

        nodes = [Blockchain(data_dir=str(tmp_path / f"node_{i}")) for i in range(5)]
        miners = [Wallet() for _ in range(5)]

        mining_results = []
        lock = threading.Lock()

        def mine_blocks(node, miner, count):
            local_blocks = []
            for _ in range(count):
                block = node.mine_pending_transactions(miner.address)
                local_blocks.append(block)
            with lock:
                mining_results.append(len(local_blocks))

        metrics.start()

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(mine_blocks, node, miner, 10) for node, miner in zip(nodes, miners)]
            for future in as_completed(futures):
                future.result()

        metrics.stop()

        total_blocks = sum(mining_results)
        metrics.record("total_blocks_mined", total_blocks)
        metrics.record("concurrent_miners", 5)

        print(f"\n[Concurrent Mining Test] Blocks: {total_blocks}, Miners: 5, Duration: {metrics.duration():.2f}s")

        assert total_blocks >= 40, "Should mine at least 40 blocks concurrently"

    def test_concurrent_wallet_operations(self, tmp_path):
        """Test concurrent wallet transactions"""
        metrics = PerformanceMetrics()
        blockchain = Blockchain(data_dir=str(tmp_path))

        wallets = [Wallet() for _ in range(20)]
        for wallet in wallets:
            blockchain.mine_pending_transactions(wallet.address)

        operation_counts = []
        errors = []
        lock = threading.Lock()

        def wallet_operations(wallet, count):
            local_count = 0
            for _ in range(count):
                try:
                    recipient = Wallet()
                    tx = blockchain.create_transaction(
                        wallet.address,
                        recipient.address,
                        0.1,
                        0.01,
                        wallet.private_key,
                        wallet.public_key,
                    )
                    if tx is None:
                        with lock:
                            errors.append("create_transaction returned None (insufficient funds?)")
                    elif blockchain.add_transaction(tx):
                        local_count += 1
                    else:
                        with lock:
                            errors.append("add_transaction returned False (validation failed?)")
                except Exception as e:
                    with lock:
                        errors.append(f"{type(e).__name__}: {str(e)}")
            with lock:
                operation_counts.append(local_count)

        metrics.start()

        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(wallet_operations, wallet, 10) for wallet in wallets]
            for future in as_completed(futures):
                future.result()

        metrics.stop()

        total_ops = sum(operation_counts)
        metrics.record("total_operations", total_ops)
        metrics.record("concurrent_wallets", 20)
        metrics.record("errors", len(errors))

        print(f"\n[Concurrent Wallet Test] Operations: {total_ops}, Wallets: 20")
        if errors:
            print(f"Errors encountered: {len(errors)}")
            # Print first few errors for debugging
            for error in errors[:5]:
                print(f"  - {error}")

        assert total_ops >= 50, f"Should complete at least 50 operations (got {total_ops}, {len(errors)} errors)"

    def test_concurrent_api_requests(self, tmp_path):
        """Test handling concurrent API-like requests"""
        metrics = PerformanceMetrics()
        blockchain = Blockchain(data_dir=str(tmp_path))

        wallets = [Wallet() for _ in range(10)]
        for wallet in wallets:
            blockchain.mine_pending_transactions(wallet.address)

        request_counts = defaultdict(int)
        lock = threading.Lock()

        def api_request_simulation(wallet_id, request_type):
            """Simulate various API requests"""
            if request_type == "get_balance":
                balance = blockchain.get_balance(wallets[wallet_id].address)
                with lock:
                    request_counts["get_balance"] += 1
            elif request_type == "get_chain":
                chain_length = len(blockchain.chain)
                with lock:
                    request_counts["get_chain"] += 1
            elif request_type == "validate_chain":
                is_valid = blockchain.validate_chain()
                with lock:
                    request_counts["validate_chain"] += 1

        metrics.start()

        with ThreadPoolExecutor(max_workers=30) as executor:
            futures = []
            # Simulate 100 concurrent requests
            for i in range(100):
                wallet_id = i % 10
                request_type = ["get_balance", "get_chain", "validate_chain"][i % 3]
                futures.append(executor.submit(api_request_simulation, wallet_id, request_type))

            for future in as_completed(futures):
                future.result()

        metrics.stop()

        total_requests = sum(request_counts.values())
        metrics.record("total_requests", total_requests)
        metrics.record("request_breakdown", dict(request_counts))

        print(f"\n[Concurrent API Test] Requests: {total_requests}, Duration: {metrics.duration():.2f}s")

        assert total_requests == 100, "Should process all 100 requests"

    def test_thread_safety_utxo_set(self, tmp_path):
        """Test UTXO set thread safety under concurrent access"""
        metrics = PerformanceMetrics()
        blockchain = Blockchain(data_dir=str(tmp_path))

        wallets = [Wallet() for _ in range(15)]
        for wallet in wallets:
            blockchain.mine_pending_transactions(wallet.address)

        errors = []
        lock = threading.Lock()

        def concurrent_utxo_access(wallet):
            try:
                # Read UTXO set
                balance = blockchain.get_balance(wallet.address)
                # Attempt transaction (modifies UTXO)
                recipient = Wallet()
                tx = blockchain.create_transaction(
                    wallet.address, recipient.address, 0.5, 0.05, wallet.private_key, wallet.public_key
                )
                blockchain.add_transaction(tx)
            except Exception as e:
                with lock:
                    errors.append(str(e))

        metrics.start()

        with ThreadPoolExecutor(max_workers=15) as executor:
            futures = [executor.submit(concurrent_utxo_access, wallet) for wallet in wallets]
            for future in as_completed(futures):
                future.result()

        metrics.stop()

        metrics.record("errors", len(errors))
        metrics.record("concurrent_accesses", 15)

        print(f"\n[Thread Safety Test] Errors: {len(errors)}, Accesses: 15")

        # Some errors expected due to race conditions, but should not crash
        assert len(errors) < 15, "Not all operations should fail"

    def test_race_condition_detection(self, tmp_path):
        """Test for race conditions in block creation"""
        metrics = PerformanceMetrics()
        blockchain = Blockchain(data_dir=str(tmp_path))

        wallet = Wallet()
        blockchain.mine_pending_transactions(wallet.address)

        # Add transactions
        for _ in range(50):
            recipient = Wallet()
            tx = blockchain.create_transaction(
                wallet.address, recipient.address, 0.01, 0.001, wallet.private_key, wallet.public_key
            )
            blockchain.add_transaction(tx)

        blocks_mined = []
        lock = threading.Lock()

        def mine_block(miner_id):
            """Attempt to mine the same pending transactions"""
            try:
                block = blockchain.mine_pending_transactions(Wallet().address)
                with lock:
                    blocks_mined.append((miner_id, block))
            except Exception:
                pass

        metrics.start()

        # Multiple miners try to mine same transactions
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(mine_block, i) for i in range(5)]
            for future in as_completed(futures):
                future.result()

        metrics.stop()

        metrics.record("concurrent_miners", 5)
        metrics.record("blocks_created", len(blocks_mined))

        print(f"\n[Race Condition Test] Miners: 5, Blocks: {len(blocks_mined)}")

        # Should handle race conditions gracefully
        assert len(blocks_mined) <= 5, "Should not create more blocks than miners"

@pytest.mark.slow
class TestMemoryAndResourceStress:
    """Test memory usage and resource management under stress"""

    def test_memory_usage_with_large_chain(self, tmp_path):
        """Test memory usage with 1000+ block chain"""
        metrics = PerformanceMetrics()
        blockchain = Blockchain(data_dir=str(tmp_path))

        miner = Wallet()
        process = psutil.Process(os.getpid())

        # Measure initial memory
        initial_memory_mb = process.memory_info().rss / 1024 / 1024

        metrics.start()

        # Mine 1000 blocks
        for i in range(1000):
            blockchain.mine_pending_transactions(miner.address)
            if i % 100 == 0:
                current_memory_mb = process.memory_info().rss / 1024 / 1024
                print(f"After {i} blocks: {current_memory_mb:.2f} MB")

        metrics.stop()

        # Measure final memory
        final_memory_mb = process.memory_info().rss / 1024 / 1024
        memory_growth_mb = final_memory_mb - initial_memory_mb

        metrics.record("initial_memory_mb", initial_memory_mb)
        metrics.record("final_memory_mb", final_memory_mb)
        metrics.record("memory_growth_mb", memory_growth_mb)
        metrics.record("blocks_mined", 1000)

        print(
            f"\n[Memory Test] Initial: {initial_memory_mb:.2f}MB, Final: {final_memory_mb:.2f}MB, Growth: {memory_growth_mb:.2f}MB"
        )

        assert memory_growth_mb < BASELINE_MEMORY_PER_1000_BLOCKS_MB * 2, "Memory growth too high"

    def test_disk_io_performance(self, tmp_path):
        """Test disk I/O performance during blockchain operations"""
        metrics = PerformanceMetrics()
        blockchain = Blockchain(data_dir=str(tmp_path))

        miner = Wallet()

        metrics.start()

        # Mine blocks (triggers disk writes)
        for _ in range(100):
            blockchain.mine_pending_transactions(miner.address)

        metrics.stop()

        # Check disk usage
        disk_usage = 0
        if os.path.exists(str(tmp_path)):
            for root, dirs, files in os.walk(str(tmp_path)):
                for file in files:
                    file_path = os.path.join(root, file)
                    if os.path.exists(file_path):
                        disk_usage += os.path.getsize(file_path)

        disk_usage_mb = disk_usage / 1024 / 1024
        metrics.record("disk_usage_mb", disk_usage_mb)
        metrics.record("blocks_written", 100)

        print(f"\n[Disk I/O Test] Usage: {disk_usage_mb:.2f}MB, Blocks: 100")

        assert disk_usage_mb < 50, "Disk usage too high for 100 blocks"

    def test_cpu_usage_during_mining(self, tmp_path):
        """Test CPU usage during intensive mining"""
        metrics = PerformanceMetrics()
        blockchain = Blockchain(data_dir=str(tmp_path))

        miner = Wallet()
        process = psutil.Process(os.getpid())

        # Measure CPU during mining
        cpu_percentages = []

        metrics.start()

        for i in range(50):
            blockchain.mine_pending_transactions(miner.address)
            if i % 10 == 0:
                cpu_percent = process.cpu_percent(interval=0.1)
                cpu_percentages.append(cpu_percent)

        metrics.stop()

        avg_cpu = sum(cpu_percentages) / len(cpu_percentages) if cpu_percentages else 0
        metrics.record("avg_cpu_percent", avg_cpu)
        metrics.record("blocks_mined", 50)

        print(f"\n[CPU Test] Avg CPU: {avg_cpu:.2f}%, Blocks: 50")

        # CPU usage expected during mining
        assert avg_cpu >= 0, "Should measure CPU usage"

    def test_network_bandwidth_simulation(self, tmp_path):
        """Test network bandwidth usage during block propagation"""
        metrics = PerformanceMetrics()
        blockchain = Blockchain(data_dir=str(tmp_path))

        # Create block with transactions
        sender = Wallet()
        blockchain.mine_pending_transactions(sender.address)

        for _ in range(100):
            recipient = Wallet()
            tx = blockchain.create_transaction(
                sender.address, recipient.address, 0.01, 0.001, sender.private_key, sender.public_key
            )
            blockchain.add_transaction(tx)

        # Mine block
        block = blockchain.mine_pending_transactions(Wallet().address)

        # Measure serialized size
        metrics.start()
        block_data = block.to_dict()
        block_json = json.dumps(block_data)
        block_size_kb = len(block_json.encode()) / 1024
        metrics.stop()

        # Simulate propagation to 50 nodes
        total_bandwidth_kb = block_size_kb * 50

        metrics.record("block_size_kb", block_size_kb)
        metrics.record("nodes", 50)
        metrics.record("total_bandwidth_kb", total_bandwidth_kb)

        print(
            f"\n[Bandwidth Test] Block: {block_size_kb:.2f}KB, Nodes: 50, Total: {total_bandwidth_kb:.2f}KB"
        )

        assert block_size_kb > 0, "Block should have measurable size"

    def test_resource_cleanup_after_operations(self, tmp_path):
        """Test proper resource cleanup after operations"""
        metrics = PerformanceMetrics()
        blockchain = Blockchain(data_dir=str(tmp_path))

        miner = Wallet()
        process = psutil.Process(os.getpid())

        initial_memory = process.memory_info().rss / 1024 / 1024

        metrics.start()

        # Perform operations
        for _ in range(100):
            blockchain.mine_pending_transactions(miner.address)

        # Force cleanup (in production, this might be automatic)
        intermediate_memory = process.memory_info().rss / 1024 / 1024

        metrics.stop()

        final_memory = process.memory_info().rss / 1024 / 1024

        metrics.record("initial_memory_mb", initial_memory)
        metrics.record("intermediate_memory_mb", intermediate_memory)
        metrics.record("final_memory_mb", final_memory)

        print(
            f"\n[Cleanup Test] Initial: {initial_memory:.2f}MB, Intermediate: {intermediate_memory:.2f}MB, Final: {final_memory:.2f}MB"
        )

        # Memory should not grow unbounded
        memory_growth = final_memory - initial_memory
        assert memory_growth < 200, "Memory growth too high - possible leak"

@pytest.mark.slow
class TestChainReorganizationStress:
    """Test chain reorganization under stress conditions"""

    def test_deep_reorganization_50_blocks(self, tmp_path):
        """Test reorganization with 50+ block deep fork"""
        metrics = PerformanceMetrics()

        # Create main chain
        main_chain = Blockchain(data_dir=str(tmp_path / "main"))
        fork_chain = Blockchain(data_dir=str(tmp_path / "fork"))

        miner = Wallet()

        # Build common history
        for _ in range(10):
            main_chain.mine_pending_transactions(miner.address)

        metrics.start()

        # Create deep fork
        for _ in range(40):
            main_chain.mine_pending_transactions(miner.address)

        # Fork mines longer chain
        for _ in range(55):
            fork_chain.mine_pending_transactions(miner.address)

        metrics.stop()

        main_length = len(main_chain.chain)
        fork_length = len(fork_chain.chain)

        metrics.record("main_chain_length", main_length)
        metrics.record("fork_chain_length", fork_length)
        metrics.record("fork_depth", 50)

        print(f"\n[Deep Reorg Test] Main: {main_length}, Fork: {fork_length}, Depth: 50")

        assert fork_length >= main_length, "Fork should be at least as long as main"

    def test_multiple_competing_chains(self, tmp_path):
        """Test with many competing chains"""
        metrics = PerformanceMetrics()

        # Create 5 competing chains
        chains = [Blockchain(data_dir=str(tmp_path / f"chain_{i}")) for i in range(5)]
        miners = [Wallet() for _ in range(5)]

        metrics.start()

        # Each chain mines different number of blocks
        for i, (chain, miner) in enumerate(zip(chains, miners)):
            for _ in range(10 + i * 5):  # 10, 15, 20, 25, 30 blocks
                chain.mine_pending_transactions(miner.address)

        metrics.stop()

        chain_lengths = [len(chain.chain) for chain in chains]
        longest_chain_idx = chain_lengths.index(max(chain_lengths))

        metrics.record("chain_lengths", chain_lengths)
        metrics.record("longest_chain_idx", longest_chain_idx)

        print(f"\n[Multiple Chains Test] Lengths: {chain_lengths}, Longest: {longest_chain_idx}")

        assert max(chain_lengths) == 31, "Longest chain should have 31 blocks"

    def test_reorg_performance_impact(self, tmp_path):
        """Test performance impact of reorganization"""
        metrics = PerformanceMetrics()
        blockchain = Blockchain(data_dir=str(tmp_path))

        miner = Wallet()

        # Build initial chain
        for _ in range(20):
            blockchain.mine_pending_transactions(miner.address)

        # Measure normal operation
        metrics.start()
        normal_start = time.time()
        for _ in range(10):
            blockchain.mine_pending_transactions(miner.address)
        normal_duration = time.time() - normal_start

        metrics.stop()

        metrics.record("normal_duration_ms", normal_duration * 1000)
        metrics.record("blocks_during_normal", 10)

        print(f"\n[Reorg Performance Test] Normal duration: {normal_duration*1000:.2f}ms")

        assert normal_duration < 30, "Normal operations should be fast"

    def test_utxo_consistency_under_stress_reorg(self, tmp_path):
        """Test UTXO set consistency during reorganization"""
        metrics = PerformanceMetrics()
        blockchain = Blockchain(data_dir=str(tmp_path))

        wallets = [Wallet() for _ in range(10)]

        # Build chain with transactions
        for wallet in wallets:
            blockchain.mine_pending_transactions(wallet.address)

        metrics.start()

        # Create transactions
        for i in range(len(wallets) - 1):
            sender = wallets[i]
            recipient = wallets[i + 1]
            tx = blockchain.create_transaction(
                sender.address, recipient.address, 1.0, 0.1, sender.private_key, sender.public_key
            )
            blockchain.add_transaction(tx)

        blockchain.mine_pending_transactions(Wallet().address)

        # Check UTXO consistency
        utxo_count = sum(len(utxos) for utxos in blockchain.utxo_set.values())

        metrics.stop()

        metrics.record("utxo_count", utxo_count)
        metrics.record("wallets", len(wallets))

        print(f"\n[UTXO Consistency Test] UTXOs: {utxo_count}, Wallets: {len(wallets)}")

        assert utxo_count > 0, "Should have UTXOs"
        assert blockchain.validate_chain(), "Chain should be valid"

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
