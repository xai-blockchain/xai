"""
Tests for Biometric Authentication Framework

Run with: pytest test_biometric_auth.py -v
"""

import secrets

import pytest

from xai.sdk.biometric.biometric_auth import (
    BiometricCapability,
    BiometricError,
    BiometricType,
    MockBiometricProvider,
)
from xai.sdk.biometric.secure_key_derivation import (
    BiometricTokenCache,
    EncryptedWalletKey,
    SecureKeyDerivation,
)


class TestMockBiometricProvider:
    """Tests for MockBiometricProvider."""

    def test_is_available_success(self):
        """Test checking biometric availability."""
        provider = MockBiometricProvider(simulate_type=BiometricType.FACE_ID)
        capability = provider.is_available()

        assert capability.available is True
        assert capability.enrolled is True
        assert BiometricType.FACE_ID in capability.biometric_types
        assert capability.hardware_detected is True
        assert capability.security_level == "strong"

    def test_is_available_not_enrolled(self):
        """Test when biometrics not enrolled."""
        provider = MockBiometricProvider()
        provider.set_enrolled(False)
        capability = provider.is_available()

        assert capability.available is True
        assert capability.enrolled is False

    def test_authenticate_success(self):
        """Test successful authentication."""
        provider = MockBiometricProvider(simulate_type=BiometricType.FINGERPRINT)
        result = provider.authenticate(
            prompt_message="Test authentication",
            cancel_button_text="Cancel",
        )

        assert result.success is True
        assert result.auth_type == BiometricType.FINGERPRINT
        assert result.error_code is None
        assert result.timestamp is not None

    def test_authenticate_failure(self):
        """Test authentication failure."""
        provider = MockBiometricProvider()
        provider.set_fail_next()
        result = provider.authenticate()

        assert result.success is False
        assert result.error_code == BiometricError.AUTHENTICATION_FAILED
        assert result.error_message is not None

    def test_authenticate_not_enrolled(self):
        """Test authentication when not enrolled."""
        provider = MockBiometricProvider()
        provider.set_enrolled(False)
        result = provider.authenticate()

        assert result.success is False
        assert result.error_code == BiometricError.NOT_ENROLLED

    def test_get_auth_type(self):
        """Test getting biometric type."""
        provider = MockBiometricProvider(simulate_type=BiometricType.TOUCH_ID)
        auth_type = provider.get_auth_type()

        assert auth_type == BiometricType.TOUCH_ID

    def test_invalidate_authentication(self):
        """Test invalidating authentication."""
        provider = MockBiometricProvider()
        result = provider.invalidate_authentication()

        assert result is True


