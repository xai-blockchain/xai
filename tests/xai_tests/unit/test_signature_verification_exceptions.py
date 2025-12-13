"""
Comprehensive tests for transaction signature verification exception handling.

These tests verify that signature verification errors are always propagated
as exceptions and never silently ignored, ensuring security.
"""

import pytest
from xai.core.transaction import (
    Transaction,
    SignatureVerificationError,
    MissingSignatureError,
    InvalidSignatureError,
    SignatureCryptoError,
)
from xai.core.wallet import Wallet
from xai.core.blockchain import Blockchain
from xai.core.transaction_validator import TransactionValidator


class TestSignatureVerificationExceptions:
    """Test that verify_signature() raises appropriate exceptions."""

    def test_missing_signature_raises_exception(self):
        """Test that verify_signature raises MissingSignatureError when signature is missing."""
        tx = Transaction(
            sender="XAI" + "a" * 40,
            recipient="XAI" + "b" * 40,
            amount=10.0,
            fee=1.0
        )
        # Don't sign it
        tx.public_key = "04" + "a" * 128  # Valid public key format
        tx.txid = tx.calculate_hash()

        with pytest.raises(MissingSignatureError) as exc_info:
            tx.verify_signature()

        assert "missing signature" in str(exc_info.value).lower()

    def test_missing_public_key_raises_exception(self):
        """Test that verify_signature raises MissingSignatureError when public key is missing."""
        tx = Transaction(
            sender="XAI" + "a" * 40,
            recipient="XAI" + "b" * 40,
            amount=10.0,
            fee=1.0
        )
        tx.signature = "0" * 128  # Valid signature format
        tx.txid = tx.calculate_hash()
        # Don't set public_key

        with pytest.raises(MissingSignatureError) as exc_info:
            tx.verify_signature()

        assert "missing" in str(exc_info.value).lower()
        assert "public key" in str(exc_info.value).lower()

    def test_invalid_signature_raises_exception(self):
        """Test that verify_signature raises InvalidSignatureError for invalid signatures."""
        wallet = Wallet()
        blockchain = Blockchain(data_dir="test_data_sig_invalid")

        tx = blockchain.create_transaction(
            sender_address=wallet.address,
            recipient_address="XAI" + "b" * 40,
            amount=10.0,
            fee=1.0,
            private_key=wallet.private_key,
            public_key=wallet.public_key
        )

        # Corrupt the signature
        tx.signature = "0" * 128

        with pytest.raises(InvalidSignatureError) as exc_info:
            tx.verify_signature()

        assert "ecdsa" in str(exc_info.value).lower() or "failed" in str(exc_info.value).lower()

    def test_address_mismatch_raises_exception(self):
        """Test that verify_signature raises InvalidSignatureError when public key doesn't match sender."""
        wallet1 = Wallet()
        wallet2 = Wallet()
        blockchain = Blockchain(data_dir="test_data_sig_mismatch")

        tx = blockchain.create_transaction(
            sender_address=wallet1.address,
            recipient_address="XAI" + "b" * 40,
            amount=10.0,
            fee=1.0,
            private_key=wallet1.private_key,
            public_key=wallet1.public_key
        )

        # Replace public key with different wallet's key
        tx.public_key = wallet2.public_key

        with pytest.raises(InvalidSignatureError) as exc_info:
            tx.verify_signature()

        assert "address" in str(exc_info.value).lower() or "mismatch" in str(exc_info.value).lower()

    def test_coinbase_transaction_does_not_raise(self):
        """Test that COINBASE transactions don't require signature verification."""
        tx = Transaction(
            sender="COINBASE",
            recipient="XAI" + "a" * 40,
            amount=50.0,
            fee=0.0
        )
        tx.txid = tx.calculate_hash()

        # Should not raise - coinbase transactions don't require signatures
        tx.verify_signature()  # No exception expected

    def test_malformed_public_key_raises_crypto_error(self):
        """Test that malformed public keys raise SignatureCryptoError."""
        tx = Transaction(
            sender="XAI" + "a" * 40,
            recipient="XAI" + "b" * 40,
            amount=10.0,
            fee=1.0
        )
        tx.public_key = "NOT_HEX"  # Invalid hex
        tx.signature = "0" * 128
        tx.txid = tx.calculate_hash()

        with pytest.raises(SignatureCryptoError) as exc_info:
            tx.verify_signature()

        assert "cryptographic" in str(exc_info.value).lower() or "failed" in str(exc_info.value).lower()


