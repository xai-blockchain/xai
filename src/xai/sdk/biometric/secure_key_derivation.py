from __future__ import annotations

"""
Secure Key Derivation for Biometric-Protected Wallet Keys

This module provides cryptographic key derivation that combines:
1. Biometric authentication (platform-specific)
2. Device-specific identifiers
3. User-provided secrets (optional)

The derived keys are used to encrypt wallet private keys at rest,
ensuring they can only be decrypted on the same device after
successful biometric authentication.
"""

import hashlib
import hmac
import os
import secrets
from dataclasses import dataclass

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

@dataclass
class DerivedKey:
    """Container for a derived encryption key."""
    key: bytes
    salt: bytes
    iterations: int
    algorithm: str

@dataclass
class EncryptedWalletKey:
    """Encrypted wallet private key with metadata."""
    ciphertext: bytes
    iv: bytes
    salt: bytes
    iterations: int
    device_id_hash: bytes  # Hash of device ID used
    algorithm: str = "AES-256-GCM"

class SecureKeyDerivation:
    """
    Derives encryption keys from biometric authentication and device identifiers.

    Security properties:
    - Keys are device-specific (cannot be transferred)
    - Keys require biometric authentication (platform enforced)
    - Keys use strong KDF (PBKDF2 with high iteration count)
    - Keys are never stored in plaintext
    """

    DEFAULT_ITERATIONS = 600_000  # OWASP 2023 recommendation for PBKDF2-SHA256
    KEY_LENGTH = 32  # 256 bits for AES-256

    def __init__(self, device_id: str):
        """
        Initialize key derivation with device identifier.

        Args:
            device_id: Unique device identifier
                       iOS: UIDevice.identifierForVendor
                       Android: Settings.Secure.ANDROID_ID
        """
        if not device_id:
            raise ValueError("Device ID cannot be empty")

        self.device_id = device_id
        self.device_id_hash = self._hash_device_id(device_id)

    def _hash_device_id(self, device_id: str) -> bytes:
        """Create a deterministic hash of the device ID."""
        return hashlib.sha256(device_id.encode('utf-8')).digest()

    def derive_key(
        self,
        biometric_token: bytes,
        salt: bytes | None = None,
        iterations: int | None = None,
        additional_context: str | None = None
    ) -> DerivedKey:
        """
        Derive an encryption key from biometric token and device ID.

        Args:
            biometric_token: Platform-specific biometric authentication token
                            iOS: LAContext.evaluatedPolicyDomainState
                            Android: BiometricPrompt.CryptoObject signature
            salt: Random salt (generated if not provided)
            iterations: PBKDF2 iterations (uses default if not provided)
            additional_context: Optional context string (e.g., wallet ID)

        Returns:
            DerivedKey containing the key material and parameters

        Security notes:
            - The biometric_token should be obtained ONLY after successful
              biometric authentication
            - Salt should be unique per wallet and stored alongside encrypted data
            - Iterations should be tuned for device performance (min 100k)
        """
        if not biometric_token:
            raise ValueError("Biometric token cannot be empty")

        # Generate or validate salt
        if salt is None:
            salt = secrets.token_bytes(32)
        elif len(salt) < 16:
            raise ValueError("Salt must be at least 16 bytes")

        # Use default or provided iterations
        iterations = iterations or self.DEFAULT_ITERATIONS
        if iterations < 100_000:
            raise ValueError("Iterations must be at least 100,000")

        # Combine inputs for key derivation
        # Format: biometric_token || device_id || context
        key_material = biometric_token + self.device_id_hash

        if additional_context:
            context_hash = hashlib.sha256(additional_context.encode('utf-8')).digest()
            key_material += context_hash

        # Derive key using PBKDF2-HMAC-SHA256
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=self.KEY_LENGTH,
            salt=salt,
            iterations=iterations,
        )
        derived_key = kdf.derive(key_material)

        return DerivedKey(
            key=derived_key,
            salt=salt,
            iterations=iterations,
            algorithm="PBKDF2-HMAC-SHA256"
        )

    def encrypt_wallet_key(
        self,
        wallet_private_key: bytes,
        biometric_token: bytes,
        wallet_id: str | None = None,
        iterations: int | None = None
    ) -> EncryptedWalletKey:
        """
        Encrypt a wallet private key using biometric-derived key.

        Args:
            wallet_private_key: The private key to encrypt
            biometric_token: Token from successful biometric auth
            wallet_id: Optional wallet identifier for key derivation context
            iterations: PBKDF2 iterations

        Returns:
            EncryptedWalletKey with all necessary data for decryption

        Usage:
            # After successful biometric authentication:
            encrypted = kdf.encrypt_wallet_key(
                wallet_private_key=private_key_bytes,
                biometric_token=auth_token,
                wallet_id="0x1234..."
            )
            # Store encrypted.ciphertext, encrypted.iv, encrypted.salt
        """
        # Derive encryption key
        derived = self.derive_key(
            biometric_token=biometric_token,
            additional_context=wallet_id,
            iterations=iterations
        )

        # Generate random IV for AES-GCM
        iv = secrets.token_bytes(12)  # 96-bit IV for GCM

        # Encrypt using AES-256-GCM
        aesgcm = AESGCM(derived.key)
        ciphertext = aesgcm.encrypt(iv, wallet_private_key, None)

        return EncryptedWalletKey(
            ciphertext=ciphertext,
            iv=iv,
            salt=derived.salt,
            iterations=derived.iterations,
            device_id_hash=self.device_id_hash,
            algorithm="AES-256-GCM"
        )

    def decrypt_wallet_key(
        self,
        encrypted: EncryptedWalletKey,
        biometric_token: bytes,
        wallet_id: str | None = None
    ) -> bytes:
        """
        Decrypt a wallet private key using biometric-derived key.

        Args:
            encrypted: EncryptedWalletKey from encrypt_wallet_key()
            biometric_token: Token from successful biometric auth
            wallet_id: Wallet identifier (must match encryption)

        Returns:
            Decrypted wallet private key

        Raises:
            ValueError: If device ID doesn't match or decryption fails

        Security notes:
            - Only call after successful biometric authentication
            - Decryption will fail if biometric token is incorrect
            - Decryption will fail if device ID doesn't match
        """
        # Verify device ID matches
        if not hmac.compare_digest(encrypted.device_id_hash, self.device_id_hash):
            raise ValueError("Device ID mismatch - key cannot be decrypted on this device")

        # Derive decryption key (must match encryption parameters)
        derived = self.derive_key(
            biometric_token=biometric_token,
            salt=encrypted.salt,
            iterations=encrypted.iterations,
            additional_context=wallet_id
        )

        # Decrypt using AES-256-GCM
        aesgcm = AESGCM(derived.key)
        try:
            plaintext = aesgcm.decrypt(encrypted.iv, encrypted.ciphertext, None)
            return plaintext
        except Exception as e:
            raise ValueError(f"Decryption failed: {e}")

    @staticmethod
    def generate_biometric_token_mock() -> bytes:
        """
        Generate a mock biometric token for testing.

        WARNING: This should NEVER be used in production!
        In production, the biometric token MUST come from the platform's
        biometric authentication APIs after successful authentication.

        Returns:
            Random 32-byte token
        """
        return secrets.token_bytes(32)

    def verify_device_binding(self, encrypted: EncryptedWalletKey) -> bool:
        """
        Verify that encrypted data is bound to this device.

        Args:
            encrypted: EncryptedWalletKey to verify

        Returns:
            True if data can be decrypted on this device
        """
        return hmac.compare_digest(encrypted.device_id_hash, self.device_id_hash)

class BiometricTokenCache:
    """
    Secure in-memory cache for biometric tokens.

    This cache allows avoiding repeated biometric prompts within a short
    time window while maintaining security.

    IMPORTANT: This is for reference only. Mobile implementations should use
    platform-specific secure storage (iOS Keychain, Android KeyStore).
    """

    def __init__(self, validity_seconds: int = 60):
        """
        Initialize token cache.

        Args:
            validity_seconds: How long tokens remain valid
        """
        self.validity_seconds = validity_seconds
        self._cache: dict[str, tuple[bytes, float]] = {}

    def store(self, key: str, token: bytes) -> None:
        """Store a biometric token with timestamp."""
        import time
        self._cache[key] = (token, time.time())

    def retrieve(self, key: str) -> bytes | None:
        """
        Retrieve a cached token if still valid.

        Returns:
            Token if valid, None otherwise
        """
        import time
        if key not in self._cache:
            return None

        token, timestamp = self._cache[key]
        if time.time() - timestamp > self.validity_seconds:
            del self._cache[key]
            return None

        return token

    def invalidate(self, key: str | None = None) -> None:
        """Invalidate cached tokens."""
        if key:
            self._cache.pop(key, None)
        else:
            self._cache.clear()
