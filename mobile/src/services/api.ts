/**
 * XAI Node API Client
 *
 * Handles all communication with the XAI blockchain node.
 */

import {
  NodeInfo,
  BlockchainStats,
  HealthStatus,
  Transaction,
  Block,
  NonceInfo,
  TransactionSendRequest,
  FaucetClaimResponse,
  MempoolStats,
  ApiResponse,
} from '../types';

// Default node URL - should be configured per environment
const DEFAULT_NODE_URL = 'http://localhost:12001';

class XaiApiClient {
  private baseUrl: string;
  private apiKey?: string;
  private timeout: number;

  constructor(baseUrl: string = DEFAULT_NODE_URL, timeout: number = 30000) {
    this.baseUrl = baseUrl.replace(/\/$/, ''); // Remove trailing slash
    this.timeout = timeout;
  }

  /**
   * Configure the API client
   */
  configure(options: { baseUrl?: string; apiKey?: string; timeout?: number }) {
    if (options.baseUrl) {
      this.baseUrl = options.baseUrl.replace(/\/$/, '');
    }
    if (options.apiKey) {
      this.apiKey = options.apiKey;
    }
    if (options.timeout) {
      this.timeout = options.timeout;
    }
  }

  /**
   * Get current base URL
   */
  getBaseUrl(): string {
    return this.baseUrl;
  }

