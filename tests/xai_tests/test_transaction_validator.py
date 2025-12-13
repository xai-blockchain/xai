"""
Test suite for XAI Blockchain - Transaction Validator functionality.
"""

import pytest
import sys
import os
import time
from unittest.mock import Mock, MagicMock

# Add parent directory to path for imports

from xai.core.blockchain import Transaction, Block  # Import Block and Transaction for context
from xai.core.wallet import Wallet
from xai.core.security_validation import ValidationError
from xai.core.nonce_tracker import NonceTracker
from xai.core.structured_logger import StructuredLogger
from xai.core.transaction_validator import TransactionValidator, get_transaction_validator


# Fixture for a mock blockchain
@pytest.fixture
def mock_blockchain():
    mock_bc = Mock()
    mock_bc.get_balance.return_value = 1000.0  # Default sufficient balance
    return mock_bc


# Fixture for a mock nonce tracker
@pytest.fixture
def mock_nonce_tracker():
    mock_nt = Mock(spec=NonceTracker)
    mock_nt.validate_nonce.return_value = True  # Default valid nonce
    mock_nt.get_next_nonce.return_value = 0
    return mock_nt


# Fixture for a mock logger
@pytest.fixture
def mock_logger():
    return Mock(spec=StructuredLogger)


# Fixture for a mock UTXO manager
@pytest.fixture
def mock_utxo_manager():
    mock_utxo = Mock()
    # Return a valid UTXO for any request
    mock_utxo.get_unspent_output.return_value = {
        "amount": 100.0,
        "script_pubkey": "P2PKH XAI1234567890",  # Will be updated per transaction
    }
    return mock_utxo


# Fixture for a TransactionValidator instance
@pytest.fixture
def validator(mock_blockchain, mock_nonce_tracker, mock_logger, mock_utxo_manager):
    return TransactionValidator(mock_blockchain, mock_nonce_tracker, mock_logger, mock_utxo_manager)


# Fixture for a valid transaction
@pytest.fixture
def valid_transaction(mock_utxo_manager):
    wallet1 = Wallet()
    wallet2 = Wallet()
    # Create transaction with proper inputs
    tx = Transaction(
        wallet1.address,
        wallet2.address,
        10.0,
        0.24,
        public_key=wallet1.public_key,
        nonce=0,
        inputs=[{"txid": "a" * 64, "vout": 0}],
        outputs=[{"address": wallet2.address, "amount": 10.0}],
    )
    # Update mock UTXO to match sender
    mock_utxo_manager.get_unspent_output.return_value = {
        "amount": 100.0,
        "script_pubkey": f"P2PKH {wallet1.address}",
    }
    tx.sign_transaction(wallet1.private_key)
    return tx


