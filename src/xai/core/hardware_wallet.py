from __future__ import annotations

"""
Hardware wallet integration for XAI blockchain.

Provides:
- Protocol interface for hardware wallet implementations
- MockHardwareWallet for testing with proper ECDSA signatures
- HardwareWalletManager for device coordination

Supported devices (via separate modules):
- Ledger: hardware_wallet_ledger.py
- Trezor: (planned)

Security Note:
    MockHardwareWallet is for TESTING ONLY. It stores private keys in memory
    which defeats the purpose of hardware wallets. Never use in production.
"""

import hashlib
import logging
import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature

from xai.core.crypto_utils import canonicalize_signature_components

if TYPE_CHECKING:  # pragma: no cover - type checking only
    from xai.core.hardware_wallet_ledger import LedgerHardwareWallet  # noqa: F401
    from xai.core.hardware_wallet_trezor import TrezorHardwareWallet  # noqa: F401

logger = logging.getLogger(__name__)

HARDWARE_WALLET_ENABLED = os.getenv("XAI_HARDWARE_WALLET_ENABLED", "false").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
DEFAULT_HARDWARE_WALLET_NAME = os.getenv("XAI_HARDWARE_WALLET_PROVIDER", "mock")
LEDGER_BIP32_PATH = os.getenv("XAI_LEDGER_BIP32_PATH", "m/44'/22593'/0'/0/0")
TREZOR_BIP32_PATH = os.getenv("XAI_TREZOR_BIP32_PATH", LEDGER_BIP32_PATH)
ALLOW_MOCK_HARDWARE_WALLET = os.getenv("XAI_ALLOW_MOCK_HARDWARE_WALLET", "false").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}

# Curve constants for SECP256K1
_CURVE = ec.SECP256K1()
_CURVE_ORDER = int("FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141", 16)

def _normalize_private_value(value: int) -> int:
    """Normalize private key value to valid range."""
    normalized = value % _CURVE_ORDER
    if normalized == 0:
        normalized = 1
    return normalized

@runtime_checkable
class HardwareWallet(Protocol):
    """
    Protocol interface for hardware wallet implementations.

    All hardware wallet adapters must implement this interface to be
    compatible with the XAI wallet system.

    Security Requirements:
    - Private keys MUST never leave the hardware device
    - All signing operations MUST occur on the device
    - Communication channels SHOULD be encrypted
    """

    def connect(self) -> bool:
        """
        Establish a secure channel to the hardware device.

        Returns:
            True if connection successful, False otherwise

        Raises:
            RuntimeError: If device not found or communication failed
        """
        ...

    def get_address(self) -> str:
        """
        Derive and return an XAI address from the hardware wallet.

        The address is derived on-device from the wallet's master key
        using the XAI derivation path.

        Returns:
            XAI address string (format: XAI + 40 hex chars)
        """
        ...

    def sign_transaction(self, payload: bytes) -> bytes:
        """
        Sign transaction payload on the hardware device.

        The private key never leaves the device. The payload is sent
        to the device, signed internally, and only the signature is returned.

        Args:
            payload: Raw transaction bytes to sign

        Returns:
            ECDSA signature as bytes (64 bytes: r || s format)

        Raises:
            RuntimeError: If signing fails or user rejects on device
        """
        ...

    def get_public_key(self) -> str:
        """
        Get the public key from the hardware wallet.

        Returns:
            Public key as hex string (64 bytes uncompressed, no prefix)
        """
        ...

