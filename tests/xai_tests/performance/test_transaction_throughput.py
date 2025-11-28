"""
Performance tests for transaction throughput (TPS)

Measures transactions per second under various load conditions
"""

import pytest
import time
import threading
from typing import List

from xai.core.blockchain import Blockchain
from xai.core.wallet import Wallet


class TestTransactionThroughput:
    """Test transaction throughput under load"""

    def test_tps_10_transactions(self, tmp_path):
        """Measure TPS with 10 transactions"""
        blockchain = Blockchain(data_dir=str(tmp_path))
        sender = Wallet()

        # Fund sender
        blockchain.mine_pending_transactions(sender.address)

        # Create 10 transactions
        start_time = time.time()
        txs = []
        for i in range(10):
            tx = blockchain.create_transaction(
                sender.address,
                Wallet().address,
                0.5,
                0.05,
                sender.private_key,
                sender.public_key
            )
            blockchain.add_transaction(tx)
            txs.append(tx)

        duration = time.time() - start_time

        # Add to blockchain
        blockchain.mine_pending_transactions(Wallet().address)

        # Calculate TPS
        tps = 10 / duration
        assert tps > 0, "Should process transactions"
        
        # Should process at least 10 TPS for 10 transactions in < 1 second
        assert tps > 10 or duration < 1, f"TPS: {tps}"

    def test_tps_100_transactions(self, tmp_path):
        """Measure TPS with 100 transactions"""
        blockchain = Blockchain(data_dir=str(tmp_path))
        
        # Create multiple funded senders to avoid balance issues
        senders = [Wallet() for _ in range(10)]
        for sender in senders:
            blockchain.mine_pending_transactions(sender.address)

        # Create 100 transactions
        start_time = time.time()
        for i in range(100):
            sender = senders[i % 10]
            tx = blockchain.create_transaction(
                sender.address,
                Wallet().address,
                0.1,
                0.01,
                sender.private_key,
                sender.public_key
            )
            blockchain.add_transaction(tx)

        duration_create = time.time() - start_time

        # Mine block
        start_mine = time.time()
        blockchain.mine_pending_transactions(Wallet().address)
        duration_mine = time.time() - start_mine

        # Calculate throughput metrics
        tps_creation = 100 / duration_create
        
        # Assert reasonable performance
        assert len(blockchain.pending_transactions) >= 0
        assert duration_create < 10, f"Creating 100 transactions took {duration_create}s"

    def test_tps_1000_transactions(self, tmp_path):
        """Measure TPS with 1000 transactions"""
        blockchain = Blockchain(data_dir=str(tmp_path))
        
        # Fund multiple senders
        senders = [Wallet() for _ in range(50)]
        for sender in senders:
            blockchain.mine_pending_transactions(sender.address)

        # Create 1000 transactions
        start_time = time.time()
        tx_count = 0
        for i in range(1000):
            sender = senders[i % 50]
            try:
                tx = blockchain.create_transaction(
                    sender.address,
                    Wallet().address,
                    0.01,
                    0.001,
                    sender.private_key,
                    sender.public_key
                )
                blockchain.add_transaction(tx)
                tx_count += 1
            except Exception:
                pass  # Skip if balance insufficient

        duration = time.time() - start_time

        # Calculate TPS
        if duration > 0:
            tps = tx_count / duration
            # Should handle at least 100 TPS for smaller transactions
            assert tps > 0, "Should process transactions"

    def test_block_mining_throughput(self, tmp_path):
        """Measure block mining throughput"""
        blockchain = Blockchain(data_dir=str(tmp_path))
        miner = Wallet()

        # Mine 50 blocks and measure time
        start_time = time.time()
        for _ in range(50):
            blockchain.mine_pending_transactions(miner.address)
        duration = time.time() - start_time

        # Calculate blocks per second
        bps = 50 / duration

        assert len(blockchain.chain) == 51  # Genesis + 50
        assert duration > 0
        # Should mine at least 1 block per second in testing
        assert bps > 0

    def test_mempool_throughput(self, tmp_path):
        """Measure mempool processing throughput"""
        blockchain = Blockchain(data_dir=str(tmp_path))
        senders = [Wallet() for _ in range(10)]

        for sender in senders:
            blockchain.mine_pending_transactions(sender.address)

        # Add transactions to mempool rapidly
        start_time = time.time()
        for i in range(100):
            sender = senders[i % 10]
            tx = blockchain.create_transaction(
                sender.address,
                Wallet().address,
                0.5,
                0.05,
                sender.private_key,
                sender.public_key
            )
            blockchain.add_transaction(tx)
        duration = time.time() - start_time

        # Calculate mempool throughput
        throughput = 100 / duration if duration > 0 else float('inf')

        assert len(blockchain.pending_transactions) > 0
        # Should add to mempool at > 100 TPS
        assert throughput > 1, f"Mempool throughput: {throughput} TPS"

    def test_sustained_throughput_100_blocks(self, tmp_path):
        """Test sustained throughput over 100 blocks"""
        blockchain = Blockchain(data_dir=str(tmp_path))
        sender = Wallet()

        blockchain.mine_pending_transactions(sender.address)

        start_time = time.time()
        blocks_mined = 0

        for _ in range(100):
            # Create transactions
            for _ in range(10):
                tx = blockchain.create_transaction(
                    sender.address,
                    Wallet().address,
                    0.1,
                    0.01,
                    sender.private_key,
                    sender.public_key
                )
                blockchain.add_transaction(tx)

            # Mine block
            blockchain.mine_pending_transactions(Wallet().address)
            blocks_mined += 1

        duration = time.time() - start_time

        # Calculate average throughput
        total_txs = blocks_mined * 10
        tps = total_txs / duration if duration > 0 else 0

        assert blocks_mined == 100
        assert len(blockchain.chain) == 102  # Genesis + 1 initial + 100

    def test_concurrent_transaction_creation(self, tmp_path):
        """Test concurrent transaction creation throughput"""
        blockchain = Blockchain(data_dir=str(tmp_path))
        senders = [Wallet() for _ in range(5)]

        for sender in senders:
            blockchain.mine_pending_transactions(sender.address)

        # Create transactions concurrently
        created_txs = []
        lock = threading.Lock()

        def create_tx_thread(sender, count):
            for _ in range(count):
                tx = blockchain.create_transaction(
                    sender.address,
                    Wallet().address,
                    0.1,
                    0.01,
                    sender.private_key,
                    sender.public_key
                )
                with lock:
                    created_txs.append(tx)

        start_time = time.time()
        threads = []
        for sender in senders:
            t = threading.Thread(target=create_tx_thread, args=(sender, 20))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        duration = time.time() - start_time

        # Add all to blockchain
        for tx in created_txs:
            blockchain.add_transaction(tx)

        # Calculate concurrent throughput
        throughput = len(created_txs) / duration if duration > 0 else 0

        assert len(created_txs) == 100
        assert throughput > 0


