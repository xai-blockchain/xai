# XAI SDK for Flutter

Production-ready Flutter/Dart SDK for the XAI blockchain with biometric authentication and push notifications.

## Features

- **XAIClient** - HTTP/WebSocket client for blockchain communication
  - Automatic retries with exponential backoff
  - Connection pooling and timeout handling
  - Real-time updates via WebSocket
  - Comprehensive error handling

- **XAIWallet** - Secure wallet management
  - ECDSA key generation (secp256k1)
  - Secure storage with flutter_secure_storage
  - Import/export functionality
  - Multi-wallet support

- **XAITransaction** - Transaction building and signing
  - UTXO-based transaction model
  - Automatic nonce management
  - Balance validation
  - Transaction status tracking

- **BiometricAuth** - Biometric authentication
  - Face ID (iOS)
  - Touch ID (iOS)
  - Fingerprint (Android)
  - Transaction signing with biometrics

- **PushNotifications** - Firebase Cloud Messaging
  - Transaction notifications
  - Block notifications
  - Price alerts
  - Security alerts

## Installation

Add to your `pubspec.yaml`:

```yaml
dependencies:
  xai_sdk: ^1.0.0
```

Or install from path:

```yaml
dependencies:
  xai_sdk:
    path: ../xai/sdk/flutter
```

Then run:

```bash
flutter pub get
```

## Quick Start

### 1. Initialize the SDK

```dart
import 'package:xai_sdk/xai_sdk.dart';

// Create client
final client = XAIClient(
  config: XAIClientConfig(
    baseUrl: 'http://localhost:12001',
    wsUrl: 'ws://localhost:12003',
    timeout: Duration(seconds: 30),
    retryAttempts: 3,
  ),
);

// Initialize wallet service
final wallet = XAIWallet();

// Initialize transaction service
final txService = XAITransaction(
  client: client,
  wallet: wallet,
);
```

### 2. Create a Wallet

```dart
// Create new wallet
final myWallet = await wallet.createWallet(
  name: 'My Wallet',
  setAsDefault: true,
);

print('Address: ${myWallet.address}');
print('Public Key: ${myWallet.publicKey}');

// Import existing wallet
final importedWallet = await wallet.importWallet(
  privateKey: 'your_private_key_hex',
  name: 'Imported Wallet',
);
```

### 3. Check Balance

```dart
final balance = await client.getBalance(myWallet.address);
print('Balance: $balance XAI');
```

### 4. Send a Transaction

```dart
// Build, sign, and send in one step
final response = await txService.transferAndSend(
  senderAddress: myWallet.address,
  recipientAddress: 'XAI...',
  amount: 10.0,
  fee: 0.0001,
);

if (response.success) {
  print('Transaction sent: ${response.txid}');
} else {
  print('Error: ${response.error}');
}

// Or do it step by step for more control
final tx = await txService.buildTransfer(
  senderAddress: myWallet.address,
  recipientAddress: 'XAI...',
  amount: 10.0,
);

final signedTx = await txService.signTransactionByAddress(
  transaction: tx,
  address: myWallet.address,
);

final result = await txService.sendSignedTransaction(signedTx);
```

### 5. Get Transaction History

```dart
final history = await client.getHistory(
  myWallet.address,
  limit: 50,
  offset: 0,
);

for (final tx in history.transactions) {
  print('${tx.sender} -> ${tx.recipient}: ${tx.amount} XAI');
}
```

### 6. Real-time Updates with WebSocket

```dart
// Connect to WebSocket
await client.connectWebSocket();

// Listen for new transactions
client.transactionStream.listen((tx) {
  print('New transaction: ${tx.txid}');
});

// Listen for new blocks
client.blockStream.listen((block) {
  print('New block: ${block.index}');
});

// Listen for errors
client.errorStream.listen((error) {
  print('WebSocket error: $error');
});
```

### 7. Biometric Authentication

```dart
final biometric = BiometricAuth();

// Check availability
final available = await biometric.isAvailable();
if (available) {
  final types = await biometric.getAvailableBiometrics();
  print('Available biometrics: $types');
}

// Authenticate
final result = await biometric.authenticate(
  localizedReason: 'Authenticate to access wallet',
);

if (result.success) {
  print('Authenticated with ${result.biometricType}');
}

// Authenticate for transaction
final authenticated = await biometric.authenticateForTransaction(
  amount: 10.0,
  recipient: 'XAI...',
);

// Enable biometric for wallet
await wallet.enableBiometric(myWallet.id);
```

### 8. Push Notifications

