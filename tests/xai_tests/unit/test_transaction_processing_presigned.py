"""
Unit tests for transaction processing with pre-signed transactions.

Tests verify that UTXO manager correctly handles transactions that have
been signed and have their txid populated. This tests the complete
transaction lifecycle:
1. Create transaction
2. Sign transaction (populates txid)
3. Process outputs (creates new UTXOs with txid)
4. Process inputs (spends UTXOs referencing txid)
5. Verify UTXO state integrity
"""

import pytest
from xai.core.transactions.utxo_manager import UTXOManager
from xai.core.transaction import Transaction
from xai.core.wallet import Wallet


class TestPreSignedTransactionOutputProcessing:
    """Test processing outputs from pre-signed transactions (txid populated)."""

    def test_process_signed_transaction_outputs(self):
        """Signed transactions should create UTXOs with correct txid."""
        manager = UTXOManager()
        wallet = Wallet()
        recipient = Wallet()

        # Create and sign transaction
        tx = Transaction(wallet.address, recipient.address, 10.0, 0.5)
        tx.public_key = wallet.public_key
        tx.sign_transaction(wallet.private_key)

        # Verify txid is populated
        assert tx.txid is not None
        assert len(tx.txid) == 64  # SHA256 hex

        # Process outputs
        manager.process_transaction_outputs(tx)

        # Verify UTXOs created with correct txid
        utxos = manager.get_utxos_for_address(recipient.address)
        assert len(utxos) == 1
        assert utxos[0]["txid"] == tx.txid
        assert utxos[0]["amount"] == 10.0
        assert utxos[0]["vout"] == 0

    def test_process_signed_transaction_multiple_outputs(self):
        """Signed transactions with multiple outputs should create multiple UTXOs."""
        manager = UTXOManager()
        wallet = Wallet()
        recipient1 = Wallet()
        recipient2 = Wallet()

        # Create transaction with explicit outputs
        tx = Transaction(
            sender=wallet.address,
            recipient=recipient1.address,
            amount=10.0,
            fee=0.5,
            outputs=[
                {"address": recipient1.address, "amount": 7.0},
                {"address": recipient2.address, "amount": 3.0},
            ]
        )
        tx.public_key = wallet.public_key
        tx.sign_transaction(wallet.private_key)

        # Verify txid populated
        assert tx.txid is not None

        # Process outputs
        manager.process_transaction_outputs(tx)

        # Verify UTXOs for both recipients
        utxos1 = manager.get_utxos_for_address(recipient1.address)
        utxos2 = manager.get_utxos_for_address(recipient2.address)

        assert len(utxos1) == 1
        assert len(utxos2) == 1
        assert utxos1[0]["txid"] == tx.txid
        assert utxos2[0]["txid"] == tx.txid
        assert utxos1[0]["vout"] == 0
        assert utxos2[0]["vout"] == 1
        assert utxos1[0]["amount"] == 7.0
        assert utxos2[0]["amount"] == 3.0

    def test_process_coinbase_transaction_outputs(self):
        """Coinbase transactions should create valid UTXOs."""
        manager = UTXOManager()
        miner_wallet = Wallet()

        # Create coinbase transaction
        coinbase_tx = Transaction("COINBASE", miner_wallet.address, 12.0, 0.0)
        coinbase_tx.sign_transaction("")  # Coinbase doesn't need real signature

        # Verify txid is set
        assert coinbase_tx.txid is not None

        # Process outputs
        manager.process_transaction_outputs(coinbase_tx)

        # Verify miner received the UTXO
        utxos = manager.get_utxos_for_address(miner_wallet.address)
        assert len(utxos) == 1
        assert utxos[0]["txid"] == coinbase_tx.txid
        assert utxos[0]["amount"] == 12.0


