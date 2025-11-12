"""
Unit tests for XAI Transaction functionality

Tests transaction creation, signing, verification, and validation
"""

import pytest
import sys
import os
import time

# Add core directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'core'))

from blockchain import Transaction, Blockchain
from wallet import Wallet


class TestTransactionCreation:
    """Test transaction creation"""

    def test_create_basic_transaction(self):
        """Test basic transaction creation"""
        wallet1 = Wallet()
        wallet2 = Wallet()

        tx = Transaction(wallet1.address, wallet2.address, 10.0, 0.24)

        assert tx.sender == wallet1.address
        assert tx.recipient == wallet2.address
        assert tx.amount == 10.0
        assert tx.fee == 0.24

    def test_transaction_timestamp(self):
        """Test transaction has timestamp"""
        wallet1 = Wallet()
        wallet2 = Wallet()

        tx = Transaction(wallet1.address, wallet2.address, 5.0, 0.1)

        assert tx.timestamp > 0
        assert tx.timestamp <= time.time()

    def test_transaction_initial_state(self):
        """Test transaction initial state"""
        wallet1 = Wallet()
        wallet2 = Wallet()

        tx = Transaction(wallet1.address, wallet2.address, 1.0, 0.01)

        assert tx.signature is None
        assert tx.txid is None

    def test_transaction_type_default(self):
        """Test default transaction type"""
        wallet1 = Wallet()
        wallet2 = Wallet()

        tx = Transaction(wallet1.address, wallet2.address, 1.0, 0.01)

        assert tx.tx_type == "normal"

    def test_coinbase_transaction(self):
        """Test coinbase transaction creation"""
        wallet = Wallet()

        tx = Transaction("COINBASE", wallet.address, 12.0)

        assert tx.sender == "COINBASE"
        assert tx.amount == 12.0


class TestTransactionSigning:
    """Test transaction signing"""

    def test_sign_transaction(self):
        """Test signing a transaction"""
        wallet = Wallet()
        tx = Transaction(wallet.address, "XAI123", 10.0, 0.24)

        tx.public_key = wallet.public_key
        tx.sign_transaction(wallet.private_key)

        assert tx.signature is not None
        assert len(tx.signature) > 0
        assert tx.txid is not None

    def test_signature_deterministic(self):
        """Test signature is deterministic for same transaction"""
        wallet = Wallet()

        tx1 = Transaction(wallet.address, "XAI123", 10.0, 0.24)
        tx1.public_key = wallet.public_key
        tx1.timestamp = 1234567890  # Fixed timestamp
        tx1.sign_transaction(wallet.private_key)

        tx2 = Transaction(wallet.address, "XAI123", 10.0, 0.24)
        tx2.public_key = wallet.public_key
        tx2.timestamp = 1234567890  # Same timestamp
        tx2.sign_transaction(wallet.private_key)

        # Same transaction data should produce same hash
        assert tx1.calculate_hash() == tx2.calculate_hash()

    def test_different_amounts_different_signatures(self):
        """Test different amounts produce different signatures"""
        wallet = Wallet()

        tx1 = Transaction(wallet.address, "XAI123", 10.0, 0.24)
        tx1.public_key = wallet.public_key
        tx1.sign_transaction(wallet.private_key)

        tx2 = Transaction(wallet.address, "XAI123", 20.0, 0.24)
        tx2.public_key = wallet.public_key
        tx2.sign_transaction(wallet.private_key)

        assert tx1.signature != tx2.signature

    def test_coinbase_no_signature_required(self):
        """Test coinbase transactions don't require signature"""
        tx = Transaction("COINBASE", "XAI123", 12.0)
        tx.sign_transaction("")  # Empty private key

        assert tx.txid is not None


class TestTransactionVerification:
    """Test transaction signature verification"""

    def test_verify_valid_signature(self):
        """Test verification of valid signature"""
        wallet = Wallet()
        tx = Transaction(wallet.address, "XAI123", 10.0, 0.24)

        tx.public_key = wallet.public_key
        tx.sign_transaction(wallet.private_key)

        assert tx.verify_signature()

    def test_reject_invalid_signature(self):
        """Test rejection of invalid signature"""
        wallet1 = Wallet()
        wallet2 = Wallet()

        tx = Transaction(wallet1.address, "XAI123", 10.0, 0.24)
        tx.public_key = wallet1.public_key

        # Sign with wrong wallet
        tx.sign_transaction(wallet2.private_key)

        assert not tx.verify_signature()

    def test_verify_coinbase_transaction(self):
        """Test coinbase transactions auto-verify"""
        tx = Transaction("COINBASE", "XAI123", 12.0)
        tx.txid = tx.calculate_hash()

        assert tx.verify_signature()

    def test_reject_unsigned_transaction(self):
        """Test unsigned transactions don't verify"""
        wallet = Wallet()
        tx = Transaction(wallet.address, "XAI123", 10.0, 0.24)
        tx.public_key = wallet.public_key

        # Don't sign
        assert not tx.verify_signature()

    def test_reject_tampered_transaction(self):
        """Test tampered transactions don't verify"""
        wallet = Wallet()
        tx = Transaction(wallet.address, "XAI123", 10.0, 0.24)

        tx.public_key = wallet.public_key
        tx.sign_transaction(wallet.private_key)

        # Tamper with amount
        original_amount = tx.amount
        tx.amount = 999999.0

        # Should fail verification
        assert not tx.verify_signature()

        # Restore amount
        tx.amount = original_amount


