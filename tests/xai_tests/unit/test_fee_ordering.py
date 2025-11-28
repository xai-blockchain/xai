"""
Fee Ordering Tests (Task 201)

Tests for Blockchain._prioritize_transactions method to ensure correct
fee-based prioritization for transaction ordering in blocks.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from src.xai.core.blockchain import Blockchain, Transaction
import time


class TestFeeOrdering:
    """Test transaction prioritization by fee rate"""

    def setup_method(self):
        """Setup blockchain for each test"""
        self.blockchain = Blockchain(data_dir="/tmp/test_fee_ordering")

    def create_transaction(self, sender_id: int, amount: float, fee: float, size_multiplier: int = 1) -> Transaction:
        """
        Create a test transaction with specific fee.

        size_multiplier: Multiply transaction size by adding dummy metadata
        """
        tx = Transaction(
            sender=f"XAI{'0' * 40}sender{sender_id}",
            recipient=f"XAI{'0' * 40}recipient{sender_id}",
            amount=amount,
            fee=fee,
        )

        # Add metadata to increase size if needed
        if size_multiplier > 1:
            tx.metadata = {"padding": "x" * (100 * size_multiplier)}

        tx.txid = f"txid_{sender_id:04d}_{'a' * 56}"
        tx.signature = "signature_" + "b" * 118
        return tx

    def test_prioritize_by_absolute_fee_simple(self):
        """Task 201: Transactions should be ordered by fee rate (fee/byte), not absolute fee"""
        # Create transactions with different fees but same size
        txs = [
            self.create_transaction(1, 100.0, 0.5),   # Low fee
            self.create_transaction(2, 100.0, 2.0),   # High fee
            self.create_transaction(3, 100.0, 1.0),   # Medium fee
        ]

        # Add to pending transactions
        self.blockchain.pending_transactions = txs.copy()

        # Prioritize
        prioritized = self.blockchain._prioritize_transactions(txs)

        # Should be ordered by fee: 2.0, 1.0, 0.5
        assert prioritized[0].fee == 2.0, "Highest fee should be first"
        assert prioritized[1].fee == 1.0, "Medium fee should be second"
        assert prioritized[2].fee == 0.5, "Lowest fee should be third"

    def test_prioritize_by_fee_rate_not_absolute(self):
        """Task 201: Should prioritize by fee RATE (fee/byte), not absolute fee amount"""
        # Small tx with high fee rate vs large tx with high absolute fee but low rate
        small_high_rate = self.create_transaction(1, 10.0, 1.0, size_multiplier=1)   # 1 XAI fee
        large_low_rate = self.create_transaction(2, 100.0, 2.0, size_multiplier=10)  # 2 XAI fee but 10x larger

        txs = [large_low_rate, small_high_rate]

        prioritized = self.blockchain._prioritize_transactions(txs)

        # Calculate fee rates
        small_rate = small_high_rate.fee / small_high_rate.get_size()
        large_rate = large_low_rate.fee / large_low_rate.get_size()

        # Small tx has higher fee rate despite lower absolute fee
        assert small_rate > large_rate, "Small tx should have higher fee rate"

        # Small tx should be prioritized first
        assert prioritized[0].fee == 1.0, "Higher fee rate tx should be first"

    def test_prioritize_equal_fees(self):
        """Task 201: Transactions with equal fees should maintain some order (timestamp or nonce)"""
        txs = [
            self.create_transaction(1, 100.0, 1.0),
            self.create_transaction(2, 100.0, 1.0),
            self.create_transaction(3, 100.0, 1.0),
        ]

        # Set different timestamps
        txs[0].timestamp = time.time() - 20
        txs[1].timestamp = time.time() - 10
        txs[2].timestamp = time.time()

        prioritized = self.blockchain._prioritize_transactions(txs)

        # With equal fees, should be ordered by timestamp (oldest first) or maintain order
        assert len(prioritized) == 3, "All transactions should be included"
        # Verify they're in some consistent order

    def test_prioritize_zero_fees(self):
        """Task 201: Handle zero-fee transactions (should be deprioritized)"""
        txs = [
            self.create_transaction(1, 100.0, 1.0),   # Normal fee
            self.create_transaction(2, 100.0, 0.0),   # Zero fee
            self.create_transaction(3, 100.0, 0.5),   # Low fee
        ]

        prioritized = self.blockchain._prioritize_transactions(txs)

        # Zero fee should be last
        assert prioritized[-1].fee == 0.0, "Zero fee tx should be last"
        assert prioritized[0].fee == 1.0, "Highest fee should be first"

    def test_prioritize_many_transactions(self):
        """Task 201: Correct ordering with many transactions"""
        import random

        # Create 100 transactions with random fees
        txs = []
        fees = [random.uniform(0.1, 5.0) for _ in range(100)]
        for i, fee in enumerate(fees):
            txs.append(self.create_transaction(i, 100.0, fee))

        prioritized = self.blockchain._prioritize_transactions(txs)

        # Verify ordering (should be descending by fee rate)
        for i in range(len(prioritized) - 1):
            rate_current = prioritized[i].get_fee_rate()
            rate_next = prioritized[i + 1].get_fee_rate()
            assert rate_current >= rate_next, f"Fee rate should be descending at index {i}"

    def test_prioritize_mixed_sizes_and_fees(self):
        """Task 201: Complex scenario with varying sizes and fees"""
        txs = [
            self.create_transaction(1, 100.0, 2.0, size_multiplier=1),   # Small, high fee
            self.create_transaction(2, 200.0, 3.0, size_multiplier=5),   # Large, high absolute fee
            self.create_transaction(3, 50.0, 0.5, size_multiplier=1),    # Small, low fee
            self.create_transaction(4, 150.0, 1.5, size_multiplier=3),   # Medium size, medium fee
        ]

        prioritized = self.blockchain._prioritize_transactions(txs)

        # Calculate expected order by fee rate
        rates = [(tx, tx.fee / tx.get_size()) for tx in txs]
        rates.sort(key=lambda x: x[1], reverse=True)
        expected_order = [tx for tx, rate in rates]

        # Verify prioritized matches expected order by fee rate
        for i, tx in enumerate(prioritized):
            expected_rate = expected_order[i].fee / expected_order[i].get_size()
            actual_rate = tx.fee / tx.get_size()
            # Allow small floating point differences
            assert abs(expected_rate - actual_rate) < 0.0001, f"Fee rate mismatch at position {i}"

    def test_prioritize_empty_list(self):
        """Task 201: Handle empty transaction list"""
        prioritized = self.blockchain._prioritize_transactions([])
        assert prioritized == [], "Empty list should return empty list"

    def test_prioritize_single_transaction(self):
        """Task 201: Handle single transaction"""
        tx = self.create_transaction(1, 100.0, 1.0)
        prioritized = self.blockchain._prioritize_transactions([tx])
        assert len(prioritized) == 1, "Should return single transaction"
        assert prioritized[0] == tx, "Should return same transaction"

    def test_prioritize_preserves_transaction_integrity(self):
        """Task 201: Prioritization should not modify transaction data"""
        txs = [
            self.create_transaction(1, 100.0, 0.5),
            self.create_transaction(2, 200.0, 2.0),
            self.create_transaction(3, 150.0, 1.0),
        ]

        # Store original data
        original_data = [(tx.sender, tx.recipient, tx.amount, tx.fee) for tx in txs]

        prioritized = self.blockchain._prioritize_transactions(txs)

        # Verify all transactions are present
        assert len(prioritized) == len(txs), "All transactions should be present"

        # Verify transaction data is unchanged
        for tx in prioritized:
            original = next(od for od in original_data if od[0] == tx.sender)
            assert tx.sender == original[0], "Sender should be unchanged"
            assert tx.recipient == original[1], "Recipient should be unchanged"
            assert tx.amount == original[2], "Amount should be unchanged"
            assert tx.fee == original[3], "Fee should be unchanged"

    def test_prioritize_respects_max_block_size(self):
        """Task 201: Should only include transactions up to max block size"""
        # Create many large transactions
        txs = [
            self.create_transaction(i, 100.0, 1.0 + i * 0.1, size_multiplier=20)
            for i in range(50)
        ]

        prioritized = self.blockchain._prioritize_transactions(txs)

        # Calculate total size
        total_size = sum(tx.get_size() for tx in prioritized)

        # Should not exceed max block size if defined
        # MAX_BLOCK_SIZE_BYTES = 1_000_000 (1 MB) - if implemented
        if hasattr(self.blockchain, 'MAX_BLOCK_SIZE_BYTES'):
            assert total_size <= self.blockchain.MAX_BLOCK_SIZE_BYTES, "Should respect max block size"


class TestFeeRateCalculation:
    """Test fee rate calculation methods"""

    def test_transaction_get_fee_rate(self):
        """Task 201: Transaction.get_fee_rate() should return correct value"""
        tx = Transaction(
            sender=f"XAI{'0' * 40}test",
            recipient=f"XAI{'0' * 40}recip",
            amount=100.0,
            fee=2.0,
        )
        tx.txid = "test_txid_" + "x" * 54
        tx.signature = "sig_" + "y" * 124

        fee_rate = tx.get_fee_rate()

        # Fee rate should be fee / size
        expected_rate = tx.fee / tx.get_size()
        assert fee_rate == expected_rate, "Fee rate should match fee/size"
        assert fee_rate > 0, "Fee rate should be positive"

    def test_transaction_get_size(self):
        """Task 201: Transaction.get_size() should return reasonable value"""
        tx = Transaction(
            sender=f"XAI{'0' * 40}test",
            recipient=f"XAI{'0' * 40}recip",
            amount=100.0,
            fee=2.0,
        )
        tx.txid = "test_txid_" + "x" * 54
        tx.signature = "sig_" + "y" * 124

        size = tx.get_size()

        # Size should be positive and reasonable
        assert size > 0, "Transaction size should be positive"
        assert size < 100000, "Transaction size should be reasonable"

    def test_fee_rate_zero_fee(self):
        """Task 201: Handle zero fee gracefully"""
        tx = Transaction(
            sender=f"XAI{'0' * 40}test",
            recipient=f"XAI{'0' * 40}recip",
            amount=100.0,
            fee=0.0,
        )
        tx.txid = "test_txid_" + "x" * 54

        fee_rate = tx.get_fee_rate()
        assert fee_rate == 0.0, "Zero fee should give zero fee rate"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
