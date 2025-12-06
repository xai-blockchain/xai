"""
Test concurrent double-spend prevention in mempool.

This test verifies that the TOCTOU vulnerability fix in add_transaction()
properly prevents race conditions where two threads could both validate
transactions spending the same UTXO and both add them to the mempool.
"""

import threading
import time
from typing import List
import pytest

from xai.core.blockchain import Blockchain
from xai.core.transaction import Transaction
from xai.core.wallet import Wallet


class TestMempoolConcurrentDoubleSpend:
    """Test concurrent transaction submission to detect double-spend races."""

    @pytest.fixture
    def blockchain(self, tmp_path):
        """Create a fresh blockchain for testing."""
        bc = Blockchain(data_dir=str(tmp_path))
        # Mine some blocks to create UTXOs for testing
        wallet = Wallet()
        for _ in range(5):
            bc.mine_pending_transactions(wallet.address)
        return bc

    @pytest.mark.skip(reason="Simplified test - covered by other tests")
    def test_concurrent_double_spend_prevented(self, blockchain):
        """
        Test that concurrent transaction submissions maintain mempool consistency.
        (Skipped - test_concurrent_same_utxo_double_spend provides better coverage)
        """
        pass

    def test_concurrent_same_utxo_double_spend(self, blockchain):
        """
        Test that concurrent transactions explicitly spending the same UTXO are rejected.

        This is a more direct test where both transactions explicitly reference
        the same UTXO inputs, ensuring one is rejected.
        """
        # Create wallets
        wallet1 = Wallet()
        wallet2 = Wallet()

        # Give wallet1 some funds
        blockchain.mine_pending_transactions(wallet1.address)
        time.sleep(0.1)

        # Get available UTXOs
        utxos = blockchain.utxo_manager.get_utxos_for_address(wallet1.address)
        assert len(utxos) > 0, "Should have UTXOs"

        # Pick the first UTXO to spend
        utxo = utxos[0]

        # Create two transactions that explicitly spend the SAME UTXO
        tx1 = Transaction(
            sender=wallet1.address,
            recipient=wallet2.address,
            amount=1.0,
            fee=0.01,
            tx_type="transfer",
            nonce=0
        )
        tx1.inputs = [{"txid": utxo["txid"], "vout": utxo["vout"]}]
        tx1.outputs = [
            {"address": wallet2.address, "amount": 1.0},
            {"address": wallet1.address, "amount": utxo["amount"] - 1.01}  # change
        ]
        tx1.sign_transaction(wallet1.private_key)

        tx2 = Transaction(
            sender=wallet1.address,
            recipient=wallet2.address,
            amount=2.0,
            fee=0.01,
            tx_type="transfer",
            nonce=0  # Same nonce to force conflict
        )
        tx2.inputs = [{"txid": utxo["txid"], "vout": utxo["vout"]}]  # SAME UTXO
        tx2.outputs = [
            {"address": wallet2.address, "amount": 2.0},
            {"address": wallet1.address, "amount": utxo["amount"] - 2.01}  # change
        ]
        tx2.sign_transaction(wallet1.private_key)

        # Track results
        results = []
        errors = []

        def submit_transaction(tx, result_list, error_list):
            """Submit a transaction and record the result."""
            try:
                result = blockchain.add_transaction(tx)
                result_list.append(result)
            except Exception as e:
                error_list.append(e)

        # Submit both transactions concurrently
        threads = []
        for tx in [tx1, tx2]:
            thread = threading.Thread(
                target=submit_transaction,
                args=(tx, results, errors)
            )
            threads.append(thread)

        # Start all threads at the same time
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=5)

        # Verify no exceptions occurred
        assert len(errors) == 0, f"Unexpected errors: {errors}"
        assert len(results) == 2, "Should have 2 results"

        # CRITICAL: Only ONE transaction should succeed (the race is prevented)
        success_count = sum(1 for r in results if r)
        assert success_count == 1, \
            f"Expected exactly 1 successful transaction, got {success_count}. " \
            f"This indicates a TOCTOU vulnerability!"

        # Verify mempool has exactly one transaction
        assert len(blockchain.pending_transactions) == 1, \
            "Mempool should contain exactly 1 transaction"

    def test_high_concurrency_stress(self, blockchain):
        """
        Stress test with many concurrent transactions to verify thread safety.

        This test ensures the lock doesn't cause deadlocks or race conditions
        under high concurrent load.
        """
        # Create multiple wallets with funds
        wallets = [Wallet() for _ in range(10)]

        # Give each wallet some funds
        for wallet in wallets:
            blockchain.mine_pending_transactions(wallet.address)

        time.sleep(0.1)

        # Create many transactions from different wallets using blockchain method
        recipient = Wallet()
        transactions = []

        for wallet in wallets:
            tx = blockchain.create_transaction(
                sender_address=wallet.address,
                recipient_address=recipient.address,
                amount=0.5,
                fee=0.01,
                private_key=wallet.private_key
            )
            if tx:  # Only add if creation succeeded
                transactions.append(tx)

        # Submit all transactions concurrently
        results = []
        errors = []

        def submit_transaction(tx, result_list, error_list):
            """Submit a transaction and record the result."""
            try:
                result = blockchain.add_transaction(tx)
                result_list.append(result)
            except Exception as e:
                error_list.append(e)

        threads = []
        for tx in transactions:
            thread = threading.Thread(
                target=submit_transaction,
                args=(tx, results, errors)
            )
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join(timeout=10)

        # Verify no exceptions or deadlocks
        assert len(errors) == 0, f"Unexpected errors: {errors}"
        assert len(results) == len(transactions), "All transactions should complete"

        # At least some should succeed (they're from different wallets)
        success_count = sum(1 for r in results if r)
        assert success_count >= len(transactions) // 2, \
            "At least half of transactions from different wallets should succeed"

        # Verify mempool consistency
        assert len(blockchain.pending_transactions) == success_count, \
            "Mempool size should match successful transactions"

    def test_lock_release_on_error(self, blockchain):
        """
        Test that the lock is properly released even when validation fails.

        This ensures the 'with' statement properly releases the lock in all cases.
        """
        wallet1 = Wallet()
        wallet2 = Wallet()

        # Create an invalid transaction using a wallet with no funds
        # This should fail validation
        invalid_tx = blockchain.create_transaction(
            sender_address=wallet1.address,
            recipient_address=wallet2.address,
            amount=1000.0,  # More than available (wallet has no funds)
            fee=0.01,
            private_key=wallet1.private_key
        )

        # Transaction creation itself may return None for invalid tx
        if invalid_tx:
            # Submit the invalid transaction
            result = blockchain.add_transaction(invalid_tx)
            # Should fail since wallet has no funds

        # Now give wallet1 some funds and submit a valid transaction
        blockchain.mine_pending_transactions(wallet1.address)
        time.sleep(0.1)

        valid_tx = blockchain.create_transaction(
            sender_address=wallet1.address,
            recipient_address=wallet2.address,
            amount=1.0,
            fee=0.01,
            private_key=wallet1.private_key
        )

        assert valid_tx is not None, "Valid transaction creation should succeed"

        # This should succeed, proving the lock was released after the previous failure
        result = blockchain.add_transaction(valid_tx)
        assert result is True, "Valid transaction should succeed after previous failure"
