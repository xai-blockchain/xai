# XAI Wallet Architecture

## Overview

XAI Wallet is a React Native mobile application built with Expo, designed for the XAI blockchain.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Framework | React Native 0.73 |
| Platform | Expo SDK 50 |
| Language | TypeScript 5.x |
| Navigation | React Navigation 6 |
| State | React Context |
| Storage | expo-secure-store |
| Build | EAS Build |

## Directory Structure

```
mobile/
├── App.tsx                    # Root component, navigation setup
├── app.config.js              # Dynamic Expo configuration
├── src/
│   ├── components/            # Reusable UI components
│   │   ├── Button.tsx
│   │   ├── Card.tsx
│   │   ├── Input.tsx
│   │   └── ...
│   ├── context/
│   │   └── WalletContext.tsx  # Global wallet state
│   ├── screens/
│   │   ├── HomeScreen.tsx     # Dashboard
│   │   ├── WalletScreen.tsx   # Wallet management
│   │   ├── SendScreen.tsx     # Send transactions
│   │   └── ExplorerScreen.tsx # Block explorer
│   ├── services/
│   │   └── api.ts             # XAI node API client
│   ├── types/
│   │   └── index.ts           # TypeScript definitions
│   └── utils/
│       ├── crypto.ts          # Cryptographic operations
│       ├── storage.ts         # Secure storage wrapper
│       └── format.ts          # Formatting utilities
├── ios/                       # iOS native config (generated)
├── android/                   # Android native config (generated)
└── assets/                    # Icons, splash screens
```

## Data Flow

```
User Action
    │
    ▼
Screen Component
    │
    ├─► WalletContext (state update)
    │       │
    │       ▼
    │   SecureStore (persist)
    │
    └─► API Service
            │
            ▼
        XAI Node (:12001)
            │
            ▼
        Response
            │
            ▼
        Update State
            │
            ▼
        Re-render UI
```

## Security Architecture

### Key Storage
- iOS: Secure Enclave via expo-secure-store
- Android: Keystore via expo-secure-store
- Keys never leave the device

### Authentication Flow
```
App Launch
    │
    ▼
Check existing wallet
    │
    ├─► No wallet → Create/Import screen
    │
    └─► Has wallet
            │
            ▼
        Biometric/PIN prompt
            │
            ├─► Failed → Lock screen
            │
            └─► Success → Decrypt keys → Home
```

### Network Security
- TLS required for production
- Certificate pinning (optional)
- No sensitive data in logs

## API Integration

### Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/balance/<addr>` | GET | Wallet balance |
| `/history/<addr>` | GET | Transactions |
| `/send` | POST | Submit transaction |
| `/blocks` | GET | Block list |
| `/stats` | GET | Network info |
| `/faucet/claim` | POST | Testnet tokens |

### Error Handling
- Network errors: Retry with backoff
- API errors: Display user message
- Validation errors: Inline feedback

## State Management

Using React Context for simplicity:

```typescript
interface WalletState {
  address: string | null;
  balance: string;
  transactions: Transaction[];
  isLoading: boolean;
  error: string | null;
}

interface WalletActions {
  createWallet: () => Promise<void>;
  importWallet: (key: string) => Promise<void>;
  sendTransaction: (to: string, amount: string) => Promise<void>;
  refreshBalance: () => Promise<void>;
}
```

## Build & Deploy

### Environments
1. **Development**: Local builds, debug mode
2. **Preview**: Internal testing, TestFlight/Internal Track
3. **Staging**: Pre-production testing
4. **Production**: App Store / Play Store

### EAS Build Profiles
- `development`: Debug builds with dev client
- `preview`: Release builds for internal testing
- `staging`: Release builds for QA
- `production`: Store-ready builds

## Performance

### Optimizations
- Lazy screen loading
- Memoized components
- Virtualized lists for transactions
- Optimistic UI updates

### Metrics Targets
- App launch: <2s
- Screen transition: <300ms
- API response handling: <100ms
