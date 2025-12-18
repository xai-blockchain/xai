# XAI Wallet Architecture

## High-Level Overview

```
┌─────────────────────────────────────────────────────────┐
│                    XAI Wallet App                       │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐  │
│  │   Screens    │  │ Components   │  │ Navigation  │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬──────┘  │
│         │                 │                  │         │
│         └─────────────────┴──────────────────┘         │
│                          │                             │
│  ┌───────────────────────┴──────────────────────────┐  │
│  │            State Management (Zustand)            │  │
│  │  ┌────────────────┐    ┌────────────────┐       │  │
│  │  │  Wallet Store  │    │   App Store    │       │  │
│  │  └────────┬───────┘    └────────┬───────┘       │  │
│  └───────────┼─────────────────────┼───────────────┘  │
│              │                     │                   │
│  ┌───────────┴─────────────────────┴───────────────┐  │
│  │                  Services Layer                  │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │  │
│  │  │   API    │  │WebSocket │  │  Biometric   │  │  │
│  │  └────┬─────┘  └────┬─────┘  └──────┬───────┘  │  │
│  └───────┼─────────────┼─────────────────┼─────────┘  │
│          │             │                 │            │
│  ┌───────┴─────────────┴─────────────────┴─────────┐  │
│  │                 Utils Layer                      │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │  │
│  │  │  Crypto  │  │ Storage  │  │   Format     │  │  │
│  │  └──────────┘  └──────────┘  └──────────────┘  │  │
│  └──────────────────────────────────────────────────┘  │
│                                                         │
└─────────────────────────────────────────────────────────┘
            │                              │
            ▼                              ▼
   ┌────────────────┐           ┌─────────────────┐
   │  XAI Node API  │           │  Device Secure  │
   │   (HTTP/WS)    │           │    Storage      │
   └────────────────┘           └─────────────────┘
```

## Layer Breakdown

### 1. Presentation Layer

#### Screens
Location: `src/screens/`

**Onboarding Flow**
- `Onboarding.tsx` - Initial welcome screen
- `CreateWallet.tsx` - New wallet creation
- `ImportWallet.tsx` - Import from mnemonic/private key
- `BackupMnemonic.tsx` - Display recovery phrase
- `VerifyMnemonic.tsx` - Verify backup
- `BiometricSetup.tsx` - Enable biometric auth

**Main App**
- `Dashboard.tsx` - Home screen with balance and recent transactions
- `Send.tsx` - Send transaction form
- `Receive.tsx` - Display QR code and address
- `History.tsx` - Transaction history list
- `Settings.tsx` - App settings and preferences

**Auxiliary**
- `LockScreen.tsx` - Authentication screen
- `TransactionDetail.tsx` - Transaction details
- `QRScanner.tsx` - QR code scanner

#### Navigation
Location: `src/navigation/`

- `RootNavigator.tsx` - Top-level navigation logic
- `MainTabNavigator.tsx` - Bottom tab navigation

**Navigation Flow**
```
App Start
    ├─ No Wallet → Onboarding Stack
    │   ├─ Onboarding
    │   ├─ CreateWallet / ImportWallet
    │   ├─ BackupMnemonic
    │   ├─ VerifyMnemonic
    │   └─ BiometricSetup → MainTabs
    │
    └─ Has Wallet → MainTabs
        ├─ Dashboard (Tab)
        ├─ Send (Tab)
        ├─ Receive (Tab)
        ├─ History (Tab)
        ├─ Settings (Tab)
        ├─ TransactionDetail (Modal)
        └─ QRScanner (Modal)
```

### 2. State Management Layer

Location: `src/store/`

**Wallet Store** (`wallet.ts`)
- Wallet state and operations
- Balance management
- Transaction handling
- Pending transaction queue

State:
```typescript
{
  wallet: Wallet | null
  balance: number
  isLoading: boolean
  error: string | null
  pendingTransactions: PendingTransaction[]
}
```

Actions:
- `createWallet()` - Generate new wallet
- `importWallet()` - Import existing wallet
- `loadWallet()` - Load from storage
- `deleteWallet()` - Remove wallet
- `refreshBalance()` - Update balance from network
- `addPendingTransaction()` - Queue transaction
- `syncPendingTransactions()` - Check pending status

**App Store** (`app.ts`)
- Application settings
- Biometric configuration
- Lock/unlock state
- Session management

State:
```typescript
{
  settings: AppSettings
  biometricConfig: BiometricConfig
  isLocked: boolean
  lastActivity: number
  isInitialized: boolean
}
```

Actions:
- `initialize()` - Load settings and config
- `updateSettings()` - Update preferences
- `enableBiometric()` - Setup biometric auth
- `lockApp()` / `unlockApp()` - Security
- `checkSession()` - Validate session

### 3. Services Layer

Location: `src/services/`

**API Service** (`api.ts`)
- HTTP client for XAI node
- Request/response handling
- Error handling and retry logic
- Network status monitoring

Methods:
```typescript
getNodeInfo(): Promise<NodeInfo>
getBalance(address): Promise<number>
getNonce(address): Promise<NonceResponse>
getHistory(address, limit, offset): Promise<TransactionHistory>
getTransaction(txid): Promise<Transaction>
sendTransaction(tx): Promise<SendTransactionResponse>
```

