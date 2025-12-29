/**
 * Unit tests for storage utilities
 */

import * as SecureStore from 'expo-secure-store';
import {
  saveWallet,
  loadWallet,
  hasWallet,
  deleteWallet,
  saveSettings,
  loadSettings,
  importWallet,
  exportPrivateKey,
  StoredWallet,
  AppSettings,
} from '../../src/utils/storage';

describe('Storage Utilities', () => {
  beforeEach(() => {
    // Clear secure store before each test
    global.clearSecureStore();
  });

  describe('saveWallet', () => {
    const sampleWallet = {
      address: 'XAIa1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2',
      publicKey: 'test-public-key-hash',
      privateKey: 'test-private-key-hex',
    };

    it('should save wallet to secure store', async () => {
      await saveWallet(sampleWallet);

      expect(SecureStore.setItemAsync).toHaveBeenCalledWith(
        'xai_wallet_address',
        sampleWallet.address
      );
      expect(SecureStore.setItemAsync).toHaveBeenCalledWith(
        'xai_wallet_public_key',
        sampleWallet.publicKey
      );
      expect(SecureStore.setItemAsync).toHaveBeenCalledWith(
        'xai_wallet_private_key',
        sampleWallet.privateKey
      );
    });

    it('should save creation timestamp', async () => {
      const beforeTime = Date.now();
      await saveWallet(sampleWallet);
      const afterTime = Date.now();

      const createdAtCall = (SecureStore.setItemAsync as jest.Mock).mock.calls.find(
        (call) => call[0] === 'xai_wallet_created_at'
      );

      expect(createdAtCall).toBeDefined();
      const savedTime = parseInt(createdAtCall[1], 10);
      expect(savedTime).toBeGreaterThanOrEqual(beforeTime);
      expect(savedTime).toBeLessThanOrEqual(afterTime);
    });

    it('should save all wallet fields in parallel', async () => {
      await saveWallet(sampleWallet);

      // Should have 4 calls: address, publicKey, privateKey, createdAt
      expect(SecureStore.setItemAsync).toHaveBeenCalledTimes(4);
    });
  });

  describe('loadWallet', () => {
    it('should return null when no wallet exists', async () => {
      const wallet = await loadWallet();
      expect(wallet).toBeNull();
    });

    it('should load wallet from secure store', async () => {
      const sampleWallet = {
        address: 'XAIa1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2',
        publicKey: 'test-public-key',
        privateKey: 'test-private-key',
      };

      await saveWallet(sampleWallet);
      const loaded = await loadWallet();

      expect(loaded).not.toBeNull();
      expect(loaded?.address).toBe(sampleWallet.address);
      expect(loaded?.publicKey).toBe(sampleWallet.publicKey);
      expect(loaded?.privateKey).toBe(sampleWallet.privateKey);
    });

    it('should include createdAt timestamp', async () => {
      const sampleWallet = {
        address: 'XAItest',
        publicKey: 'pub',
        privateKey: 'priv',
      };

      await saveWallet(sampleWallet);
      const loaded = await loadWallet();

      expect(loaded?.createdAt).toBeDefined();
      expect(typeof loaded?.createdAt).toBe('number');
    });

    it('should return null if address is missing', async () => {
      (SecureStore.getItemAsync as jest.Mock)
        .mockResolvedValueOnce(null) // address
        .mockResolvedValueOnce('pub')
        .mockResolvedValueOnce('priv')
        .mockResolvedValueOnce('12345');

      const loaded = await loadWallet();
      expect(loaded).toBeNull();
    });

    it('should return null if privateKey is missing', async () => {
      (SecureStore.getItemAsync as jest.Mock)
        .mockResolvedValueOnce('addr')
        .mockResolvedValueOnce('pub')
        .mockResolvedValueOnce(null) // privateKey
        .mockResolvedValueOnce('12345');

      const loaded = await loadWallet();
      expect(loaded).toBeNull();
    });

    it('should handle storage errors gracefully', async () => {
      (SecureStore.getItemAsync as jest.Mock).mockRejectedValue(
        new Error('Storage error')
      );

      const loaded = await loadWallet();
      expect(loaded).toBeNull();
    });
  });

  describe('hasWallet', () => {
    it('should return false when no wallet exists', async () => {
      const exists = await hasWallet();
      expect(exists).toBe(false);
    });

    it('should return true when wallet exists', async () => {
      await saveWallet({
        address: 'XAItest',
        publicKey: 'pub',
        privateKey: 'priv',
      });

      const exists = await hasWallet();
      expect(exists).toBe(true);
    });
  });

  describe('deleteWallet', () => {
    it('should delete all wallet fields', async () => {
      await saveWallet({
        address: 'XAItest',
        publicKey: 'pub',
        privateKey: 'priv',
      });

      await deleteWallet();

      expect(SecureStore.deleteItemAsync).toHaveBeenCalledWith('xai_wallet_address');
      expect(SecureStore.deleteItemAsync).toHaveBeenCalledWith('xai_wallet_public_key');
      expect(SecureStore.deleteItemAsync).toHaveBeenCalledWith('xai_wallet_private_key');
      expect(SecureStore.deleteItemAsync).toHaveBeenCalledWith('xai_wallet_created_at');
    });

    it('should result in hasWallet returning false', async () => {
      await saveWallet({
        address: 'XAItest',
        publicKey: 'pub',
        privateKey: 'priv',
      });

      await deleteWallet();
      global.clearSecureStore(); // Simulate the deletion

      const exists = await hasWallet();
      expect(exists).toBe(false);
    });
  });

  describe('saveSettings', () => {
    it('should merge with existing settings', async () => {
      // Save initial settings
      await saveSettings({ theme: 'dark' });

      // Save additional settings
      await saveSettings({ notifications: false });

      // Load and verify merged settings
      const settings = await loadSettings();
      expect(settings.theme).toBe('dark');
      expect(settings.notifications).toBe(false);
    });

    it('should save settings as JSON', async () => {
      await saveSettings({ theme: 'light' });

      const settingsCall = (SecureStore.setItemAsync as jest.Mock).mock.calls.find(
        (call) => call[0] === 'xai_settings'
      );

      expect(settingsCall).toBeDefined();
      const savedJson = JSON.parse(settingsCall[1]);
      expect(savedJson.theme).toBe('light');
    });
  });

  describe('loadSettings', () => {
    it('should return default settings when none exist', async () => {
      const settings = await loadSettings();

      expect(settings).toEqual({
        nodeUrl: 'http://localhost:12001',
        theme: 'system',
        notifications: true,
        biometricEnabled: false,
      });
    });

    it('should load saved settings', async () => {
      await saveSettings({
        nodeUrl: 'http://custom:8080',
        theme: 'dark',
      });

      const settings = await loadSettings();

      expect(settings.nodeUrl).toBe('http://custom:8080');
      expect(settings.theme).toBe('dark');
    });

    it('should merge saved settings with defaults', async () => {
      await saveSettings({ theme: 'dark' });

      const settings = await loadSettings();

      // Should have saved value
      expect(settings.theme).toBe('dark');
      // Should have default values for unsaved
      expect(settings.notifications).toBe(true);
    });

    it('should handle corrupt JSON gracefully', async () => {
      (SecureStore.getItemAsync as jest.Mock).mockResolvedValue('not-valid-json');

      const settings = await loadSettings();

      // Should return defaults on parse error
      expect(settings.nodeUrl).toBe('http://localhost:12001');
    });
  });

  describe('importWallet', () => {
    const mockDerivePublicKey = jest.fn().mockResolvedValue('derived-public-key');
    const mockDeriveAddress = jest.fn().mockResolvedValue('XAIa1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2');

    beforeEach(() => {
      mockDerivePublicKey.mockClear();
      mockDeriveAddress.mockClear();
    });

    it('should derive public key from private key', async () => {
      const privateKey = 'imported-private-key';
      await importWallet(privateKey, mockDerivePublicKey, mockDeriveAddress);

      expect(mockDerivePublicKey).toHaveBeenCalledWith(privateKey);
    });

    it('should derive address from public key', async () => {
      await importWallet('priv', mockDerivePublicKey, mockDeriveAddress);

      expect(mockDeriveAddress).toHaveBeenCalledWith('derived-public-key');
    });

    it('should save imported wallet', async () => {
      await importWallet('priv', mockDerivePublicKey, mockDeriveAddress);

      expect(SecureStore.setItemAsync).toHaveBeenCalledWith(
        'xai_wallet_private_key',
        'priv'
      );
      expect(SecureStore.setItemAsync).toHaveBeenCalledWith(
        'xai_wallet_public_key',
        'derived-public-key'
      );
    });

    it('should return stored wallet with createdAt', async () => {
      const result = await importWallet('priv', mockDerivePublicKey, mockDeriveAddress);

      expect(result).toHaveProperty('address');
      expect(result).toHaveProperty('publicKey');
      expect(result).toHaveProperty('privateKey');
      expect(result).toHaveProperty('createdAt');
      expect(typeof result.createdAt).toBe('number');
    });
  });

  describe('exportPrivateKey', () => {
    it('should return private key when wallet exists', async () => {
      await saveWallet({
        address: 'XAItest',
        publicKey: 'pub',
        privateKey: 'secret-key',
      });

      const key = await exportPrivateKey();
      expect(key).toBe('secret-key');
    });

    it('should return null when no wallet exists', async () => {
      const key = await exportPrivateKey();
      expect(key).toBeNull();
    });
  });
});
