/**
 * Blockchain Client
 * Handles blockchain queries (blocks, stats, mempool, sync)
 */

import { HTTPClient } from '../utils/http-client';
import {
  Block,
  BlockHeader,
  BlockchainInfo,
  MempoolInfo,
  NetworkInfo,
  SyncProgress,
  HealthStatus,
} from '../types';

export class BlockchainClient {
  constructor(private httpClient: HTTPClient) {}

  /**
   * Get blocks with pagination
   */
  public async getBlocks(limit: number = 10, offset: number = 0): Promise<{
    total: number;
    limit: number;
    offset: number;
    blocks: Block[];
  }> {
    return this.httpClient.get('/blocks', {
      params: { limit, offset },
    });
  }

  /**
   * Get a specific block by index
   */
  public async getBlock(index: number): Promise<Block> {
    return this.httpClient.get<Block>(`/blocks/${index}`);
  }

  /**
   * Get a block by hash
   */
  public async getBlockByHash(hash: string): Promise<Block> {
    return this.httpClient.get<Block>(`/block/${hash}`);
  }

  /**
   * Get the latest block
   */
  public async getLatestBlock(): Promise<Block> {
    return this.httpClient.get<Block>('/block/latest');
  }

  /**
   * Get blockchain info (height, difficulty, etc.)
   */
  public async getInfo(): Promise<BlockchainInfo> {
    const stats = await this.httpClient.get<any>('/stats');
    return {
      height: stats.blockchain_height || stats.height || 0,
      best_block_hash: stats.best_block_hash || stats.latest_block_hash || '',
      difficulty: stats.difficulty || 0,
      total_transactions: stats.total_transactions || 0,
      version: stats.version,
      network: stats.network,
    };
  }

  /**
   * Get mempool information
   */
  public async getMempool(): Promise<MempoolInfo> {
    return this.httpClient.get<MempoolInfo>('/mempool');
  }

  /**
   * Get mempool stats
   */
  public async getMempoolStats(): Promise<{
    size: number;
    bytes: number;
    usage: number;
    max_mempool: number;
    min_fee: number;
  }> {
    return this.httpClient.get('/mempool/stats');
  }

  /**
   * Get network/peer information
   */
  public async getNetworkInfo(): Promise<NetworkInfo> {
    const peers = await this.httpClient.get<any>('/peers');
    return {
      peers: peers.peers || [],
      peer_count: peers.count || peers.peers?.length || 0,
      connections: peers.connections || peers.count || 0,
    };
  }

  /**
   * Get sync progress
   */
  public async getSyncProgress(): Promise<SyncProgress> {
    return this.httpClient.get<SyncProgress>('/sync/progress');
  }

  /**
   * Get sync status
   */
  public async getSyncStatus(): Promise<{
    syncing: boolean;
    current_height: number;
    target_height: number;
    progress_percentage: number;
  }> {
    return this.httpClient.get('/sync/status');
  }

  /**
   * Get node health status
   */
  public async getHealth(): Promise<HealthStatus> {
    return this.httpClient.get<HealthStatus>('/health');
  }

  /**
   * Get blockchain statistics
   */
  public async getStats(): Promise<Record<string, any>> {
    return this.httpClient.get('/stats');
  }

  /**
   * Get metrics (Prometheus-style)
   */
  public async getMetrics(): Promise<string> {
    return this.httpClient.get<string>('/metrics');
  }

  /**
   * Get consensus information
   */
  public async getConsensusInfo(): Promise<Record<string, any>> {
    return this.httpClient.get('/consensus/info');
  }

  /**
   * Validate a block
   */
  public async validateBlock(block: Block): Promise<{
    valid: boolean;
    errors?: string[];
  }> {
    return this.httpClient.post('/blocks/validate', block);
  }

  /**
   * Get block header only (lightweight)
   */
  public async getBlockHeader(index: number): Promise<BlockHeader> {
    const block = await this.getBlock(index);
    return {
      index: block.index,
      timestamp: block.timestamp,
      previous_hash: block.previous_hash,
      hash: block.hash,
      merkle_root: block.merkle_root || '',
      state_root: block.state_root,
      nonce: block.nonce,
      difficulty: block.difficulty,
    };
  }

  /**
   * Get the current blockchain height
   */
  public async getHeight(): Promise<number> {
    const info = await this.getInfo();
    return info.height;
  }

  /**
   * Get the current difficulty
   */
  public async getDifficulty(): Promise<number> {
    const info = await this.getInfo();
    return info.difficulty;
  }
}
