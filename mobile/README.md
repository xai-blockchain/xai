# XAI Mobile Wallet

Official React Native mobile wallet for the XAI blockchain network.

## Requirements

- Node.js 20+
- npm 10+
- Expo CLI (`npm install -g expo-cli`)
- EAS CLI (`npm install -g eas-cli`)
- iOS: Xcode 15+ (Mac only)
- Android: Android Studio with SDK 34+

## Quick Start

```bash
# Install dependencies
npm install

# Start development server
npm start

# Run on iOS simulator
npm run ios

# Run on Android emulator
npm run android
```

## Project Structure

```
mobile/
├── App.tsx                    # Entry point
├── app.json                   # Expo static config
├── app.config.js              # Dynamic config with env vars
├── eas.json                   # EAS Build config
├── src/
│   ├── components/            # Reusable UI components
│   ├── context/               # React Context (wallet state)
│   ├── screens/               # App screens
│   ├── services/              # API client
│   ├── types/                 # TypeScript types
│   └── utils/                 # Crypto, storage, formatting
├── ios/                       # iOS native config
├── android/                   # Android native config
└── assets/                    # Icons and images
```

## Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Key variables:
- `EXPO_PUBLIC_ENV`: Environment (development/preview/staging/production)
- `EXPO_PUBLIC_API_URL`: XAI node API URL

### API Configuration

Default API endpoints by environment:
- **Development**: `http://localhost:12001`
- **Preview/Staging**: `https://testnet.xai.network:12001`
- **Production**: `https://api.xai.network`

## Development

### Available Scripts

```bash
npm start          # Start Expo dev server
npm run ios        # Run on iOS
npm run android    # Run on Android
npm run web        # Run in browser
npm run lint       # Run ESLint
npm run typecheck  # TypeScript check
npm test           # Run tests
npm run test:cov   # Tests with coverage
```

### Development Builds

```bash
# Install EAS CLI
npm install -g eas-cli

# Login to Expo
eas login

# Build development client
eas build --profile development --platform ios
eas build --profile development --platform android
```

## Building for Production

### EAS Build

```bash
# Preview build (internal testing)
eas build --profile preview --platform all

# Production build (store release)
eas build --profile production --platform all
```

### Local Build (Native)

```bash
# Generate native projects
npx expo prebuild

# iOS
cd ios && pod install && cd ..
npx expo run:ios --configuration Release

# Android
cd android && ./gradlew assembleRelease
```

## Deployment

### TestFlight (iOS)

```bash
eas build --profile production --platform ios
eas submit --platform ios
```

### Play Store (Android)

```bash
eas build --profile production --platform android
eas submit --platform android
```

See [RELEASE.md](./RELEASE.md) for the complete release process.

## Features

- **Wallet Management**: Create/import wallets with secure storage
- **Transactions**: Send/receive XAI tokens
- **QR Codes**: Scan and display QR codes for addresses
- **Block Explorer**: Browse blocks and transactions
- **Biometric Auth**: Face ID, Touch ID, fingerprint
- **Testnet Faucet**: Get test tokens for development

## Security

- Private keys stored in device Secure Enclave
- No cloud backup of sensitive data
- Biometric + PIN protection
- TLS-only connections (except localhost)
- Open source and auditable

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      App.tsx                             │
│                  (Navigation + Providers)                │
├─────────────────────────────────────────────────────────┤
│  HomeScreen  │  WalletScreen  │  SendScreen  │ Explorer │
├─────────────────────────────────────────────────────────┤
│                    Components                            │
│   (Button, Card, Input, TransactionItem, BlockItem)     │
├─────────────────────────────────────────────────────────┤
│                 WalletContext                            │
│            (Global wallet state)                         │
├──────────────────────┬──────────────────────────────────┤
│      API Client      │         Utils                     │
│  (xaiApi.ts)         │  (crypto, storage, format)       │
└──────────────────────┴──────────────────────────────────┘
                           │
                           ▼
                   XAI Blockchain Node
                   (REST API :12001)
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/balance/<addr>` | GET | Get wallet balance |
| `/history/<addr>` | GET | Transaction history |
| `/send` | POST | Send transaction |
| `/blocks` | GET | List recent blocks |
| `/block/<hash>` | GET | Get block details |
| `/stats` | GET | Network statistics |
| `/faucet/claim` | POST | Testnet faucet |

## Testing

```bash
# Run all tests
npm test

# Watch mode
npm test -- --watch

# Coverage report
npm run test:cov
```

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

## Troubleshooting

### Build Fails

```bash
# Clear caches
npm start -- --clear
npx expo prebuild --clean
```

### iOS Simulator Issues

```bash
# Reset simulator
xcrun simctl shutdown all
xcrun simctl erase all
```

### Android Emulator Issues

```bash
# Cold boot emulator
emulator -avd <avd_name> -no-snapshot-load
```

## License

MIT License - see [LICENSE](../LICENSE)
