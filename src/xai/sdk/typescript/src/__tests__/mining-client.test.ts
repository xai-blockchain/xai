/**
 * MiningClient Unit Tests
 *
 * Comprehensive tests for mining operations including:
 * - Starting and stopping mining
 * - Mining status queries
 * - Reward information
 * - Difficulty and hashrate queries
 * - Error handling and validation
 */

import { MiningClient } from '../clients/mining-client';
import { HTTPClient } from '../utils/http-client';
import { ValidationError, MiningError } from '../errors';

// Mock HTTPClient
jest.mock('../utils/http-client');

const MockHTTPClient = HTTPClient as jest.MockedClass<typeof HTTPClient>;

describe('MiningClient', () => {
  let miningClient: MiningClient;
  let mockHttpClient: jest.Mocked<HTTPClient>;

  beforeEach(() => {
    jest.clearAllMocks();
    mockHttpClient = new MockHTTPClient({
      baseUrl: 'http://localhost:5000',
    }) as jest.Mocked<HTTPClient>;
    miningClient = new MiningClient(mockHttpClient);
  });

  describe('start', () => {
    it('should start mining with default threads', async () => {
      const mockResponse = {
        status: 'started',
        threads: 1,
      };

      mockHttpClient.post = jest.fn().mockResolvedValue(mockResponse);

      const result = await miningClient.start();

      expect(mockHttpClient.post).toHaveBeenCalledWith('/mining/start', { threads: 1 });
      expect(result).toEqual(mockResponse);
    });

    it('should start mining with custom threads', async () => {
      const mockResponse = {
        status: 'started',
        threads: 8,
      };

      mockHttpClient.post = jest.fn().mockResolvedValue(mockResponse);

      const result = await miningClient.start(8);

      expect(mockHttpClient.post).toHaveBeenCalledWith('/mining/start', { threads: 8 });
      expect(result.threads).toBe(8);
    });

    it('should throw ValidationError for threads below 1', async () => {
      await expect(miningClient.start(0)).rejects.toThrow(ValidationError);
      await expect(miningClient.start(0)).rejects.toThrow('threads must be between 1 and 16');

      await expect(miningClient.start(-1)).rejects.toThrow(ValidationError);
    });

    it('should throw ValidationError for threads above 16', async () => {
      await expect(miningClient.start(17)).rejects.toThrow(ValidationError);
      await expect(miningClient.start(17)).rejects.toThrow('threads must be between 1 and 16');

      await expect(miningClient.start(100)).rejects.toThrow(ValidationError);
    });

    it('should accept boundary values 1 and 16', async () => {
      mockHttpClient.post = jest.fn().mockResolvedValue({ status: 'started' });

      await expect(miningClient.start(1)).resolves.toBeDefined();
      await expect(miningClient.start(16)).resolves.toBeDefined();
    });

    it('should wrap unknown errors in MiningError', async () => {
      mockHttpClient.post = jest.fn().mockRejectedValue(new Error('Hardware failure'));

      await expect(miningClient.start(4)).rejects.toThrow(MiningError);
      await expect(miningClient.start(4)).rejects.toThrow('Failed to start mining');
    });

    it('should re-throw MiningError without wrapping', async () => {
      const miningError = new MiningError('Mining already in progress');
      mockHttpClient.post = jest.fn().mockRejectedValue(miningError);

      await expect(miningClient.start(4)).rejects.toThrow(miningError);
    });
  });

  describe('stop', () => {
    it('should stop mining', async () => {
      const mockResponse = {
        status: 'stopped',
        blocks_found: 5,
      };

      mockHttpClient.post = jest.fn().mockResolvedValue(mockResponse);

      const result = await miningClient.stop();

      expect(mockHttpClient.post).toHaveBeenCalledWith('/mining/stop', {});
      expect(result).toEqual(mockResponse);
    });

    it('should wrap unknown errors in MiningError', async () => {
      mockHttpClient.post = jest.fn().mockRejectedValue(new Error('Cannot stop'));

      await expect(miningClient.stop()).rejects.toThrow(MiningError);
      await expect(miningClient.stop()).rejects.toThrow('Failed to stop mining');
    });

    it('should re-throw MiningError without wrapping', async () => {
      const miningError = new MiningError('Mining not running');
      mockHttpClient.post = jest.fn().mockRejectedValue(miningError);

      await expect(miningClient.stop()).rejects.toThrow(miningError);
    });
  });

  describe('getStatus', () => {
    it('should get mining status when active', async () => {
      const mockResponse = {
        mining: true,
        threads: 4,
        hashrate: '1.5 GH/s',
        blocks_found: 10,
        current_difficulty: '12345678',
        uptime: 3600,
        last_block_time: 1704067200,
      };

      mockHttpClient.get = jest.fn().mockResolvedValue(mockResponse);

      const result = await miningClient.getStatus();

      expect(mockHttpClient.get).toHaveBeenCalledWith('/mining/status');
      expect(result).toEqual({
        mining: true,
        threads: 4,
        hashrate: '1.5 GH/s',
        blocksFound: 10,
        currentDifficulty: '12345678',
        uptime: 3600,
        lastBlockTime: 1704067200,
      });
    });

    it('should get mining status when inactive', async () => {
      const mockResponse = {
        mining: false,
        threads: 0,
        hashrate: '0 H/s',
        current_difficulty: '12345678',
      };

      mockHttpClient.get = jest.fn().mockResolvedValue(mockResponse);

      const result = await miningClient.getStatus();

      expect(result.mining).toBe(false);
      expect(result.blocksFound).toBe(0);
      expect(result.uptime).toBe(0);
      expect(result.lastBlockTime).toBeUndefined();
    });

    it('should handle missing optional fields', async () => {
      const mockResponse = {
        mining: false,
        threads: 0,
        hashrate: '0 H/s',
        current_difficulty: '1000',
      };

      mockHttpClient.get = jest.fn().mockResolvedValue(mockResponse);

      const result = await miningClient.getStatus();

      expect(result.blocksFound).toBe(0);
      expect(result.uptime).toBe(0);
    });

    it('should wrap unknown errors in MiningError', async () => {
      mockHttpClient.get = jest.fn().mockRejectedValue(new Error('Connection refused'));

      await expect(miningClient.getStatus()).rejects.toThrow(MiningError);
      await expect(miningClient.getStatus()).rejects.toThrow('Failed to get mining status');
    });
  });

  describe('getRewards', () => {
    it('should get mining rewards for address', async () => {
      const mockResponse = {
        address: '0xminer123',
        total_rewards: '1000000000000000000',
        pending_rewards: '100000000000000000',
        claimed_rewards: '900000000000000000',
        blocks_found: 50,
      };

      mockHttpClient.get = jest.fn().mockResolvedValue(mockResponse);

      const result = await miningClient.getRewards('0xminer123');

      expect(mockHttpClient.get).toHaveBeenCalledWith('/mining/rewards', { address: '0xminer123' });
      expect(result).toEqual({
        address: '0xminer123',
        totalRewards: '1000000000000000000',
        pendingRewards: '100000000000000000',
        claimedRewards: '900000000000000000',
        blocksFound: 50,
      });
    });

    it('should throw ValidationError for empty address', async () => {
      await expect(miningClient.getRewards('')).rejects.toThrow(ValidationError);
      await expect(miningClient.getRewards('')).rejects.toThrow('address is required');
    });

    it('should handle address with no rewards', async () => {
      const mockResponse = {
        address: '0xnewminer',
        total_rewards: '0',
        pending_rewards: '0',
        claimed_rewards: '0',
      };

      mockHttpClient.get = jest.fn().mockResolvedValue(mockResponse);

      const result = await miningClient.getRewards('0xnewminer');

      expect(result.totalRewards).toBe('0');
      expect(result.blocksFound).toBeUndefined();
    });

    it('should wrap unknown errors in MiningError', async () => {
      mockHttpClient.get = jest.fn().mockRejectedValue(new Error('Database error'));

      await expect(miningClient.getRewards('0xminer')).rejects.toThrow(MiningError);
      await expect(miningClient.getRewards('0xminer')).rejects.toThrow(
        'Failed to get mining rewards'
      );
    });
  });

  describe('isMining', () => {
    it('should return true when mining is active', async () => {
      mockHttpClient.get = jest.fn().mockResolvedValue({
        mining: true,
        threads: 4,
        hashrate: '1 GH/s',
        current_difficulty: '1000',
      });

      const result = await miningClient.isMining();

      expect(result).toBe(true);
    });

    it('should return false when mining is inactive', async () => {
      mockHttpClient.get = jest.fn().mockResolvedValue({
        mining: false,
        threads: 0,
        hashrate: '0 H/s',
        current_difficulty: '1000',
      });

      const result = await miningClient.isMining();

      expect(result).toBe(false);
    });

    it('should wrap unknown errors in MiningError', async () => {
      mockHttpClient.get = jest.fn().mockRejectedValue(new Error('Network error'));

      await expect(miningClient.isMining()).rejects.toThrow(MiningError);
      await expect(miningClient.isMining()).rejects.toThrow('Failed to get mining status');
    });
  });

  describe('getDifficulty', () => {
    it('should get current mining difficulty', async () => {
      mockHttpClient.get = jest.fn().mockResolvedValue({
        mining: true,
        threads: 4,
        hashrate: '1 GH/s',
        current_difficulty: '9876543210',
      });

      const result = await miningClient.getDifficulty();

      expect(result).toBe('9876543210');
    });

    it('should wrap unknown errors in MiningError', async () => {
      mockHttpClient.get = jest.fn().mockRejectedValue(new Error('Timeout'));

      await expect(miningClient.getDifficulty()).rejects.toThrow(MiningError);
      await expect(miningClient.getDifficulty()).rejects.toThrow('Failed to get mining status');
    });
  });

  describe('getHashrate', () => {
    it('should get current hashrate', async () => {
      mockHttpClient.get = jest.fn().mockResolvedValue({
        mining: true,
        threads: 8,
        hashrate: '2.5 GH/s',
        current_difficulty: '1000',
      });

      const result = await miningClient.getHashrate();

      expect(result).toBe('2.5 GH/s');
    });

    it('should return zero hashrate when not mining', async () => {
      mockHttpClient.get = jest.fn().mockResolvedValue({
        mining: false,
        threads: 0,
        hashrate: '0 H/s',
        current_difficulty: '1000',
      });

      const result = await miningClient.getHashrate();

      expect(result).toBe('0 H/s');
    });

    it('should wrap unknown errors in MiningError', async () => {
      mockHttpClient.get = jest.fn().mockRejectedValue(new Error('Service unavailable'));

      await expect(miningClient.getHashrate()).rejects.toThrow(MiningError);
      await expect(miningClient.getHashrate()).rejects.toThrow('Failed to get mining status');
    });
  });
});
