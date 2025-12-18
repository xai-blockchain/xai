# XAI Wallet Setup Guide

## Environment Setup

### macOS (iOS Development)

1. **Install Xcode**
   ```bash
   # Install from App Store
   # Install Command Line Tools
   xcode-select --install
   ```

2. **Install CocoaPods**
   ```bash
   sudo gem install cocoapods
   ```

3. **Install Node.js**
   ```bash
   brew install node@18
   ```

4. **Install Watchman**
   ```bash
   brew install watchman
   ```

### Windows/Linux (Android Development)

1. **Install Java Development Kit**
   ```bash
   # Ubuntu/Debian
   sudo apt-get install openjdk-11-jdk

   # macOS
   brew install --cask adoptopenjdk11
   ```

2. **Install Android Studio**
   - Download from https://developer.android.com/studio
   - Install Android SDK
   - Configure environment variables:
     ```bash
     export ANDROID_HOME=$HOME/Android/Sdk
     export PATH=$PATH:$ANDROID_HOME/emulator
     export PATH=$PATH:$ANDROID_HOME/tools
     export PATH=$PATH:$ANDROID_HOME/tools/bin
     export PATH=$PATH:$ANDROID_HOME/platform-tools
     ```

3. **Install Node.js**
   ```bash
   # Using nvm
   curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
   nvm install 18
   nvm use 18
   ```

## Project Setup

1. **Clone and Install**
   ```bash
   cd /home/hudson/blockchain-projects/xai/mobile-app
   npm install
   ```

2. **iOS Setup (macOS only)**
   ```bash
   cd ios
   pod install
   cd ..
   ```

3. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Run Postinstall**
   ```bash
   chmod +x postinstall.sh
   ./postinstall.sh
   ```

## Running the App

### iOS Simulator
```bash
npm run ios

# Specific device
npm run ios -- --simulator="iPhone 14 Pro"
```

### Android Emulator
```bash
# Start emulator first
emulator -avd Pixel_4_API_30

# Run app
npm run android
```

### Physical Device

#### iOS
1. Connect device via USB
2. Enable Developer Mode on device
3. Trust computer on device
4. Select device in Xcode
5. Run: `npm run ios -- --device`

#### Android
1. Enable Developer Options on device
2. Enable USB Debugging
3. Connect via USB
4. Run: `adb devices` to verify connection
5. Run: `npm run android`

## Troubleshooting

### iOS

**Pod install fails**
```bash
cd ios
pod deintegrate
pod install
```

**Build fails with duplicate symbols**
```bash
cd ios
rm -rf Pods
pod cache clean --all
pod install
```

**Metro bundler issues**
```bash
npm start -- --reset-cache
```

### Android

**Gradle build fails**
```bash
cd android
./gradlew clean
cd ..
npm run android
```

**ADB not finding device**
```bash
adb kill-server
adb start-server
adb devices
```

**Metro bundler port conflict**
```bash
npx react-native start --port 8082
```

### Common Issues

**Module not found**
```bash
rm -rf node_modules
npm install
```

**Cache issues**
```bash
npm start -- --reset-cache
```

**TypeScript errors**
```bash
npm run type-check
```

## Development Workflow

1. **Start Metro Bundler**
   ```bash
   npm start
   ```

2. **In separate terminal, run app**
   ```bash
   npm run ios
   # or
   npm run android
   ```

3. **Enable Fast Refresh**
   - Shake device or press Cmd+D (iOS) / Cmd+M (Android)
   - Enable Fast Refresh

4. **Debug**
   - React Native Debugger
   - Flipper
   - Chrome DevTools

## Testing

```bash
# Unit tests
npm test

# Watch mode
npm test -- --watch

# Coverage
npm test -- --coverage

# Lint
npm run lint

# Type check
npm run type-check
```

## Building for Production

### iOS

1. **Configure signing**
   - Open `ios/XAIWallet.xcworkspace` in Xcode
   - Select target > Signing & Capabilities
   - Choose team and provisioning profile

2. **Update version**
   - Edit `ios/XAIWallet/Info.plist`
   - Update `CFBundleShortVersionString` and `CFBundleVersion`

3. **Archive**
   - Product > Archive in Xcode
   - Upload to App Store Connect

### Android

1. **Generate signing key**
   ```bash
   keytool -genkeypair -v -keystore android/app/release.keystore -alias xai-wallet -keyalg RSA -keysize 2048 -validity 10000
   ```

2. **Configure gradle**
   - Edit `android/gradle.properties`
   - Add keystore details

3. **Build**
   ```bash
   cd android
   ./gradlew assembleRelease
   ```

4. **Output**
   - APK: `android/app/build/outputs/apk/release/app-release.apk`
   - AAB: `android/app/build/outputs/bundle/release/app-release.aab`

## Required Permissions

### iOS (Info.plist)
```xml
<key>NSCameraUsageDescription</key>
<string>Camera access is required to scan QR codes</string>
<key>NSFaceIDUsageDescription</key>
<string>Face ID is used to secure your wallet</string>
```

### Android (AndroidManifest.xml)
```xml
<uses-permission android:name="android.permission.CAMERA" />
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.USE_BIOMETRIC" />
<uses-permission android:name="android.permission.USE_FINGERPRINT" />
```

## Performance Optimization

1. **Enable Hermes** (already enabled)
2. **Optimize images** - use WebP format
3. **Use ProGuard** for Android release
4. **Enable app thinning** for iOS
5. **Lazy load screens** with React.lazy()

## Resources

- [React Native Docs](https://reactnavigation.org/docs/getting-started)
- [React Navigation](https://reactnavigation.org/)
- [Zustand](https://github.com/pmndrs/zustand)
- [React Native Keychain](https://github.com/oblador/react-native-keychain)
- [React Native Biometrics](https://github.com/SelfLender/react-native-biometrics)
