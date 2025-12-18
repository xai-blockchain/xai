# Biometric Authentication Quick Start

Get started with XAI biometric authentication in under 5 minutes.

## Python (Testing & Reference)

```python
from xai.sdk.biometric import (
    SecureKeyDerivation,
    MockBiometricProvider,
    BiometricType
)

# 1. Initialize
device_id = "your-device-id"
kdf = SecureKeyDerivation(device_id)
provider = MockBiometricProvider(BiometricType.FACE_ID)

# 2. Check availability
capability = provider.is_available()
if not capability.available:
    print("Biometrics not available")
    exit()

# 3. Authenticate
result = provider.authenticate(
    prompt_message="Authenticate to secure your wallet",
    cancel_button_text="Cancel"
)

if not result.success:
    print(f"Authentication failed: {result.error_message}")
    exit()

# 4. Encrypt wallet key
wallet_key = b"your_32_byte_private_key_here!!"
biometric_token = SecureKeyDerivation.generate_biometric_token_mock()

encrypted = kdf.encrypt_wallet_key(
    wallet_private_key=wallet_key,
    biometric_token=biometric_token,
    wallet_id="0x1234..."
)

# Store encrypted.ciphertext, encrypted.iv, encrypted.salt

# 5. Later: decrypt for transaction
decrypted = kdf.decrypt_wallet_key(
    encrypted=encrypted,
    biometric_token=biometric_token,
    wallet_id="0x1234..."
)

# Use decrypted key to sign transaction
```

## React Native

```typescript
import { biometricAuth } from '@xai/biometric-sdk';

// 1. Check availability
const capability = await biometricAuth.isAvailable();
if (!capability.available) {
  Alert.alert('Biometrics not available');
  return;
}

// 2. Authenticate and secure wallet
const result = await biometricAuth.authenticate({
  promptMessage: 'Authenticate to secure your wallet',
  cancelButtonText: 'Cancel',
  fallbackToPasscode: true,
});

if (!result.success) {
  Alert.alert('Authentication Failed', result.errorMessage);
  return;
}

// 3. Store encrypted wallet key
const encrypted = await biometricAuth.storeSecure(
  walletPrivateKey,
  {
    keyAlias: `wallet_${walletId}`,
    requireBiometric: true,
    invalidateOnEnrollment: true,
  }
);

// Save encrypted data to secure storage
await SecureStore.setItemAsync('wallet_key', JSON.stringify(encrypted));

// 4. Later: retrieve for transaction
const encryptedData = JSON.parse(
  await SecureStore.getItemAsync('wallet_key')
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
}
```

## iOS (Swift)

```swift
import LocalAuthentication

class BiometricManager {
    func authenticateAndSecureWallet(privateKey: Data, completion: @escaping (Bool) -> Void) {
        let context = LAContext()
        var error: NSError?

        guard context.canEvaluatePolicy(.deviceOwnerAuthenticationWithBiometrics, error: &error) else {
            print("Biometrics not available: \(error?.localizedDescription ?? "unknown")")
            completion(false)
            return
        }

        context.evaluatePolicy(
            .deviceOwnerAuthenticationWithBiometrics,
            localizedReason: "Authenticate to secure your wallet"
        ) { success, error in
            if success {
                // Store private key in keychain with biometric access control
                self.storeInKeychain(privateKey)
                completion(true)
            } else {
                print("Authentication failed: \(error?.localizedDescription ?? "unknown")")
                completion(false)
            }
        }
    }

    private func storeInKeychain(_ data: Data) {
        let access = SecAccessControlCreateWithFlags(
            nil,
            kSecAttrAccessibleWhenUnlockedThisDeviceOnly,
            .biometryCurrentSet,
            nil
        )

        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrAccount as String: "wallet_private_key",
            kSecValueData as String: data,
            kSecAttrAccessControl as String: access as Any
        ]

        SecItemAdd(query as CFDictionary, nil)
    }

    func retrieveFromKeychain(completion: @escaping (Data?) -> Void) {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrAccount as String: "wallet_private_key",
            kSecReturnData as String: true,
            kSecUseOperationPrompt as String: "Sign transaction"
        ]

        var item: CFTypeRef?
        let status = SecItemCopyMatching(query as CFDictionary, &item)

        if status == errSecSuccess, let data = item as? Data {
            completion(data)
        } else {
            completion(nil)
        }
    }
}
```

## Android (Kotlin)

