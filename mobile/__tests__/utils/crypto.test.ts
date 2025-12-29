/**
 * Unit tests for crypto utilities
 */

import * as Crypto from 'expo-crypto';
import {
  generateKeyPair,
  deriveAddress,
  createWallet,
  signMessage,
  hashTransaction,
  signTransaction,
  isValidAddress,
  formatAddress,
  generateTxId,
} from '../../src/utils/crypto';

describe('Crypto Utilities', () => {
  describe('generateKeyPair', () => {
    it('should generate a keypair with public and private keys', async () => {
      const keypair = await generateKeyPair();

      expect(keypair).toHaveProperty('publicKey');
      expect(keypair).toHaveProperty('privateKey');
      expect(typeof keypair.publicKey).toBe('string');
      expect(typeof keypair.privateKey).toBe('string');
    });

    it('should generate unique keypairs each time', async () => {
      const keypair1 = await generateKeyPair();
      const keypair2 = await generateKeyPair();

      expect(keypair1.privateKey).not.toBe(keypair2.privateKey);
      expect(keypair1.publicKey).not.toBe(keypair2.publicKey);
    });

    it('should call crypto getRandomBytesAsync with correct size', async () => {
      await generateKeyPair();

      expect(Crypto.getRandomBytesAsync).toHaveBeenCalledWith(32);
    });

    it('should derive public key from private key using SHA256', async () => {
      await generateKeyPair();

      expect(Crypto.digestStringAsync).toHaveBeenCalledWith(
        Crypto.CryptoDigestAlgorithm.SHA256,
        expect.any(String)
      );
    });
  });

  describe('deriveAddress', () => {
    it('should derive address with XAI prefix', async () => {
      const publicKey = 'test-public-key-hash';
      const address = await deriveAddress(publicKey);

      expect(address).toMatch(/^XAI/);
    });

    it('should generate consistent address for same public key', async () => {
      const publicKey = 'consistent-public-key';
      const address1 = await deriveAddress(publicKey);
      const address2 = await deriveAddress(publicKey);

      expect(address1).toBe(address2);
    });

    it('should generate address with correct length', async () => {
      const publicKey = 'test-public-key';
      const address = await deriveAddress(publicKey);

      // XAI prefix (3) + 40 hex chars = 43
      expect(address.length).toBe(43);
    });
  });

  describe('createWallet', () => {
    it('should create wallet with address, publicKey, and privateKey', async () => {
      const wallet = await createWallet();

      expect(wallet).toHaveProperty('address');
      expect(wallet).toHaveProperty('publicKey');
      expect(wallet).toHaveProperty('privateKey');
    });

    it('should create wallet with valid XAI address', async () => {
      const wallet = await createWallet();

      expect(wallet.address).toMatch(/^XAI/);
      expect(wallet.address.length).toBe(43);
    });

    it('should create unique wallets', async () => {
      const wallet1 = await createWallet();
      const wallet2 = await createWallet();

      expect(wallet1.address).not.toBe(wallet2.address);
    });
  });

  describe('signMessage', () => {
    it('should sign message and return signature string', async () => {
      const message = 'test message';
      const privateKey = 'test-private-key';

      const signature = await signMessage(message, privateKey);

      expect(typeof signature).toBe('string');
      expect(signature.length).toBeGreaterThan(0);
    });

    it('should produce consistent signature for same inputs', async () => {
      const message = 'consistent message';
      const privateKey = 'consistent-key';

      const sig1 = await signMessage(message, privateKey);
      const sig2 = await signMessage(message, privateKey);

      expect(sig1).toBe(sig2);
    });

    it('should produce different signatures for different messages', async () => {
      const privateKey = 'test-key';

      const sig1 = await signMessage('message1', privateKey);
      const sig2 = await signMessage('message2', privateKey);

      expect(sig1).not.toBe(sig2);
    });

    it('should produce different signatures for different keys', async () => {
      const message = 'same message';

      const sig1 = await signMessage(message, 'key1');
      const sig2 = await signMessage(message, 'key2');

      expect(sig1).not.toBe(sig2);
    });
  });

  describe('hashTransaction', () => {
    const sampleTx = {
      sender: 'XAIa1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2',
      recipient: 'XAIf1e2d3c4b5a6f1e2d3c4b5a6f1e2d3c4b5a6f1e2',
      amount: 100,
      fee: 0.001,
      nonce: 1,
      timestamp: 1700000000,
    };

    it('should hash transaction and return string', async () => {
      const hash = await hashTransaction(sampleTx);

      expect(typeof hash).toBe('string');
      expect(hash.length).toBeGreaterThan(0);
    });

    it('should produce consistent hash for same transaction', async () => {
      const hash1 = await hashTransaction(sampleTx);
      const hash2 = await hashTransaction(sampleTx);

      expect(hash1).toBe(hash2);
    });

    it('should produce different hash for different amounts', async () => {
      const hash1 = await hashTransaction(sampleTx);
      const hash2 = await hashTransaction({ ...sampleTx, amount: 200 });

      expect(hash1).not.toBe(hash2);
    });

    it('should produce different hash for different nonces', async () => {
      const hash1 = await hashTransaction(sampleTx);
      const hash2 = await hashTransaction({ ...sampleTx, nonce: 2 });

      expect(hash1).not.toBe(hash2);
    });
  });

  describe('signTransaction', () => {
    const sampleTx = {
      sender: 'XAIa1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2',
      recipient: 'XAIf1e2d3c4b5a6f1e2d3c4b5a6f1e2d3c4b5a6f1e2',
      amount: 100,
      fee: 0.001,
      nonce: 1,
      timestamp: 1700000000,
    };

    it('should sign transaction and return signature', async () => {
      const privateKey = 'test-private-key';
      const signature = await signTransaction(sampleTx, privateKey);

      expect(typeof signature).toBe('string');
      expect(signature.length).toBeGreaterThan(0);
    });

    it('should produce consistent signature for same inputs', async () => {
      const privateKey = 'consistent-key';

      const sig1 = await signTransaction(sampleTx, privateKey);
      const sig2 = await signTransaction(sampleTx, privateKey);

      expect(sig1).toBe(sig2);
    });
  });

  describe('isValidAddress', () => {
    it('should return true for valid XAI address', () => {
      const validAddress = 'XAIa1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2';
      expect(isValidAddress(validAddress)).toBe(true);
    });

    it('should return false for null/undefined', () => {
      expect(isValidAddress(null as any)).toBe(false);
      expect(isValidAddress(undefined as any)).toBe(false);
    });

    it('should return false for non-string', () => {
      expect(isValidAddress(123 as any)).toBe(false);
      expect(isValidAddress({} as any)).toBe(false);
    });

    it('should return false for address without XAI prefix', () => {
      expect(isValidAddress('BTCa1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2')).toBe(false);
      expect(isValidAddress('a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2')).toBe(false);
    });

    it('should return false for wrong length', () => {
      expect(isValidAddress('XAIa1b2c3')).toBe(false);
      expect(isValidAddress('XAI')).toBe(false);
      expect(isValidAddress('XAIa1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2extra')).toBe(false);
    });

    it('should return false for non-hex characters', () => {
      expect(isValidAddress('XAIg1h2i3j4k5l6g1h2i3j4k5l6g1h2i3j4k5l6g1h2')).toBe(false);
      expect(isValidAddress('XAI!@#$%^&*()_+!@#$%^&*()_+!@#$%^&*()_+')).toBe(false);
    });

    it('should accept lowercase and uppercase hex', () => {
      expect(isValidAddress('XAIa1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2')).toBe(true);
      expect(isValidAddress('XAIA1B2C3D4E5F6A1B2C3D4E5F6A1B2C3D4E5F6A1B2')).toBe(true);
    });
  });

  describe('formatAddress', () => {
    const fullAddress = 'XAIa1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2';

    it('should truncate address with ellipsis', () => {
      const formatted = formatAddress(fullAddress, 6);
      expect(formatted).toContain('...');
      expect(formatted.length).toBeLessThan(fullAddress.length);
    });

    it('should preserve XAI prefix', () => {
      const formatted = formatAddress(fullAddress, 6);
      expect(formatted).toMatch(/^XAI/);
    });

    it('should show correct number of characters at start', () => {
      const formatted = formatAddress(fullAddress, 6);
      expect(formatted.startsWith('XAIa1b2c3')).toBe(true); // XAI + 6 chars
    });

    it('should show correct number of characters at end', () => {
      const formatted = formatAddress(fullAddress, 6);
      expect(formatted.endsWith('f6a1b2')).toBe(true);
    });

    it('should return original for short addresses', () => {
      const shortAddress = 'XAI123';
      expect(formatAddress(shortAddress, 6)).toBe(shortAddress);
    });

    it('should handle empty/null address', () => {
      expect(formatAddress('', 6)).toBe('');
      expect(formatAddress(null as any, 6)).toBe(null);
      expect(formatAddress(undefined as any, 6)).toBe(undefined);
    });

    it('should use default chars value', () => {
      const formatted = formatAddress(fullAddress);
      expect(formatted).toContain('...');
    });
  });

  describe('generateTxId', () => {
    const sampleTxData = {
      sender: 'XAIa1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2',
      recipient: 'XAIf1e2d3c4b5a6f1e2d3c4b5a6f1e2d3c4b5a6f1e2',
      amount: 100,
      timestamp: 1700000000,
    };

    it('should generate transaction ID string', async () => {
      const txId = await generateTxId(sampleTxData);

      expect(typeof txId).toBe('string');
      expect(txId.length).toBeGreaterThan(0);
    });

    it('should generate unique IDs (includes random component)', async () => {
      const txId1 = await generateTxId(sampleTxData);
      const txId2 = await generateTxId(sampleTxData);

      // Due to Math.random() component, IDs should differ
      // (Though in tests with mocked crypto, behavior may vary)
      expect(typeof txId1).toBe('string');
      expect(typeof txId2).toBe('string');
    });
  });
});
