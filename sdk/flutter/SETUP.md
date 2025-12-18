# XAI SDK Setup Guide

Quick setup guide for integrating the XAI SDK into your Flutter application.

## Prerequisites

- Flutter 3.10.0 or higher
- Dart 3.0.0 or higher
- iOS 12.0+ (for iOS apps)
- Android API 23+ (for Android apps)

## Installation

### 1. Add Dependency

Add to your `pubspec.yaml`:

```yaml
dependencies:
  xai_sdk:
    path: ../path/to/xai/sdk/flutter
```

Or from pub.dev (when published):

```yaml
dependencies:
  xai_sdk: ^1.0.0
```

### 2. Install Packages

```bash
flutter pub get
```

## Platform Configuration

### iOS Setup

1. Add to `ios/Runner/Info.plist`:

```xml
<key>NSFaceIDUsageDescription</key>
<string>Authenticate to access your XAI wallet</string>
<key>NSCameraUsageDescription</key>
<string>Scan QR codes for addresses</string>
```

2. Minimum deployment target in `ios/Podfile`:

```ruby
platform :ios, '12.0'
```

3. Run:

```bash
cd ios && pod install
```

### Android Setup

1. Update `android/app/build.gradle`:

```gradle
android {
    compileSdkVersion 34

    defaultConfig {
        minSdkVersion 23
        targetSdkVersion 34
    }
}
```

2. Add to `android/app/src/main/AndroidManifest.xml`:

```xml
<uses-permission android:name="android.permission.USE_BIOMETRIC"/>
<uses-permission android:name="android.permission.INTERNET"/>
```

## Firebase Setup (for Push Notifications)

### 1. Create Firebase Project

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Create a new project or select existing
3. Add your iOS and Android apps

### 2. iOS Configuration

1. Download `GoogleService-Info.plist`
2. Place in `ios/Runner/`
3. Add to Xcode project (Runner > Runner folder)

### 3. Android Configuration

1. Download `google-services.json`
2. Place in `android/app/`

3. Update `android/build.gradle`:

```gradle
buildscript {
    dependencies {
        classpath 'com.google.gms:google-services:4.3.15'
    }
}
```

4. Update `android/app/build.gradle`:

```gradle
apply plugin: 'com.google.gms.google-services'
```

### 4. Initialize Firebase in App

```dart
import 'package:firebase_core/firebase_core.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Firebase.initializeApp();
  runApp(MyApp());
}
```

## Basic Usage

### Initialize SDK

```dart
import 'package:xai_sdk/xai_sdk.dart';

// Create client
final client = XAIClient(
  config: XAIClientConfig(
    baseUrl: 'http://your-node-url:12001',
    wsUrl: 'ws://your-node-url:12003',
  ),
);

// Create wallet service
final wallet = XAIWallet();

// Create transaction service
final txService = XAITransaction(
  client: client,
  wallet: wallet,
);
```

### Create First Wallet

```dart
final myWallet = await wallet.createWallet(
  name: 'My Wallet',
  setAsDefault: true,
);

print('Address: ${myWallet.address}');
```

### Send Transaction

```dart
final response = await txService.transferAndSend(
  senderAddress: myWallet.address,
  recipientAddress: 'XAI...',
  amount: 10.0,
);

if (response.success) {
  print('Transaction sent: ${response.txid}');
}
```

## Troubleshooting

### iOS Build Issues

**Problem:** Biometric authentication not working

**Solution:** Ensure `NSFaceIDUsageDescription` is in Info.plist and app is running on real device (not simulator)

---

**Problem:** Pod install fails

**Solution:**
```bash
cd ios
rm -rf Pods Podfile.lock
pod install --repo-update
```

### Android Build Issues

**Problem:** Biometric authentication crashes

**Solution:** Ensure `minSdkVersion` is at least 23 and permissions are in manifest

---

**Problem:** Firebase not initializing

**Solution:** Verify `google-services.json` is in `android/app/` and Google Services plugin is applied

### Network Issues

**Problem:** Connection refused

**Solution:**
- Verify node URL is correct
- Check if node is running
- For Android emulator, use `10.0.2.2` instead of `localhost`
- For iOS simulator, use `localhost` or actual IP

### Secure Storage Issues

**Problem:** Flutter secure storage not working

**Solution:**
- iOS: May need to reset simulator
- Android: Clear app data and reinstall

## Testing

### Run Unit Tests

```bash
flutter test
```

### Run Example App

```bash
cd example
flutter run
```

### Test on Real Devices

Biometric authentication requires real devices:

```bash
# iOS
flutter run -d <ios-device-id>

# Android
flutter run -d <android-device-id>
```

## Next Steps

- Read the [README](README.md) for usage examples
- See [API Documentation](API.md) for complete API reference
- Check [example app](example/) for full implementation
- Review [CHANGELOG](CHANGELOG.md) for updates

## Support

- GitHub Issues: https://github.com/xai-blockchain/xai/issues
- Documentation: https://xai-blockchain.io/docs
- Discord: https://discord.gg/xai

## Security Notes

1. **Never commit private keys** - They are stored securely by the SDK
2. **Use HTTPS in production** - HTTP is only for local development
3. **Enable biometric authentication** for sensitive operations
4. **Keep SDK updated** to get security patches
5. **Test on real devices** before deploying to production
