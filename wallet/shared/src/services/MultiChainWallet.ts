/**
 * Multi-Chain Wallet Service
 * Unified wallet management for Aura, PAW, and XAI chains
 *
 * Features:
 * - Single mnemonic generates addresses on all chains
 * - Cosmos chains (Aura, PAW) share coin type 118
 * - XAI uses coin type 22593 (EVM-compatible)
 * - IBC transfers between Aura and PAW
 */

import * as bip39 from 'bip39';
import { bech32 } from 'bech32';
import { sha256 } from '@noble/hashes/sha256';
import { ripemd160 } from '@noble/hashes/ripemd160';
import { secp256k1 } from '@noble/curves/secp256k1';
import { HDKey } from '@scure/bip32';

import { ChainConfig, WalletAccount, Balance, IBCTransferParams } from '../types';
import { SUPPORTED_CHAINS, getChainConfig, getIBCChannel, canIBCTransfer } from '../chains';

const DEFAULT_HD_PATH = "m/44'/118'/0'/0/0";

export class MultiChainWallet {
  private mnemonic: string;
  private accounts: Map<string, WalletAccount> = new Map();
  private masterKey: HDKey | null = null;

  private constructor(mnemonic: string) {
    this.mnemonic = mnemonic;
  }

  /**
   * Create a new wallet with a fresh mnemonic
   */
  static async create(strength: 128 | 256 = 256): Promise<MultiChainWallet> {
    const mnemonic = bip39.generateMnemonic(strength);
    const wallet = new MultiChainWallet(mnemonic);
    await wallet.initMasterKey();
    return wallet;
  }

  /**
   * Import wallet from existing mnemonic
   */
  static async fromMnemonic(mnemonic: string): Promise<MultiChainWallet> {
    if (!bip39.validateMnemonic(mnemonic)) {
      throw new Error('Invalid mnemonic phrase');
    }
    const wallet = new MultiChainWallet(mnemonic);
    await wallet.initMasterKey();
    return wallet;
  }

  /**
   * Initialize master key from mnemonic
   */
  private async initMasterKey(): Promise<void> {
    const seed = await bip39.mnemonicToSeed(this.mnemonic);
    this.masterKey = HDKey.fromMasterSeed(seed);
  }

  /**
   * Get mnemonic (for backup purposes only)
   */
  getMnemonic(): string {
    return this.mnemonic;
  }

  /**
   * Derive HD path for a specific chain and account
   */
  private getHDPath(chainConfig: ChainConfig, accountIndex: number = 0): string {
    return `m/44'/${chainConfig.slip44}'/${accountIndex}'/0/0`;
  }

  /**
   * Derive public key from HD path
   */
  private deriveKeyPair(path: string): { privateKey: Uint8Array; publicKey: Uint8Array } {
    if (!this.masterKey) {
      throw new Error('Wallet not initialized');
    }
    const derived = this.masterKey.derive(path);
    if (!derived.privateKey) {
      throw new Error('Failed to derive private key');
    }
    const publicKey = secp256k1.getPublicKey(derived.privateKey, true);
    return {
      privateKey: derived.privateKey,
      publicKey,
    };
  }

  /**
   * Convert public key to bech32 address
   */
  private publicKeyToAddress(publicKey: Uint8Array, prefix: string): string {
    const sha256Hash = sha256(publicKey);
    const ripemd160Hash = ripemd160(sha256Hash);
    const words = bech32.toWords(ripemd160Hash);
    return bech32.encode(prefix, words);
  }

  /**
   * Get or create account for a specific chain
   */
  async getAccount(chainId: string, accountIndex: number = 0): Promise<WalletAccount> {
    const cacheKey = `${chainId}:${accountIndex}`;

    if (this.accounts.has(cacheKey)) {
      return this.accounts.get(cacheKey)!;
    }

    const chainConfig = getChainConfig(chainId);
    if (!chainConfig) {
      throw new Error(`Unknown chain: ${chainId}`);
    }

    const path = this.getHDPath(chainConfig, accountIndex);
    const { publicKey } = this.deriveKeyPair(path);
    const address = this.publicKeyToAddress(publicKey, chainConfig.bech32Prefix);

    const account: WalletAccount = {
      address,
      publicKey,
      chainId,
      path,
    };

    this.accounts.set(cacheKey, account);
    return account;
  }

  /**
   * Get accounts for all supported chains
   */
  async getAllAccounts(accountIndex: number = 0): Promise<WalletAccount[]> {
    const accounts: WalletAccount[] = [];
    for (const chainId of Object.keys(SUPPORTED_CHAINS)) {
      const account = await this.getAccount(chainId, accountIndex);
      accounts.push(account);
    }
    return accounts;
  }

