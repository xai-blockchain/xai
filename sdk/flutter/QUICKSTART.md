# XAI SDK Quick Start

Get up and running with the XAI SDK in 5 minutes.

## Installation

```yaml
# pubspec.yaml
dependencies:
  xai_sdk:
    path: ../path/to/xai/sdk/flutter
```

```bash
flutter pub get
```

## Basic Example

```dart
import 'package:flutter/material.dart';
import 'package:xai_sdk/xai_sdk.dart';

void main() => runApp(MyApp());

class MyApp extends StatefulWidget {
  @override
  _MyAppState createState() => _MyAppState();
}

class _MyAppState extends State<MyApp> {
  late XAIClient client;
  late XAIWallet walletService;
  late XAITransaction txService;

  Wallet? wallet;
  double balance = 0.0;

  @override
  void initState() {
    super.initState();
    _initialize();
  }

  Future<void> _initialize() async {
    // 1. Initialize client
    client = XAIClient(
      config: XAIClientConfig(
        baseUrl: 'http://localhost:12001',
        wsUrl: 'ws://localhost:12003',
      ),
    );

    // 2. Initialize wallet service
    walletService = XAIWallet();

    // 3. Initialize transaction service
    txService = XAITransaction(
      client: client,
      wallet: walletService,
    );

    // 4. Create or load wallet
    final wallets = await walletService.getWallets();
    if (wallets.isEmpty) {
      wallet = await walletService.createWallet(name: 'My Wallet');
    } else {
      wallet = wallets.first;
    }

    // 5. Load balance
    balance = await client.getBalance(wallet!.address);
    setState(() {});
  }

  Future<void> _sendTransaction() async {
    final response = await txService.transferAndSend(
      senderAddress: wallet!.address,
      recipientAddress: 'XAI...',
      amount: 1.0,
    );

    if (response.success) {
      print('Success: ${response.txid}');
      // Reload balance
      balance = await client.getBalance(wallet!.address);
      setState(() {});
    } else {
      print('Error: ${response.error}');
    }
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      home: Scaffold(
        appBar: AppBar(title: Text('XAI Wallet')),
        body: wallet == null
            ? Center(child: CircularProgressIndicator())
            : Padding(
                padding: EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Address:', style: TextStyle(fontWeight: FontWeight.bold)),
                    Text(wallet!.address),
                    SizedBox(height: 16),
                    Text('Balance:', style: TextStyle(fontWeight: FontWeight.bold)),
                    Text('$balance XAI', style: TextStyle(fontSize: 24)),
                    SizedBox(height: 32),
                    ElevatedButton(
                      onPressed: _sendTransaction,
                      child: Text('Send Transaction'),
                    ),
                  ],
                ),
              ),
      ),
    );
  }

  @override
  void dispose() {
    client.dispose();
    super.dispose();
  }
}
```

## Common Operations

### Create Wallet

```dart
final wallet = await walletService.createWallet(
  name: 'My Wallet',
  setAsDefault: true,
);
```

### Check Balance

```dart
final balance = await client.getBalance(address);
```

### Send Transaction

```dart
final response = await txService.transferAndSend(
  senderAddress: myAddress,
  recipientAddress: recipientAddress,
  amount: 10.0,
);
```

### Get Transaction History

```dart
final history = await client.getHistory(address);
for (final tx in history.transactions) {
  print('${tx.sender} -> ${tx.recipient}: ${tx.amount}');
}
```

### Real-time Updates

```dart
await client.connectWebSocket();

client.transactionStream.listen((tx) {
  print('New transaction: ${tx.txid}');
});

client.blockStream.listen((block) {
  print('New block: ${block.index}');
});
```

### Biometric Authentication

```dart
final biometric = BiometricAuth();

if (await biometric.isAvailable()) {
  final result = await biometric.authenticateForTransaction(
    amount: 10.0,
    recipient: recipientAddress,
  );

  if (result) {
    // Proceed with transaction
  }
}
```

### Push Notifications

```dart
final notifications = PushNotifications();
await notifications.initialize();

// Subscribe to address notifications
await notifications.subscribeToAddress(myAddress);

// Listen for notifications
notifications.notificationStream.listen((notification) {
  print('${notification.title}: ${notification.body}');
});
```

## Error Handling

```dart
try {
  final response = await txService.transferAndSend(...);
  if (response.success) {
    print('Success!');
  } else {
    print('Transaction failed: ${response.error}');
  }
} catch (e) {
  print('Error: $e');
}
```

## Testing

```dart
// Test network connection
try {
  final info = await client.getNodeInfo();
  print('Connected to node v${info.version}');
  print('Block height: ${info.blockHeight}');
} catch (e) {
  print('Connection failed: $e');
}
```

## Security Best Practices

1. **Store private keys securely** - The SDK uses flutter_secure_storage
2. **Validate addresses** before sending
3. **Use biometric auth** for sensitive operations
4. **Use HTTPS** in production
5. **Handle errors** gracefully

## Next Steps

- **Full documentation**: [README.md](README.md)
- **API reference**: [API.md](API.md)
- **Setup guide**: [SETUP.md](SETUP.md)
- **Example app**: [example/](example/)

## Troubleshooting

### "Connection refused"
- Check if node is running
- Verify URL is correct
- For Android emulator, use `10.0.2.2` instead of `localhost`

### "Insufficient balance"
- Check balance: `await client.getBalance(address)`
- Request testnet tokens from faucet

### "Wallet not found"
- Create wallet first: `await walletService.createWallet()`

### "Transaction failed"
- Check error message: `response.error`
- Validate transaction: `await txService.validateTransaction(tx)`

## Support

- GitHub: https://github.com/xai-blockchain/xai
- Issues: https://github.com/xai-blockchain/xai/issues
- Docs: https://xai-blockchain.io/docs
