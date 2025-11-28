from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import load_pem_public_key, load_pem_private_key
from typing import List, Dict, Optional
import json
import time


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
        self.pending_transactions: Dict[str, Dict] = {}

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
            print(f"[MULTISIG] Insufficient signatures: {len(signatures)}/{self.threshold} required")
            return False

        message_hash = hashes.Hash(hashes.SHA256())
        message_hash.update(message)
        digest = message_hash.finalize()

        valid_signatures = 0
        invalid_signatures = []

        for pub_key_hex, signature_hex in signatures.items():
            # Verify public key is authorized
            if pub_key_hex not in self.public_keys_hex:
                print(f"[MULTISIG] Unauthorized public key: {pub_key_hex[:16]}...")
                continue

            try:
                public_key = load_pem_public_key(bytes.fromhex(pub_key_hex))
                signature = bytes.fromhex(signature_hex)
                public_key.verify(signature, digest, ec.ECDSA(hashes.SHA256()))
                valid_signatures += 1
                print(f"[MULTISIG] Valid signature from: {pub_key_hex[:16]}...")
            except Exception as e:
                invalid_signatures.append(pub_key_hex[:16])
                print(f"[MULTISIG] Invalid signature from {pub_key_hex[:16]}...: {e}")
                continue

        # TASK 26: Detailed threshold validation
        if valid_signatures < self.threshold:
            print(f"[MULTISIG] Threshold not met: {valid_signatures}/{self.threshold} valid signatures")
            if invalid_signatures:
                print(f"[MULTISIG] Invalid signatures from: {', '.join(invalid_signatures)}")
            return False

        print(f"[MULTISIG] Threshold met: {valid_signatures}/{self.threshold} signatures verified")
        return True

    # ===== PARTIAL SIGNATURE SUPPORT (TASK 210) =====

    def create_transaction(self, tx_id: str, tx_data: Dict) -> Dict:
        """
        Create a new pending transaction for signature collection.

        Args:
            tx_id: Unique transaction identifier
            tx_data: Transaction data to be signed

        Returns:
            Transaction info
        """
        if tx_id in self.pending_transactions:
            raise ValueError(f"Transaction {tx_id} already exists")

        self.pending_transactions[tx_id] = {
            "tx_id": tx_id,
            "tx_data": tx_data,
            "signatures": {},
            "created_at": time.time(),
            "status": "pending",
            "threshold": self.threshold,
            "signers_required": self.threshold,
            "signers_collected": 0,
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

        # Validate signature
        message = json.dumps(tx["tx_data"], sort_keys=True).encode()
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
            print(f"[MULTISIG] Transaction {tx_id} ready: {tx['signers_collected']}/{tx['threshold']} signatures")

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

        # Return complete transaction
        result = {
            "tx_id": tx["tx_id"],
            "tx_data": tx["tx_data"],
            "signatures": tx["signatures"],
            "status": "finalized",
            "threshold_met": True,
        }

        # Remove from pending
        del self.pending_transactions[tx_id]

        return result
