/**
 * Wallet Client
 * Manages wallet creation, key management, and transaction signing
 */

import { HTTPClient } from '../utils/http-client';
import {
  generatePrivateKey,
  derivePublicKey,
  generateAddress,
  signMessage,
  generateMnemonic,
  validateMnemonic,
  mnemonicToSeed,
  deriveKeyFromSeed,
  validateAddress,
} from '../utils/crypto';
import { WalletError } from '../errors';
import {
  WalletKeyPair,
  WalletBackup,
  Balance,
  AddressNonce,
  TransactionHistory,
} from '../types';

export class Wallet {
  public readonly address: string;
  public readonly publicKey: string;
  private readonly privateKey: string;

  constructor(privateKey: string) {
    if (!privateKey || privateKey.length !== 64) {
      throw new WalletError('Invalid private key: must be 64 hex characters');
    }

    this.privateKey = privateKey;
    this.publicKey = derivePublicKey(privateKey);
    this.address = generateAddress(this.publicKey);
  }

  /**
   * Create a new wallet with a randomly generated private key
   */
  public static create(): Wallet {
    const privateKey = generatePrivateKey();
    return new Wallet(privateKey);
  }

  /**
   * Import wallet from private key
   */
  public static fromPrivateKey(privateKey: string): Wallet {
    return new Wallet(privateKey);
  }

  /**
   * Import wallet from mnemonic phrase
   */
  public static async fromMnemonic(mnemonic: string, index: number = 0): Promise<Wallet> {
    if (!validateMnemonic(mnemonic)) {
      throw new WalletError('Invalid mnemonic phrase');
    }

    const seed = await mnemonicToSeed(mnemonic);
    const privateKey = deriveKeyFromSeed(seed, index);
    return new Wallet(privateKey);
  }

  /**
   * Generate a new mnemonic phrase
   */
  public static generateMnemonic(strength: number = 256): string {
    return generateMnemonic(strength);
  }

  /**
   * Sign a message with this wallet's private key
   */
  public async sign(message: string): Promise<string> {
    return signMessage(this.privateKey, message);
  }

  /**
   * Export wallet to JSON format
   */
  public export(includePrivateKey: boolean = false): WalletBackup {
    const backup: WalletBackup = {
      address: this.address,
      public_key: this.publicKey,
    };

    if (includePrivateKey) {
      backup.private_key = this.privateKey;
    }

    return backup;
  }

  /**
   * Get the private key (use with caution)
   */
  public getPrivateKey(): string {
    return this.privateKey;
  }

  /**
   * Get key pair
   */
  public getKeyPair(): WalletKeyPair {
    return {
      address: this.address,
      publicKey: this.publicKey,
      privateKey: this.privateKey,
    };
  }
}

export class WalletClient {
  constructor(private httpClient: HTTPClient) {}

  /**
   * Create a new wallet
   */
  public create(): Wallet {
    return Wallet.create();
  }

  /**
   * Import wallet from private key
   */
  public fromPrivateKey(privateKey: string): Wallet {
    return Wallet.fromPrivateKey(privateKey);
  }

  /**
   * Import wallet from mnemonic
   */
  public async fromMnemonic(mnemonic: string, index: number = 0): Promise<Wallet> {
    return Wallet.fromMnemonic(mnemonic, index);
  }

  /**
   * Generate a new mnemonic phrase
   */
  public generateMnemonic(strength: number = 256): string {
    return Wallet.generateMnemonic(strength);
  }

  /**
   * Get balance for an address
   */
  public async getBalance(address: string): Promise<Balance> {
    if (!validateAddress(address)) {
      throw new WalletError(`Invalid address: ${address}`);
    }

    return this.httpClient.get<Balance>(`/balance/${address}`);
  }

  /**
   * Get nonce for an address
   */
  public async getNonce(address: string): Promise<AddressNonce> {
    if (!validateAddress(address)) {
      throw new WalletError(`Invalid address: ${address}`);
    }

    return this.httpClient.get<AddressNonce>(`/address/${address}/nonce`);
  }

  /**
   * Get transaction history for an address
   */
  public async getHistory(
    address: string,
    limit: number = 50,
    offset: number = 0
  ): Promise<TransactionHistory> {
    if (!validateAddress(address)) {
      throw new WalletError(`Invalid address: ${address}`);
    }

    return this.httpClient.get<TransactionHistory>(`/history/${address}`, {
      params: { limit, offset },
    });
  }

  /**
   * Validate an address format
   */
  public validateAddress(address: string): boolean {
    return validateAddress(address);
  }
}
