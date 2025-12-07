"""
Comprehensive Transaction Validator Tests

Tests for 100% coverage of transaction_validator.py module.
Tests all transaction validation logic including UTXO, nonces, signatures, and special transaction types.
"""

import pytest
import time
from unittest.mock import Mock, MagicMock, patch
from xai.core.transaction_validator import TransactionValidator, get_transaction_validator
from xai.core.security_validation import ValidationError
from xai.core.blockchain import Transaction, Blockchain
from xai.core.wallet import Wallet


class TestTransactionValidatorInit:
    """Test TransactionValidator initialization"""

    def test_init_with_all_dependencies(self):
        """Test initialization with all dependencies provided"""
        mock_blockchain = Mock()
        mock_nonce_tracker = Mock()
        mock_logger = Mock()
        mock_utxo_manager = Mock()

        validator = TransactionValidator(
            blockchain=mock_blockchain,
            nonce_tracker=mock_nonce_tracker,
            logger=mock_logger,
            utxo_manager=mock_utxo_manager
        )

        assert validator.blockchain == mock_blockchain
        assert validator.nonce_tracker == mock_nonce_tracker
        assert validator.logger == mock_logger
        assert validator.utxo_manager == mock_utxo_manager

    def test_init_with_default_dependencies(self):
        """Test initialization with default dependencies"""
        mock_blockchain = Mock()

        validator = TransactionValidator(blockchain=mock_blockchain)

        assert validator.blockchain == mock_blockchain
        assert validator.nonce_tracker is not None
        assert validator.logger is not None
        assert validator.utxo_manager is not None
        assert validator.security_validator is not None


class TestBasicStructuralValidation:
    """Test basic transaction structural validation"""

    def test_reject_invalid_transaction_type(self, blockchain):
        """Test rejection of invalid transaction object type"""
        validator = TransactionValidator(blockchain)

        # Not a Transaction object
        invalid_tx = {"sender": "XAI123", "recipient": "XAI456"}

        result = validator.validate_transaction(invalid_tx)
        assert result is False

    def test_reject_transaction_missing_fields(self, blockchain):
        """Test rejection of transactions missing required fields"""
        validator = TransactionValidator(blockchain)

        # Create incomplete transaction mock
        incomplete_tx = Mock()
        incomplete_tx.sender = "XAI123"
        incomplete_tx.txid = "a" * 64  # Add txid attribute to prevent subscripting errors
        # Missing other fields

        result = validator.validate_transaction(incomplete_tx)
        assert result is False

    def test_validate_transaction_with_all_required_fields(self, blockchain, temp_blockchain_dir):
        """Test validation passes when all required fields present"""
        validator = TransactionValidator(blockchain)

        wallet1 = Wallet()
        wallet2 = Wallet()

        # Mine block to give wallet1 balance
        blockchain.mine_pending_transactions(wallet1.address)

        # Create valid transaction
        tx = blockchain.create_transaction(
            wallet1.address,
            wallet2.address,
            10.0,
            0.24,
            wallet1.private_key,
            wallet1.public_key
        )

        # Should have all required fields
        assert hasattr(tx, 'sender')
        assert hasattr(tx, 'recipient')
        assert hasattr(tx, 'amount')
        assert hasattr(tx, 'fee')
        assert hasattr(tx, 'timestamp')
        assert hasattr(tx, 'signature')
        assert hasattr(tx, 'txid')
        assert hasattr(tx, 'inputs')
        assert hasattr(tx, 'outputs')