  /**
   * Make a fetch request with timeout and error handling
   */
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    try {
      const headers: HeadersInit = {
        'Content-Type': 'application/json',
        ...(this.apiKey && { 'X-API-Key': this.apiKey }),
        ...(options.headers || {}),
      };

      const response = await fetch(`${this.baseUrl}${endpoint}`, {
        ...options,
        headers,
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      const data = await response.json();

      if (!response.ok) {
        return {
          success: false,
          error: data.error || `Request failed with status ${response.status}`,
          code: data.code || 'request_failed',
        };
      }

      return { success: true, data };
    } catch (error) {
      clearTimeout(timeoutId);

      if (error instanceof Error) {
        if (error.name === 'AbortError') {
          return { success: false, error: 'Request timeout', code: 'timeout' };
        }
        return { success: false, error: error.message, code: 'network_error' };
      }

      return { success: false, error: 'Unknown error', code: 'unknown' };
    }
  }

  // ============== Node Information ==============

  /**
   * Get node information
   */
  async getNodeInfo(): Promise<ApiResponse<NodeInfo>> {
    const result = await this.request<any>('/');
    if (result.success && result.data) {
      return {
        success: true,
        data: {
          status: result.data.status,
          node: result.data.node,
          version: result.data.version,
          algorithmicFeatures: result.data.algorithmic_features,
        },
      };
    }
    return result as ApiResponse<NodeInfo>;
  }

  /**
   * Get node health status
   */
  async getHealth(): Promise<ApiResponse<HealthStatus>> {
    const result = await this.request<any>('/health');
    if (result.success && result.data) {
      return {
        success: true,
        data: {
          status: result.data.status,
          timestamp: result.data.timestamp,
          blockchain: result.data.blockchain,
          services: result.data.services,
          network: result.data.network,
        },
      };
    }
    return result as ApiResponse<HealthStatus>;
  }

  /**
   * Get blockchain statistics
   */
  async getStats(): Promise<ApiResponse<BlockchainStats>> {
    const result = await this.request<any>('/stats');
    if (result.success && result.data) {
      return {
        success: true,
        data: {
          chainHeight: result.data.chain_height,
          difficulty: result.data.difficulty,
          totalSupply: result.data.total_circulating_supply,
          pendingTransactionsCount: result.data.pending_transactions_count,
          latestBlockHash: result.data.latest_block_hash,
          minerAddress: result.data.miner_address,
          peers: result.data.peers,
          isMining: result.data.is_mining,
          nodeUptime: result.data.node_uptime,
        },
      };
    }
    return result as ApiResponse<BlockchainStats>;
  }

  // ============== Wallet Operations ==============

  /**
   * Get balance for an address
   */
  async getBalance(address: string): Promise<ApiResponse<{ address: string; balance: number }>> {
    return this.request(`/balance/${encodeURIComponent(address)}`);
  }

  /**
   * Get nonce information for an address
   */
  async getNonce(address: string): Promise<ApiResponse<NonceInfo>> {
    const result = await this.request<any>(`/address/${encodeURIComponent(address)}/nonce`);
    if (result.success && result.data) {
      return {
        success: true,
        data: {
          address: result.data.address,
          confirmedNonce: result.data.confirmed_nonce,
          nextNonce: result.data.next_nonce,
          pendingNonce: result.data.pending_nonce,
        },
      };
    }
    return result as ApiResponse<NonceInfo>;
  }

  /**
   * Get transaction history for an address
   */
  async getHistory(
    address: string,
    limit: number = 50,
    offset: number = 0
  ): Promise<ApiResponse<{ address: string; transactions: Transaction[]; total: number }>> {
    const result = await this.request<any>(
      `/history/${encodeURIComponent(address)}?limit=${limit}&offset=${offset}`
    );
    if (result.success && result.data) {
      return {
        success: true,
        data: {
          address: result.data.address,
          total: result.data.transaction_count,
          transactions: result.data.transactions.map(this.mapTransaction),
        },
      };
    }
    return result as ApiResponse<any>;
  }

  // ============== Transaction Operations ==============

  /**
   * Send a transaction
   */
  async sendTransaction(tx: TransactionSendRequest): Promise<ApiResponse<{ txid: string; message: string }>> {
    return this.request('/send', {
      method: 'POST',
      body: JSON.stringify({
        sender: tx.sender,
        recipient: tx.recipient,
        amount: tx.amount,
        fee: tx.fee,
        public_key: tx.publicKey,
        signature: tx.signature,
        nonce: tx.nonce,
        timestamp: tx.timestamp,
        txid: tx.txid,
        metadata: tx.metadata,
      }),
    });
  }

  /**
   * Get transaction by ID
   */
  async getTransaction(txid: string): Promise<ApiResponse<{
    found: boolean;
    transaction?: Transaction;
    block?: number;
    confirmations?: number;
    status?: string;
  }>> {
    const result = await this.request<any>(`/transaction/${encodeURIComponent(txid)}`);
    if (result.success && result.data) {
      return {
        success: true,
        data: {
          found: result.data.found,
          transaction: result.data.transaction ? this.mapTransaction(result.data.transaction) : undefined,
          block: result.data.block,
          confirmations: result.data.confirmations,
          status: result.data.status,
        },
      };
    }
    return result as ApiResponse<any>;
  }

  /**
   * Get pending transactions
   */
  async getPendingTransactions(
    limit: number = 50,
    offset: number = 0
  ): Promise<ApiResponse<{ transactions: Transaction[]; count: number }>> {
    const result = await this.request<any>(`/transactions?limit=${limit}&offset=${offset}`);
    if (result.success && result.data) {
      return {
        success: true,
        data: {
          count: result.data.count,
          transactions: result.data.transactions.map(this.mapTransaction),
        },
      };
    }
    return result as ApiResponse<any>;
  }

  // ============== Block Operations ==============

  /**
   * Get blocks with pagination
   */
  async getBlocks(
    limit: number = 10,
    offset: number = 0
  ): Promise<ApiResponse<{ blocks: Block[]; total: number }>> {
    const result = await this.request<any>(`/blocks?limit=${limit}&offset=${offset}`);
    if (result.success && result.data) {
      return {
        success: true,
        data: {
          total: result.data.total,
          blocks: result.data.blocks.map(this.mapBlock),
        },
      };
    }
    return result as ApiResponse<any>;
  }

  /**
   * Get block by index
   */
  async getBlock(index: number): Promise<ApiResponse<Block>> {
    const result = await this.request<any>(`/blocks/${index}`);
    if (result.success && result.data) {
      return {
        success: true,
        data: this.mapBlock(result.data),
      };
    }
    return result as ApiResponse<Block>;
  }

  /**
   * Get block by hash
   */
  async getBlockByHash(hash: string): Promise<ApiResponse<Block>> {
    const result = await this.request<any>(`/block/${encodeURIComponent(hash)}`);
    if (result.success && result.data) {
      return {
        success: true,
        data: this.mapBlock(result.data),
      };
    }
    return result as ApiResponse<Block>;
  }

  // ============== Faucet (Testnet Only) ==============

  /**
   * Claim tokens from faucet
   */
  async claimFaucet(address: string): Promise<ApiResponse<FaucetClaimResponse>> {
    return this.request('/faucet/claim', {
      method: 'POST',
      body: JSON.stringify({ address }),
    });
  }

  // ============== Mempool ==============

  /**
   * Get mempool statistics
   */
  async getMempoolStats(): Promise<ApiResponse<MempoolStats>> {
    const result = await this.request<any>('/mempool/stats');
    if (result.success && result.data) {
      return {
        success: true,
        data: {
          fees: {
            averageFee: result.data.fees?.average_fee || 0,
            medianFee: result.data.fees?.median_fee || 0,
            averageFeeRate: result.data.fees?.average_fee_rate || 0,
            medianFeeRate: result.data.fees?.median_fee_rate || 0,
            minFeeRate: result.data.fees?.min_fee_rate || 0,
            maxFeeRate: result.data.fees?.max_fee_rate || 0,
            recommendedFeeRates: {
              slow: result.data.fees?.recommended_fee_rates?.slow || 0,
              standard: result.data.fees?.recommended_fee_rates?.standard || 0,
              priority: result.data.fees?.recommended_fee_rates?.priority || 0,
            },
          },
          pressure: {
            status: result.data.pressure?.status || 'normal',
            capacityRatio: result.data.pressure?.capacity_ratio || 0,
            pendingTransactions: result.data.pressure?.pending_transactions || 0,
            maxTransactions: result.data.pressure?.max_transactions || 0,
          },
        },
      };
    }
    return result as ApiResponse<MempoolStats>;
  }

  // ============== Helper Methods ==============

  private mapTransaction = (tx: any): Transaction => ({
    txid: tx.txid,
    sender: tx.sender,
    recipient: tx.recipient,
    amount: tx.amount,
    fee: tx.fee,
    timestamp: tx.timestamp,
    nonce: tx.nonce,
    signature: tx.signature,
    status: tx.confirmations !== undefined ? 'confirmed' : 'pending',
    confirmations: tx.confirmations,
    blockIndex: tx.block_index || tx.block,
  });

  private mapBlock = (block: any): Block => ({
    index: block.index ?? block.header?.index,
    hash: block.hash ?? block.header?.hash,
    previousHash: block.previous_hash ?? block.header?.previous_hash,
    timestamp: block.timestamp ?? block.header?.timestamp,
    difficulty: block.difficulty ?? block.header?.difficulty,
    nonce: block.nonce ?? block.header?.nonce,
    miner: block.miner ?? block.header?.miner,
    merkleRoot: block.merkle_root ?? block.header?.merkle_root,
    transactions: (block.transactions || []).map(this.mapTransaction),
  });
}

// Export singleton instance
export const xaiApi = new XaiApiClient();

// Export class for testing or custom instances
export { XaiApiClient };
