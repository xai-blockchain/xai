"""
Hardware wallet integration stubs and guidance.

Add concrete implementations on top of this base once the supported device list is finalized.
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class HardwareWallet(Protocol):
    """Minimal interface expected from a hardware wallet provider."""

    def connect(self) -> bool:
        """Establish a secure channel to the device."""

    def get_address(self) -> str:
        """Derive the next available XAI address."""

    def sign_transaction(self, payload: bytes) -> bytes:
        """Sign raw transaction payload without exposing private keys."""


class HardwareWalletManager:
    """Helper to coordinate hardware wallet sessions."""

    def __init__(self):
        # Replace this dictionary with device discovery results in future.
        self.connected_devices: dict[str, HardwareWallet] = {}

    def register_device(self, name: str, wallet: HardwareWallet):
        self.connected_devices[name] = wallet

    def get_device(self, name: str) -> HardwareWallet | None:
        return self.connected_devices.get(name)

    def list_devices(self) -> list[str]:
        return list(self.connected_devices.keys())
