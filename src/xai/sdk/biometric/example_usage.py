from __future__ import annotations

"""
Example Usage of XAI Biometric Authentication Framework

This file demonstrates how to integrate biometric authentication
into a mobile wallet application.
"""

import asyncio
import json

from xai.sdk.biometric.biometric_auth import (
    BiometricAuthProvider,
    BiometricError,
    BiometricType,
    MockBiometricProvider,
)
from xai.sdk.biometric.secure_key_derivation import (
    BiometricTokenCache,
    EncryptedWalletKey,
    SecureKeyDerivation,
)


class WalletSecurityManager:
    """
    Example wallet security manager using biometric authentication.

    This class demonstrates the complete flow of:
    1. Setting up biometric authentication
    2. Encrypting wallet private keys
    3. Authenticating for transactions
    4. Decrypting keys for signing
    """

    def __init__(
        self,
        device_id: str,
        biometric_provider: BiometricAuthProvider,
    ):
        """
        Initialize wallet security manager.

        Args:
            device_id: Unique device identifier
            biometric_provider: Platform-specific biometric provider
        """
        self.device_id = device_id
        self.biometric_provider = biometric_provider
        self.key_derivation = SecureKeyDerivation(device_id)
        self.token_cache = BiometricTokenCache(validity_seconds=60)

    def setup_wallet_security(self, wallet_id: str, private_key: bytes) -> dict | None:
        """
        Set up biometric security for a wallet.

        Args:
            wallet_id: Wallet identifier/address
            private_key: Wallet private key to protect

        Returns:
            Encrypted wallet data to store, or None if setup failed
        """
        print(f"Setting up biometric security for wallet {wallet_id}")

        # Check if biometrics are available
        capability = self.biometric_provider.is_available()
        if not capability.available:
            print("❌ Biometric authentication not available on this device")
            if not capability.hardware_detected:
                print("   No biometric hardware detected")
            elif not capability.enrolled:
                print("   No biometrics enrolled - please enroll in device settings")
            return None

        print(f"✓ Biometric authentication available: {capability.biometric_types[0].value}")
        print(f"  Security level: {capability.security_level}")

        # Authenticate user
        auth_result = self.biometric_provider.authenticate(
            prompt_message=f"Secure wallet {wallet_id[:10]}...",
            cancel_button_text="Cancel",
            fallback_to_passcode=False,
        )

        if not auth_result.success:
            print(f"❌ Authentication failed: {auth_result.error_message}")
            return None

        print(f"✓ Authenticated with {auth_result.auth_type.value}")

        # Get biometric token (platform-specific)
        # In production, this comes from the authentication result
        biometric_token = self._get_biometric_token(auth_result)

        # Cache token for short-term use
        self.token_cache.store(wallet_id, biometric_token)

        # Encrypt wallet private key
        encrypted = self.key_derivation.encrypt_wallet_key(
            wallet_private_key=private_key,
            biometric_token=biometric_token,
            wallet_id=wallet_id,
        )

        print(f"✓ Wallet key encrypted")
        print(f"  Salt: {encrypted.salt.hex()[:16]}...")
        print(f"  Iterations: {encrypted.iterations:,}")
        print(f"  Algorithm: {encrypted.algorithm}")

        # Return encrypted data for storage
        return self._serialize_encrypted_key(encrypted)

    def unlock_wallet_for_transaction(
        self,
        wallet_id: str,
        encrypted_data: dict,
        transaction_details: str | None = None,
    ) -> bytes | None:
        """
        Unlock wallet to sign a transaction.

        Args:
            wallet_id: Wallet identifier
            encrypted_data: Encrypted wallet key data
            transaction_details: Optional transaction details to show user

        Returns:
            Decrypted private key, or None if authentication failed
        """
        prompt = f"Sign transaction for {wallet_id[:10]}..."
        if transaction_details:
            prompt = f"Sign transaction\n{transaction_details}"

        print(f"\n🔒 Requesting biometric authentication...")

        # Check cache first to avoid repeated prompts
        cached_token = self.token_cache.retrieve(wallet_id)
        if cached_token:
            print("✓ Using cached authentication token")
            biometric_token = cached_token
        else:
            # Authenticate user
            auth_result = self.biometric_provider.authenticate(
                prompt_message=prompt,
                cancel_button_text="Cancel",
                fallback_to_passcode=True,
            )

            if not auth_result.success:
                print(f"❌ Authentication failed: {auth_result.error_message}")
                self._handle_auth_error(auth_result.error_code)
                return None

            print(f"✓ Authenticated with {auth_result.auth_type.value}")

            # Get biometric token
            biometric_token = self._get_biometric_token(auth_result)

            # Cache for subsequent operations
            self.token_cache.store(wallet_id, biometric_token)

        # Deserialize encrypted data
        encrypted = self._deserialize_encrypted_key(encrypted_data)

        # Verify device binding
        if not self.key_derivation.verify_device_binding(encrypted):
            print("❌ Device mismatch - wallet cannot be unlocked on this device")
            print("   Please use account recovery")
            return None

        # Decrypt wallet private key
        try:
            private_key = self.key_derivation.decrypt_wallet_key(
                encrypted=encrypted,
                biometric_token=biometric_token,
                wallet_id=wallet_id,
            )
            print("✓ Wallet unlocked")
            return private_key
        except ValueError as e:
            print(f"❌ Decryption failed: {e}")
            print("   Biometric authentication may have changed")
            return None

    def invalidate_authentication(self, wallet_id: str | None = None):
        """
        Invalidate cached authentication tokens.

        Args:
            wallet_id: Specific wallet to invalidate, or None for all
        """
        self.token_cache.invalidate(wallet_id)
        self.biometric_provider.invalidate_authentication()
        print("✓ Authentication invalidated")

    def _get_biometric_token(self, auth_result) -> bytes:
        """
        Extract biometric token from authentication result.

        In production, this should be implemented platform-specifically:
        - iOS: LAContext.evaluatedPolicyDomainState
        - Android: BiometricPrompt.CryptoObject signature
        """
        # Mock implementation for testing
        return SecureKeyDerivation.generate_biometric_token_mock()

    def _handle_auth_error(self, error_code: BiometricError | None):
        """Handle authentication errors with appropriate user feedback."""
        if error_code == BiometricError.USER_CANCEL:
            print("   User cancelled authentication")
        elif error_code == BiometricError.LOCKOUT:
            print("   Too many failed attempts - device is locked")
            print("   Please try again later or use passcode")
        elif error_code == BiometricError.NOT_ENROLLED:
            print("   No biometrics enrolled")
            print("   Please enroll in device settings")
        elif error_code == BiometricError.HARDWARE_ERROR:
            print("   Hardware error - biometric sensor unavailable")

    def _serialize_encrypted_key(self, encrypted: EncryptedWalletKey) -> dict:
        """Serialize encrypted key for storage."""
        return {
            "ciphertext": encrypted.ciphertext.hex(),
            "iv": encrypted.iv.hex(),
            "salt": encrypted.salt.hex(),
            "iterations": encrypted.iterations,
            "device_id_hash": encrypted.device_id_hash.hex(),
            "algorithm": encrypted.algorithm,
        }

    def _deserialize_encrypted_key(self, data: dict) -> EncryptedWalletKey:
        """Deserialize encrypted key from storage."""
        return EncryptedWalletKey(
            ciphertext=bytes.fromhex(data["ciphertext"]),
            iv=bytes.fromhex(data["iv"]),
            salt=bytes.fromhex(data["salt"]),
            iterations=data["iterations"],
            device_id_hash=bytes.fromhex(data["device_id_hash"]),
            algorithm=data["algorithm"],
        )

