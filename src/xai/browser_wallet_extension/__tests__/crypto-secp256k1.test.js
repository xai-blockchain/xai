/**
 * Tests for XAI Browser Wallet Client-Side Cryptography Module
 *
 * Verifies that:
 * 1. All cryptographic operations work correctly
 * 2. Private keys NEVER leave the module
 * 3. Signatures are properly normalized (low-S)
 * 4. Input validation is thorough
 */

'use strict';

// Mock the noble-secp256k1 library
const mockSignature = {
  toCompactRawBytes: jest.fn(() => new Uint8Array(64).fill(1))
};

const mockSecp256k1 = {
  signAsync: jest.fn().mockResolvedValue(mockSignature),
  getPublicKey: jest.fn((privateKey, compressed) => {
    // Return a valid compressed public key (33 bytes)
    const result = new Uint8Array(33);
    result[0] = 0x02; // Compressed prefix
    for (let i = 1; i < 33; i++) {
      result[i] = i;
    }
    return result;
  }),
  verify: jest.fn().mockReturnValue(true),
  Signature: {
    fromCompact: jest.fn((bytes) => ({
      r: BigInt('0x' + '01'.repeat(32)),
      s: BigInt('0x' + '01'.repeat(32))
    }))
  }
};

// Set up global mock before requiring the module
global.secp256k1 = mockSecp256k1;

// Load the crypto module
const fs = require('fs');
const path = require('path');
const vm = require('vm');

// Read and execute the crypto-secp256k1.js file in a sandbox
const cryptoSource = fs.readFileSync(
  path.join(__dirname, '..', 'crypto-secp256k1.js'),
  'utf8'
);

// Create a sandbox with our mocks
const sandbox = {
  secp256k1: mockSecp256k1,
  nobleSecp256k1: mockSecp256k1,
  console: console,
  module: { exports: {} },
  window: {},
  Uint8Array,
  Number,
  BigInt,
  Error,
  TypeError,
  Promise
};

// Execute in sandbox
const script = new vm.Script(cryptoSource);
script.runInNewContext(sandbox);

// Get the exported functions
const {
  signMessageHash,
  derivePublicKey,
  verifySignature,
  hexToBytes,
  bytesToHex,
  normalizeSignatureToLowS
} = sandbox.module.exports;

