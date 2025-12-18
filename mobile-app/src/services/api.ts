import axios, { AxiosInstance, AxiosError } from 'axios';
import NetInfo from '@react-native-community/netinfo';
import {
  Transaction,
  SendTransactionRequest,
  SendTransactionResponse,
  BalanceResponse,
  NonceResponse,
  TransactionHistory,
  NodeInfo,
  Block,
} from '@/types';
import { API_CONFIG } from '@/constants';

class APIService {
  private client: AxiosInstance;
  private baseURL: string;
  private isOnline: boolean = true;

  constructor(baseURL: string = API_CONFIG.DEFAULT_ENDPOINT) {
    this.baseURL = baseURL;
    this.client = axios.create({
      baseURL,
      timeout: API_CONFIG.TIMEOUT,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Setup network monitoring
    NetInfo.addEventListener(state => {
      this.isOnline = state.isConnected ?? false;
    });

    // Request interceptor
    this.client.interceptors.request.use(
      config => {
        if (!this.isOnline) {
          throw new Error('No internet connection');
        }
        return config;
      },
      error => Promise.reject(error),
    );

    // Response interceptor
    this.client.interceptors.response.use(
      response => response,
      async (error: AxiosError) => {
        if (error.response?.status === 429) {
          // Rate limited - wait and retry
          await this.delay(API_CONFIG.RETRY_DELAY);
          return this.client.request(error.config!);
        }
        return Promise.reject(error);
      },
    );
  }

  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Update API endpoint
   */
  setBaseURL(url: string): void {
    this.baseURL = url;
    this.client.defaults.baseURL = url;
  }

  /**
   * Get node information
   */
  async getNodeInfo(): Promise<NodeInfo> {
    const response = await this.client.get<NodeInfo>('/info');
    return response.data;
  }

  /**
   * Get balance for address
   */
  async getBalance(address: string): Promise<number> {
    const response = await this.client.get<BalanceResponse>(`/balance/${address}`);
    return response.data.balance;
  }

  /**
   * Get nonce for address
   */
  async getNonce(address: string): Promise<NonceResponse> {
    const response = await this.client.get<NonceResponse>(`/address/${address}/nonce`);
    return response.data;
  }

  /**
   * Get transaction history
   */
  async getHistory(
    address: string,
    limit: number = 50,
    offset: number = 0,
  ): Promise<TransactionHistory> {
    const response = await this.client.get<TransactionHistory>(`/history/${address}`, {
      params: { limit, offset },
    });
    return response.data;
  }

  /**
   * Get transaction by ID
   */
  async getTransaction(txid: string): Promise<Transaction | null> {
    try {
      const response = await this.client.get(`/transaction/${txid}`);
      if (response.data.found) {
        return {
          ...response.data.transaction,
          confirmations: response.data.confirmations,
          status: response.data.status === 'pending' ? 'pending' : 'confirmed',
        };
      }
      return null;
    } catch (error) {
      console.error('Failed to fetch transaction:', error);
      return null;
    }
  }

  /**
   * Get pending transactions
   */
  async getPendingTransactions(limit: number = 50, offset: number = 0): Promise<Transaction[]> {
    const response = await this.client.get('/transactions', {
      params: { limit, offset },
    });
    return response.data.transactions || [];
  }

  /**
   * Send transaction
   */
  async sendTransaction(tx: SendTransactionRequest): Promise<SendTransactionResponse> {
    try {
      const response = await this.client.post<SendTransactionResponse>('/send', tx);
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        return {
          success: false,
          error: error.response?.data?.error || error.message,
        };
      }
      return {
        success: false,
        error: 'Unknown error occurred',
      };
    }
  }

  /**
   * Get latest block
   */
  async getLatestBlock(): Promise<Block | null> {
    try {
      const response = await this.client.get('/chain/latest');
      return response.data.block;
    } catch (error) {
      console.error('Failed to fetch latest block:', error);
      return null;
    }
  }

  /**
   * Get block by index
   */
  async getBlock(index: number): Promise<Block | null> {
    try {
      const response = await this.client.get(`/block/${index}`);
      return response.data.block;
    } catch (error) {
      console.error(`Failed to fetch block ${index}:`, error);
      return null;
    }
  }

  /**
   * Check if online
   */
  isConnected(): boolean {
    return this.isOnline;
  }

  /**
   * Retry with exponential backoff
   */
  async retry<T>(
    fn: () => Promise<T>,
    attempts: number = API_CONFIG.RETRY_ATTEMPTS,
  ): Promise<T> {
    let lastError: Error | null = null;

    for (let i = 0; i < attempts; i++) {
      try {
        return await fn();
      } catch (error) {
        lastError = error as Error;
        if (i < attempts - 1) {
          const delay = API_CONFIG.RETRY_DELAY * Math.pow(2, i);
          await this.delay(delay);
        }
      }
    }

    throw lastError;
  }
}

export default new APIService();
