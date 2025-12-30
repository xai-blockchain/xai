/**
 * BlockchainClient Unit Tests
 *
 * Comprehensive tests for blockchain operations including:
 * - Block retrieval by number
 * - Block listing with pagination
 * - Block transactions
 * - Sync status
 * - Blockchain statistics
 * - Node info and health
 * - Error handling
 */

import { BlockchainClient } from '../clients/blockchain-client';
import { HTTPClient } from '../utils/http-client';
import { ValidationError, XAIError } from '../errors';

// Mock HTTPClient
jest.mock('../utils/http-client');

const MockHTTPClient = HTTPClient as jest.MockedClass<typeof HTTPClient>;

describe('BlockchainClient', () => {
  let blockchainClient: BlockchainClient;
  let mockHttpClient: jest.Mocked<HTTPClient>;

  beforeEach(() => {
    jest.clearAllMocks();
    mockHttpClient = new MockHTTPClient({
      baseUrl: 'http://localhost:5000',
    }) as jest.Mocked<HTTPClient>;
    blockchainClient = new BlockchainClient(mockHttpClient);
  });

  describe('getBlock', () => {
    it('should get block by number', async () => {
      const mockResponse = {
        number: 1000,
        hash: '0xabcdef123456',
        parent_hash: '0x123456abcdef',
        timestamp: 1704067200,
        miner: '0xminer123',
        difficulty: '1000000',
        gas_limit: '8000000',
        gas_used: '1500000',
        transaction_count: 5,
        transactions: ['0xtx1', '0xtx2', '0xtx3', '0xtx4', '0xtx5'],
      };

      mockHttpClient.get = jest.fn().mockResolvedValue(mockResponse);

      const result = await blockchainClient.getBlock(1000);

      expect(mockHttpClient.get).toHaveBeenCalledWith('/blockchain/blocks/1000');
      expect(result).toEqual({
        number: 1000,
        hash: '0xabcdef123456',
        parentHash: '0x123456abcdef',
        timestamp: 1704067200,
        miner: '0xminer123',
        difficulty: '1000000',
        gasLimit: '8000000',
        gasUsed: '1500000',
        transactions: 5,
        transactionHashes: ['0xtx1', '0xtx2', '0xtx3', '0xtx4', '0xtx5'],
      });
    });

    it('should handle block with missing optional fields', async () => {
      const mockResponse = {
        number: 0,
        hash: '0xgenesis',
        parent_hash: '0x0000000000000000',
        timestamp: 1704000000,
        miner: '0x0000000000000000',
        difficulty: '1',
      };

      mockHttpClient.get = jest.fn().mockResolvedValue(mockResponse);

      const result = await blockchainClient.getBlock(0);

      expect(result.gasLimit).toBe('0');
      expect(result.gasUsed).toBe('0');
      expect(result.transactions).toBe(0);
      expect(result.transactionHashes).toEqual([]);
    });

    it('should throw ValidationError for negative block number', async () => {
      await expect(blockchainClient.getBlock(-1)).rejects.toThrow(ValidationError);
      await expect(blockchainClient.getBlock(-1)).rejects.toThrow(
        'blockNumber must be non-negative'
      );
    });

    it('should wrap unknown errors in XAIError', async () => {
      mockHttpClient.get = jest.fn().mockRejectedValue(new Error('Network error'));

      await expect(blockchainClient.getBlock(1000)).rejects.toThrow(XAIError);
      await expect(blockchainClient.getBlock(1000)).rejects.toThrow('Failed to get block');
    });

    it('should re-throw XAIError without wrapping', async () => {
      const xaiError = new XAIError('Block not found', 404);
      mockHttpClient.get = jest.fn().mockRejectedValue(xaiError);

      await expect(blockchainClient.getBlock(999999)).rejects.toThrow(xaiError);
    });
  });

  describe('listBlocks', () => {
    it('should list blocks with default pagination', async () => {
      const mockResponse = {
        blocks: [
          {
            number: 1000,
            hash: '0xblock1000',
            parent_hash: '0xblock999',
            timestamp: 1704067200,
            miner: '0xminer',
            difficulty: '1000000',
            transaction_count: 10,
          },
          {
            number: 999,
            hash: '0xblock999',
            parent_hash: '0xblock998',
            timestamp: 1704067100,
            miner: '0xminer',
            difficulty: '1000000',
            transaction_count: 5,
          },
        ],
        total: 1000,
        limit: 20,
        offset: 0,
      };

      mockHttpClient.get = jest.fn().mockResolvedValue(mockResponse);

      const result = await blockchainClient.listBlocks();

      expect(mockHttpClient.get).toHaveBeenCalledWith('/blockchain/blocks', {
        limit: 20,
        offset: 0,
      });
      expect(result.data).toHaveLength(2);
      expect(result.total).toBe(1000);
      expect(result.data[0].number).toBe(1000);
    });

    it('should list blocks with custom pagination', async () => {
      const mockResponse = {
        blocks: [],
        total: 1000,
        limit: 50,
        offset: 100,
      };

      mockHttpClient.get = jest.fn().mockResolvedValue(mockResponse);

      const result = await blockchainClient.listBlocks({ limit: 50, offset: 100 });

      expect(mockHttpClient.get).toHaveBeenCalledWith('/blockchain/blocks', {
        limit: 50,
        offset: 100,
      });
      expect(result.limit).toBe(50);
      expect(result.offset).toBe(100);
    });

    it('should cap limit at 100', async () => {
      const mockResponse = {
        blocks: [],
        total: 0,
        limit: 100,
        offset: 0,
      };

      mockHttpClient.get = jest.fn().mockResolvedValue(mockResponse);

      await blockchainClient.listBlocks({ limit: 500 });

      expect(mockHttpClient.get).toHaveBeenCalledWith('/blockchain/blocks', {
        limit: 100,
        offset: 0,
      });
    });

    it('should handle empty blocks array', async () => {
      const mockResponse = {
        blocks: null,
        total: 0,
      };

      mockHttpClient.get = jest.fn().mockResolvedValue(mockResponse);

      const result = await blockchainClient.listBlocks();

      expect(result.data).toEqual([]);
      expect(result.total).toBe(0);
    });

    it('should transform block fields correctly', async () => {
      const mockResponse = {
        blocks: [
          {
            number: 100,
            hash: '0xhash',
            parent_hash: '0xparent',
            timestamp: 1704000000,
            miner: '0xminer',
          },
        ],
        total: 1,
        limit: 20,
        offset: 0,
      };

      mockHttpClient.get = jest.fn().mockResolvedValue(mockResponse);

      const result = await blockchainClient.listBlocks();

      expect(result.data[0]).toEqual({
        number: 100,
        hash: '0xhash',
        parentHash: '0xparent',
        timestamp: 1704000000,
        miner: '0xminer',
        difficulty: '0',
        gasLimit: '0',
        gasUsed: '0',
        transactions: 0,
      });
    });

    it('should wrap unknown errors in XAIError', async () => {
      mockHttpClient.get = jest.fn().mockRejectedValue(new Error('Database error'));

      await expect(blockchainClient.listBlocks()).rejects.toThrow(XAIError);
      await expect(blockchainClient.listBlocks()).rejects.toThrow('Failed to list blocks');
    });
  });

  describe('getBlockTransactions', () => {
    it('should get transactions for block', async () => {
      const mockResponse = {
        transactions: [
          { hash: '0xtx1', from: '0xa', to: '0xb', amount: '100' },
          { hash: '0xtx2', from: '0xc', to: '0xd', amount: '200' },
        ],
      };

      mockHttpClient.get = jest.fn().mockResolvedValue(mockResponse);

      const result = await blockchainClient.getBlockTransactions(1000);

      expect(mockHttpClient.get).toHaveBeenCalledWith('/blockchain/blocks/1000/transactions');
      expect(result).toHaveLength(2);
      expect(result[0].hash).toBe('0xtx1');
    });

    it('should throw ValidationError for negative block number', async () => {
      await expect(blockchainClient.getBlockTransactions(-5)).rejects.toThrow(ValidationError);
      await expect(blockchainClient.getBlockTransactions(-5)).rejects.toThrow(
        'blockNumber must be non-negative'
      );
    });

    it('should handle empty transactions', async () => {
      const mockResponse = {
        transactions: null,
      };

      mockHttpClient.get = jest.fn().mockResolvedValue(mockResponse);

      const result = await blockchainClient.getBlockTransactions(0);

      expect(result).toEqual([]);
    });

    it('should wrap unknown errors in XAIError', async () => {
      mockHttpClient.get = jest.fn().mockRejectedValue(new Error('Not found'));

      await expect(blockchainClient.getBlockTransactions(1000)).rejects.toThrow(XAIError);
      await expect(blockchainClient.getBlockTransactions(1000)).rejects.toThrow(
        'Failed to get block transactions'
      );
    });
  });

  describe('getSyncStatus', () => {
    it('should get sync status when syncing', async () => {
      const mockResponse = {
        syncing: true,
        current_block: 500,
        highest_block: 1000,
        starting_block: 0,
      };

      mockHttpClient.get = jest.fn().mockResolvedValue(mockResponse);

      const result = await blockchainClient.getSyncStatus();

      expect(mockHttpClient.get).toHaveBeenCalledWith('/blockchain/sync');
      expect(result).toEqual({
        syncing: true,
        currentBlock: 500,
        highestBlock: 1000,
        startingBlock: 0,
        syncProgress: 50,
      });
    });

    it('should get sync status when synced', async () => {
      const mockResponse = {
        syncing: false,
        current_block: 1000,
        highest_block: 1000,
      };

      mockHttpClient.get = jest.fn().mockResolvedValue(mockResponse);

      const result = await blockchainClient.getSyncStatus();

      expect(result.syncing).toBe(false);
      expect(result.syncProgress).toBe(100);
    });

    it('should handle missing sync progress data', async () => {
      const mockResponse = {
        syncing: false,
      };

      mockHttpClient.get = jest.fn().mockResolvedValue(mockResponse);

      const result = await blockchainClient.getSyncStatus();

      expect(result.syncProgress).toBeUndefined();
    });

    it('should wrap unknown errors in XAIError', async () => {
      mockHttpClient.get = jest.fn().mockRejectedValue(new Error('Connection failed'));

      await expect(blockchainClient.getSyncStatus()).rejects.toThrow(XAIError);
      await expect(blockchainClient.getSyncStatus()).rejects.toThrow('Failed to get sync status');
    });
  });

  describe('isSynced', () => {
    it('should return true when not syncing', async () => {
      const mockResponse = { syncing: false };
      mockHttpClient.get = jest.fn().mockResolvedValue(mockResponse);

      const result = await blockchainClient.isSynced();

      expect(result).toBe(true);
    });

    it('should return false when syncing', async () => {
      const mockResponse = { syncing: true, current_block: 500, highest_block: 1000 };
      mockHttpClient.get = jest.fn().mockResolvedValue(mockResponse);

      const result = await blockchainClient.isSynced();

      expect(result).toBe(false);
    });

    it('should wrap unknown errors in XAIError', async () => {
      mockHttpClient.get = jest.fn().mockRejectedValue(new Error('Network error'));

      await expect(blockchainClient.isSynced()).rejects.toThrow(XAIError);
      // Error message comes from getSyncStatus which isSynced calls
      await expect(blockchainClient.isSynced()).rejects.toThrow('Failed to get sync status');
    });
  });

  describe('getStats', () => {
    it('should get blockchain statistics', async () => {
      const mockResponse = {
        total_blocks: 10000,
        total_transactions: 500000,
        total_accounts: 1500,
        difficulty: '5000000',
        hashrate: '1000 GH/s',
        average_block_time: 15,
        total_supply: '21000000000000000000000000',
        network: 'mainnet',
      };

      mockHttpClient.get = jest.fn().mockResolvedValue(mockResponse);

      const result = await blockchainClient.getStats();

      expect(mockHttpClient.get).toHaveBeenCalledWith('/stats');
      expect(result).toEqual({
        totalBlocks: 10000,
        totalTransactions: 500000,
        totalAccounts: 1500,
        difficulty: '5000000',
        hashrate: '1000 GH/s',
        averageBlockTime: 15,
        totalSupply: '21000000000000000000000000',
        network: 'mainnet',
      });
    });

    it('should handle missing optional fields', async () => {
      const mockResponse = {
        total_blocks: 100,
        total_transactions: 1000,
        total_accounts: 50,
        difficulty: '1000',
        hashrate: '100 MH/s',
        total_supply: '1000000',
      };

      mockHttpClient.get = jest.fn().mockResolvedValue(mockResponse);

      const result = await blockchainClient.getStats();

      expect(result.averageBlockTime).toBe(0);
      expect(result.network).toBe('mainnet');
    });

    it('should wrap unknown errors in XAIError', async () => {
      mockHttpClient.get = jest.fn().mockRejectedValue(new Error('Service unavailable'));

      await expect(blockchainClient.getStats()).rejects.toThrow(XAIError);
      await expect(blockchainClient.getStats()).rejects.toThrow('Failed to get blockchain stats');
    });
  });

  describe('getNodeInfo', () => {
    it('should get node information', async () => {
      const mockResponse = {
        status: 'running',
        node: 'xai-node-v1',
        version: '1.0.0',
        algorithmicFeatures: true,
        endpoints: ['/wallet', '/transaction', '/blockchain'],
      };

      mockHttpClient.get = jest.fn().mockResolvedValue(mockResponse);

      const result = await blockchainClient.getNodeInfo();

      expect(mockHttpClient.get).toHaveBeenCalledWith('/');
      expect(result).toEqual(mockResponse);
    });

    it('should wrap unknown errors in XAIError', async () => {
      mockHttpClient.get = jest.fn().mockRejectedValue(new Error('Connection refused'));

      await expect(blockchainClient.getNodeInfo()).rejects.toThrow(XAIError);
      await expect(blockchainClient.getNodeInfo()).rejects.toThrow('Failed to get node info');
    });
  });

  describe('getHealth', () => {
    it('should get health check response', async () => {
      const mockResponse = {
        status: 'healthy',
        timestamp: 1704067200,
        blockchain: { synced: true },
        services: { database: 'ok', cache: 'ok' },
      };

      mockHttpClient.get = jest.fn().mockResolvedValue(mockResponse);

      const result = await blockchainClient.getHealth();

      expect(mockHttpClient.get).toHaveBeenCalledWith('/health');
      expect(result).toEqual(mockResponse);
    });

    it('should handle unhealthy status', async () => {
      const mockResponse = {
        status: 'unhealthy',
        timestamp: 1704067200,
        error: 'Database connection failed',
      };

      mockHttpClient.get = jest.fn().mockResolvedValue(mockResponse);

      const result = await blockchainClient.getHealth();

      expect(result.status).toBe('unhealthy');
      expect(result.error).toBe('Database connection failed');
    });

    it('should wrap unknown errors in XAIError', async () => {
      mockHttpClient.get = jest.fn().mockRejectedValue(new Error('Timeout'));

      await expect(blockchainClient.getHealth()).rejects.toThrow(XAIError);
      await expect(blockchainClient.getHealth()).rejects.toThrow('Failed to check node health');
    });
  });
});
