"""
Trezor hardware wallet integration for XAI.

Implements read-only public key retrieval and on-device signing via trezorlib.
Never stores private keys in memory. This is a minimal bridge to support send/
sign flows in the CLI while maintaining production safety.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

try:
    from trezorlib.client import TrezorClient
    from trezorlib.transport import enumerate_devices
    from trezorlib import ethereum
except ImportError as exc:  # pragma: no cover - optional dependency
    raise ImportError("trezorlib is required for Trezor support. pip install trezor") from exc

from xai.core.hardware_wallet import HardwareWallet, LEDGER_BIP32_PATH


@dataclass
class TrezorHardwareWallet(HardwareWallet):
    bip32_path: str = LEDGER_BIP32_PATH.replace("44'/22593'", "44'/22593'")
    _client: Optional[TrezorClient] = None

    def connect(self) -> bool:
        devices = enumerate_devices()
        if not devices:
            raise ConnectionError("No Trezor device found.")
        self._client = TrezorClient(devices[0])
        return True

    def _require_client(self) -> TrezorClient:
        if not self._client:
            self.connect()
        return self._client

    def get_public_key(self) -> str:
        client = self._require_client()
        node = ethereum.get_public_node(client, self.bip32_path)
        return node.node.public_key.hex()

    def sign_message(self, message: bytes) -> bytes:
        client = self._require_client()
        sig = ethereum.sign_message(client, self.bip32_path, message)
        return bytes(sig.signature)

    def sign_transaction(self, tx_dict: dict) -> str:
        client = self._require_client()
        # Trezor expects Ethereum-style fields; adapt XAI tx dict accordingly if needed
        tx = ethereum.sign_tx(
            client,
            path=self.bip32_path,
            nonce=tx_dict["nonce"],
            gas_price=tx_dict["gasPrice"],
            gas_limit=tx_dict["gas"],
            to=tx_dict["to"],
            value=tx_dict["value"],
            data=bytes.fromhex(tx_dict.get("data", "")),
            chain_id=tx_dict.get("chainId", 1),
        )
        return tx[1].hex()  # signed raw tx

    def get_address(self) -> str:
        client = self._require_client()
        address = ethereum.get_address(client, self.bip32_path)
        return address
