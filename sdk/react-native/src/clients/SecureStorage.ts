/**
 * Secure Storage Client
 * Encrypted local storage using react-native-keychain and AsyncStorage
 */

import * as Keychain from 'react-native-keychain';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { StorageError, SecureStorageOptions } from '../types';
import { encrypt, decrypt } from '../utils/crypto';

const STORAGE_PREFIX = '@xai:';
const MASTER_KEY_SERVICE = 'xai_master_key';

export class SecureStorage {
  private masterKey: string | null = null;

  /**
   * Initialize secure storage and load master key
   */
  async initialize(): Promise<void> {
    try {
      // Try to load existing master key
      const credentials = await Keychain.getGenericPassword({
        service: MASTER_KEY_SERVICE,
      });

      if (credentials) {
        this.masterKey = credentials.password;
      } else {
        // Generate new master key
        await this.generateMasterKey();
      }
    } catch (error) {
      throw new StorageError('Failed to initialize secure storage', error);
    }
  }

  /**
   * Generate and store a new master encryption key
   */
  private async generateMasterKey(): Promise<void> {
    try {
      // Generate random 256-bit key
      const key = Array.from({ length: 32 }, () =>
        Math.floor(Math.random() * 256)
      )
        .map((byte) => byte.toString(16).padStart(2, '0'))
        .join('');

      await Keychain.setGenericPassword(MASTER_KEY_SERVICE, key, {
        service: MASTER_KEY_SERVICE,
        accessible: Keychain.ACCESSIBLE.WHEN_UNLOCKED,
      });

      this.masterKey = key;
    } catch (error) {
      throw new StorageError('Failed to generate master key', error);
    }
  }

  /**
   * Store encrypted data
   */
  async setItem(
    key: string,
    value: string,
    options?: SecureStorageOptions
  ): Promise<void> {
    try {
      if (!this.masterKey) {
        await this.initialize();
      }

      const fullKey = STORAGE_PREFIX + key;

      if (options?.service) {
        // Store in secure keychain
        await Keychain.setGenericPassword(key, value, {
          service: options.service,
          accessible: Keychain.ACCESSIBLE.WHEN_UNLOCKED_THIS_DEVICE_ONLY,
        });
      } else {
        // Encrypt and store in AsyncStorage
        const encrypted = encrypt(value, this.masterKey!);
        await AsyncStorage.setItem(fullKey, encrypted);
      }
    } catch (error) {
      throw new StorageError(`Failed to store item: ${key}`, error);
    }
  }

  /**
   * Retrieve and decrypt data
   */
  async getItem(
    key: string,
    options?: SecureStorageOptions
  ): Promise<string | null> {
    try {
      if (!this.masterKey) {
        await this.initialize();
      }

      const fullKey = STORAGE_PREFIX + key;

      if (options?.service) {
        // Retrieve from secure keychain
        const credentials = await Keychain.getGenericPassword({
          service: options.service,
        });

        return credentials ? credentials.password : null;
      } else {
        // Retrieve and decrypt from AsyncStorage
        const encrypted = await AsyncStorage.getItem(fullKey);
        if (!encrypted) {
          return null;
        }

        return decrypt(encrypted, this.masterKey!);
      }
    } catch (error) {
      throw new StorageError(`Failed to retrieve item: ${key}`, error);
    }
  }

  /**
   * Remove item from storage
   */
  async removeItem(key: string, options?: SecureStorageOptions): Promise<void> {
    try {
      const fullKey = STORAGE_PREFIX + key;

      if (options?.service) {
        await Keychain.resetGenericPassword({ service: options.service });
      } else {
        await AsyncStorage.removeItem(fullKey);
      }
    } catch (error) {
      throw new StorageError(`Failed to remove item: ${key}`, error);
    }
  }

  /**
   * Store JSON data
   */
  async setJSON<T = any>(
    key: string,
    value: T,
    options?: SecureStorageOptions
  ): Promise<void> {
    const json = JSON.stringify(value);
    await this.setItem(key, json, options);
  }

  /**
   * Retrieve JSON data
   */
  async getJSON<T = any>(
    key: string,
    options?: SecureStorageOptions
  ): Promise<T | null> {
    const json = await this.getItem(key, options);
    if (!json) {
      return null;
    }

    try {
      return JSON.parse(json) as T;
    } catch (error) {
      throw new StorageError(`Failed to parse JSON for key: ${key}`, error);
    }
  }

  /**
   * Check if item exists
   */
  async hasItem(key: string, options?: SecureStorageOptions): Promise<boolean> {
    const item = await this.getItem(key, options);
    return item !== null;
  }

  /**
   * Clear all storage (except master key)
   */
  async clear(): Promise<void> {
    try {
      const keys = await AsyncStorage.getAllKeys();
      const xaiKeys = keys.filter((key) => key.startsWith(STORAGE_PREFIX));
      await AsyncStorage.multiRemove(xaiKeys);
    } catch (error) {
      throw new StorageError('Failed to clear storage', error);
    }
  }

  /**
   * Get all keys
   */
  async getAllKeys(): Promise<string[]> {
    try {
      const keys = await AsyncStorage.getAllKeys();
      return keys
        .filter((key) => key.startsWith(STORAGE_PREFIX))
        .map((key) => key.replace(STORAGE_PREFIX, ''));
    } catch (error) {
      throw new StorageError('Failed to get keys', error);
    }
  }

  /**
   * Reset master key (WARNING: will invalidate all encrypted data)
   */
  async resetMasterKey(): Promise<void> {
    try {
      await Keychain.resetGenericPassword({ service: MASTER_KEY_SERVICE });
      await this.generateMasterKey();
    } catch (error) {
      throw new StorageError('Failed to reset master key', error);
    }
  }
}

// Singleton instance
let storageInstance: SecureStorage | null = null;

export function getSecureStorage(): SecureStorage {
  if (!storageInstance) {
    storageInstance = new SecureStorage();
  }
  return storageInstance;
}
