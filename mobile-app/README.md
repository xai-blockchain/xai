# XAI Wallet - React Native Mobile App

A production-ready mobile wallet for the XAI blockchain with comprehensive security features, biometric authentication, and real-time transaction monitoring.

## Features

### Core Features
- **Wallet Management**
  - Create new wallet with 24-word mnemonic
  - Import wallet from mnemonic or private key
  - Secure key storage using device keychain
  - Automatic backup reminder

- **Transactions**
  - Send XAI tokens
  - Receive with QR code
  - Transaction history with pagination
  - Pending transaction management
  - Offline transaction signing
  - Real-time transaction updates via WebSocket

- **Security**
  - Biometric authentication (Face ID, Touch ID, Fingerprint)
  - Session timeout and auto-lock
  - Secure storage using react-native-keychain
  - Hardware-backed encryption
  - No sensitive data in logs

- **User Experience**
  - Clean, modern UI
  - Dark mode support (planned)
  - Multiple language support (planned)
  - Network status monitoring
  - Pull-to-refresh
  - Offline mode support

## Tech Stack

- **Framework**: React Native 0.73
- **Language**: TypeScript
- **State Management**: Zustand
- **Navigation**: React Navigation v6
- **Crypto**: elliptic, bip39
- **Storage**: AsyncStorage, react-native-keychain
- **Biometrics**: react-native-biometrics
- **QR Codes**: react-native-qrcode-svg
- **API Client**: axios
- **WebSocket**: Native WebSocket API

## Project Structure

```
mobile-app/
├── src/
│   ├── components/        # Reusable components
│   ├── constants/         # App constants and configuration
│   ├── navigation/        # Navigation setup
│   ├── screens/          # Screen components
│   ├── services/         # API, WebSocket, Biometric services
│   ├── store/            # Zustand stores
│   ├── types/            # TypeScript type definitions
│   ├── utils/            # Utility functions (crypto, storage, format)
│   └── App.tsx           # Root component
├── android/              # Android native code
├── ios/                  # iOS native code
└── index.js              # Entry point
```

## Getting Started

### Prerequisites

- Node.js >= 18
- npm >= 9
- React Native development environment
- Xcode (for iOS)
- Android Studio (for Android)

### Installation

1. Install dependencies:
```bash
cd mobile-app
npm install
```

2. Install iOS dependencies (macOS only):
```bash
cd ios
pod install
cd ..
```

3. Configure environment:
```bash
cp .env.example .env
# Edit .env with your API endpoint
```

### Running the App

#### iOS
```bash
npm run ios
```

#### Android
```bash
npm run android
```

### Development

```bash
# Start Metro bundler
npm start

# Run tests
npm test

# Type checking
npm run type-check

# Linting
npm run lint

# Format code
npm run format
```

## Configuration

### API Endpoints

Configure the XAI node endpoint in `.env`:

```env
API_ENDPOINT=http://your-node:12001
WS_ENDPOINT=ws://your-node:12001
```

Or change in app settings after wallet creation.

### Security Configuration

Default security settings in `src/constants/index.ts`:

- Session timeout: 5 minutes
- PIN length: 6 digits
- Max PIN attempts: 5
- Keychain service: XAIWallet

## Building for Production

### iOS

1. Configure signing in Xcode
2. Update version in `ios/XAIWallet/Info.plist`
3. Archive and upload to App Store Connect

```bash
cd ios
xcodebuild -workspace XAIWallet.xcworkspace -scheme XAIWallet -configuration Release archive
```

### Android

1. Generate release keystore:
```bash
keytool -genkeypair -v -keystore release.keystore -alias xai-wallet -keyalg RSA -keysize 2048 -validity 10000
```

2. Configure signing in `android/app/build.gradle`

3. Build release APK/AAB:
```bash
cd android
./gradlew assembleRelease
# or
./gradlew bundleRelease
```

## Security Best Practices

1. **Private Keys**
   - Stored in device keychain with hardware-backed encryption
   - Never logged or exposed in memory dumps
   - Cleared on app deletion

2. **Biometric Authentication**
   - Uses device secure enclave/TEE
   - Fallback to PIN
   - Configurable timeout

3. **Network Security**
   - HTTPS/WSS for all API calls
   - Certificate pinning (recommended)
   - Request/response validation

4. **Session Management**
   - Automatic timeout after inactivity
   - Secure session token storage
   - Lock on app backgrounding

## Testing

### Unit Tests
```bash
npm test
```

### E2E Tests (planned)
```bash
npm run test:e2e
```

### Manual Testing Checklist

- [ ] Create wallet flow
- [ ] Import wallet from mnemonic
- [ ] Import wallet from private key
- [ ] Send transaction
- [ ] Receive transaction
- [ ] View transaction history
- [ ] Enable/disable biometric
- [ ] Auto-lock functionality
- [ ] Offline mode
- [ ] Network error handling
- [ ] Session timeout

## Known Issues

1. QR Scanner not implemented - uses placeholder
2. Camera permissions need to be added for QR scanning
3. Push notifications infrastructure not implemented
4. Light client SPV mode not fully implemented

## Roadmap

- [ ] Camera integration for QR scanning
- [ ] Push notifications
- [ ] Multi-wallet support
- [ ] Token management
- [ ] DApp browser
- [ ] NFT support
- [ ] Hardware wallet integration
- [ ] WalletConnect support
- [ ] Exchange integration
- [ ] Price charts
- [ ] Transaction filtering
- [ ] Address book
- [ ] Custom fees

## Contributing

1. Fork the repository
2. Create feature branch
3. Make changes
4. Run tests and linting
5. Submit pull request

## License

MIT License - see LICENSE file for details

## Support

For issues and questions:
- GitHub Issues: [xai/issues](https://github.com/your-org/xai/issues)
- Documentation: [docs.xai.network](https://docs.xai.network)
- Community: [Discord](https://discord.gg/xai)

## Changelog

### Version 1.0.0 (Initial Release)
- Wallet creation and import
- Send/receive transactions
- Transaction history
- Biometric authentication
- Secure key storage
- Real-time updates
- Offline signing