class TestPreSignedTransactionInputProcessing:
    """Test processing inputs from pre-signed transactions."""

    def test_process_signed_transaction_inputs(self):
        """Signed transactions should spend UTXOs correctly."""
        manager = UTXOManager()
        sender = Wallet()
        recipient = Wallet()

        # Create initial UTXO (from a previous signed coinbase)
        coinbase_tx = Transaction("COINBASE", sender.address, 100.0, 0.0)
        coinbase_tx.sign_transaction("")
        manager.process_transaction_outputs(coinbase_tx)

        # Verify initial state
        assert manager.get_balance(sender.address) == 100.0

        # Create spending transaction with inputs
        spend_tx = Transaction(
            sender=sender.address,
            recipient=recipient.address,
            amount=50.0,
            fee=0.5,
            inputs=[{"txid": coinbase_tx.txid, "vout": 0}],
        )
        spend_tx.public_key = sender.public_key
        spend_tx.sign_transaction(sender.private_key)

        # Process inputs (mark UTXOs as spent)
        result = manager.process_transaction_inputs(spend_tx)

        assert result is True
        assert manager.get_balance(sender.address) == 0.0

    def test_process_signed_transaction_multiple_inputs(self):
        """Signed transactions should spend multiple UTXOs correctly."""
        manager = UTXOManager()
        sender = Wallet()
        recipient = Wallet()

        # Create multiple UTXOs for sender
        txids = []
        for i in range(3):
            coinbase_tx = Transaction("COINBASE", sender.address, 30.0, 0.0)
            coinbase_tx.timestamp = 1000000 + i  # Different timestamps
            coinbase_tx.sign_transaction("")
            manager.process_transaction_outputs(coinbase_tx)
            txids.append(coinbase_tx.txid)

        # Verify initial balance
        assert manager.get_balance(sender.address) == 90.0

        # Create spending transaction with multiple inputs
        spend_tx = Transaction(
            sender=sender.address,
            recipient=recipient.address,
            amount=80.0,
            fee=0.5,
            inputs=[
                {"txid": txids[0], "vout": 0},
                {"txid": txids[1], "vout": 0},
                {"txid": txids[2], "vout": 0},
            ],
        )
        spend_tx.public_key = sender.public_key
        spend_tx.sign_transaction(sender.private_key)

        # Process inputs
        result = manager.process_transaction_inputs(spend_tx)

        assert result is True
        assert manager.get_balance(sender.address) == 0.0

    def test_process_inputs_with_invalid_txid_fails(self):
        """Processing inputs with non-existent txid should fail."""
        manager = UTXOManager()
        sender = Wallet()
        recipient = Wallet()

        # Create a signed transaction referencing non-existent UTXO
        spend_tx = Transaction(
            sender=sender.address,
            recipient=recipient.address,
            amount=10.0,
            fee=0.5,
            inputs=[{"txid": "nonexistent_txid_0123456789abcdef", "vout": 0}],
        )
        spend_tx.public_key = sender.public_key
        spend_tx.sign_transaction(sender.private_key)

        # Process inputs should fail
        result = manager.process_transaction_inputs(spend_tx)

        assert result is False


