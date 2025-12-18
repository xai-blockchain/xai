/**
 * WebSocket Client for XAI SDK
 *
 * Handles real-time event streaming with automatic reconnection.
 */

import WebSocket from 'ws';
import { EventEmitter } from 'events';
import { WebSocketError } from '../errors';
import { WebSocketMessage, WebSocketEventType } from '../types';

/**
 * WebSocket client configuration
 */
export interface WebSocketClientConfig {
  url: string;
  apiKey?: string;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
}

/**
 * WebSocket client for real-time blockchain events
 *
 * Features:
 * - Automatic reconnection with exponential backoff
 * - Event-based message handling
 * - Heartbeat/ping support
 * - Connection state management
 */
export class WebSocketClient extends EventEmitter {
  private ws?: WebSocket;
  private url: string;
  private apiKey?: string;
  private reconnectInterval: number;
  private maxReconnectAttempts: number;
  private reconnectAttempts: number = 0;
  private reconnectTimeout?: NodeJS.Timeout;
  private heartbeatInterval?: NodeJS.Timeout;
  private isIntentionallyClosed: boolean = false;

  constructor(config: WebSocketClientConfig) {
    super();
    this.url = config.url;
    this.apiKey = config.apiKey;
    this.reconnectInterval = config.reconnectInterval || 5000;
    this.maxReconnectAttempts = config.maxReconnectAttempts || 10;
  }

  /**
   * Connect to WebSocket server
   */
  connect(): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      return;
    }

    this.isIntentionallyClosed = false;

    try {
      const headers: Record<string, string> = {
        'User-Agent': 'XAI-SDK-TS/1.0',
      };

      if (this.apiKey) {
        headers['X-API-Key'] = this.apiKey;
      }

      this.ws = new WebSocket(this.url, { headers });
      this.setupEventHandlers();
    } catch (error) {
      this.emit('error', new WebSocketError(`Failed to connect: ${error}`));
      this.scheduleReconnect();
    }
  }

  /**
   * Setup WebSocket event handlers
   */
  private setupEventHandlers(): void {
    if (!this.ws) return;

    this.ws.on('open', () => {
      this.reconnectAttempts = 0;
      this.emit('connected');
      this.startHeartbeat();
    });

    this.ws.on('message', (data: WebSocket.Data) => {
      try {
        const message = JSON.parse(data.toString()) as WebSocketMessage;
        this.emit('message', message);
        this.emit(message.type, message.data);
      } catch (error) {
        this.emit('error', new WebSocketError(`Failed to parse message: ${error}`));
      }
    });

    this.ws.on('close', (code: number, reason: string) => {
      this.stopHeartbeat();
      this.emit('disconnected', { code, reason: reason.toString() });

      if (!this.isIntentionallyClosed) {
        this.scheduleReconnect();
      }
    });

    this.ws.on('error', (error: Error) => {
      this.emit('error', new WebSocketError(`WebSocket error: ${error.message}`));
    });

    this.ws.on('pong', () => {
      // Heartbeat response received
    });
  }

  /**
   * Start heartbeat to keep connection alive
   */
  private startHeartbeat(): void {
    this.heartbeatInterval = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.ping();
      }
    }, 30000); // Ping every 30 seconds
  }

  /**
   * Stop heartbeat
   */
  private stopHeartbeat(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = undefined;
    }
  }

  /**
   * Schedule reconnection attempt
   */
  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      this.emit(
        'error',
        new WebSocketError(
          `Max reconnection attempts (${this.maxReconnectAttempts}) reached`
        )
      );
      return;
    }

    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
    }

    const delay = this.reconnectInterval * Math.pow(2, this.reconnectAttempts);
    this.reconnectAttempts++;

    this.emit('reconnecting', {
      attempt: this.reconnectAttempts,
      maxAttempts: this.maxReconnectAttempts,
      delay,
    });

    this.reconnectTimeout = setTimeout(() => {
      this.connect();
    }, delay);
  }

  /**
   * Subscribe to specific event types
   */
  subscribe(eventType: WebSocketEventType): void {
    this.send({
      action: 'subscribe',
      event: eventType,
    });
  }

  /**
   * Unsubscribe from specific event types
   */
  unsubscribe(eventType: WebSocketEventType): void {
    this.send({
      action: 'unsubscribe',
      event: eventType,
    });
  }

  /**
   * Send message to server
   */
  send(data: unknown): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      throw new WebSocketError('WebSocket is not connected');
    }

    try {
      this.ws.send(JSON.stringify(data));
    } catch (error) {
      throw new WebSocketError(`Failed to send message: ${error}`);
    }
  }

  /**
   * Disconnect from WebSocket server
   */
  disconnect(): void {
    this.isIntentionallyClosed = true;

    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = undefined;
    }

    this.stopHeartbeat();

    if (this.ws) {
      this.ws.close();
      this.ws = undefined;
    }
  }

  /**
   * Check if connected
   */
  isConnected(): boolean {
    return this.ws !== undefined && this.ws.readyState === WebSocket.OPEN;
  }

  /**
   * Get connection state
   */
  getReadyState(): number | undefined {
    return this.ws?.readyState;
  }
}
