"""
Secure Enclave Manager for iOS Secure Enclave / Android Keystore

Production-grade secure hardware integration for:
- Key generation inside secure hardware (iOS Secure Enclave / Android Keystore)
- Signing operations requiring biometric authentication
- Key attestation support
- Hardware-backed key storage

Platform Integration:
- iOS: Secure Enclave via SecKey API with biometric protection
- Android: Android Keystore with BiometricPrompt
- Hardware-backed cryptography (keys never leave secure element)

Security Features:
- Private keys never exposed to application memory
- All cryptographic operations performed in secure hardware
- Biometric authentication required for key usage
- Key attestation for hardware verification
- Protection against rooted/jailbroken devices
"""

from __future__ import annotations

import hashlib
import logging
import secrets
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any

from xai.mobile.biometric_auth import (
    BiometricAuthProvider,
    BiometricResult,
    BiometricStrength,
    ProtectionLevel
)

logger = logging.getLogger(__name__)


class KeyProtection(Enum):
    """Key protection levels matching platform security."""
    BIOMETRIC_STRONG = "biometric_strong"      # Requires Class 3 biometric
    BIOMETRIC_ANY = "biometric_any"            # Any biometric
    DEVICE_CREDENTIAL = "device_credential"    # PIN/password
    NONE = "none"                              # No protection (not recommended)


class KeyAlgorithm(Enum):
    """Cryptographic algorithms for secure enclave keys."""
    ECDSA_SECP256K1 = "ecdsa_secp256k1"       # Bitcoin/Ethereum curve
    ECDSA_SECP256R1 = "ecdsa_secp256r1"       # NIST P-256
    RSA_2048 = "rsa_2048"
    RSA_4096 = "rsa_4096"
    ED25519 = "ed25519"                        # EdDSA


class AttestationLevel(Enum):
    """Key attestation levels."""
    HARDWARE = "hardware"                      # Hardware-backed key
    SOFTWARE = "software"                      # Software key
    TRUSTED_ENVIRONMENT = "trusted_environment"  # TEE
    SECURE_ENCLAVE = "secure_enclave"          # iOS Secure Enclave
    UNKNOWN = "unknown"


@dataclass
class SecureKey:
    """Represents a key stored in secure hardware."""
    key_id: str
    algorithm: KeyAlgorithm
    protection: KeyProtection
    public_key: bytes
    attestation_level: AttestationLevel
    created_at: int
    metadata: Dict[str, Any]


@dataclass
class SignatureResult:
    """Result of a signing operation."""
    success: bool
    signature: Optional[bytes] = None
    error_message: Optional[str] = None


@dataclass
class AttestationResult:
    """Result of key attestation verification."""
    is_valid: bool
    attestation_level: AttestationLevel
    hardware_backed: bool
    details: Dict[str, Any]


class SecureEnclaveProvider(ABC):
    """
    Abstract base class for secure enclave providers.

    Platform implementations:
    - iOS: Secure Enclave via Security framework
    - Android: Android Keystore System
    """

    @abstractmethod
    def is_available(self) -> bool:
        """Check if secure enclave is available on device."""
        pass

    @abstractmethod
    def generate_key(
        self,
        key_id: str,
        algorithm: KeyAlgorithm,
        protection: KeyProtection,
        require_biometric: bool = True
    ) -> Optional[SecureKey]:
        """
        Generate a new key in secure enclave.

        Args:
            key_id: Unique identifier for the key
            algorithm: Cryptographic algorithm
            protection: Key protection level
            require_biometric: Require biometric for key usage

        Returns:
            SecureKey if successful, None otherwise
        """
        pass

    @abstractmethod
    def get_key(self, key_id: str) -> Optional[SecureKey]:
        """Retrieve key metadata from secure enclave."""
        pass

    @abstractmethod
    def delete_key(self, key_id: str) -> bool:
        """Delete key from secure enclave."""
        pass

    @abstractmethod
    def sign_data(
        self,
        key_id: str,
        data: bytes,
        biometric_result: Optional[BiometricResult] = None
    ) -> SignatureResult:
        """
        Sign data using key in secure enclave.

        Args:
            key_id: Key identifier
            data: Data to sign
            biometric_result: Result from biometric authentication

        Returns:
            SignatureResult with signature
        """
        pass

    @abstractmethod
    def attest_key(self, key_id: str) -> AttestationResult:
        """
        Attest that key is hardware-backed.

        Returns:
            AttestationResult with attestation information
        """
        pass


