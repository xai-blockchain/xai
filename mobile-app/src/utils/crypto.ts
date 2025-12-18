import { ec as EC } from 'elliptic';
import * as bip39 from 'bip39';
import { sha256 } from 'react-native-sha256';
import { randomBytes } from 'react-native-randombytes';

const ec = new EC('secp256k1');

export interface KeyPair {
  privateKey: string;
  publicKey: string;
  address: string;
}

/**
 * Generate a new mnemonic phrase
 */
export const generateMnemonic = (): string => {
  return bip39.generateMnemonic(256); // 24 words
};

/**
 * Validate mnemonic phrase
 */
export const validateMnemonic = (mnemonic: string): boolean => {
  return bip39.validateMnemonic(mnemonic);
};

/**
 * Derive private key from mnemonic
 */
export const mnemonicToPrivateKey = async (mnemonic: string): Promise<string> => {
  if (!validateMnemonic(mnemonic)) {
    throw new Error('Invalid mnemonic phrase');
  }

  const seed = await bip39.mnemonicToSeed(mnemonic);
  const hash = await sha256(seed.toString('hex'));
  return hash;
};

/**
 * Generate keypair from private key
 */
export const privateKeyToKeyPair = (privateKey: string): KeyPair => {
  const keyPair = ec.keyFromPrivate(privateKey, 'hex');
  const publicKey = keyPair.getPublic('hex');
  const address = publicKeyToAddress(publicKey);

  return {
    privateKey,
    publicKey,
    address,
  };
};

/**
 * Derive address from public key
 */
export const publicKeyToAddress = (publicKey: string): string => {
  // XAI uses simple SHA-256 hash of public key for address
  const hash = sha256(publicKey);
  return hash.then(h => 'XAI' + h.substring(0, 40));
};

/**
 * Generate a new wallet with mnemonic
 */
export const generateWallet = async (): Promise<{
  mnemonic: string;
  keyPair: KeyPair;
}> => {
  const mnemonic = generateMnemonic();
  const privateKey = await mnemonicToPrivateKey(mnemonic);
  const keyPair = privateKeyToKeyPair(privateKey);

  return {
    mnemonic,
    keyPair,
  };
};

/**
 * Import wallet from mnemonic
 */
export const importWalletFromMnemonic = async (mnemonic: string): Promise<KeyPair> => {
  const privateKey = await mnemonicToPrivateKey(mnemonic);
  return privateKeyToKeyPair(privateKey);
};

/**
 * Import wallet from private key
 */
export const importWalletFromPrivateKey = (privateKey: string): KeyPair => {
  return privateKeyToKeyPair(privateKey);
};

/**
 * Sign message with private key
 */
export const signMessage = async (message: string, privateKey: string): Promise<string> => {
  const keyPair = ec.keyFromPrivate(privateKey, 'hex');
  const msgHash = await sha256(message);
  const signature = keyPair.sign(msgHash);
  return signature.toDER('hex');
};

/**
 * Verify signature
 */
export const verifySignature = async (
  message: string,
  signature: string,
  publicKey: string,
): Promise<boolean> => {
  try {
    const keyPair = ec.keyFromPublic(publicKey, 'hex');
    const msgHash = await sha256(message);
    return keyPair.verify(msgHash, signature);
  } catch (error) {
    return false;
  }
};

/**
 * Generate random bytes
 */
export const generateRandomBytes = (length: number): Promise<Uint8Array> => {
  return new Promise((resolve, reject) => {
    randomBytes(length, (error: Error | null, bytes: Uint8Array) => {
      if (error) reject(error);
      else resolve(bytes);
    });
  });
};

/**
 * Validate XAI address format
 */
export const isValidAddress = (address: string): boolean => {
  return /^XAI[0-9a-fA-F]{40}$/.test(address);
};

/**
 * Format address for display (truncated)
 */
export const formatAddress = (address: string, chars: number = 8): string => {
  if (!address || address.length < chars * 2) return address;
  return `${address.substring(0, chars)}...${address.substring(address.length - chars)}`;
};
