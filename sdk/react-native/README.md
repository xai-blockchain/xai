# XAI React Native SDK

Production-ready React Native SDK for the XAI blockchain with secure key storage, biometric authentication, and comprehensive React hooks.

## Features

- **Secure Wallet Management** - Hardware-backed key storage using react-native-keychain
- **Biometric Authentication** - Face ID / Touch ID support for transaction signing
- **React Hooks** - Easy-to-use hooks for React Native components
- **Encrypted Storage** - AES-256 encrypted local storage for sensitive data
- **Push Notifications** - Firebase Cloud Messaging integration hooks
- **Transaction Management** - Send, receive, and track blockchain transactions
- **Full TypeScript Support** - Complete type definitions included
- **Production Ready** - Comprehensive error handling and retry logic

## Installation

```bash
npm install @xai/react-native-sdk
```

### Peer Dependencies

You need to install the following peer dependencies:

```bash
npm install react-native-keychain react-native-biometrics @react-native-async-storage/async-storage react-native-get-random-values
```

### iOS Setup

Add to your `ios/Podfile`:

```ruby
pod 'RNKeychain', :path => '../node_modules/react-native-keychain'
```

Then run:

```bash
cd ios && pod install
```

### Android Setup

Add to your `android/app/build.gradle`:

```gradle
defaultConfig {
    ...
    minSdkVersion 23  // Required for Keychain
}
```

## Quick Start

### Basic Setup

```typescript
import { XAIClient, useWallet } from '@xai/react-native-sdk';
import React from 'react';

const client = new XAIClient({
  baseUrl: 'http://your-node:5000',
  timeout: 30000,
});

function WalletScreen() {
  const { wallet, balance, createWallet, loading } = useWallet({ client });

  const handleCreateWallet = async () => {
    const newWallet = await createWallet(true); // Enable biometrics
    console.log('Wallet created:', newWallet.address);
  };

  if (loading) return <Text>Loading...</Text>;

  return (
    <View>
      {wallet ? (
        <>
          <Text>Address: {wallet.address}</Text>
          <Text>Balance: {balance} XAI</Text>
        </>
      ) : (
        <Button title="Create Wallet" onPress={handleCreateWallet} />
      )}
    </View>
  );
}
```

### Complete Example

```typescript
import React, { useState } from 'react';
import { View, Text, Button, TextInput, Alert } from 'react-native';
import {
  XAIClient,
  useWallet,
  useTransactions,
  useBalance,
} from '@xai/react-native-sdk';

const client = new XAIClient({
  baseUrl: 'http://localhost:5000',
});

function App() {
  const { wallet, balance, createWallet, importWallet, loading } = useWallet({
    client,
    autoRefreshBalance: true,
    refreshInterval: 30000, // 30 seconds
  });

  const { transactions, sendTransaction } = useTransactions({
    client,
    address: wallet?.address || null,
  });

  const [recipient, setRecipient] = useState('');
  const [amount, setAmount] = useState('');

  const handleCreateWallet = async () => {
    try {
      const newWallet = await createWallet(true); // Enable biometric auth
      Alert.alert('Success', `Wallet created: ${newWallet.address}`);
    } catch (error) {
      Alert.alert('Error', error.message);
    }
  };

  const handleSendTransaction = async () => {
    if (!wallet) return;

    try {
      const tx = await sendTransaction({
        from: wallet.address,
        to: recipient,
        value: amount,
      });
      Alert.alert('Success', `Transaction sent: ${tx.hash}`);
      setRecipient('');
      setAmount('');
    } catch (error) {
      Alert.alert('Error', error.message);
    }
  };

  if (loading) {
    return <Text>Loading wallet...</Text>;
  }

  if (!wallet) {
    return (
      <View>
        <Button title="Create New Wallet" onPress={handleCreateWallet} />
      </View>
    );
  }

  return (
    <View style={{ padding: 20 }}>
      <Text>Address: {wallet.address}</Text>
      <Text>Balance: {balance} XAI</Text>

      <TextInput
        placeholder="Recipient Address"
        value={recipient}
        onChangeText={setRecipient}
      />
      <TextInput
        placeholder="Amount"
        value={amount}
        onChangeText={setAmount}
        keyboardType="numeric"
      />
      <Button title="Send" onPress={handleSendTransaction} />

      <Text>Recent Transactions:</Text>
      {transactions.map((tx) => (
        <View key={tx.hash}>
          <Text>{tx.hash.substring(0, 10)}...</Text>
          <Text>{tx.value} XAI</Text>
        </View>
      ))}
    </View>
  );
}
```

## API Documentation

### XAIClient

Main client for interacting with XAI blockchain nodes.

```typescript
import { XAIClient } from '@xai/react-native-sdk';

const client = new XAIClient({
  baseUrl: 'http://localhost:5000',
  timeout: 30000,
  retries: 3,
  retryDelay: 1000,
});

// Get blockchain info
const info = await client.getBlockchainInfo();

// Get balance
const balance = await client.getBalance(address);

// Get transactions
const transactions = await client.getTransactionsByAddress(address);

// Send transaction
const tx = await client.sendTransaction({
  from: address,
  to: recipient,
  value: amount,
});
```

### XAIWallet

Secure wallet management with biometric authentication.