class TestFullTransactionLifecycle:
    """Test complete transaction lifecycle with pre-signed transactions."""

    def test_full_lifecycle_send_and_receive(self):
        """Test complete flow: mine → sign → send → receive."""
        manager = UTXOManager()
        miner = Wallet()
        alice = Wallet()
        bob = Wallet()

        # Step 1: Mine block (coinbase to miner)
        coinbase = Transaction("COINBASE", miner.address, 50.0, 0.0)
        coinbase.sign_transaction("")
        manager.process_transaction_outputs(coinbase)

        assert manager.get_balance(miner.address) == 50.0
        assert coinbase.txid is not None

        # Step 2: Miner sends to Alice
        tx1 = Transaction(
            sender=miner.address,
            recipient=alice.address,
            amount=30.0,
            fee=0.5,
            inputs=[{"txid": coinbase.txid, "vout": 0}],
            outputs=[
                {"address": alice.address, "amount": 30.0},
                {"address": miner.address, "amount": 19.5},  # Change
            ]
        )
        tx1.public_key = miner.public_key
        tx1.sign_transaction(miner.private_key)

        assert tx1.txid is not None
        assert manager.process_transaction_inputs(tx1) is True
        manager.process_transaction_outputs(tx1)

        assert manager.get_balance(miner.address) == 19.5
        assert manager.get_balance(alice.address) == 30.0

        # Step 3: Alice sends to Bob
        alice_utxos = manager.get_utxos_for_address(alice.address)
        tx2 = Transaction(
            sender=alice.address,
            recipient=bob.address,
            amount=15.0,
            fee=0.3,
            inputs=[{"txid": alice_utxos[0]["txid"], "vout": alice_utxos[0]["vout"]}],
            outputs=[
                {"address": bob.address, "amount": 15.0},
                {"address": alice.address, "amount": 14.7},  # Change
            ]
        )
        tx2.public_key = alice.public_key
        tx2.sign_transaction(alice.private_key)

        assert tx2.txid is not None
        assert manager.process_transaction_inputs(tx2) is True
        manager.process_transaction_outputs(tx2)

        assert manager.get_balance(alice.address) == 14.7
        assert manager.get_balance(bob.address) == 15.0

        # Verify UTXO consistency
        verification = manager.verify_utxo_consistency()
        assert verification["is_consistent"]

    def test_lifecycle_double_spend_prevention(self):
        """Pre-signed transactions cannot double-spend UTXOs."""
        manager = UTXOManager()
        sender = Wallet()
        recipient1 = Wallet()
        recipient2 = Wallet()

        # Create initial UTXO
        coinbase = Transaction("COINBASE", sender.address, 100.0, 0.0)
        coinbase.sign_transaction("")
        manager.process_transaction_outputs(coinbase)

        # First spend (valid)
        tx1 = Transaction(
            sender=sender.address,
            recipient=recipient1.address,
            amount=50.0,
            fee=0.5,
            inputs=[{"txid": coinbase.txid, "vout": 0}],
        )
        tx1.public_key = sender.public_key
        tx1.sign_transaction(sender.private_key)

        result1 = manager.process_transaction_inputs(tx1)
        assert result1 is True

        # Attempt double-spend with same input
        tx2 = Transaction(
            sender=sender.address,
            recipient=recipient2.address,
            amount=50.0,
            fee=0.5,
            inputs=[{"txid": coinbase.txid, "vout": 0}],  # Same input!
        )
        tx2.public_key = sender.public_key
        tx2.sign_transaction(sender.private_key)

        result2 = manager.process_transaction_inputs(tx2)
        assert result2 is False  # Double spend rejected

    def test_lifecycle_chained_transactions(self):
        """Test chain of transactions where each spends output of previous."""
        manager = UTXOManager()
        wallets = [Wallet() for _ in range(5)]

        # Initial coinbase
        coinbase = Transaction("COINBASE", wallets[0].address, 100.0, 0.0)
        coinbase.sign_transaction("")
        manager.process_transaction_outputs(coinbase)

        prev_txid = coinbase.txid
        prev_vout = 0
        amount = 100.0
        fee = 0.1

        # Chain transactions through each wallet
        for i in range(len(wallets) - 1):
            sender = wallets[i]
            recipient = wallets[i + 1]

            tx = Transaction(
                sender=sender.address,
                recipient=recipient.address,
                amount=amount - fee,
                fee=fee,
                inputs=[{"txid": prev_txid, "vout": prev_vout}],
            )
            tx.public_key = sender.public_key
            tx.sign_transaction(sender.private_key)

            assert tx.txid is not None
            assert manager.process_transaction_inputs(tx) is True
            manager.process_transaction_outputs(tx)

            prev_txid = tx.txid
            prev_vout = 0
            amount = amount - fee

        # Verify final state
        assert manager.get_balance(wallets[0].address) == 0.0
        assert manager.get_balance(wallets[-1].address) == pytest.approx(99.6, rel=0.01)

        verification = manager.verify_utxo_consistency()
        assert verification["is_consistent"]


