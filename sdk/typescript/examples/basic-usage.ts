/**
 * Basic Usage Example
 *
 * Demonstrates fundamental operations with the XAI SDK.
 */

import { XAIClient } from '../src';

async function main() {
  // Create client
  const client = new XAIClient({
    baseUrl: 'http://localhost:5000',
  });

  try {
    // Check node health
    const health = await client.healthCheck();
    console.log('Node health:', health.status);

    // Get node info
    const info = await client.getInfo();
    console.log('Node version:', info.version);

    // Create a wallet
    console.log('\n--- Creating Wallet ---');
    const wallet = await client.wallet.create();
    console.log('Wallet address:', wallet.address);
    console.log('Public key:', wallet.publicKey);

    // Get wallet balance
    console.log('\n--- Checking Balance ---');
    const balance = await client.wallet.getBalance(wallet.address);
    console.log('Balance:', balance.balance);
    console.log('Available:', balance.availableBalance);

    // Get blockchain stats
    console.log('\n--- Blockchain Statistics ---');
    const stats = await client.blockchain.getStats();
    console.log('Total blocks:', stats.totalBlocks);
    console.log('Total transactions:', stats.totalTransactions);
    console.log('Network hashrate:', stats.hashrate);

    // List recent blocks
    console.log('\n--- Recent Blocks ---');
    const blocks = await client.blockchain.listBlocks({ limit: 5 });
    blocks.data.forEach((block) => {
      console.log(`Block ${block.number}: ${block.hash} (${block.transactions} txs)`);
    });
  } catch (error) {
    console.error('Error:', error);
  } finally {
    client.close();
  }
}

main();