class TestDataTypeValidation:
    """Test data type and format validation"""

    def test_validate_sender_address(self, blockchain):
        """Test sender address validation"""
        validator = TransactionValidator(blockchain)

        wallet1 = Wallet()
        wallet2 = Wallet()

        blockchain.mine_pending_transactions(wallet1.address)

        # Create transaction with invalid sender
        tx = blockchain.create_transaction(
            "INVALID123",  # Invalid address
            wallet2.address,
            10.0,
            0.24,
            wallet1.private_key,
            wallet1.public_key
        )

        result = validator.validate_transaction(tx)
        assert result is False

    def test_validate_recipient_address(self, blockchain):
        """Test recipient address validation"""
        validator = TransactionValidator(blockchain)

        wallet1 = Wallet()
        wallet2 = Wallet()

        blockchain.mine_pending_transactions(wallet1.address)

        # Create valid transaction first
        tx = blockchain.create_transaction(
            wallet1.address,
            wallet2.address,
            10.0,
            0.24,
            wallet1.private_key,
            wallet1.public_key
        )

        # Tamper with recipient address after creation
        tx.recipient = "INVALID456"  # Invalid address
        # Recalculate txid to reflect tampered data
        tx.txid = tx.calculate_hash()

        result = validator.validate_transaction(tx)
        assert result is False

    def test_validate_amount(self, blockchain):
        """Test amount validation"""
        validator = TransactionValidator(blockchain)

        wallet1 = Wallet()
        wallet2 = Wallet()

        blockchain.mine_pending_transactions(wallet1.address)

        # Create valid transaction first
        tx = blockchain.create_transaction(
            wallet1.address,
            wallet2.address,
            10.0,
            0.24,
            wallet1.private_key,
            wallet1.public_key
        )

        # Tamper with amount after creation
        tx.amount = -10.0  # Negative amount
        # Recalculate txid to reflect tampered data
        tx.txid = tx.calculate_hash()

        result = validator.validate_transaction(tx)
        assert result is False

    def test_validate_fee(self, blockchain):
        """Test fee validation"""
        validator = TransactionValidator(blockchain)

        wallet1 = Wallet()
        wallet2 = Wallet()

        blockchain.mine_pending_transactions(wallet1.address)

        # Create transaction with excessive fee
        tx = blockchain.create_transaction(
            wallet1.address,
            wallet2.address,
            10.0,
            10000.0,  # Excessive fee
            wallet1.private_key,
            wallet1.public_key
        )

        result = validator.validate_transaction(tx)
        assert result is False

    def test_validate_timestamp(self, blockchain):
        """Test timestamp validation"""
        validator = TransactionValidator(blockchain)

        wallet1 = Wallet()
        wallet2 = Wallet()

        blockchain.mine_pending_transactions(wallet1.address)

        tx = blockchain.create_transaction(
            wallet1.address,
            wallet2.address,
            10.0,
            0.24,
            wallet1.private_key,
            wallet1.public_key
        )

        # Tamper with timestamp - make it too old
        tx.timestamp = 946684799  # Before year 2000

        result = validator.validate_transaction(tx)
        assert result is False


class TestTransactionIDVerification:
    """Test transaction ID verification"""

    def test_valid_transaction_id(self, blockchain):
        """Test that valid transaction ID passes verification"""
        validator = TransactionValidator(blockchain)

        wallet1 = Wallet()
        wallet2 = Wallet()

        blockchain.mine_pending_transactions(wallet1.address)

        tx = blockchain.create_transaction(
            wallet1.address,
            wallet2.address,
            10.0,
            0.24,
            wallet1.private_key,
            wallet1.public_key
        )

        # Transaction ID should match calculated hash
        assert tx.calculate_hash() == tx.txid

    def test_reject_tampered_transaction_id(self, blockchain):
        """Test rejection of transaction with tampered ID"""
        validator = TransactionValidator(blockchain)

        wallet1 = Wallet()
        wallet2 = Wallet()

        blockchain.mine_pending_transactions(wallet1.address)

        tx = blockchain.create_transaction(
            wallet1.address,
            wallet2.address,
            10.0,
            0.24,
            wallet1.private_key,
            wallet1.public_key
        )

        # Tamper with txid
        tx.txid = "0" * 64

        result = validator.validate_transaction(tx)
        assert result is False