class TestPreSignedTransactionTxidIntegrity:
    """Test that txid is correctly used throughout processing."""

    def test_txid_deterministic_after_signing(self):
        """Txid should be deterministic based on transaction content."""
        wallet = Wallet()
        recipient = Wallet()

        # Create two identical transactions
        tx1 = Transaction(wallet.address, recipient.address, 10.0, 0.5)
        tx1.timestamp = 1234567890
        tx1.public_key = wallet.public_key
        tx1.sign_transaction(wallet.private_key)

        tx2 = Transaction(wallet.address, recipient.address, 10.0, 0.5)
        tx2.timestamp = 1234567890
        tx2.public_key = wallet.public_key
        tx2.sign_transaction(wallet.private_key)

        # Same content should produce same txid
        assert tx1.txid == tx2.txid

    def test_txid_changes_with_content(self):
        """Different content should produce different txid."""
        wallet = Wallet()
        recipient = Wallet()

        tx1 = Transaction(wallet.address, recipient.address, 10.0, 0.5)
        tx1.timestamp = 1234567890
        tx1.public_key = wallet.public_key
        tx1.sign_transaction(wallet.private_key)

        tx2 = Transaction(wallet.address, recipient.address, 20.0, 0.5)  # Different amount
        tx2.timestamp = 1234567890
        tx2.public_key = wallet.public_key
        tx2.sign_transaction(wallet.private_key)

        # Different content produces different txid
        assert tx1.txid != tx2.txid

    def test_utxo_references_correct_txid(self):
        """UTXOs created should reference the correct txid."""
        manager = UTXOManager()
        wallet = Wallet()

        # Create signed coinbase
        coinbase = Transaction("COINBASE", wallet.address, 50.0, 0.0)
        coinbase.sign_transaction("")
        expected_txid = coinbase.txid

        manager.process_transaction_outputs(coinbase)

        # Verify UTXO has correct txid
        utxo = manager.get_unspent_output(expected_txid, 0)
        assert utxo is not None
        assert utxo["txid"] == expected_txid

    def test_spending_requires_exact_txid_match(self):
        """Spending UTXO requires exact txid match."""
        manager = UTXOManager()
        sender = Wallet()
        recipient = Wallet()

        # Create UTXO
        coinbase = Transaction("COINBASE", sender.address, 50.0, 0.0)
        coinbase.sign_transaction("")
        manager.process_transaction_outputs(coinbase)

        # Try to spend with wrong txid (modified hash)
        wrong_txid = "0" * 64
        tx = Transaction(
            sender=sender.address,
            recipient=recipient.address,
            amount=10.0,
            fee=0.5,
            inputs=[{"txid": wrong_txid, "vout": 0}],
        )
        tx.public_key = sender.public_key
        tx.sign_transaction(sender.private_key)

        result = manager.process_transaction_inputs(tx)
        assert result is False

        # Spend with correct txid succeeds
        tx2 = Transaction(
            sender=sender.address,
            recipient=recipient.address,
            amount=10.0,
            fee=0.5,
            inputs=[{"txid": coinbase.txid, "vout": 0}],
        )
        tx2.public_key = sender.public_key
        tx2.sign_transaction(sender.private_key)

        result2 = manager.process_transaction_inputs(tx2)
        assert result2 is True


class TestPreSignedTransactionStateConsistency:
    """Test UTXO state consistency after processing pre-signed transactions."""

    def test_state_consistency_after_outputs(self):
        """UTXO state should be consistent after processing outputs."""
        manager = UTXOManager()
        wallets = [Wallet() for _ in range(10)]

        # Create multiple coinbase transactions
        for i, w in enumerate(wallets):
            coinbase = Transaction("COINBASE", w.address, float(i + 1) * 10.0, 0.0)
            coinbase.timestamp = 1000000 + i
            coinbase.sign_transaction("")
            manager.process_transaction_outputs(coinbase)

        # Verify consistency
        verification = manager.verify_utxo_consistency()
        assert verification["is_consistent"]
        assert verification["total_utxos_actual"] == 10
        assert verification["total_value_actual"] == 550.0  # Sum of 10+20+...+100

    def test_state_consistency_after_spending(self):
        """UTXO state should be consistent after spending."""
        manager = UTXOManager()
        sender = Wallet()
        recipient = Wallet()

        # Create multiple UTXOs
        txids = []
        for i in range(5):
            coinbase = Transaction("COINBASE", sender.address, 20.0, 0.0)
            coinbase.timestamp = 1000000 + i
            coinbase.sign_transaction("")
            manager.process_transaction_outputs(coinbase)
            txids.append(coinbase.txid)

        assert manager.total_utxos == 5
        assert manager.total_value == 100.0

        # Spend some UTXOs
        tx = Transaction(
            sender=sender.address,
            recipient=recipient.address,
            amount=50.0,
            fee=0.5,
            inputs=[
                {"txid": txids[0], "vout": 0},
                {"txid": txids[1], "vout": 0},
                {"txid": txids[2], "vout": 0},
            ],
        )
        tx.public_key = sender.public_key
        tx.sign_transaction(sender.private_key)

        manager.process_transaction_inputs(tx)
        manager.process_transaction_outputs(tx)

        # Verify consistency
        verification = manager.verify_utxo_consistency()
        assert verification["is_consistent"]
        # 2 unspent sender UTXOs + 1 recipient UTXO = 3
        assert verification["total_utxos_actual"] == 3

    def test_merkle_root_changes_after_spending(self):
        """Merkle root should change after spending UTXOs."""
        manager = UTXOManager()
        sender = Wallet()
        recipient = Wallet()

        # Create UTXO
        coinbase = Transaction("COINBASE", sender.address, 50.0, 0.0)
        coinbase.sign_transaction("")
        manager.process_transaction_outputs(coinbase)

        # Record initial merkle root
        initial_root = manager.calculate_merkle_root()

        # Spend the UTXO
        tx = Transaction(
            sender=sender.address,
            recipient=recipient.address,
            amount=40.0,
            fee=0.5,
            inputs=[{"txid": coinbase.txid, "vout": 0}],
        )
        tx.public_key = sender.public_key
        tx.sign_transaction(sender.private_key)

        manager.process_transaction_inputs(tx)
        manager.process_transaction_outputs(tx)

        # Merkle root should change
        new_root = manager.calculate_merkle_root()
        assert initial_root != new_root


