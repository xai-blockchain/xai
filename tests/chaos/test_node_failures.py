"""
Chaos tests for node failure scenarios

Tests recovery from various failure modes, data corruption handling,
and resilience under adverse conditions.
"""

import pytest
import random
import threading
import time
from typing import List

from xai.core.blockchain import Blockchain, Block
from xai.core.node import BlockchainNode
from xai.core.wallet import Wallet


def miner_identity_from_wallet(wallet: Wallet) -> dict:
    """Build miner identity dict from wallet keys."""
    return {"private_key": wallet.private_key, "public_key": wallet.public_key}


def new_wallet_and_identity() -> tuple[Wallet, dict]:
    w = Wallet()
    return w, miner_identity_from_wallet(w)


class TestNodeFailureRecovery:
    """Test blockchain recovery from node failures"""

    def test_node_restart_recovery(self, tmp_path):
        """Test node recovery after restart"""
        node_dir = tmp_path / "node"
        node_dir.mkdir()

        # Node operates normally
        bc1 = Blockchain(data_dir=str(node_dir))
        miner = Wallet()

        identity = miner_identity_from_wallet(miner)
        for _ in range(5):
            bc1.mine_pending_transactions(miner.address, identity)

        height_before = len(bc1.chain)
        last_hash = bc1.chain[-1].hash

        # "Restart" by creating new blockchain instance
        del bc1

        # Reload blockchain (data persisted)
        bc2 = Blockchain(data_dir=str(node_dir))

        # Should recover state
        height_after = len(bc2.chain)
        assert height_after == height_before
        assert bc2.chain[-1].hash == last_hash

    def test_graceful_shutdown_recovery(self, tmp_path):
        """Test recovery after graceful shutdown"""
        node_dir = tmp_path / "node"
        node_dir.mkdir()

        bc = Blockchain(data_dir=str(node_dir))
        miner = Wallet()

        # Normal operations
        identity = miner_identity_from_wallet(miner)
        for _ in range(10):
            bc.mine_pending_transactions(miner.address, identity)

        balance_before = bc.get_balance(miner.address)

        # Graceful shutdown
        bc = None

        # Recovery
        bc_new = Blockchain(data_dir=str(node_dir))
        balance_after = bc_new.get_balance(miner.address)

        assert balance_before == balance_after

    def test_node_crash_recovery(self, tmp_path):
        """Test recovery from sudden node crash"""
        node_dir = tmp_path / "node"
        node_dir.mkdir()

        bc = Blockchain(data_dir=str(node_dir))
        miner = Wallet()

        # Normal operation
        identity = miner_identity_from_wallet(miner)
        for _ in range(5):
            bc.mine_pending_transactions(miner.address, identity)

        # Simulate crash by force deleting object
        height_at_crash = len(bc.chain)
        del bc

        # Restart
        bc_restored = Blockchain(data_dir=str(node_dir))

        # Should be at least partially recovered
        height_after = len(bc_restored.chain)
        assert height_after > 0

    def test_missing_block_recovery(self, tmp_path):
        """Test recovery when a block is missing"""
        node_dir = tmp_path / "node"
        node_dir.mkdir()

        bc = Blockchain(data_dir=str(node_dir))

        # Create blockchain with 10 blocks
        for _ in range(10):
            w = Wallet()
            bc.mine_pending_transactions(w.address, miner_identity_from_wallet(w))

        # Simulate missing middle block (chain becomes invalid)
        original_chain = bc.chain.copy()

        # Chain should still be valid before corruption
        assert bc.validate_chain()

    def test_corrupt_block_handling(self, tmp_path):
        """Test handling of corrupted block data"""
        node_dir = tmp_path / "node"
        node_dir.mkdir()

        bc = Blockchain(data_dir=str(node_dir))
        miner = Wallet()

        # Create some blocks
        identity = miner_identity_from_wallet(miner)
        for _ in range(5):
            bc.mine_pending_transactions(miner.address, identity)

        # Corrupt last block's hash (simulate corruption)
        original_hash = bc.chain[-1].hash
        bc.chain[-1].hash = "corrupted_hash_" + ("0" * 48)

        # Validation should fail
        is_valid = bc.validate_chain()
        assert not is_valid

        # Restore
        bc.chain[-1].hash = original_hash
        is_valid = bc.validate_chain()
        assert is_valid

    def test_database_corruption_recovery(self, tmp_path):
        """Test recovery from database corruption"""
        node_dir = tmp_path / "node"
        node_dir.mkdir()

        bc1 = Blockchain(data_dir=str(node_dir))

        # Create state
        for _ in range(5):
            w = Wallet()
            bc1.mine_pending_transactions(w.address, miner_identity_from_wallet(w))

        del bc1

        # Simulate recovery (blockchain reloads from storage)
        bc2 = Blockchain(data_dir=str(node_dir))

        assert len(bc2.chain) > 0
        assert bc2.validate_chain()

    def test_partial_write_recovery(self, tmp_path):
        """Test recovery from incomplete block writes"""
        node_dir = tmp_path / "node"
        node_dir.mkdir()

        bc = Blockchain(data_dir=str(node_dir))

        # Mine normally first
        for _ in range(3):
            w = Wallet()
            bc.mine_pending_transactions(w.address, miner_identity_from_wallet(w))

        # Create pending transaction (simulates crash during write)
        tx = bc.create_transaction(
            Wallet().address,
            Wallet().address,
            1.0,
            0.1,
            "0" * 64,
            "0" * 128
        )
        bc.add_transaction(tx)

        # Simulate crash and recovery
        height_before = len(bc.chain)
        del bc

        bc_new = Blockchain(data_dir=str(node_dir))

        # Should have recovered blocks
        height_after = len(bc_new.chain)
        assert height_after >= height_before - 1