```dart
final notifications = PushNotifications();

// Initialize (must be called before use)
await notifications.initialize();

// Get FCM token
final token = notifications.currentToken;
print('FCM Token: $token');

// Subscribe to address notifications
await notifications.subscribeToAddress(myWallet.address);

// Listen for notifications
notifications.notificationStream.listen((notification) {
  print('${notification.title}: ${notification.body}');
});

// Subscribe to topics
await notifications.subscribeToBlocks();
await notifications.subscribeToPriceAlerts();
await notifications.subscribeToSecurityAlerts();
```

## Advanced Usage

### UTXO Transactions

```dart
// Build transaction with specific inputs and outputs
final tx = await txService.buildUTXOTransaction(
  senderAddress: myWallet.address,
  inputs: [
    TransactionInput(
      txid: 'previous_tx_id',
      vout: 0,
      amount: 5.0,
    ),
  ],
  outputs: [
    TransactionOutput(
      address: 'recipient_address',
      amount: 4.0,
    ),
    TransactionOutput(
      address: myWallet.address, // Change output
      amount: 0.9999,
    ),
  ],
  fee: 0.0001,
);

final signedTx = await txService.signTransactionByAddress(
  transaction: tx,
  address: myWallet.address,
);

await txService.sendSignedTransaction(signedTx);
```

### Transaction Validation

```dart
// Validate before sending
final errors = await txService.validateTransaction(signedTx);

if (errors.isEmpty) {
  await txService.sendSignedTransaction(signedTx);
} else {
  print('Validation errors: $errors');
}
```

### Wait for Confirmation

```dart
final response = await txService.sendSignedTransaction(signedTx);

if (response.success) {
  // Wait for 3 confirmations
  final confirmedTx = await txService.waitForConfirmation(
    txid: response.txid!,
    requiredConfirmations: 3,
    timeout: Duration(minutes: 10),
  );

  if (confirmedTx != null) {
    print('Transaction confirmed with ${confirmedTx.confirmations} confirmations');
  }
}
```

### Wallet Management

```dart
// Get all wallets
final wallets = await wallet.getWallets();

// Get default wallet
final defaultWallet = await wallet.getDefaultWallet();

// Set default wallet
await wallet.setDefaultWallet(walletId);

// Update wallet
final updatedWallet = myWallet.copyWith(name: 'New Name');
await wallet.updateWallet(updatedWallet);

// Export wallet (includes private key!)
final exported = await wallet.exportWallet(myWallet.id);
print('Private key: ${exported['privateKey']}');

// Delete wallet
await wallet.deleteWallet(myWallet.id);
```

### Custom Crypto Operations

```dart
import 'package:xai_sdk/xai_sdk.dart';

// Generate key pair
final keyPair = CryptoUtils.generateKeyPair();
print('Private key: ${keyPair['privateKey']}');
print('Public key: ${keyPair['publicKey']}');

// Derive public key from private key
final publicKey = CryptoUtils.derivePublicKey(privateKey);

// Generate address from public key
final address = CryptoUtils.publicKeyToAddress(publicKey);

// Sign message
final signature = CryptoUtils.signMessage(message, privateKey);

// Verify signature
final isValid = CryptoUtils.verifySignature(message, signature, publicKey);

// Validate address
final valid = CryptoUtils.isValidAddress('XAI...');
```

## Configuration

### Firebase Setup (for Push Notifications)

