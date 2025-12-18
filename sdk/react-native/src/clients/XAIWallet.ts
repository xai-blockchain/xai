/**
 * XAI Wallet Client
 * Secure wallet management with biometric authentication support
 */

import {
  Wallet,
  WalletError,
  BiometricConfig,
  StoredWallet,
} from '../types';
import {
  generateWallet,
  generateWalletFromMnemonic,
  validateMnemonic,
  signMessage,
  encrypt,
  decrypt,
} from '../utils/crypto';
import { SecureStorage, getSecureStorage } from './SecureStorage';
import { BiometricAuth, getBiometricAuth } from './BiometricAuth';

const WALLET_STORAGE_KEY = 'current_wallet';
const WALLET_PASSWORD_KEY = 'wallet_password';

export class XAIWallet {
  private storage: SecureStorage;
  private biometric: BiometricAuth;
  private currentWallet: Wallet | null = null;

  constructor() {
    this.storage = getSecureStorage();
    this.biometric = getBiometricAuth();
  }

  /**
   * Initialize wallet client
   */
  async initialize(): Promise<void> {
    await this.storage.initialize();

    // Try to load existing wallet
    const storedWallet = await this.storage.getJSON<StoredWallet>(
      WALLET_STORAGE_KEY
    );

    if (storedWallet) {
      // Wallet exists but private key is encrypted
      // Will be decrypted on first use
      this.currentWallet = {
        address: storedWallet.address,
        publicKey: storedWallet.publicKey,
      };
    }
  }

  /**
   * Create a new wallet
   */
  async createWallet(biometricEnabled: boolean = false): Promise<Wallet> {
    try {
      // Check if biometric is requested but not available
      if (biometricEnabled) {
        const available = await this.biometric.isAvailable();
        if (!available) {
          throw new WalletError('Biometric authentication not available');
        }
      }

      // Generate new wallet
      const wallet = generateWallet();

      // Store wallet securely
      await this.storeWallet(wallet, biometricEnabled);

      // Set as current wallet (without private key in memory)
      this.currentWallet = {
        address: wallet.address,
        publicKey: wallet.publicKey,
      };

      return wallet;
    } catch (error: any) {
      throw new WalletError('Failed to create wallet', error);
    }
  }

  /**
   * Import wallet from mnemonic phrase
   */
  async importWallet(
    mnemonic: string,
    biometricEnabled: boolean = false
  ): Promise<Wallet> {
    try {
      // Validate mnemonic
      if (!validateMnemonic(mnemonic)) {
        throw new WalletError('Invalid mnemonic phrase');
      }

      // Check if biometric is requested but not available
      if (biometricEnabled) {
        const available = await this.biometric.isAvailable();
        if (!available) {
          throw new WalletError('Biometric authentication not available');
        }
      }

      // Generate wallet from mnemonic
      const wallet = generateWalletFromMnemonic(mnemonic);

      // Store wallet securely
      await this.storeWallet(wallet, biometricEnabled);

      // Set as current wallet
      this.currentWallet = {
        address: wallet.address,
        publicKey: wallet.publicKey,
      };

      return wallet;
    } catch (error: any) {
      throw new WalletError('Failed to import wallet', error);
    }
  }

  /**
   * Get current wallet (without private key)
   */
  getCurrentWallet(): Wallet | null {
    return this.currentWallet;
  }

  /**
   * Get wallet address
   */
  getAddress(): string | null {
    return this.currentWallet?.address || null;
  }

  /**
   * Check if wallet exists
   */
  async hasWallet(): Promise<boolean> {
    const stored = await this.storage.hasItem(WALLET_STORAGE_KEY);
    return stored;
  }

  /**
   * Sign a message with wallet private key
   * Requires biometric authentication if enabled
   */
  async signMessage(
    message: string,
    config?: BiometricConfig
  ): Promise<string> {
    try {
      if (!this.currentWallet) {
        throw new WalletError('No wallet loaded');
      }

      // Get private key (with biometric auth if enabled)
      const privateKey = await this.getPrivateKey(config);

      // Sign the message
      const signature = signMessage(message, privateKey);

      return signature;
    } catch (error: any) {
      throw new WalletError('Failed to sign message', error);
    }
  }

  /**
   * Get private key (requires authentication)
   */
  async getPrivateKey(config?: BiometricConfig): Promise<string> {
    try {
      if (!this.currentWallet) {
        throw new WalletError('No wallet loaded');
      }

      const storedWallet = await this.storage.getJSON<StoredWallet>(
        WALLET_STORAGE_KEY
      );

      if (!storedWallet) {
        throw new WalletError('Wallet not found');
      }

      // Check if biometric is enabled
      if (storedWallet.biometricEnabled) {
        // Authenticate with biometrics
        const authenticated = await this.biometric.authenticate(config);
        if (!authenticated) {
          throw new WalletError('Authentication failed');
        }
      }

      // Get wallet password
      const password = await this.storage.getItem(WALLET_PASSWORD_KEY);
      if (!password) {
        throw new WalletError('Wallet password not found');
      }

      // Decrypt private key
      const privateKey = decrypt(storedWallet.encryptedPrivateKey, password);

      return privateKey;
    } catch (error: any) {
      throw new WalletError('Failed to get private key', error);
    }
  }