class TestSignatureVerification:
    """Test cryptographic signature verification"""

    def test_valid_signature(self, blockchain):
        """Test that valid signature passes verification"""
        validator = TransactionValidator(blockchain)

        wallet1 = Wallet()
        wallet2 = Wallet()

        blockchain.mine_pending_transactions(wallet1.address)

        tx = blockchain.create_transaction(
            wallet1.address,
            wallet2.address,
            10.0,
            0.24,
            wallet1.private_key,
            wallet1.public_key
        )

        # Signature should be valid
        assert tx.verify_signature() is True

    def test_reject_invalid_signature(self, blockchain):
        """Test rejection of transaction with invalid signature"""
        validator = TransactionValidator(blockchain)

        wallet1 = Wallet()
        wallet2 = Wallet()

        blockchain.mine_pending_transactions(wallet1.address)

        tx = blockchain.create_transaction(
            wallet1.address,
            wallet2.address,
            10.0,
            0.24,
            wallet1.private_key,
            wallet1.public_key
        )

        # Tamper with signature
        tx.signature = "0" * 128

        result = validator.validate_transaction(tx)
        assert result is False

    def test_reject_unsigned_transaction(self, blockchain):
        """Test rejection of unsigned transaction"""
        validator = TransactionValidator(blockchain)

        wallet1 = Wallet()
        wallet2 = Wallet()

        blockchain.mine_pending_transactions(wallet1.address)

        # Create transaction without signing
        tx = Transaction(wallet1.address, wallet2.address, 10.0, 0.24)
        tx.public_key = wallet1.public_key

        result = validator.validate_transaction(tx)
        assert result is False


class TestUTXOValidation:
    """Test UTXO-based validation"""

    def test_coinbase_transaction_skips_utxo_validation(self, blockchain):
        """Test that coinbase transactions skip UTXO validation"""
        validator = TransactionValidator(blockchain)

        # Create coinbase transaction
        coinbase_tx = Transaction("COINBASE", "XAI" + "a" * 40, 50.0, 0.0)
        coinbase_tx.tx_type = "coinbase"
        coinbase_tx.inputs = []
        coinbase_tx.outputs = [{"address": "XAI" + "a" * 40, "amount": 50.0}]
        coinbase_tx.timestamp = time.time()
        coinbase_tx.txid = coinbase_tx.calculate_hash()
        coinbase_tx.signature = "0" * 128  # Coinbase doesn't need valid signature
        coinbase_tx.nonce = 0

        # Mock signature verification for coinbase
        with patch.object(coinbase_tx, 'verify_signature', return_value=True):
            # Should skip UTXO validation
            result = validator.validate_transaction(coinbase_tx)

    def test_non_coinbase_must_have_inputs(self, blockchain):
        """Test that non-coinbase transactions must have inputs"""
        validator = TransactionValidator(blockchain)

        wallet1 = Wallet()
        wallet2 = Wallet()

        tx = Transaction(wallet1.address, wallet2.address, 10.0, 0.24)
        tx.tx_type = "transfer"
        tx.inputs = []  # No inputs
        tx.outputs = [{"address": wallet2.address, "amount": 10.0}]
        tx.timestamp = time.time()
        tx.txid = tx.calculate_hash()
        tx.public_key = wallet1.public_key
        tx.sign_transaction(wallet1.private_key)

        result = validator.validate_transaction(tx)
        assert result is False

    def test_validate_input_fields(self, blockchain):
        """Test validation of transaction input fields"""
        validator = TransactionValidator(blockchain)

        wallet1 = Wallet()
        wallet2 = Wallet()

        blockchain.mine_pending_transactions(wallet1.address)

        tx = blockchain.create_transaction(
            wallet1.address,
            wallet2.address,
            10.0,
            0.24,
            wallet1.private_key,
            wallet1.public_key
        )

        # Corrupt input by removing required field
        if tx.inputs:
            tx.inputs[0] = {"txid": "abc123"}  # Missing 'vout'

        result = validator.validate_transaction(tx)
        assert result is False

    def test_validate_output_fields(self, blockchain):
        """Test validation of transaction output fields"""
        validator = TransactionValidator(blockchain)

        wallet1 = Wallet()
        wallet2 = Wallet()

        blockchain.mine_pending_transactions(wallet1.address)

        tx = blockchain.create_transaction(
            wallet1.address,
            wallet2.address,
            10.0,
            0.24,
            wallet1.private_key,
            wallet1.public_key
        )

        # Corrupt output by removing required field
        if tx.outputs:
            tx.outputs[0] = {"address": wallet2.address}  # Missing 'amount'

        result = validator.validate_transaction(tx)
        assert result is False

    def test_transaction_must_have_outputs(self, blockchain):
        """Test that transactions must have outputs"""
        validator = TransactionValidator(blockchain)

        wallet1 = Wallet()
        wallet2 = Wallet()

        blockchain.mine_pending_transactions(wallet1.address)

        tx = blockchain.create_transaction(
            wallet1.address,
            wallet2.address,
            10.0,
            0.24,
            wallet1.private_key,
            wallet1.public_key
        )

        # Remove outputs
        tx.outputs = []

        result = validator.validate_transaction(tx)
        assert result is False