  /**
   * Get accounts for mainnet chains only
   */
  async getMainnetAccounts(accountIndex: number = 0): Promise<WalletAccount[]> {
    const mainnetChains = ['aura-mainnet-1', 'paw-mainnet-1', 'xai-mainnet-1'];
    const accounts: WalletAccount[] = [];
    for (const chainId of mainnetChains) {
      const account = await this.getAccount(chainId, accountIndex);
      accounts.push(account);
    }
    return accounts;
  }

  /**
   * Get accounts for testnet chains only
   */
  async getTestnetAccounts(accountIndex: number = 0): Promise<WalletAccount[]> {
    const testnetChains = ['aura-testnet-1', 'paw-testnet-1', 'xai-testnet-1'];
    const accounts: WalletAccount[] = [];
    for (const chainId of testnetChains) {
      const account = await this.getAccount(chainId, accountIndex);
      accounts.push(account);
    }
    return accounts;
  }

  /**
   * Sign arbitrary bytes with the private key for a specific chain
   */
  async sign(chainId: string, message: Uint8Array, accountIndex: number = 0): Promise<Uint8Array> {
    const chainConfig = getChainConfig(chainId);
    if (!chainConfig) {
      throw new Error(`Unknown chain: ${chainId}`);
    }

    const path = this.getHDPath(chainConfig, accountIndex);
    const { privateKey } = this.deriveKeyPair(path);

    const messageHash = sha256(message);
    const signature = secp256k1.sign(messageHash, privateKey);

    return signature.toCompactRawBytes();
  }

  /**
   * Check if IBC transfer is possible between two chains
   */
  canTransferIBC(sourceChainId: string, destChainId: string): boolean {
    return canIBCTransfer(sourceChainId, destChainId);
  }

  /**
   * Get IBC channel for transfer
   */
  getIBCChannel(sourceChainId: string, destChainId: string): string | undefined {
    return getIBCChannel(sourceChainId, destChainId);
  }

  /**
   * Build IBC transfer message (Cosmos SDK format)
   */
  buildIBCTransferMsg(params: IBCTransferParams): any {
    const channel = this.getIBCChannel(params.sourceChain, params.destChain);
    if (!channel) {
      throw new Error(`No IBC channel between ${params.sourceChain} and ${params.destChain}`);
    }

    // Default timeout: 10 minutes from now
    const timeoutTimestamp = params.timeoutTimestamp ||
      String(Date.now() * 1_000_000 + 600_000_000_000);

    return {
      '@type': '/ibc.applications.transfer.v1.MsgTransfer',
      source_port: 'transfer',
      source_channel: params.sourceChannel || channel,
      token: params.amount,
      sender: params.sender,
      receiver: params.receiver,
      timeout_height: params.timeoutHeight || { revision_number: '0', revision_height: '0' },
      timeout_timestamp: timeoutTimestamp,
      memo: params.memo || '',
    };
  }

  /**
   * Verify address belongs to a specific chain
   */
  static verifyAddress(address: string, chainId: string): boolean {
    const chainConfig = getChainConfig(chainId);
    if (!chainConfig) {
      return false;
    }

    try {
      const decoded = bech32.decode(address);
      return decoded.prefix === chainConfig.bech32Prefix;
    } catch {
      return false;
    }
  }

  /**
   * Convert address between chains (same public key, different prefix)
   * Only works for chains with same coin type (Aura <-> PAW)
   */
  static convertAddress(address: string, targetChainId: string): string {
    const targetConfig = getChainConfig(targetChainId);
    if (!targetConfig) {
      throw new Error(`Unknown target chain: ${targetChainId}`);
    }

    try {
      const decoded = bech32.decode(address);
      return bech32.encode(targetConfig.bech32Prefix, decoded.words);
    } catch (err) {
      throw new Error(`Invalid address format: ${address}`);
    }
  }

  /**
   * Get linked addresses across Cosmos chains (Aura <-> PAW)
   * These addresses share the same public key due to same coin type 118
   */
  async getLinkedCosmosAddresses(accountIndex: number = 0): Promise<{ aura: string; paw: string }> {
    const auraAccount = await this.getAccount('aura-mainnet-1', accountIndex);
    const pawAccount = await this.getAccount('paw-mainnet-1', accountIndex);

    return {
      aura: auraAccount.address,
      paw: pawAccount.address,
    };
  }
}

export default MultiChainWallet;
