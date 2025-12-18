# Biometric Authentication Framework

Production-ready biometric authentication framework for XAI mobile wallets with iOS Secure Enclave and Android Keystore integration.

## Overview

This framework provides three main components:

1. **BiometricAuthManager** - Biometric authentication with session management
2. **SecureEnclaveManager** - Hardware-backed key storage and signing
3. **BiometricWallet** - Wallet wrapper with biometric protection policies

## Features

### Biometric Authentication
- Abstract interface for Face ID / Touch ID / Fingerprint
- Multiple protection levels (strong, weak, device credential)
- Configurable timeout and session management
- Automatic fallback to PIN/password
- Thread-safe operation

### Secure Enclave Integration
- Key generation inside secure hardware
- Private keys never exposed to app memory
- Hardware-backed cryptographic operations
- Key attestation support
- Platform-specific implementations:
  - iOS: Secure Enclave via SecKey API
  - Android: Android Keystore System

### Biometric Wallet Protection
- Transparent integration with existing Wallet class
- Configurable security policies
- Transaction amount-based authentication
- Automatic lockout on failed attempts
- Audit logging for sensitive operations

## Quick Start

### Basic Biometric Wallet

```python
from xai.core.wallet import Wallet
from xai.mobile import (
    BiometricAuthManager,
    BiometricWallet,
    MockBiometricProvider  # Replace with platform provider
)

# Initialize biometric authentication
bio_provider = MockBiometricProvider()  # Use real provider in production
bio_manager = BiometricAuthManager(bio_provider)

# Create wallet with biometric protection
wallet = Wallet()
bio_wallet = BiometricWallet(wallet, bio_manager)

# Signing requires biometric authentication
signature = bio_wallet.sign_message("Hello XAI!")

# Accessing private key requires biometric
private_key = bio_wallet.get_private_key()
```

### Secure Enclave Integration

```python
from xai.mobile import (
    SecureEnclaveManager,
    MockSecureEnclaveProvider,
    KeyAlgorithm
)

# Initialize secure enclave
enclave_provider = MockSecureEnclaveProvider()  # Use real provider
bio_provider = MockBiometricProvider()
enclave = SecureEnclaveManager(enclave_provider, bio_provider)

# Generate key in secure hardware
key = enclave.generate_wallet_key(
    wallet_id="wallet_1",
    algorithm=KeyAlgorithm.ECDSA_SECP256K1,
    require_biometric=True
)

# Sign transaction (private key never leaves hardware)
signature = enclave.sign_transaction(
    wallet_id="wallet_1",
    transaction_hash=tx_hash
)

# Verify hardware attestation
attestation = enclave.verify_key_attestation("wallet_1")
print(f"Hardware-backed: {attestation.hardware_backed}")
```

### Custom Security Policies

```python
from decimal import Decimal
from xai.mobile import SecurityPolicy, ProtectionLevel

# Configure security policy
policy = SecurityPolicy(
    # Private key protection
    require_biometric_for_private_key=True,
    private_key_protection=ProtectionLevel.BIOMETRIC_STRONG,

    # Transaction thresholds
    small_transaction_threshold=Decimal("1000000000000000000"),   # 1 token
    large_transaction_threshold=Decimal("10000000000000000000"),  # 10 tokens
    large_tx_protection=ProtectionLevel.BIOMETRIC_STRONG,

    # Rate limiting
    max_failed_attempts=3,
    lockout_duration_seconds=300,

    # Audit
    audit_sensitive_operations=True
)

bio_wallet = BiometricWallet(wallet, bio_manager, policy)

# Small transactions may use weaker auth
bio_wallet.sign_message("tx", amount=Decimal("500000000000000000"))

# Large transactions require strong auth
bio_wallet.sign_message("tx", amount=Decimal("20000000000000000000"))
```

### Wallet Factory

```python
from xai.mobile import BiometricWalletFactory

# Create factory with default configuration
factory = BiometricWalletFactory(
    biometric_manager=bio_manager,
    default_policy=policy
)

# Create new wallet
wallet1 = factory.create_wallet()

# Create from mnemonic
mnemonic = Wallet.generate_mnemonic()
wallet2 = factory.create_from_mnemonic(mnemonic)

# Wrap existing wallet
existing = Wallet()
wallet3 = factory.wrap_wallet(existing)
```

## Architecture

### Protection Levels

```python
from xai.mobile import ProtectionLevel

# Biometric strength levels
ProtectionLevel.BIOMETRIC_STRONG      # Class 3 (hardware-backed)
ProtectionLevel.BIOMETRIC_WEAK        # Class 2 or 3
ProtectionLevel.DEVICE_CREDENTIAL     # PIN/password/pattern
ProtectionLevel.BIOMETRIC_OR_CREDENTIAL  # Either biometric or credential
```