class TestSecureKeyDerivation:
    """Tests for SecureKeyDerivation."""

    def test_initialization(self):
        """Test initialization with device ID."""
        device_id = "test-device-123"
        kdf = SecureKeyDerivation(device_id)

        assert kdf.device_id == device_id
        assert len(kdf.device_id_hash) == 32  # SHA-256 output

    def test_initialization_empty_device_id(self):
        """Test initialization fails with empty device ID."""
        with pytest.raises(ValueError, match="Device ID cannot be empty"):
            SecureKeyDerivation("")

    def test_derive_key_basic(self):
        """Test basic key derivation."""
        kdf = SecureKeyDerivation("device-123")
        biometric_token = secrets.token_bytes(32)

        derived = kdf.derive_key(biometric_token)

        assert len(derived.key) == 32  # 256 bits
        assert len(derived.salt) == 32
        assert derived.iterations == SecureKeyDerivation.DEFAULT_ITERATIONS
        assert derived.algorithm == "PBKDF2-HMAC-SHA256"

    def test_derive_key_with_salt(self):
        """Test key derivation with provided salt."""
        kdf = SecureKeyDerivation("device-123")
        biometric_token = secrets.token_bytes(32)
        salt = secrets.token_bytes(32)

        derived = kdf.derive_key(biometric_token, salt=salt)

        assert derived.salt == salt

    def test_derive_key_with_context(self):
        """Test key derivation with additional context."""
        kdf = SecureKeyDerivation("device-123")
        biometric_token = secrets.token_bytes(32)

        derived1 = kdf.derive_key(biometric_token, additional_context="wallet-1")
        derived2 = kdf.derive_key(biometric_token, additional_context="wallet-2")

        # Different contexts should produce different keys
        assert derived1.key != derived2.key

    def test_derive_key_deterministic(self):
        """Test that key derivation is deterministic."""
        kdf = SecureKeyDerivation("device-123")
        biometric_token = secrets.token_bytes(32)
        salt = secrets.token_bytes(32)

        derived1 = kdf.derive_key(biometric_token, salt=salt)
        derived2 = kdf.derive_key(biometric_token, salt=salt)

        assert derived1.key == derived2.key

    def test_derive_key_empty_token(self):
        """Test key derivation fails with empty token."""
        kdf = SecureKeyDerivation("device-123")

        with pytest.raises(ValueError, match="Biometric token cannot be empty"):
            kdf.derive_key(b"")

    def test_derive_key_short_salt(self):
        """Test key derivation fails with short salt."""
        kdf = SecureKeyDerivation("device-123")
        biometric_token = secrets.token_bytes(32)
        short_salt = b"short"

        with pytest.raises(ValueError, match="Salt must be at least 16 bytes"):
            kdf.derive_key(biometric_token, salt=short_salt)

    def test_derive_key_low_iterations(self):
        """Test key derivation fails with too few iterations."""
        kdf = SecureKeyDerivation("device-123")
        biometric_token = secrets.token_bytes(32)

        with pytest.raises(ValueError, match="Iterations must be at least 100,000"):
            kdf.derive_key(biometric_token, iterations=50000)

    def test_encrypt_decrypt_wallet_key(self):
        """Test encrypting and decrypting wallet key."""
        kdf = SecureKeyDerivation("device-123")
        biometric_token = secrets.token_bytes(32)
        wallet_key = b"supersecret_private_key_32bytes!"

        # Encrypt
        encrypted = kdf.encrypt_wallet_key(
            wallet_private_key=wallet_key,
            biometric_token=biometric_token,
            wallet_id="0x1234",
        )

        assert len(encrypted.ciphertext) > 0
        assert len(encrypted.iv) == 12
        assert len(encrypted.salt) == 32
        assert encrypted.algorithm == "AES-256-GCM"

        # Decrypt
        decrypted = kdf.decrypt_wallet_key(
            encrypted=encrypted,
            biometric_token=biometric_token,
            wallet_id="0x1234",
        )

        assert decrypted == wallet_key

    def test_decrypt_wrong_device(self):
        """Test decryption fails on different device."""
        kdf1 = SecureKeyDerivation("device-123")
        kdf2 = SecureKeyDerivation("device-456")

        biometric_token = secrets.token_bytes(32)
        wallet_key = b"supersecret_private_key_32bytes!"

        # Encrypt on device 1
        encrypted = kdf1.encrypt_wallet_key(
            wallet_private_key=wallet_key,
            biometric_token=biometric_token,
        )

        # Try to decrypt on device 2
        with pytest.raises(ValueError, match="Device ID mismatch"):
            kdf2.decrypt_wallet_key(
                encrypted=encrypted,
                biometric_token=biometric_token,
            )

    def test_decrypt_wrong_token(self):
        """Test decryption fails with wrong biometric token."""
        kdf = SecureKeyDerivation("device-123")
        biometric_token = secrets.token_bytes(32)
        wrong_token = secrets.token_bytes(32)
        wallet_key = b"supersecret_private_key_32bytes!"

        # Encrypt
        encrypted = kdf.encrypt_wallet_key(
            wallet_private_key=wallet_key,
            biometric_token=biometric_token,
        )

        # Try to decrypt with wrong token
        with pytest.raises(ValueError, match="Decryption failed"):
            kdf.decrypt_wallet_key(
                encrypted=encrypted,
                biometric_token=wrong_token,
            )

    def test_decrypt_wrong_wallet_id(self):
        """Test decryption fails with wrong wallet ID."""
        kdf = SecureKeyDerivation("device-123")
        biometric_token = secrets.token_bytes(32)
        wallet_key = b"supersecret_private_key_32bytes!"

        # Encrypt
        encrypted = kdf.encrypt_wallet_key(
            wallet_private_key=wallet_key,
            biometric_token=biometric_token,
            wallet_id="0x1234",
        )

        # Try to decrypt with wrong wallet ID
        with pytest.raises(ValueError, match="Decryption failed"):
            kdf.decrypt_wallet_key(
                encrypted=encrypted,
                biometric_token=biometric_token,
                wallet_id="0x5678",
            )

    def test_verify_device_binding(self):
        """Test verifying device binding."""
        kdf1 = SecureKeyDerivation("device-123")
        kdf2 = SecureKeyDerivation("device-456")

        biometric_token = secrets.token_bytes(32)
        wallet_key = b"supersecret_private_key_32bytes!"

        encrypted = kdf1.encrypt_wallet_key(
            wallet_private_key=wallet_key,
            biometric_token=biometric_token,
        )

        assert kdf1.verify_device_binding(encrypted) is True
        assert kdf2.verify_device_binding(encrypted) is False


