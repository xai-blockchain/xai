"""
XAI Blockchain - Transaction Validator

Validates incoming transactions against a set of rules to ensure network integrity.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from xai.core.blockchain import Transaction

import json
import time

from xai.core.config import Config
from xai.core.transactions.nonce_tracker import NonceTracker, get_nonce_tracker
from xai.core.security.security_validation import SecurityValidator, ValidationError
from xai.core.api.structured_logger import StructuredLogger, get_structured_logger
from xai.core.transactions.utxo_manager import UTXOManager, get_utxo_manager
from xai.core.consensus.validation import validate_address, validate_amount, validate_fee
from xai.core.wallet import Wallet

# Security constants for transaction validation
MAX_TRANSACTION_SIZE_BYTES = 100000  # 100 KB per transaction
MAX_TRANSACTION_AGE_SECONDS = 3600  # 1 hour - reject transactions older than this
MAX_TRANSACTION_FUTURE_SECONDS = 300  # 5 minutes - reject transactions too far in future
TRANSACTION_EXPIRY_SECONDS = 86400  # 24 hours - transactions expire after this time

class TransactionValidator:
    """
    Validates transactions before they are added to the transaction pool or a block.

    Security Features:
    - Replay attack protection via timestamp window validation
    - Transaction size limits to prevent DoS attacks
    - Transaction expiry mechanism
    - Nonce-based ordering enforcement
    """

    def __init__(
        self,
        blockchain,
        nonce_tracker: NonceTracker | None = None,
        logger: StructuredLogger | None = None,
        utxo_manager: UTXOManager | None = None,
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
            from xai.core.blockchain import Transaction as TransactionClass

            self._validate_structure(transaction, TransactionClass)
            is_settlement_receipt = transaction.tx_type == "trade_settlement"

            self._validate_size(transaction)
            self._validate_timestamp_and_fee(transaction, is_mempool_check)
            self._validate_data_formats(transaction)
            self._validate_transaction_id(transaction)
            self._validate_signature(transaction, is_settlement_receipt)
            self._validate_utxo(transaction, is_settlement_receipt)
            self._validate_nonce(transaction)
            self._validate_transaction_type_specific(transaction)

            self._log_valid_transaction(transaction)
            return True

        except ValidationError as e:
            self._log_validation_error(transaction, e)
            return False
        except (ValueError, KeyError, AttributeError, TypeError, Exception) as e:
            self._log_unexpected_error(transaction, e)
            return False

    def _validate_structure(self, transaction: "Transaction", transaction_class) -> None:
        """Validate basic transaction structure and required fields."""
        if not isinstance(transaction, transaction_class):
            raise ValidationError("Invalid transaction object type.")

        required_fields = [
            "sender", "recipient", "amount", "fee", "timestamp",
            "signature", "txid", "inputs", "outputs", "tx_type"
        ]
        if not all(hasattr(transaction, attr) for attr in required_fields):
            raise ValidationError("Transaction is missing required fields.")

    def _validate_size(self, transaction: "Transaction") -> None:
        """Validate transaction size for DoS protection."""
        tx_size = len(json.dumps(transaction.to_dict()).encode('utf-8'))
        if tx_size > MAX_TRANSACTION_SIZE_BYTES:
            raise ValidationError(
                f"Transaction size ({tx_size} bytes) exceeds maximum allowed ({MAX_TRANSACTION_SIZE_BYTES} bytes)"
            )

    def _validate_timestamp_and_fee(self, transaction: "Transaction", is_mempool_check: bool) -> None:
        """Validate timestamp for replay attack protection and fee rates."""
        if transaction.sender == "COINBASE":
            return

        current_time = time.time()
        tx_age = current_time - transaction.timestamp

        self._check_fee_rate(transaction, is_mempool_check)
        self._check_timestamp_age(tx_age)

    def _check_fee_rate(self, transaction: "Transaction", is_mempool_check: bool) -> None:
        """Check if fee rate meets minimum requirements."""
        if transaction.tx_type in ["governance_vote"]:
            return

        min_fee_rate = getattr(Config, "MEMPOOL_MIN_FEE_RATE", 0.0)
        fee_rate = transaction.get_fee_rate()
        if is_mempool_check and fee_rate < min_fee_rate:
            raise ValidationError(
                f"Fee rate too low for mempool admission ({fee_rate:.10f} < {min_fee_rate})"
            )

    def _check_timestamp_age(self, tx_age: float) -> None:
        """Check if timestamp is within acceptable bounds."""
        if tx_age > MAX_TRANSACTION_AGE_SECONDS:
            raise ValidationError(
                f"Transaction timestamp is too old ({tx_age:.0f}s > {MAX_TRANSACTION_AGE_SECONDS}s). "
                "Possible replay attack or clock skew."
            )

        if tx_age < -MAX_TRANSACTION_FUTURE_SECONDS:
            raise ValidationError(
                f"Transaction timestamp is too far in the future ({-tx_age:.0f}s > {MAX_TRANSACTION_FUTURE_SECONDS}s). "
                "Possible clock skew."
            )

    def _validate_data_formats(self, transaction: "Transaction") -> None:
        """Validate data types and format using SecurityValidator."""
        is_coinbase = transaction.sender == "COINBASE"

        if not is_coinbase:
            self.security_validator.validate_address(transaction.sender, "sender address")

        if transaction.recipient and not is_coinbase:
            self.security_validator.validate_address(transaction.recipient, "recipient address")

        if transaction.tx_type not in ["governance_vote"]:
            self.security_validator.validate_amount(transaction.amount, "amount")

        self.security_validator.validate_fee(transaction.fee)
        self.security_validator.validate_timestamp(transaction.timestamp)

        if transaction.signature and not is_coinbase:
            self.security_validator.validate_hex_string(
                transaction.signature, "signature", exact_length=128
            )

        if transaction.txid:
            self.security_validator.validate_hex_string(
                transaction.txid, "transaction ID", exact_length=64
            )

    def _validate_transaction_id(self, transaction: "Transaction") -> None:
        """Verify transaction ID matches calculated hash."""
        calculated_txid = transaction.calculate_hash()
        if calculated_txid != transaction.txid:
            if transaction.sender == "COINBASE":
                transaction.txid = calculated_txid
            else:
                raise ValidationError(
                    "Transaction ID mismatch. Transaction data has been tampered with."
                )

    def _validate_signature(self, transaction: "Transaction", is_settlement_receipt: bool) -> None:
        """Verify transaction signature."""
        if transaction.sender == "COINBASE" or is_settlement_receipt:
            return

        if not transaction.signature:
            raise ValidationError("Non-coinbase transaction must have a signature.")

        if not transaction.verify_signature():
            raise ValidationError("Signature verification failed")

    def _validate_utxo(self, transaction: "Transaction", is_settlement_receipt: bool) -> None:
        """Validate UTXO inputs and outputs."""
        if transaction.tx_type == "coinbase" or is_settlement_receipt:
            return

        if not transaction.inputs:
            raise ValidationError("Non-coinbase transaction must have inputs.")

        input_sum = self._validate_inputs(transaction)
        output_sum = self._validate_outputs(transaction)

        if input_sum + 1e-9 < (output_sum + transaction.fee):
            raise ValidationError(
                f"Insufficient input funds. Input sum: {input_sum}, Output sum: {output_sum}, Fee: {transaction.fee}"
            )

    def _validate_inputs(self, transaction: "Transaction") -> float:
        """Validate transaction inputs and return total input sum."""
        input_sum = 0.0

        for i, tx_input in enumerate(transaction.inputs):
            if not all(k in tx_input for k in ["txid", "vout"]):
                raise ValidationError(
                    f"Transaction input {i} is missing required fields (txid, vout)."
                )

            utxo = self._find_utxo(transaction, tx_input)
            if not utxo:
                raise ValidationError(
                    f"Transaction input {tx_input['txid']}:{tx_input['vout']} is not an unspent UTXO."
                )

            if utxo["script_pubkey"] != f"P2PKH {transaction.sender}":
                raise ValidationError(
                    f"Transaction input {tx_input['txid']}:{tx_input['vout']} does not belong to sender {transaction.sender}."
                )

            input_sum += utxo["amount"]

        return input_sum

    def _find_utxo(self, transaction: "Transaction", tx_input: dict[str, Any]) -> dict[str, Any] | None:
        """Find UTXO from confirmed or pending transactions."""
        utxo = self.utxo_manager.get_unspent_output(
            tx_input["txid"], tx_input["vout"], exclude_pending=False
        )

        if not utxo and hasattr(self.blockchain, "pending_transactions"):
            utxo = self._find_pending_utxo(transaction, tx_input)

        return utxo

    def _find_pending_utxo(self, transaction: "Transaction", tx_input: dict[str, Any]) -> dict[str, Any] | None:
        """Find UTXO in pending transactions."""
        for pending in self.blockchain.pending_transactions:
            if not pending.outputs or not pending.txid:
                continue

            if pending.txid == tx_input["txid"] and tx_input["vout"] < len(pending.outputs):
                if self._is_pending_output_consumed(transaction, tx_input):
                    continue

                output = pending.outputs[tx_input["vout"]]
                return {
                    "txid": tx_input["txid"],
                    "vout": tx_input["vout"],
                    "amount": output["amount"],
                    "script_pubkey": f"P2PKH {output.get('address', transaction.sender)}",
                }

        return None

    def _is_pending_output_consumed(self, transaction: "Transaction", tx_input: dict[str, Any]) -> bool:
        """
        Check if a pending output is already consumed by another transaction.

        P2 Performance: Uses _spent_inputs set for O(1) lookup instead of O(p*i)
        nested loop over pending transactions and their inputs.
        """
        input_key = f"{tx_input['txid']}:{tx_input['vout']}"
        # Use the blockchain's spent_inputs set if available (O(1) lookup)
        if hasattr(self.blockchain, '_spent_inputs'):
            return input_key in self.blockchain._spent_inputs
        # Fallback to O(p*i) search if _spent_inputs not available
        return any(
            inp.get("txid") == tx_input["txid"] and inp.get("vout") == tx_input["vout"]
            for t in self.blockchain.pending_transactions
            if t is not transaction and t.inputs
            for inp in t.inputs
        )

    def _validate_outputs(self, transaction: "Transaction") -> float:
        """Validate transaction outputs and return total output sum."""
        if not transaction.outputs:
            raise ValidationError("Transaction must have outputs.")

        output_sum = 0.0
        for i, tx_output in enumerate(transaction.outputs):
            if not all(k in tx_output for k in ["address", "amount"]):
                raise ValidationError(
                    f"Transaction output {i} is missing required fields (address, amount)."
                )

            self.security_validator.validate_address(
                tx_output["address"], f"output {i} address"
            )

            if transaction.tx_type not in ["governance_vote"]:
                self.security_validator.validate_amount(
                    tx_output["amount"], f"output {i} amount"
                )

            output_sum += tx_output["amount"]

        return output_sum

    def _validate_nonce(self, transaction: "Transaction") -> None:
        """Validate transaction nonce to prevent replay attacks."""
        if transaction.sender == "COINBASE":
            return

        # Guard against None nonce - validate_nonce expects int
        if transaction.nonce is None:
            raise ValidationError(
                f"Transaction nonce is required for sender {transaction.sender}"
            )

        expected_nonce = self.nonce_tracker.get_next_nonce(transaction.sender)
        if not self.nonce_tracker.validate_nonce(transaction.sender, transaction.nonce):
            if self._is_first_spend_backward_compatible(transaction, expected_nonce):
                return

            if self._has_duplicate_nonce_in_pending(transaction):
                raise ValidationError(
                    f"Invalid nonce for sender {transaction.sender}. Expected: {expected_nonce}, Got: {transaction.nonce}"
                )

            if transaction.nonce < 0 or transaction.nonce > expected_nonce:
                raise ValidationError(
                    f"Invalid nonce for sender {transaction.sender}. Expected: {expected_nonce}, Got: {transaction.nonce}"
                )

    def _is_first_spend_backward_compatible(self, transaction: "Transaction", expected_nonce: int) -> bool:
        """Check if this is a backward-compatible first spend."""
        return (
            expected_nonce == 1 and
            transaction.nonce == 0 and
            self.nonce_tracker.get_nonce(transaction.sender) <= 0
        )

    def _has_duplicate_nonce_in_pending(self, transaction: "Transaction") -> bool:
        """
        Check if nonce is duplicated in pending transactions.

        P2 Performance: Uses _pending_nonces set for O(1) lookup instead of O(p)
        loop over pending transactions.
        """
        if transaction.sender and transaction.nonce is not None:
            # Use the blockchain's pending_nonces set if available (O(1) lookup)
            if hasattr(self.blockchain, '_pending_nonces'):
                return (transaction.sender, transaction.nonce) in self.blockchain._pending_nonces
        # Fallback to O(p) search if _pending_nonces not available
        return any(
            getattr(tx, "sender", None) == transaction.sender and
            getattr(tx, "nonce", None) == transaction.nonce
            for tx in getattr(self.blockchain, "pending_transactions", [])
        )

    def _validate_transaction_type_specific(self, transaction: "Transaction") -> None:
        """Validate transaction type-specific requirements."""
        contract_types = {"contract_call", "contract_deploy"}
        if transaction.tx_type in contract_types:
            self._validate_contract_transaction(transaction)
        elif transaction.tx_type == "time_capsule_lock":
            self._validate_time_capsule_lock(transaction)
        elif transaction.tx_type == "governance_vote":
            self._validate_governance_vote(transaction)

    def _validate_contract_transaction(self, transaction: "Transaction") -> None:
        """Validate contract call or deploy transaction."""
        metadata = transaction.metadata if isinstance(transaction.metadata, dict) else {}

        payload = metadata.get("data")
        if not payload:
            raise ValidationError("Contract transactions require a payload in metadata['data'].")

        gas_limit = metadata.get("gas_limit")
        if not isinstance(gas_limit, int):
            raise ValidationError("Contract transactions require an integer 'gas_limit'.")

        max_gas = getattr(Config, "MAX_CONTRACT_GAS", 20_000_000)
        if gas_limit <= 0 or gas_limit > max_gas:
            raise ValidationError("Contract 'gas_limit' is outside allowed bounds.")

        if isinstance(payload, str) and not payload.strip():
            raise ValidationError("Contract payload data cannot be empty.")

        if isinstance(payload, (bytes, bytearray)) and len(payload) == 0:
            raise ValidationError("Contract payload data cannot be empty.")

    def _log_valid_transaction(self, transaction: "Transaction") -> None:
        """Log successful transaction validation."""
        txid_str = str(transaction.txid)
        txid_short = txid_str[:10] if len(txid_str) >= 10 else txid_str
        self.logger.debug(
            f"Transaction {txid_short}... is valid.", txid=transaction.txid
        )

    def _log_validation_error(self, transaction: "Transaction", error: ValidationError) -> None:
        """Log validation error."""
        txid = getattr(transaction, "txid", "UNKNOWN")
        txid_str = str(txid)
        txid_short = txid_str[:10] if txid and len(txid_str) >= 10 else txid_str
        self.logger.warn(
            f"Transaction validation failed for {txid_short}...: {error}",
            txid=txid,
            error=str(error),
        )

    def _log_unexpected_error(self, transaction: "Transaction", error: Exception) -> None:
        """Log unexpected error during validation."""
        txid = getattr(transaction, "txid", "UNKNOWN")
        txid_str = str(txid)
        txid_short = txid_str[:10] if txid and len(txid_str) >= 10 else txid_str
        self.logger.error(
            f"An unexpected error occurred during transaction validation for {txid_short}...: {error}",
            exc_info=True,
            extra={
                "txid": txid,
                "error": str(error),
                "error_type": type(error).__name__
            }
        )

    def _validate_time_capsule_lock(self, transaction: "Transaction") -> None:
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

    def _validate_governance_vote(self, transaction: "Transaction") -> None:
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

# Global instance for convenience
_global_transaction_validator = None

def get_transaction_validator(
    blockchain,
    nonce_tracker: NonceTracker | None = None,
    logger: StructuredLogger | None = None,
    utxo_manager: UTXOManager | None = None,
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
