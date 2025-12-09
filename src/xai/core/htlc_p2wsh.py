"""
HTLC helpers for Bitcoin-style P2WSH contracts.
"""

from __future__ import annotations

import hashlib
from typing import Dict, Tuple

from .utxo_address import redeem_script_to_p2wsh_address
from .aixn_blockchain.atomic_swap_11_coins import AtomicSwapHTLC


def build_utxo_contract(secret_hash: str, timelock: int, recipient_pubkey: str, sender_pubkey: str) -> Dict[str, str]:
    redeem_script = AtomicSwapHTLC.build_utxo_redeem_script(secret_hash, recipient_pubkey, sender_pubkey, timelock)
    address = redeem_script_to_p2wsh_address(redeem_script)
    return {"redeem_script": redeem_script, "p2wsh_address": address, "witness_program": hashlib.sha256(redeem_script.encode("utf-8")).hexdigest()}


def build_claim_witness(secret_hex: str, recipient_sig_hex: str, redeem_script: str) -> Tuple[str, str, str, str]:
    """
    Build witness stack for claim path: [sig, secret, 1, redeem_script]
    Returns tuple of hex elements (sig, secret, selector, redeem_script_hex_utf8).
    """
    return recipient_sig_hex, secret_hex, "01", redeem_script.encode("utf-8").hex()


def build_refund_witness(sender_sig_hex: str, redeem_script: str) -> Tuple[str, str, str]:
    """
    Build witness stack for refund path: [sig, 0, redeem_script]
    Returns tuple of hex elements (sig, selector, redeem_script_hex_utf8).
    """
    return sender_sig_hex, "00", redeem_script.encode("utf-8").hex()
