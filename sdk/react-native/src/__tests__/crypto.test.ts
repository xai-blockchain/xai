/**
 * Crypto Utilities Tests
 */

import {
  generateMnemonic,
  validateMnemonic,
  generateWallet,
  generateWalletFromMnemonic,
  signMessage,
  verifySignature,
  privateKeyToPublicKey,
  publicKeyToAddress,
} from '../utils/crypto';

describe('Crypto Utilities', () => {
  describe('mnemonic generation', () => {
    it('should generate a valid mnemonic', () => {
      const mnemonic = generateMnemonic();
      expect(mnemonic).toBeTruthy();
      expect(mnemonic.split(' ')).toHaveLength(12);
      expect(validateMnemonic(mnemonic)).toBe(true);
    });

    it('should validate correct mnemonic', () => {
      const mnemonic = generateMnemonic();
      expect(validateMnemonic(mnemonic)).toBe(true);
    });

    it('should reject invalid mnemonic', () => {
      expect(validateMnemonic('invalid mnemonic phrase')).toBe(false);
    });
  });

  describe('wallet generation', () => {
    it('should generate a complete wallet', () => {
      const wallet = generateWallet();

      expect(wallet).toHaveProperty('address');
      expect(wallet).toHaveProperty('publicKey');
      expect(wallet).toHaveProperty('privateKey');
      expect(wallet).toHaveProperty('mnemonic');

      expect(wallet.address).toMatch(/^0x[a-f0-9]{40}$/i);
      expect(wallet.privateKey).toHaveLength(64);
      expect(validateMnemonic(wallet.mnemonic)).toBe(true);
    });

    it('should generate wallet from mnemonic', () => {
      const mnemonic = generateMnemonic();
      const wallet = generateWalletFromMnemonic(mnemonic);

      expect(wallet).toHaveProperty('address');
      expect(wallet).toHaveProperty('publicKey');
      expect(wallet).toHaveProperty('privateKey');
      expect(wallet.address).toMatch(/^0x[a-f0-9]{40}$/i);
    });

    it('should generate same wallet from same mnemonic', () => {
      const mnemonic = generateMnemonic();
      const wallet1 = generateWalletFromMnemonic(mnemonic);
      const wallet2 = generateWalletFromMnemonic(mnemonic);

      expect(wallet1.address).toBe(wallet2.address);
      expect(wallet1.publicKey).toBe(wallet2.publicKey);
      expect(wallet1.privateKey).toBe(wallet2.privateKey);
    });
  });

  describe('key derivation', () => {
    it('should derive public key from private key', () => {
      const wallet = generateWallet();
      const publicKey = privateKeyToPublicKey(wallet.privateKey);

      expect(publicKey).toBe(wallet.publicKey);
    });

    it('should derive address from public key', () => {
      const wallet = generateWallet();
      const address = publicKeyToAddress(wallet.publicKey);

      expect(address).toBe(wallet.address);
      expect(address).toMatch(/^0x[a-f0-9]{40}$/i);
    });
  });

  describe('message signing', () => {
    it('should sign a message', () => {
      const wallet = generateWallet();
      const message = 'Test message';
      const signature = signMessage(message, wallet.privateKey);

      expect(signature).toBeTruthy();
      expect(typeof signature).toBe('string');
    });

    it('should verify valid signature', () => {
      const wallet = generateWallet();
      const message = 'Test message';
      const signature = signMessage(message, wallet.privateKey);

      const isValid = verifySignature(message, signature, wallet.publicKey);
      expect(isValid).toBe(true);
    });

    it('should reject invalid signature', () => {
      const wallet = generateWallet();
      const message = 'Test message';
      const signature = signMessage(message, wallet.privateKey);

      // Verify with different message
      const isValid = verifySignature(
        'Different message',
        signature,
        wallet.publicKey
      );
      expect(isValid).toBe(false);
    });

    it('should reject signature with wrong public key', () => {
      const wallet1 = generateWallet();
      const wallet2 = generateWallet();
      const message = 'Test message';
      const signature = signMessage(message, wallet1.privateKey);

      // Verify with different public key
      const isValid = verifySignature(message, signature, wallet2.publicKey);
      expect(isValid).toBe(false);
    });
  });
});