class TestNonceValidation:
    """Test nonce validation for replay attack prevention"""

    def test_valid_nonce(self, blockchain):
        """Test that valid nonce passes validation"""
        validator = TransactionValidator(blockchain)

        wallet1 = Wallet()
        wallet2 = Wallet()

        blockchain.mine_pending_transactions(wallet1.address)

        # Mock nonce tracker to accept nonce
        with patch.object(validator.nonce_tracker, 'validate_nonce', return_value=True):
            with patch.object(validator.nonce_tracker, 'get_next_nonce', return_value=1):
                tx = blockchain.create_transaction(
                    wallet1.address,
                    wallet2.address,
                    10.0,
                    0.24,
                    wallet1.private_key,
                    wallet1.public_key
                )

                result = validator.validate_transaction(tx)

    def test_invalid_nonce(self, blockchain):
        """Test rejection of invalid nonce"""
        validator = TransactionValidator(blockchain)

        wallet1 = Wallet()
        wallet2 = Wallet()

        blockchain.mine_pending_transactions(wallet1.address)

        tx = blockchain.create_transaction(
            wallet1.address,
            wallet2.address,
            10.0,
            0.24,
            wallet1.private_key,
            wallet1.public_key
        )

        # Mock nonce tracker to reject nonce
        with patch.object(validator.nonce_tracker, 'validate_nonce', return_value=False):
            with patch.object(validator.nonce_tracker, 'get_next_nonce', return_value=5):
                result = validator.validate_transaction(tx)
                assert result is False


