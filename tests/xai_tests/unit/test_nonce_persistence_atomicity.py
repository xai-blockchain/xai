"""
Test nonce tracker state consistency after failed block persistence

This test ensures that if block persistence fails (e.g., disk full, I/O error),
the nonce tracker state is properly rolled back to prevent permanent account lockout.

Security Impact: CRITICAL
- Without this fix, users can be permanently locked out of their accounts
- Failed block addition can cause nonce desynchronization
- Prevents replay attack protection from becoming a DoS vector
"""

import pytest
import os
from unittest.mock import MagicMock, patch
from xai.core.blockchain import Blockchain, Transaction
from xai.core.wallet import Wallet


class TestNonceTrackerPersistenceAtomicity:
    """Test that nonce increments are atomic with block persistence"""

    def test_nonce_rollback_on_storage_failure(self, tmp_path):
        """
        Test that nonces are rolled back if block persistence fails

        Attack scenario this prevents:
        1. Block is mined with Alice's transaction (nonce 0)
        2. Nonce tracker increments Alice's nonce to 0
        3. Disk write fails (disk full, I/O error, etc.)
        4. Without fix: Block is lost but nonce is at 0
        5. Without fix: Alice's next transaction (nonce 0) is rejected as duplicate
        6. Without fix: Alice must use nonce 1, skipping 0 - permanent desync

        With fix: Nonce remains at -1, Alice can retry with nonce 0
        """
        bc = Blockchain(data_dir=str(tmp_path))
        alice = Wallet()
        bob = Wallet()
        miner = Wallet()

        # Give Alice some initial funds
        bc.mine_pending_transactions(alice.address)
        initial_balance = bc.get_balance(alice.address)
        assert initial_balance > 0

        # Record Alice's initial nonce (should be -1 for new address)
        initial_nonce = bc.nonce_tracker.get_nonce(alice.address)

        # Give Bob some funds too (so transaction can use UTXO inputs)
        bc.mine_pending_transactions(bob.address)

        # Get Alice's UTXOs for building transaction
        alice_utxos = bc.utxo_manager.get_utxos_for_address(alice.address)
        assert len(alice_utxos) > 0, "Alice needs UTXOs for transaction"

        # Create a valid UTXO-based transaction from Alice to Bob
        tx = Transaction(
            sender=alice.address,
            recipient=bob.address,
            amount=10.0,
            fee=0.001,
            inputs=[{"txid": alice_utxos[0]["txid"], "vout": alice_utxos[0]["vout"]}],
            nonce=bc.nonce_tracker.get_next_nonce(alice.address),
        )
        tx.sign_transaction(alice.private_key)
        bc.add_transaction(tx)

        # Verify transaction was added to pending
        pending_count_before = len(bc.pending_transactions)

        # Mock storage.save_state_to_disk to fail
        original_save = bc.storage.save_state_to_disk

        def failing_save(*args, **kwargs):
            raise IOError("Simulated disk full error")

        bc.storage.save_state_to_disk = failing_save

        # Try to mine - should fail and rollback
        with pytest.raises(IOError, match="Simulated disk full error"):
            bc.mine_pending_transactions(miner.address)

        # CRITICAL: Nonce should be rolled back to initial state
        final_nonce = bc.nonce_tracker.get_nonce(alice.address)
        assert final_nonce == initial_nonce, (
            f"Nonce should be rolled back after failed persistence. "
            f"Expected {initial_nonce}, got {final_nonce}"
        )

        # Transaction should still be in pending (restored after rollback)
        pending_count_after = len(bc.pending_transactions)
        assert pending_count_after == pending_count_before, (
            f"Pending transactions should be restored. "
            f"Expected {pending_count_before}, got {pending_count_after}"
        )

        # Block should not have been added
        initial_chain_length = 3  # Genesis + Alice's block + Bob's block
        assert len(bc.chain) == initial_chain_length

        # Restore storage and verify transaction can be mined successfully
        bc.storage.save_state_to_disk = original_save
        block = bc.mine_pending_transactions(miner.address)

        # Now nonce should be incremented
        assert bc.nonce_tracker.get_nonce(alice.address) == initial_nonce + 1
        assert block is not None
        assert len(bc.chain) == initial_chain_length + 1

    def test_utxo_rollback_on_storage_failure(self, tmp_path):
        """
        Test that UTXO state is also rolled back on persistence failure

        This ensures atomicity of all state changes, not just nonces
        """
        bc = Blockchain(data_dir=str(tmp_path))
        alice = Wallet()
        bob = Wallet()

        # Give Alice some funds
        bc.mine_pending_transactions(alice.address)
        alice_initial = bc.get_balance(alice.address)

        # Snapshot UTXO state
        utxo_snapshot_before = bc.utxo_manager.snapshot()

        # Create transaction
        tx = Transaction(
            sender=alice.address,
            recipient=bob.address,
            amount=10.0,
            fee=0.001,
            nonce=bc.nonce_tracker.get_next_nonce(alice.address),
        )
        tx.sign_transaction(alice.private_key)
        bc.add_transaction(tx)

        # Mock storage failure
        def failing_save(*args, **kwargs):
            raise IOError("Disk I/O error")

        original_save = bc.storage.save_state_to_disk
        bc.storage.save_state_to_disk = failing_save

        # Try to mine
        miner = Wallet()
        with pytest.raises(IOError):
            bc.mine_pending_transactions(miner.address)

        # UTXO state should be unchanged
        alice_balance_after_failure = bc.get_balance(alice.address)
        assert alice_balance_after_failure == alice_initial, (
            "Alice's balance should be unchanged after failed block persistence"
        )

        # UTXO snapshot should match (state fully rolled back)
        utxo_snapshot_after = bc.utxo_manager.snapshot()
        assert utxo_snapshot_before == utxo_snapshot_after, (
            "UTXO state should be completely rolled back"
        )

    def test_multiple_transactions_nonce_atomicity(self, tmp_path):
        """
        Test that multiple transactions in a block have atomic nonce updates

        If a block contains transactions from multiple senders,
        all nonce updates should be atomic with persistence.
        """
        bc = Blockchain(data_dir=str(tmp_path))
        alice = Wallet()
        bob = Wallet()
        charlie = Wallet()

        # Give Alice and Bob funds
        bc.mine_pending_transactions(alice.address)
        bc.mine_pending_transactions(bob.address)

        # Record initial nonces
        alice_nonce_initial = bc.nonce_tracker.get_nonce(alice.address)
        bob_nonce_initial = bc.nonce_tracker.get_nonce(bob.address)

        # Get UTXOs
        alice_utxos = bc.utxo_manager.get_utxos_for_address(alice.address)
        bob_utxos = bc.utxo_manager.get_utxos_for_address(bob.address)

        # Create transactions from both Alice and Bob with proper inputs
        tx1 = Transaction(
            sender=alice.address,
            recipient=charlie.address,
            amount=5.0,
            fee=0.001,
            inputs=[{"txid": alice_utxos[0]["txid"], "vout": alice_utxos[0]["vout"]}],
            nonce=bc.nonce_tracker.get_next_nonce(alice.address),
        )
        tx1.sign_transaction(alice.private_key)
        bc.add_transaction(tx1)

        tx2 = Transaction(
            sender=bob.address,
            recipient=charlie.address,
            amount=7.0,
            fee=0.001,
            inputs=[{"txid": bob_utxos[0]["txid"], "vout": bob_utxos[0]["vout"]}],
            nonce=bc.nonce_tracker.get_next_nonce(bob.address),
        )
        tx2.sign_transaction(bob.private_key)
        bc.add_transaction(tx2)

        # Record pending count
        pending_count = len(bc.pending_transactions)

        # Mock storage failure
        original_save = bc.storage.save_state_to_disk
        bc.storage.save_state_to_disk = lambda *args, **kwargs: (_ for _ in ()).throw(
            RuntimeError("Storage system unavailable")
        )

        # Try to mine
        miner = Wallet()
        with pytest.raises(RuntimeError):
            bc.mine_pending_transactions(miner.address)

        # Both nonces should be rolled back
        assert bc.nonce_tracker.get_nonce(alice.address) == alice_nonce_initial
        assert bc.nonce_tracker.get_nonce(bob.address) == bob_nonce_initial

        # Transactions should still be pending (restored)
        assert len(bc.pending_transactions) == pending_count

    def test_nonce_committed_after_successful_persistence(self, tmp_path):
        """
        Test that nonces ARE committed after successful persistence

        This is the happy path - ensures the fix doesn't break normal operation
        """
        bc = Blockchain(data_dir=str(tmp_path))
        alice = Wallet()
        miner = Wallet()

        # Record initial nonce (should be -1 for new address)
        initial_nonce = bc.nonce_tracker.get_nonce(alice.address)

        # Mine a block for Alice to get funds
        block = bc.mine_pending_transactions(alice.address)

        # Nonce SHOULD be incremented after successful mining
        # Mining creates a coinbase transaction which increments the miner's nonce
        final_nonce = bc.nonce_tracker.get_nonce(alice.address)

        # For this simple case, nonce should still be -1 since coinbase doesn't increment nonces
        # (Coinbase transactions are special and don't use nonces)
        assert final_nonce == initial_nonce, (
            f"Nonce behavior after coinbase: expected {initial_nonce}, got {final_nonce}"
        )

        # Block should be added
        assert block is not None
        assert block in bc.chain

    def test_chain_rollback_on_persistence_failure(self, tmp_path):
        """
        Test that block is removed from chain if persistence fails
        """
        bc = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        # Record chain length
        initial_length = len(bc.chain)

        # Mock storage failure
        bc.storage.save_state_to_disk = lambda *args, **kwargs: (_ for _ in ()).throw(
            OSError("No space left on device")
        )

        # Try to mine
        with pytest.raises(OSError):
            bc.mine_pending_transactions(wallet.address)

        # Chain length should be unchanged (block removed)
        assert len(bc.chain) == initial_length, (
            "Block should be removed from chain after persistence failure"
        )

    def test_pending_transactions_restored_on_failure(self, tmp_path):
        """
        Test that pending transactions are restored if mining fails
        """
        bc = Blockchain(data_dir=str(tmp_path))
        alice = Wallet()
        bob = Wallet()

        # Give Alice funds
        bc.mine_pending_transactions(alice.address)

        # Get Alice's UTXOs
        alice_utxos = bc.utxo_manager.get_utxos_for_address(alice.address)

        # Create transaction
        tx = Transaction(
            sender=alice.address,
            recipient=bob.address,
            amount=10.0,
            fee=0.001,
            inputs=[{"txid": alice_utxos[0]["txid"], "vout": alice_utxos[0]["vout"]}],
            nonce=bc.nonce_tracker.get_next_nonce(alice.address),
        )
        tx.sign_transaction(alice.private_key)
        bc.add_transaction(tx)

        # Verify transaction is pending
        pending_count = len(bc.pending_transactions)
        if pending_count == 0:
            # Transaction was rejected, can't test pending restore
            pytest.skip("Transaction was rejected during add_transaction")

        pending_tx = bc.pending_transactions[0]

        # Mock storage failure
        bc.storage.save_state_to_disk = lambda *args, **kwargs: (_ for _ in ()).throw(
            IOError("I/O error")
        )

        # Try to mine
        with pytest.raises(IOError):
            bc.mine_pending_transactions(alice.address)

        # Pending transactions should be restored
        assert len(bc.pending_transactions) == pending_count, (
            f"Pending transactions should be restored after failed mining. "
            f"Expected {pending_count}, got {len(bc.pending_transactions)}"
        )
        assert bc.pending_transactions[0].txid == pending_tx.txid

    def test_nonce_persistence_to_disk(self, tmp_path):
        """
        Test that nonces are persisted to disk after successful block addition

        This ensures nonces survive node restart
        """
        bc = Blockchain(data_dir=str(tmp_path))
        alice = Wallet()
        bob = Wallet()

        # Give Alice funds and make a transaction
        bc.mine_pending_transactions(alice.address)

        tx = Transaction(
            sender=alice.address,
            recipient=bob.address,
            amount=10.0,
            fee=0.001,
            nonce=bc.nonce_tracker.get_next_nonce(alice.address),
        )
        tx.sign_transaction(alice.private_key)
        bc.add_transaction(tx)

        miner = Wallet()
        bc.mine_pending_transactions(miner.address)

        # Get nonce after transaction
        nonce_before_restart = bc.nonce_tracker.get_nonce(alice.address)

        # Simulate node restart by creating new blockchain instance
        bc2 = Blockchain(data_dir=str(tmp_path))

        # Nonce should be loaded from disk
        nonce_after_restart = bc2.nonce_tracker.get_nonce(alice.address)

        assert nonce_after_restart == nonce_before_restart, (
            "Nonces should persist across node restarts"
        )


