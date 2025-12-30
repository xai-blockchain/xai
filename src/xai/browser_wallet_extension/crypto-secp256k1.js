/**
 * XAI Browser Wallet - Client-Side Cryptography Module
 *
 * This module provides secp256k1 ECDSA signing entirely client-side,
 * eliminating the need to send private keys over the network.
 *
 * Security: Private keys NEVER leave this module or the browser.
 *
 * Uses @noble/secp256k1 - audited, zero-dependency pure JS implementation
 * https://github.com/paulmillr/noble-secp256k1
 */

// For browser extension, we load the library from node_modules via bundler
// or include it directly. This is the ES module compatible version.

/**
 * Convert hex string to Uint8Array
 * @param {string} hex - Hexadecimal string
 * @returns {Uint8Array}
 */
function hexToBytes(hex) {
  if (typeof hex !== 'string') {
    throw new TypeError('hexToBytes: expected string, got ' + typeof hex);
  }
  if (hex.length % 2 !== 0) {
    throw new Error('hexToBytes: received invalid hex string (odd length)');
  }
  const bytes = new Uint8Array(hex.length / 2);
  for (let i = 0; i < bytes.length; i++) {
    const j = i * 2;
    const hexByte = hex.slice(j, j + 2);
    const byte = Number.parseInt(hexByte, 16);
    if (Number.isNaN(byte)) {
      throw new Error('hexToBytes: invalid hex character');
    }
    bytes[i] = byte;
  }
  return bytes;
}

/**
 * Convert Uint8Array to hex string
 * @param {Uint8Array} bytes
 * @returns {string}
 */
function bytesToHex(bytes) {
  if (!(bytes instanceof Uint8Array)) {
    throw new TypeError('bytesToHex: expected Uint8Array');
  }
  let hex = '';
  for (let i = 0; i < bytes.length; i++) {
    hex += bytes[i].toString(16).padStart(2, '0');
  }
  return hex;
}

/**
 * secp256k1 curve order (n)
 * Used for low-S normalization to prevent transaction malleability
 */
const SECP256K1_ORDER = BigInt(
  '0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141'
);
const SECP256K1_HALF_ORDER = SECP256K1_ORDER / 2n;

/**
 * Ensure signature uses low-S value (BIP-62 / BIP-146)
 * This prevents transaction malleability attacks
 * @param {Uint8Array} signature - 64-byte signature (r || s)
 * @returns {Uint8Array} - Normalized signature with low-S
 */
function normalizeSignatureToLowS(signature) {
  if (signature.length !== 64) {
    throw new Error('Invalid signature length: expected 64 bytes');
  }

  const r = signature.slice(0, 32);
  const s = signature.slice(32, 64);

  // Convert s to BigInt
  let sBigInt = 0n;
  for (let i = 0; i < 32; i++) {
    sBigInt = (sBigInt << 8n) | BigInt(s[i]);
  }

  // If s > half_order, use n - s instead (low-S normalization)
  if (sBigInt > SECP256K1_HALF_ORDER) {
    sBigInt = SECP256K1_ORDER - sBigInt;

    // Convert back to bytes
    const normalizedS = new Uint8Array(32);
    let temp = sBigInt;
    for (let i = 31; i >= 0; i--) {
      normalizedS[i] = Number(temp & 0xffn);
      temp = temp >> 8n;
    }

    // Combine r and normalized s
    const result = new Uint8Array(64);
    result.set(r, 0);
    result.set(normalizedS, 32);
    return result;
  }

  return signature;
}

/**
 * Sign a message hash with a private key using secp256k1 ECDSA
 *
 * This is the secure client-side implementation that NEVER sends
 * private keys over any network.
 *
 * @param {string} messageHashHex - SHA-256 hash of the message (64 hex chars)
 * @param {string} privateKeyHex - Private key (64 hex chars, 32 bytes)
 * @returns {Promise<string>} - Signature as hex (128 chars, r || s format)
 */