def demo_wallet_flow():
    """Demonstrate complete wallet security flow."""
    print("=" * 70)
    print("XAI Biometric Wallet Security Demo")
    print("=" * 70)

    # Setup
    device_id = "mock-device-12345"
    wallet_id = "0x1234567890abcdef"
    private_key = b"mock_private_key_32_bytes_long!!"

    # Use mock provider for demo (replace with platform provider in production)
    biometric_provider = MockBiometricProvider(
        simulate_type=BiometricType.FACE_ID
    )

    manager = WalletSecurityManager(device_id, biometric_provider)

    # Step 1: Setup wallet security
    print("\n📱 Step 1: Setup Wallet Security")
    print("-" * 70)
    encrypted_data = manager.setup_wallet_security(wallet_id, private_key)

    if not encrypted_data:
        print("\n❌ Setup failed")
        return

    # Simulate storing encrypted data
    print("\n💾 Storing encrypted wallet data...")
    stored_json = json.dumps(encrypted_data, indent=2)
    print(f"   Data size: {len(stored_json)} bytes")

    # Step 2: Sign transaction
    print("\n📝 Step 2: Sign Transaction")
    print("-" * 70)
    transaction_details = "Send 10 XAI to 0xabcd..."

    decrypted_key = manager.unlock_wallet_for_transaction(
        wallet_id=wallet_id,
        encrypted_data=encrypted_data,
        transaction_details=transaction_details,
    )

    if decrypted_key:
        print("\n✓ Transaction can be signed")
        print("  (Private key would be used here, then cleared from memory)")

        # In production: sign transaction, then clear key
        # signature = sign_transaction(decrypted_key, transaction)
        # del decrypted_key  # Clear from memory immediately
    else:
        print("\n❌ Cannot sign transaction")

    # Step 3: Multiple transactions (uses cached token)
    print("\n📝 Step 3: Sign Another Transaction (Cached Auth)")
    print("-" * 70)
    transaction_details = "Send 5 XAI to 0xdcba..."

    decrypted_key = manager.unlock_wallet_for_transaction(
        wallet_id=wallet_id,
        encrypted_data=encrypted_data,
        transaction_details=transaction_details,
    )

    if decrypted_key:
        print("\n✓ Second transaction can be signed")

    # Step 4: Invalidate authentication
    print("\n🔒 Step 4: Invalidate Authentication")
    print("-" * 70)
    manager.invalidate_authentication(wallet_id)

    # Step 5: Test device binding
    print("\n🔒 Step 5: Test Device Binding")
    print("-" * 70)
    print("Simulating wallet transfer to different device...")

    different_device_manager = WalletSecurityManager(
        "different-device-67890",
        biometric_provider,
    )

    decrypted_key = different_device_manager.unlock_wallet_for_transaction(
        wallet_id=wallet_id,
        encrypted_data=encrypted_data,
    )

    if not decrypted_key:
        print("\n✓ Correctly prevented access from different device")

    print("\n" + "=" * 70)
    print("Demo Complete")
    print("=" * 70)

def demo_error_handling():
    """Demonstrate error handling scenarios."""
    print("\n" + "=" * 70)
    print("Error Handling Demo")
    print("=" * 70)

    device_id = "mock-device-12345"
    wallet_id = "0x1234567890abcdef"
    private_key = b"mock_private_key_32_bytes_long!!"

    biometric_provider = MockBiometricProvider()
    manager = WalletSecurityManager(device_id, biometric_provider)

    # Scenario 1: Authentication failure
    print("\n❌ Scenario 1: Authentication Failure")
    print("-" * 70)
    biometric_provider.set_fail_next()

    encrypted_data = manager.setup_wallet_security(wallet_id, private_key)
    if not encrypted_data:
        print("✓ Correctly handled authentication failure")

    # Scenario 2: No biometrics enrolled
    print("\n❌ Scenario 2: No Biometrics Enrolled")
    print("-" * 70)
    biometric_provider.set_enrolled(False)

    encrypted_data = manager.setup_wallet_security(wallet_id, private_key)
    if not encrypted_data:
        print("✓ Correctly detected missing biometric enrollment")

    print("\n" + "=" * 70)

if __name__ == "__main__":
    demo_wallet_flow()
    demo_error_handling()
