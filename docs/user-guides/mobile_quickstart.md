# XAI Mobile Quick Start Guide

Build mobile wallets and dApps for XAI blockchain using React Native or Flutter SDKs. This guide covers setup, basic operations, and biometric authentication.

---

## Overview

XAI provides production-ready SDKs for mobile development:

- **React Native SDK** - TypeScript/JavaScript for iOS and Android
- **Flutter SDK** - Dart for cross-platform development
- **Biometric Authentication** - Face ID, Touch ID, Fingerprint support
- **Offline Signing** - Sign transactions without network connection
- **Push Notifications** - Real-time transaction alerts

---

## Prerequisites

**React Native:**
- Node.js >= 18
- npm >= 9
- React Native CLI or Expo
- Xcode (for iOS) or Android Studio (for Android)

**Flutter:**
- Flutter SDK >= 3.0
- Dart SDK >= 2.18
- Xcode (for iOS) or Android Studio (for Android)

---

## React Native SDK Setup

### Installation

```bash
# Create new React Native project (or use existing)
npx react-native init XAIWallet
cd XAIWallet

# Install XAI SDK
npm install @xai/sdk

# Install dependencies
npm install @xai/biometric-sdk
npm install react-native-keychain
npm install react-native-biometrics
npm install axios
```

### iOS Setup

```bash
cd ios
pod install
cd ..
```

Add permissions to `ios/XAIWallet/Info.plist`:

```xml
<key>NSFaceIDUsageDescription</key>
<string>Use Face ID to secure your wallet</string>
<key>NSCameraUsageDescription</key>
<string>Scan QR codes for transactions</string>
```

### Android Setup

Add permissions to `android/app/src/main/AndroidManifest.xml`:

```xml
<uses-permission android:name="android.permission.USE_BIOMETRIC" />
<uses-permission android:name="android.permission.CAMERA" />
<uses-permission android:name="android.permission.INTERNET" />
```

### Basic Usage

```typescript
import { XAIClient } from '@xai/sdk';
import { biometricAuth } from '@xai/biometric-sdk';

// Initialize client
const client = new XAIClient({
  baseUrl: 'https://testnet-rpc.xai.network',
  network: 'testnet',
});

// Create wallet
const wallet = await client.wallet.create();
console.log('Address:', wallet.address);

// Secure private key with biometrics
const encrypted = await biometricAuth.storeSecure(
  wallet.privateKey,
  {
    keyAlias: `wallet_${wallet.address}`,
    requireBiometric: true,
  }
);

// Get balance
const balance = await client.wallet.getBalance(wallet.address);
console.log('Balance:', balance.balance);

// Send transaction with biometric auth
const privateKey = await biometricAuth.retrieveSecure(encrypted, {
  promptMessage: 'Sign transaction',
});

const tx = await client.transaction.send({
  from: wallet.address,
  to: recipientAddress,
  amount: '10.0',
  privateKey,
});

console.log('Transaction hash:', tx.hash);
```

---

## Flutter SDK Setup

### Installation

Add to `pubspec.yaml`:

```yaml
dependencies:
  xai_sdk: ^1.0.0
  local_auth: ^2.1.0
  flutter_secure_storage: ^8.0.0
  qr_code_scanner: ^1.0.1
```

Install dependencies:

```bash
flutter pub get
```

### iOS Configuration

Add to `ios/Runner/Info.plist`:

```xml
<key>NSFaceIDUsageDescription</key>
<string>Use Face ID to secure your wallet</string>
<key>NSCameraUsageDescription</key>
<string>Scan QR codes for transactions</string>
```

### Android Configuration

Add to `android/app/src/main/AndroidManifest.xml`:

```xml
<uses-permission android:name="android.permission.USE_BIOMETRIC"/>
<uses-permission android:name="android.permission.CAMERA"/>
```

Update `android/app/build.gradle`:

```gradle
android {
    compileSdkVersion 33
    minSdkVersion 23  // Biometric requires API 23+
}
```

### Basic Usage

