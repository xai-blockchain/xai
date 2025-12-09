"""
HTLC helpers for Bitcoin-style P2WSH contracts.
"""

from __future__ import annotations

import hashlib
from typing import Dict, Tuple

from .utxo_address import redeem_script_to_p2wsh_address


OP_IF = "63"
OP_ELSE = "67"
OP_ENDIF = "68"
OP_SHA256 = "a8"
OP_EQUALVERIFY = "88"
OP_CHECKSIG = "ac"
OP_CHECKLOCKTIMEVERIFY = "b1"
OP_DROP = "75"


def _encode_push(data_hex: str) -> str:
    """Encode data push (single-byte length prefix for simplicity)."""
    if len(data_hex) % 2 != 0:
        raise ValueError("data_hex must have even length")
    length = len(data_hex) // 2
    if length > 75:
        raise ValueError("push too long for single-byte length")
    return f"{length:02x}{data_hex}"


def _encode_timelock(timelock: int) -> str:
    # Minimal encoding little-endian
    raw = timelock.to_bytes((timelock.bit_length() + 7) // 8 or 1, "little")
    # Ensure highest bit not set; if so, append 0x00 for minimal encoding
    if raw[-1] & 0x80:
        raw += b"\x00"
    return _encode_push(raw.hex())


def _pubkey_push(pubkey_hex: str) -> str:
    return _encode_push(pubkey_hex)


def build_utxo_contract(secret_hash_hex: str, timelock: int, recipient_pubkey: str, sender_pubkey: str) -> Dict[str, str]:
    """
    Build canonical HTLC redeem script and derived P2WSH address.
    Script (hex):
    OP_IF
        OP_SHA256 <secret_hash> OP_EQUALVERIFY
        <recipient_pubkey> OP_CHECKSIG
    OP_ELSE
        <timelock> OP_CHECKLOCKTIMEVERIFY OP_DROP
        <sender_pubkey> OP_CHECKSIG
    OP_ENDIF
    """
    # Build script in hex
    parts = [
        OP_IF,
        OP_SHA256,
        _encode_push(secret_hash_hex),
        OP_EQUALVERIFY,
        _pubkey_push(recipient_pubkey),
        OP_CHECKSIG,
        OP_ELSE,
        _encode_timelock(timelock),
        OP_CHECKLOCKTIMEVERIFY,
        OP_DROP,
        _pubkey_push(sender_pubkey),
        OP_CHECKSIG,
        OP_ENDIF,
    ]
    redeem_script_hex = "".join(parts)
    redeem_script_bytes = bytes.fromhex(redeem_script_hex)
    witness_program = hashlib.sha256(redeem_script_bytes).digest()
    address = redeem_script_to_p2wsh_address(redeem_script_bytes)
    return {
        "redeem_script_hex": redeem_script_hex,
        "p2wsh_address": address,
        "witness_program": witness_program.hex(),
    }


def build_claim_witness(secret_hex: str, recipient_sig_hex: str, redeem_script_hex: str) -> Tuple[str, str, str, str]:
    """
    Build witness stack for claim path: [sig, secret, 1, redeem_script]
    Returns tuple of hex elements (sig, secret, selector, redeem_script_hex).
    """
    return recipient_sig_hex, secret_hex, "01", redeem_script_hex


def build_refund_witness(sender_sig_hex: str, redeem_script_hex: str) -> Tuple[str, str, str]:
    """
    Build witness stack for refund path: [sig, 0, redeem_script]
    Returns tuple of hex elements (sig, selector, redeem_script_hex).
    """
    return sender_sig_hex, "00", redeem_script_hex