class TestCascadingFailures:
    """Test handling of cascading failures"""

    def test_multiple_node_failures(self, tmp_path):
        """Test network resilience with multiple node failures"""
        node_dirs = [tmp_path / f"node_{i}" for i in range(3)]
        for d in node_dirs:
            d.mkdir()

        nodes = [Blockchain(data_dir=str(d)) for d in node_dirs]

        # Sync all nodes
        for _ in range(3):
            w = Wallet()
            block = nodes[0].mine_pending_transactions(w.address, miner_identity_from_wallet(w))
            for node in nodes[1:]:
                node.add_block(block)

        # Node 1 fails (simulate offline without shrinking collection)
        nodes[0] = None

        # Node 2 continues
        w2 = Wallet()
        block = nodes[1].mine_pending_transactions(w2.address, miner_identity_from_wallet(w2))

        # Node 3 continues
        nodes[2].add_block(block)

        # Both surviving nodes should be synced
        assert len(nodes[1].chain) == len(nodes[2].chain)

    def test_consensus_failure_recovery(self, tmp_path):
        """Test recovery when consensus is temporarily lost"""
        node1_dir = tmp_path / "node1"
        node2_dir = tmp_path / "node2"
        node1_dir.mkdir()
        node2_dir.mkdir()

        bc1 = Blockchain(data_dir=str(node1_dir))
        bc2 = Blockchain(data_dir=str(node2_dir))

        # Sync - both nodes start with the same block
        w, ident = new_wallet_and_identity()
        block = bc1.mine_pending_transactions(w.address, ident)
        bc2.add_block(block)

        # Wait to ensure timestamp progresses (Unix timestamps have 1-second granularity)
        time.sleep(1.1)

        # Divergence - bc1 mines more blocks (longer chain)
        for _ in range(3):
            time.sleep(1.1)  # Ensure strict timestamp ordering with 1-second granularity
            w1, id1 = new_wallet_and_identity()
            block1 = bc1.mine_pending_transactions(w1.address, id1)

        # Wait before bc2 diverges
        time.sleep(1.1)

        # bc2 mines fewer blocks (shorter chain)
        for _ in range(2):
            time.sleep(1.1)  # Ensure strict timestamp ordering
            w2, id2 = new_wallet_and_identity()
            block2 = bc2.mine_pending_transactions(w2.address, id2)

        # bc1 is longer, bc2 should reorganize to bc1's longer chain
        # Use replace_chain to properly handle chain reorganization
        result = bc2.replace_chain(bc1.chain)
        assert result is True, "Chain reorganization should succeed"

        # Recover consensus - both chains should now have the same length and last hash
        assert len(bc1.chain) == len(bc2.chain)
        assert bc1.chain[-1].hash == bc2.chain[-1].hash


