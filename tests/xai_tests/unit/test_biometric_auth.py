"""
Unit tests for biometric authentication framework

Tests cover:
- BiometricAuthManager session management
- SecureEnclaveManager key operations
- BiometricWallet policy enforcement
- Error handling and edge cases
- Thread safety
- Mock providers for testing
"""

import pytest
import time
import threading
from decimal import Decimal
from unittest.mock import Mock, patch

from xai.mobile.biometric_auth import (
    BiometricAuthManager,
    BiometricSession,
    SessionConfig,
    MockBiometricProvider,
    BiometricType,
    BiometricStrength,
    BiometricError,
    ProtectionLevel,
    BiometricResult
)

from xai.mobile.secure_enclave import (
    SecureEnclaveManager,
    MockSecureEnclaveProvider,
    KeyAlgorithm,
    KeyProtection,
    AttestationLevel
)

from xai.mobile.biometric_wallet import (
    BiometricWallet,
    BiometricWalletFactory,
    SecurityPolicy,
    AuthenticationRequiredError,
    AuthenticationFailedError,
    WalletLockedError
)

from xai.core.wallet import Wallet


class TestBiometricSession:
    """Test BiometricSession class."""

    def test_session_creation(self):
        """Test creating a new session."""
        config = SessionConfig(timeout_seconds=60, max_operations=5)
        session = BiometricSession(config)

        assert not session.is_valid()
        assert session.get_token() is None

    def test_session_start(self):
        """Test starting an authenticated session."""
        config = SessionConfig(timeout_seconds=60, max_operations=5)
        session = BiometricSession(config)

        result = BiometricResult(
            success=True,
            auth_type=BiometricType.FINGERPRINT,
            strength=BiometricStrength.STRONG,
            token=b"test_token_123456789"
        )

        session.start_session(result)

        assert session.is_valid()
        assert session.get_token() == b"test_token_123456789"

    def test_session_timeout(self):
        """Test session timeout expiry."""
        config = SessionConfig(timeout_seconds=1, max_operations=10)
        session = BiometricSession(config)

        result = BiometricResult(
            success=True,
            auth_type=BiometricType.FACE_ID,
            strength=BiometricStrength.STRONG,
            token=b"test_token"
        )

        session.start_session(result)
        assert session.is_valid()

        # Wait for timeout
        time.sleep(1.1)
        assert not session.is_valid()

    def test_session_operation_limit(self):
        """Test session expires after max operations."""
        config = SessionConfig(timeout_seconds=60, max_operations=3)
        session = BiometricSession(config)

        result = BiometricResult(
            success=True,
            auth_type=BiometricType.FINGERPRINT,
            strength=BiometricStrength.STRONG,
            token=b"test_token"
        )

        session.start_session(result)

        # Use up operations
        for i in range(3):
            assert session.get_token() is not None

        # Should be invalid after max operations
        assert not session.is_valid()

    def test_session_invalidate(self):
        """Test manual session invalidation."""
        config = SessionConfig()
        session = BiometricSession(config)

        result = BiometricResult(
            success=True,
            auth_type=BiometricType.FINGERPRINT,
            strength=BiometricStrength.STRONG,
            token=b"test_token"
        )

        session.start_session(result)
        assert session.is_valid()

        session.invalidate()
        assert not session.is_valid()
        assert session.get_token() is None

    def test_session_strength_requirement(self):
        """Test session strength validation."""
        config = SessionConfig()
        session = BiometricSession(config)

        result = BiometricResult(
            success=True,
            auth_type=BiometricType.FINGERPRINT,
            strength=BiometricStrength.WEAK,
            token=b"test_token"
        )

        session.start_session(result)

        # Should fail strong requirement
        assert not session.is_valid(require_strength=BiometricStrength.STRONG)

        # Should pass weak requirement
        assert session.is_valid(require_strength=BiometricStrength.WEAK)

    def test_session_info(self):
        """Test session information retrieval."""
        config = SessionConfig()
        session = BiometricSession(config)

        result = BiometricResult(
            success=True,
            auth_type=BiometricType.FACE_ID,
            strength=BiometricStrength.STRONG,
            token=b"test_token"
        )

        session.start_session(result)
        info = session.get_info()

        assert info["valid"] is True
        assert info["auth_type"] == "face_id"
        assert info["strength"] == "strong"
        assert "age_seconds" in info
        assert "operations" in info


