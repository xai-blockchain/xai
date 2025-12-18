# XAI SDK API Documentation

Complete API reference for the XAI Flutter SDK.

## Table of Contents

- [XAIClient](#xaiclient)
- [XAIWallet](#xaiwallet)
- [XAITransaction](#xaitransaction)
- [BiometricAuth](#biometricauth)
- [PushNotifications](#pushnotifications)
- [CryptoUtils](#cryptoutils)
- [Models](#models)

---

## XAIClient

Main HTTP/WebSocket client for blockchain communication.

### Constructor

```dart
XAIClient({
  required XAIClientConfig config,
  http.Client? httpClient,
})
```

### Configuration

```dart
class XAIClientConfig {
  final String baseUrl;           // HTTP API endpoint
  final String? wsUrl;            // WebSocket endpoint (optional)
  final Duration timeout;         // Request timeout
  final int retryAttempts;        // Number of retry attempts
  final Duration retryDelay;      // Initial retry delay
  final Map<String, String>? headers;  // Custom headers
}
```

### Methods

#### Node Information

```dart
Future<NodeInfo> getNodeInfo()
```
Returns blockchain node information including version, block height, peer count, and sync status.

**Returns:** `NodeInfo` object
**Throws:** `Exception` if request fails

---

#### Balance

```dart
Future<double> getBalance(String address)
```
Get balance for a specific address.

**Parameters:**
- `address` - XAI address to query

**Returns:** Balance in XAI tokens
**Throws:** `Exception` if address is invalid or request fails

---

#### Nonce

```dart
Future<NonceResponse> getNonce(String address)
```
Get nonce information for an address (for transaction ordering).

**Parameters:**
- `address` - XAI address to query

**Returns:** `NonceResponse` with confirmed, next, and pending nonces
**Throws:** `Exception` if request fails

---

#### Transaction History

```dart
Future<TransactionHistory> getHistory(
  String address, {
  int limit = 50,
  int offset = 0,
})
```
Get transaction history for an address with pagination.

**Parameters:**
- `address` - XAI address to query
- `limit` - Maximum number of transactions to return (default: 50)
- `offset` - Number of transactions to skip (default: 0)

**Returns:** `TransactionHistory` with paginated transactions
**Throws:** `Exception` if request fails

---

#### Get Transaction

```dart
Future<Transaction?> getTransaction(String txid)
```
Get a specific transaction by ID.

**Parameters:**
- `txid` - Transaction ID to query

**Returns:** `Transaction` object or `null` if not found
**Throws:** `Exception` if request fails

---

#### Pending Transactions

```dart
Future<List<Transaction>> getPendingTransactions({
  int limit = 50,
  int offset = 0,
})
```
Get pending (unconfirmed) transactions.

**Parameters:**
- `limit` - Maximum transactions to return
- `offset` - Number to skip

**Returns:** List of pending `Transaction` objects
**Throws:** `Exception` if request fails

---

#### Send Transaction

```dart
Future<SendTransactionResponse> sendTransaction(Transaction tx)
```
Send a signed transaction to the network.

**Parameters:**
- `tx` - Signed `Transaction` object

**Returns:** `SendTransactionResponse` with success status and txid
**Throws:** `Exception` if request fails

---

#### Blocks

```dart
Future<Block?> getBlock(int index)
```
Get a specific block by index.

**Parameters:**
- `index` - Block index

**Returns:** `Block` object or `null` if not found

---

```dart
Future<Block?> getLatestBlock()
```
Get the latest block in the chain.

**Returns:** Latest `Block` object or `null` if unavailable

---

```dart
Future<List<Block>> getBlocks({
  int limit = 10,
  int offset = 0,
})
```
Get blocks with pagination.

**Parameters:**
- `limit` - Maximum blocks to return
- `offset` - Number to skip

**Returns:** List of `Block` objects

---

#### Chain Statistics

```dart
Future<ChainStats?> getChainStats()
```
Get blockchain statistics.

**Returns:** `ChainStats` object with network statistics

---

#### WebSocket

```dart
Future<void> connectWebSocket()
```
Connect to WebSocket for real-time updates.

**Throws:** `Exception` if connection fails

---

```dart
Future<void> disconnectWebSocket()
```
Disconnect from WebSocket.

---

### Properties

```dart
Stream<Block> get blockStream
```
Stream of new blocks received via WebSocket.

---

```dart
Stream<Transaction> get transactionStream
```
Stream of new transactions received via WebSocket.

---

```dart
Stream<String> get errorStream
```
Stream of WebSocket errors.

---

### Cleanup

```dart
void dispose()
```
Close all connections and cleanup resources. Must be called when done.

---

## XAIWallet

Secure wallet management with flutter_secure_storage.

### Constructor

```dart
XAIWallet({FlutterSecureStorage? secureStorage})
```

### Methods

#### Create Wallet

```dart
Future<Wallet> createWallet({
  String? name,
  bool setAsDefault = false,
})
```
Generate a new wallet with ECDSA key pair.

**Parameters:**
- `name` - Optional wallet name
- `setAsDefault` - Set as default wallet

**Returns:** Created `Wallet` object (without private key)
**Throws:** `Exception` if creation fails

---

#### Import Wallet

```dart
Future<Wallet> importWallet({
  required String privateKey,
  String? name,
  bool setAsDefault = false,
})
```
Import a wallet from a private key.

**Parameters:**
- `privateKey` - Private key in hex format
- `name` - Optional wallet name
- `setAsDefault` - Set as default wallet

**Returns:** Imported `Wallet` object
**Throws:** `ArgumentError` if private key is invalid
**Throws:** `Exception` if wallet already exists

---

#### Get Wallets

```dart
Future<List<Wallet>> getWallets()
```
Get all wallets (metadata only, no private keys).

**Returns:** List of `Wallet` objects

---

```dart
Future<Wallet?> getWallet(String walletId)
```
Get a specific wallet by ID.

**Parameters:**
- `walletId` - Wallet UUID

**Returns:** `Wallet` object or `null` if not found

---

```dart
Future<Wallet?> getWalletByAddress(String address)
```
Get wallet by address.

**Parameters:**
- `address` - XAI address

**Returns:** `Wallet` object or `null` if not found

---

```dart
Future<Wallet?> getDefaultWallet()
```
Get the default wallet.

**Returns:** Default `Wallet` or first wallet if no default set

---

#### Manage Wallets

```dart
Future<void> setDefaultWallet(String walletId)
```
Set the default wallet.

**Parameters:**
- `walletId` - Wallet UUID

**Throws:** `Exception` if wallet not found

---

```dart
Future<Wallet> updateWallet(Wallet wallet)
```
Update wallet metadata.

**Parameters:**
- `wallet` - Updated `Wallet` object

**Returns:** Updated `Wallet`
**Throws:** `Exception` if wallet not found

---

```dart
Future<void> deleteWallet(String walletId)
```
Delete a wallet and its private key.

**Parameters:**
- `walletId` - Wallet UUID

---

#### Private Keys

```dart
Future<String?> getPrivateKey(String walletId)
```
Get private key for a wallet. **Use with caution!**

**Parameters:**
- `walletId` - Wallet UUID

**Returns:** Private key in hex format or `null` if not found

---

```dart
Future<WalletKeyPair?> getKeyPair(String walletId)
```
Get complete key pair for a wallet.

**Parameters:**
- `walletId` - Wallet UUID

**Returns:** `WalletKeyPair` with private key, public key, and address

---

#### Export/Import

```dart
Future<Map<String, dynamic>> exportWallet(String walletId)
```
Export wallet as JSON including private key. **Use with extreme caution!**

**Parameters:**
- `walletId` - Wallet UUID

**Returns:** JSON object with all wallet data including private key
**Throws:** `Exception` if wallet not found

---

#### Biometric

```dart
Future<Wallet> enableBiometric(String walletId)
```
Enable biometric authentication for wallet.

**Parameters:**
- `walletId` - Wallet UUID

**Returns:** Updated `Wallet` with biometric enabled
**Throws:** `Exception` if wallet not found

---

```dart
Future<Wallet> disableBiometric(String walletId)
```
Disable biometric authentication for wallet.

**Parameters:**
- `walletId` - Wallet UUID

**Returns:** Updated `Wallet` with biometric disabled

---

#### Cleanup

```dart
Future<void> clearAllWallets()
```
Delete all wallets and private keys. **Use with extreme caution!**

---

## XAITransaction

Transaction building, signing, and validation.

### Constructor

```dart
XAITransaction({
  required XAIClient client,
  required XAIWallet wallet,
})
```

### Methods

#### Build Transactions

```dart
Future<Transaction> buildTransfer({
  required String senderAddress,
  required String recipientAddress,
  required double amount,
  double fee = 0.0001,
  Map<String, dynamic>? metadata,
})
```
Build a simple transfer transaction.

**Parameters:**
- `senderAddress` - Sender XAI address
- `recipientAddress` - Recipient XAI address
- `amount` - Amount to send
- `fee` - Transaction fee (default: 0.0001)
- `metadata` - Optional metadata

**Returns:** Unsigned `Transaction`
**Throws:** `ArgumentError` if parameters invalid
**Throws:** `Exception` if insufficient balance

---

```dart
Future<Transaction> buildUTXOTransaction({
  required String senderAddress,
  required List<TransactionInput> inputs,
  required List<TransactionOutput> outputs,
  double fee = 0.0001,
  Map<String, dynamic>? metadata,
})
```
Build a transaction with specific UTXO inputs and outputs.

**Parameters:**
- `senderAddress` - Sender XAI address
- `inputs` - List of UTXO inputs
- `outputs` - List of UTXO outputs
- `fee` - Transaction fee
- `metadata` - Optional metadata

**Returns:** Unsigned `Transaction`
**Throws:** `ArgumentError` if inputs/outputs invalid

---

#### Sign Transactions

```dart
Future<Transaction> signTransaction({
  required Transaction transaction,
  required String walletId,
})
```
Sign a transaction with wallet's private key.

**Parameters:**
- `transaction` - Unsigned transaction
- `walletId` - Wallet UUID to sign with

**Returns:** Signed `Transaction`
**Throws:** `Exception` if wallet not found or signing fails

---

```dart
Future<Transaction> signTransactionByAddress({
  required Transaction transaction,
  required String address,
})
```
Sign transaction by address (finds wallet automatically).

**Parameters:**
- `transaction` - Unsigned transaction
- `address` - Sender address

**Returns:** Signed `Transaction`
**Throws:** `Exception` if wallet not found

---

#### Send Transactions

```dart
Future<SendTransactionResponse> sendSignedTransaction(
  Transaction transaction,
)
```
Send a signed transaction to the network.

**Parameters:**
- `transaction` - Signed transaction

**Returns:** `SendTransactionResponse`
**Throws:** `Exception` if transaction not signed

---

#### Convenience Methods

```dart
Future<Transaction> buildAndSignTransfer({
  required String senderAddress,
  required String recipientAddress,
  required double amount,
  double fee = 0.0001,
  Map<String, dynamic>? metadata,
})
```
Build and sign a transfer in one step.

**Returns:** Signed `Transaction`

---

```dart
Future<SendTransactionResponse> transferAndSend({
  required String senderAddress,
  required String recipientAddress,
  required double amount,
  double fee = 0.0001,
  Map<String, dynamic>? metadata,
})
```
Build, sign, and send a transaction in one step.

**Returns:** `SendTransactionResponse`

---

#### Utilities

```dart
bool verifySignature(Transaction transaction)
```
Verify a transaction's signature.

**Parameters:**
- `transaction` - Transaction to verify

**Returns:** `true` if signature is valid

---

```dart
Future<double> estimateFee({
  int inputCount = 1,
  int outputCount = 1,
  int? metadataSize,
})
```
Estimate transaction fee.

**Returns:** Estimated fee in XAI

---

```dart
Future<Transaction?> waitForConfirmation({
  required String txid,
  int requiredConfirmations = 1,
  Duration timeout = const Duration(minutes: 5),
  Duration pollInterval = const Duration(seconds: 5),
})
```
Wait for transaction confirmation.

**Parameters:**
- `txid` - Transaction ID to monitor
- `requiredConfirmations` - Number of confirmations needed
- `timeout` - Maximum time to wait
- `pollInterval` - Polling interval

**Returns:** Confirmed `Transaction` or `null` if timeout

---

```dart
Future<List<String>> validateTransaction(Transaction transaction)
```
Validate transaction before sending.

**Parameters:**
- `transaction` - Transaction to validate

**Returns:** List of validation errors (empty if valid)

---

## BiometricAuth

Biometric authentication wrapper.

### Constructor

```dart
BiometricAuth({LocalAuthentication? auth})
```

### Methods

#### Availability

```dart
Future<bool> isAvailable()
```
Check if biometric authentication is available.

**Returns:** `true` if available

---

```dart
Future<List<BiometricType>> getAvailableBiometrics()
```
Get available biometric types.

**Returns:** List of `BiometricType` (faceId, touchId, fingerprint, etc.)

---

```dart
Future<BiometricCapability> getCapability()
```
Get detailed biometric capability information.

**Returns:** `BiometricCapability` object

---

#### Authenticate

```dart
Future<BiometricAuthResult> authenticate({
  required String localizedReason,
  bool useErrorDialogs = true,
  bool stickyAuth = true,
})
```
Authenticate user with biometrics.

**Parameters:**
- `localizedReason` - Message explaining why authentication is needed
- `useErrorDialogs` - Show error dialogs
- `stickyAuth` - Keep authentication active

**Returns:** `BiometricAuthResult`

---

```dart
Future<bool> authenticateForTransaction({
  required double amount,
  required String recipient,
})
```
Authenticate for transaction signing.

**Returns:** `true` if authenticated

---

```dart
Future<bool> authenticateForWalletAccess({String? walletName})
```
Authenticate for wallet access.

**Returns:** `true` if authenticated

---

```dart
Future<bool> authenticateForKeyExport()
```
Authenticate for private key export.

**Returns:** `true` if authenticated

---

```dart
Future<void> stopAuthentication()
```
Cancel ongoing authentication.

---

## PushNotifications

Firebase Cloud Messaging integration.

### Constructor

```dart
PushNotifications({
  FirebaseMessaging? messaging,
  FlutterLocalNotificationsPlugin? localNotifications,
})
```

### Methods

#### Initialize

```dart
Future<void> initialize()
```
Initialize push notifications. Must be called before use.

**Throws:** `Exception` if permissions denied or initialization fails

---

#### Token Management

```dart
String? get currentToken
```
Get current FCM token.

---

```dart
Stream<String> get tokenStream
```
Stream of FCM token updates.

---

```dart
Future<void> deleteToken()
```
Delete FCM token (for logout).

---

#### Subscriptions

```dart
Future<void> subscribeToAddress(String address)
```
Subscribe to notifications for an address.

---

```dart
Future<void> unsubscribeFromAddress(String address)
```
Unsubscribe from address notifications.

---

```dart
Future<void> subscribeToBlocks()
Future<void> unsubscribeFromBlocks()
Future<void> subscribeToPriceAlerts()
Future<void> subscribeToSecurityAlerts()
```
Subscribe/unsubscribe to various notification topics.

---

#### Permissions

```dart
Future<AuthorizationStatus> getPermissionStatus()
```
Get notification permission status.

---

```dart
Future<bool> requestPermissions()
```
Request notification permissions.

**Returns:** `true` if granted

---

```dart
Future<bool> areNotificationsEnabled()
```
Check if notifications are enabled.

---

#### Notifications

```dart
Stream<NotificationMessage> get notificationStream
```
Stream of incoming notifications.

---

```dart
Future<void> clearAllNotifications()
```
Clear all notifications.

---

```dart
Future<void> clearNotification(int id)
```
Clear specific notification.

---

## CryptoUtils

Cryptographic utilities for ECDSA operations.

### Static Methods

```dart
static Map<String, String> generateKeyPair()
```
Generate a new ECDSA key pair (secp256k1).

**Returns:** Map with `privateKey` and `publicKey` in hex

---

```dart
static String derivePublicKey(String privateKeyHex)
```
Derive public key from private key.

**Parameters:**
- `privateKeyHex` - Private key in hex

**Returns:** Public key in hex
**Throws:** `CryptoException` if derivation fails

---

```dart
static String signMessage(String message, String privateKeyHex)
```
Sign a message with ECDSA.

**Parameters:**
- `message` - Message to sign
- `privateKeyHex` - Private key in hex

**Returns:** Signature in hex (r + s)
**Throws:** `CryptoException` if signing fails

---

```dart
static bool verifySignature(
  String message,
  String signatureHex,
  String publicKeyHex,
)
```
Verify ECDSA signature.

**Parameters:**
- `message` - Original message
- `signatureHex` - Signature in hex
- `publicKeyHex` - Public key in hex

**Returns:** `true` if signature is valid

---

```dart
static String publicKeyToAddress(String publicKeyHex)
```
Generate XAI address from public key.

**Parameters:**
- `publicKeyHex` - Public key in hex

**Returns:** XAI address (XAI + base58check)
**Throws:** `CryptoException` if generation fails

---

```dart
static bool isValidAddress(String address)
```
Validate XAI address format.

**Parameters:**
- `address` - Address to validate

**Returns:** `true` if valid

---

```dart
static String sha256Hash(String data)
```
Hash data with SHA-256.

**Parameters:**
- `data` - Data to hash

**Returns:** Hex-encoded hash

---

## Models

### Transaction

Complete transaction with UTXO support.

```dart
class Transaction {
  final String? txid;
  final String sender;
  final String recipient;
  final double amount;
  final double fee;
  final String? publicKey;
  final String? signature;
  final String txType;
  final int nonce;
  final List<TransactionInput> inputs;
  final List<TransactionOutput> outputs;
  final Map<String, dynamic>? metadata;
  final int timestamp;
  final TransactionStatus status;
  final int? confirmations;
}
```

### Wallet

Wallet metadata (no private key).

```dart
class Wallet {
  final String id;
  final String name;
  final String address;
  final String publicKey;
  final DateTime createdAt;
  final DateTime? lastUsedAt;
  final bool isDefault;
  final bool biometricEnabled;
}
```

### Block

Blockchain block.

```dart
class Block {
  final int index;
  final String hash;
  final String previousHash;
  final int timestamp;
  final int nonce;
  final String merkleRoot;
  final List<Transaction> transactions;
  final String? miner;
  final int? difficulty;
}
```

### NodeInfo

Node information.

```dart
class NodeInfo {
  final String version;
  final int blockHeight;
  final String networkId;
  final int peerCount;
  final bool syncing;
  final String? syncTarget;
}
```

---

For more examples and usage, see the [README](README.md) and [example app](example/).
