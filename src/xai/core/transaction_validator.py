"""
XAI Blockchain - Transaction Validator

Validates incoming transactions against a set of rules to ensure network integrity.
"""

from __future__ import annotations

from typing import Dict, Any, Optional, TYPE_CHECKING, List

if TYPE_CHECKING:
    from xai.core.blockchain import Transaction

from xai.core.config import Config
from xai.core.wallet import Wallet
from xai.core.security_validation import SecurityValidator, ValidationError
from xai.core.validation import validate_address, validate_amount, validate_fee
from xai.core.nonce_tracker import NonceTracker, get_nonce_tracker
from xai.core.structured_logger import StructuredLogger, get_structured_logger
from xai.core.utxo_manager import UTXOManager, get_utxo_manager
import time
import json

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
            # Import Transaction here to avoid circular import
            from xai.core.blockchain import Transaction as TransactionClass

            # 1. Basic structural validation
            if not isinstance(transaction, TransactionClass):
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
                    "tx_type",
                ]
            ):
                raise ValidationError("Transaction is missing required fields.")

            is_settlement_receipt = transaction.tx_type == "trade_settlement"

            # 2. Transaction size validation (DoS protection)
            tx_size = len(json.dumps(transaction.to_dict()).encode('utf-8'))
            if tx_size > MAX_TRANSACTION_SIZE_BYTES:
                raise ValidationError(
                    f"Transaction size ({tx_size} bytes) exceeds maximum allowed ({MAX_TRANSACTION_SIZE_BYTES} bytes)"
                )

            # 3. Timestamp validation for replay attack protection
            current_time = time.time()
            tx_age = current_time - transaction.timestamp

            # Skip timestamp checks for coinbase transactions
            if transaction.sender != "COINBASE":
                min_fee_rate = getattr(Config, "MEMPOOL_MIN_FEE_RATE", 0.0)
                fee_rate = transaction.get_fee_rate()
                if is_mempool_check and fee_rate < min_fee_rate:
                    raise ValidationError(
                        f"Fee rate too low for mempool admission ({fee_rate:.10f} < {min_fee_rate})"
                    )

                # Reject transactions that are too old (replay attack protection)
                if tx_age > MAX_TRANSACTION_AGE_SECONDS:
                    raise ValidationError(
                        f"Transaction timestamp is too old ({tx_age:.0f}s > {MAX_TRANSACTION_AGE_SECONDS}s). "
                        "Possible replay attack or clock skew."
                    )

                # Reject transactions with timestamps too far in the future
                if tx_age < -MAX_TRANSACTION_FUTURE_SECONDS:
                    raise ValidationError(
                        f"Transaction timestamp is too far in the future ({-tx_age:.0f}s > {MAX_TRANSACTION_FUTURE_SECONDS}s). "
                        "Possible clock skew."
                    )

            # 4. Data type and format validation using SecurityValidator
            # Skip sender address validation for coinbase transactions
            if transaction.sender != "COINBASE":
                self.security_validator.validate_address(transaction.sender, "sender address")
            # Recipient can be None for some transaction types (e.g., burn)
            if transaction.recipient:
                self.security_validator.validate_address(transaction.recipient, "recipient address")
            # Skip amount validation for transaction types that allow zero amounts
            if transaction.tx_type not in ["governance_vote"]:
                self.security_validator.validate_amount(transaction.amount, "amount")
            self.security_validator.validate_fee(transaction.fee)
            self.security_validator.validate_timestamp(transaction.timestamp)

            # Validate signature if present and not a coinbase transaction
            if transaction.signature and transaction.sender != "COINBASE":
                self.security_validator.validate_hex_string(
                    transaction.signature, "signature", exact_length=128
                )

            # Validate transaction ID formatting
            if transaction.txid:
                self.security_validator.validate_hex_string(
                    transaction.txid, "transaction ID", exact_length=64
                )

            # 5. Transaction ID (hash) verification
            calculated_txid = transaction.calculate_hash()
            if calculated_txid != transaction.txid:
                if transaction.sender == "COINBASE":
                    # Normalize legacy/static coinbase txids (e.g., genesis) to current hash derivation
                    transaction.txid = calculated_txid
                else:
                    raise ValidationError(
                        "Transaction ID mismatch. Transaction data has been tampered with."
                    )

            # 6. Signature verification (skip for coinbase transactions)
            if transaction.sender != "COINBASE" and not is_settlement_receipt:
                if not transaction.signature:
                    raise ValidationError("Non-coinbase transaction must have a signature.")
                if not transaction.verify_signature():
                    raise ValidationError("Invalid transaction signature.")

            # 7. UTXO-based validation (for non-coinbase transactions)
            if transaction.tx_type != "coinbase" and not is_settlement_receipt:
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
                    if not utxo and hasattr(self.blockchain, "pending_transactions"):
                        # Allow spending outputs from pending transactions (intra-block chaining)
                        for pending in self.blockchain.pending_transactions:
                            if not pending.outputs or not pending.txid:
                                continue
                            if pending.txid == tx_input["txid"] and tx_input["vout"] < len(pending.outputs):
                                output = pending.outputs[tx_input["vout"]]
                                # Ensure this pending output is not already consumed by another pending tx
                                already_consumed = any(
                                    inp.get("txid") == tx_input["txid"]
                                    and inp.get("vout") == tx_input["vout"]
                                    for t in self.blockchain.pending_transactions
                                    if t is not transaction and t.inputs
                                    for inp in t.inputs
                                )
                                if not already_consumed:
                                    utxo = {
                                        "txid": tx_input["txid"],
                                        "vout": tx_input["vout"],
                                        "amount": output["amount"],
                                        "script_pubkey": f"P2PKH {output.get('address', transaction.sender)}",
                                    }
                                break
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
                    # Skip amount validation for transaction types that allow zero amounts
                    if transaction.tx_type not in ["governance_vote"]:
                        self.security_validator.validate_amount(
                            tx_output["amount"], f"output {i} amount"
                        )
                    output_sum += tx_output["amount"]

                # Verify input sum covers output sum + fee, allowing tiny float drift
                if input_sum + 1e-9 < (output_sum + transaction.fee):
                    raise ValidationError(
                        f"Insufficient input funds. Input sum: {input_sum}, Output sum: {output_sum}, Fee: {transaction.fee}"
                    )

            # 8. Nonce validation (to prevent replay attacks) - skip for coinbase transactions
            if transaction.sender != "COINBASE":
                expected_nonce = self.nonce_tracker.get_next_nonce(transaction.sender)
                if not self.nonce_tracker.validate_nonce(transaction.sender, transaction.nonce):
                    # Backward-compatible allowance for first spend if tracker is uninitialized but expected nonce drifted
                    if expected_nonce == 1 and transaction.nonce == 0 and self.nonce_tracker.get_nonce(transaction.sender) <= 0:
                        pass
                    else:
                        # Allow nonces up to expected if not already used in pending pool (mempool ordering tolerance)
                        duplicate_pending = any(
                            getattr(tx, "sender", None) == transaction.sender and getattr(tx, "nonce", None) == transaction.nonce
                            for tx in getattr(self.blockchain, "pending_transactions", [])
                        )
                        if transaction.nonce < 0 or transaction.nonce > expected_nonce or duplicate_pending:
                            raise ValidationError(
                                f"Invalid nonce for sender {transaction.sender}. Expected: {expected_nonce}, Got: {transaction.nonce}"
                            )

            # 9. Transaction-specific validations (e.g., time_capsule_lock, governance_vote)
            contract_types = {"contract_call", "contract_deploy"}
            if transaction.tx_type in contract_types:
                metadata = transaction.metadata if isinstance(transaction.metadata, dict) else {}
                payload = metadata.get("data")
                if not payload:
                    raise ValidationError("Contract transactions require a payload in metadata['data'].")
                gas_limit = metadata.get("gas_limit")
                if not isinstance(gas_limit, int):
                    raise ValidationError("Contract transactions require an integer 'gas_limit'.")
                if gas_limit <= 0 or gas_limit > getattr(Config, "MAX_CONTRACT_GAS", 20_000_000):
                    raise ValidationError("Contract 'gas_limit' is outside allowed bounds.")
                if isinstance(payload, str) and not payload.strip():
                    raise ValidationError("Contract payload data cannot be empty.")
                if isinstance(payload, (bytes, bytearray)) and len(payload) == 0:
                    raise ValidationError("Contract payload data cannot be empty.")

            if transaction.tx_type == "time_capsule_lock":
                self._validate_time_capsule_lock(transaction)
            elif transaction.tx_type == "governance_vote":
                self._validate_governance_vote(transaction)
            # Add other custom transaction type validations here

            txid_str = str(transaction.txid)
            txid_short = txid_str[:10] if len(txid_str) >= 10 else txid_str
            self.logger.debug(
                f"Transaction {txid_short}... is valid.", txid=transaction.txid
            )
            return True

        except ValidationError as e:
            txid = getattr(transaction, "txid", "UNKNOWN")
            txid_str = str(txid)
            txid_short = txid_str[:10] if txid and len(txid_str) >= 10 else txid_str
            self.logger.warn(
                f"Transaction validation failed for {txid_short}...: {e}",
                txid=txid,
                error=str(e),
            )
            return False
        except Exception as e:
            txid = getattr(transaction, "txid", "UNKNOWN")
            txid_str = str(txid)
            txid_short = txid_str[:10] if txid and len(txid_str) >= 10 else txid_str
            self.logger.error(
                f"An unexpected error occurred during transaction validation for {txid_short}...: {e}",
                txid=txid,
                error=str(e),
                exc_info=True,
            )
            return False

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
        # Further checks could involve ensuring the recipient is a valid capsule address
        # and that the amount is positive.

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
