# Development Guide

Guide for developers working on the XAI React Native SDK.

## Prerequisites

- Node.js >= 16
- npm or yarn
- React Native development environment set up
- For iOS: Xcode and CocoaPods
- For Android: Android Studio and SDK

## Setup

1. Clone the repository:
```bash
git clone https://github.com/xai-blockchain/xai.git
cd xai/sdk/react-native
```

2. Install dependencies:
```bash
npm install
```

3. Build the SDK:
```bash
npm run build
```

## Project Structure

```
sdk/react-native/
├── src/
│   ├── clients/           # Core client implementations
│   │   ├── XAIClient.ts       # Blockchain API client
│   │   ├── XAIWallet.ts       # Wallet management
│   │   ├── BiometricAuth.ts   # Biometric authentication
│   │   ├── SecureStorage.ts   # Encrypted storage
│   │   └── PushNotifications.ts # FCM integration
│   ├── hooks/             # React hooks
│   │   ├── useWallet.ts       # Wallet hook
│   │   ├── useBalance.ts      # Balance monitoring
│   │   ├── useTransactions.ts # Transaction management
│   │   └── useBlockchain.ts   # Blockchain queries
│   ├── utils/             # Utilities
│   │   ├── http-client.ts     # HTTP client with retry
│   │   └── crypto.ts          # Cryptographic functions
│   ├── types/             # TypeScript types
│   │   └── index.ts           # Type definitions
│   ├── __tests__/         # Unit tests
│   └── index.ts           # Main entry point
├── examples/              # Example implementations
├── dist/                  # Build output
├── package.json
├── tsconfig.json
└── README.md
```

## Development Workflow

### Building

```bash
# Build once
npm run build

# Watch mode (rebuild on changes)
npm run dev
```

### Testing

```bash
# Run all tests
npm test

# Watch mode
npm run test:watch

# Coverage report
npm run test:coverage
```

### Linting

```bash
# Check for issues
npm run lint

# Auto-fix issues
npm run lint:fix
```

### Formatting

```bash
npm run format
```

### Type Checking

```bash
npm run typecheck
```

## Architecture

### Client Layer

The SDK is organized into specialized clients:

- **XAIClient**: HTTP communication with blockchain nodes
- **XAIWallet**: Secure wallet operations with biometric auth
- **BiometricAuth**: Face ID / Touch ID wrapper
- **SecureStorage**: Encrypted key-value storage
- **PushNotifications**: FCM integration framework

### Hook Layer

React hooks provide declarative APIs:

- **useWallet**: Manages wallet state and operations
- **useBalance**: Monitors and updates balance
- **useTransactions**: Sends and tracks transactions
- **useBlockchain**: Queries blockchain state

### Utility Layer

Low-level utilities:

- **http-client**: Axios with retry logic
- **crypto**: Key generation, signing, encryption

## Security Considerations

### Key Storage

- Private keys are encrypted before storage
- Encryption key stored in hardware keychain
- Never store keys in plain text
- Support for biometric-protected operations

### Biometric Authentication

- Hardware-backed key storage (Secure Enclave / Keystore)
- Fallback to device PIN/password
- No keys transmitted over network

### API Security

- HTTPS only for production
- Request validation
- Rate limiting awareness
- Proper error handling without leaking sensitive data

## Testing

### Unit Tests

Located in `src/__tests__/`:

```typescript
import { XAIWallet } from '../clients/XAIWallet';

describe('XAIWallet', () => {
  it('should create wallet', async () => {
    const wallet = new XAIWallet();
    await wallet.initialize();
    const newWallet = await wallet.createWallet(false);
    expect(newWallet.address).toMatch(/^0x[a-f0-9]{40}$/i);
  });
});
```

### Integration Tests

Test with actual XAI node:

```typescript
const client = new XAIClient({
  baseUrl: 'http://localhost:12001',
});

const info = await client.getBlockchainInfo();
expect(info.height).toBeGreaterThan(0);
```

## Adding New Features

### Adding a New Client

1. Create file in `src/clients/`:
```typescript
export class MyClient {
  constructor() {
    // Initialize
  }

  async myMethod() {
    // Implementation
  }
}
```

2. Export from `src/index.ts`:
```typescript
export { MyClient } from './clients/MyClient';
```

3. Add types to `src/types/index.ts`

4. Write tests in `src/__tests__/MyClient.test.ts`

### Adding a New Hook

1. Create file in `src/hooks/`:
```typescript
import { useState, useEffect } from 'react';

export function useMyFeature(options) {
  const [data, setData] = useState(null);

  useEffect(() => {
    // Effect logic
  }, []);

  return { data };
}
```

2. Export from `src/hooks/index.ts`

3. Document usage in README.md

4. Add example to `examples/`

## Publishing

### Pre-publish Checklist

- [ ] All tests pass
- [ ] Linting passes
- [ ] Type checking passes
- [ ] Version bumped in package.json
- [ ] CHANGELOG.md updated
- [ ] README.md up to date
- [ ] Build succeeds

### Publishing to npm

```bash
# Login to npm
npm login

# Build
npm run build

# Publish
npm publish --access public
```

## Troubleshooting

### Build Issues

**TypeScript errors:**
```bash
# Clean and rebuild
rm -rf dist node_modules
npm install
npm run build
```

**Missing dependencies:**
```bash
npm install
cd ios && pod install
```

### Runtime Issues

**Biometric not working:**
- Check Info.plist (iOS) has Face ID permission
- Check AndroidManifest.xml has biometric permission
- Verify device supports biometric

**Storage errors:**
- Clear app data
- Verify keychain access permissions
- Check device storage space

### Testing Issues

**Tests failing:**
```bash
# Clear Jest cache
npm test -- --clearCache

# Run specific test
npm test -- XAIWallet.test.ts
```

## Best Practices

### Code Style

- Use TypeScript for all new code
- Follow existing naming conventions
- Add JSDoc comments for public APIs
- Keep functions small and focused

### Error Handling

```typescript
try {
  await operation();
} catch (error: any) {
  if (error instanceof WalletError) {
    // Handle wallet-specific error
  } else if (error instanceof NetworkError) {
    // Handle network error
  } else {
    // Handle unknown error
  }
}
```

### Async Patterns

```typescript
// Good: Use async/await
async function fetchData() {
  const result = await client.getData();
  return result;
}

// Avoid: Promise chains
function fetchData() {
  return client.getData()
    .then(result => result);
}
```

### React Hooks

```typescript
// Good: Proper dependencies
useEffect(() => {
  fetchData();
}, [dependency]);

// Avoid: Missing dependencies
useEffect(() => {
  fetchData();
}, []); // Warning if fetchData uses props/state
```

## Resources

- [React Native Docs](https://reactnative.dev/docs/getting-started)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)
- [Jest Testing](https://jestjs.io/docs/getting-started)
- [XAI Blockchain Docs](https://xai-blockchain.io/docs)

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

### Commit Message Format

```
type(scope): subject

body

footer
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

Example:
```
feat(wallet): add multi-wallet support

- Add wallet switching
- Persist wallet selection
- Update UI for multiple wallets

Closes #123
```

## License

MIT - See LICENSE file for details