class TestPreSignedTransactionEdgeCases:
    """Test edge cases with pre-signed transactions."""

    def test_empty_inputs_non_coinbase(self):
        """Non-coinbase transactions with empty inputs should process inputs OK."""
        manager = UTXOManager()
        sender = Wallet()
        recipient = Wallet()

        # Transaction with no inputs (unusual but possible before validation)
        tx = Transaction(
            sender=sender.address,
            recipient=recipient.address,
            amount=10.0,
            fee=0.5,
            inputs=[],  # Empty inputs
        )
        tx.public_key = sender.public_key
        tx.sign_transaction(sender.private_key)

        # Should return True because no inputs to mark as spent
        result = manager.process_transaction_inputs(tx)
        assert result is True

    def test_process_outputs_with_empty_outputs(self):
        """Transactions with no outputs should not create UTXOs."""
        manager = UTXOManager()
        sender = Wallet()

        # Transaction with explicit empty outputs
        tx = Transaction(
            sender=sender.address,
            recipient="",
            amount=0.0,
            fee=0.0,
            outputs=[],
        )
        tx.sign_transaction(sender.private_key)

        manager.process_transaction_outputs(tx)

        assert manager.total_utxos == 0

    def test_high_precision_amounts(self):
        """Test transactions with high precision amounts."""
        manager = UTXOManager()
        wallet = Wallet()

        # Coinbase with high precision
        coinbase = Transaction("COINBASE", wallet.address, 12.123456789012, 0.0)
        coinbase.sign_transaction("")
        manager.process_transaction_outputs(coinbase)

        balance = manager.get_balance(wallet.address)
        assert abs(balance - 12.123456789012) < 1e-10

    def test_snapshot_includes_presigned_txids(self):
        """Snapshot should include all txids from pre-signed transactions."""
        manager = UTXOManager()
        wallet = Wallet()

        # Create multiple signed transactions
        txids = []
        for i in range(3):
            coinbase = Transaction("COINBASE", wallet.address, 10.0, 0.0)
            coinbase.timestamp = 1000000 + i
            coinbase.sign_transaction("")
            manager.process_transaction_outputs(coinbase)
            txids.append(coinbase.txid)

        # Take snapshot
        snapshot = manager.snapshot()

        # Verify all txids in snapshot
        for txid in txids:
            found = False
            for addr_utxos in snapshot["utxo_set"].values():
                for utxo in addr_utxos:
                    if utxo["txid"] == txid:
                        found = True
                        break
            assert found, f"txid {txid} not found in snapshot"

    def test_restore_preserves_presigned_txids(self):
        """Restore should preserve txids from pre-signed transactions."""
        manager = UTXOManager()
        wallet = Wallet()

        # Create signed coinbase
        coinbase = Transaction("COINBASE", wallet.address, 50.0, 0.0)
        coinbase.sign_transaction("")
        original_txid = coinbase.txid
        manager.process_transaction_outputs(coinbase)

        # Snapshot and restore
        snapshot = manager.snapshot()
        manager.reset()
        manager.restore(snapshot)

        # Verify txid preserved
        utxo = manager.get_unspent_output(original_txid, 0)
        assert utxo is not None
        assert utxo["txid"] == original_txid


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
