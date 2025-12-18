# XAI Biometric Authentication Framework

Secure, cross-platform biometric authentication for XAI mobile wallets and SDKs.

## Overview

This framework provides a unified interface for biometric authentication across iOS, Android, and React Native platforms. It enables secure wallet key storage protected by device biometrics (Face ID, Touch ID, fingerprint).

**Security Features:**
- Device-bound encryption keys
- Biometric-protected key access
- Strong key derivation (PBKDF2 600k iterations)
- No plaintext key storage
- Platform keychain/keystore integration

## Architecture

```
┌─────────────────────────────────────┐
│  Mobile App (React Native/iOS/Android) │
└────────────────┬────────────────────┘
                 │
    ┌────────────▼────────────┐
    │  Biometric Auth Layer   │
    │  (biometric_auth.py)    │
    └────────────┬────────────┘
                 │
    ┌────────────▼─────────────────┐
    │  Key Derivation Layer        │
    │  (secure_key_derivation.py)  │
    └────────────┬─────────────────┘
                 │
    ┌────────────▼────────────────┐
    │  Platform Native APIs       │
    │  iOS: LAContext/Keychain    │
    │  Android: BiometricPrompt/  │
    │           KeyStore          │
    └─────────────────────────────┘
```

## Quick Start

### React Native

```bash
npm install react-native-biometrics
cd ios && pod install
```

```typescript
import { biometricAuth } from './sdk/biometric/react-native-integration';

// Check availability
const capability = await biometricAuth.isAvailable();
if (!capability.available) {
  console.log('Biometrics not available');
  return;
}

// Authenticate
const result = await biometricAuth.authenticate({
  promptMessage: 'Authenticate to access your wallet',
  cancelButtonText: 'Cancel',
  fallbackToPasscode: true,
});

if (result.success) {
  // Access wallet
  console.log('Authenticated with', result.biometricType);
}
```

### iOS (Swift)

```swift
import LocalAuthentication

class BiometricAuthProvider {
    func authenticate(completion: @escaping (Bool, Error?) -> Void) {
        let context = LAContext()
        var error: NSError?

        guard context.canEvaluatePolicy(.deviceOwnerAuthenticationWithBiometrics, error: &error) else {
            completion(false, error)
            return
        }

        context.evaluatePolicy(
            .deviceOwnerAuthenticationWithBiometrics,
            localizedReason: "Authenticate to access your wallet"
        ) { success, error in
            completion(success, error)
        }
    }

    func getBiometricType() -> BiometricType {
        let context = LAContext()

        switch context.biometryType {
        case .faceID:
            return .FACE_ID
        case .touchID:
            return .TOUCH_ID
        default:
            return .NONE
        }
    }
}
```

**iOS Setup (Info.plist):**
```xml
<key>NSFaceIDUsageDescription</key>
<string>We use Face ID to secure your wallet and authenticate transactions</string>
```

### Android (Kotlin)

```kotlin
import androidx.biometric.BiometricManager
import androidx.biometric.BiometricPrompt
import androidx.fragment.app.FragmentActivity

class BiometricAuthProvider(private val activity: FragmentActivity) {

    fun isAvailable(): BiometricCapability {
        val biometricManager = BiometricManager.from(activity)

        return when (biometricManager.canAuthenticate(
            BiometricManager.Authenticators.BIOMETRIC_STRONG
        )) {
            BiometricManager.BIOMETRIC_SUCCESS ->
                BiometricCapability(available = true, securityLevel = "strong")
            BiometricManager.BIOMETRIC_ERROR_NO_HARDWARE ->
                BiometricCapability(available = false, hardwareDetected = false)
            BiometricManager.BIOMETRIC_ERROR_NONE_ENROLLED ->
                BiometricCapability(available = false, enrolled = false)
            else ->
                BiometricCapability(available = false)
        }
    }

    fun authenticate(
        promptMessage: String,
        callback: (BiometricResult) -> Unit
    ) {
        val executor = ContextCompat.getMainExecutor(activity)
        val biometricPrompt = BiometricPrompt(
            activity,
            executor,
            object : BiometricPrompt.AuthenticationCallback() {
                override fun onAuthenticationSucceeded(
                    result: BiometricPrompt.AuthenticationResult
                ) {
                    callback(BiometricResult(success = true))
                }

                override fun onAuthenticationFailed() {
                    callback(BiometricResult(
                        success = false,
                        errorCode = BiometricError.AUTHENTICATION_FAILED
                    ))
                }

                override fun onAuthenticationError(
                    errorCode: Int,
                    errString: CharSequence
                ) {
                    callback(BiometricResult(
                        success = false,
                        errorCode = mapErrorCode(errorCode),
                        errorMessage = errString.toString()
                    ))
                }
            }
        )

        val promptInfo = BiometricPrompt.PromptInfo.Builder()
            .setTitle(promptMessage)
            .setNegativeButtonText("Cancel")
            .setAllowedAuthenticators(
                BiometricManager.Authenticators.BIOMETRIC_STRONG
            )
            .build()

        biometricPrompt.authenticate(promptInfo)
    }
}
```

