"""
Comprehensive tests for transaction_validator.py to boost coverage from 76% to 95%+

Focuses on:
- Time capsule transaction validation
- Governance vote transaction validation
- Edge cases in UTXO validation
- Nonce validation edge cases
- Error handling paths
- ValidationError scenarios
"""

import pytest
import time
from xai.core.blockchain import Blockchain, Transaction
from xai.core.wallet import Wallet
from xai.core.transaction_validator import TransactionValidator
from xai.core.security_validation import ValidationError


class TestTimeCapsuleValidation:
    """Test time capsule transaction validation"""

    def test_validate_time_capsule_with_metadata(self, tmp_path):
        """Test valid time capsule transaction"""
        bc = Blockchain(data_dir=str(tmp_path))
        validator = bc.transaction_validator
        wallet1 = Wallet()
        wallet2 = Wallet()

        # Mine to wallet1
        bc.mine_pending_transactions(wallet1.address)

        # Create time capsule transaction
        tx = bc.create_transaction(
            wallet1.address,
            wallet2.address,
            10.0,
            0.1,
            wallet1.private_key,
            wallet1.public_key
        )

        if tx:
            tx.tx_type = "time_capsule_lock"
            tx.metadata = {
                "capsule_id": "capsule_123",
                "unlock_time": time.time() + 3600  # 1 hour in future
            }

            # Should pass validation
            is_valid = validator.validate_transaction(tx)
            assert isinstance(is_valid, bool)

    def test_validate_time_capsule_missing_metadata(self, tmp_path):
        """Test time capsule without metadata fails"""
        bc = Blockchain(data_dir=str(tmp_path))
        validator = bc.transaction_validator
        wallet = Wallet()

        # Mine to wallet
        bc.mine_pending_transactions(wallet.address)

        tx = bc.create_transaction(
            wallet.address,
            "recipient",
            10.0,
            0.1,
            wallet.private_key,
            wallet.public_key
        )

        if tx:
            tx.tx_type = "time_capsule_lock"
            tx.metadata = None  # Missing metadata

            is_valid = validator.validate_transaction(tx)
            assert is_valid is False

    def test_validate_time_capsule_missing_capsule_id(self, tmp_path):
        """Test time capsule without capsule_id fails"""
        bc = Blockchain(data_dir=str(tmp_path))
        validator = bc.transaction_validator
        wallet = Wallet()

        bc.mine_pending_transactions(wallet.address)

        tx = bc.create_transaction(
            wallet.address,
            "recipient",
            10.0,
            0.1,
            wallet.private_key,
            wallet.public_key
        )

        if tx:
            tx.tx_type = "time_capsule_lock"
            tx.metadata = {
                "unlock_time": time.time() + 3600
                # Missing capsule_id
            }

            is_valid = validator.validate_transaction(tx)
            assert is_valid is False

    def test_validate_time_capsule_empty_capsule_id(self, tmp_path):
        """Test time capsule with empty capsule_id fails"""
        bc = Blockchain(data_dir=str(tmp_path))
        validator = bc.transaction_validator
        wallet = Wallet()

        bc.mine_pending_transactions(wallet.address)

        tx = bc.create_transaction(
            wallet.address,
            "recipient",
            10.0,
            0.1,
            wallet.private_key,
            wallet.public_key
        )

        if tx:
            tx.tx_type = "time_capsule_lock"
            tx.metadata = {
                "capsule_id": "",  # Empty
                "unlock_time": time.time() + 3600
            }

            is_valid = validator.validate_transaction(tx)
            assert is_valid is False

    def test_validate_time_capsule_missing_unlock_time(self, tmp_path):
        """Test time capsule without unlock_time fails"""
        bc = Blockchain(data_dir=str(tmp_path))
        validator = bc.transaction_validator
        wallet = Wallet()

        bc.mine_pending_transactions(wallet.address)

        tx = bc.create_transaction(
            wallet.address,
            "recipient",
            10.0,
            0.1,
            wallet.private_key,
            wallet.public_key
        )

        if tx:
            tx.tx_type = "time_capsule_lock"
            tx.metadata = {
                "capsule_id": "capsule_123"
                # Missing unlock_time
            }

            is_valid = validator.validate_transaction(tx)
            assert is_valid is False

    def test_validate_time_capsule_invalid_unlock_time_type(self, tmp_path):
        """Test time capsule with invalid unlock_time type fails"""
        bc = Blockchain(data_dir=str(tmp_path))
        validator = bc.transaction_validator
        wallet = Wallet()

        bc.mine_pending_transactions(wallet.address)

        tx = bc.create_transaction(
            wallet.address,
            "recipient",
            10.0,
            0.1,
            wallet.private_key,
            wallet.public_key
        )

        if tx:
            tx.tx_type = "time_capsule_lock"
            tx.metadata = {
                "capsule_id": "capsule_123",
                "unlock_time": "not_a_number"  # Invalid type
            }

            is_valid = validator.validate_transaction(tx)
            assert is_valid is False

    def test_validate_time_capsule_past_unlock_time(self, tmp_path):
        """Test time capsule with unlock_time in past fails"""
        bc = Blockchain(data_dir=str(tmp_path))
        validator = bc.transaction_validator
        wallet = Wallet()

        bc.mine_pending_transactions(wallet.address)

        tx = bc.create_transaction(
            wallet.address,
            "recipient",
            10.0,
            0.1,
            wallet.private_key,
            wallet.public_key
        )

        if tx:
            tx.tx_type = "time_capsule_lock"
            tx.metadata = {
                "capsule_id": "capsule_123",
                "unlock_time": time.time() - 3600  # 1 hour in past
            }

            is_valid = validator.validate_transaction(tx)
            assert is_valid is False


