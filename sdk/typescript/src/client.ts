/**
 * XAI Client
 * Main entry point for the XAI SDK
 */

import { HTTPClient } from './utils/http-client';
import { WebSocketClient } from './utils/websocket-client';
import { WalletClient } from './clients/wallet-client';
import { TransactionClient } from './clients/transaction-client';
import { BlockchainClient } from './clients/blockchain-client';
import { MiningClient } from './clients/mining-client';
import { GovernanceClient } from './clients/governance-client';
import { XAIClientConfig } from './types';

export class XAIClient {
  private httpClient: HTTPClient;
  private wsClient?: WebSocketClient;

  public readonly wallet: WalletClient;
  public readonly transaction: TransactionClient;
  public readonly blockchain: BlockchainClient;
  public readonly mining: MiningClient;
  public readonly governance: GovernanceClient;

  constructor(config: XAIClientConfig) {
    // Initialize HTTP client
    this.httpClient = new HTTPClient({
      baseUrl: config.baseUrl,
      timeout: config.timeout,
      retries: config.retries,
      retryDelay: config.retryDelay,
      apiKey: config.apiKey,
    });

    // Initialize WebSocket client if URL provided
    if (config.wsUrl) {
      this.wsClient = new WebSocketClient({
        url: config.wsUrl,
        reconnect: true,
      });
    }

    // Initialize sub-clients
    this.wallet = new WalletClient(this.httpClient);
    this.transaction = new TransactionClient(this.httpClient);
    this.blockchain = new BlockchainClient(this.httpClient);
    this.mining = new MiningClient(this.httpClient);
    this.governance = new GovernanceClient(this.httpClient);
  }

  /**
   * Connect to WebSocket for real-time events
   */
  public async connectWebSocket(): Promise<void> {
    if (!this.wsClient) {
      throw new Error('WebSocket URL not configured');
    }
    await this.wsClient.connect();
  }

  /**
   * Subscribe to blockchain events via WebSocket
   */
  public subscribe(event: string, callback: (data: any) => void): () => void {
    if (!this.wsClient) {
      throw new Error('WebSocket not configured');
    }
    return this.wsClient.subscribe(event, callback);
  }

  /**
   * Disconnect WebSocket
   */
  public disconnectWebSocket(): void {
    if (this.wsClient) {
      this.wsClient.disconnect();
    }
  }

  /**
   * Check if WebSocket is connected
   */
  public isWebSocketConnected(): boolean {
    return this.wsClient?.isConnected() || false;
  }

  /**
   * Get the base URL of the node
   */
  public getBaseUrl(): string {
    return this.httpClient.getBaseUrl();
  }

  /**
   * Ping the node
   */
  public async ping(): Promise<boolean> {
    try {
      await this.blockchain.getHealth();
      return true;
    } catch (error) {
      return false;
    }
  }
}
