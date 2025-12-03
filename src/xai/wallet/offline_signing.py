"""
Offline transaction signing helpers.

Provides deterministic serialization and signing/verification helpers so users
can sign transactions on an air-gapped device and submit later.
"""

from __future__ import annotations

import json
import hashlib
from typing import Any, Dict

from xai.core.crypto_utils import sign_message_hex, verify_signature_hex, derive_public_key_hex


CANONICAL_FIELDS = [
    "sender",
    "recipient",
    "amount",
    "fee",
    "nonce",
    "tx_type",
    "metadata",
]


def serialize_transaction_payload(tx: Dict[str, Any]) -> str:
    """Deterministically serialize a transaction dict for signing."""
    payload: Dict[str, Any] = {}
    for k in CANONICAL_FIELDS:
        if k in tx and tx[k] is not None:
            payload[k] = tx[k]
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def signing_digest(payload_str: str) -> bytes:
    return hashlib.sha256(payload_str.encode("utf-8")).digest()


def sign_offline(tx: Dict[str, Any], private_key_hex: str) -> Dict[str, Any]:
    """Sign a transaction payload offline and return signed payload."""
    payload_str = serialize_transaction_payload(tx)
    digest = signing_digest(payload_str)
    signature = sign_message_hex(private_key_hex, digest)
    public_key = derive_public_key_hex(private_key_hex)
    signed = dict(tx)
    signed["public_key"] = public_key
    signed["signature"] = signature
    return signed


def verify_offline_signature(tx: Dict[str, Any]) -> bool:
    """Verify an offline-signed transaction dict with public_key/signature included."""
    pub = tx.get("public_key")
    sig = tx.get("signature")
    if not pub or not sig:
        return False
    payload_str = serialize_transaction_payload(tx)
    digest = signing_digest(payload_str)
    return verify_signature_hex(pub, digest, sig)
