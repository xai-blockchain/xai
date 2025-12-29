/**
 * Unit tests for API client
 */

import { xaiApi, XaiApiClient } from '../../src/services/api';

describe('XAI API Client', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (global.fetch as jest.Mock).mockReset();
  });

  describe('constructor and configuration', () => {
    it('should have default base URL', () => {
      const client = new XaiApiClient();
      expect(client.getBaseUrl()).toBe('http://localhost:12001');
    });

    it('should accept custom base URL', () => {
      const client = new XaiApiClient('http://custom:8080');
      expect(client.getBaseUrl()).toBe('http://custom:8080');
    });

    it('should remove trailing slash from base URL', () => {
      const client = new XaiApiClient('http://localhost:12001/');
      expect(client.getBaseUrl()).toBe('http://localhost:12001');
    });

    it('should configure client options', () => {
      const client = new XaiApiClient();
      client.configure({
        baseUrl: 'http://new-server:9000',
        apiKey: 'test-api-key',
        timeout: 5000,
      });

      expect(client.getBaseUrl()).toBe('http://new-server:9000');
    });
  });

  describe('getNodeInfo', () => {
    it('should fetch node info successfully', async () => {
      const mockResponse = {
        status: 'online',
        node: 'xai-node-1',
        version: '1.0.0',
        algorithmic_features: true,
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const result = await xaiApi.getNodeInfo();

      expect(result.success).toBe(true);
      expect(result.data).toEqual({
        status: 'online',
        node: 'xai-node-1',
        version: '1.0.0',
        algorithmicFeatures: true,
      });
    });

    it('should handle error response', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: () => Promise.resolve({ error: 'Internal server error' }),
      });

      const result = await xaiApi.getNodeInfo();

      expect(result.success).toBe(false);
      expect(result.error).toBe('Internal server error');
    });
  });

  describe('getHealth', () => {
    it('should fetch health status', async () => {
      const mockResponse = {
        status: 'healthy',
        timestamp: 1700000000,
        blockchain: {
          accessible: true,
          height: 1000,
        },
        services: {
          api: 'running',
        },
        network: {
          peers: 5,
        },
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const result = await xaiApi.getHealth();

      expect(result.success).toBe(true);
      expect(result.data?.status).toBe('healthy');
      expect(result.data?.blockchain.accessible).toBe(true);
    });
  });

  describe('getStats', () => {
    it('should fetch blockchain stats', async () => {
      const mockResponse = {
        chain_height: 5000,
        difficulty: 1000000,
        total_circulating_supply: 1000000,
        pending_transactions_count: 10,
        latest_block_hash: 'abc123',
        miner_address: 'XAItest',
        peers: 5,
        is_mining: true,
        node_uptime: 3600,
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const result = await xaiApi.getStats();

      expect(result.success).toBe(true);
      expect(result.data?.chainHeight).toBe(5000);
      expect(result.data?.difficulty).toBe(1000000);
      expect(result.data?.isMining).toBe(true);
    });
  });

  describe('getBalance', () => {
    it('should fetch address balance', async () => {
      const address = 'XAIa1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2';
      const mockResponse = {
        address,
        balance: 100.5,
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const result = await xaiApi.getBalance(address);

      expect(result.success).toBe(true);
      expect(result.data?.balance).toBe(100.5);
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining(`/balance/${address}`),
        expect.any(Object)
      );
    });

    it('should URL encode address', async () => {
      const address = 'XAI+special/chars';

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ address, balance: 0 }),
      });

      await xaiApi.getBalance(address);

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining(encodeURIComponent(address)),
        expect.any(Object)
      );
    });
  });

  describe('getNonce', () => {
    it('should fetch nonce info', async () => {
      const mockResponse = {
        address: 'XAItest',
        confirmed_nonce: 5,
        next_nonce: 6,
        pending_nonce: 7,
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const result = await xaiApi.getNonce('XAItest');

      expect(result.success).toBe(true);
      expect(result.data?.confirmedNonce).toBe(5);
      expect(result.data?.nextNonce).toBe(6);
    });
  });

  describe('getHistory', () => {
    it('should fetch transaction history with pagination', async () => {
      const mockResponse = {
        address: 'XAItest',
        transaction_count: 50,
        transactions: [
          {
            txid: 'tx1',
            sender: 'XAItest',
            recipient: 'XAIother',
            amount: 10,
            fee: 0.001,
            timestamp: 1700000000,
            nonce: 1,
          },
        ],
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const result = await xaiApi.getHistory('XAItest', 50, 0);

      expect(result.success).toBe(true);
      expect(result.data?.transactions).toHaveLength(1);
      expect(result.data?.total).toBe(50);
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('limit=50'),
        expect.any(Object)
      );
    });
  });

  describe('sendTransaction', () => {
    it('should send transaction', async () => {
      const txRequest = {
        sender: 'XAIsender',
        recipient: 'XAIrecipient',
        amount: 100,
        fee: 0.001,
        publicKey: 'pubkey',
        signature: 'sig',
        nonce: 1,
        timestamp: 1700000000,
      };

      const mockResponse = {
        txid: 'newtx123',
        message: 'Transaction accepted',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const result = await xaiApi.sendTransaction(txRequest);

      expect(result.success).toBe(true);
      expect(result.data?.txid).toBe('newtx123');
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/send'),
        expect.objectContaining({
          method: 'POST',
          body: expect.any(String),
        })
      );
    });

    it('should send transaction body with correct field names', async () => {
      const txRequest = {
        sender: 'XAIsender',
        recipient: 'XAIrecipient',
        amount: 100,
        fee: 0.001,
        publicKey: 'pubkey',
        signature: 'sig',
        nonce: 1,
        timestamp: 1700000000,
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ txid: 'tx' }),
      });

      await xaiApi.sendTransaction(txRequest);

      const callArgs = (global.fetch as jest.Mock).mock.calls[0];
      const body = JSON.parse(callArgs[1].body);

      expect(body.public_key).toBe('pubkey'); // snake_case
      expect(body.sender).toBe('XAIsender');
    });
  });

  describe('getTransaction', () => {
    it('should fetch transaction by ID', async () => {
      const mockResponse = {
        found: true,
        transaction: {
          txid: 'tx123',
          sender: 'XAIsender',
          recipient: 'XAIrecipient',
          amount: 100,
          fee: 0.001,
          timestamp: 1700000000,
          nonce: 1,
        },
        confirmations: 10,
        status: 'confirmed',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const result = await xaiApi.getTransaction('tx123');

      expect(result.success).toBe(true);
      expect(result.data?.found).toBe(true);
      expect(result.data?.confirmations).toBe(10);
    });

    it('should handle not found transaction', async () => {
      const mockResponse = {
        found: false,
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const result = await xaiApi.getTransaction('nonexistent');

      expect(result.success).toBe(true);
      expect(result.data?.found).toBe(false);
    });
  });

  describe('getPendingTransactions', () => {
    it('should fetch pending transactions', async () => {
      const mockResponse = {
        count: 5,
        transactions: [
          { txid: 'tx1', sender: 'XAI1', recipient: 'XAI2', amount: 10 },
          { txid: 'tx2', sender: 'XAI3', recipient: 'XAI4', amount: 20 },
        ],
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const result = await xaiApi.getPendingTransactions(50, 0);

      expect(result.success).toBe(true);
      expect(result.data?.count).toBe(5);
      expect(result.data?.transactions).toHaveLength(2);
    });
  });

  describe('getBlocks', () => {
    it('should fetch blocks with pagination', async () => {
      const mockResponse = {
        total: 1000,
        blocks: [
          {
            index: 1000,
            hash: 'hash1000',
            previous_hash: 'hash999',
            timestamp: 1700000000,
            difficulty: 1000,
            nonce: 12345,
            transactions: [],
            merkle_root: 'merkle',
          },
        ],
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const result = await xaiApi.getBlocks(10, 0);

      expect(result.success).toBe(true);
      expect(result.data?.total).toBe(1000);
      expect(result.data?.blocks[0].index).toBe(1000);
    });
  });

  describe('getBlock', () => {
    it('should fetch block by index', async () => {
      const mockResponse = {
        index: 100,
        hash: 'blockhash',
        previous_hash: 'prevhash',
        timestamp: 1700000000,
        difficulty: 1000,
        nonce: 12345,
        miner: 'XAIminer',
        merkle_root: 'merkle',
        transactions: [],
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const result = await xaiApi.getBlock(100);

      expect(result.success).toBe(true);
      expect(result.data?.index).toBe(100);
      expect(result.data?.miner).toBe('XAIminer');
    });
  });

  describe('getBlockByHash', () => {
    it('should fetch block by hash', async () => {
      const mockResponse = {
        index: 50,
        hash: 'specific-hash',
        previous_hash: 'prev',
        timestamp: 1700000000,
        difficulty: 1000,
        nonce: 12345,
        transactions: [],
        merkle_root: 'merkle',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const result = await xaiApi.getBlockByHash('specific-hash');

      expect(result.success).toBe(true);
      expect(result.data?.hash).toBe('specific-hash');
    });
  });

  describe('claimFaucet', () => {
    it('should claim faucet tokens', async () => {
      const mockResponse = {
        amount: 100,
        txid: 'faucet-tx',
        message: 'Tokens sent',
        note: 'Testnet only',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const result = await xaiApi.claimFaucet('XAItest');

      expect(result.success).toBe(true);
      expect(result.data?.amount).toBe(100);
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/faucet/claim'),
        expect.objectContaining({
          method: 'POST',
        })
      );
    });
  });

  describe('getMempoolStats', () => {
    it('should fetch mempool statistics', async () => {
      const mockResponse = {
        fees: {
          average_fee: 0.001,
          median_fee: 0.0008,
          average_fee_rate: 0.00001,
          median_fee_rate: 0.000008,
          min_fee_rate: 0.000005,
          max_fee_rate: 0.0001,
          recommended_fee_rates: {
            slow: 0.0005,
            standard: 0.001,
            priority: 0.002,
          },
        },
        pressure: {
          status: 'normal',
          capacity_ratio: 0.3,
          pending_transactions: 50,
          max_transactions: 1000,
        },
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const result = await xaiApi.getMempoolStats();

      expect(result.success).toBe(true);
      expect(result.data?.fees.averageFee).toBe(0.001);
      expect(result.data?.pressure.status).toBe('normal');
      expect(result.data?.fees.recommendedFeeRates.standard).toBe(0.001);
    });
  });

  describe('error handling', () => {
    it('should handle network errors', async () => {
      (global.fetch as jest.Mock).mockRejectedValueOnce(new Error('Network error'));

      const result = await xaiApi.getNodeInfo();

      expect(result.success).toBe(false);
      expect(result.code).toBe('network_error');
    });

    it('should handle timeout', async () => {
      const abortError = new Error('Aborted');
      abortError.name = 'AbortError';

      (global.fetch as jest.Mock).mockRejectedValueOnce(abortError);

      const result = await xaiApi.getNodeInfo();

      expect(result.success).toBe(false);
      expect(result.code).toBe('timeout');
    });

    it('should handle unknown errors', async () => {
      (global.fetch as jest.Mock).mockRejectedValueOnce('string error');

      const result = await xaiApi.getNodeInfo();

      expect(result.success).toBe(false);
      expect(result.code).toBe('unknown');
    });

    it('should include API error code from response', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: () =>
          Promise.resolve({
            error: 'Invalid request',
            code: 'invalid_params',
          }),
      });

      const result = await xaiApi.getBalance('invalid');

      expect(result.success).toBe(false);
      expect(result.code).toBe('invalid_params');
    });
  });

  describe('headers', () => {
    it('should include Content-Type header', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({}),
      });

      await xaiApi.getNodeInfo();

      expect(global.fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
          }),
        })
      );
    });

    it('should include API key when configured', async () => {
      const client = new XaiApiClient();
      client.configure({ apiKey: 'secret-key' });

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({}),
      });

      await client.getNodeInfo();

      expect(global.fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({
            'X-API-Key': 'secret-key',
          }),
        })
      );
    });
  });
});
