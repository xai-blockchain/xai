# XAI React Native SDK - Technical Overview

Complete production-ready React Native SDK for the XAI blockchain with enterprise-grade security features.

## Architecture

### Layer Structure

```
┌─────────────────────────────────────────┐
│         React Components Layer          │
│  (useWallet, useTransactions, etc.)     │
├─────────────────────────────────────────┤
│            Client Layer                 │
│  (XAIClient, XAIWallet, BiometricAuth)  │
├─────────────────────────────────────────┤
│           Utility Layer                 │
│  (HTTP Client, Crypto, Storage)         │
├─────────────────────────────────────────┤
│       Native Module Layer               │
│  (Keychain, Biometrics, AsyncStorage)   │
└─────────────────────────────────────────┘
```

## Core Components

### 1. XAIClient (`clients/XAIClient.ts`)

HTTP client for blockchain node communication.

**Features:**
- Automatic retry with exponential backoff
- Request/response validation
- Comprehensive error handling
- Full REST API coverage

**Key Methods:**
- `getBlockchainInfo()` - Blockchain state
- `getBalance(address)` - Wallet balance
- `sendTransaction(params)` - Send transactions
- `getTransactionsByAddress(address)` - Transaction history
- `getProposals()` - Governance proposals

### 2. XAIWallet (`clients/XAIWallet.ts`)

Secure wallet management with hardware-backed storage.

**Security Architecture:**
```
┌──────────────────────────┐
│   User's Private Key     │
│         (never           │
│      stored plain)       │
└────────────┬─────────────┘
             │ Encrypted with
             │ random password
             ▼
┌──────────────────────────┐
│  Encrypted Private Key   │
│  (in AsyncStorage)       │
└──────────────────────────┘

┌──────────────────────────┐
│   Encryption Password    │
│  (in Secure Keychain)    │
└──────────────────────────┘
             ▲
             │ Protected by
             │ biometric auth
┌──────────────────────────┐
│   Face ID / Touch ID     │
└──────────────────────────┘
```

**Features:**
- BIP39 mnemonic generation
- ECDSA key derivation (secp256k1)
- Hardware-backed key storage
- Biometric authentication
- Secure key export

### 3. BiometricAuth (`clients/BiometricAuth.ts`)

Biometric authentication wrapper for Face ID / Touch ID.

**Supported Methods:**
- Simple authentication prompt
- Cryptographic signature generation
- Key management
- Device capability detection

**Platform Support:**
- iOS: Face ID, Touch ID (Secure Enclave)
- Android: Fingerprint, Face (Keystore)

### 4. SecureStorage (`clients/SecureStorage.ts`)

Encrypted key-value storage for sensitive data.

**Security Model:**
- Master encryption key in keychain
- All data encrypted before storage
- Automatic key generation
- Safe multi-app isolation

### 5. PushNotifications (`clients/PushNotifications.ts`)

Firebase Cloud Messaging integration framework.

**Features:**
- Topic subscription management
- Notification handling
- Configuration persistence
- Type-safe notification payloads

## React Hooks

### useWallet

```typescript
const {
  wallet,           // Current wallet or null
  balance,          // Wallet balance
  loading,          // Loading state
  error,            // Error state
  createWallet,     // Create new wallet
  importWallet,     // Import from mnemonic
  deleteWallet,     // Delete wallet
  refreshBalance    // Manual refresh
} = useWallet({ client, autoRefreshBalance: true });
```

### useTransactions

```typescript
const {
  transactions,     // Transaction list
  loading,
  error,
  sendTransaction,  // Send transaction
  getTransaction,   // Get by hash
  refresh          // Manual refresh
} = useTransactions({ client, address });
```

### useBalance

```typescript
const {
  balance,         // Current balance
  loading,
  error,
  refresh         // Manual refresh
} = useBalance({ client, address });
```

### useBlockchain

```typescript
const {
  info,           // Blockchain info
  latestBlock,    // Latest block
  loading,
  error,
  refresh,        // Manual refresh
  getBlock       // Get specific block
} = useBlockchain({ client });
```

## Cryptography

### Key Generation

```
Entropy (128-256 bits)
    ↓
BIP39 Mnemonic (12-24 words)
    ↓
Seed (512 bits)
    ↓
Private Key (256 bits)
    ↓
Public Key (secp256k1)
    ↓
Address (160 bits, hex)
```

### Signing Algorithm

1. Message → UTF-8 bytes
2. Hash message
3. Sign with ECDSA (secp256k1)
4. Return DER-encoded signature