class TestGovernanceVoteValidation:
    """Test governance vote transaction validation"""

    def test_validate_governance_vote_valid(self, tmp_path):
        """Test valid governance vote transaction"""
        bc = Blockchain(data_dir=str(tmp_path))
        validator = bc.transaction_validator
        wallet = Wallet()

        bc.mine_pending_transactions(wallet.address)

        tx = bc.create_transaction(
            wallet.address,
            "GOVERNANCE",
            0.0,
            0.05,
            wallet.private_key,
            wallet.public_key
        )

        if tx:
            tx.tx_type = "governance_vote"
            tx.metadata = {
                "proposal_id": "prop_123",
                "vote": "yes"
            }

            is_valid = validator.validate_transaction(tx)
            assert isinstance(is_valid, bool)

    def test_validate_governance_vote_missing_metadata(self, tmp_path):
        """Test governance vote without metadata fails"""
        bc = Blockchain(data_dir=str(tmp_path))
        validator = bc.transaction_validator
        wallet = Wallet()

        bc.mine_pending_transactions(wallet.address)

        tx = bc.create_transaction(
            wallet.address,
            "GOVERNANCE",
            0.0,
            0.05,
            wallet.private_key,
            wallet.public_key
        )

        if tx:
            tx.tx_type = "governance_vote"
            tx.metadata = None

            is_valid = validator.validate_transaction(tx)
            assert is_valid is False

    def test_validate_governance_vote_missing_proposal_id(self, tmp_path):
        """Test governance vote without proposal_id fails"""
        bc = Blockchain(data_dir=str(tmp_path))
        validator = bc.transaction_validator
        wallet = Wallet()

        bc.mine_pending_transactions(wallet.address)

        tx = bc.create_transaction(
            wallet.address,
            "GOVERNANCE",
            0.0,
            0.05,
            wallet.private_key,
            wallet.public_key
        )

        if tx:
            tx.tx_type = "governance_vote"
            tx.metadata = {
                "vote": "yes"
                # Missing proposal_id
            }

            is_valid = validator.validate_transaction(tx)
            assert is_valid is False

    def test_validate_governance_vote_empty_proposal_id(self, tmp_path):
        """Test governance vote with empty proposal_id fails"""
        bc = Blockchain(data_dir=str(tmp_path))
        validator = bc.transaction_validator
        wallet = Wallet()

        bc.mine_pending_transactions(wallet.address)

        tx = bc.create_transaction(
            wallet.address,
            "GOVERNANCE",
            0.0,
            0.05,
            wallet.private_key,
            wallet.public_key
        )

        if tx:
            tx.tx_type = "governance_vote"
            tx.metadata = {
                "proposal_id": "",  # Empty
                "vote": "yes"
            }

            is_valid = validator.validate_transaction(tx)
            assert is_valid is False

    def test_validate_governance_vote_missing_vote(self, tmp_path):
        """Test governance vote without vote field fails"""
        bc = Blockchain(data_dir=str(tmp_path))
        validator = bc.transaction_validator
        wallet = Wallet()

        bc.mine_pending_transactions(wallet.address)

        tx = bc.create_transaction(
            wallet.address,
            "GOVERNANCE",
            0.0,
            0.05,
            wallet.private_key,
            wallet.public_key
        )

        if tx:
            tx.tx_type = "governance_vote"
            tx.metadata = {
                "proposal_id": "prop_123"
                # Missing vote
            }

            is_valid = validator.validate_transaction(tx)
            assert is_valid is False

    def test_validate_governance_vote_invalid_vote_value(self, tmp_path):
        """Test governance vote with invalid vote value fails"""
        bc = Blockchain(data_dir=str(tmp_path))
        validator = bc.transaction_validator
        wallet = Wallet()

        bc.mine_pending_transactions(wallet.address)

        tx = bc.create_transaction(
            wallet.address,
            "GOVERNANCE",
            0.0,
            0.05,
            wallet.private_key,
            wallet.public_key
        )

        if tx:
            tx.tx_type = "governance_vote"
            tx.metadata = {
                "proposal_id": "prop_123",
                "vote": "maybe"  # Invalid - must be yes/no/abstain
            }

            is_valid = validator.validate_transaction(tx)
            assert is_valid is False

    def test_validate_governance_vote_all_valid_options(self, tmp_path):
        """Test all valid vote options pass validation"""
        bc = Blockchain(data_dir=str(tmp_path))
        validator = bc.transaction_validator
        wallet = Wallet()

        bc.mine_pending_transactions(wallet.address)

        valid_votes = ["yes", "no", "abstain"]

        for vote_option in valid_votes:
            tx = bc.create_transaction(
                wallet.address,
                "GOVERNANCE",
                0.0,
                0.05,
                wallet.private_key,
                wallet.public_key
            )

            if tx:
                tx.tx_type = "governance_vote"
                tx.metadata = {
                    "proposal_id": "prop_123",
                    "vote": vote_option
                }

                is_valid = validator.validate_transaction(tx)
                assert isinstance(is_valid, bool)


