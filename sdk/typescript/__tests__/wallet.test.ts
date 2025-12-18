/**
 * Wallet Tests
 */

import { Wallet } from '../src/clients/wallet-client';
import { validateAddress } from '../src/utils/crypto';

describe('Wallet', () => {
  describe('create', () => {
    it('should create a new wallet with valid keys', () => {
      const wallet = Wallet.create();
      
      expect(wallet.address).toBeDefined();
      expect(wallet.publicKey).toBeDefined();
      expect(wallet.address.startsWith('XAI')).toBe(true);
      expect(wallet.publicKey.length).toBeGreaterThan(0);
    });

    it('should create different wallets on each call', () => {
      const wallet1 = Wallet.create();
      const wallet2 = Wallet.create();
      
      expect(wallet1.address).not.toBe(wallet2.address);
      expect(wallet1.publicKey).not.toBe(wallet2.publicKey);
    });
  });

  describe('fromPrivateKey', () => {
    it('should import wallet from private key', () => {
      const wallet1 = Wallet.create();
      const privateKey = wallet1.getPrivateKey();
      
      const wallet2 = Wallet.fromPrivateKey(privateKey);
      
      expect(wallet2.address).toBe(wallet1.address);
      expect(wallet2.publicKey).toBe(wallet1.publicKey);
    });

    it('should throw on invalid private key', () => {
      expect(() => Wallet.fromPrivateKey('invalid')).toThrow();
    });
  });

  describe('fromMnemonic', () => {
    it('should generate mnemonic and import wallet', async () => {
      const mnemonic = Wallet.generateMnemonic();
      
      expect(mnemonic.split(' ').length).toBeGreaterThanOrEqual(12);
      
      const wallet = await Wallet.fromMnemonic(mnemonic);
      
      expect(wallet.address).toBeDefined();
      expect(validateAddress(wallet.address)).toBe(true);
    });

    it('should derive same wallet from same mnemonic and index', async () => {
      const mnemonic = Wallet.generateMnemonic();
      
      const wallet1 = await Wallet.fromMnemonic(mnemonic, 0);
      const wallet2 = await Wallet.fromMnemonic(mnemonic, 0);
      
      expect(wallet1.address).toBe(wallet2.address);
    });

    it('should derive different wallets for different indices', async () => {
      const mnemonic = Wallet.generateMnemonic();
      
      const wallet1 = await Wallet.fromMnemonic(mnemonic, 0);
      const wallet2 = await Wallet.fromMnemonic(mnemonic, 1);
      
      expect(wallet1.address).not.toBe(wallet2.address);
    });
  });

  describe('sign', () => {
    it('should sign messages', async () => {
      const wallet = Wallet.create();
      const message = 'Hello XAI';
      
      const signature = await wallet.sign(message);
      
      expect(signature).toBeDefined();
      expect(signature.length).toBeGreaterThan(0);
    });

    it('should produce consistent signatures', async () => {
      const wallet = Wallet.create();
      const message = 'Test message';
      
      const sig1 = await wallet.sign(message);
      const sig2 = await wallet.sign(message);
      
      expect(sig1).toBe(sig2);
    });
  });

  describe('export', () => {
    it('should export wallet without private key by default', () => {
      const wallet = Wallet.create();
      const exported = wallet.export();
      
      expect(exported.address).toBe(wallet.address);
      expect(exported.public_key).toBe(wallet.publicKey);
      expect(exported.private_key).toBeUndefined();
    });

    it('should export wallet with private key when requested', () => {
      const wallet = Wallet.create();
      const exported = wallet.export(true);
      
      expect(exported.address).toBe(wallet.address);
      expect(exported.public_key).toBe(wallet.publicKey);
      expect(exported.private_key).toBe(wallet.getPrivateKey());
    });
  });
});
