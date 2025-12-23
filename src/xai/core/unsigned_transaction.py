from __future__ import annotations

"""
XAI Unsigned Transaction Format (XUTX)

A standardized format for unsigned transactions, inspired by Bitcoin's PSBT (BIP-174).
Enables safe transaction construction, review, and signing across different wallets
and hardware devices.

Format supports:
- Transaction metadata for human review
- Multiple input/output support
- Partial signature collection
- Hardware wallet compatibility
- JSON serialization for portability
"""

import base64
import hashlib
import json
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class TxStatus(Enum):
    """Transaction lifecycle status."""
    UNSIGNED = "unsigned"
    PARTIALLY_SIGNED = "partially_signed"
    FULLY_SIGNED = "fully_signed"
    BROADCAST = "broadcast"
    CONFIRMED = "confirmed"

@dataclass
class TxInput:
    """Transaction input (source of funds)."""
    address: str
    amount: float
    utxo_id: str | None = None  # Reference to unspent output
    sequence: int = 0xFFFFFFFF

@dataclass
class TxOutput:
    """Transaction output (destination of funds)."""
    address: str
    amount: float
    memo: str | None = None

@dataclass
class SignatureSlot:
    """Slot for collecting signatures."""
    public_key: str
    signature: str | None = None
    signed_at: int | None = None
    signer_label: str | None = None

