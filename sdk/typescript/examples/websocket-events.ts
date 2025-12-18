/**
 * WebSocket Events Example
 *
 * Demonstrates real-time event streaming using WebSocket connections.
 */

import { XAIClient } from '../src';

async function main() {
  const client = new XAIClient({
    baseUrl: 'http://localhost:5000',
  });

  try {
    // Connect to WebSocket
    console.log('Connecting to WebSocket...');
    client.connectWebSocket('ws://localhost:5000/ws');

    // Handle connection events
    client.on('connected', () => {
      console.log('✓ WebSocket connected');
    });

    client.on('disconnected', ({ code, reason }) => {
      console.log('✗ WebSocket disconnected:', code, reason);
    });

    client.on('error', (error) => {
      console.error('✗ WebSocket error:', error);
    });

    client.on('reconnecting', ({ attempt, maxAttempts, delay }) => {
      console.log(`Reconnecting... (${attempt}/${maxAttempts}, delay: ${delay}ms)`);
    });

    // Listen for new blocks
    client.on('new_block', (block) => {
      console.log('\n📦 New Block:');
      console.log('  Number:', block.number);
      console.log('  Hash:', block.hash);
      console.log('  Miner:', block.miner);
      console.log('  Transactions:', block.transactions);
    });

    // Listen for new transactions
    client.on('new_transaction', (tx) => {
      console.log('\n💸 New Transaction:');
      console.log('  Hash:', tx.hash);
      console.log('  From:', tx.from);
      console.log('  To:', tx.to);
      console.log('  Amount:', tx.amount);
    });

    // Listen for transaction confirmations
    client.on('transaction_confirmed', (data) => {
      console.log('\n✓ Transaction Confirmed:');
      console.log('  Hash:', data.hash);
      console.log('  Block:', data.blockNumber);
      console.log('  Confirmations:', data.confirmations);
    });

    // Listen for mining events
    client.on('mining_block_found', (block) => {
      console.log('\n⛏️  Block Found by Miner:');
      console.log('  Number:', block.number);
      console.log('  Hash:', block.hash);
      console.log('  Reward:', block.reward);
    });

    // Listen for governance events
    client.on('proposal_created', (proposal) => {
      console.log('\n📜 New Proposal Created:');
      console.log('  ID:', proposal.id);
      console.log('  Title:', proposal.title);
      console.log('  Creator:', proposal.creator);
    });

    client.on('proposal_vote', (vote) => {
      console.log('\n🗳️  New Vote:');
      console.log('  Proposal ID:', vote.proposalId);
      console.log('  Voter:', vote.voter);
      console.log('  Choice:', vote.choice);
    });

    // Keep the process running
    console.log('\nListening for events... (Press Ctrl+C to exit)');

    // Graceful shutdown
    process.on('SIGINT', () => {
      console.log('\n\nShutting down...');
      client.close();
      process.exit(0);
    });

    // Keep alive
    await new Promise(() => {});
  } catch (error) {
    console.error('Error:', error);
    client.close();
    process.exit(1);
  }
}

main();
