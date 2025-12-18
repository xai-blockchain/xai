/**
 * Wallet Client for XAI SDK
 *
 * Handles all wallet-related operations including creation, balance queries,
 * and transaction history.
 */

import { HTTPClient } from '../utils/http-client';
import {
  Wallet,
  Balance,
  WalletType,
  CreateWalletParams,
  CreateEmbeddedWalletParams,
  EmbeddedWalletLoginParams,
  TransactionHistoryParams,
  PaginatedResponse,
  Transaction,
} from '../types';
import { WalletError, ValidationError } from '../errors';

/**
 * Client for wallet operations
 */
export class WalletClient {
  constructor(private httpClient: HTTPClient) {}

  /**
   * Create a new wallet
   *
   * @param params - Wallet creation parameters
   * @returns Created wallet with address and keys
   *
   * @example
   * ```typescript
   * const wallet = await client.wallet.create({
   *   walletType: WalletType.STANDARD,
   *   name: 'My Wallet'
   * });
   * console.log('New wallet address:', wallet.address);
   * ```
   */
  async create(params: CreateWalletParams = {}): Promise<Wallet> {
    try {
      const payload: Record<string, unknown> = {};

      if (params.walletType) {
        payload.wallet_type = params.walletType;
      }
      if (params.name) {
        payload.name = params.name;
      }

      const response = await this.httpClient.post<{
        address: string;
        public_key: string;
        created_at: string;
        wallet_type?: string;
        private_key?: string;
      }>('/wallet/create', payload);

      return {
        address: response.address,
        publicKey: response.public_key,
        createdAt: response.created_at,
        walletType: response.wallet_type as WalletType,
        privateKey: response.private_key,
      };
    } catch (error) {
      if (error instanceof WalletError) {
        throw error;
      }
      throw new WalletError(`Failed to create wallet: ${error}`);
    }
  }

  /**
   * Get wallet information
   *
   * @param address - Wallet address
   * @returns Wallet details
   *
   * @example
   * ```typescript
   * const wallet = await client.wallet.get('0x1234...');
   * console.log('Wallet nonce:', wallet.nonce);
   * ```
   */
  async get(address: string): Promise<Wallet> {
    if (!address) {
      throw new ValidationError('Address is required');
    }

    try {
      const response = await this.httpClient.get<{
        address: string;
        public_key: string;
        created_at: string;
        wallet_type?: string;
        nonce?: number;
      }>(`/wallet/${address}`);

      return {
        address: response.address,
        publicKey: response.public_key,
        createdAt: response.created_at,
        walletType: response.wallet_type as WalletType,
        nonce: response.nonce || 0,
      };
    } catch (error) {
      if (error instanceof WalletError) {
        throw error;
      }
      throw new WalletError(`Failed to get wallet: ${error}`);
    }
  }

  /**
   * Get wallet balance
   *
   * @param address - Wallet address
   * @returns Balance information
   *
   * @example
   * ```typescript
   * const balance = await client.wallet.getBalance('0x1234...');
   * console.log('Balance:', balance.balance);
   * console.log('Available:', balance.availableBalance);
   * ```
   */
  async getBalance(address: string): Promise<Balance> {
    if (!address) {
      throw new ValidationError('Address is required');
    }

    try {
      const response = await this.httpClient.get<{
        address: string;
        balance: string;
        locked_balance?: string;
        available_balance?: string;
        nonce?: number;
      }>(`/wallet/${address}/balance`);

      return {
        address: response.address,
        balance: response.balance,
        lockedBalance: response.locked_balance || '0',
        availableBalance: response.available_balance || response.balance,
        nonce: response.nonce || 0,
      };
    } catch (error) {
      if (error instanceof WalletError) {
        throw error;
      }
      throw new WalletError(`Failed to get balance: ${error}`);
    }
  }

  /**
   * Get wallet transaction history
   *
   * @param params - Query parameters with address, limit, and offset
   * @returns Paginated transaction history
   *
   * @example
   * ```typescript
   * const history = await client.wallet.getTransactions({
   *   address: '0x1234...',
   *   limit: 20,
   *   offset: 0
   * });
   * console.log('Transactions:', history.data);
   * console.log('Total:', history.total);
   * ```
   */
  async getTransactions(params: TransactionHistoryParams): Promise<PaginatedResponse<Transaction>> {
    if (!params.address) {
      throw new ValidationError('Address is required');
    }

    const limit = Math.min(params.limit || 50, 100);
    const offset = params.offset || 0;

    try {
      const response = await this.httpClient.get<{
        transactions: Transaction[];
        total: number;
        limit: number;
        offset: number;
      }>(`/wallet/${params.address}/transactions`, {
        limit,
        offset,
      });

      return {
        data: response.transactions || [],
        total: response.total || 0,
        limit: response.limit || limit,
        offset: response.offset || offset,
      };
    } catch (error) {
      if (error instanceof WalletError) {
        throw error;
      }
      throw new WalletError(`Failed to get transactions: ${error}`);
    }
  }

  /**
   * Create an embedded wallet
   *
   * @param params - Embedded wallet creation parameters
   * @returns Embedded wallet information
   *
   * @example
   * ```typescript
   * const embeddedWallet = await client.wallet.createEmbedded({
   *   appId: 'my-app',
   *   userId: 'user-123',
   *   metadata: { email: 'user@example.com' }
   * });
   * ```
   */
  async createEmbedded(params: CreateEmbeddedWalletParams): Promise<Record<string, unknown>> {
    if (!params.appId || !params.userId) {
      throw new ValidationError('appId and userId are required');
    }

    try {
      const payload: Record<string, unknown> = {
        app_id: params.appId,
        user_id: params.userId,
      };

      if (params.metadata) {
        payload.metadata = params.metadata;
      }

      return await this.httpClient.post('/wallet/embedded/create', payload);
    } catch (error) {
      if (error instanceof WalletError) {
        throw error;
      }
      throw new WalletError(`Failed to create embedded wallet: ${error}`);
    }
  }

  /**
   * Login to an embedded wallet
   *
   * @param params - Login parameters with wallet ID and password
   * @returns Session information
   *
   * @example
   * ```typescript
   * const session = await client.wallet.loginEmbedded({
   *   walletId: 'wallet-123',
   *   password: 'secure-password'
   * });
   * ```
   */
  async loginEmbedded(params: EmbeddedWalletLoginParams): Promise<Record<string, unknown>> {
    if (!params.walletId || !params.password) {
      throw new ValidationError('walletId and password are required');
    }

    try {
      const payload = {
        wallet_id: params.walletId,
        password: params.password,
      };

      return await this.httpClient.post('/wallet/embedded/login', payload);
    } catch (error) {
      if (error instanceof WalletError) {
        throw error;
      }
      throw new WalletError(`Failed to login to embedded wallet: ${error}`);
    }
  }
}
