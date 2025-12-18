# XAI SDK Quick Start Guide

Get started with the XAI TypeScript/JavaScript SDK in 5 minutes.

## Installation

```bash
npm install @xai/sdk
```

## 1. Create a Wallet

```typescript
import { Wallet } from '@xai/sdk';

// Option 1: Generate a new wallet
const wallet = Wallet.create();
console.log('Address:', wallet.address);
console.log('Public Key:', wallet.publicKey);

// Option 2: Import from private key
const importedWallet = Wallet.fromPrivateKey(privateKeyHex);

// Option 3: Use mnemonic (HD wallet)
const mnemonic = Wallet.generateMnemonic();
const hdWallet = await Wallet.fromMnemonic(mnemonic, 0);
```

## 2. Connect to XAI Node

```typescript
import { XAIClient } from '@xai/sdk';

const client = new XAIClient({
  baseUrl: 'http://localhost:5000',
  wsUrl: 'ws://localhost:5000/ws'  // Optional: for real-time events
});
```

## 3. Check Balance

```typescript
const balance = await client.wallet.getBalance(wallet.address);
console.log('Balance:', balance.balance, 'XAI');
```

## 4. Send a Transaction

```typescript
// Simple send (automatic fee and nonce)
const result = await client.transaction.send(
  wallet,
  'XAI0000000000000000000000000000000000000000',
  10,  // amount
  { fee: 0.1 }
);

if (result.success) {
  console.log('Transaction sent:', result.txid);
} else {
  console.error('Failed:', result.error);
}
```

## 5. Build Custom Transaction

```typescript
// Advanced: full control
const tx = await client.transaction
  .build(wallet.address, recipientAddress, 10)
  .setFee(0.1)
  .setNonce(5)
  .setMetadata({ note: 'Payment for services' })
  .sign(wallet);

const result = await client.transaction.broadcast(tx);
```

## 6. Query Blockchain

```typescript
// Get latest block
const block = await client.blockchain.getLatestBlock();
console.log('Block:', block.index, 'Hash:', block.hash);

// Get blockchain info
const info = await client.blockchain.getInfo();
console.log('Height:', info.height, 'Difficulty:', info.difficulty);

// Get mempool
const mempool = await client.blockchain.getMempool();
console.log('Pending transactions:', mempool.size);
```

## 7. Subscribe to Events

```typescript
await client.connectWebSocket();

// Subscribe to new blocks
const unsubscribe = client.subscribe('new_block', (block) => {
  console.log('New block:', block.index);
});

// Unsubscribe when done
unsubscribe();
```

## Complete Example

```typescript
import { XAIClient, Wallet } from '@xai/sdk';

async function main() {
  // 1. Create wallet
  const wallet = Wallet.create();
  console.log('Created wallet:', wallet.address);

  // 2. Connect to node
  const client = new XAIClient({
    baseUrl: 'http://localhost:5000'
  });

  // 3. Check balance
  const balance = await client.wallet.getBalance(wallet.address);
  console.log('Balance:', balance.balance);

  // 4. Get blockchain info
  const info = await client.blockchain.getInfo();
  console.log('Blockchain height:', info.height);

  // 5. Send transaction (if you have funds)
  if (balance.balance > 0) {
    const result = await client.transaction.send(
      wallet,
      'RECIPIENT_ADDRESS',
      1,
      { fee: 0.1 }
    );
    console.log('Transaction:', result.txid);
  }
}

main().catch(console.error);
```

## Mining

```typescript
// Start mining
await client.mining.start(minerAddress);

// Check status
const status = await client.mining.getStatus();
console.log('Mining:', status.mining_enabled);

// Enable auto-mining (10 second interval)
await client.mining.enableAutoMine(minerAddress, 10000);
```

## Governance

```typescript
// Get proposals
const proposals = await client.governance.getProposals();

// Vote on a proposal
await client.governance.vote(
  proposalId,
  wallet.address,
  'yes',
  signature
);
```

## Error Handling

```typescript
import { NetworkError, NotFoundError } from '@xai/sdk';

try {
  const tx = await client.transaction.getTransaction(txid);
} catch (error) {
  if (error instanceof NotFoundError) {
    console.error('Transaction not found');
  } else if (error instanceof NetworkError) {
    console.error('Network error:', error.message);
  }
}
```

## Next Steps

- Read the [full documentation](./README.md)
- Explore [examples](./examples/)
- Check the [API reference](./SDK_SUMMARY.md)

## Support

- GitHub Issues: https://github.com/xai-blockchain/xai/issues
- Documentation: https://docs.xai-blockchain.io
