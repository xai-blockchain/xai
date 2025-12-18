/**
 * Mining Client for XAI SDK
 *
 * Handles mining operations, status monitoring, and reward management.
 */

import { HTTPClient } from '../utils/http-client';
import { MiningStatus, MiningRewards } from '../types';
import { MiningError, ValidationError } from '../errors';

/**
 * Client for mining operations
 */
export class MiningClient {
  constructor(private httpClient: HTTPClient) {}

  /**
   * Start mining
   *
   * @param threads - Number of mining threads (1-16, default: 1)
   * @returns Mining status
   *
   * @example
   * ```typescript
   * const status = await client.mining.start(4);
   * console.log('Mining started with 4 threads');
   * ```
   */
  async start(threads: number = 1): Promise<Record<string, unknown>> {
    if (threads < 1 || threads > 16) {
      throw new ValidationError('threads must be between 1 and 16');
    }

    try {
      const payload = { threads };
      return await this.httpClient.post('/mining/start', payload);
    } catch (error) {
      if (error instanceof MiningError) {
        throw error;
      }
      throw new MiningError(`Failed to start mining: ${error}`);
    }
  }

  /**
   * Stop mining
   *
   * @returns Mining status
   *
   * @example
   * ```typescript
   * const status = await client.mining.stop();
   * console.log('Mining stopped');
   * ```
   */
  async stop(): Promise<Record<string, unknown>> {
    try {
      return await this.httpClient.post('/mining/stop', {});
    } catch (error) {
      if (error instanceof MiningError) {
        throw error;
      }
      throw new MiningError(`Failed to stop mining: ${error}`);
    }
  }

  /**
   * Get mining status
   *
   * @returns Mining status information
   *
   * @example
   * ```typescript
   * const status = await client.mining.getStatus();
   * console.log('Mining:', status.mining);
   * console.log('Hashrate:', status.hashrate);
   * console.log('Blocks found:', status.blocksFound);
   * ```
   */
  async getStatus(): Promise<MiningStatus> {
    try {
      const response = await this.httpClient.get<{
        mining: boolean;
        threads: number;
        hashrate: string;
        blocks_found?: number;
        current_difficulty: string;
        uptime?: number;
        last_block_time?: number;
      }>('/mining/status');

      return {
        mining: response.mining,
        threads: response.threads,
        hashrate: response.hashrate,
        blocksFound: response.blocks_found || 0,
        currentDifficulty: response.current_difficulty,
        uptime: response.uptime || 0,
        lastBlockTime: response.last_block_time,
      };
    } catch (error) {
      if (error instanceof MiningError) {
        throw error;
      }
      throw new MiningError(`Failed to get mining status: ${error}`);
    }
  }

  /**
   * Get mining rewards for an address
   *
   * @param address - Wallet address
   * @returns Reward information
   *
   * @example
   * ```typescript
   * const rewards = await client.mining.getRewards('0x1234...');
   * console.log('Total rewards:', rewards.totalRewards);
   * console.log('Pending rewards:', rewards.pendingRewards);
   * ```
   */
  async getRewards(address: string): Promise<MiningRewards> {
    if (!address) {
      throw new ValidationError('address is required');
    }

    try {
      const response = await this.httpClient.get<{
        address: string;
        total_rewards: string;
        pending_rewards: string;
        claimed_rewards: string;
        blocks_found?: number;
      }>('/mining/rewards', { address });

      return {
        address: response.address,
        totalRewards: response.total_rewards,
        pendingRewards: response.pending_rewards,
        claimedRewards: response.claimed_rewards,
        blocksFound: response.blocks_found,
      };
    } catch (error) {
      if (error instanceof MiningError) {
        throw error;
      }
      throw new MiningError(`Failed to get mining rewards: ${error}`);
    }
  }

  /**
   * Check if mining is active
   *
   * @returns True if mining is active
   *
   * @example
   * ```typescript
   * const isMining = await client.mining.isMining();
   * if (isMining) {
   *   console.log('Mining is active');
   * }
   * ```
   */
  async isMining(): Promise<boolean> {
    try {
      const status = await this.getStatus();
      return status.mining;
    } catch (error) {
      if (error instanceof MiningError) {
        throw error;
      }
      throw new MiningError(`Failed to check mining status: ${error}`);
    }
  }

  /**
   * Get current mining difficulty
   *
   * @returns Current difficulty as string
   *
   * @example
   * ```typescript
   * const difficulty = await client.mining.getDifficulty();
   * console.log('Current difficulty:', difficulty);
   * ```
   */
  async getDifficulty(): Promise<string> {
    try {
      const status = await this.getStatus();
      return status.currentDifficulty;
    } catch (error) {
      if (error instanceof MiningError) {
        throw error;
      }
      throw new MiningError(`Failed to get difficulty: ${error}`);
    }
  }

  /**
   * Get current hashrate
   *
   * @returns Current hashrate as string
   *
   * @example
   * ```typescript
   * const hashrate = await client.mining.getHashrate();
   * console.log('Current hashrate:', hashrate);
   * ```
   */
  async getHashrate(): Promise<string> {
    try {
      const status = await this.getStatus();
      return status.hashrate;
    } catch (error) {
      if (error instanceof MiningError) {
        throw error;
      }
      throw new MiningError(`Failed to get hashrate: ${error}`);
    }
  }
}
