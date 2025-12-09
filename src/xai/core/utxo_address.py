"""
Utility for deriving P2WSH bech32 addresses for HTLC scripts.
"""

from __future__ import annotations

import hashlib
from typing import Optional

import bech32


def redeem_script_to_p2wsh_address(redeem_script: bytes | str, hrp: str = "bc") -> Optional[str]:
    """
    Convert a redeem script string to a P2WSH bech32 address.
    """
    if redeem_script is None or redeem_script == b"" or redeem_script == "":
        return None
    if isinstance(redeem_script, str):
        redeem_script = bytes.fromhex(redeem_script)
    script_hash = hashlib.sha256(redeem_script).digest()
    # Witness version 0, program is 32 bytes
    data = [0] + list(bech32.convertbits(script_hash, 8, 5))
    return bech32.bech32_encode(hrp, data)
