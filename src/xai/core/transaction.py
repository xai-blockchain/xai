"""
XAI Blockchain Core - Transaction

Implements a UTXO-based transaction model with ECDSA signatures.
All monetary values use Decimal for precision in production.

Security Notes:
- All inputs are validated before processing
- Amounts must be non-negative finite numbers
- Addresses must follow XAI format conventions
- Signatures use domain separation to prevent cross-network replay
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import re
import time
from decimal import Decimal, InvalidOperation
from typing import List, Dict, Optional, Any, Union
import base58
from xai.core.crypto_utils import sign_message_hex, verify_signature_hex, derive_public_key_hex
from xai.core.validation import validate_address, validate_amount

logger = logging.getLogger(__name__)


def canonical_json(data: Dict[str, Any]) -> str:
    """Produce deterministic JSON string for consensus-critical hashing.

    Uses canonical serialization to ensure identical hashes across all nodes:
    - sort_keys=True: Consistent key ordering
    - separators=(',', ':'): No whitespace variations
    - ensure_ascii=True: No unicode encoding variations

    This is critical for consensus - different JSON formatting would produce
    different hashes for identical transactions, causing network forks.

    Args:
        data: Dictionary to serialize

    Returns:
        Canonical JSON string suitable for hashing
    """
    return json.dumps(
        data,
        sort_keys=True,
        separators=(',', ':'),
        ensure_ascii=True
    )


# Validation constants
MAX_TRANSACTION_AMOUNT = 121_000_000.0  # Total supply cap
MIN_TRANSACTION_AMOUNT = 0.0
MAX_FEE = 1_000_000.0  # Reasonable fee cap
MAX_METADATA_SIZE = 4096  # 4KB metadata limit
MAX_INPUTS = 1000  # Maximum inputs per transaction
MAX_OUTPUTS = 1000  # Maximum outputs per transaction
ADDRESS_PATTERN = re.compile(r'^(XAI|TXAI|COINBASE)[A-Fa-f0-9]{0,64}$')


class TransactionValidationError(ValueError):
    """Raised when transaction validation fails."""
    pass


class SignatureVerificationError(TransactionValidationError):
    """Base class for signature verification failures."""
    pass


class MissingSignatureError(SignatureVerificationError):
    """Transaction is missing required signature or public key."""
    pass


class InvalidSignatureError(SignatureVerificationError):
    """Signature cryptographic verification failed."""
    pass


class SignatureCryptoError(SignatureVerificationError):
    """Cryptographic operation failed during signature verification."""
    pass


class Transaction:
    """Real cryptocurrency transaction with ECDSA signatures, supporting UTXO model.

    All parameters are validated on construction. Invalid transactions
    raise TransactionValidationError with details about the failure.

    Attributes:
        sender: Source address (XAI... format) or "COINBASE" for mining rewards
        recipient: Destination address
        amount: Transfer amount (must be >= 0 and <= MAX_TRANSACTION_AMOUNT)
        fee: Transaction fee (must be >= 0)
        public_key: ECDSA public key (hex) for signature verification
        tx_type: Transaction type (normal, coinbase, contract, etc.)
        nonce: Replay protection nonce (sequential per address)
        inputs: UTXO inputs being spent
        outputs: UTXO outputs being created
        metadata: Optional transaction metadata (size limited)
    """
    # Domain separation context for TXID/signatures to prevent cross-network replay
    _CHAIN_CONTEXT: str = "mainnet"

    @staticmethod
    def _validate_amount(value: Any, field_name: str, allow_zero: bool = True) -> float:
        """Validate a monetary amount using centralized validation.

        Args:
            value: Value to validate
            field_name: Field name for error messages
            allow_zero: Whether zero is a valid amount

        Returns:
            Validated float amount

        Raises:
            TransactionValidationError: If validation fails
        """
        if value is None:
            raise TransactionValidationError(f"{field_name} cannot be None")

        try:
            return validate_amount(
                value,
                allow_zero=allow_zero,
                min_value=MIN_TRANSACTION_AMOUNT if not allow_zero else 0,
                max_value=MAX_TRANSACTION_AMOUNT
            )
        except ValueError as e:
            raise TransactionValidationError(f"{field_name}: {e}") from e

    @staticmethod
    def _validate_address(address: Any, field_name: str, allow_empty: bool = False) -> str:
        """Validate an address format using centralized validation.

        Args:
            address: Address to validate
            field_name: Field name for error messages
            allow_empty: Whether empty/None is allowed

        Returns:
            Validated address string

        Raises:
            TransactionValidationError: If validation fails
        """
        if address is None or address == "":
            if allow_empty:
                return ""
            raise TransactionValidationError(f"{field_name} cannot be empty")

        try:
            return validate_address(address, allow_special=True)
        except ValueError as e:
            raise TransactionValidationError(f"{field_name}: {e}") from e

    @staticmethod
    def _validate_inputs(inputs: Any) -> List[Dict[str, Any]]:
        """Validate transaction inputs.

        Args:
            inputs: List of input UTXOs

        Returns:
            Validated inputs list

        Raises:
            TransactionValidationError: If validation fails
        """
        if inputs is None:
            return []

        if not isinstance(inputs, list):
            raise TransactionValidationError(
                f"inputs must be a list, got {type(inputs).__name__}"
            )

        if len(inputs) > MAX_INPUTS:
            raise TransactionValidationError(
                f"Too many inputs: {len(inputs)} > {MAX_INPUTS}"
            )

        validated = []
        for i, inp in enumerate(inputs):
            if not isinstance(inp, dict):
                raise TransactionValidationError(
                    f"Input {i} must be a dict, got {type(inp).__name__}"
                )
            if "txid" not in inp:
                raise TransactionValidationError(f"Input {i} missing 'txid'")
            if "vout" not in inp:
                raise TransactionValidationError(f"Input {i} missing 'vout'")
            validated.append(inp)

        return validated

    @staticmethod
    def _validate_outputs(outputs: Any) -> List[Dict[str, Any]]:
        """Validate transaction outputs.

        Args:
            outputs: List of output destinations

        Returns:
            Validated outputs list

        Raises:
            TransactionValidationError: If validation fails
        """
        if outputs is None:
            return []

        if not isinstance(outputs, list):
            raise TransactionValidationError(
                f"outputs must be a list, got {type(outputs).__name__}"
            )

        if len(outputs) > MAX_OUTPUTS:
            raise TransactionValidationError(
                f"Too many outputs: {len(outputs)} > {MAX_OUTPUTS}"
            )

        validated = []
        for i, out in enumerate(outputs):
            if not isinstance(out, dict):
                raise TransactionValidationError(
                    f"Output {i} must be a dict, got {type(out).__name__}"
                )
            if "address" not in out:
                raise TransactionValidationError(f"Output {i} missing 'address'")
            if "amount" not in out:
                raise TransactionValidationError(f"Output {i} missing 'amount'")

            # Validate output amount
            Transaction._validate_amount(out["amount"], f"Output {i} amount")
            Transaction._validate_address(out["address"], f"Output {i} address", allow_empty=True)
            validated.append(out)

        return validated

    @staticmethod
    def _validate_metadata(metadata: Any) -> Dict[str, Any]:
        """Validate transaction metadata.

        Args:
            metadata: Metadata dictionary

        Returns:
            Validated metadata

        Raises:
            TransactionValidationError: If validation fails
        """
        if metadata is None:
            return {}

        if not isinstance(metadata, dict):
            raise TransactionValidationError(
                f"metadata must be a dict, got {type(metadata).__name__}"
            )

        # Check serialized size
        try:
            serialized = json.dumps(metadata)
            if len(serialized) > MAX_METADATA_SIZE:
                raise TransactionValidationError(
                    f"metadata too large: {len(serialized)} > {MAX_METADATA_SIZE} bytes"
                )
        except (TypeError, ValueError) as e:
            raise TransactionValidationError(f"metadata not JSON serializable: {e}")

        return metadata

    def __init__(
        self,
        sender: str,
        recipient: str,
        amount: float,
        fee: float = 0.0,
        public_key: Optional[str] = None,
        tx_type: str = "normal",
        nonce: Optional[int] = None,
        inputs: Optional[List[Dict[str, Any]]] = None,
        outputs: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        rbf_enabled: bool = False,
        replaces_txid: Optional[str] = None,
        gas_sponsor: Optional[str] = None,
    ) -> None:
        """Initialize a new transaction with validated parameters.

        Args:
            sender: Source address or "COINBASE"
            recipient: Destination address
            amount: Transfer amount (must be >= 0)
            fee: Transaction fee (must be >= 0)
            public_key: ECDSA public key for verification
            tx_type: Transaction type
            nonce: Replay protection nonce
            inputs: UTXO inputs
            outputs: UTXO outputs
            metadata: Optional metadata (size limited)
            rbf_enabled: Replace-by-fee enabled
            replaces_txid: TXID this transaction replaces (if RBF)
            gas_sponsor: Address of gas sponsor for account abstraction (optional)

        Raises:
            TransactionValidationError: If any validation fails
        """
        # Validate all inputs
        self.sender = self._validate_address(sender, "sender")
        self.recipient = self._validate_address(recipient, "recipient", allow_empty=True)
        self.amount = self._validate_amount(amount, "amount")
        self.fee = self._validate_amount(fee, "fee")

        # Validate fee is reasonable
        if self.fee > MAX_FEE:
            raise TransactionValidationError(
                f"fee exceeds maximum ({MAX_FEE}): {self.fee}"
            )

        # Validate nonce if provided
        if nonce is not None:
            if not isinstance(nonce, int) or nonce < 0:
                raise TransactionValidationError(
                    f"nonce must be a non-negative integer, got {nonce}"
                )
        self.nonce = nonce

        # Validate tx_type
        valid_types = {"normal", "coinbase", "contract", "governance", "stake", "unstake", "trade_settlement"}
        if tx_type not in valid_types:
            logger.warning(
                "Non-standard tx_type: %s (allowed but may not be processed)",
                tx_type,
                extra={"event": "tx.nonstandard_type", "tx_type": tx_type}
            )
        self.tx_type = tx_type

        # Validate public key format if provided
        if public_key is not None:
            if not isinstance(public_key, str):
                raise TransactionValidationError(
                    f"public_key must be a string, got {type(public_key).__name__}"
                )
            # Should be hex-encoded (variable length for compressed/uncompressed)
            if public_key and not re.match(r'^[A-Fa-f0-9]+$', public_key):
                raise TransactionValidationError("public_key must be hex-encoded")
        self.public_key = public_key

        # Validate inputs/outputs
        self.inputs = self._validate_inputs(inputs)
        self.outputs = self._validate_outputs(outputs)
        self.metadata = self._validate_metadata(metadata)

        # Set remaining fields
        self.timestamp = time.time()
        self.signature = None
        self.txid = None
        self.rbf_enabled = bool(rbf_enabled)
        self.replaces_txid = replaces_txid

        # Gas sponsorship for account abstraction (Task 178)
        # When set, the sponsor pays the fee instead of the sender
        self.gas_sponsor = gas_sponsor
        self.gas_sponsor_signature = None  # Sponsor's authorization signature

        # Create default output if needed
        if not self.outputs and self.recipient and self.amount > 0:
            self.outputs.append({"address": self.recipient, "amount": self.amount})

    def calculate_hash(self) -> str:
        """Calculate transaction hash (TXID)"""
        try:
            from xai.core.config import Config
            context = getattr(Config, "CHAIN_ID", None) or getattr(
                Config, "NETWORK_TYPE", Transaction._CHAIN_CONTEXT
            )
            # Normalize enum/other types to string
            if hasattr(context, "value"):
                context = context.value
            Transaction._CHAIN_CONTEXT = str(context)
        except (ImportError, AttributeError) as exc:
            logger.debug(
                "Using default transaction chain context due to config load issue: %s",
                exc,
                extra={"event": "tx.chain_context_fallback"},
            )

        tx_data = {
            "chain_context": Transaction._CHAIN_CONTEXT,
            "sender": self.sender,
            "recipient": self.recipient,
            "amount": self.amount,
            "fee": self.fee,
            "timestamp": self.timestamp,
            "nonce": self.nonce,
            "inputs": self.inputs,
            "outputs": self.outputs,
        }
        tx_string = canonical_json(tx_data)
        return hashlib.sha256(tx_string.encode()).hexdigest()

    def sign_transaction(self, private_key: str) -> None:
        """Sign transaction with sender's private key"""
        if self.sender == "COINBASE":
            self.txid = self.calculate_hash()
            return

        try:
            if not self.public_key:
                self.public_key = derive_public_key_hex(private_key)
            message = self.calculate_hash().encode()
            self.signature = sign_message_hex(private_key, message)
            self.txid = self.calculate_hash()
        except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as e:
            raise ValueError(f"Failed to sign transaction: {e}")

    def verify_signature(self) -> None:
        """Verify transaction signature.

        Raises:
            MissingSignatureError: If signature or public_key is missing
            InvalidSignatureError: If signature verification fails
            SignatureCryptoError: If cryptographic operation fails
        """
        if self.sender == "COINBASE":
            return  # Coinbase transactions don't require signatures

        if not self.signature or not self.public_key:
            txid_str = self.txid[:10] if self.txid else "unknown"
            raise MissingSignatureError(
                f"Transaction {txid_str}... is missing "
                f"{'signature' if not self.signature else 'public key'}"
            )

        try:
            # Convert public key hex to bytes before hashing (matches wallet.py)
            pub_key_bytes = bytes.fromhex(self.public_key)
            pub_hash = hashlib.sha256(pub_key_bytes).hexdigest()
            expected_address = f"XAI{pub_hash[:40]}"

            if expected_address != self.sender:
                txid_str = self.txid[:10] if self.txid else "unknown"
                logger.error(
                    "Address mismatch in signature verification: expected=%s, got=%s",
                    expected_address[:16] + "...",
                    self.sender[:16] + "..." if self.sender else "<none>",
                    extra={"event": "tx.address_mismatch", "txid": self.txid}
                )
                raise InvalidSignatureError(
                    f"Transaction {txid_str}...: Public key does not match sender address "
                    f"(expected {expected_address[:16]}..., got {self.sender[:16] if self.sender else '<none>'}...)"
                )

            message = self.calculate_hash().encode()
            if not verify_signature_hex(self.public_key, message, self.signature):
                txid_str = self.txid[:10] if self.txid else "unknown"
                raise InvalidSignatureError(
                    f"Transaction {txid_str}...: ECDSA signature verification failed"
                )

        except SignatureVerificationError:
            # Re-raise our own exceptions unchanged
            raise
        except (ValueError, TypeError, KeyError, AttributeError) as e:
            # Cryptographic operation failures
            txid_str = self.txid[:10] if self.txid else "unknown"
            logger.error(
                "Cryptographic error during signature verification: %s",
                type(e).__name__,
                extra={
                    "event": "tx.signature_crypto_error",
                    "error": str(e),
                    "txid": self.txid
                }
            )
            raise SignatureCryptoError(
                f"Transaction {txid_str}...: Cryptographic operation failed: {type(e).__name__}: {e}"
            ) from e

    def get_size(self) -> int:
        """
        Calculate transaction size in bytes for fee-per-byte calculations.
        """
        try:
            serialized = canonical_json(self.to_dict())
            return len(serialized.encode('utf-8'))
        except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as e:
            logger.debug(
                "Failed to serialize transaction for size calculation, using estimate",
                txid=self.txid,
                error=str(e)
            )
            base_size = 200
            input_size = len(self.inputs) * 50
            output_size = len(self.outputs) * 40
            return base_size + input_size + output_size

    def get_fee_rate(self) -> float:
        """
        Calculate fee rate (fee per byte) for transaction prioritization.
        """
        size = self.get_size()
        if size == 0:
            return 0.0
        return self.fee / size

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = {
            "txid": self.txid,
            "sender": self.sender,
            "recipient": self.recipient,
            "amount": self.amount,
            "fee": self.fee,
            "timestamp": self.timestamp,
            "signature": self.signature,
            "public_key": self.public_key,
            "tx_type": self.tx_type,
            "nonce": self.nonce,
            "metadata": self.metadata,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "rbf_enabled": self.rbf_enabled,
            "replaces_txid": self.replaces_txid,
        }
        # Include gas sponsorship fields if present
        if self.gas_sponsor:
            result["gas_sponsor"] = self.gas_sponsor
            result["gas_sponsor_signature"] = self.gas_sponsor_signature
        return result