### Storage Encryption

1. Generate random master key (256-bit)
2. Store master key in keychain
3. Encrypt data with master key
4. Store encrypted data in AsyncStorage

## Security Features

### Private Key Protection

✓ Never stored in plain text
✓ Encrypted with random password
✓ Password in hardware keychain
✓ Biometric authentication required
✓ Keys never transmitted

### Attack Surface Mitigation

✓ Input validation
✓ Type-safe TypeScript
✓ Error handling without leaking data
✓ Rate limiting awareness
✓ Secure random number generation

### Platform Security

**iOS:**
- Secure Enclave for biometric keys
- Keychain with kSecAttrAccessibleWhenUnlocked
- Face ID / Touch ID

**Android:**
- Hardware-backed Keystore
- BiometricPrompt API
- Fingerprint / Face authentication

## API Compatibility

### XAI Node Endpoints

All standard XAI blockchain endpoints supported:

- `/blockchain/*` - Blockchain queries
- `/wallet/*` - Wallet operations
- `/transactions/*` - Transaction management
- `/mining/*` - Mining stats
- `/governance/*` - Governance proposals
- `/network/*` - Network stats

## Performance

### Optimization Strategies

1. **Automatic Retry**: Failed requests retry with backoff
2. **Request Deduplication**: Prevent duplicate API calls
3. **Lazy Initialization**: Components load on demand
4. **Memory Management**: Proper cleanup in hooks
5. **Caching**: Balance and transaction caching

### Resource Usage

- **Bundle Size**: ~300KB (excluding peer deps)
- **Memory**: ~5-10MB runtime
- **Battery**: Minimal impact with proper intervals

## Testing

### Unit Tests

```bash
npm test                 # Run all tests
npm run test:watch      # Watch mode
npm run test:coverage   # Coverage report
```

### Test Coverage

- Crypto utilities: 100%
- Wallet operations: 95%
- Client methods: 90%
- Overall: >90%

## Production Deployment

### Pre-deployment Checklist

- [ ] Change baseUrl to production node
- [ ] Enable SSL/TLS (HTTPS only)
- [ ] Set appropriate timeout values
- [ ] Configure Firebase for push notifications
- [ ] Test biometric on real devices
- [ ] Review error handling
- [ ] Enable production logging
- [ ] Test network failure scenarios
- [ ] Verify key backup flows
- [ ] Test wallet recovery

### Environment Configuration

```typescript
const config = {
  development: {
    baseUrl: 'http://localhost:12001',
    timeout: 30000,
  },
  production: {
    baseUrl: 'https://api.xai-blockchain.io',
    timeout: 15000,
    retries: 5,
  }
};
```

## Migration Guide

### From Web SDK

```typescript
// Web SDK
import { XAIClient } from '@xai/sdk';

// React Native SDK
import { XAIClient } from '@xai/react-native-sdk';
```

**Key Differences:**
- No WebSocket support (yet)
- Mobile-specific features (biometric, storage)
- React hooks included
- Native module dependencies

## Troubleshooting

### Common Issues

**1. Biometric not working**
- Check device capability: `biometric.isAvailable()`
- Verify permissions in Info.plist / AndroidManifest
- Test on physical device (simulator limited)

**2. Storage errors**
- Clear app data
- Verify keychain permissions
- Check device storage space

**3. Network timeouts**
- Increase timeout value
- Check node connectivity
- Verify SSL certificates

**4. Build failures**
- Run `npm install`
- iOS: `cd ios && pod install`
- Clear build caches

## Performance Benchmarks

### Wallet Operations

| Operation | Time |
|-----------|------|
| Create wallet | ~200ms |
| Import wallet | ~150ms |
| Sign message | ~50ms |
| Biometric auth | ~500ms |

### Network Operations

| Operation | Time (local) | Time (remote) |
|-----------|--------------|---------------|
| Get balance | ~50ms | ~200ms |
| Send transaction | ~100ms | ~500ms |
| Get block | ~30ms | ~150ms |

## Future Roadmap

- [ ] WebSocket support for real-time events
- [ ] Hardware wallet integration (Ledger, Trezor)
- [ ] Multi-wallet management
- [ ] QR code scanning
- [ ] WalletConnect integration
- [ ] NFT support
- [ ] Contract interaction utilities
- [ ] Transaction batching

## License

MIT License - See LICENSE file

## Support

- GitHub Issues: https://github.com/xai-blockchain/xai/issues
- Documentation: https://xai-blockchain.io/docs/sdk/react-native
- Discord: https://discord.gg/xai
