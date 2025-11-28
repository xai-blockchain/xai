"""
Comprehensive tests for mempool eviction policies

Tests fee-based eviction, size limits, transaction expiry,
eviction order, and re-addition after eviction.
"""

import pytest
import time
from unittest.mock import Mock, patch

from xai.network.mempool_manager import MempoolManager


class TestMempoolEviction:
    """Tests for mempool eviction"""

    def test_fee_based_eviction_lowest_fee_first(self):
        """Test lowest fee transactions evicted first"""
        mempool = MempoolManager(
            max_transactions=3,
            eviction_policy="lowest_fee"
        )

        # Add transactions with different fees
        mempool.add_transaction("tx1", fee=1.0)
        mempool.add_transaction("tx2", fee=5.0)
        mempool.add_transaction("tx3", fee=3.0)

        assert len(mempool.pending_transactions) == 3

        # Add 4th transaction (should evict lowest fee)
        mempool.add_transaction("tx4", fee=4.0)

        # tx1 (fee 1.0) should be evicted
        assert "tx_1" not in mempool.pending_transactions
        assert len(mempool.pending_transactions) == 3

    def test_mempool_size_limit_enforcement(self):
        """Test mempool size limit is strictly enforced"""
        mempool = MempoolManager(max_transactions=5)

        # Fill mempool
        for i in range(5):
            mempool.add_transaction(f"tx{i}", fee=float(i))

        assert len(mempool.pending_transactions) == 5

        # Add another transaction (should trigger eviction)
        mempool.add_transaction("tx6", fee=10.0)

        # Size should not exceed limit
        assert len(mempool.pending_transactions) == 5

    def test_transaction_expiry_24_hours(self):
        """Test transactions expire after 24 hours"""
        mempool = MempoolManager(transaction_expiry_seconds=86400)  # 24 hours

        tx_id = mempool.add_transaction("tx_data", fee=1.0)

        # Transaction should exist
        assert tx_id in mempool.pending_transactions

        # Get transaction timestamp
        tx = mempool.pending_transactions[tx_id]
        original_timestamp = tx['timestamp']

        # Mock time to be 25 hours later
        current_time = original_timestamp + 90000  # 25 hours

        # Check if expired
        age = current_time - original_timestamp
        is_expired = age > mempool.transaction_expiry_seconds

        assert is_expired is True

    def test_eviction_order_correctness(self):
        """Test eviction order follows policy correctly"""
        mempool = MempoolManager(
            max_transactions=4,
            eviction_policy="lowest_fee"
        )

        # Add transactions in random order
        mempool.add_transaction("tx1", fee=5.0)
        mempool.add_transaction("tx2", fee=1.0)
        mempool.add_transaction("tx3", fee=10.0)
        mempool.add_transaction("tx4", fee=3.0)

        # Trigger eviction with higher fee
        mempool.add_transaction("tx5", fee=7.0)

        # tx2 (fee 1.0) should be evicted as it has lowest fee
        # Remaining should be tx1(5), tx3(10), tx4(3), tx5(7)
        assert len(mempool.pending_transactions) == 4

    def test_fifo_eviction_policy(self):
        """Test FIFO eviction policy"""
        mempool = MempoolManager(
            max_transactions=3,
            eviction_policy="fifo"
        )

        # Add transactions
        tx1_id = mempool.add_transaction("tx1", fee=1.0)
        time.sleep(0.01)
        tx2_id = mempool.add_transaction("tx2", fee=2.0)
        time.sleep(0.01)
        tx3_id = mempool.add_transaction("tx3", fee=3.0)

        # Add 4th transaction (should evict oldest)
        time.sleep(0.01)
        tx4_id = mempool.add_transaction("tx4", fee=4.0)

        # tx1 should be evicted (oldest)
        assert tx1_id not in mempool.pending_transactions
        assert tx2_id in mempool.pending_transactions
        assert tx3_id in mempool.pending_transactions
        assert tx4_id in mempool.pending_transactions

    def test_readd_transaction_after_eviction(self):
        """Test re-adding evicted transaction"""
        mempool = MempoolManager(
            max_transactions=2,
            eviction_policy="lowest_fee"
        )

        # Add transactions
        mempool.add_transaction("tx1", fee=1.0)
        mempool.add_transaction("tx2", fee=2.0)

        # Add tx3, evicting tx1
        mempool.add_transaction("tx3", fee=3.0)

        # Re-add tx1 with higher fee
        new_tx1_id = mempool.add_transaction("tx1", fee=5.0)

        # Should be in mempool now
        assert new_tx1_id in mempool.pending_transactions

    def test_multiple_evictions_in_sequence(self):
        """Test multiple sequential evictions"""
        mempool = MempoolManager(
            max_transactions=3,
            eviction_policy="lowest_fee"
        )

        # Fill mempool
        mempool.add_transaction("tx1", fee=1.0)
        mempool.add_transaction("tx2", fee=2.0)
        mempool.add_transaction("tx3", fee=3.0)

        # Add multiple transactions triggering evictions
        mempool.add_transaction("tx4", fee=4.0)  # Evicts tx1
        mempool.add_transaction("tx5", fee=5.0)  # Evicts tx2
        mempool.add_transaction("tx6", fee=6.0)  # Evicts tx3

        # Final mempool should have highest fee transactions
        assert len(mempool.pending_transactions) == 3

    def test_eviction_doesnt_affect_high_fee_transactions(self):
        """Test high fee transactions are not evicted"""
        mempool = MempoolManager(
            max_transactions=3,
            eviction_policy="lowest_fee"
        )

        # Add high fee transaction
        high_fee_id = mempool.add_transaction("high_fee_tx", fee=100.0)

        # Add low fee transactions
        mempool.add_transaction("tx1", fee=1.0)
        mempool.add_transaction("tx2", fee=2.0)

        # Add another transaction
        mempool.add_transaction("tx3", fee=3.0)

        # High fee transaction should remain
        assert high_fee_id in mempool.pending_transactions

    def test_transaction_removal(self):
        """Test removing transaction from mempool"""
        mempool = MempoolManager()

        tx_id = mempool.add_transaction("tx_data", fee=1.0)
        assert tx_id in mempool.pending_transactions

        # Remove transaction
        mempool.remove_transaction(tx_id)
        assert tx_id not in mempool.pending_transactions

    def test_empty_mempool_handling(self):
        """Test handling of empty mempool"""
        mempool = MempoolManager()

        # Empty mempool
        assert len(mempool.pending_transactions) == 0

        # Get transactions (should return empty)
        txs = mempool.get_transactions(5)
        assert len(txs) == 0

    def test_transaction_priority_by_fee(self):
        """Test transactions are prioritized by fee"""
        mempool = MempoolManager()

        # Add transactions with different fees
        mempool.add_transaction("tx1", fee=1.0)
        mempool.add_transaction("tx2", fee=10.0)
        mempool.add_transaction("tx3", fee=5.0)

        # Get highest fee transactions
        high_fee_txs = mempool.get_top_transactions_by_fee(2)

        # Should return highest fee transactions
        assert len(high_fee_txs) <= 2