class TestBiometricTokenCache:
    """Tests for BiometricTokenCache."""

    def test_store_and_retrieve(self):
        """Test storing and retrieving tokens."""
        cache = BiometricTokenCache(validity_seconds=60)
        token = secrets.token_bytes(32)

        cache.store("wallet-1", token)
        retrieved = cache.retrieve("wallet-1")

        assert retrieved == token

    def test_retrieve_expired(self):
        """Test retrieving expired token returns None."""
        cache = BiometricTokenCache(validity_seconds=0)
        token = secrets.token_bytes(32)

        cache.store("wallet-1", token)

        import time
        time.sleep(0.1)

        retrieved = cache.retrieve("wallet-1")
        assert retrieved is None

    def test_retrieve_nonexistent(self):
        """Test retrieving nonexistent token returns None."""
        cache = BiometricTokenCache()
        retrieved = cache.retrieve("nonexistent")

        assert retrieved is None

    def test_invalidate_specific(self):
        """Test invalidating specific token."""
        cache = BiometricTokenCache()
        token1 = secrets.token_bytes(32)
        token2 = secrets.token_bytes(32)

        cache.store("wallet-1", token1)
        cache.store("wallet-2", token2)

        cache.invalidate("wallet-1")

        assert cache.retrieve("wallet-1") is None
        assert cache.retrieve("wallet-2") == token2

    def test_invalidate_all(self):
        """Test invalidating all tokens."""
        cache = BiometricTokenCache()
        token1 = secrets.token_bytes(32)
        token2 = secrets.token_bytes(32)

        cache.store("wallet-1", token1)
        cache.store("wallet-2", token2)

        cache.invalidate()

        assert cache.retrieve("wallet-1") is None
        assert cache.retrieve("wallet-2") is None


class TestIntegration:
    """Integration tests combining multiple components."""

    def test_full_wallet_flow(self):
        """Test complete wallet security flow."""
        # Setup
        device_id = "device-123"
        wallet_id = "0x1234567890abcdef"
        private_key = b"supersecret_private_key_32bytes!"

        provider = MockBiometricProvider(BiometricType.FACE_ID)
        kdf = SecureKeyDerivation(device_id)
        cache = BiometricTokenCache()

        # Check availability
        capability = provider.is_available()
        assert capability.available is True

        # Authenticate
        auth_result = provider.authenticate()
        assert auth_result.success is True

        # Get biometric token (mock)
        biometric_token = SecureKeyDerivation.generate_biometric_token_mock()
        cache.store(wallet_id, biometric_token)

        # Encrypt wallet key
        encrypted = kdf.encrypt_wallet_key(
            wallet_private_key=private_key,
            biometric_token=biometric_token,
            wallet_id=wallet_id,
        )

        # Verify device binding
        assert kdf.verify_device_binding(encrypted) is True

        # Later: decrypt for transaction
        cached_token = cache.retrieve(wallet_id)
        assert cached_token is not None

        decrypted = kdf.decrypt_wallet_key(
            encrypted=encrypted,
            biometric_token=cached_token,
            wallet_id=wallet_id,
        )

        assert decrypted == private_key

    def test_multiple_wallets(self):
        """Test managing multiple wallets."""
        device_id = "device-123"
        kdf = SecureKeyDerivation(device_id)
        biometric_token = secrets.token_bytes(32)

        wallets = {
            "wallet-1": b"private_key_1_32_bytes_long!!!",
            "wallet-2": b"private_key_2_32_bytes_long!!!",
            "wallet-3": b"private_key_3_32_bytes_long!!!",
        }

        # Encrypt all wallets
        encrypted_wallets = {}
        for wallet_id, private_key in wallets.items():
            encrypted_wallets[wallet_id] = kdf.encrypt_wallet_key(
                wallet_private_key=private_key,
                biometric_token=biometric_token,
                wallet_id=wallet_id,
            )

        # Decrypt and verify each
        for wallet_id, private_key in wallets.items():
            decrypted = kdf.decrypt_wallet_key(
                encrypted=encrypted_wallets[wallet_id],
                biometric_token=biometric_token,
                wallet_id=wallet_id,
            )
            assert decrypted == private_key


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