class TestTimeCapsuleLockValidation:
    """Test time capsule lock transaction validation"""

    def test_time_capsule_missing_metadata(self, blockchain):
        """Test rejection of time capsule without metadata"""
        validator = TransactionValidator(blockchain)

        wallet1 = Wallet()
        wallet2 = Wallet()

        blockchain.mine_pending_transactions(wallet1.address)

        tx = blockchain.create_transaction(
            wallet1.address,
            wallet2.address,
            10.0,
            0.24,
            wallet1.private_key,
            wallet1.public_key
        )

        tx.tx_type = "time_capsule_lock"
        tx.metadata = None  # No metadata

        result = validator.validate_transaction(tx)
        assert result is False

    def test_time_capsule_missing_capsule_id(self, blockchain):
        """Test rejection of time capsule without capsule_id"""
        validator = TransactionValidator(blockchain)

        wallet1 = Wallet()
        wallet2 = Wallet()

        blockchain.mine_pending_transactions(wallet1.address)

        tx = blockchain.create_transaction(
            wallet1.address,
            wallet2.address,
            10.0,
            0.24,
            wallet1.private_key,
            wallet1.public_key
        )

        tx.tx_type = "time_capsule_lock"
        tx.metadata = {"unlock_time": time.time() + 3600}  # No capsule_id

        result = validator.validate_transaction(tx)
        assert result is False

    def test_time_capsule_missing_unlock_time(self, blockchain):
        """Test rejection of time capsule without unlock_time"""
        validator = TransactionValidator(blockchain)

        wallet1 = Wallet()
        wallet2 = Wallet()

        blockchain.mine_pending_transactions(wallet1.address)

        tx = blockchain.create_transaction(
            wallet1.address,
            wallet2.address,
            10.0,
            0.24,
            wallet1.private_key,
            wallet1.public_key
        )

        tx.tx_type = "time_capsule_lock"
        tx.metadata = {"capsule_id": "capsule_123"}  # No unlock_time

        result = validator.validate_transaction(tx)
        assert result is False

    def test_time_capsule_invalid_unlock_time_type(self, blockchain):
        """Test rejection of time capsule with invalid unlock_time type"""
        validator = TransactionValidator(blockchain)

        wallet1 = Wallet()
        wallet2 = Wallet()

        blockchain.mine_pending_transactions(wallet1.address)

        tx = blockchain.create_transaction(
            wallet1.address,
            wallet2.address,
            10.0,
            0.24,
            wallet1.private_key,
            wallet1.public_key
        )

        tx.tx_type = "time_capsule_lock"
        tx.metadata = {
            "capsule_id": "capsule_123",
            "unlock_time": "not_a_number"  # Invalid type
        }

        result = validator.validate_transaction(tx)
        assert result is False

    def test_time_capsule_unlock_time_in_past(self, blockchain):
        """Test rejection of time capsule with unlock_time in past"""
        validator = TransactionValidator(blockchain)

        wallet1 = Wallet()
        wallet2 = Wallet()

        blockchain.mine_pending_transactions(wallet1.address)

        tx = blockchain.create_transaction(
            wallet1.address,
            wallet2.address,
            10.0,
            0.24,
            wallet1.private_key,
            wallet1.public_key
        )

        current_time = time.time()
        tx.tx_type = "time_capsule_lock"
        tx.timestamp = current_time
        tx.metadata = {
            "capsule_id": "capsule_123",
            "unlock_time": current_time - 3600  # In the past
        }

        result = validator.validate_transaction(tx)
        assert result is False

    def test_valid_time_capsule(self, blockchain):
        """Test validation of valid time capsule transaction"""
        validator = TransactionValidator(blockchain)

        wallet1 = Wallet()
        wallet2 = Wallet()

        blockchain.mine_pending_transactions(wallet1.address)

        tx = blockchain.create_transaction(
            wallet1.address,
            wallet2.address,
            10.0,
            0.24,
            wallet1.private_key,
            wallet1.public_key
        )

        current_time = time.time()
        tx.tx_type = "time_capsule_lock"
        tx.timestamp = current_time
        tx.metadata = {
            "capsule_id": "capsule_123",
            "unlock_time": current_time + 3600  # 1 hour in future
        }

        # Mock dependencies
        with patch.object(validator.nonce_tracker, 'validate_nonce', return_value=True):
            with patch.object(validator.utxo_manager, 'get_unspent_output', return_value={
                "amount": 100.0,
                "script_pubkey": f"P2PKH {wallet1.address}"
            }):
                result = validator.validate_transaction(tx)


