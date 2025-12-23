"""
Ledger hardware wallet integration for XAI.

This module provides a thin abstraction for interacting with Ledger devices over HID
using the standard Ethereum/XAI app APDUs. It deliberately avoids storing private
keys in memory and returns only public keys and signatures produced on-device.

Dependencies:
- ledgerblue (for HID/APDU)
- eth_account for signature normalization
"""

from __future__ import annotations

import binascii
from dataclasses import dataclass

from eth_account._utils.legacy_transactions import serializable_unsigned_transaction_from_dict
from eth_account._utils.signing import to_standard_v

try:
    from ledgerblue.comm import getDongle
except ImportError as exc:  # pragma: no cover - optional dependency
    raise ImportError("ledgerblue is required for Ledger support. pip install ledgerblue") from exc

from xai.core.hardware_wallet import HardwareWallet, _normalize_private_value

def _parse_bip32_path(path: str) -> bytes:
    if not path.startswith("m/"):
        raise ValueError("BIP32 path must start with m/")
    elements = path.lstrip("m/").split("/")
    result = len(elements).to_bytes(1, "big")
    for elt in elements:
        hardened = elt.endswith("'")
        index_str = elt[:-1] if hardened else elt
        index = int(index_str)
        if index < 0 or index >= 0x80000000:
            raise ValueError("Invalid index in BIP32 path")
        if hardened:
            index |= 0x80000000
        result += index.to_bytes(4, "big")
    return result

@dataclass
class LedgerHardwareWallet(HardwareWallet):
    bip32_path: str = "m/44'/22593'/0'/0/0"
    _dongle: object | None = None

    def connect(self) -> bool:
        self._dongle = getDongle(True)
        return True

    def _require_dongle(self) -> object:
        if not self._dongle:
            self.connect()
        return self._dongle

    def get_public_key(self) -> str:
        dongle = self._require_dongle()
        path = _parse_bip32_path(self.bip32_path)
        apdu = bytes.fromhex("e0020000") + len(path).to_bytes(1, "big") + path
        result = dongle.exchange(apdu)
        offset = 1 + result[0]
        public_key = result[offset + 1 : offset + 1 + result[offset]]
        return binascii.hexlify(public_key).decode()

    def sign_message(self, message: bytes) -> bytes:
        dongle = self._require_dongle()
        path = _parse_bip32_path(self.bip32_path)
        msg_len = len(message).to_bytes(2, "big")
        chunks = [
            bytes.fromhex("e0040000")
            + len(path).to_bytes(1, "big")
            + path
            + msg_len
            + message
        ]
        result = dongle.exchange(chunks[0])
        return bytes(result)

    def sign_transaction(self, tx_dict: dict) -> str:
        unsigned_tx = serializable_unsigned_transaction_from_dict(tx_dict)
        raw_unsigned = unsigned_tx.to_bytes()
        signature = self.sign_message(raw_unsigned)
        r = int.from_bytes(signature[0:32], "big")
        s = int.from_bytes(signature[32:64], "big")
        v = to_standard_v(signature[64])
        tx_signed = unsigned_tx.as_signed_transaction(vrs=(v, r, s))
        return tx_signed.hex()

    def get_address(self) -> str:
        # Derive address from pubkey
        pub_hex = self.get_public_key()
        pub_bytes = bytes.fromhex(pub_hex)
        import hashlib

        # Use network-appropriate prefix
        from xai.core.config import NETWORK
        prefix = "XAI" if NETWORK.lower() == "mainnet" else "TXAI"
        h = hashlib.sha256(pub_bytes).hexdigest()
        return f"{prefix}{h[:40]}"