### Session Management

```python
from xai.mobile import SessionConfig

# Configure session behavior
config = SessionConfig(
    timeout_seconds=300,               # 5 minutes
    max_operations=10,                 # Max operations before re-auth
    require_reauth_on_sensitive=True,  # Always re-auth sensitive ops
    invalidate_on_background=True,     # Invalidate when app backgrounds
    grace_period_seconds=30            # Grace period after timeout
)

manager = BiometricAuthManager(provider, config)

# Check session status
session_info = manager.get_session_info()
print(f"Valid: {session_info['valid']}")
print(f"Operations: {session_info['operations']}")

# Handle app lifecycle
manager.on_app_background()  # Invalidate session
manager.on_app_foreground()  # App returns
```

### Key Algorithms

```python
from xai.mobile import KeyAlgorithm

# Supported cryptographic algorithms
KeyAlgorithm.ECDSA_SECP256K1  # Bitcoin/Ethereum (default)
KeyAlgorithm.ECDSA_SECP256R1  # NIST P-256
KeyAlgorithm.RSA_2048
KeyAlgorithm.RSA_4096
KeyAlgorithm.ED25519          # EdDSA
```

### Error Handling

```python
from xai.mobile import (
    AuthenticationRequiredError,
    AuthenticationFailedError,
    WalletLockedError
)

try:
    private_key = bio_wallet.get_private_key()
except AuthenticationFailedError as e:
    print(f"Authentication failed: {e}")
except WalletLockedError as e:
    print(f"Wallet locked: {e}")
    # Wait for lockout to expire or unlock manually
```

## Platform Integration

### iOS Implementation

Replace `MockBiometricProvider` with iOS LocalAuthentication:

```python
# iOS biometric provider (Swift/Objective-C bridge)
import LocalAuthentication

class iOSBiometricProvider(BiometricAuthProvider):
    def __init__(self):
        self.context = LAContext()

    def authenticate(self, prompt_message, protection_level, timeout_seconds, allow_device_credential):
        policy = LAPolicy.deviceOwnerAuthenticationWithBiometrics
        if allow_device_credential:
            policy = LAPolicy.deviceOwnerAuthentication

        # Use LAContext.evaluatePolicy()
        result = self.context.evaluatePolicy(policy, localizedReason=prompt_message)

        if result.success:
            # Get biometric token
            token = self.context.evaluatedPolicyDomainState
            return BiometricResult(
                success=True,
                auth_type=self._get_biometry_type(),
                strength=BiometricStrength.STRONG,
                token=token
            )
        else:
            return BiometricResult(
                success=False,
                auth_type=BiometricType.NONE,
                strength=BiometricStrength.NONE,
                error_code=self._map_error(result.error)
            )
```

### Android Implementation

Replace `MockBiometricProvider` with Android BiometricPrompt:

```kotlin
// Android biometric provider (Kotlin)
class AndroidBiometricProvider : BiometricAuthProvider() {
    private lateinit var biometricPrompt: BiometricPrompt

    override fun authenticate(
        promptMessage: String,
        protectionLevel: ProtectionLevel,
        timeoutSeconds: Int,
        allowDeviceCredential: Boolean
    ): BiometricResult {
        val promptInfo = BiometricPrompt.PromptInfo.Builder()
            .setTitle("Authentication Required")
            .setSubtitle(promptMessage)
            .setAllowedAuthenticators(
                if (allowDeviceCredential)
                    BIOMETRIC_STRONG or DEVICE_CREDENTIAL
                else
                    BIOMETRIC_STRONG
            )
            .build()

        // Use BiometricPrompt.authenticate()
        val result = biometricPrompt.authenticate(promptInfo)

        if (result is BiometricPrompt.AuthenticationSucceeded) {
            val token = result.cryptoObject?.signature?.sign() ?: ByteArray(32)
            return BiometricResult(
                success = true,
                authType = BiometricType.FINGERPRINT,
                strength = BiometricStrength.STRONG,
                token = token
            )
        } else {
            return BiometricResult(
                success = false,
                authType = BiometricType.NONE,
                strength = BiometricStrength.NONE,
                errorCode = mapError(result)
            )
        }
    }
}
```

### React Native Bridge

