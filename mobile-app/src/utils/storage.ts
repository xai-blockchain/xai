import AsyncStorage from '@react-native-async-storage/async-storage';
import * as Keychain from 'react-native-keychain';
import { STORAGE_KEYS, SECURITY } from '@/constants';

/**
 * Secure storage for sensitive data using Keychain
 */
export const SecureStorage = {
  /**
   * Store private key securely
   */
  async setPrivateKey(privateKey: string): Promise<void> {
    await Keychain.setGenericPassword('privateKey', privateKey, {
      service: SECURITY.KEYCHAIN_SERVICE,
      accessible: Keychain.ACCESSIBLE.WHEN_UNLOCKED,
      securityLevel: Keychain.SECURITY_LEVEL.SECURE_HARDWARE,
    });
  },

  /**
   * Retrieve private key
   */
  async getPrivateKey(): Promise<string | null> {
    try {
      const credentials = await Keychain.getGenericPassword({
        service: SECURITY.KEYCHAIN_SERVICE,
      });
      return credentials ? credentials.password : null;
    } catch (error) {
      console.error('Failed to retrieve private key:', error);
      return null;
    }
  },

  /**
   * Store mnemonic securely
   */
  async setMnemonic(mnemonic: string): Promise<void> {
    await Keychain.setGenericPassword('mnemonic', mnemonic, {
      service: `${SECURITY.KEYCHAIN_SERVICE}_mnemonic`,
      accessible: Keychain.ACCESSIBLE.WHEN_UNLOCKED,
      securityLevel: Keychain.SECURITY_LEVEL.SECURE_HARDWARE,
    });
  },

  /**
   * Retrieve mnemonic
   */
  async getMnemonic(): Promise<string | null> {
    try {
      const credentials = await Keychain.getGenericPassword({
        service: `${SECURITY.KEYCHAIN_SERVICE}_mnemonic`,
      });
      return credentials ? credentials.password : null;
    } catch (error) {
      console.error('Failed to retrieve mnemonic:', error);
      return null;
    }
  },

  /**
   * Clear all secure storage
   */
  async clear(): Promise<void> {
    await Keychain.resetGenericPassword({ service: SECURITY.KEYCHAIN_SERVICE });
    await Keychain.resetGenericPassword({ service: `${SECURITY.KEYCHAIN_SERVICE}_mnemonic` });
  },
};

/**
 * General storage utilities
 */
export const Storage = {
  /**
   * Store data
   */
  async set<T>(key: string, value: T): Promise<void> {
    try {
      const jsonValue = JSON.stringify(value);
      await AsyncStorage.setItem(key, jsonValue);
    } catch (error) {
      console.error(`Failed to store ${key}:`, error);
      throw error;
    }
  },

  /**
   * Retrieve data
   */
  async get<T>(key: string): Promise<T | null> {
    try {
      const jsonValue = await AsyncStorage.getItem(key);
      return jsonValue != null ? JSON.parse(jsonValue) : null;
    } catch (error) {
      console.error(`Failed to retrieve ${key}:`, error);
      return null;
    }
  },

  /**
   * Remove data
   */
  async remove(key: string): Promise<void> {
    try {
      await AsyncStorage.removeItem(key);
    } catch (error) {
      console.error(`Failed to remove ${key}:`, error);
    }
  },

  /**
   * Clear all storage
   */
  async clear(): Promise<void> {
    try {
      await AsyncStorage.clear();
    } catch (error) {
      console.error('Failed to clear storage:', error);
    }
  },

  /**
   * Get multiple items
   */
  async getMultiple(keys: string[]): Promise<{ [key: string]: any }> {
    try {
      const pairs = await AsyncStorage.multiGet(keys);
      const result: { [key: string]: any } = {};
      pairs.forEach(([key, value]) => {
        if (value != null) {
          try {
            result[key] = JSON.parse(value);
          } catch {
            result[key] = value;
          }
        }
      });
      return result;
    } catch (error) {
      console.error('Failed to get multiple items:', error);
      return {};
    }
  },
};

/**
 * Wallet-specific storage utilities
 */
export const WalletStorage = {
  async saveWallet(wallet: any): Promise<void> {
    // Store non-sensitive data in AsyncStorage
    const publicWallet = {
      address: wallet.address,
      publicKey: wallet.publicKey,
      name: wallet.name,
      createdAt: wallet.createdAt,
    };
    await Storage.set(STORAGE_KEYS.WALLET, publicWallet);

    // Store sensitive data in Keychain
    if (wallet.privateKey) {
      await SecureStorage.setPrivateKey(wallet.privateKey);
    }
    if (wallet.mnemonic) {
      await SecureStorage.setMnemonic(wallet.mnemonic);
    }
  },

  async loadWallet(): Promise<any | null> {
    const publicWallet = await Storage.get(STORAGE_KEYS.WALLET);
    if (!publicWallet) return null;

    const privateKey = await SecureStorage.getPrivateKey();
    const mnemonic = await SecureStorage.getMnemonic();

    return {
      ...publicWallet,
      privateKey,
      mnemonic,
    };
  },

  async deleteWallet(): Promise<void> {
    await Storage.remove(STORAGE_KEYS.WALLET);
    await SecureStorage.clear();
  },
};