class SecureEnclaveManager:
    """
    High-level manager for secure enclave operations.

    Features:
    - Simplified key generation and management
    - Automatic biometric authentication integration
    - Key lifecycle management
    - Attestation verification

    Usage:
        manager = SecureEnclaveManager(provider, biometric_provider)

        # Generate key with biometric protection
        key = manager.generate_wallet_key("wallet_1", require_biometric=True)

        # Sign transaction (triggers biometric prompt if needed)
        signature = manager.sign_with_key("wallet_1", tx_hash)
    """

    def __init__(
        self,
        enclave_provider: SecureEnclaveProvider,
        biometric_provider: Optional[BiometricAuthProvider] = None
    ):
        """
        Initialize secure enclave manager.

        Args:
            enclave_provider: Platform-specific secure enclave provider
            biometric_provider: Biometric authentication provider
        """
        self.enclave = enclave_provider
        self.biometric = biometric_provider
        self._key_cache: Dict[str, SecureKey] = {}

        if not self.enclave.is_available():
            logger.warning(
                "Secure enclave not available on this device",
                extra={"event": "secure_enclave.unavailable"}
            )

    def is_available(self) -> bool:
        """Check if secure enclave is available."""
        return self.enclave.is_available()

    def generate_wallet_key(
        self,
        wallet_id: str,
        algorithm: KeyAlgorithm = KeyAlgorithm.ECDSA_SECP256K1,
        require_biometric: bool = True,
        protection_level: KeyProtection = KeyProtection.BIOMETRIC_STRONG
    ) -> Optional[SecureKey]:
        """
        Generate a new wallet key in secure enclave.

        Args:
            wallet_id: Unique wallet identifier
            algorithm: Cryptographic algorithm (default: secp256k1 for blockchain)
            require_biometric: Require biometric for key usage
            protection_level: Key protection level

        Returns:
            SecureKey if successful, None otherwise
        """
        if not self.is_available():
            logger.error(
                "Cannot generate key: secure enclave unavailable",
                extra={"event": "secure_enclave.generate_failed"}
            )
            return None

        key_id = f"wallet_{wallet_id}"

        # Check if key already exists
        existing = self.enclave.get_key(key_id)
        if existing:
            logger.warning(
                "Key already exists for wallet",
                extra={
                    "event": "secure_enclave.key_exists",
                    "key_id": key_id
                }
            )
            return existing

        # Generate new key
        key = self.enclave.generate_key(
            key_id=key_id,
            algorithm=algorithm,
            protection=protection_level,
            require_biometric=require_biometric
        )

        if key:
            self._key_cache[key_id] = key
            logger.info(
                "Wallet key generated in secure enclave",
                extra={
                    "event": "secure_enclave.key_generated",
                    "key_id": key_id,
                    "algorithm": algorithm.value,
                    "protection": protection_level.value
                }
            )

        return key

    def get_public_key(self, wallet_id: str) -> Optional[bytes]:
        """
        Get public key for wallet.

        Args:
            wallet_id: Wallet identifier

        Returns:
            Public key bytes if exists, None otherwise
        """
        key_id = f"wallet_{wallet_id}"

        # Check cache first
        if key_id in self._key_cache:
            return self._key_cache[key_id].public_key

        # Retrieve from enclave
        key = self.enclave.get_key(key_id)
        if key:
            self._key_cache[key_id] = key
            return key.public_key

        return None

    def sign_transaction(
        self,
        wallet_id: str,
        transaction_hash: bytes,
        prompt_message: str = "Sign transaction"
    ) -> Optional[bytes]:
        """
        Sign transaction hash using wallet key.

        This method will trigger biometric authentication if required.

        Args:
            wallet_id: Wallet identifier
            transaction_hash: Transaction hash to sign
            prompt_message: Message for biometric prompt

        Returns:
            Signature bytes if successful, None otherwise
        """
        key_id = f"wallet_{wallet_id}"

        # Get key info
        key = self.enclave.get_key(key_id)
        if not key:
            logger.error(
                "Key not found for wallet",
                extra={
                    "event": "secure_enclave.key_not_found",
                    "wallet_id": wallet_id
                }
            )
            return None

        # Authenticate if biometric provider available
        biometric_result = None
        if self.biometric and key.protection != KeyProtection.NONE:
            protection_level = self._key_protection_to_biometric(key.protection)
            biometric_result = self.biometric.authenticate(
                prompt_message=prompt_message,
                protection_level=protection_level
            )

            if not biometric_result.success:
                logger.warning(
                    "Biometric authentication failed for signing",
                    extra={
                        "event": "secure_enclave.auth_failed",
                        "error": biometric_result.error_code.value if biometric_result.error_code else "unknown"
                    }
                )
                return None

        # Sign data
        result = self.enclave.sign_data(
            key_id=key_id,
            data=transaction_hash,
            biometric_result=biometric_result
        )

        if result.success:
            logger.info(
                "Transaction signed successfully",
                extra={
                    "event": "secure_enclave.sign_success",
                    "wallet_id": wallet_id
                }
            )
            return result.signature
        else:
            logger.error(
                "Signing failed",
                extra={
                    "event": "secure_enclave.sign_failed",
                    "error": result.error_message
                }
            )
            return None

    def _key_protection_to_biometric(self, protection: KeyProtection) -> ProtectionLevel:
        """Map key protection to biometric protection level."""
        mapping = {
            KeyProtection.BIOMETRIC_STRONG: ProtectionLevel.BIOMETRIC_STRONG,
            KeyProtection.BIOMETRIC_ANY: ProtectionLevel.BIOMETRIC_WEAK,
            KeyProtection.DEVICE_CREDENTIAL: ProtectionLevel.DEVICE_CREDENTIAL,
            KeyProtection.NONE: ProtectionLevel.BIOMETRIC_OR_CREDENTIAL
        }
        return mapping.get(protection, ProtectionLevel.BIOMETRIC_STRONG)

    def verify_key_attestation(self, wallet_id: str) -> AttestationResult:
        """
        Verify that wallet key is hardware-backed.

        Args:
            wallet_id: Wallet identifier

        Returns:
            AttestationResult with verification information
        """
        key_id = f"wallet_{wallet_id}"
        return self.enclave.attest_key(key_id)

    def delete_wallet_key(self, wallet_id: str) -> bool:
        """
        Delete wallet key from secure enclave.

        Args:
            wallet_id: Wallet identifier

        Returns:
            True if successful
        """
        key_id = f"wallet_{wallet_id}"

        # Remove from cache
        self._key_cache.pop(key_id, None)

        # Delete from enclave
        success = self.enclave.delete_key(key_id)

        if success:
            logger.info(
                "Wallet key deleted",
                extra={
                    "event": "secure_enclave.key_deleted",
                    "wallet_id": wallet_id
                }
            )

        return success

    def get_key_info(self, wallet_id: str) -> Optional[SecureKey]:
        """Get key metadata for wallet."""
        key_id = f"wallet_{wallet_id}"

        if key_id in self._key_cache:
            return self._key_cache[key_id]

        key = self.enclave.get_key(key_id)
        if key:
            self._key_cache[key_id] = key

        return key


