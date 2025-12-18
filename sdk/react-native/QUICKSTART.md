# Quick Start Guide

Get started with the XAI React Native SDK in 5 minutes.

## Installation

```bash
# Install the SDK
npm install @xai/react-native-sdk

# Install peer dependencies
npm install react-native-keychain react-native-biometrics @react-native-async-storage/async-storage react-native-get-random-values

# iOS only: Install pods
cd ios && pod install && cd ..
```

## Basic Setup

### 1. Initialize Client

```typescript
import { XAIClient } from '@xai/react-native-sdk';

const client = new XAIClient({
  baseUrl: 'http://your-xai-node:12001',
  timeout: 30000,
});
```

### 2. Create Your First Component

```typescript
import React from 'react';
import { View, Text, Button } from 'react-native';
import { useWallet } from '@xai/react-native-sdk';

function WalletScreen() {
  const { wallet, balance, createWallet, loading } = useWallet({ client });

  if (loading) return <Text>Loading...</Text>;

  if (!wallet) {
    return (
      <Button
        title="Create Wallet"
        onPress={() => createWallet(true)} // Enable biometric
      />
    );
  }

  return (
    <View>
      <Text>Address: {wallet.address}</Text>
      <Text>Balance: {balance} XAI</Text>
    </View>
  );
}
```

## Common Tasks

### Create a Wallet

```typescript
import { useWallet } from '@xai/react-native-sdk';

const { createWallet } = useWallet({ client });

// Create with biometric authentication
const wallet = await createWallet(true);
console.log('Created:', wallet.address);
```

### Send a Transaction

```typescript
import { useTransactions } from '@xai/react-native-sdk';

const { sendTransaction } = useTransactions({
  client,
  address: wallet.address
});

const tx = await sendTransaction({
  from: wallet.address,
  to: recipientAddress,
  value: '100',
});
```

### Check Balance

```typescript
import { useBalance } from '@xai/react-native-sdk';

const { balance, refresh } = useBalance({
  client,
  address: wallet.address
});

// Balance updates automatically every 30s
// Or refresh manually:
await refresh();
```

### Import Existing Wallet

```typescript
const { importWallet } = useWallet({ client });

const wallet = await importWallet(
  'your twelve word mnemonic phrase here',
  true // Enable biometric
);
```

## iOS Setup

Add to `ios/YourApp/Info.plist`:

```xml
<key>NSFaceIDUsageDescription</key>
<string>We use Face ID to secure your wallet</string>
```

## Android Setup

Add to `android/app/src/main/AndroidManifest.xml`:

```xml
<uses-permission android:name="android.permission.USE_BIOMETRIC" />
```

Add to `android/app/build.gradle`:

```gradle
android {
    ...
    defaultConfig {
        ...
        minSdkVersion 23  // Required for Keychain
    }
}
```

## Configuration Options

### Client Configuration

```typescript
const client = new XAIClient({
  baseUrl: 'http://localhost:12001',  // Your node URL
  timeout: 30000,                      // Request timeout (ms)
  retries: 3,                          // Retry attempts
  retryDelay: 1000,                    // Delay between retries (ms)
});
```

### Hook Configuration

```typescript
const { wallet, balance } = useWallet({
  client,
  autoRefreshBalance: true,  // Auto-refresh balance
  refreshInterval: 30000,    // Refresh every 30s
});
```

## Security Best Practices

1. **Always enable biometric authentication in production**
   ```typescript
   await createWallet(true); // Enable biometric
   ```

2. **Prompt users to backup mnemonic**
   ```typescript
   const wallet = await createWallet();
   Alert.alert('Save This!', wallet.mnemonic);
   ```

3. **Use HTTPS in production**
   ```typescript
   const client = new XAIClient({
     baseUrl: 'https://api.xai-blockchain.io', // HTTPS only!
   });
   ```

4. **Verify transactions before sending**
   ```typescript
   const { fee } = await client.estimateFee(params);
   Alert.alert('Confirm', `Fee: ${fee} XAI`);
   ```

## Troubleshooting

### "Biometric not available"
- Test on physical device (simulator has limitations)
- Check Info.plist / AndroidManifest permissions
- Verify device has biometric enrolled

### "Network error"
- Verify node URL is correct
- Check node is running
- Ensure device can reach node (same network)

### "Build failed"
- Run `npm install`
- iOS: `cd ios && pod install`
- Clean build: `react-native clean-project`

## Next Steps

- See [README.md](./README.md) for complete API documentation
- Check [examples/](./examples/) for full examples
- Read [OVERVIEW.md](./OVERVIEW.md) for architecture details
- View [DEVELOPMENT.md](./DEVELOPMENT.md) for contributing

## Support

- Issues: https://github.com/xai-blockchain/xai/issues
- Discord: https://discord.gg/xai
- Docs: https://xai-blockchain.io/docs
