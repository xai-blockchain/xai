# XAI TypeScript/JavaScript SDK

Production-ready TypeScript/JavaScript SDK for the XAI blockchain. Provides complete type-safe access to blockchain functionality including wallet management, transactions, querying, mining, and governance.

## Features

- **Full TypeScript Support** - Complete type definitions for all APIs
- **Wallet Management** - Create, import, and manage wallets with BIP39 mnemonic support
- **Transaction Building** - Fluent API for building and signing transactions
- **Blockchain Queries** - Query blocks, transactions, and network state
- **WebSocket Support** - Real-time event subscriptions
- **Automatic Retries** - Exponential backoff for failed requests
- **Error Handling** - Comprehensive typed error classes
- **Browser & Node.js** - Works in both environments
- **Multiple Export Formats** - CommonJS and ESM builds

## Installation

```bash
npm install @xai/sdk
```

## Quick Start

```typescript
import { XAIClient, Wallet } from '@xai/sdk';

// Initialize client
const client = new XAIClient({
  baseUrl: 'http://localhost:12001'
});

// Create a wallet
const wallet = client.wallet.create();
console.log('Address:', wallet.address);

// Get balance
const balance = await client.wallet.getBalance(wallet.address);
console.log('Balance:', balance.balance, 'XAI');

// Send a transaction
const result = await client.transaction.send(
  wallet,
  'XAI0000000000000000000000000000000000000000',
  10,
  { fee: 0.1 }
);
console.log('Transaction ID:', result.txid);
```

## Wallet Management

### Create a New Wallet

```typescript
const wallet = Wallet.create();
console.log('Address:', wallet.address);
console.log('Public Key:', wallet.publicKey);
```

### Import from Private Key

```typescript
const wallet = Wallet.fromPrivateKey(privateKeyHex);
```

### Import from Mnemonic

```typescript
// Generate mnemonic
const mnemonic = Wallet.generateMnemonic();

// Import wallet
const wallet = await Wallet.fromMnemonic(mnemonic, 0);

// Derive multiple wallets from same mnemonic
const wallet1 = await Wallet.fromMnemonic(mnemonic, 0);
const wallet2 = await Wallet.fromMnemonic(mnemonic, 1);
```

### Sign Messages

```typescript
const signature = await wallet.sign('Hello XAI');
```

### Export Wallet

```typescript
// Export without private key
const publicExport = wallet.export(false);

// Export with private key
const fullExport = wallet.export(true);
```

## Transactions

### Build and Sign Transaction

```typescript
const tx = await client.transaction
  .build(senderAddress, recipientAddress, amount)
  .setFee(0.1)
  .setNonce(5)
  .setMetadata({ note: 'Payment for services' })
  .enableRBF()
  .sign(wallet);
```

### Send Transaction (Automatic)

```typescript
// Automatically handles nonce and fee estimation
const result = await client.transaction.send(
  wallet,
  recipientAddress,
  amount,
  {
    fee: 0.1,  // Optional - will estimate if not provided
    metadata: { note: 'Payment' }
  }
);

if (result.success) {
  console.log('Transaction sent:', result.txid);
} else {
  console.error('Transaction failed:', result.error);
}
```

### Broadcast Pre-Signed Transaction

```typescript
const result = await client.transaction.broadcast(signedTx);
```

### Query Transactions

```typescript
// Get transaction by ID
const tx = await client.transaction.getTransaction(txid);

// Get pending transactions
const pending = await client.transaction.getPending(50, 0);

// Get transaction history for address
const history = await client.wallet.getHistory(address, 100, 0);
```

### Fee Estimation

```typescript
const fees = await client.transaction.estimateFee();
console.log('Recommended fee:', fees.recommended);
console.log('Fast:', fees.fast);
console.log('Medium:', fees.medium);
console.log('Slow:', fees.slow);
```

## Blockchain Queries

### Get Blockchain Info

```typescript
const info = await client.blockchain.getInfo();
console.log('Height:', info.height);
console.log('Difficulty:', info.difficulty);
console.log('Total Transactions:', info.total_transactions);
```

### Query Blocks