1. Add Firebase to your Flutter app:
   - [iOS Setup](https://firebase.google.com/docs/flutter/setup?platform=ios)
   - [Android Setup](https://firebase.google.com/docs/flutter/setup?platform=android)

2. Add configuration files:
   - iOS: `ios/Runner/GoogleService-Info.plist`
   - Android: `android/app/google-services.json`

3. Initialize Firebase in your app:

```dart
import 'package:firebase_core/firebase_core.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Firebase.initializeApp();
  runApp(MyApp());
}
```

### Platform-Specific Configuration

#### iOS

Add to `ios/Runner/Info.plist`:

```xml
<key>NSFaceIDUsageDescription</key>
<string>Authenticate to access your XAI wallet</string>
```

#### Android

Add to `android/app/src/main/AndroidManifest.xml`:

```xml
<uses-permission android:name="android.permission.USE_BIOMETRIC"/>
<uses-permission android:name="android.permission.INTERNET"/>
```

## API Reference

### XAIClient

```dart
// Node information
Future<NodeInfo> getNodeInfo()

// Balance
Future<double> getBalance(String address)

// Nonce
Future<NonceResponse> getNonce(String address)

// Transaction history
Future<TransactionHistory> getHistory(String address, {int limit, int offset})

// Get transaction
Future<Transaction?> getTransaction(String txid)

// Pending transactions
Future<List<Transaction>> getPendingTransactions({int limit, int offset})

// Send transaction
Future<SendTransactionResponse> sendTransaction(Transaction tx)

// Blocks
Future<Block?> getBlock(int index)
Future<Block?> getLatestBlock()
Future<List<Block>> getBlocks({int limit, int offset})

// Chain stats
Future<ChainStats?> getChainStats()

// WebSocket
Future<void> connectWebSocket()
Future<void> disconnectWebSocket()

// Streams
Stream<Block> get blockStream
Stream<Transaction> get transactionStream
Stream<String> get errorStream
```

### XAIWallet

```dart
// Create wallet
Future<Wallet> createWallet({String? name, bool setAsDefault})

// Import wallet
Future<Wallet> importWallet({required String privateKey, String? name, bool setAsDefault})

// Get wallets
Future<List<Wallet>> getWallets()
Future<Wallet?> getWallet(String walletId)
Future<Wallet?> getWalletByAddress(String address)
Future<Wallet?> getDefaultWallet()

// Manage wallets
Future<void> setDefaultWallet(String walletId)
Future<Wallet> updateWallet(Wallet wallet)
Future<void> deleteWallet(String walletId)

// Keys
Future<String?> getPrivateKey(String walletId)
Future<WalletKeyPair?> getKeyPair(String walletId)

// Export/Import
Future<Map<String, dynamic>> exportWallet(String walletId)

// Biometric
Future<Wallet> enableBiometric(String walletId)
Future<Wallet> disableBiometric(String walletId)

// Cleanup
Future<void> clearAllWallets()
```

### XAITransaction

```dart
// Build transactions
Future<Transaction> buildTransfer({...})
Future<Transaction> buildUTXOTransaction({...})

// Sign transactions
Future<Transaction> signTransaction({required Transaction transaction, required String walletId})
Future<Transaction> signTransactionByAddress({required Transaction transaction, required String address})

// Send transactions
Future<SendTransactionResponse> sendSignedTransaction(Transaction transaction)

// Convenience methods
Future<Transaction> buildAndSignTransfer({...})
Future<SendTransactionResponse> transferAndSend({...})

// Utilities
bool verifySignature(Transaction transaction)
Future<double> estimateFee({int inputCount, int outputCount, int? metadataSize})
Future<double> getRecommendedFee()
Future<Transaction?> waitForConfirmation({required String txid, int requiredConfirmations, Duration timeout})
Future<List<String>> validateTransaction(Transaction transaction)
```

### BiometricAuth

```dart
// Availability
Future<bool> isAvailable()
Future<List<BiometricType>> getAvailableBiometrics()
Future<BiometricCapability> getCapability()

// Check specific types
Future<bool> isFaceIdAvailable()
Future<bool> isTouchIdAvailable()
Future<bool> isFingerprintAvailable()

// Authenticate
Future<BiometricAuthResult> authenticate({required String localizedReason, bool useErrorDialogs, bool stickyAuth})
Future<bool> authenticateForTransaction({required double amount, required String recipient})
Future<bool> authenticateForWalletAccess({String? walletName})
Future<bool> authenticateForKeyExport()

// Control
Future<void> stopAuthentication()
```

### PushNotifications

```dart
// Initialize
Future<void> initialize()

// Token management
String? get currentToken
Stream<String> get tokenStream
Future<void> deleteToken()

// Subscriptions
Future<void> subscribeToAddress(String address)
Future<void> unsubscribeFromAddress(String address)
Future<void> subscribeToBlocks()
Future<void> unsubscribeFromBlocks()
Future<void> subscribeToPriceAlerts()
Future<void> subscribeToSecurityAlerts()

// Permissions
Future<AuthorizationStatus> getPermissionStatus()
Future<bool> requestPermissions()
Future<bool> areNotificationsEnabled()

// Notifications
Stream<NotificationMessage> get notificationStream
Future<void> clearAllNotifications()
Future<void> clearNotification(int id)

// Cleanup
void dispose()
```

## Error Handling

```dart
try {
  final tx = await txService.transferAndSend(...);
} on CryptoException catch (e) {
  print('Crypto error: $e');
} on Exception catch (e) {
  print('Error: $e');
}
```

## Security Best Practices

1. **Never expose private keys** - They are stored securely in flutter_secure_storage
2. **Enable biometric authentication** for sensitive operations
3. **Validate addresses** before sending transactions
4. **Use HTTPS/WSS** for production node connections
5. **Implement rate limiting** on your backend
6. **Keep the SDK updated** to get security patches

## Testing

Run tests:

```bash
flutter test
```

## Example App

See the `example/` directory for a complete working app demonstrating all SDK features.

To run the example:

```bash
cd example
flutter run
```

## Platform Support

- iOS 12.0+
- Android API 23+ (Android 6.0+)
- Web (partial support, no biometrics or push notifications)

## License

MIT

## Support

- GitHub: https://github.com/xai-blockchain/xai
- Issues: https://github.com/xai-blockchain/xai/issues
- Documentation: https://xai-blockchain.io/docs

## Contributing

Contributions are welcome! Please read our contributing guidelines before submitting PRs.