class TestBiometricAuthManager:
    """Test BiometricAuthManager class."""

    def test_manager_initialization(self):
        """Test manager initialization."""
        provider = MockBiometricProvider()
        manager = BiometricAuthManager(provider)

        assert manager.is_available().available is True

    def test_authenticate_success(self):
        """Test successful authentication."""
        provider = MockBiometricProvider()
        manager = BiometricAuthManager(provider)

        result = manager.authenticate("Test prompt")

        assert result.success is True
        assert result.token is not None
        assert manager.is_session_valid()

    def test_authenticate_failure(self):
        """Test failed authentication."""
        provider = MockBiometricProvider()
        provider.set_fail_next(True)
        manager = BiometricAuthManager(provider)

        result = manager.authenticate("Test prompt")

        assert result.success is False
        assert result.error_code == BiometricError.AUTHENTICATION_FAILED
        assert not manager.is_session_valid()

    def test_session_reuse(self):
        """Test session reuse without re-authentication."""
        provider = MockBiometricProvider()
        manager = BiometricAuthManager(provider)

        # First authentication
        result1 = manager.authenticate("Test")
        assert result1.success is True
        token1 = result1.token

        # Second call should reuse session
        result2 = manager.authenticate("Test", force_reauth=False)
        assert result2.success is True
        assert result2.token == token1

    def test_force_reauth(self):
        """Test forced re-authentication."""
        provider = MockBiometricProvider()
        manager = BiometricAuthManager(provider)

        # First authentication
        result1 = manager.authenticate("Test")
        token1 = result1.token

        # Force new authentication
        result2 = manager.authenticate("Test", force_reauth=True)
        assert result2.success is True
        assert result2.token != token1  # New token

    def test_session_invalidation(self):
        """Test session invalidation."""
        provider = MockBiometricProvider()
        manager = BiometricAuthManager(provider)

        manager.authenticate("Test")
        assert manager.is_session_valid()

        manager.invalidate_session()
        assert not manager.is_session_valid()

    def test_app_background_invalidation(self):
        """Test session invalidation on app background."""
        provider = MockBiometricProvider()
        config = SessionConfig(invalidate_on_background=True)
        manager = BiometricAuthManager(provider, config)

        manager.authenticate("Test")
        assert manager.is_session_valid()

        manager.on_app_background()
        assert not manager.is_session_valid()

    def test_not_enrolled(self):
        """Test behavior when biometric not enrolled."""
        provider = MockBiometricProvider()
        provider.set_enrolled(False)
        manager = BiometricAuthManager(provider)

        result = manager.authenticate("Test")

        assert result.success is False
        assert result.error_code == BiometricError.NOT_ENROLLED

    def test_lockout(self):
        """Test biometric lockout handling."""
        provider = MockBiometricProvider()
        provider.set_locked(True)
        manager = BiometricAuthManager(provider)

        result = manager.authenticate("Test")

        assert result.success is False
        assert result.error_code == BiometricError.LOCKOUT


