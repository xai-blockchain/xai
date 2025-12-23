"""
Offline transaction signing helpers.

Provides deterministic serialization and signing/verification helpers so users
can sign transactions on an air-gapped device and submit later.
"""

from __future__ import annotations

import hashlib
import json
import time
from hmac import compare_digest
from typing import Any

from xai.core.crypto_utils import derive_public_key_hex, sign_message_hex, verify_signature_hex
from xai.core.transaction import Transaction, TransactionValidationError

# Minimum number of characters of the signing digest a user must acknowledge
_ACK_MIN_PREFIX = 8

def _build_transaction(tx: dict[str, Any]) -> tuple[Transaction, dict[str, Any]]:
    """
    Build a canonical Transaction instance from a loose dict without mutating the caller's data.

    Returns:
        (Transaction, canonical_payload_dict)
    """
    tx_copy = dict(tx)
    try:
        timestamp = float(tx_copy.pop("timestamp", time.time()))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid timestamp: {exc}") from exc

    try:
        tx_obj = Transaction(
            sender=tx_copy.get("sender"),
            recipient=tx_copy.get("recipient"),
            amount=tx_copy.get("amount"),
            fee=tx_copy.get("fee", 0.0),
            public_key=tx_copy.get("public_key"),
            tx_type=tx_copy.get("tx_type", "normal"),
            nonce=tx_copy.get("nonce"),
            inputs=tx_copy.get("inputs"),
            outputs=tx_copy.get("outputs"),
            metadata=tx_copy.get("metadata") or {},
        )
    except TransactionValidationError as exc:
        raise ValueError(f"Invalid transaction payload: {exc}") from exc

    tx_obj.timestamp = timestamp
    canonical_payload: dict[str, Any] = {
        "sender": tx_obj.sender,
        "recipient": tx_obj.recipient,
        "amount": tx_obj.amount,
        "fee": tx_obj.fee,
        "nonce": tx_obj.nonce,
        "tx_type": tx_obj.tx_type,
        "metadata": tx_obj.metadata,
        "inputs": tx_obj.inputs,
        "outputs": tx_obj.outputs,
        "timestamp": tx_obj.timestamp,
    }
    return tx_obj, canonical_payload

def signing_preview(tx: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
    """
    Produce a deterministic preview for user acknowledgement.

    Returns:
        payload_str: Canonical JSON string with stable ordering
        tx_hash: Transaction hash to be signed (hex)
        canonical_payload: Dict suitable for persistence/logging
    """
    tx_obj, canonical_payload = _build_transaction(tx)
    payload_str = json.dumps(canonical_payload, sort_keys=True, separators=(",", ":"))
    tx_hash = tx_obj.calculate_hash()
    return payload_str, tx_hash, canonical_payload

def _validate_acknowledgement(tx_hash: str, acknowledged_prefix: str) -> None:
    """Ensure the user explicitly acknowledged the signing hash."""
    if not acknowledged_prefix or len(acknowledged_prefix) < _ACK_MIN_PREFIX:
        raise ValueError(
            f"Acknowledgement prefix must be at least {_ACK_MIN_PREFIX} characters of the transaction hash"
        )
    normalized_ack = acknowledged_prefix.lower()
    if not tx_hash.lower().startswith(normalized_ack):
        raise ValueError("Acknowledgement hash prefix does not match the transaction hash")

def sign_offline(tx: dict[str, Any], private_key_hex: str, *, acknowledged_digest: str) -> dict[str, Any]:
    """
    Sign a transaction payload offline and return signed payload.

    The caller must present the transaction hash to the user and supply the
    acknowledged_digest (prefix of the hash) to enforce explicit consent before
    the private key is used.
    """
    payload_str, tx_hash, canonical_payload = signing_preview(tx)
    _validate_acknowledgement(tx_hash, acknowledged_digest)

    signature = sign_message_hex(private_key_hex, tx_hash.encode("utf-8"))
    public_key = derive_public_key_hex(private_key_hex)
    signed = dict(canonical_payload)
    signed["public_key"] = public_key
    signed["signature"] = signature
    signed["txid"] = tx_hash
    # Retain the exact preview string for auditability/debugging without recomputation
    signed["payload_preview"] = payload_str
    return signed

def verify_offline_signature(tx: dict[str, Any]) -> bool:
    """Verify an offline-signed transaction dict with public_key/signature included."""
    pub = tx.get("public_key")
    sig = tx.get("signature")
    if not pub or not sig:
        return False

    try:
        tx_obj, _ = _build_transaction(tx)
    except ValueError:
        return False

    expected_hash = tx_obj.calculate_hash()
    provided_txid = tx.get("txid")
    if provided_txid and not compare_digest(provided_txid.lower(), expected_hash.lower()):
        return False

    tx_obj.signature = sig
    tx_obj.public_key = pub
    return tx_obj.verify_signature()
