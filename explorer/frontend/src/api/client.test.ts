import { describe, it, expect, vi, beforeAll, afterAll, afterEach } from 'vitest';
import { server } from '../__tests__/mocks/server';
import {
  getBlocks,
  getBlock,
  getTransactions,
  getTransaction,
  getAddress,
  search,
  getNetworkStats,
  getAITasks,
  getAITask,
  getAIModels,
  getAIStats,
} from './client';

// Start server before all tests
beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));

// Reset handlers after each test
afterEach(() => server.resetHandlers());

// Close server after all tests
afterAll(() => server.close());

describe('API Client', () => {
  describe('getBlocks', () => {
    it('fetches blocks with default pagination', async () => {
      const result = await getBlocks();

      expect(result).toHaveProperty('blocks');
      expect(result).toHaveProperty('total');
      expect(Array.isArray(result.blocks)).toBe(true);
    });

    it('fetches blocks with custom pagination', async () => {
      const result = await getBlocks(2, 10);

      expect(result).toHaveProperty('blocks');
      expect(result).toHaveProperty('total');
    });
  });

  describe('getBlock', () => {
    it('fetches a single block by ID', async () => {
      const result = await getBlock('12345');

      expect(result).toHaveProperty('height');
      expect(result).toHaveProperty('hash');
      expect(result).toHaveProperty('timestamp');
    });

    it('throws error for non-existent block', async () => {
      await expect(getBlock('notfound')).rejects.toThrow();
    });
  });

  describe('getTransactions', () => {
    it('fetches transactions with default pagination', async () => {
      const result = await getTransactions();

      expect(result).toHaveProperty('transactions');
      expect(result).toHaveProperty('total');
      expect(Array.isArray(result.transactions)).toBe(true);
    });
  });

  describe('getTransaction', () => {
    it('fetches a single transaction by ID', async () => {
      const result = await getTransaction('tx123456');

      expect(result).toHaveProperty('txid');
    });

    it('throws error for non-existent transaction', async () => {
      await expect(getTransaction('notfound')).rejects.toThrow();
    });
  });

  describe('getAddress', () => {
    it('fetches address details', async () => {
      const result = await getAddress('XAIaddress123');

      expect(result).toHaveProperty('address');
      expect(result).toHaveProperty('balance');
      expect(result).toHaveProperty('totalReceived');
      expect(result).toHaveProperty('totalSent');
      expect(result).toHaveProperty('transactionCount');
    });

    it('throws error for non-existent address', async () => {
      await expect(getAddress('notfound')).rejects.toThrow();
    });
  });

  describe('search', () => {
    it('returns search results', async () => {
      const results = await search('test query');

      expect(Array.isArray(results)).toBe(true);
      expect(results.length).toBeGreaterThan(0);
      expect(results[0]).toHaveProperty('type');
      expect(results[0]).toHaveProperty('id');
    });

    it('returns empty array for empty query', async () => {
      const results = await search('');

      expect(Array.isArray(results)).toBe(true);
    });
  });

  describe('getNetworkStats', () => {
    it('fetches network statistics', async () => {
      const result = await getNetworkStats();

      expect(result).toHaveProperty('blockchain');
      expect(result).toHaveProperty('mempool');
      expect(result).toHaveProperty('updatedAt');
      expect(result.blockchain).toHaveProperty('totalBlocks');
      expect(result.blockchain).toHaveProperty('totalTransactions');
      expect(result.blockchain).toHaveProperty('avgBlockTime');
      expect(result.mempool).toHaveProperty('pendingTransactions');
    });
  });

  describe('getAITasks', () => {
    it('fetches AI tasks with default params', async () => {
      const result = await getAITasks();

      expect(result).toHaveProperty('tasks');
      expect(result).toHaveProperty('total');
      expect(Array.isArray(result.tasks)).toBe(true);
    });

    it('fetches AI tasks with filters', async () => {
      const result = await getAITasks({
        status: 'completed',
        aiModel: 'gpt-4',
        page: 1,
        limit: 10,
      });

      expect(result).toHaveProperty('tasks');
      expect(result).toHaveProperty('total');
    });

    it('transforms snake_case to camelCase', async () => {
      const result = await getAITasks();

      if (result.tasks.length > 0) {
        const task = result.tasks[0];
        expect(task).toHaveProperty('taskId');
        expect(task).toHaveProperty('taskType');
        expect(task).toHaveProperty('providerAddress');
        expect(task).toHaveProperty('aiModel');
        expect(task).toHaveProperty('costEstimate');
        expect(task).toHaveProperty('createdAt');
      }
    });
  });

  describe('getAITask', () => {
    it('fetches a single AI task by ID', async () => {
      const result = await getAITask('task123');

      expect(result).toHaveProperty('taskId');
      expect(result).toHaveProperty('taskType');
      expect(result).toHaveProperty('status');
      expect(result).toHaveProperty('aiModel');
    });

    it('throws error for non-existent task', async () => {
      await expect(getAITask('notfound')).rejects.toThrow();
    });
  });

  describe('getAIModels', () => {
    it('fetches available AI models', async () => {
      const result = await getAIModels();

      expect(Array.isArray(result)).toBe(true);
      expect(result.length).toBeGreaterThan(0);

      const model = result[0];
      expect(model).toHaveProperty('modelName');
      expect(model).toHaveProperty('provider');
      expect(model).toHaveProperty('totalTasks');
      expect(model).toHaveProperty('successRate');
      expect(model).toHaveProperty('averageComputeTime');
      expect(model).toHaveProperty('averageCost');
      expect(model).toHaveProperty('qualityScore');
    });
  });

  describe('getAIStats', () => {
    it('fetches AI statistics', async () => {
      const result = await getAIStats();

      expect(result).toHaveProperty('totalTasks');
      expect(result).toHaveProperty('completedTasks');
      expect(result).toHaveProperty('activeTasks');
      expect(result).toHaveProperty('failedTasks');
      expect(result).toHaveProperty('totalComputeHours');
      expect(result).toHaveProperty('totalCost');
      expect(result).toHaveProperty('activeProviders');
      expect(result).toHaveProperty('modelsInUse');
      expect(result).toHaveProperty('averageTaskTime');
      expect(result).toHaveProperty('successRate');
    });
  });
});
