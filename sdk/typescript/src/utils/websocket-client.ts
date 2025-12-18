/**
 * WebSocket Client
 * Handles real-time event subscriptions from the XAI blockchain
 */

import WebSocket from 'ws';
import { WebSocketError } from '../errors';
import { WebSocketEvent, EventSubscription } from '../types';

export interface WebSocketClientConfig {
  url: string;
  reconnect?: boolean;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
}

export class WebSocketClient {
  private ws: WebSocket | null = null;
  private readonly url: string;
  private readonly reconnect: boolean;
  private readonly reconnectInterval: number;
  private readonly maxReconnectAttempts: number;
  private reconnectAttempts: number = 0;
  private subscriptions: Map<string, Set<(data: any) => void>> = new Map();
  private isConnecting: boolean = false;
  private reconnectTimeout: NodeJS.Timeout | null = null;

  constructor(config: WebSocketClientConfig) {
    this.url = config.url;
    this.reconnect = config.reconnect !== false;
    this.reconnectInterval = config.reconnectInterval || 5000;
    this.maxReconnectAttempts = config.maxReconnectAttempts || 5;
  }

  public async connect(): Promise<void> {
    if (this.ws?.readyState === WebSocket.OPEN || this.isConnecting) {
      return;
    }

    this.isConnecting = true;

    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(this.url);

        this.ws.on('open', () => {
          this.isConnecting = false;
          this.reconnectAttempts = 0;
          this.resubscribeAll();
          resolve();
        });

        this.ws.on('message', (data: WebSocket.Data) => {
          try {
            const event: WebSocketEvent = JSON.parse(data.toString());
            this.handleEvent(event);
          } catch (error) {
            console.error('Failed to parse WebSocket message:', error);
          }
        });

        this.ws.on('error', (error: Error) => {
          this.isConnecting = false;
          console.error('WebSocket error:', error);
        });

        this.ws.on('close', () => {
          this.isConnecting = false;
          this.ws = null;
          if (this.reconnect && this.reconnectAttempts < this.maxReconnectAttempts) {
            this.scheduleReconnect();
          }
        });
      } catch (error) {
        this.isConnecting = false;
        reject(new WebSocketError('Failed to connect to WebSocket', { originalError: error }));
      }
    });
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
    }

    this.reconnectAttempts++;
    const delay = this.reconnectInterval * Math.pow(2, this.reconnectAttempts - 1);

    this.reconnectTimeout = setTimeout(() => {
      this.connect().catch((error) => {
        console.error('Reconnection failed:', error);
      });
    }, delay);
  }

  private handleEvent(event: WebSocketEvent): void {
    const callbacks = this.subscriptions.get(event.type);
    if (callbacks) {
      callbacks.forEach((callback) => {
        try {
          callback(event.data);
        } catch (error) {
          console.error(`Error in event handler for ${event.type}:`, error);
        }
      });
    }
  }

  public subscribe(event: string, callback: (data: any) => void): () => void {
    if (!this.subscriptions.has(event)) {
      this.subscriptions.set(event, new Set());
    }

    const callbacks = this.subscriptions.get(event)!;
    callbacks.add(callback);

    // Send subscription message to server if connected
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.sendSubscription(event);
    }

    // Return unsubscribe function
    return () => {
      callbacks.delete(callback);
      if (callbacks.size === 0) {
        this.subscriptions.delete(event);
        if (this.ws?.readyState === WebSocket.OPEN) {
          this.sendUnsubscription(event);
        }
      }
    };
  }

  private sendSubscription(event: string): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(
        JSON.stringify({
          action: 'subscribe',
          event,
        })
      );
    }
  }

  private sendUnsubscription(event: string): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(
        JSON.stringify({
          action: 'unsubscribe',
          event,
        })
      );
    }
  }

  private resubscribeAll(): void {
    this.subscriptions.forEach((_, event) => {
      this.sendSubscription(event);
    });
  }

  public disconnect(): void {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }

    this.subscriptions.clear();
    this.reconnectAttempts = 0;
  }

  public isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}