@dataclass
class MockHardwareWallet:
    """
    Mock hardware wallet for TESTING ONLY.

    WARNING: This implementation stores private keys in memory, which
    completely defeats the security purpose of hardware wallets.
    NEVER use this in production environments.

    This mock produces valid ECDSA signatures that can be verified
    by the standard verification functions, making it suitable for
    integration testing.

    Attributes:
        address: Pre-configured XAI address (for testing)
        _private_key: Internal ECDSA private key (TESTING ONLY)
        _public_key: Corresponding public key
    """

    address: str = ""
    _private_key: ec.EllipticCurvePrivateKey | None = field(default=None, repr=False)
    _public_key: ec.EllipticCurvePublicKey | None = field(default=None, repr=False)
    _public_key_hex: str = field(default="", repr=False)

    def __post_init__(self):
        """Generate deterministic keys for testing."""
        if self._private_key is None:
            # Generate deterministic key from seed for reproducible tests
            seed = hashlib.sha256(b"XAI_MOCK_HARDWARE_WALLET_SEED_V1").digest()
            private_value = _normalize_private_value(int.from_bytes(seed, "big"))
            self._private_key = ec.derive_private_key(private_value, _CURVE)
            self._public_key = self._private_key.public_key()

            # Generate public key hex (uncompressed, no prefix)
            numbers = self._public_key.public_numbers()
            self._public_key_hex = (
                numbers.x.to_bytes(32, "big") + numbers.y.to_bytes(32, "big")
            ).hex()

            # Generate address if not provided
            if not self.address:
                # Use network-appropriate prefix
                from xai.core.config import NETWORK
                prefix = "XAI" if NETWORK.lower() == "mainnet" else "TXAI"
                pub_key_bytes = bytes.fromhex(self._public_key_hex)
                pub_hash = hashlib.sha256(pub_key_bytes).hexdigest()
                self.address = f"{prefix}{pub_hash[:40]}"

        logger.warning(
            "MockHardwareWallet initialized - FOR TESTING ONLY",
            extra={"event": "hw_mock.init", "address": self.address[:16] + "..."}
        )

    def connect(self) -> bool:
        """
        Simulate hardware wallet connection.

        Returns:
            Always True for mock
        """
        logger.debug(
            "Mock hardware wallet connected",
            extra={"event": "hw_mock.connect"}
        )
        return True

    def get_address(self) -> str:
        """
        Return the mock wallet address.

        Returns:
            XAI address string
        """
        return self.address

    def get_public_key(self) -> str:
        """
        Return the mock wallet's public key.

        Returns:
            Public key as hex string (64 bytes)
        """
        return self._public_key_hex

    def sign_transaction(self, payload: bytes) -> bytes:
        """
        Sign payload with proper ECDSA signature.

        This produces a valid secp256k1 ECDSA signature that can be
        verified by verify_signature_hex() in crypto_utils.

        Args:
            payload: Transaction bytes to sign

        Returns:
            64-byte signature in r || s format
        """
        # Sign with SHA256 hash (matches crypto_utils.sign_message_hex)
        der_signature = self._private_key.sign(payload, ec.ECDSA(hashes.SHA256()))

        # Convert DER to raw r || s format (64 bytes)
        r, s = decode_dss_signature(der_signature)
        r, s = canonicalize_signature_components(r, s)
        signature = r.to_bytes(32, "big") + s.to_bytes(32, "big")

        logger.debug(
            "Mock hardware wallet signed transaction",
            extra={
                "event": "hw_mock.sign",
                "payload_size": len(payload),
                "signature_size": len(signature)
            }
        )

        return signature

class HardwareWalletManager:
    """Helper to coordinate hardware wallet sessions."""

    def __init__(self):
        # Replace this dictionary with device discovery results in future.
        self.connected_devices: dict[str, HardwareWallet] = {}

        # Register mock provider only when explicitly allowed; production defaults to real devices.
        if ALLOW_MOCK_HARDWARE_WALLET:
            self.register_device("mock", MockHardwareWallet())

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
    if not HARDWARE_WALLET_ENABLED:
        return None
    provider = DEFAULT_HARDWARE_WALLET_NAME.lower()
    if provider == "mock" and not ALLOW_MOCK_HARDWARE_WALLET:
        raise ValueError(
            "MockHardwareWallet is disabled for production. "
            "Set XAI_ALLOW_MOCK_HARDWARE_WALLET=1 only in test environments."
        )
    if provider == "ledger":
        wallet = manager.get_device("ledger")
        if wallet is None:
            try:
                from xai.core.hardware_wallet_ledger import LedgerHardwareWallet
            except ImportError as exc:  # pragma: no cover - optional dependency
                raise ImportError("Ledger support requires ledgerblue. pip install ledgerblue") from exc
            manager.register_device("ledger", LedgerHardwareWallet(bip32_path=LEDGER_BIP32_PATH))
        return manager.get_device("ledger")
    if provider == "trezor":
        wallet = manager.get_device("trezor")
        if wallet is None:
            try:
                from xai.core.hardware_wallet_trezor import TrezorHardwareWallet
            except ImportError as exc:  # pragma: no cover - optional dependency
                raise ImportError("Trezor support requires trezorlib. pip install trezor") from exc
            manager.register_device("trezor", TrezorHardwareWallet(bip32_path=TREZOR_BIP32_PATH))
        return manager.get_device("trezor")
    return manager.get_device(DEFAULT_HARDWARE_WALLET_NAME)
