"""
Ledger hardware wallet adapter for the XAI blockchain.

This module wraps `ledgerblue` commands for public key derivation and signing.
It currently relies on the built-in Bitcoin-style APDUs (0xE0/0x02 for GET_PUBLIC_KEY
and 0xE0/0x04 for SIGN) so that any Ledger already supporting Bitcoin can derive the
same compressed public key and compute an XAI address.
"""

import hashlib
import struct
from typing import Optional

from hardware_wallet import HardwareWallet
from aixn.core.config import Config

try:
    from ledgerblue.comm import getDongle
    from ledgerblue.commException import CommException
except ImportError:  # pragma: no cover
    getDongle = None
    CommException = None


class LedgerHardwareWallet(HardwareWallet):
    """Ledger-based hardware wallet implementation."""

    CLA = 0xE0
    INS_GET_PUBLIC_KEY = 0x02
    INS_SIGN = 0x04

    def __init__(self, derivation_path: Optional[str] = None):
        self.derivation_path = derivation_path or Config.LEDGER_DERIVATION_PATH
        self.dongle = None

    def connect(self) -> bool:
        """Open a transport channel to the Ledger device."""
        if getDongle is None:
            raise RuntimeError("ledgerblue is not installed")
        if self.dongle:
            return True
        try:
            self.dongle = getDongle(False)
            return True
        except CommException as exc:  # pragma: no cover
            raise RuntimeError(f"Ledger connection failed: {exc}")

    def _serialize_derivation_path(self) -> bytes:
        """Serialize BIP32 path into ledger-friendly format."""
        elements = self.derivation_path.split("/")
        if elements[0].lower() == "m":
            elements = elements[1:]

        result = struct.pack("B", len(elements))
        for component in elements:
            hardened = component.endswith("'")
            if hardened:
                component = component[:-1]
            value = int(component)
            if hardened:
                value |= 0x80000000
            result += struct.pack(">I", value)
        return result

    def _exchange(self, cla: int, ins: int, p1: int, p2: int, data: bytes) -> bytes:
        if not self.dongle:
            self.connect()
        apdu = bytes([cla, ins, p1, p2, len(data)]) + data
        return self.dongle.exchange(apdu, timeout=20000)

    def _get_public_key(self) -> bytes:
        """Request the compressed public key from the Ledger."""
        payload = self._serialize_derivation_path()
        response = self._exchange(self.CLA, self.INS_GET_PUBLIC_KEY, 0x00, 0x00, payload)
        # Response structure: [0x41][0x04 + 64 bytes compressed key]...
        if len(response) < 66:
            raise RuntimeError("Unexpected Ledger response for public key")
        return response[1:66]

    def get_address(self) -> str:
        """Derive an XAI address (`XAI` + first 40 hex of sha256(pubkey))."""
        pub_key = self._get_public_key()
        pub_hash = hashlib.sha256(pub_key).hexdigest()
        return f"XAI{pub_hash[:40]}"

    def sign_transaction(self, payload: bytes) -> bytes:
        """Sign `payload` via the Ledger device."""
        if not self.dongle:
            self.connect()

        data = self._serialize_derivation_path() + payload
        offset = 0
        signature = b""
        while offset < len(data):
            chunk = data[offset : offset + 250]
            p1 = 0x00 if offset == 0 else 0x80
            response = self._exchange(self.CLA, self.INS_SIGN, p1, 0x00, chunk)
            signature = response
            offset += len(chunk)

        return signature