```dart
import 'package:xai_sdk/xai_sdk.dart';
import 'package:local_auth/local_auth.dart';

// Initialize client
final client = XAIClient(
  baseUrl: 'https://testnet-rpc.xai.network',
  network: Network.testnet,
);

// Create wallet
final wallet = await client.wallet.create();
print('Address: ${wallet.address}');

// Check biometric availability
final localAuth = LocalAuthentication();
final canAuthenticate = await localAuth.canCheckBiometrics;

if (canAuthenticate) {
  // Authenticate user
  final didAuthenticate = await localAuth.authenticate(
    localizedReason: 'Secure your wallet',
    options: AuthenticationOptions(biometricOnly: true),
  );

  if (didAuthenticate) {
    // Store private key securely
    await wallet.storeSecure();
  }
}

// Get balance
final balance = await client.wallet.getBalance(wallet.address);
print('Balance: ${balance.balance}');

// Send transaction
final tx = await client.transaction.send(
  from: wallet.address,
  to: recipientAddress,
  amount: '10.0',
);

print('Transaction: ${tx.hash}');
```

---

## Biometric Authentication

### React Native Implementation

```typescript
import { biometricAuth, BiometricType } from '@xai/biometric-sdk';

// Check availability
const capability = await biometricAuth.isAvailable();

if (!capability.available) {
  Alert.alert('Biometrics not available');
  return;
}

console.log('Type:', capability.biometricType); // FACE_ID, TOUCH_ID, or FINGERPRINT

// Authenticate and secure wallet
const result = await biometricAuth.authenticate({
  promptMessage: 'Authenticate to secure your wallet',
  cancelButtonText: 'Cancel',
  fallbackToPasscode: true,
});

if (result.success) {
  // Store encrypted wallet key
  const encrypted = await biometricAuth.storeSecure(
    walletPrivateKey,
    {
      keyAlias: `wallet_${walletId}`,
      requireBiometric: true,
      invalidateOnEnrollment: true, // Re-auth if biometrics change
    }
  );

  // Save to secure storage
  await SecureStore.setItemAsync('wallet_key', JSON.stringify(encrypted));
} else {
  console.log('Auth failed:', result.errorMessage);
}

// Later: retrieve for transaction
const encryptedData = JSON.parse(
  await SecureStore.getItemAsync('wallet_key')
);

const privateKey = await biometricAuth.retrieveSecure(encryptedData, {
  promptMessage: 'Sign transaction',
  cancelButtonText: 'Cancel',
});

if (privateKey) {
  // Sign and send transaction
  const signature = await signTransaction(privateKey, transaction);
  // Clear from memory
  privateKey = null;
}
```

### Flutter Implementation

```dart
import 'package:local_auth/local_auth.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

final localAuth = LocalAuthentication();
final secureStorage = FlutterSecureStorage();

// Check availability
final canCheckBiometrics = await localAuth.canCheckBiometrics;
final availableBiometrics = await localAuth.getAvailableBiometrics();

if (availableBiometrics.contains(BiometricType.face)) {
  print('Face ID available');
} else if (availableBiometrics.contains(BiometricType.fingerprint)) {
  print('Fingerprint available');
}

// Authenticate
final didAuthenticate = await localAuth.authenticate(
  localizedReason: 'Authenticate to access your wallet',
  options: const AuthenticationOptions(
    biometricOnly: true,
    stickyAuth: true,
  ),
);

if (didAuthenticate) {
  // Store private key
  await secureStorage.write(
    key: 'wallet_private_key',
    value: privateKey,
    iOptions: IOSOptions(
      accessibility: KeychainAccessibility.whenUnlockedThisDeviceOnly,
      accountName: 'XAI Wallet',
    ),
    aOptions: AndroidOptions(
      encryptedSharedPreferences: true,
    ),
  );
}

// Retrieve for transaction
final privateKey = await secureStorage.read(
  key: 'wallet_private_key',
  iOptions: IOSOptions(
    accessibility: KeychainAccessibility.whenUnlockedThisDeviceOnly,
  ),
);
```

---

## Wallet Operations

### Create Wallet

**React Native:**
```typescript
// Generate new wallet
const wallet = await client.wallet.create({
  walletType: WalletType.STANDARD,
  name: 'My Wallet',
});

console.log('Address:', wallet.address);
console.log('Private Key:', wallet.privateKey); // SECURE THIS!

// Create HD wallet with mnemonic
const hdWallet = await client.wallet.createHD({
  name: 'HD Wallet',
  mnemonicLength: 24, // 12 or 24 words
});

console.log('Mnemonic:', hdWallet.mnemonic); // BACKUP THIS!
console.log('Address:', hdWallet.address);
```

**Flutter:**
```dart
// Generate new wallet
final wallet = await client.wallet.create(
  walletType: WalletType.standard,
  name: 'My Wallet',
);

print('Address: ${wallet.address}');

// Create HD wallet
final hdWallet = await client.wallet.createHD(
  name: 'HD Wallet',
  mnemonicLength: 24,
);

print('Mnemonic: ${hdWallet.mnemonic}');
```

