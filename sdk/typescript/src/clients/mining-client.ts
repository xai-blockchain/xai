/**
 * Mining Client
 * Handles mining operations and statistics
 */

import { HTTPClient } from '../utils/http-client';
import { MiningStats } from '../types';

export class MiningClient {
  constructor(private httpClient: HTTPClient) {}

  /**
   * Start mining
   */
  public async start(minerAddress: string): Promise<{ success: boolean; message: string }> {
    return this.httpClient.post('/mine/start', { miner_address: minerAddress });
  }

  /**
   * Stop mining
   */
  public async stop(): Promise<{ success: boolean; message: string }> {
    return this.httpClient.post('/mine/stop');
  }

  /**
   * Mine a single block
   */
  public async mineBlock(minerAddress: string): Promise<{
    success: boolean;
    block?: any;
    message?: string;
  }> {
    return this.httpClient.post('/mine', { miner_address: minerAddress });
  }

  /**
   * Get mining status
   */
  public async getStatus(): Promise<MiningStats> {
    return this.httpClient.get<MiningStats>('/mine/status');
  }

  /**
   * Get mining statistics
   */
  public async getStats(): Promise<{
    blocks_mined: number;
    total_rewards: number;
    current_difficulty: number;
    hashrate?: number;
    last_block_time?: number;
  }> {
    return this.httpClient.get('/mine/stats');
  }

  /**
   * Enable auto-mining
   */
  public async enableAutoMine(minerAddress: string, interval?: number): Promise<{
    success: boolean;
    message: string;
  }> {
    return this.httpClient.post('/mine/auto/enable', {
      miner_address: minerAddress,
      interval,
    });
  }

  /**
   * Disable auto-mining
   */
  public async disableAutoMine(): Promise<{ success: boolean; message: string }> {
    return this.httpClient.post('/mine/auto/disable');
  }

  /**
   * Get auto-mining status
   */
  public async getAutoMineStatus(): Promise<{
    enabled: boolean;
    interval?: number;
    miner_address?: string;
  }> {
    return this.httpClient.get('/mine/auto/status');
  }

  /**
   * Get mining difficulty
   */
  public async getDifficulty(): Promise<{ difficulty: number }> {
    return this.httpClient.get('/mine/difficulty');
  }

  /**
   * Get block reward
   */
  public async getBlockReward(): Promise<{ reward: number }> {
    return this.httpClient.get('/mine/reward');
  }
}
