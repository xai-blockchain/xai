"""
Comprehensive tests for address transaction index performance and correctness.

Tests cover:
- Index creation and initialization
- Transaction indexing on block addition
- O(log n) query performance
- Pagination support
- Chain reorganization handling
- Index rebuild from existing chain
"""

import pytest
import tempfile
import time
import os
from pathlib import Path

from xai.core.blockchain import Blockchain, Block
from xai.core.transaction import Transaction
from xai.core.chain.block_header import BlockHeader


class TestAddressIndex:
    """Test address transaction index functionality."""

    @pytest.fixture
    def temp_blockchain(self):
        """Create a temporary blockchain for testing."""
        temp_dir = tempfile.mkdtemp(prefix="xai_index_test_")
        bc = Blockchain(data_dir=temp_dir)
        yield bc
        # Cleanup
        try:
            bc.address_index.close()
        except Exception:
            pass

    def test_index_initialization(self, temp_blockchain):
        """Test that address index is initialized correctly."""
        bc = temp_blockchain
        assert bc.address_index is not None
        assert os.path.exists(os.path.join(bc.data_dir, "address_index.db"))

    def test_index_transaction_on_block_addition(self, temp_blockchain):
        """Test that coinbase transactions are indexed when blocks are mined."""
        bc = temp_blockchain

        # Use genesis-funded address as miner
        miner = "XAI6b7c3bb643c795f43e5c461f275e658b56566613"

        # Get initial transaction count for miner
        initial_count = bc.address_index.get_transaction_count(miner)

        # Mine a block - this creates a coinbase transaction for the miner
        bc.mine_pending_transactions(miner)

        # Verify coinbase transaction is indexed for miner (recipient)
        miner_txs = bc.address_index.get_transactions(miner, limit=20)
        assert len(miner_txs) > initial_count, "Miner should have new indexed transactions"

        # Verify at least one coinbase transaction was indexed
        found_coinbase = False
        for block_idx, tx_idx, txid, is_sender, amount, timestamp in miner_txs:
            # is_sender from SQLite is 0/1 integer, not Python bool
            # Coinbase: positive amount and not sender (is_sender == 0)
            if amount > 0 and not is_sender:  # Positive incoming amount = coinbase reward
                found_coinbase = True
                break

        assert found_coinbase, "Coinbase transaction not found in miner index"

        # Verify transaction count increased
        new_count = bc.address_index.get_transaction_count(miner)
        assert new_count > initial_count, "Transaction count should increase after mining"

    def test_query_performance(self, temp_blockchain):
        """Test that indexed queries are fast (O(log n) vs O(n²))."""
        bc = temp_blockchain

        # Use genesis-funded address
        miner = "XAI6b7c3bb643c795f43e5c461f275e658b56566613"

        # Create multiple blocks (each will have coinbase transaction)
        num_blocks = 20
        for i in range(num_blocks):
            bc.mine_pending_transactions(miner)

        # Measure query time for miner address
        start = time.time()
        window, total = bc.get_transaction_history_window(miner, limit=10, offset=0)
        query_time = time.time() - start

        # Should be very fast (< 100ms even on slow systems)
        assert query_time < 0.1, f"Query took {query_time}s - should be < 0.1s"

        # Verify correct count - miner should have genesis + coinbase rewards
        assert total > 0, "Should have indexed transactions"

    def test_pagination(self, temp_blockchain):
        """Test pagination support for large transaction histories."""
        bc = temp_blockchain

        miner = "XAI6b7c3bb643c795f43e5c461f275e658b56566613"

        # Create 15 blocks (each has coinbase transaction)
        num_blocks = 15
        for i in range(num_blocks):
            bc.mine_pending_transactions(miner)

        # Test pagination
        page1, total = bc.get_transaction_history_window(miner, limit=5, offset=0)
        page2, _ = bc.get_transaction_history_window(miner, limit=5, offset=5)
        page3, _ = bc.get_transaction_history_window(miner, limit=5, offset=10)

        assert len(page1) == 5, "First page should have 5 entries"
        assert len(page2) == 5, "Second page should have 5 entries"
        assert len(page3) <= 5, "Third page should have remaining entries"

        # Verify total count is correct (genesis + mined blocks)
        assert total >= num_blocks, "Total should include all transactions"

        # Verify no duplicates across pages
        page1_txids = {tx["txid"] for tx in page1}
        page2_txids = {tx["txid"] for tx in page2}
        assert len(page1_txids & page2_txids) == 0, "Pages should not overlap"

    def test_transaction_count(self, temp_blockchain):
        """Test transaction count accuracy."""
        bc = temp_blockchain

        miner = "XAI6b7c3bb643c795f43e5c461f275e658b56566613"
        unknown = "XAIzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz"

        # Unknown address should have 0
        assert bc.address_index.get_transaction_count(unknown) == 0

        # Mine some blocks
        num_blocks = 5
        for i in range(num_blocks):
            bc.mine_pending_transactions(miner)

        # Miner has: genesis transactions + coinbase rewards
        miner_count = bc.address_index.get_transaction_count(miner)
        assert miner_count >= num_blocks, f"Miner should have at least {num_blocks} transactions"

    def test_index_rebuild(self, temp_blockchain):
        """Test rebuilding index from existing chain."""
        bc = temp_blockchain

        miner = "XAI6b7c3bb643c795f43e5c461f275e658b56566613"

        # Mine some blocks
        for i in range(5):
            bc.mine_pending_transactions(miner)

        # Get initial count
        initial_count = bc.address_index.get_transaction_count(miner)
        assert initial_count > 0

        # Rebuild index
        bc.address_index.rebuild_from_chain(bc)

        # Count should be the same after rebuild
        rebuilt_count = bc.address_index.get_transaction_count(miner)
        assert rebuilt_count == initial_count, "Rebuild should maintain same count"

    def test_chain_reorganization_index_update(self, temp_blockchain):
        """Test that address index is updated correctly during chain reorg."""
        bc = temp_blockchain

        miner = "XAI6b7c3bb643c795f43e5c461f275e658b56566613"

        # Build initial chain (3 blocks)
        for i in range(3):
            bc.mine_pending_transactions(miner)

        initial_count = bc.address_index.get_transaction_count(miner)
        assert initial_count > 0, "Should have transactions initially"

        # Test rollback to block 2 (remove block 3)
        chain_length_before = len(bc.chain)
        bc.address_index.rollback_to_block(chain_length_before - 1)

        # Count should decrease
        after_rollback = bc.address_index.get_transaction_count(miner)
        assert after_rollback < initial_count, "Rollback should reduce transaction count"

    def test_empty_address_query(self, temp_blockchain):
        """Test querying address with no transactions."""
        bc = temp_blockchain

        unknown_address = "XAIzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz"

        # Should return empty results, not error
        window, total = bc.get_transaction_history_window(unknown_address, limit=10, offset=0)

        assert len(window) == 0, "Unknown address should have no transactions"
        assert total == 0, "Total count should be 0 for unknown address"

    def test_index_validation_errors(self, temp_blockchain):
        """Test that invalid parameters raise appropriate errors."""
        bc = temp_blockchain

        address = "XAIaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"

        # Negative limit should raise error
        with pytest.raises(ValueError, match="limit must be positive"):
            bc.get_transaction_history_window(address, limit=-1, offset=0)

        # Zero limit should raise error
        with pytest.raises(ValueError, match="limit must be positive"):
            bc.get_transaction_history_window(address, limit=0, offset=0)

        # Negative offset should raise error
        with pytest.raises(ValueError, match="offset cannot be negative"):
            bc.get_transaction_history_window(address, limit=10, offset=-5)

    def test_index_thread_safety(self, temp_blockchain):
        """Test that index operations are thread-safe."""
        bc = temp_blockchain

        miner = "XAI6b7c3bb643c795f43e5c461f275e658b56566613"

        # Mine a block
        bc.mine_pending_transactions(miner)

        # Multiple concurrent queries should not cause issues
        import threading

        results = []
        errors = []

        def query_index():
            try:
                window, total = bc.get_transaction_history_window(miner, limit=10, offset=0)
                results.append(len(window))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=query_index) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Concurrent queries should not error: {errors}"
        assert all(r > 0 for r in results), "All queries should return results"


class TestAddressIndexPerformance:
    """Performance benchmarks for address index."""

    @pytest.fixture
    def large_blockchain(self):
        """Create a blockchain with many blocks for performance testing."""
        temp_dir = tempfile.mkdtemp(prefix="xai_perf_test_")
        bc = Blockchain(data_dir=temp_dir)
        yield bc
        try:
            bc.address_index.close()
        except Exception:
            pass

    @pytest.mark.slow
    def test_large_chain_query_performance(self, large_blockchain):
        """Test query performance on larger chain (50+ blocks)."""
        bc = large_blockchain

        miner = "XAI6b7c3bb643c795f43e5c461f275e658b56566613"

        # Create 50 blocks
        num_blocks = 50
        for i in range(num_blocks):
            bc.mine_pending_transactions(miner)

        # Measure query time
        start = time.time()
        window, total = bc.get_transaction_history_window(miner, limit=100, offset=0)
        query_time = time.time() - start

        # Should be very fast even with 50+ blocks
        assert query_time < 0.2, f"Query took {query_time}s - should be < 0.2s for 50 blocks"
        assert total >= num_blocks, "Should have all transactions indexed"

        print(f"\nPerformance: Queried {total} transactions in {query_time*1000:.2f}ms")