```typescript
// Get latest block
const latest = await client.blockchain.getLatestBlock();

// Get block by index
const block = await client.blockchain.getBlock(100);

// Get block by hash
const block = await client.blockchain.getBlockByHash(hash);

// Get blocks with pagination
const blocks = await client.blockchain.getBlocks(10, 0);
```

### Mempool

```typescript
const mempool = await client.blockchain.getMempool();
console.log('Pending transactions:', mempool.size);

const stats = await client.blockchain.getMempoolStats();
console.log('Mempool usage:', stats.usage);
```

### Network Info

```typescript
const network = await client.blockchain.getNetworkInfo();
console.log('Peers:', network.peer_count);

const syncStatus = await client.blockchain.getSyncStatus();
console.log('Syncing:', syncStatus.syncing);
console.log('Progress:', syncStatus.progress_percentage + '%');
```

### Health Check

```typescript
const health = await client.blockchain.getHealth();
console.log('Status:', health.status);
console.log('Version:', health.version);
console.log('Uptime:', health.uptime);
```

## WebSocket Events

### Subscribe to Events

```typescript
// Connect WebSocket
await client.connectWebSocket();

// Subscribe to new blocks
const unsubscribe = client.subscribe('new_block', (block) => {
  console.log('New block:', block.index);
});

// Subscribe to new transactions
client.subscribe('new_transaction', (tx) => {
  console.log('New transaction:', tx.txid);
});

// Unsubscribe
unsubscribe();

// Disconnect
client.disconnectWebSocket();
```

## Mining

```typescript
// Start mining
await client.mining.start(minerAddress);

// Mine a single block
const result = await client.mining.mineBlock(minerAddress);

// Get mining status
const status = await client.mining.getStatus();
console.log('Mining enabled:', status.mining_enabled);

// Enable auto-mining
await client.mining.enableAutoMine(minerAddress, 10000); // 10 second interval

// Disable auto-mining
await client.mining.disableAutoMine();
```

## Governance

```typescript
// Get proposals
const proposals = await client.governance.getProposals();

// Get specific proposal
const proposal = await client.governance.getProposal(proposalId);

// Create proposal
const result = await client.governance.createProposal(
  'Increase block reward',
  'Detailed description...',
  proposerAddress
);

// Vote on proposal
await client.governance.vote(
  proposalId,
  voterAddress,
  'yes',
  signature
);

// Get votes
const votes = await client.governance.getVotes(proposalId);

// Execute passed proposal
await client.governance.executeProposal(proposalId);
```

## Error Handling

```typescript
import { 
  NetworkError, 
  ValidationError, 
  NotFoundError,
  TransactionError 
} from '@xai/sdk';

try {
  const tx = await client.transaction.getTransaction(txid);
} catch (error) {
  if (error instanceof NotFoundError) {
    console.error('Transaction not found');
  } else if (error instanceof NetworkError) {
    console.error('Network error:', error.message);
  } else if (error instanceof ValidationError) {
    console.error('Validation error:', error.message);
  }
}
```

## Configuration

```typescript
const client = new XAIClient({
  baseUrl: 'http://localhost:12001',           // Required
  wsUrl: 'ws://localhost:12003/ws',            // Optional
  timeout: 30000,                             // Request timeout (ms)
  retries: 3,                                 // Number of retries
  retryDelay: 1000,                           // Base retry delay (ms)
  apiKey: 'your-api-key'                      // Optional API key
});
```

## TypeScript Types

All types are exported and fully documented:

```typescript
import type {
  Block,
  Transaction,
  SignedTransaction,
  Balance,
  WalletKeyPair,
  FeeEstimate,
  GovernanceProposal,
  // ... and many more
} from '@xai/sdk';
```

## Examples

See the [examples](./examples) directory for complete working examples:

- `basic-usage.ts` - Basic wallet and transaction usage
- `wallet-management.ts` - Wallet creation and import

## Development

```bash
# Install dependencies
npm install

# Build
npm run build

# Run tests
npm test

# Watch mode
npm run dev

# Type checking
npm run typecheck

# Lint
npm run lint
```

## License

MIT

## Links

- [XAI Blockchain](https://xai-blockchain.io)
- [Documentation](https://docs.xai-blockchain.io)
- [GitHub](https://github.com/xai-blockchain/xai)
- [Issues](https://github.com/xai-blockchain/xai/issues)
