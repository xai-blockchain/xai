"""
Example usage of the biometric authentication framework

This demonstrates how to integrate biometric authentication with XAI wallets
for production mobile applications.

Platform-specific implementations:
- iOS: Replace MockBiometricProvider with LocalAuthentication wrapper
- Android: Replace MockBiometricProvider with BiometricPrompt wrapper
- React Native: Use react-native-biometrics bridge
"""

from decimal import Decimal

from xai.core.wallet import Wallet
from xai.mobile.biometric_auth import (
    BiometricAuthManager,
    MockBiometricProvider,
    ProtectionLevel,
    SessionConfig,
)
from xai.mobile.biometric_wallet import BiometricWallet, BiometricWalletFactory, SecurityPolicy
from xai.mobile.secure_enclave import KeyAlgorithm, MockSecureEnclaveProvider, SecureEnclaveManager


def example_basic_biometric_wallet():
    """Example: Basic biometric-protected wallet."""
    print("\n=== Example 1: Basic Biometric Wallet ===\n")

    # Initialize biometric provider (mock for testing)
    # In production, use platform-specific provider
    bio_provider = MockBiometricProvider()
    bio_manager = BiometricAuthManager(bio_provider)

    # Create standard wallet
    wallet = Wallet()
    print(f"Wallet address: {wallet.address}")

    # Wrap with biometric protection
    bio_wallet = BiometricWallet(wallet, bio_manager)

    # Signing requires biometric authentication
    print("\nSigning message (requires biometric)...")
    signature = bio_wallet.sign_message("Hello XAI!")
    print(f"Signature: {signature[:32]}...")

    # Viewing private key requires biometric
    print("\nAccessing private key (requires biometric)...")
    private_key = bio_wallet.get_private_key()
    print(f"Private key: {private_key[:16]}...")


def example_secure_enclave():
    """Example: Hardware-backed key storage and signing."""
    print("\n=== Example 2: Secure Enclave Integration ===\n")

    # Initialize secure enclave (mock for testing)
    enclave_provider = MockSecureEnclaveProvider()
    bio_provider = MockBiometricProvider()

    enclave_manager = SecureEnclaveManager(enclave_provider, bio_provider)

    # Generate key in secure enclave
    print("Generating key in secure enclave...")
    key = enclave_manager.generate_wallet_key(
        wallet_id="secure_wallet_1",
        algorithm=KeyAlgorithm.ECDSA_SECP256K1,
        require_biometric=True
    )

    print(f"Key ID: {key.key_id}")
    print(f"Algorithm: {key.algorithm.value}")
    print(f"Public key: {key.public_key.hex()[:32]}...")

    # Sign transaction with hardware key (requires biometric)
    print("\nSigning transaction in secure enclave...")
    tx_hash = b"transaction_hash_example_123456789"
    signature = enclave_manager.sign_transaction("secure_wallet_1", tx_hash)
    print(f"Signature: {signature.hex()[:32]}...")

    # Verify key attestation
    print("\nVerifying key attestation...")
    attestation = enclave_manager.verify_key_attestation("secure_wallet_1")
    print(f"Hardware-backed: {attestation.hardware_backed}")
    print(f"Attestation level: {attestation.attestation_level.value}")


def example_custom_security_policy():
    """Example: Custom security policies for different use cases."""
    print("\n=== Example 3: Custom Security Policies ===\n")

    bio_provider = MockBiometricProvider()
    bio_manager = BiometricAuthManager(bio_provider)

    # High-security policy for large amounts
    high_security_policy = SecurityPolicy(
        require_biometric_for_private_key=True,
        require_biometric_for_export=True,
        require_biometric_for_signing=True,
        small_transaction_threshold=Decimal("1000000000000000000"),  # 1 token
        large_transaction_threshold=Decimal("10000000000000000000"),  # 10 tokens
        private_key_protection=ProtectionLevel.BIOMETRIC_STRONG,
        large_tx_protection=ProtectionLevel.BIOMETRIC_STRONG,
        max_failed_attempts=3,
        lockout_duration_seconds=300,
        audit_sensitive_operations=True
    )

    wallet = Wallet()
    bio_wallet = BiometricWallet(wallet, bio_manager, high_security_policy)

    print("Policy configuration:")
    print(f"  Private key protection: {high_security_policy.private_key_protection.value}")
    print(f"  Large TX threshold: {high_security_policy.large_transaction_threshold}")
    print(f"  Max failed attempts: {high_security_policy.max_failed_attempts}")
    print(f"  Audit enabled: {high_security_policy.audit_sensitive_operations}")

    # Sign small transaction
    print("\nSigning small transaction...")
    sig1 = bio_wallet.sign_message(
        "Small TX",
        amount=Decimal("500000000000000000")  # 0.5 token
    )
    print(f"Signature: {sig1[:32]}...")

    # Sign large transaction (requires stronger auth)
    print("\nSigning large transaction...")
    sig2 = bio_wallet.sign_message(
        "Large TX",
        amount=Decimal("20000000000000000000")  # 20 tokens
    )
    print(f"Signature: {sig2[:32]}...")

    # Check audit log
    audit_log = bio_wallet.get_audit_log()
    print(f"\nAudit log entries: {len(audit_log)}")
    for entry in audit_log:
        print(f"  - {entry.operation}: {'✓' if entry.success else '✗'}")