**Android Setup (AndroidManifest.xml):**
```xml
<uses-permission android:name="android.permission.USE_BIOMETRIC" />
```

## Secure Wallet Key Storage

### Flow

1. **Initial Setup (App Install)**
   ```
   User creates wallet → Generate private key →
   Prompt biometric enrollment → Derive encryption key →
   Encrypt private key → Store in secure storage
   ```

2. **Transaction Signing**
   ```
   User initiates transaction → Prompt biometric auth →
   Derive decryption key → Decrypt private key →
   Sign transaction → Clear key from memory
   ```

### Python Implementation

```python
from xai.sdk.biometric.secure_key_derivation import SecureKeyDerivation
from xai.sdk.biometric.biometric_auth import BiometricAuthProvider

# Initialize with device ID
device_id = get_device_identifier()  # Platform-specific
kdf = SecureKeyDerivation(device_id)

# After successful biometric authentication
biometric_token = auth_provider.get_biometric_token()  # Platform-specific

# Encrypt wallet private key
encrypted = kdf.encrypt_wallet_key(
    wallet_private_key=private_key_bytes,
    biometric_token=biometric_token,
    wallet_id=wallet_address
)

# Store encrypted.ciphertext, encrypted.iv, encrypted.salt in secure storage

# Later: Decrypt to sign transaction
biometric_token = auth_provider.authenticate()  # Re-authenticate
private_key = kdf.decrypt_wallet_key(
    encrypted=encrypted,
    biometric_token=biometric_token,
    wallet_id=wallet_address
)
# Use private_key to sign transaction
# Clear private_key from memory immediately after use
```

### TypeScript/React Native

```typescript
import { SecureKeyDerivation } from './secure_key_derivation';
import { biometricAuth } from './react-native-integration';

// Encrypt wallet key
const authResult = await biometricAuth.authenticate({
  promptMessage: 'Secure your wallet',
  cancelButtonText: 'Cancel',
  fallbackToPasscode: false,
});

if (authResult.success) {
  const encrypted = await biometricAuth.storeSecure(
    walletPrivateKey,
    {
      keyAlias: `wallet_${walletId}`,
      requireBiometric: true,
      invalidateOnEnrollment: true,
    }
  );

  // Store encrypted data in AsyncStorage or SecureStore
  await SecureStore.setItemAsync('wallet_encrypted', JSON.stringify(encrypted));
}

// Decrypt wallet key for transaction
const encryptedData = JSON.parse(
  await SecureStore.getItemAsync('wallet_encrypted')
);

const privateKey = await biometricAuth.retrieveSecure(
  encryptedData,
  {
    promptMessage: 'Sign transaction',
    cancelButtonText: 'Cancel',
    fallbackToPasscode: false,
  }
);

if (privateKey) {
  // Sign transaction
  const signature = await signTransaction(privateKey, transaction);
  // Clear from memory
}
```

## Security Best Practices

### Key Derivation

- **Iterations**: Minimum 100,000, recommended 600,000 PBKDF2 iterations
- **Salt**: Unique 32-byte random salt per wallet
- **Device Binding**: Include device ID in key derivation
- **Context**: Include wallet ID for key separation

### Biometric Tokens

- **Never store**: Biometric tokens must be ephemeral
- **Platform-specific**: Use native APIs only
  - iOS: `LAContext.evaluatedPolicyDomainState`
  - Android: `BiometricPrompt.CryptoObject` signature
- **Validity**: Tokens should be short-lived (max 60 seconds)

### Key Storage

- **No plaintext**: Never store private keys unencrypted
- **Platform keychain**: Use native secure storage
  - iOS: Keychain Services (`kSecAttrAccessControlUserPresence`)
  - Android: Android KeyStore (hardware-backed when available)
- **Invalidation**: Invalidate keys when biometrics change

### Error Handling

- **Lockout**: Respect biometric lockout (too many failures)
- **Fallback**: Provide PIN/password fallback option
- **User cancel**: Handle gracefully, don't force authentication
- **Hardware failure**: Detect and inform user

