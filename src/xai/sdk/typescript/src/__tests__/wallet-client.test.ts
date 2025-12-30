/**
 * WalletClient Unit Tests
 *
 * Comprehensive tests for wallet operations including:
 * - Wallet creation
 * - Wallet retrieval
 * - Balance queries
 * - Transaction history
 * - Embedded wallet operations
 * - Error handling and validation
 */

import { WalletClient } from '../clients/wallet-client';
import { HTTPClient } from '../utils/http-client';
import { ValidationError, WalletError } from '../errors';
import { WalletType } from '../types';

// Mock HTTPClient
jest.mock('../utils/http-client');

const MockHTTPClient = HTTPClient as jest.MockedClass<typeof HTTPClient>;

describe('WalletClient', () => {
  let walletClient: WalletClient;
  let mockHttpClient: jest.Mocked<HTTPClient>;

  beforeEach(() => {
    jest.clearAllMocks();
    mockHttpClient = new MockHTTPClient({
      baseUrl: 'http://localhost:5000',
    }) as jest.Mocked<HTTPClient>;
    walletClient = new WalletClient(mockHttpClient);
  });

  describe('create', () => {
    it('should create wallet with default parameters', async () => {
      const mockResponse = {
        address: '0x1234567890abcdef',
        public_key: 'pk_test123',
        created_at: '2024-01-01T00:00:00Z',
        wallet_type: 'standard',
        private_key: 'sk_test123',
      };

      mockHttpClient.post = jest.fn().mockResolvedValue(mockResponse);

      const result = await walletClient.create();

      expect(mockHttpClient.post).toHaveBeenCalledWith('/wallet/create', {});
      expect(result).toEqual({
        address: '0x1234567890abcdef',
        publicKey: 'pk_test123',
        createdAt: '2024-01-01T00:00:00Z',
        walletType: 'standard',
        privateKey: 'sk_test123',
      });
    });

    it('should create wallet with custom parameters', async () => {
      const mockResponse = {
        address: '0xabcdef1234567890',
        public_key: 'pk_embedded123',
        created_at: '2024-01-01T00:00:00Z',
        wallet_type: 'embedded',
      };

      mockHttpClient.post = jest.fn().mockResolvedValue(mockResponse);

      const result = await walletClient.create({
        walletType: WalletType.EMBEDDED,
        name: 'My Embedded Wallet',
      });

      expect(mockHttpClient.post).toHaveBeenCalledWith('/wallet/create', {
        wallet_type: WalletType.EMBEDDED,
        name: 'My Embedded Wallet',
      });
      expect(result.walletType).toBe('embedded');
    });

    it('should wrap unknown errors in WalletError', async () => {
      mockHttpClient.post = jest.fn().mockRejectedValue(new Error('Network failure'));

      await expect(walletClient.create()).rejects.toThrow(WalletError);
      await expect(walletClient.create()).rejects.toThrow('Failed to create wallet');
    });

    it('should re-throw WalletError without wrapping', async () => {
      const walletError = new WalletError('Wallet creation denied');
      mockHttpClient.post = jest.fn().mockRejectedValue(walletError);

      await expect(walletClient.create()).rejects.toThrow(walletError);
    });
  });

  describe('get', () => {
    it('should get wallet by address', async () => {
      const mockResponse = {
        address: '0x1234567890abcdef',
        public_key: 'pk_test123',
        created_at: '2024-01-01T00:00:00Z',
        wallet_type: 'standard',
        nonce: 5,
      };

      mockHttpClient.get = jest.fn().mockResolvedValue(mockResponse);

      const result = await walletClient.get('0x1234567890abcdef');

      expect(mockHttpClient.get).toHaveBeenCalledWith('/wallet/0x1234567890abcdef');
      expect(result).toEqual({
        address: '0x1234567890abcdef',
        publicKey: 'pk_test123',
        createdAt: '2024-01-01T00:00:00Z',
        walletType: 'standard',
        nonce: 5,
      });
    });

    it('should throw ValidationError for empty address', async () => {
      await expect(walletClient.get('')).rejects.toThrow(ValidationError);
      await expect(walletClient.get('')).rejects.toThrow('Address is required');
    });

    it('should handle missing nonce with default value', async () => {
      const mockResponse = {
        address: '0x1234567890abcdef',
        public_key: 'pk_test123',
        created_at: '2024-01-01T00:00:00Z',
      };

      mockHttpClient.get = jest.fn().mockResolvedValue(mockResponse);

      const result = await walletClient.get('0x1234567890abcdef');

      expect(result.nonce).toBe(0);
    });

    it('should wrap unknown errors in WalletError', async () => {
      mockHttpClient.get = jest.fn().mockRejectedValue(new Error('Not found'));

      await expect(walletClient.get('0x1234')).rejects.toThrow(WalletError);
      await expect(walletClient.get('0x1234')).rejects.toThrow('Failed to get wallet');
    });
  });

  describe('getBalance', () => {
    it('should get balance for address', async () => {
      const mockResponse = {
        address: '0x1234567890abcdef',
        balance: '1000000000000000000',
        locked_balance: '100000000000000000',
        available_balance: '900000000000000000',
        nonce: 10,
      };

      mockHttpClient.get = jest.fn().mockResolvedValue(mockResponse);

      const result = await walletClient.getBalance('0x1234567890abcdef');

      expect(mockHttpClient.get).toHaveBeenCalledWith('/wallet/0x1234567890abcdef/balance');
      expect(result).toEqual({
        address: '0x1234567890abcdef',
        balance: '1000000000000000000',
        lockedBalance: '100000000000000000',
        availableBalance: '900000000000000000',
        nonce: 10,
      });
    });

    it('should throw ValidationError for empty address', async () => {
      await expect(walletClient.getBalance('')).rejects.toThrow(ValidationError);
      await expect(walletClient.getBalance('')).rejects.toThrow('Address is required');
    });

    it('should handle missing optional fields with defaults', async () => {
      const mockResponse = {
        address: '0x1234567890abcdef',
        balance: '1000000000000000000',
      };

      mockHttpClient.get = jest.fn().mockResolvedValue(mockResponse);

      const result = await walletClient.getBalance('0x1234567890abcdef');

      expect(result.lockedBalance).toBe('0');
      expect(result.availableBalance).toBe('1000000000000000000');
      expect(result.nonce).toBe(0);
    });

    it('should wrap unknown errors in WalletError', async () => {
      mockHttpClient.get = jest.fn().mockRejectedValue(new Error('Network error'));

      await expect(walletClient.getBalance('0x1234')).rejects.toThrow(WalletError);
      await expect(walletClient.getBalance('0x1234')).rejects.toThrow('Failed to get balance');
    });
  });

  describe('getTransactions', () => {
    it('should get transactions with default pagination', async () => {
      const mockResponse = {
        transactions: [
          { hash: 'tx1', from: '0x1234', to: '0x5678', amount: '100' },
          { hash: 'tx2', from: '0x1234', to: '0x9abc', amount: '200' },
        ],
        total: 2,
        limit: 50,
        offset: 0,
      };

      mockHttpClient.get = jest.fn().mockResolvedValue(mockResponse);

      const result = await walletClient.getTransactions({ address: '0x1234' });

      expect(mockHttpClient.get).toHaveBeenCalledWith('/wallet/0x1234/transactions', {
        limit: 50,
        offset: 0,
      });
      expect(result.data).toHaveLength(2);
      expect(result.total).toBe(2);
    });

    it('should get transactions with custom pagination', async () => {
      const mockResponse = {
        transactions: [],
        total: 100,
        limit: 20,
        offset: 40,
      };

      mockHttpClient.get = jest.fn().mockResolvedValue(mockResponse);

      const result = await walletClient.getTransactions({
        address: '0x1234',
        limit: 20,
        offset: 40,
      });

      expect(mockHttpClient.get).toHaveBeenCalledWith('/wallet/0x1234/transactions', {
        limit: 20,
        offset: 40,
      });
      expect(result.offset).toBe(40);
    });

    it('should cap limit at 100', async () => {
      const mockResponse = {
        transactions: [],
        total: 0,
        limit: 100,
        offset: 0,
      };

      mockHttpClient.get = jest.fn().mockResolvedValue(mockResponse);

      await walletClient.getTransactions({
        address: '0x1234',
        limit: 500, // Should be capped to 100
      });

      expect(mockHttpClient.get).toHaveBeenCalledWith('/wallet/0x1234/transactions', {
        limit: 100,
        offset: 0,
      });
    });

    it('should throw ValidationError for missing address', async () => {
      await expect(walletClient.getTransactions({ address: '' })).rejects.toThrow(ValidationError);
      await expect(walletClient.getTransactions({ address: '' })).rejects.toThrow(
        'Address is required'
      );
    });

    it('should handle empty response', async () => {
      const mockResponse = {
        transactions: null,
        total: 0,
      };

      mockHttpClient.get = jest.fn().mockResolvedValue(mockResponse);

      const result = await walletClient.getTransactions({ address: '0x1234' });

      expect(result.data).toEqual([]);
      expect(result.total).toBe(0);
    });

    it('should wrap unknown errors in WalletError', async () => {
      mockHttpClient.get = jest.fn().mockRejectedValue(new Error('Database error'));

      await expect(walletClient.getTransactions({ address: '0x1234' })).rejects.toThrow(WalletError);
      await expect(walletClient.getTransactions({ address: '0x1234' })).rejects.toThrow(
        'Failed to get transactions'
      );
    });
  });

  describe('createEmbedded', () => {
    it('should create embedded wallet', async () => {
      const mockResponse = {
        wallet_id: 'embed_123',
        address: '0xabcdef',
        status: 'active',
      };

      mockHttpClient.post = jest.fn().mockResolvedValue(mockResponse);

      const result = await walletClient.createEmbedded({
        appId: 'my-app',
        userId: 'user-123',
        metadata: { email: 'test@example.com' },
      });

      expect(mockHttpClient.post).toHaveBeenCalledWith('/wallet/embedded/create', {
        app_id: 'my-app',
        user_id: 'user-123',
        metadata: { email: 'test@example.com' },
      });
      expect(result).toEqual(mockResponse);
    });

    it('should create embedded wallet without metadata', async () => {
      const mockResponse = { wallet_id: 'embed_123' };

      mockHttpClient.post = jest.fn().mockResolvedValue(mockResponse);

      await walletClient.createEmbedded({
        appId: 'my-app',
        userId: 'user-123',
      });

      expect(mockHttpClient.post).toHaveBeenCalledWith('/wallet/embedded/create', {
        app_id: 'my-app',
        user_id: 'user-123',
      });
    });

    it('should throw ValidationError for missing appId', async () => {
      await expect(
        walletClient.createEmbedded({ appId: '', userId: 'user-123' })
      ).rejects.toThrow(ValidationError);
      await expect(
        walletClient.createEmbedded({ appId: '', userId: 'user-123' })
      ).rejects.toThrow('appId and userId are required');
    });

    it('should throw ValidationError for missing userId', async () => {
      await expect(
        walletClient.createEmbedded({ appId: 'my-app', userId: '' })
      ).rejects.toThrow(ValidationError);
    });

    it('should wrap unknown errors in WalletError', async () => {
      mockHttpClient.post = jest.fn().mockRejectedValue(new Error('Server error'));

      await expect(
        walletClient.createEmbedded({ appId: 'my-app', userId: 'user-123' })
      ).rejects.toThrow(WalletError);
      await expect(
        walletClient.createEmbedded({ appId: 'my-app', userId: 'user-123' })
      ).rejects.toThrow('Failed to create embedded wallet');
    });
  });

  describe('loginEmbedded', () => {
    it('should login to embedded wallet', async () => {
      const mockResponse = {
        session_token: 'sess_abc123',
        expires_at: '2024-01-02T00:00:00Z',
      };

      mockHttpClient.post = jest.fn().mockResolvedValue(mockResponse);

      const result = await walletClient.loginEmbedded({
        walletId: 'wallet-123',
        password: 'secure-password',
      });

      expect(mockHttpClient.post).toHaveBeenCalledWith('/wallet/embedded/login', {
        wallet_id: 'wallet-123',
        password: 'secure-password',
      });
      expect(result).toEqual(mockResponse);
    });

    it('should throw ValidationError for missing walletId', async () => {
      await expect(
        walletClient.loginEmbedded({ walletId: '', password: 'password' })
      ).rejects.toThrow(ValidationError);
      await expect(
        walletClient.loginEmbedded({ walletId: '', password: 'password' })
      ).rejects.toThrow('walletId and password are required');
    });

    it('should throw ValidationError for missing password', async () => {
      await expect(
        walletClient.loginEmbedded({ walletId: 'wallet-123', password: '' })
      ).rejects.toThrow(ValidationError);
    });

    it('should wrap unknown errors in WalletError', async () => {
      mockHttpClient.post = jest.fn().mockRejectedValue(new Error('Auth failed'));

      await expect(
        walletClient.loginEmbedded({ walletId: 'wallet-123', password: 'password' })
      ).rejects.toThrow(WalletError);
      await expect(
        walletClient.loginEmbedded({ walletId: 'wallet-123', password: 'password' })
      ).rejects.toThrow('Failed to login to embedded wallet');
    });
  });
});