class MockSecureEnclaveProvider(SecureEnclaveProvider):
    """
    Mock implementation for testing.

    DO NOT USE IN PRODUCTION.
    Simulates secure enclave behavior for development and testing.
    """

    def __init__(self):
        self._keys: Dict[str, SecureKey] = {}
        self._is_available = True

    def is_available(self) -> bool:
        """Check mock enclave availability."""
        return self._is_available

    def generate_key(
        self,
        key_id: str,
        algorithm: KeyAlgorithm,
        protection: KeyProtection,
        require_biometric: bool = True
    ) -> Optional[SecureKey]:
        """Generate mock key."""
        if key_id in self._keys:
            return None

        # Generate mock key pair (simplified - not real crypto)
        private_key = secrets.token_bytes(32)
        public_key = hashlib.sha256(private_key).digest()

        key = SecureKey(
            key_id=key_id,
            algorithm=algorithm,
            protection=protection,
            public_key=public_key,
            attestation_level=AttestationLevel.HARDWARE,
            created_at=int(time.time()),
            metadata={"require_biometric": require_biometric}
        )

        self._keys[key_id] = key

        # Store private key internally (in real implementation, this never leaves hardware)
        self._keys[f"{key_id}_private"] = private_key

        return key

    def get_key(self, key_id: str) -> Optional[SecureKey]:
        """Get mock key."""
        return self._keys.get(key_id)

    def delete_key(self, key_id: str) -> bool:
        """Delete mock key."""
        if key_id in self._keys:
            del self._keys[key_id]
            self._keys.pop(f"{key_id}_private", None)
            return True
        return False

    def sign_data(
        self,
        key_id: str,
        data: bytes,
        biometric_result: Optional[BiometricResult] = None
    ) -> SignatureResult:
        """Sign data with mock key."""
        key = self._keys.get(key_id)
        if not key:
            return SignatureResult(
                success=False,
                error_message="Key not found"
            )

        # Check biometric requirement
        if key.metadata.get("require_biometric") and not biometric_result:
            return SignatureResult(
                success=False,
                error_message="Biometric authentication required"
            )

        # Mock signing (not real signature)
        private_key = self._keys.get(f"{key_id}_private")
        signature = hashlib.sha256(private_key + data).digest()

        return SignatureResult(
            success=True,
            signature=signature
        )

    def attest_key(self, key_id: str) -> AttestationResult:
        """Mock attestation."""
        key = self._keys.get(key_id)
        if not key:
            return AttestationResult(
                is_valid=False,
                attestation_level=AttestationLevel.UNKNOWN,
                hardware_backed=False,
                details={"error": "Key not found"}
            )

        return AttestationResult(
            is_valid=True,
            attestation_level=AttestationLevel.HARDWARE,
            hardware_backed=True,
            details={
                "algorithm": key.algorithm.value,
                "protection": key.protection.value,
                "created_at": key.created_at
            }
        )

    # Mock-specific methods for testing
    def set_available(self, available: bool):
        """Set mock enclave availability."""
        self._is_available = available