```typescript
// React Native integration
import ReactNativeBiometrics from 'react-native-biometrics';

export class RNBiometricProvider implements BiometricAuthProvider {
    private rnBiometrics = new ReactNativeBiometrics();

    async authenticate(
        promptMessage: string,
        protectionLevel: ProtectionLevel,
        timeoutSeconds: number,
        allowDeviceCredential: boolean
    ): Promise<BiometricResult> {
        try {
            const result = await this.rnBiometrics.simplePrompt({
                promptMessage: promptMessage,
                cancelButtonText: 'Cancel'
            });

            if (result.success) {
                const token = await this.generateToken();
                return {
                    success: true,
                    authType: result.biometryType,
                    strength: 'strong',
                    token: token
                };
            } else {
                return {
                    success: false,
                    authType: 'none',
                    strength: 'none',
                    errorCode: 'authentication_failed'
                };
            }
        } catch (error) {
            return {
                success: false,
                authType: 'none',
                strength: 'none',
                errorCode: 'hardware_error',
                errorMessage: error.message
            };
        }
    }
}
```

## Security Considerations

### Best Practices

1. **Never store private keys in application memory**
   - Use secure enclave for key generation and signing
   - Private keys should never leave secure hardware

2. **Implement proper session management**
   - Use time-based and operation-based expiry
   - Invalidate sessions when app backgrounds
   - Require re-authentication for sensitive operations

3. **Configure appropriate protection levels**
   - Use BIOMETRIC_STRONG for high-value operations
   - Use transaction thresholds to balance security and UX
   - Enable audit logging for compliance

4. **Handle biometric changes**
   - Detect when biometrics are added/removed
   - Invalidate keys when biometric enrollment changes
   - Implement fallback authentication methods

5. **Rate limiting and lockout**
   - Implement exponential backoff on failures
   - Lock wallet after repeated failures
   - Log security events for monitoring

### Threat Model

This framework protects against:
- Unauthorized access to private keys
- Transaction signing without user consent
- Wallet export without authentication
- Replay attacks (time-based tokens)
- Brute force attacks (rate limiting)

Does NOT protect against:
- Compromised biometric data (hardware level)
- Rooted/jailbroken devices (use attestation)
- Malicious apps with accessibility permissions
- Physical device compromise

## Testing

Run the test suite:

```bash
# Unit tests
pytest tests/xai_tests/unit/test_biometric_auth.py -v

# Integration tests
python src/xai/mobile/example_biometric_usage.py
```

### Mock Providers

Use mock providers for testing:

```python
from xai.mobile import MockBiometricProvider, MockSecureEnclaveProvider

# Configure mock behavior
mock_bio = MockBiometricProvider()
mock_bio.set_fail_next(True)      # Simulate failure
mock_bio.set_enrolled(False)      # Simulate no biometrics
mock_bio.set_locked(True)         # Simulate lockout

mock_enclave = MockSecureEnclaveProvider()
mock_enclave.set_available(False)  # Simulate unavailable
```

## Performance

### Benchmarks (estimated)

| Operation | Time | Notes |
|-----------|------|-------|
| Biometric authentication | 0.5-2s | Platform dependent |
| Session token retrieval | <1ms | Cached in memory |
| Key generation (enclave) | 10-50ms | Hardware dependent |
| Transaction signing (enclave) | 10-30ms | Hardware dependent |
| Policy evaluation | <1ms | In-memory check |

### Optimization Tips

1. Enable session reuse for multiple operations
2. Adjust session timeout based on use case
3. Use appropriate protection levels (avoid over-authentication)
4. Cache biometric availability checks
5. Use background threads for non-blocking operations

## Troubleshooting

### Common Issues

**Issue**: Biometric authentication fails immediately
- Check device has biometrics enrolled
- Verify permissions in app manifest
- Check hardware availability

**Issue**: Session expires too quickly
- Increase `timeout_seconds` in SessionConfig
- Increase `max_operations` limit
- Reduce `require_reauth_on_sensitive`

**Issue**: Wallet locks too aggressively
- Increase `max_failed_attempts`
- Increase `lockout_duration_seconds`
- Check for proper error handling

**Issue**: Secure enclave unavailable
- Verify device supports secure hardware
- Check for rooted/jailbroken device
- Use software fallback if appropriate

## API Reference

See inline documentation in:
- `biometric_auth.py` - Authentication and session management
- `secure_enclave.py` - Hardware key storage and signing
- `biometric_wallet.py` - Wallet integration and policies

## Examples

Complete examples available in:
- `example_biometric_usage.py` - Comprehensive usage examples
- `tests/xai_tests/unit/test_biometric_auth.py` - Unit tests

## License

Part of the XAI blockchain project. See project LICENSE for details.

## Contributing

Follow XAI contribution guidelines. All changes must:
- Include comprehensive tests (>90% coverage)
- Pass security review
- Maintain backward compatibility
- Include documentation updates
