/**
 * Transaction Examples
 *
 * Demonstrates transaction operations including sending,
 * fee estimation, and confirmation tracking.
 */

import { XAIClient } from '../src';

async function main() {
  const client = new XAIClient({
    baseUrl: 'http://localhost:12080',
  });

  try {
    // Create two wallets for testing
    console.log('--- Creating Wallets ---');
    const wallet1 = await client.wallet.create();
    const wallet2 = await client.wallet.create();
    console.log('Sender:', wallet1.address);
    console.log('Recipient:', wallet2.address);

    // Estimate transaction fee
    console.log('\n--- Estimating Fee ---');
    const feeEstimate = await client.transaction.estimateFee({
      from: wallet1.address,
      to: wallet2.address,
      amount: '1000',
    });
    console.log('Estimated fee:', feeEstimate.estimatedFee);
    console.log('Gas limit:', feeEstimate.gasLimit);
    console.log('Gas price:', feeEstimate.gasPrice);

    // Send transaction
    console.log('\n--- Sending Transaction ---');
    const tx = await client.transaction.send({
      from: wallet1.address,
      to: wallet2.address,
      amount: '1000',
    });
    console.log('Transaction hash:', tx.hash);
    console.log('Status:', tx.status);
    console.log('Fee:', tx.fee);

    // Get transaction details
    console.log('\n--- Transaction Details ---');
    const txDetails = await client.transaction.get(tx.hash);
    console.log('From:', txDetails.from);
    console.log('To:', txDetails.to);
    console.log('Amount:', txDetails.amount);
    console.log('Confirmations:', txDetails.confirmations);

    // Wait for confirmation
    console.log('\n--- Waiting for Confirmation ---');
    console.log('Waiting for 3 confirmations...');
    const confirmedTx = await client.transaction.waitForConfirmation(
      tx.hash,
      3,
      300000, // 5 minutes timeout
      5000    // 5 second poll interval
    );
    console.log('Transaction confirmed!');
    console.log('Block number:', confirmedTx.blockNumber);
    console.log('Confirmations:', confirmedTx.confirmations);

    // Check final balance
    console.log('\n--- Final Balances ---');
    const balance1 = await client.wallet.getBalance(wallet1.address);
    const balance2 = await client.wallet.getBalance(wallet2.address);
    console.log('Sender balance:', balance1.balance);
    console.log('Recipient balance:', balance2.balance);
  } catch (error) {
    console.error('Error:', error);
  } finally {
    client.close();
  }
}

main();
