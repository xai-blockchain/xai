import json
import logging
import time
from typing import Any, Dict, List, Optional, Set, Tuple

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import load_pem_public_key, load_pem_private_key

logger = logging.getLogger(__name__)


class MultiSigWallet:
    """
    M-of-N Multisignature Wallet with threshold validation (TASK 26)
    Supports partial signature collection and aggregation (TASK 210)
    """

    def __init__(self, public_keys: List[str], threshold: int, max_signers: int = 15):
        """
        Initialize multisig wallet.

        Args:
            public_keys: List of PEM-encoded public keys (hex strings)
            threshold: Number of signatures required (M in M-of-N)
            max_signers: Maximum number of signers allowed (default: 15)

        Raises:
            ValueError: If threshold > signers or threshold < 1
        """
        # TASK 26: Enhanced validation
        if not public_keys or len(public_keys) == 0:
            raise ValueError("At least one public key is required")

        if threshold < 1:
            raise ValueError("Threshold must be at least 1")

        if threshold > len(public_keys):
            raise ValueError(f"Threshold ({threshold}) cannot be greater than number of public keys ({len(public_keys)})")

        if len(public_keys) > max_signers:
            raise ValueError(f"Number of signers ({len(public_keys)}) exceeds maximum ({max_signers})")

        # Check for duplicate public keys
        if len(public_keys) != len(set(public_keys)):
            raise ValueError("Duplicate public keys are not allowed")

        self.public_keys = [load_pem_public_key(bytes.fromhex(pk)) for pk in public_keys]
        self.public_keys_hex = public_keys  # Keep hex versions for lookup
        self.threshold = threshold
        self.max_signers = max_signers

        # TASK 210: Storage for partial signatures
        self.pending_transactions: Dict[str, Dict[str, Any]] = {}

        # Nonce/sequence tracking to prevent replay attacks
        self._next_nonce: int = 0
        self._sequence_counter: int = 0
        self._consumed_nonces: Set[int] = set()

    def _allocate_nonce_and_sequence(
        self,
        provided_nonce: Optional[int],
        provided_sequence: Optional[int],
    ) -> Tuple[int, int]:
        """
        Allocate a nonce/sequence pair for a new transaction.

        Raises:
            ValueError: If provided values are invalid or already used
        """
        if provided_nonce is not None:
            if provided_nonce < 0:
                raise ValueError("Nonce must be non-negative")
            nonce = provided_nonce
            if nonce in self._consumed_nonces or any(
                tx["nonce"] == nonce for tx in self.pending_transactions.values()
            ):
                raise ValueError(f"Nonce {nonce} already used or pending")
            if nonce >= self._next_nonce:
                self._next_nonce = nonce + 1
        else:
            nonce = self._next_nonce
            self._next_nonce += 1

        if provided_sequence is not None:
            if provided_sequence <= self._sequence_counter:
                raise ValueError("Sequence must be strictly increasing")
            sequence = provided_sequence
            self._sequence_counter = sequence
        else:
            self._sequence_counter += 1
            sequence = self._sequence_counter

        return nonce, sequence

    @staticmethod
    def _serialize_for_signing(tx: Dict[str, Any]) -> bytes:
        """
        Build canonical payload for signature binding.

        Includes nonce/sequence fields so previously signed payloads cannot
        be replayed after the transaction is finalized.
        """
        envelope = {
            "tx_id": tx["tx_id"],
            "nonce": tx["nonce"],
            "sequence": tx["sequence"],
            "tx_data": tx["tx_data"],
        }
        return json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode()

    def verify_signatures(self, message: bytes, signatures: Dict[str, str]) -> bool:
        """
        Verify M-of-N signatures meet threshold (TASK 26).

        Args:
            message: Message that was signed
            signatures: Dict of {public_key_hex: signature_hex}

        Returns:
            True if threshold met with valid signatures
        """
        # TASK 26: Enhanced threshold validation
        if len(signatures) < self.threshold:
            logger.debug(
                "Insufficient signatures for multisig threshold",
                extra={
                    "event": "multisig.insufficient_signatures",
                    "signatures_provided": len(signatures),
                    "threshold_required": self.threshold
                }
            )
            return False

        message_hash = hashes.Hash(hashes.SHA256())
        message_hash.update(message)
        digest = message_hash.finalize()

        valid_signatures = 0
        invalid_signatures = []

        for pub_key_hex, signature_hex in signatures.items():
            # Verify public key is authorized
            if pub_key_hex not in self.public_keys_hex:
                logger.warning(
                    "Unauthorized public key in multisig verification",
                    extra={
                        "event": "multisig.unauthorized_key",
                        "key_prefix": pub_key_hex[:16]
                    }
                )
                continue

            try:
                public_key = load_pem_public_key(bytes.fromhex(pub_key_hex))
                signature = bytes.fromhex(signature_hex)
                public_key.verify(signature, digest, ec.ECDSA(hashes.SHA256()))
                valid_signatures += 1
                logger.debug(
                    "Valid multisig signature verified",
                    extra={
                        "event": "multisig.valid_signature",
                        "key_prefix": pub_key_hex[:16]
                    }
                )
            except Exception as e:
                invalid_signatures.append(pub_key_hex[:16])
                logger.debug(
                    "Invalid multisig signature",
                    extra={
                        "event": "multisig.invalid_signature",
                        "key_prefix": pub_key_hex[:16],
                        "error_type": type(e).__name__
                    }
                )
                continue

        # TASK 26: Detailed threshold validation
        if valid_signatures < self.threshold:
            logger.info(
                "Multisig threshold not met",
                extra={
                    "event": "multisig.threshold_not_met",
                    "valid_signatures": valid_signatures,
                    "threshold_required": self.threshold,
                    "invalid_count": len(invalid_signatures)
                }
            )
            return False

        logger.info(
            "Multisig threshold met - transaction authorized",
            extra={
                "event": "multisig.threshold_met",
                "valid_signatures": valid_signatures,
                "threshold_required": self.threshold
            }
        )
        return True

    # ===== PARTIAL SIGNATURE SUPPORT (TASK 210) =====

    def create_transaction(
        self,
        tx_id: str,
        tx_data: Dict,
        nonce: Optional[int] = None,
        sequence: Optional[int] = None,
    ) -> Dict:
        """
        Create a new pending transaction for signature collection.

        Args:
            tx_id: Unique transaction identifier
            tx_data: Transaction data to be signed
            nonce: Optional explicit nonce (must be unique if provided)
            sequence: Optional explicit sequence number (must increase monotonically)

        Returns:
            Transaction info
        """
        if tx_id in self.pending_transactions:
            raise ValueError(f"Transaction {tx_id} already exists")

        assigned_nonce, assigned_sequence = self._allocate_nonce_and_sequence(nonce, sequence)

        self.pending_transactions[tx_id] = {
            "tx_id": tx_id,
            "tx_data": tx_data,
            "signatures": {},
            "created_at": time.time(),
            "status": "pending",
            "threshold": self.threshold,
            "signers_required": self.threshold,
            "signers_collected": 0,
            "nonce": assigned_nonce,
            "sequence": assigned_sequence,
        }

        return self.pending_transactions[tx_id]

    def add_partial_signature(self, tx_id: str, public_key_hex: str, signature_hex: str) -> Dict:
        """
        Add a partial signature to a pending transaction (TASK 210).

        Args:
            tx_id: Transaction ID
            public_key_hex: Signer's public key (hex)
            signature_hex: Signature (hex)

        Returns:
            Updated transaction status

        Raises:
            ValueError: If transaction not found or signature invalid
        """
        if tx_id not in self.pending_transactions:
            raise ValueError(f"Transaction {tx_id} not found")

        tx = self.pending_transactions[tx_id]

        if tx["status"] != "pending":
            raise ValueError(f"Transaction {tx_id} is {tx['status']}, cannot add signatures")

        # Verify public key is authorized
        if public_key_hex not in self.public_keys_hex:
            raise ValueError(f"Public key not authorized for this multisig wallet")

        # Check if already signed
        if public_key_hex in tx["signatures"]:
            raise ValueError(f"Public key {public_key_hex[:16]}... has already signed")

        # Validate signature against canonical payload (includes nonce/sequence)
        message = self._serialize_for_signing(tx)
        message_hash = hashes.Hash(hashes.SHA256())
        message_hash.update(message)
        digest = message_hash.finalize()

        try:
            public_key = load_pem_public_key(bytes.fromhex(public_key_hex))
            signature = bytes.fromhex(signature_hex)
            public_key.verify(signature, digest, ec.ECDSA(hashes.SHA256()))
        except Exception as e:
            raise ValueError(f"Invalid signature: {e}")

        # Add signature
        tx["signatures"][public_key_hex] = signature_hex
        tx["signers_collected"] = len(tx["signatures"])

        # Check if threshold met
        if tx["signers_collected"] >= tx["threshold"]:
            tx["status"] = "ready"
            tx["completed_at"] = time.time()
            logger.info(
                "Multisig transaction ready for finalization",
                extra={
                    "event": "multisig.tx_ready",
                    "tx_id": tx_id,
                    "signatures_collected": tx["signers_collected"],
                    "threshold": tx["threshold"]
                }
            )

        return {
            "tx_id": tx_id,
            "status": tx["status"],
            "signatures_collected": tx["signers_collected"],
            "signatures_required": tx["threshold"],
            "is_ready": tx["status"] == "ready",
        }

    def get_transaction_status(self, tx_id: str) -> Optional[Dict]:
        """
        Get status of a pending transaction.

        Args:
            tx_id: Transaction ID

        Returns:
            Transaction status or None if not found
        """
        tx = self.pending_transactions.get(tx_id)
        if not tx:
            return None

        return {
            "tx_id": tx["tx_id"],
            "status": tx["status"],
            "signatures_collected": tx["signers_collected"],
            "signatures_required": tx["threshold"],
            "is_ready": tx["status"] == "ready",
            "signers": list(tx["signatures"].keys()),
        }

    def finalize_transaction(self, tx_id: str) -> Dict:
        """
        Finalize and broadcast a transaction once threshold is met (TASK 210).

        Args:
            tx_id: Transaction ID

        Returns:
            Finalized transaction with all signatures

        Raises:
            ValueError: If transaction not ready
        """
        if tx_id not in self.pending_transactions:
            raise ValueError(f"Transaction {tx_id} not found")

        tx = self.pending_transactions[tx_id]

        if tx["status"] != "ready":
            raise ValueError(f"Transaction not ready: {tx['signers_collected']}/{tx['threshold']} signatures")

        # Mark as finalized
        tx["status"] = "finalized"
        tx["finalized_at"] = time.time()

        # Burn nonce to prevent replay
        self._consumed_nonces.add(tx["nonce"])

        # Return complete transaction
        result = {
            "tx_id": tx["tx_id"],
            "tx_data": tx["tx_data"],
            "signatures": tx["signatures"],
            "status": "finalized",
            "threshold_met": True,
            "nonce": tx["nonce"],
            "sequence": tx["sequence"],
        }

        # Remove from pending
        del self.pending_transactions[tx_id]

        return result