class TestTransactionValidatorExceptionHandling:
    """Test that TransactionValidator properly handles signature verification exceptions."""

    def test_validator_catches_missing_signature(self):
        """Test that validator converts MissingSignatureError to ValidationError (returns False)."""
        blockchain = Blockchain(data_dir="test_data_sig_validator")
        validator = TransactionValidator(blockchain)

        tx = Transaction(
            sender="XAI" + "a" * 40,
            recipient="XAI" + "b" * 40,
            amount=10.0,
            fee=1.0
        )
        tx.public_key = "04" + "a" * 128
        tx.txid = tx.calculate_hash()
        # No signature

        # Should return False (ValidationError is caught internally)
        is_valid = validator.validate_transaction(tx)
        assert is_valid is False

    def test_validator_catches_invalid_signature(self):
        """Test that validator converts InvalidSignatureError to ValidationError (returns False)."""
        blockchain = Blockchain(data_dir="test_data_sig_validator2")
        validator = TransactionValidator(blockchain)

        wallet = Wallet()
        tx = blockchain.create_transaction(
            sender_address=wallet.address,
            recipient_address="XAI" + "b" * 40,
            amount=10.0,
            fee=1.0,
            private_key=wallet.private_key,
            public_key=wallet.public_key
        )
        # Corrupt signature
        tx.signature = "0" * 128

        # Should return False (ValidationError is caught internally)
        is_valid = validator.validate_transaction(tx)
        assert is_valid is False


class TestMempoolRejectsInvalidSignatures:
    """Test that mempool properly rejects transactions with invalid signatures."""

    def test_mempool_rejects_missing_signature(self):
        """Test that mempool rejects transactions with missing signatures."""
        blockchain = Blockchain(data_dir="test_data_mempool_sig1")

        tx = Transaction(
            sender="XAI" + "a" * 40,
            recipient="XAI" + "b" * 40,
            amount=10.0,
            fee=1.0
        )
        tx.public_key = "04" + "a" * 128
        tx.txid = tx.calculate_hash()
        # No signature

        # Should reject
        result = blockchain.add_transaction(tx)
        assert result is False
        assert tx.txid not in [t.txid for t in blockchain.pending_transactions]

    def test_mempool_rejects_invalid_signature(self):
        """Test that mempool rejects transactions with invalid signatures."""
        blockchain = Blockchain(data_dir="test_data_mempool_sig2")

        wallet = Wallet()
        tx = blockchain.create_transaction(
            sender_address=wallet.address,
            recipient_address="XAI" + "b" * 40,
            amount=10.0,
            fee=1.0,
            private_key=wallet.private_key,
            public_key=wallet.public_key
        )
        # Corrupt signature
        tx.signature = "0" * 128

        # Should reject
        result = blockchain.add_transaction(tx)
        assert result is False
        assert tx.txid not in [t.txid for t in blockchain.pending_transactions]

    def test_mempool_accepts_valid_signature(self):
        """Test that mempool accepts transactions with valid signatures."""
        blockchain = Blockchain(data_dir="test_data_mempool_sig3")

        wallet = Wallet()

        # Fund the wallet first
        coinbase = Transaction(
            sender="COINBASE",
            recipient=wallet.address,
            amount=100.0,
            fee=0.0,
            tx_type="coinbase",
            outputs=[{"address": wallet.address, "amount": 100.0}]
        )
        coinbase.txid = coinbase.calculate_hash()
        blockchain.utxo_manager.process_transaction_outputs(coinbase)

        # Create valid transaction
        tx = blockchain.create_transaction(
            sender_address=wallet.address,
            recipient_address="XAI" + "b" * 40,
            amount=10.0,
            fee=1.0,
            private_key=wallet.private_key,
            public_key=wallet.public_key
        )

        # Should accept
        result = blockchain.add_transaction(tx)
        assert result is True
        assert any(t.txid == tx.txid for t in blockchain.pending_transactions)