async function signMessageHash(messageHashHex, privateKeyHex) {
  // Validate inputs
  if (!messageHashHex || typeof messageHashHex !== 'string') {
    throw new Error('Message hash is required and must be a string');
  }
  if (messageHashHex.length !== 64) {
    throw new Error('Message hash must be 64 hex characters (32 bytes SHA-256)');
  }
  if (!privateKeyHex || typeof privateKeyHex !== 'string') {
    throw new Error('Private key is required and must be a string');
  }
  if (privateKeyHex.length !== 64) {
    throw new Error('Private key must be 64 hex characters (32 bytes)');
  }

  // Validate hex format
  if (!/^[0-9a-fA-F]+$/.test(messageHashHex)) {
    throw new Error('Message hash must be valid hexadecimal');
  }
  if (!/^[0-9a-fA-F]+$/.test(privateKeyHex)) {
    throw new Error('Private key must be valid hexadecimal');
  }

  try {
    // Convert to bytes
    const messageHash = hexToBytes(messageHashHex);
    const privateKey = hexToBytes(privateKeyHex);

    // Validate private key is within valid range (1 < key < curve order)
    let keyBigInt = 0n;
    for (let i = 0; i < 32; i++) {
      keyBigInt = (keyBigInt << 8n) | BigInt(privateKey[i]);
    }
    if (keyBigInt <= 0n || keyBigInt >= SECP256K1_ORDER) {
      throw new Error('Private key is out of valid range');
    }

    // Sign using noble-secp256k1
    // The library should be loaded globally or via import
    if (typeof secp256k1 === 'undefined' && typeof nobleSecp256k1 === 'undefined') {
      throw new Error(
        'secp256k1 library not loaded. Include noble-secp256k1 before this script.'
      );
    }

    const secp = typeof secp256k1 !== 'undefined' ? secp256k1 : nobleSecp256k1;

    // Sign the message hash (not the message itself - we receive pre-hashed data)
    const signature = await secp.signAsync(messageHash, privateKey, {
      lowS: true, // Enforce low-S for BIP-62 compliance
    });

    // Get the compact signature (r || s, 64 bytes)
    const sigBytes = signature.toCompactRawBytes();

    // Double-check low-S normalization
    const normalizedSig = normalizeSignatureToLowS(sigBytes);

    // Convert to hex and return
    return bytesToHex(normalizedSig);
  } catch (error) {
    // Don't leak private key information in error messages
    if (error.message.includes('Private key')) {
      throw error;
    }
    throw new Error(`Signing failed: ${error.message}`);
  }
}

/**
 * Derive public key from private key
 *
 * @param {string} privateKeyHex - Private key (64 hex chars)
 * @param {boolean} compressed - Whether to return compressed format (default: true)
 * @returns {string} - Public key as hex
 */
function derivePublicKey(privateKeyHex, compressed = true) {
  if (!privateKeyHex || privateKeyHex.length !== 64) {
    throw new Error('Private key must be 64 hex characters');
  }
  if (!/^[0-9a-fA-F]+$/.test(privateKeyHex)) {
    throw new Error('Private key must be valid hexadecimal');
  }

  const secp = typeof secp256k1 !== 'undefined' ? secp256k1 : nobleSecp256k1;
  const privateKey = hexToBytes(privateKeyHex);
  const publicKey = secp.getPublicKey(privateKey, compressed);
  return bytesToHex(publicKey);
}

/**
 * Verify a signature against a message hash and public key
 *
 * @param {string} signatureHex - Signature (128 hex chars, r || s)
 * @param {string} messageHashHex - Message hash (64 hex chars)
 * @param {string} publicKeyHex - Public key (66 or 130 hex chars)
 * @returns {boolean} - True if signature is valid
 */
function verifySignature(signatureHex, messageHashHex, publicKeyHex) {
  if (!signatureHex || signatureHex.length !== 128) {
    throw new Error('Signature must be 128 hex characters');
  }
  if (!messageHashHex || messageHashHex.length !== 64) {
    throw new Error('Message hash must be 64 hex characters');
  }
  if (!publicKeyHex || (publicKeyHex.length !== 66 && publicKeyHex.length !== 130)) {
    throw new Error('Public key must be 66 (compressed) or 130 (uncompressed) hex characters');
  }

  try {
    const secp = typeof secp256k1 !== 'undefined' ? secp256k1 : nobleSecp256k1;
    const signature = hexToBytes(signatureHex);
    const messageHash = hexToBytes(messageHashHex);
    const publicKey = hexToBytes(publicKeyHex);

    // Create signature object from raw bytes
    const sig = secp.Signature.fromCompact(signature);

    return secp.verify(sig, messageHash, publicKey);
  } catch (error) {
    console.error('Signature verification error:', error.message);
    return false;
  }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    signMessageHash,
    derivePublicKey,
    verifySignature,
    hexToBytes,
    bytesToHex,
    normalizeSignatureToLowS,
  };
}

// Also expose globally for browser usage
if (typeof window !== 'undefined') {
  window.XAICrypto = {
    signMessageHash,
    derivePublicKey,
    verifySignature,
    hexToBytes,
    bytesToHex,
  };
}