class TestSecureEnclaveManager:
    """Test SecureEnclaveManager class."""

    def test_manager_initialization(self):
        """Test secure enclave manager initialization."""
        provider = MockSecureEnclaveProvider()
        manager = SecureEnclaveManager(provider)

        assert manager.is_available() is True

    def test_generate_wallet_key(self):
        """Test wallet key generation."""
        provider = MockSecureEnclaveProvider()
        manager = SecureEnclaveManager(provider)

        key = manager.generate_wallet_key(
            wallet_id="test_wallet",
            algorithm=KeyAlgorithm.ECDSA_SECP256K1
        )

        assert key is not None
        assert key.key_id == "wallet_test_wallet"
        assert key.algorithm == KeyAlgorithm.ECDSA_SECP256K1
        assert len(key.public_key) > 0

    def test_get_public_key(self):
        """Test retrieving public key."""
        provider = MockSecureEnclaveProvider()
        manager = SecureEnclaveManager(provider)

        # Generate key first
        key = manager.generate_wallet_key("test_wallet")
        public_key = manager.get_public_key("test_wallet")

        assert public_key == key.public_key

    def test_sign_transaction_without_biometric(self):
        """Test signing without biometric provider."""
        provider = MockSecureEnclaveProvider()
        manager = SecureEnclaveManager(provider, biometric_provider=None)

        # Generate key
        manager.generate_wallet_key("test_wallet", require_biometric=False)

        # Sign transaction
        tx_hash = b"transaction_hash_123"
        signature = manager.sign_transaction("test_wallet", tx_hash)

        assert signature is not None
        assert len(signature) > 0

    def test_sign_transaction_with_biometric(self):
        """Test signing with biometric authentication."""
        enclave_provider = MockSecureEnclaveProvider()
        bio_provider = MockBiometricProvider()
        manager = SecureEnclaveManager(enclave_provider, bio_provider)

        # Generate key with biometric requirement
        manager.generate_wallet_key("test_wallet", require_biometric=True)

        # Sign transaction (should trigger biometric)
        tx_hash = b"transaction_hash_123"
        signature = manager.sign_transaction("test_wallet", tx_hash)

        assert signature is not None

    def test_delete_wallet_key(self):
        """Test deleting wallet key."""
        provider = MockSecureEnclaveProvider()
        manager = SecureEnclaveManager(provider)

        # Generate key
        manager.generate_wallet_key("test_wallet")
        assert manager.get_public_key("test_wallet") is not None

        # Delete key
        success = manager.delete_wallet_key("test_wallet")
        assert success is True
        assert manager.get_public_key("test_wallet") is None

    def test_key_attestation(self):
        """Test key attestation."""
        provider = MockSecureEnclaveProvider()
        manager = SecureEnclaveManager(provider)

        # Generate key
        manager.generate_wallet_key("test_wallet")

        # Verify attestation
        attestation = manager.verify_key_attestation("test_wallet")

        assert attestation.is_valid is True
        assert attestation.hardware_backed is True
        assert attestation.attestation_level == AttestationLevel.HARDWARE

    def test_enclave_unavailable(self):
        """Test behavior when enclave unavailable."""
        provider = MockSecureEnclaveProvider()
        provider.set_available(False)
        manager = SecureEnclaveManager(provider)

        assert manager.is_available() is False

        key = manager.generate_wallet_key("test_wallet")
        assert key is None


