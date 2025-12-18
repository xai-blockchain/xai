# XAI TypeScript/JavaScript SDK

Production-ready TypeScript/JavaScript SDK for the XAI blockchain. Provides comprehensive access to wallet operations, transactions, mining, governance, and real-time blockchain events.

## Features

- **Full TypeScript Support** - Complete type definitions for all operations
- **Async/Await Patterns** - Modern promise-based API
- **Automatic Retries** - Exponential backoff for failed requests
- **Connection Pooling** - Efficient HTTP connection management
- **WebSocket Support** - Real-time blockchain event streaming
- **Comprehensive Error Handling** - Typed exceptions for all error cases
- **Browser & Node.js** - Works in both environments
- **Zero Dependencies** - Minimal production dependencies (axios, ws)

## Installation

```bash
npm install @xai/sdk
```

or with yarn:

```bash
yarn add @xai/sdk
```

## Quick Start

```typescript
import { XAIClient } from '@xai/sdk';

// Create client
const client = new XAIClient({
  baseUrl: 'http://localhost:5000',
  apiKey: 'your-api-key', // optional
});

// Create a wallet
const wallet = await client.wallet.create();
console.log('New wallet address:', wallet.address);

// Check balance
const balance = await client.wallet.getBalance(wallet.address);
console.log('Balance:', balance.balance);

// Send a transaction
const tx = await client.transaction.send({
  from: wallet.address,
  to: '0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb',
  amount: '1000',
});
console.log('Transaction hash:', tx.hash);

// Wait for confirmation
const confirmedTx = await client.transaction.waitForConfirmation(tx.hash, 3);
console.log('Transaction confirmed!');
```

## Configuration

```typescript
const client = new XAIClient({
  baseUrl: 'http://localhost:5000',    // API base URL
  apiKey: 'your-api-key',              // Optional API key
  timeout: 30000,                       // Request timeout (ms)
  maxRetries: 3,                        // Max retry attempts
  retryDelay: 500,                      // Initial retry delay (ms)
});
```

## API Reference

### Wallet Operations

```typescript
// Create a new wallet
const wallet = await client.wallet.create({
  walletType: WalletType.STANDARD,
  name: 'My Wallet',
});

// Get wallet information
const walletInfo = await client.wallet.get(wallet.address);

// Get wallet balance
const balance = await client.wallet.getBalance(wallet.address);
console.log('Balance:', balance.balance);
console.log('Available:', balance.availableBalance);
console.log('Locked:', balance.lockedBalance);

// Get transaction history
const history = await client.wallet.getTransactions({
  address: wallet.address,
  limit: 20,
  offset: 0,
});
console.log('Transactions:', history.data);
console.log('Total:', history.total);

// Create embedded wallet
const embeddedWallet = await client.wallet.createEmbedded({
  appId: 'my-app',
  userId: 'user-123',
  metadata: { email: 'user@example.com' },
});

// Login to embedded wallet
const session = await client.wallet.loginEmbedded({
  walletId: 'wallet-id',
  password: 'secure-password',
});
```

### Transaction Operations

```typescript
// Send a transaction
const tx = await client.transaction.send({
  from: '0x1234...',
  to: '0x5678...',
  amount: '1000',
  data: '0x...', // optional
  gasLimit: '21000', // optional
  gasPrice: '1', // optional
});

// Get transaction details
const transaction = await client.transaction.get(tx.hash);
console.log('Status:', transaction.status);
console.log('Confirmations:', transaction.confirmations);
console.log('Block:', transaction.blockNumber);

// Estimate transaction fee
const feeEstimate = await client.transaction.estimateFee({
  from: '0x1234...',
  to: '0x5678...',
  amount: '1000',
});
console.log('Estimated fee:', feeEstimate.estimatedFee);
console.log('Gas limit:', feeEstimate.gasLimit);

// Check if transaction is confirmed
const isConfirmed = await client.transaction.isConfirmed(tx.hash, 3);

// Wait for confirmation (with timeout)
const confirmedTx = await client.transaction.waitForConfirmation(
  tx.hash,
  3,      // confirmations
  600000, // timeout (ms)
  5000    // poll interval (ms)
);

// Get pending transactions
const pending = await client.transaction.getPending();
```

### Blockchain Operations

```typescript
// Get block by number
const block = await client.blockchain.getBlock(1000);
console.log('Block hash:', block.hash);
console.log('Miner:', block.miner);
console.log('Transactions:', block.transactions);

// List recent blocks
const blocks = await client.blockchain.listBlocks({
  limit: 10,
  offset: 0,
});

// Get block transactions
const blockTxs = await client.blockchain.getBlockTransactions(1000);

// Get blockchain statistics
const stats = await client.blockchain.getStats();
console.log('Total blocks:', stats.totalBlocks);
console.log('Total transactions:', stats.totalTransactions);
console.log('Network hashrate:', stats.hashrate);

// Check sync status
const syncStatus = await client.blockchain.getSyncStatus();
if (syncStatus.syncing) {
  console.log('Syncing:', syncStatus.syncProgress + '%');
}

// Check if synced
const isSynced = await client.blockchain.isSynced();

// Get node info
const nodeInfo = await client.blockchain.getNodeInfo();
console.log('Node version:', nodeInfo.version);

// Health check
const health = await client.blockchain.getHealth();
console.log('Status:', health.status);
```

### Mining Operations