class TestTransactionValidator:
    """Tests for the TransactionValidator class."""

    def test_valid_transaction(self, validator, valid_transaction):
        """Test that a well-formed and valid transaction passes validation."""
        assert validator.validate_transaction(valid_transaction) is True
        validator.logger.debug.assert_called_once()

    def test_invalid_transaction_object_type(self, validator):
        """Test validation fails for an object that is not a Transaction."""
        result = validator.validate_transaction(Mock())
        assert result is False
        validator.logger.warn.assert_called_once()

    def test_missing_required_fields(self, validator):
        """Test validation fails if a transaction is missing required fields."""
        # Note: We use a Mock to simulate missing attributes
        # Creating a real Transaction with invalid addresses would fail validation

        # Mock the Transaction class to simulate missing attributes
        mock_tx = Mock(spec=Transaction)
        mock_tx.sender = "sender"
        mock_tx.recipient = "recipient"
        mock_tx.amount = 10.0
        mock_tx.fee = 0.24
        mock_tx.timestamp = time.time()
        mock_tx.signature = "validsignature"
        mock_tx.txid = "validtxid"
        mock_tx.public_key = "validpublickey"
        mock_tx.tx_type = "normal"
        mock_tx.nonce = 0
        mock_tx.calculate_hash.return_value = "validtxid"
        mock_tx.verify_signature.return_value = True

        # Remove an attribute to simulate missing field
        del mock_tx.recipient

        result = validator.validate_transaction(mock_tx)
        assert result is False
        validator.logger.warn.assert_called_once()

    def test_txid_mismatch(self, validator, valid_transaction):
        """Test validation fails if transaction ID does not match calculated hash."""
        valid_transaction.txid = "tampered_txid"
        result = validator.validate_transaction(valid_transaction)
        assert result is False
        validator.logger.warn.assert_called_once()

    def test_invalid_signature(self, validator, valid_transaction):
        """Test validation fails if transaction signature is invalid."""
        validator.blockchain.get_balance.return_value = 1000.0  # Ensure balance is not an issue
        valid_transaction.verify_signature = Mock(return_value=False)
        result = validator.validate_transaction(valid_transaction)
        assert result is False
        validator.logger.warn.assert_called_once()

    def test_insufficient_funds(self, validator, valid_transaction, mock_utxo_manager):
        """Test validation fails if sender has insufficient funds."""
        # Set UTXO amount to less than transaction amount + fee (10.0 + 0.24)
        mock_utxo_manager.get_unspent_output.return_value = {
            "amount": 5.0,  # Insufficient
            "script_pubkey": f"P2PKH {valid_transaction.sender}",
        }
        result = validator.validate_transaction(valid_transaction)
        assert result is False
        validator.logger.warn.assert_called_once()

    def test_coinbase_transaction_always_valid(self, validator):
        """Test that coinbase transactions bypass certain checks."""
        coinbase_tx = Transaction(
            "COINBASE",
            "miner_address",
            50.0,
            fee=0.0,
            tx_type="coinbase",
            inputs=[],
            outputs=[{"address": "miner_address", "amount": 50.0}]
        )
        coinbase_tx.txid = coinbase_tx.calculate_hash()
        coinbase_tx.signature = None  # Coinbase transactions don't have signatures
        coinbase_tx.public_key = None

        assert validator.validate_transaction(coinbase_tx) is True
        validator.logger.debug.assert_called_once()

    def test_invalid_nonce(self, validator, valid_transaction, mock_nonce_tracker):
        """Test validation fails if nonce is invalid."""
        mock_nonce_tracker.validate_nonce.return_value = False
        mock_nonce_tracker.get_next_nonce.return_value = (
            1  # Simulate expected nonce is 1, but tx.nonce is 0
        )
        mock_nonce_tracker.get_nonce.return_value = (
            1  # Ensure backward-compatible check doesn't allow it
        )
        result = validator.validate_transaction(valid_transaction)
        assert result is False
        validator.logger.warn.assert_called_once()

    def test_time_capsule_lock_validation(self, validator, mock_utxo_manager):
        """Test validation for time_capsule_lock transaction type."""
        wallet1 = Wallet()
        wallet2 = Wallet()
        tx = Transaction(
            wallet1.address,
            wallet2.address,
            10.0,
            0.24,
            public_key=wallet1.public_key,
            tx_type="time_capsule_lock",
            nonce=0,
            inputs=[{"txid": "a" * 64, "vout": 0}],
            outputs=[{"address": wallet2.address, "amount": 10.0}],
        )
        # Setup mock UTXO
        mock_utxo_manager.get_unspent_output.return_value = {
            "amount": 100.0,
            "script_pubkey": f"P2PKH {wallet1.address}",
        }

        # Valid metadata (set before signing)
        tx.metadata = {
            "capsule_id": "abc123xyz",
            "unlock_time": time.time() + 3600,  # 1 hour in future
        }
        tx.sign_transaction(wallet1.private_key)
        assert validator.validate_transaction(tx) is True

        # Missing capsule_id - need to re-sign after metadata change
        tx.metadata = {"unlock_time": time.time() + 3600}
        tx.sign_transaction(wallet1.private_key)
        result = validator.validate_transaction(tx)
        assert result is False
        validator.logger.warn.assert_called()
        validator.logger.warn.reset_mock()  # Reset mock call count

        # Invalid unlock_time (in past) - validator catches this and returns False, not raises
        tx.metadata = {
            "capsule_id": "abc123xyz",
            "unlock_time": time.time() - 3600,  # 1 hour in past
        }
        tx.sign_transaction(wallet1.private_key)
        result = validator.validate_transaction(tx)
        assert result is False
        validator.logger.warn.assert_called()

    def test_governance_vote_validation(self, validator, mock_utxo_manager):
        """Test validation for governance_vote transaction type."""
        wallet1 = Wallet()
        wallet2 = Wallet()

        # Valid metadata (set first)
        tx = Transaction(
            wallet1.address,
            wallet2.address,
            0.0,
            0.0,
            public_key=wallet1.public_key,
            tx_type="governance_vote",
            nonce=0,
            inputs=[{"txid": "a" * 64, "vout": 0}],
            outputs=[{"address": wallet2.address, "amount": 0.0}],
        )
        # Setup mock UTXO
        mock_utxo_manager.get_unspent_output.return_value = {
            "amount": 100.0,
            "script_pubkey": f"P2PKH {wallet1.address}",
        }

        tx.metadata = {"proposal_id": "prop_123", "vote": "yes"}
        tx.sign_transaction(wallet1.private_key)
        assert validator.validate_transaction(tx) is True

        # Missing proposal_id
        tx.metadata = {"vote": "no"}
        tx.sign_transaction(wallet1.private_key)
        result = validator.validate_transaction(tx)
        assert result is False
        validator.logger.warn.assert_called()
        validator.logger.warn.reset_mock()

        # Invalid vote
        tx.metadata = {"proposal_id": "prop_123", "vote": "abstain_invalid"}
        tx.sign_transaction(wallet1.private_key)
        result = validator.validate_transaction(tx)
        assert result is False
        validator.logger.warn.assert_called()

    def test_unexpected_exception_handling(self, validator, valid_transaction):
        """Test that unexpected exceptions during validation are caught and logged."""
        # Simulate an unexpected error during signature verification
        valid_transaction.verify_signature = Mock(side_effect=Exception("Unexpected crypto error"))

        assert validator.validate_transaction(valid_transaction) is False
        validator.logger.error.assert_called_once()

    def test_get_transaction_validator_singleton(
        self, mock_blockchain, mock_nonce_tracker, mock_logger
    ):
        """Test that get_transaction_validator returns a singleton instance."""
        validator1 = get_transaction_validator(mock_blockchain, mock_nonce_tracker, mock_logger)
        validator2 = get_transaction_validator(mock_blockchain, mock_nonce_tracker, mock_logger)
        assert validator1 is validator2
        assert isinstance(validator1, TransactionValidator)