@dataclass
class UnsignedTransaction:
    """
    XAI Unsigned Transaction (XUTX) Format.

    A complete, self-describing transaction format that can be:
    - Created by any wallet
    - Reviewed by humans (all amounts, addresses visible)
    - Signed by hardware wallets
    - Passed between parties for multisig
    - Verified before broadcast
    """

    # Version for format evolution
    version: str = "1.0"

    # Transaction type
    tx_type: str = "transfer"  # transfer, multisig, contract, etc.

    # Core transaction data
    sender: str = ""
    recipient: str = ""
    amount: float = 0.0
    fee: float = 0.001

    # Extended fields
    inputs: list[TxInput] = field(default_factory=list)
    outputs: list[TxOutput] = field(default_factory=list)

    # Timing
    created_at: int = field(default_factory=lambda: int(time.time()))
    expires_at: int | None = None  # Optional expiration
    nonce: int | None = None

    # Signing
    threshold: int = 1  # Signatures required
    signature_slots: list[SignatureSlot] = field(default_factory=list)

    # Metadata for human review
    memo: str = ""
    network: str = "mainnet"  # mainnet, testnet

    # Status tracking
    status: str = TxStatus.UNSIGNED.value

    # Computed fields (not serialized, computed on demand)
    _payload_hash: str | None = field(default=None, repr=False)

    def __post_init__(self):
        """Initialize computed fields."""
        if not self.signature_slots and self.threshold == 1:
            # Single-sig: create one slot
            self.signature_slots = [SignatureSlot(public_key="")]

    @property
    def payload(self) -> dict[str, Any]:
        """Get the signable payload (excludes signatures)."""
        return {
            "version": self.version,
            "tx_type": self.tx_type,
            "sender": self.sender,
            "recipient": self.recipient,
            "amount": self.amount,
            "fee": self.fee,
            "nonce": self.nonce,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "memo": self.memo,
            "network": self.network,
        }

    @property
    def payload_hash(self) -> str:
        """Compute SHA256 hash of the signable payload."""
        if self._payload_hash is None:
            canonical = json.dumps(self.payload, sort_keys=True, separators=(',', ':'))
            self._payload_hash = hashlib.sha256(canonical.encode('utf-8')).hexdigest()
        return self._payload_hash

    @property
    def payload_bytes(self) -> bytes:
        """Get payload as bytes for signing."""
        canonical = json.dumps(self.payload, sort_keys=True, separators=(',', ':'))
        return canonical.encode('utf-8')

    @property
    def signature_count(self) -> int:
        """Count collected signatures."""
        return sum(1 for slot in self.signature_slots if slot.signature)

    @property
    def is_ready(self) -> bool:
        """Check if transaction has enough signatures."""
        return self.signature_count >= self.threshold

    def add_signature(self, public_key: str, signature: str, label: str | None = None) -> bool:
        """
        Add a signature to the transaction.

        Args:
            public_key: Signer's public key (hex)
            signature: ECDSA signature (hex)
            label: Optional human-readable signer label

        Returns:
            True if signature was added, False if already signed or invalid
        """
        # Check for existing signature from this key
        for slot in self.signature_slots:
            if slot.public_key == public_key:
                if slot.signature:
                    return False  # Already signed
                slot.signature = signature
                slot.signed_at = int(time.time())
                slot.signer_label = label
                self._update_status()
                return True

        # Add new slot if threshold allows
        if len(self.signature_slots) < self.threshold or self.signature_slots[0].public_key == "":
            if self.signature_slots and self.signature_slots[0].public_key == "":
                # Fill empty slot (single-sig)
                self.signature_slots[0].public_key = public_key
                self.signature_slots[0].signature = signature
                self.signature_slots[0].signed_at = int(time.time())
                self.signature_slots[0].signer_label = label
            else:
                self.signature_slots.append(SignatureSlot(
                    public_key=public_key,
                    signature=signature,
                    signed_at=int(time.time()),
                    signer_label=label,
                ))
            self._update_status()
            return True

        return False

    def _update_status(self):
        """Update transaction status based on signatures."""
        if self.signature_count == 0:
            self.status = TxStatus.UNSIGNED.value
        elif self.signature_count < self.threshold:
            self.status = TxStatus.PARTIALLY_SIGNED.value
        else:
            self.status = TxStatus.FULLY_SIGNED.value

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        data = {
            "version": self.version,
            "tx_type": self.tx_type,
            "sender": self.sender,
            "recipient": self.recipient,
            "amount": self.amount,
            "fee": self.fee,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "nonce": self.nonce,
            "threshold": self.threshold,
            "memo": self.memo,
            "network": self.network,
            "status": self.status,
            "payload_hash": self.payload_hash,
            "signature_slots": [asdict(s) for s in self.signature_slots],
        }
        if self.inputs:
            data["inputs"] = [asdict(i) for i in self.inputs]
        if self.outputs:
            data["outputs"] = [asdict(o) for o in self.outputs]
        return data

    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    def to_base64(self) -> str:
        """Serialize to base64 for compact transmission."""
        return base64.b64encode(self.to_json(indent=None).encode('utf-8')).decode('utf-8')

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UnsignedTransaction":
        """Deserialize from dictionary."""
        signature_slots = [
            SignatureSlot(**s) for s in data.get("signature_slots", [])
        ]
        inputs = [TxInput(**i) for i in data.get("inputs", [])]
        outputs = [TxOutput(**o) for o in data.get("outputs", [])]

        return cls(
            version=data.get("version", "1.0"),
            tx_type=data.get("tx_type", "transfer"),
            sender=data.get("sender", ""),
            recipient=data.get("recipient", ""),
            amount=data.get("amount", 0.0),
            fee=data.get("fee", 0.001),
            created_at=data.get("created_at", int(time.time())),
            expires_at=data.get("expires_at"),
            nonce=data.get("nonce"),
            threshold=data.get("threshold", 1),
            signature_slots=signature_slots,
            inputs=inputs,
            outputs=outputs,
            memo=data.get("memo", ""),
            network=data.get("network", "mainnet"),
            status=data.get("status", TxStatus.UNSIGNED.value),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "UnsignedTransaction":
        """Deserialize from JSON string."""
        return cls.from_dict(json.loads(json_str))

    @classmethod
    def from_base64(cls, b64_str: str) -> "UnsignedTransaction":
        """Deserialize from base64 string."""
        json_str = base64.b64decode(b64_str.encode('utf-8')).decode('utf-8')
        return cls.from_json(json_str)

    def display_for_review(self) -> str:
        """Generate human-readable summary for review before signing."""
        lines = [
            "=" * 60,
            "XAI UNSIGNED TRANSACTION - REVIEW CAREFULLY",
            "=" * 60,
            f"Network:     {self.network.upper()}",
            f"Type:        {self.tx_type}",
            f"Status:      {self.status}",
            "-" * 60,
            f"From:        {self.sender}",
            f"To:          {self.recipient}",
            f"Amount:      {self.amount} XAI",
            f"Fee:         {self.fee} XAI",
            f"Total:       {self.amount + self.fee} XAI",
            "-" * 60,
            f"Payload Hash: {self.payload_hash}",
            f"Created:     {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.created_at))}",
        ]

        if self.expires_at:
            lines.append(f"Expires:     {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.expires_at))}")

        if self.memo:
            lines.append(f"Memo:        {self.memo}")

        lines.extend([
            "-" * 60,
            f"Signatures:  {self.signature_count}/{self.threshold}",
        ])

        for i, slot in enumerate(self.signature_slots, 1):
            status = "✓ Signed" if slot.signature else "○ Pending"
            label = f" ({slot.signer_label})" if slot.signer_label else ""
            pk = slot.public_key[:16] + "..." if slot.public_key else "awaiting"
            lines.append(f"  {i}. [{status}] {pk}{label}")

        lines.append("=" * 60)

        return "\n".join(lines)

def create_transfer(
    sender: str,
    recipient: str,
    amount: float,
    fee: float = 0.001,
    memo: str = "",
    network: str = "mainnet",
    nonce: int | None = None,
) -> UnsignedTransaction:
    """
    Create a simple transfer transaction.

    Args:
        sender: Sender's XAI address
        recipient: Recipient's XAI address
        amount: Amount to transfer
        fee: Transaction fee (default: 0.001)
        memo: Optional memo/note
        network: Network name (mainnet/testnet)
        nonce: Optional nonce for replay protection

    Returns:
        UnsignedTransaction ready for signing
    """
    return UnsignedTransaction(
        tx_type="transfer",
        sender=sender,
        recipient=recipient,
        amount=amount,
        fee=fee,
        memo=memo,
        network=network,
        nonce=nonce,
    )

def create_multisig_transfer(
    sender: str,
    recipient: str,
    amount: float,
    public_keys: list[str],
    threshold: int,
    fee: float = 0.001,
    memo: str = "",
    network: str = "mainnet",
) -> UnsignedTransaction:
    """
    Create a multisig transfer transaction.

    Args:
        sender: Multisig wallet address
        recipient: Recipient's XAI address
        amount: Amount to transfer
        public_keys: List of authorized signer public keys
        threshold: Required number of signatures
        fee: Transaction fee
        memo: Optional memo
        network: Network name

    Returns:
        UnsignedTransaction with signature slots for each signer
    """
    signature_slots = [SignatureSlot(public_key=pk) for pk in public_keys]

    return UnsignedTransaction(
        tx_type="multisig",
        sender=sender,
        recipient=recipient,
        amount=amount,
        fee=fee,
        threshold=threshold,
        signature_slots=signature_slots,
        memo=memo,
        network=network,
    )