```typescript
// Start mining
await client.mining.start(4); // 4 threads

// Stop mining
await client.mining.stop();

// Get mining status
const status = await client.mining.getStatus();
console.log('Mining:', status.mining);
console.log('Hashrate:', status.hashrate);
console.log('Blocks found:', status.blocksFound);
console.log('Difficulty:', status.currentDifficulty);

// Get mining rewards
const rewards = await client.mining.getRewards('0x1234...');
console.log('Total rewards:', rewards.totalRewards);
console.log('Pending rewards:', rewards.pendingRewards);

// Check if mining
const isMining = await client.mining.isMining();

// Get current difficulty
const difficulty = await client.mining.getDifficulty();

// Get current hashrate
const hashrate = await client.mining.getHashrate();
```

### Governance Operations

```typescript
// List proposals
const proposals = await client.governance.listProposals({
  status: 'active',
  limit: 10,
  offset: 0,
});

// Get proposal details
const proposal = await client.governance.getProposal(1);
console.log('Title:', proposal.title);
console.log('Votes for:', proposal.votesFor);
console.log('Votes against:', proposal.votesAgainst);

// Create a proposal
const newProposal = await client.governance.createProposal({
  title: 'Upgrade Protocol',
  description: 'Propose upgrading the protocol to v2.0',
  proposer: '0x1234...',
  duration: 604800, // 7 days in seconds
});

// Vote on a proposal
await client.governance.vote(1, '0x1234...', VoteChoice.YES);

// Get active proposals
const activeProposals = await client.governance.getActiveProposals();

// Get proposal votes
const votes = await client.governance.getProposalVotes(1);
console.log('Total votes:', votes.totalVotes);
```

## WebSocket Real-Time Events

```typescript
// Connect to WebSocket
client.connectWebSocket('ws://localhost:5000/ws');

// Listen for new blocks
client.on('new_block', (block) => {
  console.log('New block mined:', block);
});

// Listen for new transactions
client.on('new_transaction', (transaction) => {
  console.log('New transaction:', transaction);
});

// Listen for transaction confirmations
client.on('transaction_confirmed', (data) => {
  console.log('Transaction confirmed:', data);
});

// Listen for mining events
client.on('mining_block_found', (block) => {
  console.log('Block found by miner:', block);
});

// Listen for governance events
client.on('proposal_created', (proposal) => {
  console.log('New proposal:', proposal);
});

client.on('proposal_vote', (vote) => {
  console.log('New vote:', vote);
});

// Handle connection events
client.on('connected', () => {
  console.log('WebSocket connected');
});

client.on('disconnected', ({ code, reason }) => {
  console.log('WebSocket disconnected:', code, reason);
});

client.on('error', (error) => {
  console.error('WebSocket error:', error);
});

// Disconnect WebSocket
client.disconnectWebSocket();
```

## Error Handling

The SDK provides typed exceptions for different error scenarios:

```typescript
import {
  XAIError,
  AuthenticationError,
  ValidationError,
  NotFoundError,
  RateLimitError,
  NetworkError,
  TimeoutError,
  TransactionError,
  WalletError,
  MiningError,
  GovernanceError,
} from '@xai/sdk';

try {
  const wallet = await client.wallet.create();
} catch (error) {
  if (error instanceof ValidationError) {
    console.error('Validation failed:', error.message);
  } else if (error instanceof AuthenticationError) {
    console.error('Authentication failed:', error.message);
  } else if (error instanceof RateLimitError) {
    console.error('Rate limit exceeded. Retry after:', error.retryAfter);
  } else if (error instanceof WalletError) {
    console.error('Wallet operation failed:', error.message);
  } else {
    console.error('Unknown error:', error);
  }
}
```

## TypeScript Types

All operations are fully typed:

```typescript
import {
  Wallet,
  Balance,
  Transaction,
  Block,
  Proposal,
  MiningStatus,
  BlockchainStats,
  TransactionStatus,
  WalletType,
  ProposalStatus,
  VoteChoice,
} from '@xai/sdk';
```

## Browser Usage

The SDK works in browsers with a bundler (Webpack, Rollup, etc.):

```typescript
import { XAIClient } from '@xai/sdk';

const client = new XAIClient({
  baseUrl: 'https://api.xai-blockchain.io',
});

// WebSocket will work automatically in browsers
client.connectWebSocket('wss://api.xai-blockchain.io/ws');
```

## Advanced Usage

### Custom HTTP Configuration

```typescript
import { XAIClient } from '@xai/sdk';

const client = new XAIClient({
  baseUrl: 'http://localhost:5000',
  timeout: 60000, // 60 seconds
  maxRetries: 5,
  retryDelay: 1000, // 1 second initial delay
});
```

### Cleanup Resources

```typescript
// Always close the client when done
client.close();

// Or use try-finally
try {
  const wallet = await client.wallet.create();
  // ... operations
} finally {
  client.close();
}
```

### Checking WebSocket Connection

```typescript
if (client.isWebSocketConnected()) {
  console.log('WebSocket is connected');
}
```

## Development

### Build

```bash
npm run build
```

### Test

```bash
npm test
```

### Lint

```bash
npm run lint
```

### Format

```bash
npm run format
```

## License

MIT

## Support

For issues and questions:
- GitHub Issues: https://github.com/xai-blockchain/xai/issues
- Documentation: https://xai-blockchain.io/docs
- Support: support@xai-blockchain.io
