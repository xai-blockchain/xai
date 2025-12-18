/**
 * Crypto Utilities Tests
 */

import {
  generatePrivateKey,
  derivePublicKey,
  generateAddress,
  signMessage,
  verifySignature,
  validateAddress,
  hash256,
} from '../src/utils/crypto';

describe('Crypto Utilities', () => {
  describe('generatePrivateKey', () => {
    it('should generate a 64-character hex private key', () => {
      const privateKey = generatePrivateKey();

      expect(privateKey).toMatch(/^[a-f0-9]{64}$/);
    });

    it('should generate unique keys', () => {
      const key1 = generatePrivateKey();
      const key2 = generatePrivateKey();

      expect(key1).not.toBe(key2);
    });
  });

  describe('derivePublicKey', () => {
    it('should derive public key from private key', () => {
      const privateKey = generatePrivateKey();
      const publicKey = derivePublicKey(privateKey);

      expect(publicKey).toBeDefined();
      expect(publicKey.length).toBeGreaterThan(0);
    });

    it('should derive same public key from same private key', () => {
      const privateKey = generatePrivateKey();
      const pubKey1 = derivePublicKey(privateKey);
      const pubKey2 = derivePublicKey(privateKey);

      expect(pubKey1).toBe(pubKey2);
    });
  });

  describe('generateAddress', () => {
    it('should generate address with XAI prefix', () => {
      const privateKey = generatePrivateKey();
      const publicKey = derivePublicKey(privateKey);
      const address = generateAddress(publicKey);

      expect(address.startsWith('XAI')).toBe(true);
      expect(address.length).toBe(43); // XAI + 40 hex chars
    });

    it('should generate same address from same public key', () => {
      const privateKey = generatePrivateKey();
      const publicKey = derivePublicKey(privateKey);
      const addr1 = generateAddress(publicKey);
      const addr2 = generateAddress(publicKey);

      expect(addr1).toBe(addr2);
    });
  });

  describe('signMessage and verifySignature', () => {
    it('should sign and verify messages', async () => {
      const privateKey = generatePrivateKey();
      const publicKey = derivePublicKey(privateKey);
      const message = 'Hello XAI';

      const signature = await signMessage(privateKey, message);
      const isValid = await verifySignature(publicKey, message, signature);

      expect(isValid).toBe(true);
    });

    it('should reject invalid signatures', async () => {
      const privateKey = generatePrivateKey();
      const publicKey = derivePublicKey(privateKey);
      const message = 'Hello XAI';
      const signature = await signMessage(privateKey, message);

      const isValid = await verifySignature(publicKey, 'Different message', signature);

      expect(isValid).toBe(false);
    });

    it('should reject signature from different key', async () => {
      const privateKey1 = generatePrivateKey();
      const privateKey2 = generatePrivateKey();
      const publicKey2 = derivePublicKey(privateKey2);
      const message = 'Test';

      const signature = await signMessage(privateKey1, message);
      const isValid = await verifySignature(publicKey2, message, signature);

      expect(isValid).toBe(false);
    });
  });

  describe('validateAddress', () => {
    it('should validate correct XAI addresses', () => {
      const privateKey = generatePrivateKey();
      const publicKey = derivePublicKey(privateKey);
      const address = generateAddress(publicKey);

      expect(validateAddress(address)).toBe(true);
    });

    it('should validate COINBASE special address', () => {
      expect(validateAddress('COINBASE')).toBe(true);
    });

    it('should reject invalid addresses', () => {
      expect(validateAddress('invalid')).toBe(false);
      expect(validateAddress('XAI123')).toBe(false);
      expect(validateAddress('0x' + '0'.repeat(40))).toBe(false);
    });
  });

  describe('hash256', () => {
    it('should hash strings', () => {
      const hash = hash256('test data');

      expect(hash).toMatch(/^[a-f0-9]{64}$/);
    });

    it('should produce consistent hashes', () => {
      const data = 'consistent data';
      const hash1 = hash256(data);
      const hash2 = hash256(data);

      expect(hash1).toBe(hash2);
    });

    it('should produce different hashes for different data', () => {
      const hash1 = hash256('data1');
      const hash2 = hash256('data2');

      expect(hash1).not.toBe(hash2);
    });
  });
});
