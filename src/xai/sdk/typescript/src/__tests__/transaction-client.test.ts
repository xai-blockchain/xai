/**
 * TransactionClient Unit Tests
 *
 * Comprehensive tests for transaction operations including:
 * - Transaction sending
 * - Transaction retrieval
 * - Status checking
 * - Fee estimation
 * - Confirmation waiting
 * - Pending transactions
 * - Error handling and validation
 */

import { TransactionClient } from '../clients/transaction-client';
import { HTTPClient } from '../utils/http-client';
import { ValidationError, TransactionError } from '../errors';
import { TransactionStatus } from '../types';

// Mock HTTPClient
jest.mock('../utils/http-client');

const MockHTTPClient = HTTPClient as jest.MockedClass<typeof HTTPClient>;

describe('TransactionClient', () => {
  let transactionClient: TransactionClient;
  let mockHttpClient: jest.Mocked<HTTPClient>;

  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();
    mockHttpClient = new MockHTTPClient({
      baseUrl: 'http://localhost:5000',
    }) as jest.Mocked<HTTPClient>;
    transactionClient = new TransactionClient(mockHttpClient);
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  describe('send', () => {
    it('should send transaction with required parameters', async () => {
      const mockResponse = {
        hash: '0xtxhash123',
        from: '0xsender',
        to: '0xreceiver',
        amount: '1000',
        timestamp: '2024-01-01T00:00:00Z',
        status: 'pending',
        fee: '21000',
        gas_used: '21000',
      };

      mockHttpClient.post = jest.fn().mockResolvedValue(mockResponse);

      const result = await transactionClient.send({
        from: '0xsender',
        to: '0xreceiver',
        amount: '1000',
      });

      expect(mockHttpClient.post).toHaveBeenCalledWith('/transaction/send', {
        from: '0xsender',
        to: '0xreceiver',
        amount: '1000',
      });
      expect(result).toEqual({
        hash: '0xtxhash123',
        from: '0xsender',
        to: '0xreceiver',
        amount: '1000',
        timestamp: '2024-01-01T00:00:00Z',
        status: TransactionStatus.PENDING,
        fee: '21000',
        gasUsed: '21000',
      });
    });

    it('should send transaction with all optional parameters', async () => {
      const mockResponse = {
        hash: '0xtxhash456',
        from: '0xsender',
        to: '0xreceiver',
        amount: '5000',
        timestamp: '2024-01-01T00:00:00Z',
      };

      mockHttpClient.post = jest.fn().mockResolvedValue(mockResponse);

      await transactionClient.send({
        from: '0xsender',
        to: '0xreceiver',
        amount: '5000',
        data: '0xabcdef',
        gasLimit: '100000',
        gasPrice: '20000000000',
        nonce: 5,
        signature: '0xsig123',
      });

      expect(mockHttpClient.post).toHaveBeenCalledWith('/transaction/send', {
        from: '0xsender',
        to: '0xreceiver',
        amount: '5000',
        data: '0xabcdef',
        gas_limit: '100000',
        gas_price: '20000000000',
        nonce: 5,
        signature: '0xsig123',
      });
    });

    it('should handle nonce of 0 correctly', async () => {
      const mockResponse = {
        hash: '0xtx',
        from: '0xsender',
        to: '0xreceiver',
        amount: '100',
        timestamp: '2024-01-01T00:00:00Z',
      };

      mockHttpClient.post = jest.fn().mockResolvedValue(mockResponse);

      await transactionClient.send({
        from: '0xsender',
        to: '0xreceiver',
        amount: '100',
        nonce: 0,
      });

      expect(mockHttpClient.post).toHaveBeenCalledWith('/transaction/send', {
        from: '0xsender',
        to: '0xreceiver',
        amount: '100',
        nonce: 0,
      });
    });

    it('should throw ValidationError for missing from', async () => {
      await expect(
        transactionClient.send({ from: '', to: '0xreceiver', amount: '1000' })
      ).rejects.toThrow(ValidationError);
      await expect(
        transactionClient.send({ from: '', to: '0xreceiver', amount: '1000' })
      ).rejects.toThrow('from, to, and amount are required');
    });

    it('should throw ValidationError for missing to', async () => {
      await expect(
        transactionClient.send({ from: '0xsender', to: '', amount: '1000' })
      ).rejects.toThrow(ValidationError);
    });

    it('should throw ValidationError for missing amount', async () => {
      await expect(
        transactionClient.send({ from: '0xsender', to: '0xreceiver', amount: '' })
      ).rejects.toThrow(ValidationError);
    });

    it('should handle missing optional response fields', async () => {
      const mockResponse = {
        hash: '0xtx',
        from: '0xsender',
        to: '0xreceiver',
        amount: '100',
        timestamp: '2024-01-01T00:00:00Z',
      };

      mockHttpClient.post = jest.fn().mockResolvedValue(mockResponse);

      const result = await transactionClient.send({
        from: '0xsender',
        to: '0xreceiver',
        amount: '100',
      });

      expect(result.status).toBe(TransactionStatus.PENDING);
      expect(result.fee).toBe('0');
      expect(result.gasUsed).toBe('0');
    });

    it('should wrap unknown errors in TransactionError', async () => {
      mockHttpClient.post = jest.fn().mockRejectedValue(new Error('Insufficient funds'));

      await expect(
        transactionClient.send({ from: '0xsender', to: '0xreceiver', amount: '1000' })
      ).rejects.toThrow(TransactionError);
      await expect(
        transactionClient.send({ from: '0xsender', to: '0xreceiver', amount: '1000' })
      ).rejects.toThrow('Failed to send transaction');
    });

    it('should re-throw TransactionError without wrapping', async () => {
      const txError = new TransactionError('Transaction rejected');
      mockHttpClient.post = jest.fn().mockRejectedValue(txError);

      await expect(
        transactionClient.send({ from: '0xsender', to: '0xreceiver', amount: '1000' })
      ).rejects.toThrow(txError);
    });
  });

  describe('get', () => {
    it('should get transaction by hash', async () => {
      const mockResponse = {
        hash: '0xtxhash123',
        from: '0xsender',
        to: '0xreceiver',
        amount: '1000',
        timestamp: '2024-01-01T00:00:00Z',
        status: 'confirmed',
        fee: '21000',
        gas_used: '21000',
        block_number: 12345,
        block_hash: '0xblockhash',
        confirmations: 10,
      };

      mockHttpClient.get = jest.fn().mockResolvedValue(mockResponse);

      const result = await transactionClient.get('0xtxhash123');

      expect(mockHttpClient.get).toHaveBeenCalledWith('/transaction/0xtxhash123');
      expect(result).toEqual({
        hash: '0xtxhash123',
        from: '0xsender',
        to: '0xreceiver',
        amount: '1000',
        timestamp: '2024-01-01T00:00:00Z',
        status: TransactionStatus.CONFIRMED,
        fee: '21000',
        gasUsed: '21000',
        blockNumber: 12345,
        blockHash: '0xblockhash',
        confirmations: 10,
      });
    });

    it('should throw ValidationError for empty txHash', async () => {
      await expect(transactionClient.get('')).rejects.toThrow(ValidationError);
      await expect(transactionClient.get('')).rejects.toThrow('txHash is required');
    });

    it('should handle missing optional fields', async () => {
      const mockResponse = {
        hash: '0xtx',
        from: '0xsender',
        to: '0xreceiver',
        amount: '100',
        timestamp: '2024-01-01T00:00:00Z',
      };

      mockHttpClient.get = jest.fn().mockResolvedValue(mockResponse);

      const result = await transactionClient.get('0xtx');

      expect(result.status).toBe(TransactionStatus.PENDING);
      expect(result.fee).toBe('0');
      expect(result.gasUsed).toBe('0');
      expect(result.confirmations).toBe(0);
    });

    it('should wrap unknown errors in TransactionError', async () => {
      mockHttpClient.get = jest.fn().mockRejectedValue(new Error('Not found'));

      await expect(transactionClient.get('0xinvalid')).rejects.toThrow(TransactionError);
      await expect(transactionClient.get('0xinvalid')).rejects.toThrow('Failed to get transaction');
    });
  });

  describe('getStatus', () => {
    it('should get transaction status', async () => {
      const mockResponse = {
        status: 'confirmed',
        confirmations: 15,
        block_number: 12345,
      };

      mockHttpClient.get = jest.fn().mockResolvedValue(mockResponse);

      const result = await transactionClient.getStatus('0xtxhash');

      expect(mockHttpClient.get).toHaveBeenCalledWith('/transaction/0xtxhash/status');
      expect(result).toEqual(mockResponse);
    });

    it('should throw ValidationError for empty txHash', async () => {
      await expect(transactionClient.getStatus('')).rejects.toThrow(ValidationError);
      await expect(transactionClient.getStatus('')).rejects.toThrow('txHash is required');
    });

    it('should wrap unknown errors in TransactionError', async () => {
      mockHttpClient.get = jest.fn().mockRejectedValue(new Error('Network error'));

      await expect(transactionClient.getStatus('0xtx')).rejects.toThrow(TransactionError);
      await expect(transactionClient.getStatus('0xtx')).rejects.toThrow(
        'Failed to get transaction status'
      );
    });
  });

  describe('estimateFee', () => {
    it('should estimate fee for transaction', async () => {
      const mockResponse = {
        estimated_fee: '21000000000000',
        gas_limit: '21000',
        gas_price: '1000000000',
        base_fee: '500000000',
        priority_fee: '500000000',
      };

      mockHttpClient.post = jest.fn().mockResolvedValue(mockResponse);

      const result = await transactionClient.estimateFee({
        from: '0xsender',
        to: '0xreceiver',
        amount: '1000',
      });

      expect(mockHttpClient.post).toHaveBeenCalledWith('/transaction/estimate-fee', {
        from: '0xsender',
        to: '0xreceiver',
        amount: '1000',
      });
      expect(result).toEqual({
        estimatedFee: '21000000000000',
        gasLimit: '21000',
        gasPrice: '1000000000',
        baseFee: '500000000',
        priorityFee: '500000000',
      });
    });

    it('should estimate fee with data', async () => {
      const mockResponse = {
        estimated_fee: '50000000000000',
        gas_limit: '50000',
        gas_price: '1000000000',
      };

      mockHttpClient.post = jest.fn().mockResolvedValue(mockResponse);

      await transactionClient.estimateFee({
        from: '0xsender',
        to: '0xcontract',
        amount: '0',
        data: '0xabcdef123456',
      });

      expect(mockHttpClient.post).toHaveBeenCalledWith('/transaction/estimate-fee', {
        from: '0xsender',
        to: '0xcontract',
        amount: '0',
        data: '0xabcdef123456',
      });
    });

    it('should throw ValidationError for missing required fields', async () => {
      await expect(
        transactionClient.estimateFee({ from: '', to: '0xreceiver', amount: '1000' })
      ).rejects.toThrow(ValidationError);
      await expect(
        transactionClient.estimateFee({ from: '0xsender', to: '', amount: '1000' })
      ).rejects.toThrow(ValidationError);
      await expect(
        transactionClient.estimateFee({ from: '0xsender', to: '0xreceiver', amount: '' })
      ).rejects.toThrow(ValidationError);
    });

    it('should wrap unknown errors in TransactionError', async () => {
      mockHttpClient.post = jest.fn().mockRejectedValue(new Error('Estimation failed'));

      await expect(
        transactionClient.estimateFee({ from: '0x1', to: '0x2', amount: '100' })
      ).rejects.toThrow(TransactionError);
      await expect(
        transactionClient.estimateFee({ from: '0x1', to: '0x2', amount: '100' })
      ).rejects.toThrow('Failed to estimate fee');
    });
  });

  describe('isConfirmed', () => {
    it('should return true when confirmations meet threshold', async () => {
      mockHttpClient.get = jest.fn().mockResolvedValue({
        confirmations: 6,
      });

      const result = await transactionClient.isConfirmed('0xtx', 3);

      expect(result).toBe(true);
    });

    it('should return false when confirmations below threshold', async () => {
      mockHttpClient.get = jest.fn().mockResolvedValue({
        confirmations: 2,
      });

      const result = await transactionClient.isConfirmed('0xtx', 3);

      expect(result).toBe(false);
    });

    it('should use default confirmations of 1', async () => {
      mockHttpClient.get = jest.fn().mockResolvedValue({
        confirmations: 1,
      });

      const result = await transactionClient.isConfirmed('0xtx');

      expect(result).toBe(true);
    });

    it('should wrap unknown errors in TransactionError', async () => {
      mockHttpClient.get = jest.fn().mockRejectedValue(new Error('Network error'));

      await expect(transactionClient.isConfirmed('0xtx', 3)).rejects.toThrow(TransactionError);
      // Error message comes from getStatus which isConfirmed calls
      await expect(transactionClient.isConfirmed('0xtx', 3)).rejects.toThrow(
        'Failed to get transaction status'
      );
    });
  });

  describe('waitForConfirmation', () => {
    it('should return immediately if already confirmed', async () => {
      const mockTransaction = {
        hash: '0xtx',
        from: '0xsender',
        to: '0xreceiver',
        amount: '100',
        timestamp: '2024-01-01T00:00:00Z',
        status: 'confirmed',
        confirmations: 10,
      };

      mockHttpClient.get = jest.fn().mockResolvedValue(mockTransaction);

      const resultPromise = transactionClient.waitForConfirmation('0xtx', 3);

      // No need to advance timers since it should resolve immediately
      const result = await resultPromise;

      expect(result.confirmations).toBe(10);
    });

    it('should poll until confirmed', async () => {
      // Use real timers for this specific test since waitForConfirmation uses real timing
      jest.useRealTimers();

      let callCount = 0;
      mockHttpClient.get = jest.fn().mockImplementation(() => {
        callCount++;
        if (callCount < 3) {
          return Promise.resolve({
            hash: '0xtx',
            from: '0xsender',
            to: '0xreceiver',
            amount: '100',
            timestamp: '2024-01-01T00:00:00Z',
            confirmations: 0,
          });
        }
        return Promise.resolve({
          hash: '0xtx',
          from: '0xsender',
          to: '0xreceiver',
          amount: '100',
          timestamp: '2024-01-01T00:00:00Z',
          confirmations: 3,
        });
      });

      // Use very short poll interval for test
      const result = await transactionClient.waitForConfirmation('0xtx', 3, 5000, 10);

      expect(result.confirmations).toBe(3);
      expect(callCount).toBe(3);
    }, 10000);

    it('should throw TransactionError on timeout', async () => {
      mockHttpClient.get = jest.fn().mockResolvedValue({
        hash: '0xtx',
        from: '0xsender',
        to: '0xreceiver',
        amount: '100',
        timestamp: '2024-01-01T00:00:00Z',
        confirmations: 0,
      });

      // Use real timers for this test to test timeout behavior
      jest.useRealTimers();

      // Use a very short timeout
      const promise = transactionClient.waitForConfirmation('0xtx', 3, 100, 50);

      await expect(promise).rejects.toThrow(TransactionError);
      await expect(
        transactionClient.waitForConfirmation('0xtx', 3, 100, 50)
      ).rejects.toThrow('Transaction confirmation timeout after 100ms');
    });
  });

  describe('getPending', () => {
    it('should get pending transactions', async () => {
      const mockResponse = {
        transactions: [
          { hash: '0xtx1', from: '0xa', to: '0xb', amount: '100' },
          { hash: '0xtx2', from: '0xc', to: '0xd', amount: '200' },
        ],
      };

      mockHttpClient.get = jest.fn().mockResolvedValue(mockResponse);

      const result = await transactionClient.getPending();

      expect(mockHttpClient.get).toHaveBeenCalledWith('/mempool');
      expect(result).toHaveLength(2);
    });

    it('should handle empty mempool', async () => {
      const mockResponse = {
        transactions: null,
      };

      mockHttpClient.get = jest.fn().mockResolvedValue(mockResponse);

      const result = await transactionClient.getPending();

      expect(result).toEqual([]);
    });

    it('should wrap unknown errors in TransactionError', async () => {
      mockHttpClient.get = jest.fn().mockRejectedValue(new Error('Database error'));

      await expect(transactionClient.getPending()).rejects.toThrow(TransactionError);
      await expect(transactionClient.getPending()).rejects.toThrow(
        'Failed to get pending transactions'
      );
    });
  });
});