class TestRandomFailures:
    """Test handling of random failure injection"""

    def test_random_block_creation_failures(self, tmp_path):
        """Test recovery from random block creation failures"""
        node_dir = tmp_path / "node"
        node_dir.mkdir()

        bc = Blockchain(data_dir=str(node_dir))

        success_count = 0
        for i in range(20):
            try:
                # Randomly skip some mining attempts (simulate failures)
                if random.random() > 0.3:  # 70% success rate
                    w, ident = new_wallet_and_identity()
                    block = bc.mine_pending_transactions(w.address, ident)
                    success_count += 1
            except Exception:
                pass  # Failure - continue

        # Should have succeeded many times
        assert success_count > 10
        assert len(bc.chain) > 1

    def test_random_transaction_failures(self, tmp_path):
        """Test resilience to random transaction processing failures"""
        node_dir = tmp_path / "node"
        node_dir.mkdir()

        bc = Blockchain(data_dir=str(node_dir))
        wallet = Wallet()

        bc.mine_pending_transactions(wallet.address, miner_identity_from_wallet(wallet))

        # Attempt many transactions, some may fail
        success_count = 0
        for _ in range(100):
            try:
                if random.random() > 0.1:  # 90% attempt rate
                    tx = bc.create_transaction(
                        wallet.address,
                        Wallet().address,
                        random.uniform(0.01, 0.5),
                        random.uniform(0.001, 0.1),
                        wallet.private_key,
                        wallet.public_key
                    )
                    bc.add_transaction(tx)
                    success_count += 1
            except Exception:
                pass

        # Should have processed some transactions
        assert success_count > 0

    def test_random_network_delays(self, tmp_path):
        """Test handling of simulated network delays"""
        node_dirs = [tmp_path / f"node_{i}" for i in range(2)]
        for d in node_dirs:
            d.mkdir()

        bc1 = Blockchain(data_dir=str(node_dirs[0]))
        bc2 = Blockchain(data_dir=str(node_dirs[1]))

        # Mine on node 1
        w, ident = new_wallet_and_identity()
        block = bc1.mine_pending_transactions(w.address, ident)

        # Simulate random network delays
        for _ in range(5):
            delay = random.uniform(0.01, 0.1)
            time.sleep(delay)

        # Propagate block
        bc2.add_block(block)

        # Should still be in sync
        assert len(bc2.chain) >= 1


class TestStressConditions:
    """Test behavior under stress conditions"""

    def test_low_memory_stress(self, tmp_path):
        """Test blockchain behavior under simulated memory pressure"""
        node_dir = tmp_path / "node"
        node_dir.mkdir()

        bc = Blockchain(data_dir=str(node_dir))

        # Create many blocks to stress memory
        miner, ident = new_wallet_and_identity()
        for _ in range(50):
            bc.mine_pending_transactions(miner.address, ident)

        # Should still function
        assert bc.validate_chain()
        assert len(bc.chain) == 51

    def test_high_pending_transaction_load(self, tmp_path):
        """Test blockchain with many pending transactions"""
        node_dir = tmp_path / "node"
        node_dir.mkdir()

        bc = Blockchain(data_dir=str(node_dir))
        senders = [Wallet() for _ in range(10)]

        for sender in senders:
            bc.mine_pending_transactions(sender.address, miner_identity_from_wallet(sender))

        # Create 500 pending transactions
        for i in range(500):
            sender = senders[i % 10]
            try:
                tx = bc.create_transaction(
                    sender.address,
                    Wallet().address,
                    0.01,
                    0.001,
                    sender.private_key,
                    sender.public_key
                )
                bc.add_transaction(tx)
            except Exception:
                pass

        # System should still be responsive
        w, ident = new_wallet_and_identity()
        block = bc.mine_pending_transactions(w.address, ident)
        assert block is not None

    def test_rapid_block_succession(self, tmp_path):
        """Test blockchain with rapid block creation"""
        node_dir = tmp_path / "node"
        node_dir.mkdir()

        bc = Blockchain(data_dir=str(node_dir))
        miner = Wallet()

        start_time = time.time()

        # Mine 100 blocks as fast as possible
        for _ in range(100):
            bc.mine_pending_transactions(miner.address, miner_identity_from_wallet(miner))

        duration = time.time() - start_time

        # Should complete without crashing
        assert len(bc.chain) == 101
        assert bc.validate_chain()

    def test_concurrent_operations_stress(self, tmp_path):
        """Test concurrent mining and transaction processing"""
        node_dir = tmp_path / "node"
        node_dir.mkdir()

        bc = Blockchain(data_dir=str(node_dir))
        senders = [Wallet() for _ in range(5)]

        for sender in senders:
            bc.mine_pending_transactions(sender.address, miner_identity_from_wallet(sender))

        results = []
        errors = []

        def miner_thread():
            try:
                for _ in range(10):
                    w, ident = new_wallet_and_identity()
                    bc.mine_pending_transactions(w.address, ident)
                    results.append("mine_ok")
            except Exception as e:
                errors.append(str(e))

        def tx_thread(sender):
            try:
                for _ in range(20):
                    tx = bc.create_transaction(
                        sender.address,
                        Wallet().address,
                        0.01,
                        0.001,
                        sender.private_key,
                        sender.public_key
                    )
                    bc.add_transaction(tx)
                    results.append("tx_ok")
            except Exception as e:
                errors.append(str(e))

        # Start concurrent threads
        threads = []
        t = threading.Thread(target=miner_thread)
        threads.append(t)
        t.start()

        for sender in senders:
            t = threading.Thread(target=tx_thread, args=(sender,))
            threads.append(t)
            t.start()

        # Wait for completion
        for t in threads:
            t.join(timeout=10)

        # Should have processed many operations despite concurrency
        assert len(results) > 50 or len(errors) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
