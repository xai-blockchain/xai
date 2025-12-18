/**
 * Mining Example
 *
 * Demonstrates mining operations including starting/stopping mining
 * and monitoring mining status.
 */

import { XAIClient } from '../src';

async function main() {
  const client = new XAIClient({
    baseUrl: 'http://localhost:12080',
  });

  try {
    // Create a wallet for mining rewards
    console.log('--- Creating Miner Wallet ---');
    const minerWallet = await client.wallet.create();
    console.log('Miner address:', minerWallet.address);

    // Check initial mining status
    console.log('\n--- Initial Mining Status ---');
    let status = await client.mining.getStatus();
    console.log('Mining:', status.mining);
    console.log('Threads:', status.threads);
    console.log('Hashrate:', status.hashrate);
    console.log('Difficulty:', status.currentDifficulty);

    // Start mining if not already running
    if (!status.mining) {
      console.log('\n--- Starting Mining ---');
      await client.mining.start(4); // 4 threads
      console.log('Mining started with 4 threads');

      // Wait a bit for mining to initialize
      await new Promise((resolve) => setTimeout(resolve, 2000));

      status = await client.mining.getStatus();
      console.log('Mining:', status.mining);
      console.log('Hashrate:', status.hashrate);
    }

    // Monitor mining for 30 seconds
    console.log('\n--- Monitoring Mining ---');
    console.log('Monitoring for 30 seconds...');

    const startTime = Date.now();
    while (Date.now() - startTime < 30000) {
      status = await client.mining.getStatus();
      console.log(
        `Hashrate: ${status.hashrate} | Blocks: ${status.blocksFound} | Uptime: ${status.uptime}s`
      );

      await new Promise((resolve) => setTimeout(resolve, 5000));
    }

    // Get mining rewards
    console.log('\n--- Mining Rewards ---');
    const rewards = await client.mining.getRewards(minerWallet.address);
    console.log('Total rewards:', rewards.totalRewards);
    console.log('Pending rewards:', rewards.pendingRewards);
    console.log('Claimed rewards:', rewards.claimedRewards);
    console.log('Blocks found:', rewards.blocksFound);

    // Stop mining
    console.log('\n--- Stopping Mining ---');
    await client.mining.stop();
    console.log('Mining stopped');

    // Final status
    status = await client.mining.getStatus();
    console.log('Mining:', status.mining);
    console.log('Total blocks found:', status.blocksFound);
  } catch (error) {
    console.error('Error:', error);
  } finally {
    client.close();
  }
}

main();