```typescript
import { getXAIWallet } from '@xai/react-native-sdk';

const wallet = getXAIWallet();
await wallet.initialize();

// Create wallet with biometric auth
const newWallet = await wallet.createWallet(true);

// Import from mnemonic
const importedWallet = await wallet.importWallet(mnemonic, true);

// Sign message (requires biometric auth if enabled)
const signature = await wallet.signMessage('Hello, XAI!');

// Get private key (requires authentication)
const privateKey = await wallet.getPrivateKey();

// Export mnemonic (requires authentication)
const mnemonic = await wallet.exportMnemonic();

// Delete wallet
await wallet.deleteWallet();
```

### BiometricAuth

Biometric authentication wrapper.

```typescript
import { getBiometricAuth } from '@xai/react-native-sdk';

const biometric = getBiometricAuth();

// Check availability
const available = await biometric.isAvailable();
const type = await biometric.getBiometricType(); // 'FaceID' | 'TouchID' | 'Biometrics'

// Authenticate
const authenticated = await biometric.authenticate({
  title: 'Authenticate',
  description: 'Confirm your identity',
  cancelText: 'Cancel',
});

// Create signature
const signature = await biometric.createSignature('payload');
```

### SecureStorage

Encrypted local storage for sensitive data.

```typescript
import { getSecureStorage } from '@xai/react-native-sdk';

const storage = getSecureStorage();
await storage.initialize();

// Store data
await storage.setItem('key', 'value');

// Store JSON
await storage.setJSON('settings', { theme: 'dark' });

// Retrieve data
const value = await storage.getItem('key');
const settings = await storage.getJSON('settings');

// Remove data
await storage.removeItem('key');

// Clear all
await storage.clear();
```

### PushNotifications

Firebase Cloud Messaging integration hooks.

```typescript
import { getPushNotifications, NotificationType } from '@xai/react-native-sdk';

const notifications = getPushNotifications();
await notifications.initialize();

// Request permissions
await notifications.requestPermissions();

// Get FCM token
const token = await notifications.getToken();

// Subscribe to topics
await notifications.subscribeToTopic('transactions');

// Handle notifications
notifications.onNotification(NotificationType.TRANSACTION, (payload) => {
  console.log('New transaction:', payload);
});

// Update config
await notifications.updateConfig({
  enabled: true,
  transactionAlerts: true,
  governanceAlerts: false,
});
```

## React Hooks

### useWallet

Manage wallet with automatic balance updates.

```typescript
const { wallet, balance, loading, error, createWallet, importWallet, deleteWallet, refreshBalance } = useWallet({
  client,
  autoRefreshBalance: true,
  refreshInterval: 30000,
});
```

### useBalance

Monitor wallet balance.

```typescript
const { balance, loading, error, refresh } = useBalance({
  client,
  address: wallet?.address,
  autoRefresh: true,
  refreshInterval: 30000,
});
```

### useTransactions

Send and track transactions.

```typescript
const { transactions, loading, error, sendTransaction, getTransaction, refresh } = useTransactions({
  client,
  address: wallet?.address,
  autoRefresh: true,
  refreshInterval: 15000,
});

// Send transaction
const tx = await sendTransaction({
  from: wallet.address,
  to: recipient,
  value: amount,
});
```

### useBlockchain

Monitor blockchain state.

```typescript
const { info, latestBlock, loading, error, refresh, getBlock } = useBlockchain({
  client,
  autoRefresh: true,
  refreshInterval: 10000,
});
```

## Security Best Practices

### Key Storage

- Private keys are encrypted with a random password
- Password is stored in hardware-backed keychain
- Master encryption key is generated on first use
- Never store private keys in plain text

### Biometric Authentication

- Enable biometric auth for sensitive operations
- Fallback to device PIN/password if biometric fails
- Keys are stored in secure enclave (iOS) or keystore (Android)

### Transaction Signing

```typescript
// Always verify before signing
const { fee } = await client.estimateFee(params);
Alert.alert('Confirm', `Fee: ${fee} XAI`, [
  { text: 'Cancel' },
  { text: 'Confirm', onPress: () => sendTransaction(params) }
]);
```

## Error Handling

All SDK methods throw typed errors:

```typescript
import { WalletError, NetworkError, BiometricError } from '@xai/react-native-sdk';

try {
  await wallet.createWallet();
} catch (error) {
  if (error instanceof WalletError) {
    console.error('Wallet error:', error.message);
  } else if (error instanceof NetworkError) {
    console.error('Network error:', error.message);
  } else if (error instanceof BiometricError) {
    console.error('Biometric error:', error.message);
  }
}
```

## Testing

```bash
npm test
npm run test:coverage
```

## Examples

See the `/examples` directory for complete examples:

- Basic wallet creation
- Transaction sending
- Biometric authentication
- Push notifications
- Multi-wallet management

## TypeScript

Full TypeScript support with complete type definitions:

```typescript
import type {
  Wallet,
  Transaction,
  Block,
  BlockchainInfo,
  SendTransactionParams,
} from '@xai/react-native-sdk';
```

## License

MIT

## Contributing

Contributions are welcome! Please read the contributing guidelines before submitting PRs.

## Support

- GitHub Issues: https://github.com/xai-blockchain/xai/issues
- Documentation: https://xai-blockchain.io/docs
- Discord: https://discord.gg/xai

## Related Projects

- [@xai/sdk](../typescript) - TypeScript/JavaScript SDK for Node.js and browsers
- [XAI Mobile App](../../mobile-app) - Reference React Native application
- [XAI Browser Extension](../../browser-wallet-extension) - Browser wallet extension