def example_wallet_factory():
    """Example: Using BiometricWalletFactory for consistent configuration."""
    print("\n=== Example 4: Wallet Factory ===\n")

    bio_provider = MockBiometricProvider()
    bio_manager = BiometricAuthManager(bio_provider)

    # Configure factory with default policy
    default_policy = SecurityPolicy(
        require_biometric_for_private_key=True,
        session_timeout_seconds=300
    )

    factory = BiometricWalletFactory(
        biometric_manager=bio_manager,
        default_policy=default_policy
    )

    # Create new wallet
    print("Creating new biometric wallet...")
    wallet1 = factory.create_wallet()
    print(f"Wallet 1: {wallet1.address[:16]}...")

    # Create from mnemonic
    print("\nCreating wallet from mnemonic...")
    mnemonic = Wallet.generate_mnemonic()
    wallet2 = factory.create_from_mnemonic(mnemonic)
    print(f"Wallet 2: {wallet2.address[:16]}...")

    # Wrap existing wallet
    print("\nWrapping existing wallet...")
    existing = Wallet()
    wallet3 = factory.wrap_wallet(existing)
    print(f"Wallet 3: {wallet3.address[:16]}...")


def example_session_management():
    """Example: Session management and configuration."""
    print("\n=== Example 5: Session Management ===\n")

    bio_provider = MockBiometricProvider()

    # Configure session behavior
    session_config = SessionConfig(
        timeout_seconds=300,           # 5 minutes
        max_operations=10,             # Max 10 ops before re-auth
        require_reauth_on_sensitive=True,
        invalidate_on_background=True,
        grace_period_seconds=30
    )

    bio_manager = BiometricAuthManager(bio_provider, session_config)

    # First authentication
    print("Authenticating...")
    result = bio_manager.authenticate("Access wallet")
    print(f"Authentication: {'✓' if result.success else '✗'}")

    # Check session status
    session_info = bio_manager.get_session_info()
    print(f"\nSession info:")
    print(f"  Valid: {session_info['valid']}")
    print(f"  Auth type: {session_info.get('auth_type', 'N/A')}")
    print(f"  Operations: {session_info.get('operations', 0)}")

    # Subsequent operations use session (no re-auth)
    print("\nPerforming operations (using session)...")
    for i in range(3):
        token = bio_manager.get_session_token()
        print(f"  Operation {i+1}: Token available = {token is not None}")

    # Simulate app going to background
    print("\nApp going to background...")
    bio_manager.on_app_background()
    print(f"Session valid after background: {bio_manager.is_session_valid()}")


def example_error_handling():
    """Example: Error handling and lockout."""
    print("\n=== Example 6: Error Handling ===\n")

    bio_provider = MockBiometricProvider()
    bio_manager = BiometricAuthManager(bio_provider)

    policy = SecurityPolicy(
        max_failed_attempts=3,
        lockout_duration_seconds=5  # Short for demo
    )

    wallet = Wallet()
    bio_wallet = BiometricWallet(wallet, bio_manager, policy)

    # Simulate failed attempts
    print("Simulating failed authentication attempts...")
    for i in range(3):
        bio_provider.set_fail_next(True)
        try:
            bio_wallet.get_private_key()
        except Exception as e:
            print(f"  Attempt {i+1}: {type(e).__name__}")

    # Check if locked
    status = bio_wallet.get_status()
    print(f"\nWallet locked: {status['locked']}")
    print(f"Failed attempts: {status['failed_attempts']}")

    # Try to unlock
    print("\nWaiting for lockout to expire...")
    import time
    time.sleep(5.1)

    print("Attempting to unlock...")
    unlocked = bio_wallet.unlock()
    print(f"Unlock successful: {unlocked}")


def main():
    """Run all examples."""
    print("=" * 60)
    print("XAI Biometric Authentication Framework - Examples")
    print("=" * 60)

    example_basic_biometric_wallet()
    example_secure_enclave()
    example_custom_security_policy()
    example_wallet_factory()
    example_session_management()
    example_error_handling()

    print("\n" + "=" * 60)
    print("All examples completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
