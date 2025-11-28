"""
Hardware wallet integration stubs and guidance.

Add concrete implementations on top of this base once the supported device list is finalized.
"""

from dataclasses import dataclass
import hashlib
import os
from typing import Protocol, runtime_checkable, Dict


HARDWARE_WALLET_ENABLED = os.getenv("XAI_HARDWARE_WALLET_ENABLED", "false").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
DEFAULT_HARDWARE_WALLET_NAME = os.getenv("XAI_HARDWARE_WALLET_PROVIDER", "mock")


@runtime_checkable
class HardwareWallet(Protocol):
    """Minimal interface expected from a hardware wallet provider."""

    def connect(self) -> bool:
        """Establish a secure channel to the device."""

    def get_address(self) -> str:
        """Derive the next available XAI address."""

    def sign_transaction(self, payload: bytes) -> bytes:
        """Sign raw transaction payload without exposing private keys."""


@dataclass
class MockHardwareWallet:
    """Simple mock provider we can expand when real devices are registered."""

    address: str = "XAI" + "0" * 40

    def connect(self) -> bool:
        """Always succeed when mocking hardware wallet connections."""
        return True

    def get_address(self) -> str:
        """Return the preconfigured mock address."""
        return self.address

    def sign_transaction(self, payload: bytes) -> bytes:
        """Return deterministic data so tests can verify signatures."""
        digest = hashlib.sha256(payload + self.address.encode()).digest()
        return digest


class HardwareWalletManager:
    """Helper to coordinate hardware wallet sessions."""

    def __init__(self):
        # Replace this dictionary with device discovery results in future.
        self.connected_devices: Dict[str, HardwareWallet] = {}

        # Register default mock provider so the manager can always work during testing.
        self.register_device(DEFAULT_HARDWARE_WALLET_NAME, MockHardwareWallet())

    def register_device(self, name: str, wallet: HardwareWallet):
        self.connected_devices[name] = wallet

    def get_device(self, name: str) -> HardwareWallet | None:
        return self.connected_devices.get(name)

    def list_devices(self) -> list[str]:
        return list(self.connected_devices.keys())


_global_hw_manager: HardwareWalletManager | None = None


def get_hardware_wallet_manager() -> HardwareWalletManager:
    global _global_hw_manager
    if _global_hw_manager is None:
        _global_hw_manager = HardwareWalletManager()
    return _global_hw_manager


def get_default_hardware_wallet() -> HardwareWallet | None:
    manager = get_hardware_wallet_manager()
    return manager.get_device(DEFAULT_HARDWARE_WALLET_NAME) if HARDWARE_WALLET_ENABLED else None