### Send Transaction

**React Native:**
```typescript
// Prepare transaction
const tx = await client.transaction.send({
  from: wallet.address,
  to: 'TXAI_RECIPIENT',
  amount: '10.0',
  privateKey: walletPrivateKey,
});

console.log('Transaction hash:', tx.hash);

// Wait for confirmation
const confirmed = await client.transaction.waitForConfirmation(
  tx.hash,
  3, // confirmations
);

console.log('Confirmed in block:', confirmed.blockNumber);
```

**Flutter:**
```dart
// Send transaction
final tx = await client.transaction.send(
  from: wallet.address,
  to: 'TXAI_RECIPIENT',
  amount: '10.0',
  privateKey: walletPrivateKey,
);

print('Transaction: ${tx.hash}');

// Monitor confirmation
await for (final status in client.transaction.watchConfirmation(tx.hash)) {
  print('Confirmations: ${status.confirmations}');
  if (status.confirmations >= 3) {
    print('Transaction confirmed!');
    break;
  }
}
```

### Get Balance and Transactions

**React Native:**
```typescript
// Get balance
const balance = await client.wallet.getBalance(wallet.address);
console.log('Available:', balance.availableBalance);
console.log('Locked:', balance.lockedBalance);
console.log('Total:', balance.balance);

// Get transaction history
const history = await client.wallet.getTransactions({
  address: wallet.address,
  limit: 20,
  offset: 0,
});

history.data.forEach(tx => {
  console.log(`${tx.type}: ${tx.amount} XAI`);
  console.log(`Status: ${tx.status}`);
  console.log(`Time: ${new Date(tx.timestamp)}`);
});
```

**Flutter:**
```dart
// Get balance
final balance = await client.wallet.getBalance(wallet.address);
print('Total: ${balance.balance}');
print('Available: ${balance.availableBalance}');

// Get transactions
final history = await client.wallet.getTransactions(
  address: wallet.address,
  limit: 20,
);

for (final tx in history.data) {
  print('${tx.type}: ${tx.amount} XAI');
  print('Status: ${tx.status}');
}
```

---

## Real-Time Updates (WebSocket)

### React Native

```typescript
import { XAIClient } from '@xai/sdk';

const client = new XAIClient({
  baseUrl: 'https://testnet-rpc.xai.network',
});

// Connect to WebSocket
client.connectWebSocket('wss://testnet-rpc.xai.network/ws');

// Listen for new transactions
client.on('new_transaction', (transaction) => {
  if (transaction.to === wallet.address || transaction.from === wallet.address) {
    Alert.alert('New Transaction', `${transaction.amount} XAI`);
  }
});

// Listen for confirmations
client.on('transaction_confirmed', (data) => {
  console.log('Transaction confirmed:', data.txHash);
  // Update UI
});

// Listen for new blocks
client.on('new_block', (block) => {
  console.log('New block:', block.height);
});

// Clean up on unmount
useEffect(() => {
  return () => {
    client.disconnectWebSocket();
  };
}, []);
```

### Flutter

```dart
import 'package:web_socket_channel/web_socket_channel.dart';

final channel = WebSocketChannel.connect(
  Uri.parse('wss://testnet-rpc.xai.network/ws'),
);

// Listen for messages
channel.stream.listen((message) {
  final data = jsonDecode(message);

  if (data['type'] == 'new_transaction') {
    final tx = Transaction.fromJson(data['data']);
    if (tx.to == wallet.address || tx.from == wallet.address) {
      // Show notification
      showNotification('New Transaction: ${tx.amount} XAI');
    }
  }
});

// Clean up
@override
void dispose() {
  channel.sink.close();
  super.dispose();
}
```

---

## Push Notifications

### React Native (Firebase Cloud Messaging)

```typescript
import messaging from '@react-native-firebase/messaging';

// Request permission
const authStatus = await messaging().requestPermission();
const enabled = authStatus === messaging.AuthorizationStatus.AUTHORIZED;

if (enabled) {
  // Get FCM token
  const fcmToken = await messaging().getToken();

  // Register with XAI backend
  await client.wallet.registerPushNotifications({
    address: wallet.address,
    fcmToken,
    platform: Platform.OS,
  });
}

// Handle foreground messages
messaging().onMessage(async remoteMessage => {
  Alert.alert(
    remoteMessage.notification?.title,
    remoteMessage.notification?.body
  );
});

// Handle background messages
messaging().setBackgroundMessageHandler(async remoteMessage => {
  console.log('Background message:', remoteMessage);
});
```