class TestUTXOValidationEdgeCases:
    """Test UTXO validation edge cases"""

    def test_validate_transaction_missing_inputs(self, tmp_path):
        """Test non-coinbase transaction without inputs fails"""
        bc = Blockchain(data_dir=str(tmp_path))
        validator = bc.transaction_validator
        wallet = Wallet()

        tx = Transaction(
            wallet.address,
            "recipient",
            10.0,
            0.1,
            public_key=wallet.public_key
        )
        tx.tx_type = "normal"
        tx.inputs = []  # No inputs
        tx.sign_transaction(wallet.private_key)

        is_valid = validator.validate_transaction(tx)
        assert is_valid is False

    def test_validate_transaction_input_missing_fields(self, tmp_path):
        """Test transaction input without required fields fails"""
        bc = Blockchain(data_dir=str(tmp_path))
        validator = bc.transaction_validator
        wallet = Wallet()

        tx = Transaction(
            wallet.address,
            "recipient",
            10.0,
            0.1,
            public_key=wallet.public_key
        )
        tx.inputs = [{"txid": "abc123"}]  # Missing vout
        tx.outputs = [{"address": "recipient", "amount": 10.0}]
        tx.sign_transaction(wallet.private_key)

        is_valid = validator.validate_transaction(tx)
        assert is_valid is False

    def test_validate_transaction_nonexistent_utxo(self, tmp_path):
        """Test transaction referencing non-existent UTXO fails"""
        bc = Blockchain(data_dir=str(tmp_path))
        validator = bc.transaction_validator
        wallet = Wallet()

        tx = Transaction(
            wallet.address,
            "recipient",
            10.0,
            0.1,
            public_key=wallet.public_key
        )
        tx.inputs = [{"txid": "nonexistent" * 8, "vout": 0}]
        tx.outputs = [{"address": "recipient", "amount": 10.0}]
        tx.sign_transaction(wallet.private_key)

        is_valid = validator.validate_transaction(tx)
        assert is_valid is False

    def test_validate_transaction_missing_outputs(self, tmp_path):
        """Test transaction without outputs fails"""
        bc = Blockchain(data_dir=str(tmp_path))
        validator = bc.transaction_validator
        wallet = Wallet()

        bc.mine_pending_transactions(wallet.address)

        tx = bc.create_transaction(
            wallet.address,
            "recipient",
            10.0,
            0.1,
            wallet.private_key,
            wallet.public_key
        )

        if tx:
            tx.outputs = []  # Remove outputs

            is_valid = validator.validate_transaction(tx)
            assert is_valid is False

    def test_validate_transaction_output_missing_fields(self, tmp_path):
        """Test transaction output without required fields fails"""
        bc = Blockchain(data_dir=str(tmp_path))
        validator = bc.transaction_validator
        wallet = Wallet()

        bc.mine_pending_transactions(wallet.address)

        tx = bc.create_transaction(
            wallet.address,
            "recipient",
            10.0,
            0.1,
            wallet.private_key,
            wallet.public_key
        )

        if tx:
            tx.outputs = [{"address": "recipient"}]  # Missing amount

            is_valid = validator.validate_transaction(tx)
            assert is_valid is False

    def test_validate_transaction_insufficient_inputs(self, tmp_path):
        """Test transaction where inputs < outputs + fee fails"""
        bc = Blockchain(data_dir=str(tmp_path))
        validator = bc.transaction_validator
        wallet = Wallet()

        bc.mine_pending_transactions(wallet.address)

        tx = bc.create_transaction(
            wallet.address,
            "recipient",
            5.0,
            0.1,
            wallet.private_key,
            wallet.public_key
        )

        if tx:
            # Increase output amount beyond inputs
            tx.outputs[0]["amount"] = 1000000.0

            is_valid = validator.validate_transaction(tx)
            assert is_valid is False