class TestBiometricWallet:
    """Test BiometricWallet class."""

    def test_wallet_initialization(self):
        """Test biometric wallet initialization."""
        wallet = Wallet()
        provider = MockBiometricProvider()
        bio_manager = BiometricAuthManager(provider)

        bio_wallet = BiometricWallet(wallet, bio_manager)

        assert bio_wallet.address == wallet.address
        assert bio_wallet.public_key == wallet.public_key

    def test_sign_message_with_biometric(self):
        """Test signing message with biometric authentication."""
        wallet = Wallet()
        provider = MockBiometricProvider()
        bio_manager = BiometricAuthManager(provider)
        bio_wallet = BiometricWallet(wallet, bio_manager)

        # Sign message (should trigger biometric)
        signature = bio_wallet.sign_message("Hello XAI")

        assert signature is not None
        assert len(signature) > 0

    def test_sign_message_auth_failure(self):
        """Test signing fails when authentication fails."""
        wallet = Wallet()
        provider = MockBiometricProvider()
        provider.set_fail_next(True)
        bio_manager = BiometricAuthManager(provider)
        bio_wallet = BiometricWallet(wallet, bio_manager)

        with pytest.raises(AuthenticationFailedError):
            bio_wallet.sign_message("Hello XAI")

    def test_get_private_key_requires_auth(self):
        """Test getting private key requires authentication."""
        wallet = Wallet()
        provider = MockBiometricProvider()
        bio_manager = BiometricAuthManager(provider)
        bio_wallet = BiometricWallet(wallet, bio_manager)

        private_key = bio_wallet.get_private_key()

        assert private_key == wallet.private_key

    def test_get_private_key_auth_failure(self):
        """Test getting private key fails on auth failure."""
        wallet = Wallet()
        provider = MockBiometricProvider()
        provider.set_fail_next(True)
        bio_manager = BiometricAuthManager(provider)
        bio_wallet = BiometricWallet(wallet, bio_manager)

        with pytest.raises(AuthenticationFailedError):
            bio_wallet.get_private_key()

    def test_export_wallet_requires_auth(self):
        """Test exporting wallet requires authentication."""
        wallet = Wallet()
        provider = MockBiometricProvider()
        bio_manager = BiometricAuthManager(provider)
        bio_wallet = BiometricWallet(wallet, bio_manager)

        exported = bio_wallet.export_wallet(password="secret")

        assert "address" in exported
        assert exported["address"] == wallet.address

    def test_transaction_threshold_policy(self):
        """Test transaction amount-based authentication policy."""
        wallet = Wallet()
        provider = MockBiometricProvider()
        bio_manager = BiometricAuthManager(provider)

        policy = SecurityPolicy(
            small_transaction_threshold=Decimal("1000000000000000000"),
            large_transaction_threshold=Decimal("10000000000000000000")
        )

        bio_wallet = BiometricWallet(wallet, bio_manager, policy)

        # Small transaction
        sig1 = bio_wallet.sign_message("tx1", amount=Decimal("500000000000000000"))
        assert sig1 is not None

        # Large transaction
        sig2 = bio_wallet.sign_message("tx2", amount=Decimal("20000000000000000000"))
        assert sig2 is not None

    def test_wallet_lockout_after_failures(self):
        """Test wallet locks after repeated auth failures."""
        wallet = Wallet()
        provider = MockBiometricProvider()
        bio_manager = BiometricAuthManager(provider)

        policy = SecurityPolicy(
            max_failed_attempts=3,
            lockout_duration_seconds=1
        )

        bio_wallet = BiometricWallet(wallet, bio_manager, policy)

        # Fail authentication 3 times
        for i in range(3):
            provider.set_fail_next(True)
            with pytest.raises(AuthenticationFailedError):
                bio_wallet.get_private_key()

        # Should be locked now
        assert bio_wallet.is_locked()

        with pytest.raises(WalletLockedError):
            bio_wallet.get_private_key()

        # Wait for lockout to expire
        time.sleep(1.1)
        assert not bio_wallet.is_locked()

    def test_audit_log(self):
        """Test audit logging of sensitive operations."""
        wallet = Wallet()
        provider = MockBiometricProvider()
        bio_manager = BiometricAuthManager(provider)

        policy = SecurityPolicy(audit_sensitive_operations=True)
        bio_wallet = BiometricWallet(wallet, bio_manager, policy)

        # Perform operations
        bio_wallet.sign_message("test")
        bio_wallet.get_private_key()

        audit_log = bio_wallet.get_audit_log()
        assert len(audit_log) >= 2

    def test_policy_update(self):
        """Test updating security policy."""
        wallet = Wallet()
        provider = MockBiometricProvider()
        bio_manager = BiometricAuthManager(provider)
        bio_wallet = BiometricWallet(wallet, bio_manager)

        new_policy = SecurityPolicy(
            require_biometric_for_private_key=False
        )

        bio_wallet.update_policy(new_policy)

        # Should not require auth now
        private_key = bio_wallet.get_private_key()
        assert private_key == wallet.private_key

    def test_wallet_status(self):
        """Test getting wallet status."""
        wallet = Wallet()
        provider = MockBiometricProvider()
        bio_manager = BiometricAuthManager(provider)
        bio_wallet = BiometricWallet(wallet, bio_manager)

        status = bio_wallet.get_status()

        assert "address" in status
        assert "locked" in status
        assert "biometric_session_valid" in status