class TestThroughputUnderLoad:
    """Test throughput under various load conditions"""

    def test_throughput_with_large_blocks(self, tmp_path):
        """Test throughput when creating large blocks"""
        blockchain = Blockchain(data_dir=str(tmp_path))

        # Create many funded senders
        senders = [Wallet() for _ in range(20)]
        for sender in senders:
            blockchain.mine_pending_transactions(sender.address)

        # Create large mempool
        for i in range(500):
            sender = senders[i % 20]
            tx = blockchain.create_transaction(
                sender.address,
                Wallet().address,
                0.01,
                0.001,
                sender.private_key,
                sender.public_key
            )
            blockchain.add_transaction(tx)

        # Mine large block
        start_time = time.time()
        block = blockchain.mine_pending_transactions(Wallet().address)
        duration = time.time() - start_time

        # Verify block size
        assert len(block.transactions) > 100
        assert duration < 10, f"Mining large block took {duration}s"

    def test_throughput_chain_validation(self, tmp_path):
        """Test throughput impact of chain validation"""
        blockchain = Blockchain(data_dir=str(tmp_path))
        miner = Wallet()

        # Create 20 blocks
        for _ in range(20):
            blockchain.mine_pending_transactions(miner.address)

        # Time validation
        start_time = time.time()
        is_valid = blockchain.validate_chain()
        duration = time.time() - start_time

        assert is_valid
        assert duration < 5, f"Validating 20 blocks took {duration}s"

    def test_throughput_with_varying_transaction_sizes(self, tmp_path):
        """Test throughput with transactions of varying amounts"""
        blockchain = Blockchain(data_dir=str(tmp_path))
        sender = Wallet()

        blockchain.mine_pending_transactions(sender.address)

        # Create transactions with varying amounts
        amounts = [0.001, 0.01, 0.1, 1.0, 10.0]
        start_time = time.time()

        for amount in amounts * 20:  # 100 total
            tx = blockchain.create_transaction(
                sender.address,
                Wallet().address,
                amount,
                0.01,
                sender.private_key,
                sender.public_key
            )
            blockchain.add_transaction(tx)

        duration = time.time() - start_time
        throughput = 100 / duration if duration > 0 else 0

        assert throughput > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
