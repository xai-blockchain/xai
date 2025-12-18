# XAI Wallet - Quick Start Guide

## TL;DR

```bash
# Clone and install
cd /home/hudson/blockchain-projects/xai/mobile-app
npm install

# iOS (macOS only)
cd ios && pod install && cd ..
npm run ios

# Android
npm run android
```

## Prerequisites Checklist

- [ ] Node.js 18+ installed
- [ ] npm 9+ installed
- [ ] React Native environment setup
- [ ] iOS: Xcode + CocoaPods (macOS only)
- [ ] Android: Android Studio + JDK

## First Time Setup

### 1. Install Dependencies

```bash
npm install
```

This will install all required packages including:
- React Native core
- Navigation libraries
- Crypto libraries (elliptic, bip39)
- Storage (AsyncStorage, Keychain)
- Biometric authentication
- UI components

### 2. Platform Setup

**iOS (macOS only)**
```bash
cd ios
pod install
cd ..
```

**Android**
- No additional steps needed
- Android SDK will be downloaded automatically

### 3. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` to point to your XAI node:
```env
API_ENDPOINT=http://192.168.1.100:12001
WS_ENDPOINT=ws://192.168.1.100:12001
```

### 4. Run the App

**iOS**
```bash
npm run ios
```

**Android**
```bash
npm run android
```

## Development Workflow

### Start Metro Bundler
```bash
npm start
```

### Run on Specific Device

**iOS**
```bash
# List simulators
xcrun simctl list devices

# Run on specific simulator
npm run ios -- --simulator="iPhone 14 Pro"

# Run on physical device
npm run ios -- --device
```

**Android**
```bash
# List devices
adb devices

# Run on specific device
npm run android -- --deviceId=DEVICE_ID
```

### Debug Menu

- **iOS**: Cmd+D (simulator) or shake device
- **Android**: Cmd+M (emulator) or shake device

Options:
- Reload
- Debug
- Enable Fast Refresh
- Toggle Inspector
- Show Perf Monitor

## Common Tasks

### Clear Cache
```bash
npm start -- --reset-cache
```

### Rebuild
```bash
# iOS
cd ios
pod install
cd ..
npm run ios

# Android
cd android
./gradlew clean
cd ..
npm run android
```

### Run Tests
```bash
npm test
npm run type-check
npm run lint
```

## Project Structure

```
mobile-app/
├── src/
│   ├── screens/          # 15 screen components
│   ├── navigation/       # Navigation setup
│   ├── services/         # API, WebSocket, Biometric
│   ├── store/            # Zustand state management
│   ├── utils/            # Crypto, Storage, Format
│   ├── types/            # TypeScript definitions
│   ├── constants/        # App constants
│   └── App.tsx           # Root component
├── android/              # Android native
├── ios/                  # iOS native
├── package.json          # Dependencies
└── tsconfig.json         # TypeScript config
```

## Features Overview

### Implemented
✅ Wallet creation with 24-word mnemonic
✅ Import wallet (mnemonic or private key)
✅ Secure key storage (device keychain)
✅ Send transactions
✅ Receive with QR code
✅ Transaction history
✅ Biometric authentication
✅ Session management
✅ Real-time updates (WebSocket)
✅ Offline transaction signing
✅ Pending transaction queue

### To Implement
⏳ QR code scanner (camera integration)
⏳ Push notifications
⏳ Multi-wallet support
⏳ Token management
⏳ DApp browser

## Testing the App

### 1. Create Wallet
1. Open app
2. Tap "Create New Wallet"
3. Write down 24-word phrase
4. Verify backup
5. Enable biometric (optional)

### 2. Send Transaction
1. Go to Send tab
2. Enter recipient address
3. Enter amount
4. Tap Send
5. Confirm transaction
6. Transaction appears in pending

### 3. Receive
1. Go to Receive tab
2. View QR code
3. Copy address
4. Share with sender

### 4. View History
1. Go to History tab
2. See all transactions
3. Tap transaction for details
4. Pull to refresh

## Troubleshooting

### Build Fails

**iOS**
```bash
# Clean build
cd ios
rm -rf Pods
pod deintegrate
pod cache clean --all
pod install
cd ..
```

**Android**
```bash
cd android
./gradlew clean
./gradlew cleanBuildCache
cd ..
```

### Metro Bundler Issues
```bash
# Kill existing Metro
pkill -f "node.*react-native"

# Clear watchman
watchman watch-del-all

# Clear Metro cache
rm -rf $TMPDIR/metro-*
rm -rf $TMPDIR/haste-*

# Restart
npm start -- --reset-cache
```

### Module Not Found
```bash
rm -rf node_modules
rm package-lock.json
npm install
```

### iOS Simulator Not Found
```bash
# Open simulator
open -a Simulator

# List available simulators
xcrun simctl list devices
```

### Android Emulator Not Starting
```bash
# List AVDs
emulator -list-avds

# Start specific AVD
emulator -avd Pixel_4_API_30
```

## Configuration

### Change API Endpoint

**Before wallet creation:**
Edit `.env` file

**After wallet creation:**
Settings → Network → Node Endpoint

### Security Settings

Settings → Security:
- Biometric Authentication
- Auto-Lock
- Session Timeout

## Performance Tips

1. **Enable Fast Refresh**
   - Automatically enabled
   - Preserves component state

2. **Use Production Build for Testing**
   ```bash
   # iOS
   npm run ios -- --configuration Release

   # Android
   cd android
   ./gradlew installRelease
   ```

3. **Profile Performance**
   - Enable Performance Monitor in Debug Menu
   - Check for unnecessary re-renders

## Next Steps

1. **Add XAI Node**
   - Start local XAI node
   - Configure endpoint in app

2. **Get Test Tokens**
   - Use faucet if available
   - Mine some blocks

3. **Test Transactions**
   - Create second wallet
   - Send between wallets

4. **Enable Biometric**
   - Works best on physical device
   - Simulator has limited support

5. **Explore Code**
   - Read ARCHITECTURE.md
   - Check SECURITY.md
   - Review screen implementations

## Resources

- **Documentation**: See README.md
- **Setup Guide**: See SETUP.md
- **Architecture**: See ARCHITECTURE.md
- **Security**: See SECURITY.md

- **React Native**: https://reactnative.dev
- **React Navigation**: https://reactnavigation.org
- **Zustand**: https://github.com/pmndrs/zustand

## Getting Help

1. Check documentation files
2. Review error messages
3. Search GitHub issues
4. Ask in community Discord

## Version Info

- **App Version**: 1.0.0
- **React Native**: 0.73.2
- **Node**: >=18
- **npm**: >=9

---

**Ready to build?** Run `npm run ios` or `npm run android` to get started!