class TestBiometricWalletFactory:
    """Test BiometricWalletFactory class."""

    def test_factory_initialization(self):
        """Test factory initialization."""
        provider = MockBiometricProvider()
        bio_manager = BiometricAuthManager(provider)

        factory = BiometricWalletFactory(bio_manager)

        assert factory.biometric_manager == bio_manager

    def test_create_wallet(self):
        """Test creating new wallet through factory."""
        provider = MockBiometricProvider()
        bio_manager = BiometricAuthManager(provider)
        factory = BiometricWalletFactory(bio_manager)

        wallet = factory.create_wallet()

        assert wallet.address is not None
        assert wallet.public_key is not None

    def test_wrap_wallet(self):
        """Test wrapping existing wallet."""
        existing_wallet = Wallet()
        provider = MockBiometricProvider()
        bio_manager = BiometricAuthManager(provider)
        factory = BiometricWalletFactory(bio_manager)

        wrapped = factory.wrap_wallet(existing_wallet)

        assert wrapped.address == existing_wallet.address

    def test_create_from_mnemonic(self):
        """Test creating wallet from mnemonic through factory."""
        provider = MockBiometricProvider()
        bio_manager = BiometricAuthManager(provider)
        factory = BiometricWalletFactory(bio_manager)

        mnemonic = Wallet.generate_mnemonic()
        wallet = factory.create_from_mnemonic(mnemonic)

        assert wallet.address is not None

    def test_factory_with_custom_policy(self):
        """Test factory with custom default policy."""
        provider = MockBiometricProvider()
        bio_manager = BiometricAuthManager(provider)

        custom_policy = SecurityPolicy(
            require_biometric_for_private_key=False
        )

        factory = BiometricWalletFactory(bio_manager, default_policy=custom_policy)
        wallet = factory.create_wallet()

        # Should use custom policy
        assert wallet.get_policy().require_biometric_for_private_key is False


class TestThreadSafety:
    """Test thread safety of biometric components."""

    def test_session_thread_safety(self):
        """Test BiometricSession is thread-safe."""
        config = SessionConfig(timeout_seconds=60, max_operations=100)
        session = BiometricSession(config)

        result = BiometricResult(
            success=True,
            auth_type=BiometricType.FINGERPRINT,
            strength=BiometricStrength.STRONG,
            token=b"test_token"
        )

        session.start_session(result)

        tokens = []
        errors = []

        def get_token():
            try:
                token = session.get_token()
                tokens.append(token)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=get_token) for _ in range(10)]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(tokens) == 10

    def test_manager_thread_safety(self):
        """Test BiometricAuthManager is thread-safe."""
        provider = MockBiometricProvider()
        manager = BiometricAuthManager(provider)

        results = []
        errors = []

        def authenticate():
            try:
                result = manager.authenticate("Test")
                results.append(result)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=authenticate) for _ in range(5)]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(results) == 5


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_invalid_session_start(self):
        """Test starting session with failed authentication."""
        config = SessionConfig()
        session = BiometricSession(config)

        result = BiometricResult(
            success=False,
            auth_type=BiometricType.NONE,
            strength=BiometricStrength.NONE,
            error_code=BiometricError.AUTHENTICATION_FAILED
        )

        with pytest.raises(ValueError):
            session.start_session(result)

    def test_session_without_token(self):
        """Test session cannot start without token."""
        config = SessionConfig()
        session = BiometricSession(config)

        result = BiometricResult(
            success=True,
            auth_type=BiometricType.FINGERPRINT,
            strength=BiometricStrength.STRONG,
            token=None  # No token
        )

        with pytest.raises(ValueError):
            session.start_session(result)

    def test_sign_nonexistent_key(self):
        """Test signing with non-existent key."""
        provider = MockSecureEnclaveProvider()
        manager = SecureEnclaveManager(provider)

        signature = manager.sign_transaction("nonexistent", b"data")

        assert signature is None

    def test_wallet_verify_signature_no_auth(self):
        """Test signature verification doesn't require auth."""
        wallet = Wallet()
        provider = MockBiometricProvider()
        bio_manager = BiometricAuthManager(provider)
        bio_wallet = BiometricWallet(wallet, bio_manager)

        message = "test"
        signature = wallet.sign_message(message)

        # Should not require authentication
        is_valid = bio_wallet.verify_signature(message, signature, wallet.public_key)
        assert is_valid is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
