/**
 * Cryptographic Utilities
 * Provides secp256k1 key generation, signing, and address derivation
 */

import * as secp256k1 from '@noble/secp256k1';
import { sha256 } from '@noble/hashes/sha256';
import { ripemd160 } from '@noble/hashes/ripemd160';
import * as bip39 from 'bip39';

/**
 * Generate a random secp256k1 private key
 */
export function generatePrivateKey(): string {
  const privateKey = secp256k1.utils.randomPrivateKey();
  return Buffer.from(privateKey).toString('hex');
}

/**
 * Derive public key from private key
 */
export function derivePublicKey(privateKeyHex: string): string {
  const privateKey = Buffer.from(privateKeyHex, 'hex');
  const publicKey = secp256k1.getPublicKey(privateKey, false); // Uncompressed
  return Buffer.from(publicKey).toString('hex');
}

/**
 * Generate XAI address from public key
 * Format: XAI + 40 hex chars (similar to Ethereum)
 */
export function generateAddress(publicKeyHex: string): string {
  const publicKey = Buffer.from(publicKeyHex, 'hex');
  
  // Hash with SHA-256 then RIPEMD-160
  const sha256Hash = sha256(publicKey);
  const ripemd160Hash = ripemd160(sha256Hash);
  
  // Take first 20 bytes and convert to hex
  const addressHash = Buffer.from(ripemd160Hash).toString('hex');
  
  // XAI prefix + 40 hex characters
  return 'XAI' + addressHash;
}

/**
 * Sign a message with a private key
 */
export async function signMessage(privateKeyHex: string, message: string): Promise<string> {
  const privateKey = Buffer.from(privateKeyHex, 'hex');
  const messageHash = sha256(Buffer.from(message, 'utf-8'));

  const signature = await secp256k1.signAsync(messageHash, privateKey);
  // Convert Signature object to compact format (64 bytes)
  const compactSig = signature.toCompactRawBytes();
  return Buffer.from(compactSig).toString('hex');
}

/**
 * Verify a signature
 */
export async function verifySignature(
  publicKeyHex: string,
  message: string,
  signatureHex: string
): Promise<boolean> {
  try {
    const publicKey = Buffer.from(publicKeyHex, 'hex');
    const messageHash = sha256(Buffer.from(message, 'utf-8'));
    const signatureBytes = Buffer.from(signatureHex, 'hex');

    // Create Signature object from compact bytes
    const signature = secp256k1.Signature.fromCompact(signatureBytes);
    return secp256k1.verify(signature, messageHash, publicKey);
  } catch (error) {
    return false;
  }
}

/**
 * Generate a BIP39 mnemonic phrase
 */
export function generateMnemonic(strength: number = 256): string {
  return bip39.generateMnemonic(strength);
}

/**
 * Validate a BIP39 mnemonic phrase
 */
export function validateMnemonic(mnemonic: string): boolean {
  return bip39.validateMnemonic(mnemonic);
}

/**
 * Derive seed from mnemonic
 */
export async function mnemonicToSeed(mnemonic: string, password?: string): Promise<Buffer> {
  return bip39.mnemonicToSeed(mnemonic, password);
}

/**
 * Derive private key from seed (simplified BIP32 derivation)
 */
export function deriveKeyFromSeed(seed: Buffer, index: number = 0): string {
  // Simple derivation: hash(seed + index)
  // For production, use full BIP32/BIP44 implementation
  const data = Buffer.concat([seed, Buffer.from([index])]);
  const hash = sha256(data);
  return Buffer.from(hash).toString('hex');
}

/**
 * Calculate SHA-256 hash
 */
export function hash256(data: string | Buffer): string {
  const buffer = typeof data === 'string' ? Buffer.from(data, 'utf-8') : data;
  return Buffer.from(sha256(buffer)).toString('hex');
}

/**
 * Validate address format
 */
export function validateAddress(address: string): boolean {
  // XAI addresses: XAI + 40 hex chars or TXAI + 40 hex chars (testnet)
  const mainnetPattern = /^XAI[0-9a-fA-F]{40}$/;
  const testnetPattern = /^TXAI[0-9a-fA-F]{40}$/;
  const specialAddresses = ['COINBASE'];
  
  return (
    mainnetPattern.test(address) ||
    testnetPattern.test(address) ||
    specialAddresses.includes(address)
  );
}
