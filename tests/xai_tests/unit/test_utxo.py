"""
Test UTXO Double-Spend Window Fix (TODO 005)

Tests that UTXO locking prevents concurrent double-spend attacks
through proper lock management across transaction lifecycle.
"""

import pytest
import threading
import time
from xai.core.blockchain import Blockchain
from xai.core.wallet import Wallet
from xai.core.transactions.utxo_manager import UTXOManager


class TestUTXODoubleSpendWindow:
    """Test UTXO locking prevents TOCTOU race conditions"""

    def test_concurrent_double_spend_prevented(self, tmp_path):
        """
        Test that concurrent attempts to spend same UTXO are prevented by locking.

        This tests the fix for TODO 005: UTXO Double-Spend Window.
        The race condition is prevented by:
        1. Locking UTXOs immediately when selected in create_transaction
        2. Keeping locks held through validation and mempool insertion
        3. Releasing locks only when transaction is rejected or mined
        """
        bc = Blockchain(data_dir=str(tmp_path))
        wallet1 = Wallet()
        wallet2 = Wallet()
        wallet3 = Wallet()

        # Mine to get funds for wallet1
        bc.mine_pending_transactions(wallet1.address)
        initial_balance = bc.get_balance(wallet1.address)
        assert initial_balance > 10.0

        # Track which transactions succeeded
        results = {"tx1": None, "tx2": None}
        errors = []

        def create_tx1():
            """Try to spend wallet1's UTXOs to wallet2"""
            try:
                tx = bc.create_transaction(
                    wallet1.address, wallet2.address,
                    initial_balance - 1.0, 0.5,
                    wallet1.private_key, wallet1.public_key
                )
                if tx:
                    # Try to add to mempool
                    added = bc.add_transaction(tx)
                    results["tx1"] = tx if added else None
                else:
                    results["tx1"] = None
            except Exception as e:
                errors.append(("tx1", e))

        def create_tx2():
            """Try to spend same UTXOs to wallet3 (should fail)"""
            try:
                tx = bc.create_transaction(
                    wallet1.address, wallet3.address,
                    initial_balance - 1.0, 0.5,
                    wallet1.private_key, wallet1.public_key
                )
                if tx:
                    # Try to add to mempool
                    added = bc.add_transaction(tx)
                    results["tx2"] = tx if added else None
                else:
                    results["tx2"] = None
            except Exception as e:
                errors.append(("tx2", e))

        # Start both threads at nearly same time
        thread1 = threading.Thread(target=create_tx1)
        thread2 = threading.Thread(target=create_tx2)

        thread1.start()
        thread2.start()

        thread1.join()
        thread2.join()

        # Check results
        if errors:
            pytest.fail(f"Unexpected errors: {errors}")

        # Exactly one transaction should succeed, one should fail
        success_count = sum(1 for tx in results.values() if tx is not None)
        assert success_count == 1, (
            f"Expected exactly 1 transaction to succeed, got {success_count}. "
            f"tx1={results['tx1']}, tx2={results['tx2']}"
        )

        # The successful transaction should be in mempool
        assert len(bc.pending_transactions) == 1

    def test_utxo_lock_timeout(self, tmp_path):
        """Test that UTXO locks expire after timeout"""
        manager = UTXOManager()

        # Override timeout to 1 second for testing
        manager._pending_timeout = 1.0

        # Add a UTXO
        manager.add_utxo("XAI123", "tx_abc", 0, 10.0, "script")

        # Get and lock the UTXO
        utxos = manager.get_utxos_for_address("XAI123", exclude_pending=False)
        assert len(utxos) == 1

        # Lock it
        assert manager.lock_utxos(utxos) is True

        # Should be locked now
        available = manager.get_utxos_for_address("XAI123", exclude_pending=True)
        assert len(available) == 0

        # Wait for timeout
        time.sleep(1.5)

        # Should be unlocked after timeout
        available = manager.get_utxos_for_address("XAI123", exclude_pending=True)
        assert len(available) == 1

    def test_utxo_lock_prevents_double_lock(self, tmp_path):
        """Test that already locked UTXOs cannot be locked again"""
        manager = UTXOManager()

        # Add a UTXO
        manager.add_utxo("XAI123", "tx_abc", 0, 10.0, "script")

        # Get the UTXO
        utxos = manager.get_utxos_for_address("XAI123", exclude_pending=False)
        assert len(utxos) == 1

        # Lock it
        assert manager.lock_utxos(utxos) is True

        # Try to lock again (should fail)
        assert manager.lock_utxos(utxos) is False

    def test_utxo_unlock_on_transaction_rejection(self, tmp_path):
        """Test that UTXOs are unlocked when transaction is rejected"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet1 = Wallet()
        wallet2 = Wallet()

        # Mine to get funds
        bc.mine_pending_transactions(wallet1.address)
        initial_balance = bc.get_balance(wallet1.address)

        # Get initial pending UTXO count
        initial_pending = bc.utxo_manager.get_pending_utxo_count()

        # Create a valid transaction
        tx1 = bc.create_transaction(
            wallet1.address, wallet2.address,
            5.0, 0.1,
            wallet1.private_key, wallet1.public_key
        )

        assert tx1 is not None

        # UTXOs should be locked now
        locked_count = bc.utxo_manager.get_pending_utxo_count()
        assert locked_count > initial_pending

        # Try to create invalid transaction (amount too high)
        # This should fail and NOT lock any UTXOs
        tx2 = bc.create_transaction(
            wallet1.address, wallet2.address,
            initial_balance * 10, 0.1,
            wallet1.private_key, wallet1.public_key
        )

        assert tx2 is None

        # Locked count should remain same (only tx1's UTXOs locked)
        assert bc.utxo_manager.get_pending_utxo_count() == locked_count

    def test_utxo_unlock_on_mining(self, tmp_path):
        """Test that UTXOs are unlocked when transaction is mined"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet1 = Wallet()
        wallet2 = Wallet()

        # Mine to get funds
        bc.mine_pending_transactions(wallet1.address)

        # Create transaction (locks UTXOs)
        tx = bc.create_transaction(
            wallet1.address, wallet2.address,
            5.0, 0.1,
            wallet1.private_key, wallet1.public_key
        )

        assert tx is not None

        # Add to mempool
        bc.add_transaction(tx)

        # UTXOs should be locked
        locked_count_before = bc.utxo_manager.get_pending_utxo_count()
        assert locked_count_before > 0

        # Mine the transaction
        bc.mine_pending_transactions(wallet1.address)

        # UTXOs should be unlocked (or at least reduced count)
        locked_count_after = bc.utxo_manager.get_pending_utxo_count()
        # After mining, pending mempool is cleared, so locks should be released
        assert locked_count_after < locked_count_before or locked_count_after == 0

    def test_get_utxos_excludes_pending_by_default(self, tmp_path):
        """Test that get_utxos_for_address excludes pending UTXOs by default"""
        manager = UTXOManager()

        # Add UTXOs
        manager.add_utxo("XAI123", "tx1", 0, 10.0, "script")
        manager.add_utxo("XAI123", "tx2", 0, 20.0, "script")

        # Should get both
        all_utxos = manager.get_utxos_for_address("XAI123", exclude_pending=False)
        assert len(all_utxos) == 2

        # Lock one
        manager.lock_utxos([all_utxos[0]])

        # Default should exclude pending
        available = manager.get_utxos_for_address("XAI123")
        assert len(available) == 1

        # With exclude_pending=False, should get both
        all_again = manager.get_utxos_for_address("XAI123", exclude_pending=False)
        assert len(all_again) == 2

    def test_reset_clears_pending_locks(self, tmp_path):
        """Test that reset() clears pending UTXO locks"""
        manager = UTXOManager()

        # Add and lock UTXO
        manager.add_utxo("XAI123", "tx1", 0, 10.0, "script")
        utxos = manager.get_utxos_for_address("XAI123", exclude_pending=False)
        manager.lock_utxos(utxos)

        assert manager.get_pending_utxo_count() == 1

        # Reset should clear locks
        manager.reset()

        assert manager.get_pending_utxo_count() == 0

    def test_clear_clears_pending_locks(self, tmp_path):
        """Test that clear() clears pending UTXO locks"""
        manager = UTXOManager()

        # Add and lock UTXO
        manager.add_utxo("XAI123", "tx1", 0, 10.0, "script")
        utxos = manager.get_utxos_for_address("XAI123", exclude_pending=False)
        manager.lock_utxos(utxos)

        assert manager.get_pending_utxo_count() == 1

        # Clear should clear locks
        manager.clear()

        assert manager.get_pending_utxo_count() == 0

    def test_multiple_threads_sequential_success(self, tmp_path):
        """Test that sequential transactions from different threads succeed"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet1 = Wallet()
        wallet2 = Wallet()
        wallet3 = Wallet()

        # Mine multiple blocks to get multiple UTXOs
        for _ in range(3):
            bc.mine_pending_transactions(wallet1.address)

        balance = bc.get_balance(wallet1.address)
        assert balance > 20.0

        results = []

        def create_tx(recipient, amount):
            tx = bc.create_transaction(
                wallet1.address, recipient,
                amount, 0.1,
                wallet1.private_key, wallet1.public_key
            )
            if tx:
                bc.add_transaction(tx)
            results.append(tx)

        # Create transactions sequentially but from different threads
        thread1 = threading.Thread(target=create_tx, args=(wallet2.address, 5.0))
        thread1.start()
        thread1.join()

        # Short delay to ensure first transaction is fully processed
        time.sleep(0.1)

        thread2 = threading.Thread(target=create_tx, args=(wallet3.address, 5.0))
        thread2.start()
        thread2.join()

        # Both should succeed as they're sequential
        assert len(results) == 2
        assert all(tx is not None for tx in results)
        assert len(bc.pending_transactions) == 2
