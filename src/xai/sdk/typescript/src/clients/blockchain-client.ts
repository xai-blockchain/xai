/**
 * Blockchain Client for XAI SDK
 *
 * Handles blockchain querying, block retrieval, and synchronization status.
 */

import { HTTPClient } from '../utils/http-client';
import {
  Block,
  BlockchainStats,
  BlockQueryParams,
  PaginatedResponse,
  Transaction,
  SyncStatus,
  NodeInfo,
  HealthCheckResponse,
} from '../types';
import { XAIError, ValidationError } from '../errors';

/**
 * Client for blockchain operations
 */
export class BlockchainClient {
  constructor(private httpClient: HTTPClient) {}

  /**
   * Get block details by number
   *
   * @param blockNumber - Block number
   * @returns Block details
   *
   * @example
   * ```typescript
   * const block = await client.blockchain.getBlock(1000);
   * console.log('Block hash:', block.hash);
   * console.log('Transactions:', block.transactions);
   * ```
   */
  async getBlock(blockNumber: number): Promise<Block> {
    if (blockNumber < 0) {
      throw new ValidationError('blockNumber must be non-negative');
    }

    try {
      const response = await this.httpClient.get<{
        number: number;
        hash: string;
        parent_hash: string;
        timestamp: number;
        miner: string;
        difficulty: string;
        gas_limit?: string;
        gas_used?: string;
        transaction_count?: number;
        transactions?: string[];
      }>(`/blockchain/blocks/${blockNumber}`);

      return {
        number: response.number,
        hash: response.hash,
        parentHash: response.parent_hash,
        timestamp: response.timestamp,
        miner: response.miner,
        difficulty: response.difficulty,
        gasLimit: response.gas_limit || '0',
        gasUsed: response.gas_used || '0',
        transactions: response.transaction_count || 0,
        transactionHashes: response.transactions || [],
      };
    } catch (error) {
      if (error instanceof XAIError) {
        throw error;
      }
      throw new XAIError(`Failed to get block: ${error}`);
    }
  }

  /**
   * List recent blocks
   *
   * @param params - Query parameters with limit and offset
   * @returns Paginated list of blocks
   *
   * @example
   * ```typescript
   * const result = await client.blockchain.listBlocks({ limit: 10, offset: 0 });
   * console.log('Latest blocks:', result.data);
   * console.log('Total blocks:', result.total);
   * ```
   */
  async listBlocks(params: BlockQueryParams = {}): Promise<PaginatedResponse<Block>> {
    const limit = Math.min(params.limit || 20, 100);
    const offset = params.offset || 0;

    try {
      const response = await this.httpClient.get<{
        blocks: Array<{
          number: number;
          hash: string;
          parent_hash: string;
          timestamp: number;
          miner: string;
          difficulty?: string;
          gas_limit?: string;
          gas_used?: string;
          transaction_count?: number;
        }>;
        total: number;
        limit: number;
        offset: number;
      }>('/blockchain/blocks', {
        limit,
        offset,
      });

      const blocks = (response.blocks || []).map((b) => ({
        number: b.number,
        hash: b.hash,
        parentHash: b.parent_hash,
        timestamp: b.timestamp,
        miner: b.miner,
        difficulty: b.difficulty || '0',
        gasLimit: b.gas_limit || '0',
        gasUsed: b.gas_used || '0',
        transactions: b.transaction_count || 0,
      }));

      return {
        data: blocks,
        total: response.total || 0,
        limit: response.limit || limit,
        offset: response.offset || offset,
      };
    } catch (error) {
      if (error instanceof XAIError) {
        throw error;
      }
      throw new XAIError(`Failed to list blocks: ${error}`);
    }
  }

  /**
   * Get transactions in a specific block
   *
   * @param blockNumber - Block number
   * @returns List of transactions
   *
   * @example
   * ```typescript
   * const transactions = await client.blockchain.getBlockTransactions(1000);
   * console.log('Transactions in block:', transactions);
   * ```
   */
  async getBlockTransactions(blockNumber: number): Promise<Transaction[]> {
    if (blockNumber < 0) {
      throw new ValidationError('blockNumber must be non-negative');
    }

    try {
      const response = await this.httpClient.get<{
        transactions: Transaction[];
      }>(`/blockchain/blocks/${blockNumber}/transactions`);

      return response.transactions || [];
    } catch (error) {
      if (error instanceof XAIError) {
        throw error;
      }
      throw new XAIError(`Failed to get block transactions: ${error}`);
    }
  }