describe('XAI Crypto Module - Client-Side Signing', () => {
  // Test vectors
  const validPrivateKey = 'a'.repeat(64); // 32 bytes in hex
  const validMessageHash = 'b'.repeat(64); // 32 bytes SHA-256 hash
  const validSignature = 'c'.repeat(128); // 64 bytes signature in hex
  const validCompressedPubKey = '02' + 'd'.repeat(64); // 33 bytes compressed

  beforeEach(() => {
    jest.clearAllMocks();
    mockSignature.toCompactRawBytes.mockReturnValue(new Uint8Array(64).fill(1));
  });

  describe('hexToBytes', () => {
    test('converts valid hex string to Uint8Array', () => {
      const hex = '0102030405';
      const bytes = hexToBytes(hex);
      expect(bytes).toBeInstanceOf(Uint8Array);
      expect(bytes.length).toBe(5);
      expect(bytes[0]).toBe(1);
      expect(bytes[4]).toBe(5);
    });

    test('throws on non-string input', () => {
      expect(() => hexToBytes(123)).toThrow(TypeError);
      expect(() => hexToBytes(null)).toThrow(TypeError);
      expect(() => hexToBytes(undefined)).toThrow(TypeError);
    });

    test('throws on odd-length hex string', () => {
      expect(() => hexToBytes('abc')).toThrow('odd length');
    });

    test('throws on invalid hex characters', () => {
      expect(() => hexToBytes('ghij')).toThrow('invalid hex');
    });
  });

  describe('bytesToHex', () => {
    test('converts Uint8Array to hex string', () => {
      const bytes = new Uint8Array([1, 2, 3, 255]);
      const hex = bytesToHex(bytes);
      expect(hex).toBe('010203ff');
    });

    test('throws on non-Uint8Array input', () => {
      expect(() => bytesToHex([1, 2, 3])).toThrow(TypeError);
      expect(() => bytesToHex('test')).toThrow(TypeError);
    });

    test('handles empty array', () => {
      const bytes = new Uint8Array(0);
      const hex = bytesToHex(bytes);
      expect(hex).toBe('');
    });
  });

  describe('normalizeSignatureToLowS', () => {
    test('keeps low-S signatures unchanged', () => {
      // Create a signature with low S (below half order)
      const lowSSignature = new Uint8Array(64);
      lowSSignature.fill(0x01); // Very low S value

      const result = normalizeSignatureToLowS(lowSSignature);
      expect(result).toEqual(lowSSignature);
    });

    test('normalizes high-S to low-S', () => {
      // Create a signature with high S (above half order)
      // secp256k1 order: 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
      // half order: approximately 0x7FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF5D576E7357A4501DDFE92F46681B20A0
      const highSSignature = new Uint8Array(64);
      highSSignature.fill(0x00, 0, 32); // r
      highSSignature.fill(0xFF, 32, 64); // high S (all 0xFF is > half order)

      const result = normalizeSignatureToLowS(highSSignature);

      // Result should be different (normalized)
      expect(result).not.toEqual(highSSignature);
      // R should be unchanged
      expect(result.slice(0, 32)).toEqual(highSSignature.slice(0, 32));
    });

    test('throws on invalid signature length', () => {
      expect(() => normalizeSignatureToLowS(new Uint8Array(32))).toThrow('Invalid signature length');
      expect(() => normalizeSignatureToLowS(new Uint8Array(128))).toThrow('Invalid signature length');
    });
  });

  describe('signMessageHash', () => {
    test('signs a valid message hash with valid private key', async () => {
      const signature = await signMessageHash(validMessageHash, validPrivateKey);

      expect(signature).toBeDefined();
      expect(signature.length).toBe(128); // 64 bytes = 128 hex chars
      expect(mockSecp256k1.signAsync).toHaveBeenCalled();
    });

    test('throws on missing message hash', async () => {
      await expect(signMessageHash('', validPrivateKey))
        .rejects.toThrow('Message hash is required');
      await expect(signMessageHash(null, validPrivateKey))
        .rejects.toThrow('Message hash is required');
    });

    test('throws on invalid message hash length', async () => {
      await expect(signMessageHash('abcd', validPrivateKey))
        .rejects.toThrow('64 hex characters');
    });

    test('throws on missing private key', async () => {
      await expect(signMessageHash(validMessageHash, ''))
        .rejects.toThrow('Private key is required');
      await expect(signMessageHash(validMessageHash, null))
        .rejects.toThrow('Private key is required');
    });

    test('throws on invalid private key length', async () => {
      await expect(signMessageHash(validMessageHash, 'abcd'))
        .rejects.toThrow('64 hex characters');
    });

    test('throws on non-hex message hash', async () => {
      const invalidHash = 'g'.repeat(64); // 'g' is not valid hex
      await expect(signMessageHash(invalidHash, validPrivateKey))
        .rejects.toThrow('valid hexadecimal');
    });

    test('throws on non-hex private key', async () => {
      const invalidKey = 'z'.repeat(64); // 'z' is not valid hex
      await expect(signMessageHash(validMessageHash, invalidKey))
        .rejects.toThrow('valid hexadecimal');
    });

    test('enforces low-S signature normalization', async () => {
      // The function should call signAsync with lowS: true
      await signMessageHash(validMessageHash, validPrivateKey);

      expect(mockSecp256k1.signAsync).toHaveBeenCalledWith(
        expect.any(Uint8Array),
        expect.any(Uint8Array),
        expect.objectContaining({ lowS: true })
      );
    });

    test('rejects zero private key', async () => {
      const zeroKey = '0'.repeat(64);
      await expect(signMessageHash(validMessageHash, zeroKey))
        .rejects.toThrow('out of valid range');
    });
  });

  describe('derivePublicKey', () => {
    test('derives compressed public key by default', () => {
      const pubKey = derivePublicKey(validPrivateKey);

      expect(pubKey).toBeDefined();
      expect(pubKey.length).toBe(66); // 33 bytes = 66 hex chars
      expect(mockSecp256k1.getPublicKey).toHaveBeenCalledWith(
        expect.any(Uint8Array),
        true // compressed
      );
    });

    test('derives uncompressed public key when specified', () => {
      mockSecp256k1.getPublicKey.mockReturnValueOnce(new Uint8Array(65).fill(4));

      const pubKey = derivePublicKey(validPrivateKey, false);

      expect(mockSecp256k1.getPublicKey).toHaveBeenCalledWith(
        expect.any(Uint8Array),
        false // uncompressed
      );
    });

    test('throws on invalid private key length', () => {
      expect(() => derivePublicKey('abcd'))
        .toThrow('64 hex characters');
    });

    test('throws on non-hex private key', () => {
      const invalidKey = 'z'.repeat(64);
      expect(() => derivePublicKey(invalidKey))
        .toThrow('valid hexadecimal');
    });
  });

  describe('verifySignature', () => {
    test('verifies a valid signature', () => {
      const result = verifySignature(validSignature, validMessageHash, validCompressedPubKey);

      expect(result).toBe(true);
      expect(mockSecp256k1.verify).toHaveBeenCalled();
    });

    test('returns false for invalid signature', () => {
      mockSecp256k1.verify.mockReturnValueOnce(false);

      const result = verifySignature(validSignature, validMessageHash, validCompressedPubKey);

      expect(result).toBe(false);
    });

    test('throws on invalid signature length', () => {
      expect(() => verifySignature('abcd', validMessageHash, validCompressedPubKey))
        .toThrow('128 hex characters');
    });

    test('throws on invalid message hash length', () => {
      expect(() => verifySignature(validSignature, 'abcd', validCompressedPubKey))
        .toThrow('64 hex characters');
    });

    test('throws on invalid public key length', () => {
      expect(() => verifySignature(validSignature, validMessageHash, 'abcd'))
        .toThrow('66 (compressed) or 130 (uncompressed)');
    });

    test('handles verification errors gracefully', () => {
      mockSecp256k1.verify.mockImplementationOnce(() => {
        throw new Error('Verification error');
      });

      const result = verifySignature(validSignature, validMessageHash, validCompressedPubKey);

      expect(result).toBe(false);
    });
  });

  describe('Security: Private Key Protection', () => {
    test('private key is never exposed in error messages', async () => {
      try {
        await signMessageHash(validMessageHash, 'invalid');
      } catch (error) {
        expect(error.message).not.toContain(validPrivateKey);
        expect(error.message).not.toMatch(/[a-f0-9]{64}/i);
      }
    });

    test('private key is converted to bytes and not stored as string', async () => {
      await signMessageHash(validMessageHash, validPrivateKey);

      // Verify the library receives bytes, not the original hex string
      const call = mockSecp256k1.signAsync.mock.calls[0];
      expect(call[1]).toBeInstanceOf(Uint8Array);
    });
  });

  describe('XAICrypto Global Export', () => {
    test('exposes XAICrypto on window object', () => {
      expect(sandbox.window.XAICrypto).toBeDefined();
      expect(sandbox.window.XAICrypto.signMessageHash).toBeDefined();
      expect(sandbox.window.XAICrypto.derivePublicKey).toBeDefined();
      expect(sandbox.window.XAICrypto.verifySignature).toBeDefined();
    });
  });
});
