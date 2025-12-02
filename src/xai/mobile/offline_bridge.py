"""
Mobile Wallet Bridge for Offline Signing
Task 180: Add mobile wallet bridge for offline signing

This module provides air-gapped transaction signing for enhanced security.
Transactions are created online, signed offline, and broadcast online.
"""

from __future__ import annotations

import json
import base64
import hashlib
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict


@dataclass
class UnsignedTransaction:
    """Unsigned transaction for offline signing"""
    sender: str
    recipient: str
    amount: float
    fee: float
    timestamp: float
    nonce: Optional[int] = None
    inputs: Optional[List[Dict[str, Any]]] = None
    outputs: Optional[List[Dict[str, Any]]] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True)

    def to_base64(self) -> str:
        return base64.b64encode(self.to_json().encode()).decode()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> UnsignedTransaction:
        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str) -> UnsignedTransaction:
        return cls.from_dict(json.loads(json_str))

    @classmethod
    def from_base64(cls, b64_str: str) -> UnsignedTransaction:
        json_str = base64.b64decode(b64_str).decode()
        return cls.from_json(json_str)


@dataclass
class SignedTransaction:
    """Signed transaction ready for broadcast"""
    unsigned_tx: UnsignedTransaction
    signature: str
    public_key: str
    txid: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "unsigned_tx": self.unsigned_tx.to_dict(),
            "signature": self.signature,
            "public_key": self.public_key,
            "txid": self.txid
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True)

    def to_base64(self) -> str:
        return base64.b64encode(self.to_json().encode()).decode()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SignedTransaction:
        return cls(
            unsigned_tx=UnsignedTransaction.from_dict(data["unsigned_tx"]),
            signature=data["signature"],
            public_key=data["public_key"],
            txid=data["txid"]
        )

    @classmethod
    def from_json(cls, json_str: str) -> SignedTransaction:
        return cls.from_dict(json.loads(json_str))

    @classmethod
    def from_base64(cls, b64_str: str) -> SignedTransaction:
        json_str = base64.b64decode(b64_str).decode()
        return cls.from_json(json_str)


