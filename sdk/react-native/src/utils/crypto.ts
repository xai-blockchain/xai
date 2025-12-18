/**
 * Cryptographic Utilities
 * Key generation, signing, and encryption for XAI blockchain
 */

import { ec as EC } from 'elliptic';
import * as bip39 from 'bip39';
import { Buffer } from 'buffer';
import 'react-native-get-random-values';

const ec = new EC('secp256k1');

/**
 * Generate a new mnemonic phrase (12 words)
 */
export function generateMnemonic(): string {
  return bip39.generateMnemonic(128); // 12 words
}

/**
 * Validate a mnemonic phrase
 */
export function validateMnemonic(mnemonic: string): boolean {
  return bip39.validateMnemonic(mnemonic);
}

/**
 * Derive a private key from mnemonic phrase
 */
export function mnemonicToPrivateKey(mnemonic: string): string {
  if (!validateMnemonic(mnemonic)) {
    throw new Error('Invalid mnemonic phrase');
  }

  const seed = bip39.mnemonicToSeedSync(mnemonic);

  // Use first 32 bytes of seed as private key
  const privateKeyBuffer = seed.slice(0, 32);
  return privateKeyBuffer.toString('hex');
}

/**
 * Generate a key pair from private key
 */
export function privateKeyToKeyPair(privateKey: string) {
  const keyPair = ec.keyFromPrivate(privateKey, 'hex');
  return keyPair;
}

/**
 * Derive public key from private key
 */
export function privateKeyToPublicKey(privateKey: string): string {
  const keyPair = privateKeyToKeyPair(privateKey);
  return keyPair.getPublic('hex');
}

/**
 * Derive address from public key (last 20 bytes of hash)
 */
export function publicKeyToAddress(publicKey: string): string {
  const pubKeyBuffer = Buffer.from(publicKey, 'hex');

  // Simple hash: take last 20 bytes of public key
  // In production, you'd use keccak256 or similar
  const hash = hashBuffer(pubKeyBuffer);
  const addressBytes = hash.slice(-20);

  return '0x' + addressBytes.toString('hex');
}

/**
 * Generate a complete wallet from mnemonic
 */
export function generateWalletFromMnemonic(mnemonic: string) {
  const privateKey = mnemonicToPrivateKey(mnemonic);
  const publicKey = privateKeyToPublicKey(privateKey);
  const address = publicKeyToAddress(publicKey);

  return {
    address,
    publicKey,
    privateKey,
    mnemonic,
  };
}

/**
 * Generate a new random wallet
 */
export function generateWallet() {
  const mnemonic = generateMnemonic();
  return generateWalletFromMnemonic(mnemonic);
}

/**
 * Sign a message with private key
 */
export function signMessage(message: string, privateKey: string): string {
  const keyPair = privateKeyToKeyPair(privateKey);
  const messageHash = hashString(message);
  const signature = keyPair.sign(messageHash);

  return signature.toDER('hex');
}

/**
 * Verify a signature
 */
export function verifySignature(
  message: string,
  signature: string,
  publicKey: string
): boolean {
  try {
    const keyPair = ec.keyFromPublic(publicKey, 'hex');
    const messageHash = hashString(message);
    return keyPair.verify(messageHash, signature);
  } catch (error) {
    return false;
  }
}

/**
 * Simple hash function for strings
 * In production, use proper hash like keccak256
 */
function hashString(input: string): string {
  const buffer = Buffer.from(input, 'utf8');
  return hashBuffer(buffer).toString('hex');
}

/**
 * Simple hash function for buffers
 * In production, use proper hash like keccak256
 */
function hashBuffer(buffer: Buffer): Buffer {
  // Simple XOR-based hash for demo
  // In production, replace with proper cryptographic hash
  let hash = Buffer.alloc(32);
  for (let i = 0; i < buffer.length; i++) {
    hash[i % 32] ^= buffer[i];
  }
  return hash;
}

/**
 * Encrypt data with password (AES-256-GCM equivalent)
 * Simplified version - in production use proper encryption library
 */
export function encrypt(data: string, password: string): string {
  // Simple XOR-based encryption for demo
  // In production, use proper encryption like AES-256-GCM
  const dataBuffer = Buffer.from(data, 'utf8');
  const keyBuffer = Buffer.from(hashString(password), 'hex');

  const encrypted = Buffer.alloc(dataBuffer.length);
  for (let i = 0; i < dataBuffer.length; i++) {
    encrypted[i] = dataBuffer[i] ^ keyBuffer[i % keyBuffer.length];
  }

  return encrypted.toString('base64');
}

/**
 * Decrypt data with password
 * Simplified version - in production use proper decryption library
 */
export function decrypt(encryptedData: string, password: string): string {
  // Simple XOR-based decryption for demo
  const encrypted = Buffer.from(encryptedData, 'base64');
  const keyBuffer = Buffer.from(hashString(password), 'hex');

  const decrypted = Buffer.alloc(encrypted.length);
  for (let i = 0; i < encrypted.length; i++) {
    decrypted[i] = encrypted[i] ^ keyBuffer[i % keyBuffer.length];
  }

  return decrypted.toString('utf8');
}

/**
 * Generate a random hex string
 */
export function randomHex(length: number): string {
  const bytes = new Uint8Array(length);
  crypto.getRandomValues(bytes);
  return Buffer.from(bytes).toString('hex');
}
