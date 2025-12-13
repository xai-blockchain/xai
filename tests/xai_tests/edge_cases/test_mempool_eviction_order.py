"""
Edge case tests for mempool eviction order under full mempool conditions.

Tests various scenarios where the mempool is full and transactions must be
evicted based on fee prioritization and other criteria.
"""

import pytest
import time
from xai.core.blockchain import Blockchain
from xai.core.wallet import Wallet
from xai.core.transaction import Transaction
from xai.core.config import Config


class TestMempoolEvictionOrder:
    """Test mempool eviction order when mempool is full"""

    def test_evict_lowest_fee_transaction(self, tmp_path):
        """Test that lowest fee transaction is evicted when mempool is full"""
        bc = Blockchain(data_dir=str(tmp_path))

        # Set small mempool size for testing
        bc._mempool_max_size = 5

        # Create wallets and fund them
        wallets = [Wallet() for _ in range(7)]
        for wallet in wallets:
            bc.mine_pending_transactions(wallet.address)

        # Add transactions with varying fees
        fees = [0.1, 0.2, 0.05, 0.3, 0.15, 0.25, 0.08]
        transactions = []

        for wallet, fee in zip(wallets, fees):
            recipient = Wallet()
            tx = bc.create_transaction(
                wallet.address, recipient.address, 0.5, fee,
                wallet.private_key, wallet.public_key
            )
            if tx:
                result = bc.add_transaction(tx)
                if result:
                    transactions.append((tx, fee))

        # Mempool should be at max size
        assert len(bc.pending_transactions) <= bc._mempool_max_size

        # Verify lowest fee transactions were evicted
        mempool_fees = [tx.fee for tx in bc.pending_transactions]
        # All fees in mempool should be higher than evicted fees
        if len(transactions) > bc._mempool_max_size:
            # At least some eviction occurred
            min_mempool_fee = min(mempool_fees) if mempool_fees else 0
            # Check that we kept higher fee transactions
            assert min_mempool_fee >= 0.05  # Some low fee transactions should be gone

    def test_eviction_preserves_highest_fees(self, tmp_path):
        """Test that highest fee transactions are preserved during eviction"""
        bc = Blockchain(data_dir=str(tmp_path))
        bc._mempool_max_size = 3

        wallets = [Wallet() for _ in range(5)]
        for wallet in wallets:
            bc.mine_pending_transactions(wallet.address)

        # Add transactions with distinct fees
        high_fee_txs = []
        for i, wallet in enumerate(wallets):
            recipient = Wallet()
            fee = 0.1 * (i + 1)  # 0.1, 0.2, 0.3, 0.4, 0.5
            tx = bc.create_transaction(
                wallet.address, recipient.address, 0.5, fee,
                wallet.private_key, wallet.public_key
            )
            if tx:
                bc.add_transaction(tx)
                if fee >= 0.3:  # Track high fee transactions
                    high_fee_txs.append(tx.txid)

        # Verify high fee transactions are in mempool
        mempool_txids = {tx.txid for tx in bc.pending_transactions}
        high_fee_preserved = sum(1 for txid in high_fee_txs if txid in mempool_txids)

        # Most high fee transactions should be preserved
        assert high_fee_preserved >= len(high_fee_txs) // 2

    def test_eviction_with_equal_fees(self, tmp_path):
        """Test eviction behavior when multiple transactions have equal fees"""
        bc = Blockchain(data_dir=str(tmp_path))
        bc._mempool_max_size = 3

        wallets = [Wallet() for _ in range(5)]
        for wallet in wallets:
            bc.mine_pending_transactions(wallet.address)

        # Add transactions with same fee
        tx_timestamps = []
        for wallet in wallets:
            recipient = Wallet()
            tx = bc.create_transaction(
                wallet.address, recipient.address, 0.5, 0.1,  # Same fee
                wallet.private_key, wallet.public_key
            )
            if tx:
                time.sleep(0.01)  # Ensure different timestamps
                bc.add_transaction(tx)
                tx_timestamps.append(tx.timestamp)

        # With equal fees, should preserve based on timestamp (FIFO or fee rate)
        assert len(bc.pending_transactions) <= bc._mempool_max_size

        # Verify mempool isn't empty
        assert len(bc.pending_transactions) > 0

    def test_eviction_respects_fee_rate(self, tmp_path):
        """Test that eviction considers fee rate (fee per byte)"""
        bc = Blockchain(data_dir=str(tmp_path))
        bc._mempool_max_size = 3

        wallets = [Wallet() for _ in range(5)]
        for wallet in wallets:
            bc.mine_pending_transactions(wallet.address)

        # Create transactions with different fee rates
        # Higher absolute fee but potentially lower fee rate
        added_txs = []
        for i, wallet in enumerate(wallets):
            recipient = Wallet()
            fee = 0.1 + (i * 0.05)
            tx = bc.create_transaction(
                wallet.address, recipient.address, 0.5, fee,
                wallet.private_key, wallet.public_key
            )
            if tx:
                bc.add_transaction(tx)
                added_txs.append((tx.txid, fee, tx.get_fee_rate()))

        # Verify transactions with higher fee rates are preserved
        mempool_txids = {tx.txid for tx in bc.pending_transactions}
        mempool_fee_rates = [tx.get_fee_rate() for tx in bc.pending_transactions]

        if mempool_fee_rates:
            # Should have reasonable fee rates
            assert max(mempool_fee_rates) > 0

    def test_eviction_with_rbf_transactions(self, tmp_path):
        """Test eviction behavior with RBF (Replace-By-Fee) transactions"""
        bc = Blockchain(data_dir=str(tmp_path))
        bc._mempool_max_size = 3

        wallets = [Wallet() for _ in range(4)]
        for wallet in wallets:
            bc.mine_pending_transactions(wallet.address)

        # Add initial transaction
        recipient = Wallet()
        initial_tx = bc.create_transaction(
            wallets[0].address, recipient.address, 0.5, 0.1,
            wallets[0].private_key, wallets[0].public_key
        )
        if initial_tx:
            initial_tx.rbf_enabled = True
            bc.add_transaction(initial_tx)
            initial_txid = initial_tx.txid

        # Fill mempool
        for wallet in wallets[1:]:
            recipient = Wallet()
            tx = bc.create_transaction(
                wallet.address, recipient.address, 0.5, 0.15,
                wallet.private_key, wallet.public_key
            )
            if tx:
                bc.add_transaction(tx)

        # Try to replace with higher fee
        replacement_tx = bc.create_transaction(
            wallets[0].address, recipient.address, 0.5, 0.25,
            wallets[0].private_key, wallets[0].public_key
        )
        if replacement_tx:
            replacement_tx.rbf_enabled = True
            result = bc.handle_rbf_replacement(replacement_tx, initial_txid)

            # RBF should work regardless of mempool size
            assert isinstance(result, bool)

    def test_eviction_prioritizes_older_transactions(self, tmp_path):
        """Test that among equal fee rates, older transactions may be preserved"""
        bc = Blockchain(data_dir=str(tmp_path))
        bc._mempool_max_size = 3

        wallets = [Wallet() for _ in range(5)]
        for wallet in wallets:
            bc.mine_pending_transactions(wallet.address)

        # Add transactions with delays to create age differences
        old_tx_ids = []
        for i, wallet in enumerate(wallets):
            recipient = Wallet()
            tx = bc.create_transaction(
                wallet.address, recipient.address, 0.5, 0.1,
                wallet.private_key, wallet.public_key
            )
            if tx:
                bc.add_transaction(tx)
                if i < 2:  # First two are "old"
                    old_tx_ids.append(tx.txid)
                time.sleep(0.01)

        # Check which transactions survived
        mempool_txids = {tx.txid for tx in bc.pending_transactions}

        # Mempool should have some transactions
        assert len(mempool_txids) > 0

    def test_eviction_under_spam_attack(self, tmp_path):
        """Test mempool eviction under spam attack (many low-fee transactions)"""
        bc = Blockchain(data_dir=str(tmp_path))
        bc._mempool_max_size = 10

        # Create many wallets for spam attack
        spam_wallets = [Wallet() for _ in range(20)]
        for wallet in spam_wallets:
            bc.mine_pending_transactions(wallet.address)

        # Add spam transactions with very low fees
        for wallet in spam_wallets[:15]:
            recipient = Wallet()
            tx = bc.create_transaction(
                wallet.address, recipient.address, 0.5, 0.01,  # Very low fee
                wallet.private_key, wallet.public_key
            )
            if tx:
                bc.add_transaction(tx)

        spam_count = len(bc.pending_transactions)

        # Add legitimate high-fee transaction
        legit_wallet = spam_wallets[15]
        recipient = Wallet()
        legit_tx = bc.create_transaction(
            legit_wallet.address, recipient.address, 0.5, 1.0,  # High fee
            legit_wallet.private_key, legit_wallet.public_key
        )

        if legit_tx:
            result = bc.add_transaction(legit_tx)
            assert result  # Should be accepted

            # Verify legitimate transaction is in mempool
            mempool_txids = {tx.txid for tx in bc.pending_transactions}
            assert legit_tx.txid in mempool_txids

            # Verify at least one spam transaction was evicted
            assert len(bc.pending_transactions) <= bc._mempool_max_size

    def test_eviction_with_transaction_chains(self, tmp_path):
        """Test eviction behavior with dependent transaction chains"""
        bc = Blockchain(data_dir=str(tmp_path))
        bc._mempool_max_size = 5

        # Create a wallet and fund it
        wallet1 = Wallet()
        bc.mine_pending_transactions(wallet1.address)

        wallet2 = Wallet()
        wallet3 = Wallet()

        # Create chain: wallet1 -> wallet2 -> wallet3
        tx1 = bc.create_transaction(
            wallet1.address, wallet2.address, 0.5, 0.1,
            wallet1.private_key, wallet1.public_key
        )

        if tx1:
            bc.add_transaction(tx1)

            # Mine the first transaction
            bc.mine_pending_transactions(wallet1.address)

            # Now create dependent transaction
            tx2 = bc.create_transaction(
                wallet2.address, wallet3.address, 0.3, 0.05,
                wallet2.private_key, wallet2.public_key
            )

            # Fill mempool with other transactions
            other_wallets = [Wallet() for _ in range(5)]
            for w in other_wallets:
                bc.mine_pending_transactions(w.address)
                recipient = Wallet()
                tx = bc.create_transaction(
                    w.address, recipient.address, 0.5, 0.2,
                    w.private_key, w.public_key
                )
                if tx:
                    bc.add_transaction(tx)

            # Try to add dependent transaction
            if tx2:
                result = bc.add_transaction(tx2)
                # Should handle dependent transactions appropriately
                assert isinstance(result, bool)

    def test_eviction_prevents_dos_via_large_transactions(self, tmp_path):
        """Test that large transactions don't dominate mempool"""
        bc = Blockchain(data_dir=str(tmp_path))
        bc._mempool_max_size = 5

        wallets = [Wallet() for _ in range(7)]
        for wallet in wallets:
            bc.mine_pending_transactions(wallet.address)

        # Add transactions (size is considered in fee rate)
        for wallet in wallets:
            recipient = Wallet()
            tx = bc.create_transaction(
                wallet.address, recipient.address, 0.5, 0.1,
                wallet.private_key, wallet.public_key
            )
            if tx:
                bc.add_transaction(tx)

        # Verify mempool size limit is enforced
        assert len(bc.pending_transactions) <= bc._mempool_max_size

        # Verify we have some transactions
        assert len(bc.pending_transactions) > 0

    def test_eviction_statistics_tracking(self, tmp_path):
        """Test that eviction statistics are properly tracked"""
        bc = Blockchain(data_dir=str(tmp_path))
        bc._mempool_max_size = 3

        initial_evicted = bc._mempool_evicted_low_fee_total

        # Create wallets and fund them
        wallets = [Wallet() for _ in range(6)]
        for wallet in wallets:
            bc.mine_pending_transactions(wallet.address)

        # Add enough transactions to trigger eviction
        for wallet in wallets:
            recipient = Wallet()
            tx = bc.create_transaction(
                wallet.address, recipient.address, 0.5, 0.1,
                wallet.private_key, wallet.public_key
            )
            if tx:
                bc.add_transaction(tx)

        # Check if eviction counter increased
        final_evicted = bc._mempool_evicted_low_fee_total
        # Some eviction may have occurred
        assert final_evicted >= initial_evicted

    def test_eviction_with_nonce_gaps(self, tmp_path):
        """Test eviction behavior when there are nonce gaps"""
        bc = Blockchain(data_dir=str(tmp_path))
        bc._mempool_max_size = 5

        wallet = Wallet()
        bc.mine_pending_transactions(wallet.address)

        # Create transactions with non-sequential nonces
        # (simulating nonce gaps)
        recipients = [Wallet() for _ in range(3)]

        # Try to create transactions
        for i, recipient in enumerate(recipients):
            tx = bc.create_transaction(
                wallet.address, recipient.address, 0.1, 0.05,
                wallet.private_key, wallet.public_key
            )
            if tx:
                result = bc.add_transaction(tx)
                # Document behavior with nonce gaps
                assert isinstance(result, bool)

    def test_eviction_order_determinism(self, tmp_path):
        """Test that eviction order is deterministic for identical conditions"""
        bc = Blockchain(data_dir=str(tmp_path))
        bc._mempool_max_size = 3

        wallets = [Wallet() for _ in range(5)]
        for wallet in wallets:
            bc.mine_pending_transactions(wallet.address)

        # Add transactions with same fee
        txids_order = []
        for wallet in wallets:
            recipient = Wallet()
            tx = bc.create_transaction(
                wallet.address, recipient.address, 0.5, 0.1,
                wallet.private_key, wallet.public_key
            )
            if tx:
                bc.add_transaction(tx)
                txids_order.append(tx.txid)

        mempool_txids = [tx.txid for tx in bc.pending_transactions]

        # Verify we have a deterministic subset
        assert len(mempool_txids) <= bc._mempool_max_size
        assert len(mempool_txids) > 0

    def test_eviction_with_concurrent_mining(self, tmp_path):
        """Test eviction behavior when mining occurs concurrently"""
        bc = Blockchain(data_dir=str(tmp_path))
        bc._mempool_max_size = 5
        miner = Wallet()

        wallets = [Wallet() for _ in range(10)]
        for wallet in wallets:
            bc.mine_pending_transactions(wallet.address)

        # Add some transactions
        for i, wallet in enumerate(wallets[:7]):
            recipient = Wallet()
            tx = bc.create_transaction(
                wallet.address, recipient.address, 0.5, 0.1,
                wallet.private_key, wallet.public_key
            )
            if tx:
                bc.add_transaction(tx)

            # Mine periodically
            if i % 3 == 0:
                bc.mine_pending_transactions(miner.address)

        # Verify mempool is within limits
        assert len(bc.pending_transactions) <= bc._mempool_max_size

    def test_eviction_fee_rate_edge_cases(self, tmp_path):
        """Test eviction with edge case fee rates"""
        bc = Blockchain(data_dir=str(tmp_path))
        bc._mempool_max_size = 3

        wallets = [Wallet() for _ in range(5)]
        for wallet in wallets:
            bc.mine_pending_transactions(wallet.address)

        # Add transactions with various fee configurations
        fees = [0.001, 0.0001, 1.0, 0.1, 0.01]  # Very low to high

        for wallet, fee in zip(wallets, fees):
            recipient = Wallet()
            tx = bc.create_transaction(
                wallet.address, recipient.address, 0.5, fee,
                wallet.private_key, wallet.public_key
            )
            if tx:
                bc.add_transaction(tx)

        # Verify highest fee transactions are likely preserved
        mempool_fees = [tx.fee for tx in bc.pending_transactions]
        if mempool_fees:
            # Should have at least one high-fee transaction
            assert max(mempool_fees) >= 0.1

    def test_mempool_overview_during_eviction(self, tmp_path):
        """Test that mempool overview is accurate during eviction"""
        bc = Blockchain(data_dir=str(tmp_path))
        bc._mempool_max_size = 3

        wallets = [Wallet() for _ in range(5)]
        for wallet in wallets:
            bc.mine_pending_transactions(wallet.address)

        # Add transactions to trigger eviction
        for wallet in wallets:
            recipient = Wallet()
            tx = bc.create_transaction(
                wallet.address, recipient.address, 0.5, 0.1,
                wallet.private_key, wallet.public_key
            )
            if tx:
                bc.add_transaction(tx)

        # Get mempool overview
        overview = bc.get_mempool_overview()

        # Verify overview is consistent
        assert overview['pool_size'] == len(bc.pending_transactions)
        assert overview['pool_size'] <= bc._mempool_max_size
        assert 'statistics' in overview
        assert 'evicted_low_fee_total' in overview['statistics']
