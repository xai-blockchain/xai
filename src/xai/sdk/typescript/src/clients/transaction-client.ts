/**
 * Transaction Client for XAI SDK
 *
 * Handles transaction sending, retrieval, fee estimation, and confirmation tracking.
 */

import { HTTPClient } from '../utils/http-client';
import {
  Transaction,
  TransactionStatus,
  SendTransactionParams,
  FeeEstimation,
} from '../types';
import { TransactionError, ValidationError } from '../errors';

/**
 * Client for transaction operations
 */
export class TransactionClient {
  constructor(private httpClient: HTTPClient) {}

  /**
   * Send a transaction
   *
   * @param params - Transaction parameters
   * @returns Transaction details
   *
   * @example
   * ```typescript
   * const tx = await client.transaction.send({
   *   from: '0x1234...',
   *   to: '0x5678...',
   *   amount: '1000',
   *   data: '0x...'
   * });
   * console.log('Transaction hash:', tx.hash);
   * ```
   */
  async send(params: SendTransactionParams): Promise<Transaction> {
    if (!params.from || !params.to || !params.amount) {
      throw new ValidationError('from, to, and amount are required');
    }

    try {
      const payload: Record<string, unknown> = {
        from: params.from,
        to: params.to,
        amount: params.amount,
      };

      if (params.data) {
        payload.data = params.data;
      }
      if (params.gasLimit) {
        payload.gas_limit = params.gasLimit;
      }
      if (params.gasPrice) {
        payload.gas_price = params.gasPrice;
      }
      if (params.nonce !== undefined) {
        payload.nonce = params.nonce;
      }
      if (params.signature) {
        payload.signature = params.signature;
      }

      const response = await this.httpClient.post<{
        hash: string;
        from: string;
        to: string;
        amount: string;
        timestamp: string;
        status?: string;
        fee?: string;
        gas_used?: string;
      }>('/transaction/send', payload);

      return {
        hash: response.hash,
        from: response.from,
        to: response.to,
        amount: response.amount,
        timestamp: response.timestamp,
        status: (response.status as TransactionStatus) || TransactionStatus.PENDING,
        fee: response.fee || '0',
        gasUsed: response.gas_used || '0',
      };
    } catch (error) {
      if (error instanceof TransactionError) {
        throw error;
      }
      throw new TransactionError(`Failed to send transaction: ${error}`);
    }
  }

  /**
   * Get transaction details
   *
   * @param txHash - Transaction hash
   * @returns Transaction details
   *
   * @example
   * ```typescript
   * const tx = await client.transaction.get('0xabc...');
   * console.log('Transaction status:', tx.status);
   * console.log('Confirmations:', tx.confirmations);
   * ```
   */
  async get(txHash: string): Promise<Transaction> {
    if (!txHash) {
      throw new ValidationError('txHash is required');
    }

    try {
      const response = await this.httpClient.get<{
        hash: string;
        from: string;
        to: string;
        amount: string;
        timestamp: string;
        status?: string;
        fee?: string;
        gas_used?: string;
        block_number?: number;
        block_hash?: string;
        confirmations?: number;
      }>(`/transaction/${txHash}`);

      return {
        hash: response.hash,
        from: response.from,
        to: response.to,
        amount: response.amount,
        timestamp: response.timestamp,
        status: (response.status as TransactionStatus) || TransactionStatus.PENDING,
        fee: response.fee || '0',
        gasUsed: response.gas_used || '0',
        blockNumber: response.block_number,
        blockHash: response.block_hash,
        confirmations: response.confirmations || 0,
      };
    } catch (error) {
      if (error instanceof TransactionError) {
        throw error;
      }
      throw new TransactionError(`Failed to get transaction: ${error}`);
    }
  }

  /**
   * Get transaction status
   *
   * @param txHash - Transaction hash
   * @returns Transaction status information
   *
   * @example
   * ```typescript
   * const status = await client.transaction.getStatus('0xabc...');
   * console.log('Status:', status);
   * ```
   */
  async getStatus(txHash: string): Promise<Record<string, unknown>> {
    if (!txHash) {
      throw new ValidationError('txHash is required');
    }

    try {
      return await this.httpClient.get(`/transaction/${txHash}/status`);
    } catch (error) {
      if (error instanceof TransactionError) {
        throw error;
      }
      throw new TransactionError(`Failed to get transaction status: ${error}`);
    }
  }