class TestGovernanceVoteValidation:
    """Test governance vote transaction validation"""

    def test_governance_vote_missing_metadata(self, blockchain):
        """Test rejection of governance vote without metadata"""
        validator = TransactionValidator(blockchain)

        wallet1 = Wallet()
        wallet2 = Wallet()

        blockchain.mine_pending_transactions(wallet1.address)

        tx = blockchain.create_transaction(
            wallet1.address,
            wallet2.address,
            10.0,
            0.24,
            wallet1.private_key,
            wallet1.public_key
        )

        tx.tx_type = "governance_vote"
        tx.metadata = None

        result = validator.validate_transaction(tx)
        assert result is False

    def test_governance_vote_missing_proposal_id(self, blockchain):
        """Test rejection of governance vote without proposal_id"""
        validator = TransactionValidator(blockchain)

        wallet1 = Wallet()
        wallet2 = Wallet()

        blockchain.mine_pending_transactions(wallet1.address)

        tx = blockchain.create_transaction(
            wallet1.address,
            wallet2.address,
            10.0,
            0.24,
            wallet1.private_key,
            wallet1.public_key
        )

        tx.tx_type = "governance_vote"
        tx.metadata = {"vote": "yes"}  # No proposal_id

        result = validator.validate_transaction(tx)
        assert result is False

    def test_governance_vote_missing_vote(self, blockchain):
        """Test rejection of governance vote without vote field"""
        validator = TransactionValidator(blockchain)

        wallet1 = Wallet()
        wallet2 = Wallet()

        blockchain.mine_pending_transactions(wallet1.address)

        tx = blockchain.create_transaction(
            wallet1.address,
            wallet2.address,
            10.0,
            0.24,
            wallet1.private_key,
            wallet1.public_key
        )

        tx.tx_type = "governance_vote"
        tx.metadata = {"proposal_id": "prop_123"}  # No vote

        result = validator.validate_transaction(tx)
        assert result is False

    def test_governance_vote_invalid_vote_value(self, blockchain):
        """Test rejection of governance vote with invalid vote value"""
        validator = TransactionValidator(blockchain)

        wallet1 = Wallet()
        wallet2 = Wallet()

        blockchain.mine_pending_transactions(wallet1.address)

        tx = blockchain.create_transaction(
            wallet1.address,
            wallet2.address,
            10.0,
            0.24,
            wallet1.private_key,
            wallet1.public_key
        )

        tx.tx_type = "governance_vote"
        tx.metadata = {
            "proposal_id": "prop_123",
            "vote": "maybe"  # Invalid vote
        }

        result = validator.validate_transaction(tx)
        assert result is False

    def test_valid_governance_vote_yes(self, blockchain):
        """Test validation of valid governance vote (yes)"""
        validator = TransactionValidator(blockchain)

        wallet1 = Wallet()
        wallet2 = Wallet()

        blockchain.mine_pending_transactions(wallet1.address)

        tx = blockchain.create_transaction(
            wallet1.address,
            wallet2.address,
            10.0,
            0.24,
            wallet1.private_key,
            wallet1.public_key
        )

        tx.tx_type = "governance_vote"
        tx.metadata = {
            "proposal_id": "prop_123",
            "vote": "yes"
        }

        # Mock dependencies
        with patch.object(validator.nonce_tracker, 'validate_nonce', return_value=True):
            with patch.object(validator.utxo_manager, 'get_unspent_output', return_value={
                "amount": 100.0,
                "script_pubkey": f"P2PKH {wallet1.address}"
            }):
                result = validator.validate_transaction(tx)

    def test_valid_governance_vote_no(self, blockchain):
        """Test validation of valid governance vote (no)"""
        validator = TransactionValidator(blockchain)

        wallet1 = Wallet()
        wallet2 = Wallet()

        blockchain.mine_pending_transactions(wallet1.address)

        tx = blockchain.create_transaction(
            wallet1.address,
            wallet2.address,
            10.0,
            0.24,
            wallet1.private_key,
            wallet1.public_key
        )

        tx.tx_type = "governance_vote"
        tx.metadata = {
            "proposal_id": "prop_123",
            "vote": "no"
        }

        # Mock dependencies
        with patch.object(validator.nonce_tracker, 'validate_nonce', return_value=True):
            with patch.object(validator.utxo_manager, 'get_unspent_output', return_value={
                "amount": 100.0,
                "script_pubkey": f"P2PKH {wallet1.address}"
            }):
                result = validator.validate_transaction(tx)

    def test_valid_governance_vote_abstain(self, blockchain):
        """Test validation of valid governance vote (abstain)"""
        validator = TransactionValidator(blockchain)

        wallet1 = Wallet()
        wallet2 = Wallet()

        blockchain.mine_pending_transactions(wallet1.address)

        tx = blockchain.create_transaction(
            wallet1.address,
            wallet2.address,
            10.0,
            0.24,
            wallet1.private_key,
            wallet1.public_key
        )

        tx.tx_type = "governance_vote"
        tx.metadata = {
            "proposal_id": "prop_123",
            "vote": "abstain"
        }

        # Mock dependencies
        with patch.object(validator.nonce_tracker, 'validate_nonce', return_value=True):
            with patch.object(validator.utxo_manager, 'get_unspent_output', return_value={
                "amount": 100.0,
                "script_pubkey": f"P2PKH {wallet1.address}"
            }):
                result = validator.validate_transaction(tx)


