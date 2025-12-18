/**
 * XAIWallet Tests
 */

import { XAIWallet } from '../clients/XAIWallet';
import { WalletError } from '../types';

describe('XAIWallet', () => {
  let wallet: XAIWallet;

  beforeEach(() => {
    wallet = new XAIWallet();
  });

  describe('initialization', () => {
    it('should initialize successfully', async () => {
      await expect(wallet.initialize()).resolves.not.toThrow();
    });
  });

  describe('wallet creation', () => {
    it('should create a new wallet without biometric', async () => {
      await wallet.initialize();
      const newWallet = await wallet.createWallet(false);

      expect(newWallet).toHaveProperty('address');
      expect(newWallet).toHaveProperty('publicKey');
      expect(newWallet).toHaveProperty('privateKey');
      expect(newWallet).toHaveProperty('mnemonic');
      expect(newWallet.address).toMatch(/^0x[a-f0-9]{40}$/i);
    });

    it('should create a new wallet with biometric enabled', async () => {
      await wallet.initialize();
      const newWallet = await wallet.createWallet(true);

      expect(newWallet).toHaveProperty('address');
      expect(await wallet.isBiometricEnabled()).toBe(true);
    });
  });

  describe('wallet import', () => {
    it('should import wallet from valid mnemonic', async () => {
      await wallet.initialize();

      // Create wallet first to get mnemonic
      const createdWallet = await wallet.createWallet(false);
      const mnemonic = createdWallet.mnemonic!;

      // Delete and reimport
      await wallet.deleteWallet();
      const importedWallet = await wallet.importWallet(mnemonic, false);

      expect(importedWallet.address).toBe(createdWallet.address);
    });

    it('should reject invalid mnemonic', async () => {
      await wallet.initialize();

      await expect(
        wallet.importWallet('invalid mnemonic phrase', false)
      ).rejects.toThrow(WalletError);
    });
  });

  describe('wallet operations', () => {
    beforeEach(async () => {
      await wallet.initialize();
      await wallet.createWallet(false);
    });

    it('should get current wallet', () => {
      const currentWallet = wallet.getCurrentWallet();
      expect(currentWallet).not.toBeNull();
      expect(currentWallet).toHaveProperty('address');
    });

    it('should get wallet address', () => {
      const address = wallet.getAddress();
      expect(address).toMatch(/^0x[a-f0-9]{40}$/i);
    });

    it('should check if wallet exists', async () => {
      const exists = await wallet.hasWallet();
      expect(exists).toBe(true);
    });

    it('should sign a message', async () => {
      const message = 'Test message';
      const signature = await wallet.signMessage(message);

      expect(signature).toBeTruthy();
      expect(typeof signature).toBe('string');
    });
  });

  describe('biometric settings', () => {
    beforeEach(async () => {
      await wallet.initialize();
      await wallet.createWallet(false);
    });

    it('should enable biometric authentication', async () => {
      await wallet.setBiometricEnabled(true);
      const enabled = await wallet.isBiometricEnabled();
      expect(enabled).toBe(true);
    });

    it('should disable biometric authentication', async () => {
      await wallet.setBiometricEnabled(true);
      await wallet.setBiometricEnabled(false);
      const enabled = await wallet.isBiometricEnabled();
      expect(enabled).toBe(false);
    });
  });

  describe('wallet deletion', () => {
    it('should delete wallet successfully', async () => {
      await wallet.initialize();
      await wallet.createWallet(false);

      await wallet.deleteWallet();

      const exists = await wallet.hasWallet();
      expect(exists).toBe(false);

      const currentWallet = wallet.getCurrentWallet();
      expect(currentWallet).toBeNull();
    });
  });
});