  /**
   * Export mnemonic (requires authentication)
   */
  async exportMnemonic(config?: BiometricConfig): Promise<string> {
    try {
      const storedWallet = await this.storage.getJSON<StoredWallet>(
        WALLET_STORAGE_KEY
      );

      if (!storedWallet) {
        throw new WalletError('No wallet found');
      }

      // Check if biometric is enabled
      if (storedWallet.biometricEnabled) {
        const authenticated = await this.biometric.authenticate(config);
        if (!authenticated) {
          throw new WalletError('Authentication failed');
        }
      }

      // Get mnemonic from secure storage
      const mnemonic = await this.storage.getItem('wallet_mnemonic', {
        service: 'xai_mnemonic',
      });

      if (!mnemonic) {
        throw new WalletError('Mnemonic not found');
      }

      return mnemonic;
    } catch (error: any) {
      throw new WalletError('Failed to export mnemonic', error);
    }
  }

  /**
   * Delete wallet
   */
  async deleteWallet(config?: BiometricConfig): Promise<void> {
    try {
      const storedWallet = await this.storage.getJSON<StoredWallet>(
        WALLET_STORAGE_KEY
      );

      if (storedWallet?.biometricEnabled) {
        // Require authentication before deletion
        const authenticated = await this.biometric.authenticate(config);
        if (!authenticated) {
          throw new WalletError('Authentication required to delete wallet');
        }
      }

      // Remove all wallet data
      await this.storage.removeItem(WALLET_STORAGE_KEY);
      await this.storage.removeItem(WALLET_PASSWORD_KEY);
      await this.storage.removeItem('wallet_mnemonic', {
        service: 'xai_mnemonic',
      });

      // Delete biometric keys if they exist
      if (await this.biometric.hasKeys()) {
        await this.biometric.deleteKeys();
      }

      this.currentWallet = null;
    } catch (error: any) {
      throw new WalletError('Failed to delete wallet', error);
    }
  }

  /**
   * Enable or disable biometric authentication
   */
  async setBiometricEnabled(
    enabled: boolean,
    config?: BiometricConfig
  ): Promise<void> {
    try {
      const storedWallet = await this.storage.getJSON<StoredWallet>(
        WALLET_STORAGE_KEY
      );

      if (!storedWallet) {
        throw new WalletError('No wallet found');
      }

      if (enabled) {
        // Check if biometric is available
        const available = await this.biometric.isAvailable();
        if (!available) {
          throw new WalletError('Biometric authentication not available');
        }

        // Test authentication
        const authenticated = await this.biometric.authenticate(config);
        if (!authenticated) {
          throw new WalletError('Biometric authentication failed');
        }
      }

      // Update stored wallet
      storedWallet.biometricEnabled = enabled;
      await this.storage.setJSON(WALLET_STORAGE_KEY, storedWallet);
    } catch (error: any) {
      throw new WalletError('Failed to update biometric setting', error);
    }
  }

  /**
   * Check if biometric is enabled for wallet
   */
  async isBiometricEnabled(): Promise<boolean> {
    const storedWallet = await this.storage.getJSON<StoredWallet>(
      WALLET_STORAGE_KEY
    );
    return storedWallet?.biometricEnabled || false;
  }

  /**
   * Store wallet securely
   */
  private async storeWallet(
    wallet: Wallet,
    biometricEnabled: boolean
  ): Promise<void> {
    // Generate random password for encryption
    const password = Array.from({ length: 32 }, () =>
      Math.floor(Math.random() * 256)
    )
      .map((byte) => byte.toString(16).padStart(2, '0'))
      .join('');

    // Encrypt private key
    const encryptedPrivateKey = encrypt(wallet.privateKey!, password);

    // Store encrypted wallet
    const storedWallet: StoredWallet = {
      address: wallet.address,
      publicKey: wallet.publicKey,
      encryptedPrivateKey,
      biometricEnabled,
      createdAt: Date.now(),
    };

    await this.storage.setJSON(WALLET_STORAGE_KEY, storedWallet);
    await this.storage.setItem(WALLET_PASSWORD_KEY, password);

    // Store mnemonic in keychain
    if (wallet.mnemonic) {
      await this.storage.setItem('wallet_mnemonic', wallet.mnemonic, {
        service: 'xai_mnemonic',
      });
    }
  }
}

// Singleton instance
let walletInstance: XAIWallet | null = null;

export function getXAIWallet(): XAIWallet {
  if (!walletInstance) {
    walletInstance = new XAIWallet();
  }
  return walletInstance;
}
