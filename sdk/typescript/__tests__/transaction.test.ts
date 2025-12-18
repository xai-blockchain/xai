/**
 * Transaction Tests
 */

import { Wallet } from '../src/clients/wallet-client';
import { TransactionBuilder } from '../src/clients/transaction-client';

describe('TransactionBuilder', () => {
  let wallet: Wallet;

  beforeEach(() => {
    wallet = Wallet.create();
  });

  describe('build', () => {
    it('should build a basic transaction', () => {
      const builder = new TransactionBuilder(wallet.address, 'XAI' + '0'.repeat(40), 100);
      const tx = builder.setFee(1).build();

      expect(tx.sender).toBe(wallet.address);
      expect(tx.amount).toBe(100);
      expect(tx.fee).toBe(1);
    });

    it('should set nonce', () => {
      const builder = new TransactionBuilder(wallet.address, 'XAI' + '0'.repeat(40), 100);
      const tx = builder.setNonce(5).build();

      expect(tx.nonce).toBe(5);
    });

    it('should set metadata', () => {
      const metadata = { note: 'Test payment' };
      const builder = new TransactionBuilder(wallet.address, 'XAI' + '0'.repeat(40), 100);
      const tx = builder.setMetadata(metadata).build();

      expect(tx.metadata).toEqual(metadata);
    });

    it('should enable RBF', () => {
      const builder = new TransactionBuilder(wallet.address, 'XAI' + '0'.repeat(40), 100);
      const tx = builder.enableRBF().build();

      expect(tx.rbf_enabled).toBe(true);
    });
  });

  describe('sign', () => {
    it('should sign a transaction', async () => {
      const builder = new TransactionBuilder(wallet.address, 'XAI' + '0'.repeat(40), 100);
      const signedTx = await builder.setFee(1).setNonce(0).sign(wallet);

      expect(signedTx.signature).toBeDefined();
      expect(signedTx.public_key).toBe(wallet.publicKey);
      expect(signedTx.txid).toBeDefined();
      expect(signedTx.timestamp).toBeDefined();
    });

    it('should produce valid transaction ID', async () => {
      const builder = new TransactionBuilder(wallet.address, 'XAI' + '0'.repeat(40), 100);
      const signedTx = await builder.setFee(1).setNonce(0).sign(wallet);

      expect(signedTx.txid).toMatch(/^[a-f0-9]{64}$/);
    });
  });

  describe('validation', () => {
    it('should reject negative fee', () => {
      const builder = new TransactionBuilder(wallet.address, 'XAI' + '0'.repeat(40), 100);

      expect(() => builder.setFee(-1)).toThrow();
    });

    it('should reject negative nonce', () => {
      const builder = new TransactionBuilder(wallet.address, 'XAI' + '0'.repeat(40), 100);

      expect(() => builder.setNonce(-1)).toThrow();
    });
  });
});