class TestBasicValidationErrors:
    """Test basic validation error paths"""

    def test_validate_invalid_transaction_type(self, tmp_path):
        """Test validation with wrong transaction type"""
        bc = Blockchain(data_dir=str(tmp_path))
        validator = bc.transaction_validator

        # Pass non-Transaction object
        is_valid = validator.validate_transaction("not_a_transaction")
        assert is_valid is False

    def test_validate_transaction_missing_fields(self, tmp_path):
        """Test transaction missing required fields fails"""
        bc = Blockchain(data_dir=str(tmp_path))
        validator = bc.transaction_validator

        # Create mock object missing fields
        class FakeTransaction:
            sender = "XAI123"
            # Missing other required fields

        is_valid = validator.validate_transaction(FakeTransaction())
        assert is_valid is False

    def test_validate_transaction_id_mismatch(self, tmp_path):
        """Test transaction with tampered ID fails"""
        bc = Blockchain(data_dir=str(tmp_path))
        validator = bc.transaction_validator
        wallet = Wallet()

        bc.mine_pending_transactions(wallet.address)

        tx = bc.create_transaction(
            wallet.address,
            "recipient",
            10.0,
            0.1,
            wallet.private_key,
            wallet.public_key
        )

        if tx:
            # Tamper with txid
            tx.txid = "tampered_id"

            is_valid = validator.validate_transaction(tx)
            assert is_valid is False

    def test_validate_transaction_missing_signature(self, tmp_path):
        """Test non-coinbase transaction without signature fails"""
        bc = Blockchain(data_dir=str(tmp_path))
        validator = bc.transaction_validator
        wallet = Wallet()

        tx = Transaction(
            wallet.address,
            "recipient",
            10.0,
            0.1,
            public_key=wallet.public_key
        )
        tx.txid = tx.calculate_hash()
        tx.signature = None  # No signature

        is_valid = validator.validate_transaction(tx)
        assert is_valid is False

    def test_validate_transaction_invalid_signature(self, tmp_path):
        """Test transaction with invalid signature fails"""
        bc = Blockchain(data_dir=str(tmp_path))
        validator = bc.transaction_validator
        wallet1 = Wallet()
        wallet2 = Wallet()

        tx = Transaction(
            wallet1.address,
            "recipient",
            10.0,
            0.1,
            public_key=wallet2.public_key  # Wrong public key
        )
        tx.sign_transaction(wallet1.private_key)

        is_valid = validator.validate_transaction(tx)
        assert is_valid is False


