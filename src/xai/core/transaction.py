
"""
XAI Blockchain Core - Transaction
"""

from __future__ import annotations

import hashlib
import json
import time
from typing import List, Dict, Optional, Any
import base58
from xai.core.crypto_utils import sign_message_hex, verify_signature_hex, derive_public_key_hex


class Transaction:
    """Real cryptocurrency transaction with ECDSA signatures, supporting UTXO model."""
    # Domain separation context for TXID/signatures to prevent cross-network replay
    _CHAIN_CONTEXT: str = "mainnet"

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
    ) -> None:
        self.sender = sender
        self.recipient = recipient
        self.amount = amount
        self.fee = fee
        self.timestamp = time.time()
        self.signature = None
        self.txid = None
        self.public_key = public_key
        self.tx_type = tx_type
        self.nonce = nonce
        self.metadata: Dict[str, Any] = metadata or {}
        self.rbf_enabled = rbf_enabled
        self.replaces_txid = replaces_txid
        self.inputs = (
            inputs if inputs is not None else []
        )
        self.outputs = (
            outputs if outputs is not None else []
        )

        if not self.outputs and self.recipient and self.amount > 0:
            self.outputs.append({"address": self.recipient, "amount": self.amount})

    def calculate_hash(self) -> str:
        """Calculate transaction hash (TXID)"""
        try:
            from xai.core.config import Config
            context = getattr(Config, "CHAIN_ID", None) or getattr(Config, "NETWORK_TYPE", Transaction._CHAIN_CONTEXT)
            # Normalize enum/other types to string
            if hasattr(context, "value"):
                context = context.value
            Transaction._CHAIN_CONTEXT = str(context)
        except Exception:
            pass

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
        tx_string = json.dumps(tx_data, sort_keys=True)
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
        except Exception as e:
            raise ValueError(f"Failed to sign transaction: {e}")

    def verify_signature(self) -> bool:
        """Verify transaction signature"""
        if self.sender == "COINBASE":
            return True

        if not self.signature or not self.public_key:
            return False

        try:
            pub_hash = hashlib.sha256(self.public_key.encode()).hexdigest()
            expected_address = f"XAI{pub_hash[:40]}"
            if expected_address != self.sender:
                print(f"Address mismatch: expected {expected_address}, got {self.sender}")
                return False

            message = self.calculate_hash().encode()
            return verify_signature_hex(self.public_key, message, self.signature)
        except Exception as e:
            print(f"Signature verification error: {e}")
            return False

    def get_size(self) -> int:
        """
        Calculate transaction size in bytes for fee-per-byte calculations.
        """
        try:
            serialized = json.dumps(self.to_dict(), sort_keys=True)
            return len(serialized.encode('utf-8'))
        except Exception:
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
        return {
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