## Platform-Specific Notes

### iOS

**Biometric Types:**
- Face ID (iPhone X+)
- Touch ID (iPhone 5s - iPhone 8, iPad)

**APIs:**
- `LocalAuthentication.framework` for authentication
- `Security.framework` for keychain storage

**Requirements:**
- iOS 11.0+ for Face ID
- iOS 8.0+ for Touch ID
- Keychain access groups for app groups

**Best Practices:**
- Use `kSecAttrAccessControlBiometryCurrentSet` to invalidate on biometric change
- Handle biometry change notifications
- Test on device (not simulator) for Face ID

### Android

**Biometric Types:**
- Fingerprint (Android 6.0+)
- Face unlock (varies by manufacturer)
- Iris scanner (Samsung, limited)

**APIs:**
- `BiometricPrompt` (Android 9.0+, recommended)
- `FingerprintManager` (deprecated, Android 6.0-8.1)
- `KeyStore` for key storage

**Requirements:**
- Android 6.0+ (API 23+)
- `USE_BIOMETRIC` permission
- Device must have biometric hardware

**Best Practices:**
- Use `BIOMETRIC_STRONG` authenticator for crypto operations
- Check `KeyInfo.isInsideSecureHardware()` for hardware-backed keys
- Handle `BIOMETRIC_ERROR_HW_UNAVAILABLE` gracefully

### React Native

**Library:** `react-native-biometrics` (recommended)

**Cross-platform considerations:**
- iOS and Android have different capabilities
- Abstract platform differences in wrapper
- Test on both platforms thoroughly

**Alternatives:**
- `expo-local-authentication` (Expo apps)
- `react-native-touch-id` (iOS only, deprecated)

## Testing

### Mock Provider

```python
from xai.sdk.biometric.biometric_auth import MockBiometricProvider

# Create mock provider
provider = MockBiometricProvider(simulate_type=BiometricType.FACE_ID)

# Test authentication flow
result = provider.authenticate()
assert result.success

# Simulate failure
provider.set_fail_next()
result = provider.authenticate()
assert not result.success
```

### Platform Testing

**iOS Simulator:**
- Face ID: Hardware → Face ID → Enrolled
- Touch ID: Hardware → Touch ID → Enrolled
- Trigger success: Hardware → Toggle Enrolled

**Android Emulator:**
- Settings → Security → Fingerprint
- `adb -e emu finger touch 1` to simulate fingerprint

## API Reference

See individual files for detailed API documentation:
- `biometric_auth.py` - Core authentication interfaces
- `secure_key_derivation.py` - Key derivation and encryption
- `types.ts` - TypeScript type definitions
- `react-native-integration.ts` - React Native implementation

## Migration Guide

### From PIN/Password to Biometric

```typescript
// 1. Check if biometrics available
const capability = await biometricAuth.isAvailable();
if (!capability.available) {
  // Keep using PIN/password
  return;
}

// 2. Offer biometric enrollment
const userWants = await showBiometricEnrollmentPrompt();
if (!userWants) return;

// 3. Authenticate with old method (PIN)
const pinValid = await verifyPIN(userPin);
if (!pinValid) return;

// 4. Load wallet key (decrypted with PIN)
const privateKey = await loadPrivateKeyWithPIN(userPin);

// 5. Re-encrypt with biometric
const authResult = await biometricAuth.authenticate({
  promptMessage: 'Enable biometric authentication',
  cancelButtonText: 'Cancel',
  fallbackToPasscode: false,
});

if (authResult.success) {
  const encrypted = await biometricAuth.storeSecure(
    privateKey,
    { keyAlias: `wallet_${walletId}`, requireBiometric: true }
  );

  // Store new encrypted key
  await SecureStore.setItemAsync('wallet_key', JSON.stringify(encrypted));

  // Remove old PIN-encrypted key
  await removePINEncryptedKey();
}
```

## Troubleshooting

**Biometrics not available**
- Check device has biometric hardware
- Verify user has enrolled biometrics
- Check permissions (Android)
- Check Info.plist usage description (iOS)

**Authentication fails**
- User may be locked out (too many attempts)
- Biometric settings changed
- Hardware malfunction
- Provide fallback option

**Decryption fails**
- Device ID mismatch (app reinstalled or transferred)
- Biometric enrollment changed (keys invalidated)
- Corrupted encrypted data
- Prompt for account recovery

## License

MIT License - See LICENSE file in project root
