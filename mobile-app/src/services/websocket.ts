import { API_CONFIG } from '@/constants';
import { Transaction, Block } from '@/types';

type WebSocketEventType = 'transaction' | 'block' | 'balance' | 'error' | 'connected' | 'disconnected';

type WebSocketListener = (data: any) => void;

class WebSocketService {
  private ws: WebSocket | null = null;
  private url: string;
  private reconnectAttempts: number = 0;
  private maxReconnectAttempts: number = 5;
  private reconnectDelay: number = 3000;
  private listeners: Map<WebSocketEventType, Set<WebSocketListener>> = new Map();
  private isConnecting: boolean = false;

  constructor(url: string = API_CONFIG.DEFAULT_WS_ENDPOINT) {
    this.url = url;
  }

  /**
   * Connect to WebSocket server
   */
  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN || this.isConnecting) {
      return;
    }

    this.isConnecting = true;

    try {
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        console.log('WebSocket connected');
        this.isConnecting = false;
        this.reconnectAttempts = 0;
        this.emit('connected', {});
      };

      this.ws.onmessage = (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data);
          this.handleMessage(data);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      this.ws.onerror = (error: Event) => {
        console.error('WebSocket error:', error);
        this.emit('error', error);
      };

      this.ws.onclose = () => {
        console.log('WebSocket disconnected');
        this.isConnecting = false;
        this.emit('disconnected', {});
        this.reconnect();
      };
    } catch (error) {
      console.error('Failed to create WebSocket:', error);
      this.isConnecting = false;
      this.reconnect();
    }
  }

  /**
   * Disconnect from WebSocket server
   */
  disconnect(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.reconnectAttempts = this.maxReconnectAttempts; // Prevent reconnection
  }

  /**
   * Reconnect with exponential backoff
   */
  private reconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.log('Max reconnect attempts reached');
      return;
    }

    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts);
    this.reconnectAttempts++;

    console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);

    setTimeout(() => {
      this.connect();
    }, delay);
  }

  /**
   * Handle incoming message
   */
  private handleMessage(data: any): void {
    const { type, payload } = data;

    switch (type) {
      case 'transaction':
        this.emit('transaction', payload as Transaction);
        break;
      case 'block':
        this.emit('block', payload as Block);
        break;
      case 'balance':
        this.emit('balance', payload);
        break;
      default:
        console.log('Unknown WebSocket message type:', type);
    }
  }

  /**
   * Subscribe to address updates
   */
  subscribeToAddress(address: string): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.send({
        type: 'subscribe',
        address,
      });
    }
  }

  /**
   * Unsubscribe from address updates
   */
  unsubscribeFromAddress(address: string): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.send({
        type: 'unsubscribe',
        address,
      });
    }
  }

  /**
   * Send message to server
   */
  private send(data: any): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    } else {
      console.warn('WebSocket not connected, cannot send message');
    }
  }

  /**
   * Add event listener
   */
  on(event: WebSocketEventType, listener: WebSocketListener): () => void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event)!.add(listener);

    // Return unsubscribe function
    return () => {
      this.off(event, listener);
    };
  }

  /**
   * Remove event listener
   */
  off(event: WebSocketEventType, listener: WebSocketListener): void {
    const listeners = this.listeners.get(event);
    if (listeners) {
      listeners.delete(listener);
    }
  }

  /**
   * Emit event to listeners
   */
  private emit(event: WebSocketEventType, data: any): void {
    const listeners = this.listeners.get(event);
    if (listeners) {
      listeners.forEach(listener => listener(data));
    }
  }

  /**
   * Check if connected
   */
  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  /**
   * Update WebSocket URL
   */
  setURL(url: string): void {
    const wasConnected = this.isConnected();
    this.disconnect();
    this.url = url;
    if (wasConnected) {
      this.connect();
    }
  }
}

export default new WebSocketService();