  /**
   * Estimate transaction fee
   *
   * @param params - Transaction parameters for estimation
   * @returns Fee estimation details
   *
   * @example
   * ```typescript
   * const fee = await client.transaction.estimateFee({
   *   from: '0x1234...',
   *   to: '0x5678...',
   *   amount: '1000'
   * });
   * console.log('Estimated fee:', fee.estimatedFee);
   * console.log('Gas limit:', fee.gasLimit);
   * ```
   */
  async estimateFee(params: {
    from: string;
    to: string;
    amount: string;
    data?: string;
  }): Promise<FeeEstimation> {
    if (!params.from || !params.to || !params.amount) {
      throw new ValidationError('from, to, and amount are required');
    }

    try {
      const payload: Record<string, unknown> = {
        from: params.from,
        to: params.to,
        amount: params.amount,
      };

      if (params.data) {
        payload.data = params.data;
      }

      const response = await this.httpClient.post<{
        estimated_fee: string;
        gas_limit: string;
        gas_price: string;
        base_fee?: string;
        priority_fee?: string;
      }>('/transaction/estimate-fee', payload);

      return {
        estimatedFee: response.estimated_fee,
        gasLimit: response.gas_limit,
        gasPrice: response.gas_price,
        baseFee: response.base_fee,
        priorityFee: response.priority_fee,
      };
    } catch (error) {
      if (error instanceof TransactionError) {
        throw error;
      }
      throw new TransactionError(`Failed to estimate fee: ${error}`);
    }
  }

  /**
   * Check if transaction is confirmed
   *
   * @param txHash - Transaction hash
   * @param confirmations - Number of required confirmations (default: 1)
   * @returns True if transaction has required confirmations
   *
   * @example
   * ```typescript
   * const isConfirmed = await client.transaction.isConfirmed('0xabc...', 3);
   * if (isConfirmed) {
   *   console.log('Transaction confirmed with 3+ confirmations');
   * }
   * ```
   */
  async isConfirmed(txHash: string, confirmations: number = 1): Promise<boolean> {
    try {
      const status = await this.getStatus(txHash);
      return (status.confirmations as number) >= confirmations;
    } catch (error) {
      if (error instanceof TransactionError) {
        throw error;
      }
      throw new TransactionError(`Failed to check confirmation: ${error}`);
    }
  }

  /**
   * Wait for transaction confirmation
   *
   * @param txHash - Transaction hash
   * @param confirmations - Number of required confirmations (default: 1)
   * @param timeout - Maximum time to wait in milliseconds (default: 600000)
   * @param pollInterval - Polling interval in milliseconds (default: 5000)
   * @returns Confirmed transaction
   *
   * @example
   * ```typescript
   * const tx = await client.transaction.waitForConfirmation('0xabc...', 3);
   * console.log('Transaction confirmed!', tx);
   * ```
   */
  async waitForConfirmation(
    txHash: string,
    confirmations: number = 1,
    timeout: number = 600000,
    pollInterval: number = 5000
  ): Promise<Transaction> {
    const startTime = Date.now();

    while (true) {
      if (Date.now() - startTime > timeout) {
        throw new TransactionError(`Transaction confirmation timeout after ${timeout}ms`);
      }

      try {
        const tx = await this.get(txHash);
        if ((tx.confirmations || 0) >= confirmations) {
          return tx;
        }
      } catch (error) {
        if (error instanceof TransactionError) {
          throw error;
        }
        throw new TransactionError(`Failed to wait for confirmation: ${error}`);
      }

      await new Promise((resolve) => setTimeout(resolve, pollInterval));
    }
  }

  /**
   * Get pending transactions
   *
   * @returns List of pending transactions
   *
   * @example
   * ```typescript
   * const pending = await client.transaction.getPending();
   * console.log('Pending transactions:', pending);
   * ```
   */
  async getPending(): Promise<Transaction[]> {
    try {
      const response = await this.httpClient.get<{
        transactions: Transaction[];
      }>('/mempool');

      return response.transactions || [];
    } catch (error) {
      if (error instanceof TransactionError) {
        throw error;
      }
      throw new TransactionError(`Failed to get pending transactions: ${error}`);
    }
  }
}
