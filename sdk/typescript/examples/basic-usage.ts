/**
 * Basic Usage Example
 * Demonstrates wallet creation, transaction building, and blockchain queries
 */

import { XAIClient, Wallet } from '@xai/sdk';

async function main() {
  // Initialize client
  const client = new XAIClient({
    baseUrl: 'http://localhost:5000',
    wsUrl: 'ws://localhost:5000/ws',
  });

  console.log('XAI SDK Basic Usage Example\n');

  // 1. Create a new wallet
  console.log('1. Creating wallet...');
  const wallet = client.wallet.create();
  console.log('   Address:', wallet.address);
  console.log('   Public Key:', wallet.publicKey.substring(0, 32) + '...');

  // 2. Get wallet balance
  console.log('\n2. Getting balance...');
  try {
    const balance = await client.wallet.getBalance(wallet.address);
    console.log('   Balance:', balance.balance, 'XAI');
  } catch (error: any) {
    console.log('   Error:', error.message);
  }

  // 3. Get blockchain info
  console.log('\n3. Getting blockchain info...');
  try {
    const info = await client.blockchain.getInfo();
    console.log('   Height:', info.height);
    console.log('   Difficulty:', info.difficulty);
    console.log('   Total Transactions:', info.total_transactions);
  } catch (error: any) {
    console.log('   Error:', error.message);
  }

  // 4. Build a transaction
  console.log('\n4. Building transaction...');
  const recipientAddress = 'XAI' + '0'.repeat(40);
  const tx = await client.transaction
    .build(wallet.address, recipientAddress, 10)
    .setFee(0.1)
    .setNonce(0)
    .sign(wallet);
  console.log('   Transaction ID:', tx.txid.substring(0, 32) + '...');
  console.log('   Amount:', tx.amount, 'XAI');
  console.log('   Fee:', tx.fee, 'XAI');

  console.log('\nExample completed!');
}

main().catch(console.error);