class TestTransactionHash:
    """Test transaction hash calculation"""

    def test_calculate_hash(self):
        """Test hash calculation"""
        wallet = Wallet()
        tx = Transaction(wallet.address, "XAI123", 10.0, 0.24)

        hash1 = tx.calculate_hash()

        assert hash1 is not None
        assert len(hash1) == 64  # SHA256 hex length
        assert all(c in '0123456789abcdef' for c in hash1)

    def test_hash_consistency(self):
        """Test hash is consistent for same transaction"""
        wallet = Wallet()
        tx = Transaction(wallet.address, "XAI123", 10.0, 0.24)
        tx.timestamp = 1234567890  # Fixed timestamp

        hash1 = tx.calculate_hash()
        hash2 = tx.calculate_hash()

        assert hash1 == hash2

    def test_different_data_different_hash(self):
        """Test different transaction data produces different hash"""
        wallet = Wallet()

        tx1 = Transaction(wallet.address, "XAI123", 10.0, 0.24)
        tx2 = Transaction(wallet.address, "XAI123", 20.0, 0.24)

        hash1 = tx1.calculate_hash()
        hash2 = tx2.calculate_hash()

        assert hash1 != hash2


class TestTransactionValidation:
    """Test transaction validation in blockchain context"""

    def test_validate_proper_transaction(self):
        """Test validation of properly formed transaction"""
        bc = Blockchain()
        wallet1 = Wallet()
        wallet2 = Wallet()

        # Give wallet1 some balance
        bc.mine_pending_transactions(wallet1.address)

        # Create valid transaction
        tx = Transaction(wallet1.address, wallet2.address, 5.0, 0.24)
        tx.public_key = wallet1.public_key
        tx.sign_transaction(wallet1.private_key)

        assert bc.validate_transaction(tx)

    def test_reject_insufficient_balance(self):
        """Test rejection of transaction with insufficient balance"""
        bc = Blockchain()
        wallet1 = Wallet()
        wallet2 = Wallet()

        # wallet1 has no balance
        tx = Transaction(wallet1.address, wallet2.address, 100.0, 0.24)
        tx.public_key = wallet1.public_key
        tx.sign_transaction(wallet1.private_key)

        assert not bc.validate_transaction(tx)

    def test_reject_negative_amount(self):
        """Test rejection of negative amount"""
        bc = Blockchain()
        wallet1 = Wallet()
        wallet2 = Wallet()

        bc.mine_pending_transactions(wallet1.address)

        tx = Transaction(wallet1.address, wallet2.address, -10.0, 0.24)
        tx.public_key = wallet1.public_key
        tx.sign_transaction(wallet1.private_key)

        assert not bc.validate_transaction(tx)

    def test_validate_coinbase_transaction(self):
        """Test coinbase transactions validate"""
        bc = Blockchain()
        wallet = Wallet()

        tx = Transaction("COINBASE", wallet.address, 12.0)
        tx.txid = tx.calculate_hash()

        assert bc.validate_transaction(tx)


class TestTransactionNonce:
    """Test transaction nonce for replay protection"""

    def test_transaction_with_nonce(self):
        """Test transaction can include nonce"""
        wallet1 = Wallet()
        wallet2 = Wallet()

        tx = Transaction(wallet1.address, wallet2.address, 10.0, 0.24, nonce=1)

        assert tx.nonce == 1

    def test_nonce_in_hash(self):
        """Test nonce affects transaction hash"""
        wallet1 = Wallet()
        wallet2 = Wallet()

        tx1 = Transaction(wallet1.address, wallet2.address, 10.0, 0.24, nonce=1)
        tx2 = Transaction(wallet1.address, wallet2.address, 10.0, 0.24, nonce=2)

        tx1.timestamp = tx2.timestamp  # Same timestamp

        hash1 = tx1.calculate_hash()
        hash2 = tx2.calculate_hash()

        assert hash1 != hash2


class TestTransactionFees:
    """Test transaction fee handling"""

    def test_transaction_with_fee(self):
        """Test transaction includes fee"""
        wallet1 = Wallet()
        wallet2 = Wallet()

        tx = Transaction(wallet1.address, wallet2.address, 10.0, 0.24)

        assert tx.fee == 0.24

    def test_transaction_without_fee(self):
        """Test transaction with zero fee"""
        wallet1 = Wallet()
        wallet2 = Wallet()

        tx = Transaction(wallet1.address, wallet2.address, 10.0, 0.0)

        assert tx.fee == 0.0

    def test_fee_validation(self):
        """Test fee must be non-negative"""
        wallet1 = Wallet()
        wallet2 = Wallet()

        tx = Transaction(wallet1.address, wallet2.address, 10.0, -0.5)

        # Negative fees should be rejected by validation
        bc = Blockchain()
        bc.mine_pending_transactions(wallet1.address)  # Give balance

        tx.public_key = wallet1.public_key
        tx.sign_transaction(wallet1.private_key)

        # Should fail validation
        assert not bc.validate_transaction(tx)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
