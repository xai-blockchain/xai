// Secure WebSocket Client
import config from './config.js';

class WebSocketClient {
  constructor(url = config.WS_URL) {
    this.url = url;
    this.ws = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = config.MAX_WEBSOCKET_RECONNECT_ATTEMPTS;
    this.reconnectTimeout = null;
    this.messageHandlers = new Map();
    this.connectionListeners = new Set();
    this.isManualClose = false;
    this.heartbeatInterval = null;
    this.heartbeatTimeout = null;
    this.missedHeartbeats = 0;
    this.maxMissedHeartbeats = 3;
  }

  connect() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      console.warn('WebSocket already connected');
      return;
    }

    this.isManualClose = false;

    try {
      // Use secure WebSocket if available
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const secureUrl = this.url.replace(/^ws:/, protocol);

      this.ws = new WebSocket(secureUrl);
      this.setupEventHandlers();
    } catch (error) {
      console.error('WebSocket connection error:', error);
      this.handleReconnect();
    }
  }

  setupEventHandlers() {
    if (!this.ws) {return;}

    this.ws.onopen = () => {
      console.log('WebSocket connected');
      this.reconnectAttempts = 0;
      this.missedHeartbeats = 0;
      this.notifyConnectionChange('connected');
      this.startHeartbeat();
    };

    this.ws.onmessage = event => {
      try {
        const data = JSON.parse(event.data);
        this.handleMessage(data);
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    };

    this.ws.onerror = error => {
      console.error('WebSocket error:', error);
      this.notifyConnectionChange('error');
    };

    this.ws.onclose = event => {
      console.log('WebSocket disconnected:', event.code, event.reason);
      this.stopHeartbeat();
      this.notifyConnectionChange('disconnected');

      // Attempt reconnection if not manually closed
      if (!this.isManualClose && this.reconnectAttempts < this.maxReconnectAttempts) {
        this.handleReconnect();
      }
    };
  }

  handleMessage(data) {
    // Handle heartbeat/ping messages
    if (data.type === 'ping') {
      this.send({ type: 'pong' });
      this.missedHeartbeats = 0;
      return;
    }

    if (data.type === 'pong') {
      this.missedHeartbeats = 0;
      return;
    }

    // Route message to registered handlers
    const handlers = this.messageHandlers.get(data.type);
    if (handlers) {
      handlers.forEach(handler => {
        try {
          handler(data.data || data);
        } catch (error) {
          console.error('Error in message handler:', error);
        }
      });
    }

    // Call wildcard handlers
    const wildcardHandlers = this.messageHandlers.get('*');
    if (wildcardHandlers) {
      wildcardHandlers.forEach(handler => {
        try {
          handler(data);
        } catch (error) {
          console.error('Error in wildcard handler:', error);
        }
      });
    }
  }

  handleReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached');
      this.notifyConnectionChange('failed');
      return;
    }

    this.reconnectAttempts++;
    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);

    console.log(`Reconnecting in ${delay}ms... (attempt ${this.reconnectAttempts})`);
    this.notifyConnectionChange('reconnecting');

    this.reconnectTimeout = setTimeout(() => {
      this.connect();
    }, delay);
  }

  startHeartbeat() {
    // Send heartbeat every 30 seconds
    this.heartbeatInterval = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.send({ type: 'ping' });
        this.missedHeartbeats++;

        if (this.missedHeartbeats >= this.maxMissedHeartbeats) {
          console.warn('WebSocket heartbeat timeout, reconnecting...');
          this.close();
          this.connect();
        }
      }
    }, 30000);
  }

  stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
    if (this.heartbeatTimeout) {
      clearTimeout(this.heartbeatTimeout);
      this.heartbeatTimeout = null;
    }
  }

  send(data) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.warn('WebSocket not connected, cannot send message');
      return false;
    }

    try {
      const message = typeof data === 'string' ? data : JSON.stringify(data);
      this.ws.send(message);
      return true;
    } catch (error) {
      console.error('Error sending WebSocket message:', error);
      return false;
    }
  }

  subscribe(channel) {
    return this.send({ type: 'subscribe', channel });
  }

  unsubscribe(channel) {
    return this.send({ type: 'unsubscribe', channel });
  }

  on(messageType, handler) {
    if (!this.messageHandlers.has(messageType)) {
      this.messageHandlers.set(messageType, new Set());
    }
    this.messageHandlers.get(messageType).add(handler);
  }

  off(messageType, handler) {
    const handlers = this.messageHandlers.get(messageType);
    if (handlers) {
      handlers.delete(handler);
      if (handlers.size === 0) {
        this.messageHandlers.delete(messageType);
      }
    }
  }

  onConnectionChange(listener) {
    this.connectionListeners.add(listener);
  }

  offConnectionChange(listener) {
    this.connectionListeners.delete(listener);
  }

  notifyConnectionChange(status) {
    this.connectionListeners.forEach(listener => {
      try {
        listener(status);
      } catch (error) {
        console.error('Error in connection listener:', error);
      }
    });
  }

  close() {
    this.isManualClose = true;
    this.stopHeartbeat();

    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }

    this.messageHandlers.clear();
    this.notifyConnectionChange('disconnected');
  }

  getState() {
    if (!this.ws) {return 'disconnected';}

    switch (this.ws.readyState) {
      case WebSocket.CONNECTING:
        return 'connecting';
      case WebSocket.OPEN:
        return 'connected';
      case WebSocket.CLOSING:
        return 'closing';
      case WebSocket.CLOSED:
        return 'disconnected';
      default:
        return 'unknown';
    }
  }

  isConnected() {
    return this.ws && this.ws.readyState === WebSocket.OPEN;
  }
}

export default WebSocketClient;