```kotlin
import androidx.biometric.BiometricPrompt
import androidx.core.content.ContextCompat

class BiometricManager(private val activity: FragmentActivity) {

    fun authenticateAndSecureWallet(privateKey: ByteArray, callback: (Boolean) -> Unit) {
        val executor = ContextCompat.getMainExecutor(activity)

        val biometricPrompt = BiometricPrompt(
            activity,
            executor,
            object : BiometricPrompt.AuthenticationCallback() {
                override fun onAuthenticationSucceeded(result: BiometricPrompt.AuthenticationResult) {
                    // Store private key in KeyStore
                    storeInKeyStore(privateKey)
                    callback(true)
                }

                override fun onAuthenticationError(errorCode: Int, errString: CharSequence) {
                    Log.e("Biometric", "Authentication error: $errString")
                    callback(false)
                }

                override fun onAuthenticationFailed() {
                    Log.e("Biometric", "Authentication failed")
                    callback(false)
                }
            }
        )

        val promptInfo = BiometricPrompt.PromptInfo.Builder()
            .setTitle("Authenticate")
            .setSubtitle("Secure your wallet")
            .setNegativeButtonText("Cancel")
            .setAllowedAuthenticators(BiometricManager.Authenticators.BIOMETRIC_STRONG)
            .build()

        biometricPrompt.authenticate(promptInfo)
    }

    private fun storeInKeyStore(privateKey: ByteArray) {
        val keyStore = KeyStore.getInstance("AndroidKeyStore")
        keyStore.load(null)

        val keyGenerator = KeyGenerator.getInstance(
            KeyProperties.KEY_ALGORITHM_AES,
            "AndroidKeyStore"
        )

        val keyGenParameterSpec = KeyGenParameterSpec.Builder(
            "wallet_key",
            KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT
        )
            .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
            .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
            .setUserAuthenticationRequired(true)
            .setUserAuthenticationValidityDurationSeconds(30)
            .build()

        keyGenerator.init(keyGenParameterSpec)
        keyGenerator.generateKey()

        // Encrypt and store private key
        // ... (implementation details)
    }
}
```

## Common Patterns

### Pattern 1: First-Time Wallet Setup

```python
# Check availability → Authenticate → Encrypt → Store
capability = provider.is_available()
if capability.available:
    result = provider.authenticate()
    if result.success:
        encrypted = kdf.encrypt_wallet_key(private_key, token, wallet_id)
        store_encrypted_data(encrypted)
```

### Pattern 2: Transaction Signing

```python
# Authenticate → Decrypt → Sign → Clear memory
result = provider.authenticate(prompt_message="Sign transaction")
if result.success:
    private_key = kdf.decrypt_wallet_key(encrypted, token, wallet_id)
    signature = sign_transaction(private_key, transaction)
    del private_key  # Clear from memory immediately
```

### Pattern 3: Multiple Quick Transactions

```python
# Use token cache to avoid repeated prompts
cache = BiometricTokenCache(validity_seconds=60)

# First transaction
result = provider.authenticate()
cache.store(wallet_id, token)

# Subsequent transactions (within 60s)
cached_token = cache.retrieve(wallet_id)
if cached_token:
    # Use cached token, no new prompt needed
    private_key = kdf.decrypt_wallet_key(encrypted, cached_token, wallet_id)
```

### Pattern 4: Error Handling

```python
result = provider.authenticate()
if not result.success:
    if result.error_code == BiometricError.USER_CANCEL:
        # User cancelled - allow retry
        show_retry_button()
    elif result.error_code == BiometricError.LOCKOUT:
        # Too many attempts - suggest passcode
        suggest_passcode_fallback()
    elif result.error_code == BiometricError.NOT_ENROLLED:
        # No biometrics - use PIN/password instead
        fallback_to_pin_authentication()
```

## Testing

Run the included example:

```bash
python3 src/xai/sdk/biometric/example_usage.py
```

Run tests:

```bash
pytest src/xai/sdk/biometric/test_biometric_auth.py -v
```

## Next Steps

1. Read the full [README.md](./README.md) for comprehensive documentation
2. Review [example_usage.py](./example_usage.py) for complete implementation
3. Check [IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md) for architecture details
4. Integrate into your mobile app using platform-specific code

## Support

For questions or issues:
- Check the [README.md](./README.md) troubleshooting section
- Review test cases in [test_biometric_auth.py](./test_biometric_auth.py)
- Examine the example implementation in [example_usage.py](./example_usage.py)
