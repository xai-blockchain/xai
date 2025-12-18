/**
 * XAI Client
 * Main client for interacting with XAI blockchain nodes
 */

import {
  XAIConfig,
  Block,
  Transaction,
  WalletBalance,
  BlockchainInfo,
  MiningStats,
  Proposal,
  Vote,
  VoteOption,
  Peer,
  SendTransactionParams,
  PaginationParams,
  PaginatedResponse,
} from '../types';
import { HttpClient } from '../utils/http-client';

export class XAIClient {
  private http: HttpClient;

  constructor(config: XAIConfig) {
    this.http = new HttpClient(config);
  }

  // ============================================================================
  // Blockchain Methods
  // ============================================================================

  /**
   * Get blockchain information
   */
  async getBlockchainInfo(): Promise<BlockchainInfo> {
    return this.http.get('/blockchain/info');
  }

  /**
   * Get block by number or hash
   */
  async getBlock(blockNumberOrHash: number | string): Promise<Block> {
    return this.http.get(`/blockchain/blocks/${blockNumberOrHash}`);
  }

  /**
   * Get latest block
   */
  async getLatestBlock(): Promise<Block> {
    return this.http.get('/blockchain/blocks/latest');
  }

  /**
   * Get blocks with pagination
   */
  async getBlocks(params?: PaginationParams): Promise<PaginatedResponse<Block>> {
    return this.http.get('/blockchain/blocks', { params });
  }

  // ============================================================================
  // Wallet Methods
  // ============================================================================

  /**
   * Get wallet balance
   */
  async getBalance(address: string): Promise<WalletBalance> {
    return this.http.get(`/wallet/balance/${address}`);
  }

  /**
   * Create a new wallet on the node (not recommended for mobile)
   */
  async createWallet(): Promise<{ address: string; privateKey: string }> {
    return this.http.post('/wallet/create');
  }

  // ============================================================================
  // Transaction Methods
  // ============================================================================

  /**
   * Get transaction by hash
   */
  async getTransaction(hash: string): Promise<Transaction> {
    return this.http.get(`/transactions/${hash}`);
  }

  /**
   * Get transactions for an address
   */
  async getTransactionsByAddress(
    address: string,
    params?: PaginationParams
  ): Promise<PaginatedResponse<Transaction>> {
    return this.http.get(`/transactions/address/${address}`, { params });
  }

  /**
   * Get pending transactions
   */
  async getPendingTransactions(): Promise<Transaction[]> {
    return this.http.get('/transactions/pending');
  }

  /**
   * Send a signed transaction
   */
  async sendTransaction(params: SendTransactionParams): Promise<Transaction> {
    return this.http.post('/transactions/send', params);
  }

  /**
   * Broadcast a raw signed transaction
   */
  async broadcastTransaction(rawTransaction: string): Promise<Transaction> {
    return this.http.post('/transactions/broadcast', { rawTransaction });
  }

  /**
   * Estimate transaction fee
   */
  async estimateFee(params: SendTransactionParams): Promise<{ fee: string }> {
    return this.http.post('/transactions/estimate-fee', params);
  }

  /**
   * Get transaction count for address (nonce)
   */
  async getTransactionCount(address: string): Promise<{ count: number }> {
    return this.http.get(`/transactions/count/${address}`);
  }

  // ============================================================================
  // Mining Methods
  // ============================================================================

  /**
   * Get mining statistics
   */
  async getMiningStats(): Promise<MiningStats> {
    return this.http.get('/mining/stats');
  }

  /**
   * Start mining (if supported)
   */
  async startMining(address: string): Promise<{ success: boolean }> {
    return this.http.post('/mining/start', { address });
  }

  /**
   * Stop mining
   */
  async stopMining(): Promise<{ success: boolean }> {
    return this.http.post('/mining/stop');
  }

  // ============================================================================
  // Governance Methods
  // ============================================================================

  /**
   * Get all proposals
   */
  async getProposals(
    params?: PaginationParams
  ): Promise<PaginatedResponse<Proposal>> {
    return this.http.get('/governance/proposals', { params });
  }

  /**
   * Get proposal by ID
   */
  async getProposal(id: string): Promise<Proposal> {
    return this.http.get(`/governance/proposals/${id}`);
  }

  /**
   * Submit a new proposal
   */
  async submitProposal(
    title: string,
    description: string,
    from: string
  ): Promise<Proposal> {
    return this.http.post('/governance/proposals', {
      title,
      description,
      from,
    });
  }

  /**
   * Vote on a proposal
   */
  async vote(
    proposalId: string,
    vote: VoteOption,
    from: string
  ): Promise<Vote> {
    return this.http.post(`/governance/proposals/${proposalId}/vote`, {
      vote,
      from,
    });
  }

  /**
   * Get votes for a proposal
   */
  async getVotes(proposalId: string): Promise<Vote[]> {
    return this.http.get(`/governance/proposals/${proposalId}/votes`);
  }

  // ============================================================================
  // Network Methods
  // ============================================================================

  /**
   * Get connected peers
   */
  async getPeers(): Promise<Peer[]> {
    return this.http.get('/network/peers');
  }

  /**
   * Get network statistics
   */
  async getNetworkStats(): Promise<{
    peers: number;
    height: number;
    version: string;
  }> {
    return this.http.get('/network/stats');
  }

  /**
   * Add a peer
   */
  async addPeer(address: string, port: number): Promise<{ success: boolean }> {
    return this.http.post('/network/peers', { address, port });
  }

  // ============================================================================
  // Health & Status Methods
  // ============================================================================

  /**
   * Check node health
   */
  async getHealth(): Promise<{ status: string; timestamp: number }> {
    return this.http.get('/health');
  }

  /**
   * Get node version
   */
  async getVersion(): Promise<{ version: string; buildDate: string }> {
    return this.http.get('/version');
  }

  /**
   * Ping the node
   */
  async ping(): Promise<{ pong: boolean; latency: number }> {
    const start = Date.now();
    await this.http.get('/ping');
    const latency = Date.now() - start;
    return { pong: true, latency };
  }

  // ============================================================================
  // Configuration Methods
  // ============================================================================

  /**
   * Update the base URL
   */
  setBaseUrl(baseUrl: string): void {
    this.http.updateBaseUrl(baseUrl);
  }

  /**
   * Get current base URL
   */
  getBaseUrl(): string {
    return this.http.getBaseUrl();
  }
}