  /**
   * Get blockchain synchronization status
   *
   * @returns Sync status information
   *
   * @example
   * ```typescript
   * const syncStatus = await client.blockchain.getSyncStatus();
   * if (syncStatus.syncing) {
   *   console.log('Sync progress:', syncStatus.syncProgress);
   * }
   * ```
   */
  async getSyncStatus(): Promise<SyncStatus> {
    try {
      const response = await this.httpClient.get<{
        syncing: boolean;
        current_block?: number;
        highest_block?: number;
        starting_block?: number;
      }>('/blockchain/sync');

      return {
        syncing: response.syncing,
        currentBlock: response.current_block,
        highestBlock: response.highest_block,
        startingBlock: response.starting_block,
        syncProgress:
          response.current_block && response.highest_block
            ? (response.current_block / response.highest_block) * 100
            : undefined,
      };
    } catch (error) {
      if (error instanceof XAIError) {
        throw error;
      }
      throw new XAIError(`Failed to get sync status: ${error}`);
    }
  }

  /**
   * Check if blockchain is synchronized
   *
   * @returns True if blockchain is synced
   *
   * @example
   * ```typescript
   * const isSynced = await client.blockchain.isSynced();
   * if (isSynced) {
   *   console.log('Blockchain is fully synchronized');
   * }
   * ```
   */
  async isSynced(): Promise<boolean> {
    try {
      const status = await this.getSyncStatus();
      return !status.syncing;
    } catch (error) {
      if (error instanceof XAIError) {
        throw error;
      }
      throw new XAIError(`Failed to check sync status: ${error}`);
    }
  }

  /**
   * Get blockchain statistics
   *
   * @returns Blockchain statistics
   *
   * @example
   * ```typescript
   * const stats = await client.blockchain.getStats();
   * console.log('Total blocks:', stats.totalBlocks);
   * console.log('Total transactions:', stats.totalTransactions);
   * console.log('Network hashrate:', stats.hashrate);
   * ```
   */
  async getStats(): Promise<BlockchainStats> {
    try {
      const response = await this.httpClient.get<{
        total_blocks: number;
        total_transactions: number;
        total_accounts: number;
        difficulty: string;
        hashrate: string;
        average_block_time?: number;
        total_supply: string;
        network?: string;
      }>('/stats');

      return {
        totalBlocks: response.total_blocks,
        totalTransactions: response.total_transactions,
        totalAccounts: response.total_accounts,
        difficulty: response.difficulty,
        hashrate: response.hashrate,
        averageBlockTime: response.average_block_time || 0,
        totalSupply: response.total_supply,
        network: response.network || 'mainnet',
      };
    } catch (error) {
      if (error instanceof XAIError) {
        throw error;
      }
      throw new XAIError(`Failed to get blockchain stats: ${error}`);
    }
  }

  /**
   * Get blockchain node information
   *
   * @returns Node information
   *
   * @example
   * ```typescript
   * const info = await client.blockchain.getNodeInfo();
   * console.log('Node version:', info.version);
   * console.log('Node type:', info.node);
   * ```
   */
  async getNodeInfo(): Promise<NodeInfo> {
    try {
      return await this.httpClient.get<NodeInfo>('/');
    } catch (error) {
      if (error instanceof XAIError) {
        throw error;
      }
      throw new XAIError(`Failed to get node info: ${error}`);
    }
  }

  /**
   * Get node health status
   *
   * @returns Health check response
   *
   * @example
   * ```typescript
   * const health = await client.blockchain.getHealth();
   * if (health.status === 'healthy') {
   *   console.log('Node is healthy');
   * }
   * ```
   */
  async getHealth(): Promise<HealthCheckResponse> {
    try {
      return await this.httpClient.get<HealthCheckResponse>('/health');
    } catch (error) {
      if (error instanceof XAIError) {
        throw error;
      }
      throw new XAIError(`Failed to check node health: ${error}`);
    }
  }
}