**WebSocket Service** (`websocket.ts`)
- Real-time updates
- Transaction notifications
- Balance changes
- Block updates
- Auto-reconnection

Events:
```typescript
on('transaction', callback)
on('block', callback)
on('balance', callback)
on('connected', callback)
on('disconnected', callback)
```

**Biometric Service** (`biometric.ts`)
- Biometric authentication
- Hardware-backed keys
- Signature creation

Methods:
```typescript
isAvailable(): Promise<BiometricAvailability>
authenticate(prompt): Promise<boolean>
createKeys(): Promise<boolean>
deleteKeys(): Promise<boolean>
```

### 4. Utils Layer

Location: `src/utils/`

**Crypto** (`crypto.ts`)
- Key generation and derivation
- Transaction signing
- Address validation
- Mnemonic handling

**Storage** (`storage.ts`)
- Secure key storage (Keychain)
- General data storage (AsyncStorage)
- Wallet-specific operations

**Format** (`format.ts`)
- Number formatting
- Date/time formatting
- Address truncation
- Amount parsing

### 5. Types Layer

Location: `src/types/`

Core type definitions:
- Transaction
- Wallet
- Block
- Settings
- Navigation params

## Data Flow

### Transaction Send Flow

```
User Input (Send Screen)
    ↓
Validation (amount, address, balance)
    ↓
Get Nonce (API Service)
    ↓
Create Transaction Object
    ↓
Sign Transaction (Crypto Utils + Private Key from Keychain)
    ↓
Send to Network (API Service)
    ↓
Add to Pending Queue (Wallet Store)
    ↓
WebSocket Notification
    ↓
Update Balance & History
```

### Balance Update Flow

```
App Launch / Pull to Refresh
    ↓
API Request (getBalance)
    ↓
Update Store (Wallet Store)
    ↓
UI Re-render (Dashboard)

Parallel:
    WebSocket Connection
        ↓
    Subscribe to Address
        ↓
    Receive Balance Update
        ↓
    Update Store
        ↓
    UI Re-render
```

### Authentication Flow

```
App Start
    ↓
Load Settings (App Store)
    ↓
Check Lock Status
    ↓
If Locked:
    ├─ Show Lock Screen
    ├─ Biometric Enabled? → Prompt Biometric
    ├─ Success? → Unlock App
    └─ Failure? → Show PIN Entry

During Use:
    ├─ Track Activity (updateActivity)
    ├─ Check Session Timeout (every 30s)
    └─ Timeout? → Lock App
```

## Security Architecture

### Key Storage Hierarchy

```
User Interaction
    ↓
Biometric/PIN Authentication
    ↓
OS Keychain/Keystore (encrypted)
    ├─ Private Key (hardware-backed)
    └─ Mnemonic (hardware-backed)
    ↓
In-Memory (during transaction)
    ↓
Cleared after use
```

### Transaction Signing

```
Transaction Data
    ↓
Canonical Serialization
    ↓
SHA-256 Hash
    ↓
ECDSA Sign (secp256k1)
    ↓
DER Encoding
    ↓
Signed Transaction
```

## Performance Optimizations

1. **State Management**
   - Zustand for minimal re-renders
   - Selective updates
   - Computed values

2. **Network**
   - Request deduplication
   - Caching with TTL
   - Retry with exponential backoff
   - Request queue

3. **UI**
   - FlatList virtualization
   - Lazy loading
   - Memoized components
   - Image optimization

4. **Storage**
   - Batched writes
   - Compression
   - Cache invalidation

## Error Handling

### Levels

1. **UI Level**
   - User-friendly messages
   - Actionable errors
   - Retry mechanisms
   - Error boundaries

2. **Service Level**
   - Retry logic
   - Fallback strategies
   - Graceful degradation

3. **Storage Level**
   - Data validation
   - Corruption detection
   - Recovery mechanisms

## Testing Strategy

### Unit Tests
- Utils functions
- Store actions
- Service methods
- Crypto operations

### Integration Tests
- API integration
- Storage operations
- Navigation flows

### E2E Tests (planned)
- Wallet creation
- Transaction flow
- Settings changes

## Deployment

### Build Process

```
Development
    ├─ npm install
    ├─ npm run android/ios
    └─ Metro bundler

Production
    ├─ Update version
    ├─ Run tests
    ├─ Build release
    ├─ Code signing
    └─ Upload to store
```

### CI/CD (planned)

```
Git Push
    ↓
Run Tests
    ↓
Build APK/IPA
    ↓
Internal Testing
    ↓
Beta Release
    ↓
Production Release
```

## Monitoring

### Metrics
- App launches
- Wallet creations
- Transaction success rate
- Error rates
- Crash reports

### Analytics (planned)
- Screen views
- User flows
- Feature usage
- Performance metrics

## Future Architecture Considerations

1. **Multi-Wallet Support**
   - Wallet switching
   - Account management
   - Unified balance view

2. **DApp Integration**
   - WalletConnect
   - In-app browser
   - dApp permissions

3. **Advanced Features**
   - Staking
   - NFT support
   - Token management
   - DEX integration

4. **Scalability**
   - Pagination optimization
   - Database (Realm/SQLite)
   - Background sync
   - Push notifications
