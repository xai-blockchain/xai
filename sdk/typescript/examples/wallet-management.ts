/**
 * Wallet Management Example
 */

import { Wallet } from '@xai/sdk';

async function main() {
  console.log('XAI Wallet Management Example\n');

  // 1. Create a new wallet
  console.log('1. Creating new wallet...');
  const wallet = Wallet.create();
  console.log('   Address:', wallet.address);

  // 2. Generate mnemonic
  console.log('\n2. Generating mnemonic phrase...');
  const mnemonic = Wallet.generateMnemonic();
  console.log('   Mnemonic:', mnemonic);

  // 3. Create wallet from mnemonic
  console.log('\n3. Creating wallet from mnemonic...');
  const mnemonicWallet = await Wallet.fromMnemonic(mnemonic, 0);
  console.log('   Address:', mnemonicWallet.address);

  // 4. Sign a message
  console.log('\n4. Signing a message...');
  const message = 'Hello XAI Blockchain!';
  const signature = await wallet.sign(message);
  console.log('   Message:', message);
  console.log('   Signature:', signature.substring(0, 32) + '...');

  console.log('\nWallet management example completed!');
}

main().catch(console.error);