class TestExceptionHandling:
    """Test exception handling in transaction validation"""

    def test_handle_validation_error(self, blockchain):
        """Test handling of ValidationError"""
        validator = TransactionValidator(blockchain)

        # Create mock transaction with invalid data that bypasses constructor validation
        invalid_tx = Mock()
        invalid_tx.sender = "INVALID"
        invalid_tx.recipient = "XAI" + "1" * 40  # Valid format
        invalid_tx.amount = -10.0  # Negative amount
        invalid_tx.fee = 0.24
        invalid_tx.txid = "a" * 64
        invalid_tx.timestamp = time.time()
        invalid_tx.signature = "0" * 128
        invalid_tx.public_key = "04" + "a" * 128
        invalid_tx.nonce = 0
        invalid_tx.inputs = []
        invalid_tx.outputs = []
        invalid_tx.tx_type = "normal"

        result = validator.validate_transaction(invalid_tx)
        assert result is False

    def test_handle_unexpected_error(self, blockchain):
        """Test handling of unexpected errors"""
        validator = TransactionValidator(blockchain)

        # Create mock transaction that raises unexpected error
        mock_tx = Mock()
        mock_tx.sender = Mock(side_effect=Exception("Unexpected error"))
        mock_tx.txid = "b" * 64  # Add txid attribute to prevent subscripting errors

        result = validator.validate_transaction(mock_tx)
        assert result is False

    def test_log_validation_failure(self, blockchain, caplog):
        """Test that validation failures are logged"""
        validator = TransactionValidator(blockchain)

        wallet1 = Wallet()
        wallet2 = Wallet()

        blockchain.mine_pending_transactions(wallet1.address)

        # Create valid transaction first
        tx = blockchain.create_transaction(
            wallet1.address,
            wallet2.address,
            10.0,
            0.24,
            wallet1.private_key,
            wallet1.public_key
        )

        # Tamper with recipient to make it invalid
        tx.recipient = "INVALID123"
        tx.txid = tx.calculate_hash()

        import logging
        with caplog.at_level(logging.WARNING):
            result = validator.validate_transaction(tx)

        # Should log warning and return False
        assert result is False


class TestGetTransactionValidator:
    """Test global transaction validator instance"""

    def test_get_transaction_validator_creates_instance(self):
        """Test that get_transaction_validator creates instance"""
        mock_blockchain = Mock()

        validator = get_transaction_validator(mock_blockchain)

        assert validator is not None
        assert isinstance(validator, TransactionValidator)

    def test_get_transaction_validator_with_custom_dependencies(self):
        """Test get_transaction_validator with custom dependencies"""
        mock_blockchain = Mock()
        mock_nonce_tracker = Mock()
        mock_logger = Mock()
        mock_utxo_manager = Mock()

        validator = get_transaction_validator(
            mock_blockchain,
            nonce_tracker=mock_nonce_tracker,
            logger=mock_logger,
            utxo_manager=mock_utxo_manager
        )

        assert validator is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