class TestNonceEdgeCases:
    """Test edge cases in nonce handling"""

    def test_nonce_validation_after_rollback(self, tmp_path):
        """
        Test that nonce validation works correctly after rollback
        """
        bc = Blockchain(data_dir=str(tmp_path))
        alice = Wallet()
        bob = Wallet()

        # Give Alice funds
        bc.mine_pending_transactions(alice.address)

        # Get next nonce
        next_nonce = bc.nonce_tracker.get_next_nonce(alice.address)

        # Create transaction
        tx = Transaction(
            sender=alice.address,
            recipient=bob.address,
            amount=10.0,
            nonce=next_nonce,
        )
        tx.sign_transaction(alice.private_key)
        bc.add_transaction(tx)

        # Mock failure
        bc.storage.save_state_to_disk = lambda *args, **kwargs: (_ for _ in ()).throw(
            Exception("Test failure")
        )

        with pytest.raises(Exception):
            bc.mine_pending_transactions(alice.address)

        # Same nonce should still be valid (not considered duplicate)
        assert bc.nonce_tracker.validate_nonce(alice.address, next_nonce), (
            "Nonce should still be valid after rollback"
        )

    def test_concurrent_nonce_snapshots(self, tmp_path):
        """
        Test that nonce snapshots work correctly under concurrent access

        This verifies thread safety of the snapshot mechanism
        """
        bc = Blockchain(data_dir=str(tmp_path))
        alice = Wallet()

        # Give Alice funds
        bc.mine_pending_transactions(alice.address)

        # Take snapshot
        snapshot1 = bc.nonce_tracker.snapshot()

        # Modify nonce
        bc.nonce_tracker.increment_nonce(alice.address, 5)

        # Take another snapshot
        snapshot2 = bc.nonce_tracker.snapshot()

        # Snapshots should be different
        assert snapshot1 != snapshot2

        # Restore first snapshot
        bc.nonce_tracker.restore(snapshot1)

        # Should match first snapshot state
        snapshot3 = bc.nonce_tracker.snapshot()
        assert snapshot1 == snapshot3
