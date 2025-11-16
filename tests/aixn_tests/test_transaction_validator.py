"""
Test suite for XAI Blockchain - Transaction Validator functionality.
"""

import pytest
import sys
import os
import time
from unittest.mock import Mock, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "core"))

from blockchain import Transaction, Block  # Import Block and Transaction for context
from wallet import Wallet
from security_validation import ValidationError
from nonce_tracker import NonceTracker
from structured_logger import StructuredLogger
from transaction_validator import TransactionValidator, get_transaction_validator


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


# Fixture for a TransactionValidator instance
@pytest.fixture
def validator(mock_blockchain, mock_nonce_tracker, mock_logger):
    return TransactionValidator(mock_blockchain, mock_nonce_tracker, mock_logger)


# Fixture for a valid transaction
@pytest.fixture
def valid_transaction():
    wallet1 = Wallet()
    wallet2 = Wallet()
    tx = Transaction(
        wallet1.address, wallet2.address, 10.0, 0.24, public_key=wallet1.public_key, nonce=0
    )
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
        with pytest.raises(ValidationError, match="Invalid transaction object type."):
            validator.validate_transaction(Mock())
        validator.logger.warn.assert_called_once()

    def test_missing_required_fields(self, validator):
        """Test validation fails if a transaction is missing required fields."""
        incomplete_tx = Transaction(
            "sender", "recipient", 10.0
        )  # Missing fee, public_key, nonce etc.
        incomplete_tx.txid = (
            incomplete_tx.calculate_hash()
        )  # Manually set txid to avoid hash mismatch first

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

        with pytest.raises(ValidationError, match="Transaction is missing required fields."):
            validator.validate_transaction(mock_tx)
        validator.logger.warn.assert_called_once()

    def test_txid_mismatch(self, validator, valid_transaction):
        """Test validation fails if transaction ID does not match calculated hash."""
        valid_transaction.txid = "tampered_txid"
        with pytest.raises(ValidationError, match="Transaction ID mismatch."):
            validator.validate_transaction(valid_transaction)
        validator.logger.warn.assert_called_once()

    def test_invalid_signature(self, validator, valid_transaction):
        """Test validation fails if transaction signature is invalid."""
        validator.blockchain.get_balance.return_value = 1000.0  # Ensure balance is not an issue
        valid_transaction.verify_signature = Mock(return_value=False)
        with pytest.raises(ValidationError, match="Invalid transaction signature."):
            validator.validate_transaction(valid_transaction)
        validator.logger.warn.assert_called_once()

    def test_insufficient_funds(self, validator, valid_transaction):
        """Test validation fails if sender has insufficient funds."""
        validator.blockchain.get_balance.return_value = 5.0  # Less than 10.0 + 0.24
        with pytest.raises(ValidationError, match="Insufficient funds for sender"):
            validator.validate_transaction(valid_transaction)
        validator.logger.warn.assert_called_once()

    def test_coinbase_transaction_always_valid(self, validator):
        """Test that coinbase transactions bypass certain checks."""
        coinbase_tx = Transaction("COINBASE", "miner_address", 50.0)
        coinbase_tx.txid = coinbase_tx.calculate_hash()

        # Mock signature verification to return False, should still pass
        coinbase_tx.verify_signature = Mock(return_value=False)

        assert validator.validate_transaction(coinbase_tx) is True
        validator.logger.debug.assert_called_once()

    def test_invalid_nonce(self, validator, valid_transaction, mock_nonce_tracker):
        """Test validation fails if nonce is invalid."""
        mock_nonce_tracker.validate_nonce.return_value = False
        mock_nonce_tracker.get_next_nonce.return_value = (
            1  # Simulate expected nonce is 1, but tx.nonce is 0
        )
        with pytest.raises(ValidationError, match="Invalid nonce for sender"):
            validator.validate_transaction(valid_transaction)
        validator.logger.warn.assert_called_once()

    def test_time_capsule_lock_validation(self, validator):
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
        )
        tx.sign_transaction(wallet1.private_key)

        # Valid metadata
        tx.metadata = {
            "capsule_id": "abc123xyz",
            "unlock_time": time.time() + 3600,  # 1 hour in future
        }
        assert validator.validate_transaction(tx) is True

        # Missing capsule_id
        tx.metadata = {"unlock_time": time.time() + 3600}
        with pytest.raises(ValidationError, match="Time capsule transaction missing capsule_id."):
            validator.validate_transaction(tx)
        validator.logger.warn.assert_called_once()
        validator.logger.warn.reset_mock()  # Reset mock call count

        # Invalid unlock_time (in past)
        tx.metadata = {
            "capsule_id": "abc123xyz",
            "unlock_time": time.time() - 3600,  # 1 hour in past
        }
        with pytest.raises(
            ValidationError, match="Time capsule unlock_time must be in the future."
        ):
            validator.validate_transaction(tx)
        validator.logger.warn.assert_called_once()

    def test_governance_vote_validation(self, validator):
        """Test validation for governance_vote transaction type."""
        wallet1 = Wallet()
        wallet2 = Wallet()
        tx = Transaction(
            wallet1.address,
            wallet2.address,
            0.0,
            0.0,
            public_key=wallet1.public_key,
            tx_type="governance_vote",
            nonce=0,
        )
        tx.sign_transaction(wallet1.private_key)

        # Valid metadata
        tx.metadata = {"proposal_id": "prop_123", "vote": "yes"}
        assert validator.validate_transaction(tx) is True

        # Missing proposal_id
        tx.metadata = {"vote": "no"}
        with pytest.raises(ValidationError, match="Governance vote missing proposal_id."):
            validator.validate_transaction(tx)
        validator.logger.warn.assert_called_once()
        validator.logger.warn.reset_mock()

        # Invalid vote
        tx.metadata = {"proposal_id": "prop_123", "vote": "abstain_invalid"}
        with pytest.raises(ValidationError, match="Governance vote missing valid vote."):
            validator.validate_transaction(tx)
        validator.logger.warn.assert_called_once()

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