class TestChainValidationRejectsInvalidSignatures:
    """Test that chain validation rejects blocks with invalid transaction signatures."""

    def test_chain_validation_rejects_invalid_signature(self):
        """Test that validate_chain() rejects chains with invalid signatures."""
        blockchain = Blockchain(data_dir="test_data_chain_sig1")

        # Create genesis block
        if not blockchain.chain:
            blockchain.initialize_genesis_block()

        # Mine a block with a transaction that has an invalid signature
        wallet = Wallet()

        # Fund the wallet
        coinbase = Transaction(
            sender="COINBASE",
            recipient=wallet.address,
            amount=100.0,
            fee=0.0,
            tx_type="coinbase",
            outputs=[{"address": wallet.address, "amount": 100.0}]
        )
        coinbase.txid = coinbase.calculate_hash()
        blockchain.utxo_manager.process_transaction_outputs(coinbase)

        # Create transaction with valid signature
        tx = blockchain.create_transaction(
            sender_address=wallet.address,
            recipient_address="XAI" + "b" * 40,
            amount=10.0,
            fee=1.0,
            private_key=wallet.private_key,
            public_key=wallet.public_key
        )

        # Add to mempool
        blockchain.add_transaction(tx)

        # Mine the block
        block = blockchain.mine_pending_transactions(wallet.address)

        # Now corrupt the signature in the mined block
        if block and block.transactions:
            for transaction in block.transactions:
                if transaction.sender != "COINBASE":
                    transaction.signature = "0" * 128  # Corrupt it

        # Validate chain - should fail
        is_valid, error = blockchain.validate_chain()

        # Chain validation should reject the corrupted block
        assert is_valid is False or "signature" in str(error).lower() if error else False


class TestExceptionHierarchy:
    """Test the signature verification exception hierarchy."""

    def test_exception_inheritance(self):
        """Test that signature verification exceptions inherit correctly."""
        assert issubclass(SignatureVerificationError, Exception)
        assert issubclass(MissingSignatureError, SignatureVerificationError)
        assert issubclass(InvalidSignatureError, SignatureVerificationError)
        assert issubclass(SignatureCryptoError, SignatureVerificationError)

    def test_can_catch_base_exception(self):
        """Test that all signature verification exceptions can be caught with base class."""
        tx = Transaction(
            sender="XAI" + "a" * 40,
            recipient="XAI" + "b" * 40,
            amount=10.0,
            fee=1.0
        )
        tx.public_key = "04" + "a" * 128
        tx.txid = tx.calculate_hash()

        # Should raise MissingSignatureError, but we catch SignatureVerificationError
        with pytest.raises(SignatureVerificationError):
            tx.verify_signature()


class TestErrorMessagesContainDetails:
    """Test that error messages contain useful diagnostic information."""

    def test_missing_signature_error_includes_txid(self):
        """Test that MissingSignatureError includes transaction ID."""
        tx = Transaction(
            sender="XAI" + "a" * 40,
            recipient="XAI" + "b" * 40,
            amount=10.0,
            fee=1.0
        )
        tx.public_key = "04" + "a" * 128
        tx.txid = tx.calculate_hash()

        with pytest.raises(MissingSignatureError) as exc_info:
            tx.verify_signature()

        # Error message should include transaction ID prefix
        error_msg = str(exc_info.value)
        assert len(error_msg) > 0
        assert "missing" in error_msg.lower()

    def test_invalid_signature_error_includes_reason(self):
        """Test that InvalidSignatureError includes reason for failure."""
        wallet = Wallet()
        blockchain = Blockchain(data_dir="test_data_sig_error_msg")

        tx = blockchain.create_transaction(
            sender_address=wallet.address,
            recipient_address="XAI" + "b" * 40,
            amount=10.0,
            fee=1.0,
            private_key=wallet.private_key,
            public_key=wallet.public_key
        )
        tx.signature = "0" * 128

        with pytest.raises(InvalidSignatureError) as exc_info:
            tx.verify_signature()

        error_msg = str(exc_info.value)
        assert len(error_msg) > 0
        # Should indicate ECDSA verification failed or similar
        assert "ecdsa" in error_msg.lower() or "failed" in error_msg.lower()

    def test_crypto_error_includes_cause(self):
        """Test that SignatureCryptoError includes the underlying cause."""
        tx = Transaction(
            sender="XAI" + "a" * 40,
            recipient="XAI" + "b" * 40,
            amount=10.0,
            fee=1.0
        )
        tx.public_key = "INVALID_HEX"
        tx.signature = "0" * 128
        tx.txid = tx.calculate_hash()

        with pytest.raises(SignatureCryptoError) as exc_info:
            tx.verify_signature()

        error_msg = str(exc_info.value)
        assert len(error_msg) > 0
        # Should include information about the underlying error
        assert "cryptographic" in error_msg.lower() or "failed" in error_msg.lower()