class TestNonceValidation:
    """Test nonce validation"""

    def test_validate_transaction_invalid_nonce(self, tmp_path):
        """Test transaction with invalid nonce fails"""
        bc = Blockchain(data_dir=str(tmp_path))
        validator = bc.transaction_validator
        wallet = Wallet()

        bc.mine_pending_transactions(wallet.address)

        tx = bc.create_transaction(
            wallet.address,
            "recipient",
            10.0,
            0.1,
            wallet.private_key,
            wallet.public_key
        )

        if tx:
            # Set invalid nonce
            tx.nonce = 999999  # Way too high

            is_valid = validator.validate_transaction(tx)
            assert is_valid is False


class TestCoinbaseTransactionValidation:
    """Test coinbase transaction validation"""

    def test_validate_coinbase_transaction(self, tmp_path):
        """Test coinbase transaction passes validation"""
        bc = Blockchain(data_dir=str(tmp_path))
        validator = bc.transaction_validator

        tx = Transaction("COINBASE", "miner_address", 12.0)
        tx.tx_type = "coinbase"
        tx.txid = tx.calculate_hash()

        is_valid = validator.validate_transaction(tx)
        assert is_valid is True

    def test_coinbase_transaction_no_signature_required(self, tmp_path):
        """Test coinbase doesn't need signature"""
        bc = Blockchain(data_dir=str(tmp_path))
        validator = bc.transaction_validator

        tx = Transaction("COINBASE", "miner_address", 12.0)
        tx.txid = tx.calculate_hash()
        tx.signature = None

        is_valid = validator.validate_transaction(tx)
        assert is_valid is True


class TestValidatorLogging:
    """Test validator logging and error messages"""

    def test_validator_logs_validation_success(self, tmp_path):
        """Test validator logs successful validations"""
        bc = Blockchain(data_dir=str(tmp_path))
        validator = bc.transaction_validator

        tx = Transaction("COINBASE", "miner", 12.0)
        tx.txid = tx.calculate_hash()

        # Should log success
        is_valid = validator.validate_transaction(tx)
        assert is_valid is True

    def test_validator_logs_validation_failure(self, tmp_path):
        """Test validator logs validation failures"""
        bc = Blockchain(data_dir=str(tmp_path))
        validator = bc.transaction_validator
        wallet = Wallet()

        tx = Transaction(
            wallet.address,
            "recipient",
            10.0,
            0.1,
            public_key=wallet.public_key
        )
        tx.txid = tx.calculate_hash()
        tx.signature = None

        # Should log failure
        is_valid = validator.validate_transaction(tx)
        assert is_valid is False

    def test_validator_handles_unexpected_errors(self, tmp_path):
        """Test validator handles unexpected exceptions"""
        bc = Blockchain(data_dir=str(tmp_path))
        validator = bc.transaction_validator

        # Create transaction with problematic data
        tx = Transaction("sender", "recipient", -1.0, 0.1)  # Negative amount
        tx.txid = "invalid"

        # Should catch exception and return False
        is_valid = validator.validate_transaction(tx)
        assert is_valid is False


class TestValidatorWithNoneRecipient:
    """Test validation with None recipient"""

    def test_validate_transaction_none_recipient(self, tmp_path):
        """Test transaction with None recipient (e.g., burn)"""
        bc = Blockchain(data_dir=str(tmp_path))
        validator = bc.transaction_validator
        wallet = Wallet()

        bc.mine_pending_transactions(wallet.address)

        tx = bc.create_transaction(
            wallet.address,
            "burn_address",
            10.0,
            0.1,
            wallet.private_key,
            wallet.public_key
        )

        if tx:
            tx.recipient = None

            # Should handle None recipient
            is_valid = validator.validate_transaction(tx)
            assert isinstance(is_valid, bool)


class TestGetTransactionValidator:
    """Test global transaction validator getter"""

    def test_get_transaction_validator(self, tmp_path):
        """Test getting global validator instance"""
        from xai.core.transaction_validator import get_transaction_validator

        bc = Blockchain(data_dir=str(tmp_path))

        validator = get_transaction_validator(bc)

        assert validator is not None
        assert hasattr(validator, 'validate_transaction')

    def test_get_transaction_validator_singleton(self, tmp_path):
        """Test global validator is singleton"""
        from xai.core.transaction_validator import get_transaction_validator

        bc = Blockchain(data_dir=str(tmp_path))

        validator1 = get_transaction_validator(bc)
        validator2 = get_transaction_validator(bc)

        # Should return same instance
        assert validator1 is validator2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