### Flutter (Firebase Cloud Messaging)

```dart
import 'package:firebase_messaging/firebase_messaging.dart';

final messaging = FirebaseMessaging.instance;

// Request permission
final settings = await messaging.requestPermission();

if (settings.authorizationStatus == AuthorizationStatus.authorized) {
  // Get token
  final fcmToken = await messaging.getToken();

  // Register with XAI backend
  await client.wallet.registerPushNotifications(
    address: wallet.address,
    fcmToken: fcmToken,
    platform: Platform.operatingSystem,
  );
}

// Handle foreground messages
FirebaseMessaging.onMessage.listen((RemoteMessage message) {
  print('Notification: ${message.notification?.title}');
  showDialog(/* ... */);
});

// Handle background messages
FirebaseMessaging.onBackgroundMessage(_handleBackgroundMessage);

Future<void> _handleBackgroundMessage(RemoteMessage message) async {
  print('Background message: ${message.messageId}');
}
```

---

## QR Code Integration

### React Native

```typescript
import { QRCodeScanner } from 'react-native-qrcode-scanner';
import QRCode from 'react-native-qrcode-svg';

// Generate QR code for receiving
<QRCode
  value={wallet.address}
  size={200}
  backgroundColor="white"
  color="black"
/>

// Scan QR code for sending
<QRCodeScanner
  onRead={({ data }) => {
    // Parse address from QR code
    const address = data.startsWith('xai:')
      ? data.substring(4)
      : data;

    setRecipientAddress(address);
  }}
  topContent={<Text>Scan recipient address</Text>}
  bottomContent={
    <Button title="Cancel" onPress={() => setScanning(false)} />
  }
/>
```

### Flutter

```dart
import 'package:qr_code_scanner/qr_code_scanner.dart';
import 'package:qr_flutter/qr_flutter.dart';

// Generate QR code
QrImageView(
  data: wallet.address,
  version: QrVersions.auto,
  size: 200.0,
)

// Scan QR code
QRView(
  key: qrKey,
  onQRViewCreated: (QRViewController controller) {
    controller.scannedDataStream.listen((scanData) {
      final address = scanData.code?.startsWith('xai:') == true
        ? scanData.code!.substring(4)
        : scanData.code;

      setState(() {
        recipientAddress = address;
      });
    });
  },
)
```

---

## Testing

### React Native

```bash
# Run on iOS simulator
npm run ios

# Run on Android emulator
npm run android

# Run tests
npm test

# E2E tests with Detox
npx detox test
```

### Flutter

```bash
# Run on iOS simulator
flutter run -d ios

# Run on Android emulator
flutter run -d android

# Run tests
flutter test

# Integration tests
flutter drive --target=test_driver/app.dart
```

---

## Example Apps

### Complete React Native Wallet

See `/mobile-app/` for a full-featured React Native wallet:
- Wallet creation and import
- Biometric authentication
- Send/receive transactions
- Transaction history
- QR code scanner
- Push notifications

```bash
cd mobile-app
npm install
npm run ios  # or npm run android
```

### Sample Code

**[React Native Example](https://github.com/xai-blockchain/xai/tree/main/mobile-app)**
**[Flutter Example](https://github.com/xai-blockchain/xai/tree/main/examples/flutter-wallet)**

---

## Security Best Practices

1. **Never log private keys** - Use secure storage only
2. **Use biometric authentication** - Adds extra security layer
3. **Validate addresses** - Check format before sending
4. **Confirm transactions** - Show amount and recipient before signing
5. **Use HTTPS/WSS** - Always use secure connections
6. **Handle background state** - Lock app when backgrounded
7. **Clear sensitive data** - Remove from memory after use
8. **Test on testnet first** - Always test with testnet tokens

---

## Next Steps

- **[Biometric Authentication Deep Dive](../../src/xai/sdk/biometric/README.md)**
- **[TypeScript SDK Reference](../api/sdk.md)**
- **[Push Notifications Setup](../PUSH_NOTIFICATIONS.md)**
- **[Mobile App Architecture](../../mobile-app/ARCHITECTURE.md)**
- **[Security Best Practices](../../mobile-app/SECURITY.md)**

---

*Last Updated: January 2025 | XAI Version: 0.2.0*
