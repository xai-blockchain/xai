/**
 * XAI SDK Main Client
 *
 * Provides unified interface to all blockchain operations with support for
 * HTTP requests and WebSocket real-time events.
 */

import { HTTPClient } from './utils/http-client';
import { WebSocketClient } from './utils/websocket-client';
import { WalletClient } from './clients/wallet-client';
import { TransactionClient } from './clients/transaction-client';
import { BlockchainClient } from './clients/blockchain-client';
import { MiningClient } from './clients/mining-client';
import { GovernanceClient } from './clients/governance-client';
import { XAIClientConfig, NodeInfo, HealthCheckResponse } from './types';

/**
 * Main client for XAI blockchain operations
 *
 * Provides unified interface to wallet, transaction, blockchain,
 * mining, and governance operations with optional WebSocket support.
 *
 * @example
 * ```typescript
 * // Create client
 * const client = new XAIClient({
 *   baseUrl: 'http://localhost:5000',
 *   apiKey: 'your-api-key'
 * });
 *
 * // Use wallet operations
 * const wallet = await client.wallet.create();
 * const balance = await client.wallet.getBalance(wallet.address);
 *
 * // Send transaction
 * const tx = await client.transaction.send({
 *   from: wallet.address,
 *   to: '0x...',
 *   amount: '1000'
 * });
 *
 * // Subscribe to real-time events
 * client.connectWebSocket();
 * client.on('new_block', (block) => {
 *   console.log('New block:', block);
 * });
 *
 * // Clean up
 * client.close();
 * ```
 */
export class XAIClient {
  private httpClient: HTTPClient;
  private wsClient?: WebSocketClient;

  public readonly wallet: WalletClient;
  public readonly transaction: TransactionClient;
  public readonly blockchain: BlockchainClient;
  public readonly mining: MiningClient;
  public readonly governance: GovernanceClient;

  constructor(config: XAIClientConfig = {}) {
    const baseUrl = config.baseUrl || 'http://localhost:5000';
    const timeout = config.timeout || 30000;
    const maxRetries = config.maxRetries || 3;
    const retryDelay = config.retryDelay || 500;

    // Initialize HTTP client
    this.httpClient = new HTTPClient({
      baseUrl,
      apiKey: config.apiKey,
      timeout,
      maxRetries,
      retryDelay,
    });

    // Initialize service clients
    this.wallet = new WalletClient(this.httpClient);
    this.transaction = new TransactionClient(this.httpClient);
    this.blockchain = new BlockchainClient(this.httpClient);
    this.mining = new MiningClient(this.httpClient);
    this.governance = new GovernanceClient(this.httpClient);
  }

  /**
   * Connect to WebSocket for real-time events
   *
   * @param wsUrl - WebSocket URL (defaults to base URL with ws/wss protocol)
   *
   * @example
   * ```typescript
   * client.connectWebSocket('ws://localhost:5000/ws');
   * client.on('new_block', (block) => {
   *   console.log('New block:', block);
   * });
   * ```
   */
  connectWebSocket(wsUrl?: string): void {
    if (this.wsClient && this.wsClient.isConnected()) {
      return;
    }

    const url =
      wsUrl ||
      this.httpClient['client'].defaults.baseURL?.replace(/^http/, 'ws') + '/ws' ||
      'ws://localhost:5000/ws';

    this.wsClient = new WebSocketClient({
      url,
      apiKey: this.httpClient['apiKey'],
    });

    this.wsClient.connect();
  }

  /**
   * Disconnect WebSocket
   */
  disconnectWebSocket(): void {
    if (this.wsClient) {
      this.wsClient.disconnect();
      this.wsClient = undefined;
    }
  }

  /**
   * Subscribe to WebSocket event
   *
   * @param event - Event name
   * @param listener - Event listener function
   *
   * @example
   * ```typescript
   * client.on('new_transaction', (tx) => {
   *   console.log('New transaction:', tx);
   * });
   * ```
   */
  on(event: string, listener: (...args: unknown[]) => void): void {
    if (!this.wsClient) {
      throw new Error('WebSocket not connected. Call connectWebSocket() first.');
    }
    this.wsClient.on(event, listener);
  }

  /**
   * Unsubscribe from WebSocket event
   *
   * @param event - Event name
   * @param listener - Event listener function
   */
  off(event: string, listener: (...args: unknown[]) => void): void {
    if (!this.wsClient) {
      return;
    }
    this.wsClient.off(event, listener);
  }

  /**
   * Quick health check of the API
   *
   * @returns Health status
   *
   * @example
   * ```typescript
   * const health = await client.healthCheck();
   * if (health.status === 'healthy') {
   *   console.log('API is healthy');
   * }
   * ```
   */
  async healthCheck(): Promise<HealthCheckResponse> {
    return this.blockchain.getHealth();
  }

  /**
   * Get blockchain node information
   *
   * @returns Node information
   *
   * @example
   * ```typescript
   * const info = await client.getInfo();
   * console.log('Node version:', info.version);
   * ```
   */
  async getInfo(): Promise<NodeInfo> {
    return this.blockchain.getNodeInfo();
  }

  /**
   * Close the HTTP client and WebSocket connection
   *
   * @example
   * ```typescript
   * client.close();
   * ```
   */
  close(): void {
    this.httpClient.close();
    this.disconnectWebSocket();
  }

  /**
   * Check if WebSocket is connected
   *
   * @returns True if WebSocket is connected
   */
  isWebSocketConnected(): boolean {
    return this.wsClient?.isConnected() || false;
  }
}

// Export default for convenience
export default XAIClient;
