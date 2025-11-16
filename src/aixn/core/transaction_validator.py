"""
XAI Blockchain - Transaction Validator

Validates incoming transactions against a set of rules to ensure network integrity.
"""

from typing import Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from aixn.core.blockchain import Transaction

from aixn.core.wallet import Wallet
from aixn.core.security_validation import SecurityValidator, ValidationError
from aixn.core.nonce_tracker import NonceTracker, get_nonce_tracker
from aixn.core.structured_logger import StructuredLogger, get_structured_logger
from aixn.core.utxo_manager import UTXOManager, get_utxo_manager


class TransactionValidator:
    """
    Validates transactions before they are added to the transaction pool or a block.
    """

    def __init__(
        self,
        blockchain,
        nonce_tracker: Optional[NonceTracker] = None,
        logger: Optional[StructuredLogger] = None,
        utxo_manager: Optional[UTXOManager] = None,
    ):
        self.blockchain = blockchain
        self.nonce_tracker = nonce_tracker or get_nonce_tracker()
        self.logger = logger or get_structured_logger()
        self.security_validator = SecurityValidator()
        self.utxo_manager = utxo_manager or get_utxo_manager()

    def validate_transaction(
        self, transaction: "Transaction", is_mempool_check: bool = True
    ) -> bool:
        """
        Performs a comprehensive validation of a transaction.

        Args:
            transaction: The Transaction object to validate.
            is_mempool_check: True if validating for mempool, False if for block inclusion.

        Returns:
            True if the transaction is valid, False otherwise.
        """
        try:
            # 1. Basic structural validation
            if not isinstance(transaction, Transaction):
                raise ValidationError("Invalid transaction object type.")
            if not all(
                hasattr(transaction, attr)
                for attr in [
                    "sender",
                    "recipient",
                    "amount",
                    "fee",
                    "timestamp",
                    "signature",
                    "txid",
                    "inputs",
                    "outputs",
                ]
            ):
                raise ValidationError("Transaction is missing required fields.")

            # 2. Data type and format validation using SecurityValidator
            self.security_validator.validate_address(transaction.sender, "sender address")
            # Recipient can be None for some transaction types (e.g., burn)
            if transaction.recipient:
                self.security_validator.validate_address(transaction.recipient, "recipient address")
            self.security_validator.validate_amount(transaction.amount, "amount")
            self.security_validator.validate_fee(transaction.fee)
            self.security_validator.validate_timestamp(transaction.timestamp)
            self.security_validator.validate_hex_string(
                transaction.signature, "signature", exact_length=128
            )
            self.security_validator.validate_hex_string(
                transaction.txid, "transaction ID", exact_length=64
            )

            # 3. Transaction ID (hash) verification
            if transaction.calculate_hash() != transaction.txid:
                raise ValidationError(
                    "Transaction ID mismatch. Transaction data has been tampered with."
                )

            # 4. Signature verification
            if not transaction.verify_signature():
                raise ValidationError("Invalid transaction signature.")

            # 5. UTXO-based validation (for non-coinbase transactions)
            if transaction.tx_type != "coinbase":
                input_sum = 0.0
                output_sum = 0.0

                # Validate inputs
                if not transaction.inputs:
                    raise ValidationError("Non-coinbase transaction must have inputs.")

                for i, tx_input in enumerate(transaction.inputs):
                    if not all(k in tx_input for k in ["txid", "vout"]):
                        raise ValidationError(
                            f"Transaction input {i} is missing required fields (txid, vout)."
                        )

                    utxo = self.utxo_manager.get_unspent_output(tx_input["txid"], tx_input["vout"])
                    if not utxo:
                        raise ValidationError(
                            f"Transaction input {tx_input['txid']}:{tx_input['vout']} is not an unspent UTXO."
                        )

                    # Ensure the UTXO belongs to the sender
                    # This check assumes the sender's address is implicitly linked to the UTXO's owner
                    # A more robust check would involve verifying the script_pubkey of the UTXO
                    # For now, we'll assume the UTXO's address matches the transaction sender
                    if (
                        utxo["script_pubkey"] != f"P2PKH {transaction.sender}"
                    ):  # Assuming P2PKH format
                        raise ValidationError(
                            f"Transaction input {tx_input['txid']}:{tx_input['vout']} does not belong to sender {transaction.sender}."
                        )

                    input_sum += utxo["amount"]

                # Validate outputs
                if not transaction.outputs:
                    raise ValidationError("Transaction must have outputs.")

                for i, tx_output in enumerate(transaction.outputs):
                    if not all(k in tx_output for k in ["address", "amount"]):
                        raise ValidationError(
                            f"Transaction output {i} is missing required fields (address, amount)."
                        )
                    self.security_validator.validate_address(
                        tx_output["address"], f"output {i} address"
                    )
                    self.security_validator.validate_amount(
                        tx_output["amount"], f"output {i} amount"
                    )
                    output_sum += tx_output["amount"]

                # Verify input sum covers output sum + fee
                if input_sum < (output_sum + transaction.fee):
                    raise ValidationError(
                        f"Insufficient input funds. Input sum: {input_sum}, Output sum: {output_sum}, Fee: {transaction.fee}"
                    )

            # 6. Nonce validation (to prevent replay attacks)
            if not self.nonce_tracker.validate_nonce(transaction.sender, transaction.nonce):
                raise ValidationError(
                    f"Invalid nonce for sender {transaction.sender}. Expected: {self.nonce_tracker.get_next_nonce(transaction.sender)}, Got: {transaction.nonce}"
                )

            # 7. Transaction-specific validations (e.g., time_capsule_lock, governance_vote)
            if transaction.tx_type == "time_capsule_lock":
                self._validate_time_capsule_lock(transaction)
            elif transaction.tx_type == "governance_vote":
                self._validate_governance_vote(transaction)
            # Add other custom transaction type validations here

            self.logger.debug(
                f"Transaction {transaction.txid[:10]}... is valid.", txid=transaction.txid
            )
            return True

        except ValidationError as e:
            self.logger.warn(
                f"Transaction validation failed for {transaction.txid[:10]}...: {e}",
                txid=transaction.txid,
                error=str(e),
            )
            return False
        except Exception as e:
            self.logger.error(
                f"An unexpected error occurred during transaction validation for {transaction.txid[:10]}...: {e}",
                txid=transaction.txid,
                error=str(e),
                exc_info=True,
            )
            return False

    def _validate_time_capsule_lock(self, transaction: "Transaction"):
        """
        Validates a time_capsule_lock transaction.
        """
        if not transaction.metadata:
            raise ValidationError("Time capsule transaction missing metadata.")
        if "capsule_id" not in transaction.metadata or not transaction.metadata["capsule_id"]:
            raise ValidationError("Time capsule transaction missing capsule_id.")
        if "unlock_time" not in transaction.metadata or not isinstance(
            transaction.metadata["unlock_time"], (int, float)
        ):
            raise ValidationError("Time capsule transaction missing valid unlock_time.")
        if transaction.metadata["unlock_time"] <= transaction.timestamp:
            raise ValidationError("Time capsule unlock_time must be in the future.")
        # Further checks could involve ensuring the recipient is a valid capsule address
        # and that the amount is positive.

    def _validate_governance_vote(self, transaction: "Transaction"):
        """
        Validates a governance_vote transaction.
        """
        if not transaction.metadata:
            raise ValidationError("Governance vote transaction missing metadata.")
        if "proposal_id" not in transaction.metadata or not transaction.metadata["proposal_id"]:
            raise ValidationError("Governance vote missing proposal_id.")
        if "vote" not in transaction.metadata or transaction.metadata["vote"] not in [
            "yes",
            "no",
            "abstain",
        ]:
            raise ValidationError("Governance vote missing valid vote ('yes', 'no', 'abstain').")
        # Additional checks: ensure sender is a registered voter, proposal exists, etc.


# Global instance for convenience
_global_transaction_validator = None


def get_transaction_validator(
    blockchain,
    nonce_tracker: Optional[NonceTracker] = None,
    logger: Optional[StructuredLogger] = None,
    utxo_manager: Optional[UTXOManager] = None,
) -> TransactionValidator:
    """
    Get global transaction validator instance.
    """
    global _global_transaction_validator
    if _global_transaction_validator is None:
        _global_transaction_validator = TransactionValidator(
            blockchain, nonce_tracker, logger, utxo_manager
        )
    return _global_transaction_validator