class OfflineSigningBridge:
    """
    Bridge for offline transaction signing

    Workflow:
    1. Online device creates unsigned transaction
    2. Transfer unsigned tx to offline device (QR/USB/etc)
    3. Offline device signs transaction
    4. Transfer signed tx back to online device
    5. Online device broadcasts transaction
    """

    @staticmethod
    def create_unsigned_transaction(
        sender: str,
        recipient: str,
        amount: float,
        fee: float = 0.001,
        nonce: Optional[int] = None,
        inputs: Optional[List[Dict[str, Any]]] = None,
        outputs: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> UnsignedTransaction:
        """
        Create an unsigned transaction (online device)

        Args:
            sender: Sender address
            recipient: Recipient address
            amount: Amount to send
            fee: Transaction fee
            nonce: Transaction nonce
            inputs: Transaction inputs (UTXO)
            outputs: Transaction outputs
            metadata: Additional metadata

        Returns:
            Unsigned transaction
        """
        return UnsignedTransaction(
            sender=sender,
            recipient=recipient,
            amount=amount,
            fee=fee,
            timestamp=time.time(),
            nonce=nonce,
            inputs=inputs or [],
            outputs=outputs or [],
            metadata=metadata or {}
        )

    @staticmethod
    def sign_transaction_offline(
        unsigned_tx: UnsignedTransaction,
        private_key: str,
        public_key: str
    ) -> SignedTransaction:
        """
        Sign transaction on offline device

        Args:
            unsigned_tx: Unsigned transaction
            private_key: Private key for signing
            public_key: Public key

        Returns:
            Signed transaction
        """
        # Import here to avoid circular dependencies
        from xai.core.crypto_utils import sign_message_hex

        # Calculate transaction hash
        tx_data = unsigned_tx.to_dict()
        tx_string = json.dumps(tx_data, sort_keys=True)
        txid = hashlib.sha256(tx_string.encode()).hexdigest()

        # Sign the transaction
        message = txid.encode()
        signature = sign_message_hex(private_key, message)

        return SignedTransaction(
            unsigned_tx=unsigned_tx,
            signature=signature,
            public_key=public_key,
            txid=txid
        )

    @staticmethod
    def verify_signed_transaction(signed_tx: SignedTransaction) -> bool:
        """
        Verify signed transaction before broadcast

        Args:
            signed_tx: Signed transaction

        Returns:
            True if signature is valid
        """
        # Import here to avoid circular dependencies
        from xai.core.crypto_utils import verify_signature_hex

        # Recalculate txid
        tx_data = signed_tx.unsigned_tx.to_dict()
        tx_string = json.dumps(tx_data, sort_keys=True)
        expected_txid = hashlib.sha256(tx_string.encode()).hexdigest()

        if expected_txid != signed_tx.txid:
            return False

        # Verify signature
        message = signed_tx.txid.encode()
        return verify_signature_hex(
            signed_tx.public_key,
            message,
            signed_tx.signature
        )

    @staticmethod
    def convert_to_blockchain_transaction(signed_tx: SignedTransaction) -> Dict[str, Any]:
        """
        Convert signed transaction to blockchain format

        Args:
            signed_tx: Signed transaction

        Returns:
            Transaction dictionary for blockchain
        """
        tx = signed_tx.unsigned_tx
        return {
            "txid": signed_tx.txid,
            "sender": tx.sender,
            "recipient": tx.recipient,
            "amount": tx.amount,
            "fee": tx.fee,
            "timestamp": tx.timestamp,
            "nonce": tx.nonce,
            "inputs": tx.inputs,
            "outputs": tx.outputs,
            "metadata": tx.metadata,
            "signature": signed_tx.signature,
            "public_key": signed_tx.public_key
        }


class QROfflineBridge:
    """
    QR code-based offline signing

    Uses QR codes to transfer data between online and offline devices
    """

    @staticmethod
    def create_unsigned_qr(unsigned_tx: UnsignedTransaction) -> str:
        """
        Create QR code data for unsigned transaction

        Args:
            unsigned_tx: Unsigned transaction

        Returns:
            QR code data string
        """
        return f"xai:unsigned:{unsigned_tx.to_base64()}"

    @staticmethod
    def parse_unsigned_qr(qr_data: str) -> UnsignedTransaction:
        """
        Parse unsigned transaction from QR code

        Args:
            qr_data: QR code data

        Returns:
            Unsigned transaction
        """
        if not qr_data.startswith("xai:unsigned:"):
            raise ValueError("Invalid unsigned transaction QR code")

        b64_data = qr_data[13:]  # Remove 'xai:unsigned:' prefix
        return UnsignedTransaction.from_base64(b64_data)

    @staticmethod
    def create_signed_qr(signed_tx: SignedTransaction) -> str:
        """
        Create QR code data for signed transaction

        Args:
            signed_tx: Signed transaction

        Returns:
            QR code data string
        """
        return f"xai:signed:{signed_tx.to_base64()}"

    @staticmethod
    def parse_signed_qr(qr_data: str) -> SignedTransaction:
        """
        Parse signed transaction from QR code

        Args:
            qr_data: QR code data

        Returns:
            Signed transaction
        """
        if not qr_data.startswith("xai:signed:"):
            raise ValueError("Invalid signed transaction QR code")

        b64_data = qr_data[11:]  # Remove 'xai:signed:' prefix
        return SignedTransaction.from_base64(b64_data)


class BatchOfflineSigning:
    """
    Batch multiple transactions for offline signing

    Useful for signing multiple transactions at once on an offline device
    """

    @staticmethod
    def create_batch(unsigned_txs: List[UnsignedTransaction]) -> str:
        """
        Create batch of unsigned transactions

        Args:
            unsigned_txs: List of unsigned transactions

        Returns:
            Base64-encoded batch
        """
        batch_data = {
            "version": 1,
            "count": len(unsigned_txs),
            "transactions": [tx.to_dict() for tx in unsigned_txs]
        }
        batch_json = json.dumps(batch_data, sort_keys=True)
        return base64.b64encode(batch_json.encode()).decode()

    @staticmethod
    def parse_batch(batch_data: str) -> List[UnsignedTransaction]:
        """
        Parse batch of unsigned transactions

        Args:
            batch_data: Base64-encoded batch

        Returns:
            List of unsigned transactions
        """
        batch_json = base64.b64decode(batch_data).decode()
        batch = json.loads(batch_json)

        return [
            UnsignedTransaction.from_dict(tx)
            for tx in batch["transactions"]
        ]

    @staticmethod
    def sign_batch(
        unsigned_txs: List[UnsignedTransaction],
        private_key: str,
        public_key: str
    ) -> List[SignedTransaction]:
        """
        Sign a batch of transactions offline

        Args:
            unsigned_txs: List of unsigned transactions
            private_key: Private key
            public_key: Public key

        Returns:
            List of signed transactions
        """
        bridge = OfflineSigningBridge()
        return [
            bridge.sign_transaction_offline(tx, private_key, public_key)
            for tx in unsigned_txs
        ]

    @staticmethod
    def create_signed_batch(signed_txs: List[SignedTransaction]) -> str:
        """
        Create batch of signed transactions

        Args:
            signed_txs: List of signed transactions

        Returns:
            Base64-encoded batch
        """
        batch_data = {
            "version": 1,
            "count": len(signed_txs),
            "transactions": [tx.to_dict() for tx in signed_txs]
        }
        batch_json = json.dumps(batch_data, sort_keys=True)
        return base64.b64encode(batch_json.encode()).decode()

    @staticmethod
    def parse_signed_batch(batch_data: str) -> List[SignedTransaction]:
        """
        Parse batch of signed transactions

        Args:
            batch_data: Base64-encoded batch

        Returns:
            List of signed transactions
        """
        batch_json = base64.b64decode(batch_data).decode()
        batch = json.loads(batch_json)

        return [
            SignedTransaction.from_dict(tx)
            for tx in batch["transactions"]
        ]


class OfflineSigningValidator:
    """Security validation for offline signing"""

    @staticmethod
    def validate_unsigned_transaction(unsigned_tx: UnsignedTransaction) -> bool:
        """
        Validate unsigned transaction before signing

        Args:
            unsigned_tx: Unsigned transaction

        Returns:
            True if valid
        """
        # Check required fields
        if not unsigned_tx.sender or not unsigned_tx.recipient:
            return False

        # Validate addresses
        if not unsigned_tx.sender.startswith("XAI"):
            return False
        if not unsigned_tx.recipient.startswith("XAI"):
            return False

        # Validate amounts
        if unsigned_tx.amount < 0 or unsigned_tx.fee < 0:
            return False

        # Check timestamp is reasonable (within 1 hour of current time)
        current_time = time.time()
        if abs(unsigned_tx.timestamp - current_time) > 3600:
            return False

        return True

    @staticmethod
    def validate_signature_before_broadcast(signed_tx: SignedTransaction) -> bool:
        """
        Validate signed transaction before broadcast

        Args:
            signed_tx: Signed transaction

        Returns:
            True if valid
        """
        # Validate unsigned transaction
        if not OfflineSigningValidator.validate_unsigned_transaction(signed_tx.unsigned_tx):
            return False

        # Verify signature
        if not OfflineSigningBridge.verify_signed_transaction(signed_tx):
            return False

        # Verify address matches public key (hash bytes, not hex string)
        pub_key_bytes = bytes.fromhex(signed_tx.public_key)
        pub_hash = hashlib.sha256(pub_key_bytes).hexdigest()
        expected_address = f"XAI{pub_hash[:40]}"
        if expected_address != signed_tx.unsigned_tx.sender:
            return False

        return True
