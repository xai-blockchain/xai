/**
 * WebSocketClient Unit Tests
 *
 * Comprehensive tests for WebSocket client functionality including:
 * - Connection management
 * - Event handling
 * - Message parsing
 * - Reconnection logic
 * - Subscription management
 * - Error handling
 */

import WebSocket from 'ws';
import { WebSocketClient } from '../utils/websocket-client';
import { WebSocketError } from '../errors';
import { WebSocketEventType } from '../types';

// Mock ws module
jest.mock('ws');

const MockWebSocket = WebSocket as jest.MockedClass<typeof WebSocket>;

describe('WebSocketClient', () => {
  let wsClient: WebSocketClient;
  let mockWs: any;

  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();

    // Create a mock WebSocket instance
    mockWs = {
      on: jest.fn(),
      send: jest.fn(),
      close: jest.fn(),
      ping: jest.fn(),
      readyState: WebSocket.OPEN,
    };

    MockWebSocket.mockImplementation(() => mockWs);
  });

  afterEach(() => {
    jest.useRealTimers();
    if (wsClient) {
      wsClient.disconnect();
    }
  });

  describe('constructor', () => {
    it('should create client with required config', () => {
      wsClient = new WebSocketClient({
        url: 'ws://localhost:5000/ws',
      });

      expect(wsClient).toBeDefined();
    });

    it('should create client with optional config', () => {
      wsClient = new WebSocketClient({
        url: 'ws://localhost:5000/ws',
        apiKey: 'test-key',
        reconnectInterval: 10000,
        maxReconnectAttempts: 5,
      });

      expect(wsClient).toBeDefined();
    });
  });

  describe('connect', () => {
    beforeEach(() => {
      wsClient = new WebSocketClient({
        url: 'ws://localhost:5000/ws',
      });
    });

    it('should create WebSocket connection', () => {
      wsClient.connect();

      expect(MockWebSocket).toHaveBeenCalledWith('ws://localhost:5000/ws', {
        headers: {
          'User-Agent': 'XAI-SDK-TS/1.0',
        },
      });
    });

    it('should include API key in headers when provided', () => {
      wsClient = new WebSocketClient({
        url: 'ws://localhost:5000/ws',
        apiKey: 'my-api-key',
      });

      wsClient.connect();

      expect(MockWebSocket).toHaveBeenCalledWith('ws://localhost:5000/ws', {
        headers: {
          'User-Agent': 'XAI-SDK-TS/1.0',
          'X-API-Key': 'my-api-key',
        },
      });
    });

    it('should not reconnect if already connected', () => {
      mockWs.readyState = WebSocket.OPEN;

      wsClient.connect();
      wsClient.connect();

      // Should only create one connection
      expect(MockWebSocket).toHaveBeenCalledTimes(1);
    });

    it('should set up event handlers', () => {
      wsClient.connect();

      expect(mockWs.on).toHaveBeenCalledWith('open', expect.any(Function));
      expect(mockWs.on).toHaveBeenCalledWith('message', expect.any(Function));
      expect(mockWs.on).toHaveBeenCalledWith('close', expect.any(Function));
      expect(mockWs.on).toHaveBeenCalledWith('error', expect.any(Function));
      expect(mockWs.on).toHaveBeenCalledWith('pong', expect.any(Function));
    });
  });

  describe('event handling', () => {
    let openHandler: Function;
    let messageHandler: Function;
    let closeHandler: Function;
    let errorHandler: Function;

    beforeEach(() => {
      wsClient = new WebSocketClient({
        url: 'ws://localhost:5000/ws',
      });

      mockWs.on = jest.fn((event: string, handler: Function) => {
        switch (event) {
          case 'open':
            openHandler = handler;
            break;
          case 'message':
            messageHandler = handler;
            break;
          case 'close':
            closeHandler = handler;
            break;
          case 'error':
            errorHandler = handler;
            break;
        }
      });

      wsClient.connect();
    });

    it('should emit connected event on open', () => {
      const connectedListener = jest.fn();
      wsClient.on('connected', connectedListener);

      openHandler();

      expect(connectedListener).toHaveBeenCalled();
    });

    it('should start heartbeat on open', () => {
      openHandler();

      jest.advanceTimersByTime(30000);

      expect(mockWs.ping).toHaveBeenCalled();
    });

    it('should emit message event with parsed data', () => {
      const messageListener = jest.fn();
      wsClient.on('message', messageListener);

      const testMessage = {
        type: 'new_block',
        data: { number: 1000 },
      };

      messageHandler(JSON.stringify(testMessage));

      expect(messageListener).toHaveBeenCalledWith(testMessage);
    });

    it('should emit event type with data', () => {
      const blockListener = jest.fn();
      wsClient.on('new_block', blockListener);

      const testMessage = {
        type: 'new_block',
        data: { number: 1000, hash: '0xabc' },
      };

      messageHandler(JSON.stringify(testMessage));

      expect(blockListener).toHaveBeenCalledWith({ number: 1000, hash: '0xabc' });
    });

    it('should emit error on invalid JSON', () => {
      const errorListener = jest.fn();
      wsClient.on('error', errorListener);

      messageHandler('invalid json {{{');

      expect(errorListener).toHaveBeenCalledWith(expect.any(WebSocketError));
    });

    it('should emit disconnected event on close', () => {
      const disconnectedListener = jest.fn();
      wsClient.on('disconnected', disconnectedListener);

      closeHandler(1000, 'Normal closure');

      expect(disconnectedListener).toHaveBeenCalledWith({
        code: 1000,
        reason: 'Normal closure',
      });
    });

    it('should emit error on WebSocket error', () => {
      const errorListener = jest.fn();
      wsClient.on('error', errorListener);

      const wsError = new Error('Connection failed');
      errorHandler(wsError);

      expect(errorListener).toHaveBeenCalledWith(expect.any(WebSocketError));
    });
  });

  describe('reconnection', () => {
    let closeHandler: Function;

    beforeEach(() => {
      wsClient = new WebSocketClient({
        url: 'ws://localhost:5000/ws',
        reconnectInterval: 1000,
        maxReconnectAttempts: 3,
      });

      mockWs.on = jest.fn((event: string, handler: Function) => {
        if (event === 'close') {
          closeHandler = handler;
        }
      });

      wsClient.connect();
    });

    it('should schedule reconnect on unexpected close', () => {
      const reconnectingListener = jest.fn();
      wsClient.on('reconnecting', reconnectingListener);

      closeHandler(1006, 'Abnormal closure');

      expect(reconnectingListener).toHaveBeenCalledWith({
        attempt: 1,
        maxAttempts: 3,
        delay: 1000,
      });
    });

    it('should use exponential backoff for reconnection', () => {
      const reconnectingListener = jest.fn();
      wsClient.on('reconnecting', reconnectingListener);

      // First close
      closeHandler(1006, 'Abnormal closure');
      expect(reconnectingListener).toHaveBeenLastCalledWith({
        attempt: 1,
        maxAttempts: 3,
        delay: 1000,
      });

      // Advance timer and trigger reconnect
      jest.advanceTimersByTime(1000);

      // Mock new connection fails
      closeHandler(1006, 'Abnormal closure');
      expect(reconnectingListener).toHaveBeenLastCalledWith({
        attempt: 2,
        maxAttempts: 3,
        delay: 2000,
      });
    });

    it('should emit error when max reconnect attempts reached', () => {
      const errorListener = jest.fn();
      wsClient.on('error', errorListener);

      // Simulate 3 failed reconnect attempts
      closeHandler(1006, 'Abnormal closure');
      jest.advanceTimersByTime(1000);
      closeHandler(1006, 'Abnormal closure');
      jest.advanceTimersByTime(2000);
      closeHandler(1006, 'Abnormal closure');
      jest.advanceTimersByTime(4000);
      closeHandler(1006, 'Abnormal closure');

      expect(errorListener).toHaveBeenCalledWith(
        expect.objectContaining({
          message: expect.stringContaining('Max reconnection attempts'),
        })
      );
    });

    it('should not reconnect on intentional close', () => {
      const reconnectingListener = jest.fn();
      wsClient.on('reconnecting', reconnectingListener);

      wsClient.disconnect();
      closeHandler(1000, 'Normal closure');

      expect(reconnectingListener).not.toHaveBeenCalled();
    });
  });

  describe('subscribe', () => {
    beforeEach(() => {
      wsClient = new WebSocketClient({
        url: 'ws://localhost:5000/ws',
      });
      wsClient.connect();
    });

    it('should send subscribe message', () => {
      wsClient.subscribe(WebSocketEventType.NEW_BLOCK);

      expect(mockWs.send).toHaveBeenCalledWith(
        JSON.stringify({
          action: 'subscribe',
          event: WebSocketEventType.NEW_BLOCK,
        })
      );
    });

    it('should throw error if not connected', () => {
      mockWs.readyState = WebSocket.CLOSED;

      expect(() => wsClient.subscribe(WebSocketEventType.NEW_BLOCK)).toThrow(WebSocketError);
      expect(() => wsClient.subscribe(WebSocketEventType.NEW_BLOCK)).toThrow(
        'WebSocket is not connected'
      );
    });
  });

  describe('unsubscribe', () => {
    beforeEach(() => {
      wsClient = new WebSocketClient({
        url: 'ws://localhost:5000/ws',
      });
      wsClient.connect();
    });

    it('should send unsubscribe message', () => {
      wsClient.unsubscribe(WebSocketEventType.NEW_TRANSACTION);

      expect(mockWs.send).toHaveBeenCalledWith(
        JSON.stringify({
          action: 'unsubscribe',
          event: WebSocketEventType.NEW_TRANSACTION,
        })
      );
    });
  });

  describe('send', () => {
    beforeEach(() => {
      wsClient = new WebSocketClient({
        url: 'ws://localhost:5000/ws',
      });
      wsClient.connect();
    });

    it('should send message as JSON', () => {
      const message = { type: 'custom', data: { key: 'value' } };
      wsClient.send(message);

      expect(mockWs.send).toHaveBeenCalledWith(JSON.stringify(message));
    });

    it('should throw error if not connected', () => {
      mockWs.readyState = WebSocket.CLOSED;

      expect(() => wsClient.send({ test: 'data' })).toThrow(WebSocketError);
      expect(() => wsClient.send({ test: 'data' })).toThrow('WebSocket is not connected');
    });

    it('should throw error if send fails', () => {
      mockWs.send.mockImplementation(() => {
        throw new Error('Send failed');
      });

      expect(() => wsClient.send({ test: 'data' })).toThrow(WebSocketError);
      expect(() => wsClient.send({ test: 'data' })).toThrow('Failed to send message');
    });
  });

  describe('disconnect', () => {
    beforeEach(() => {
      wsClient = new WebSocketClient({
        url: 'ws://localhost:5000/ws',
      });
      wsClient.connect();
    });

    it('should close WebSocket connection', () => {
      wsClient.disconnect();

      expect(mockWs.close).toHaveBeenCalled();
    });

    it('should clear heartbeat interval', () => {
      // Trigger open to start heartbeat
      const openHandler = mockWs.on.mock.calls.find((call: any) => call[0] === 'open')[1];
      openHandler();

      wsClient.disconnect();

      // Advance timer - ping should not be called
      jest.advanceTimersByTime(30000);
      expect(mockWs.ping).not.toHaveBeenCalled();
    });

    it('should clear reconnect timeout', () => {
      // Trigger close to start reconnection timer
      const closeHandler = mockWs.on.mock.calls.find((call: any) => call[0] === 'close')[1];
      closeHandler(1006, 'Abnormal closure');

      wsClient.disconnect();

      // Advance timer - should not reconnect
      jest.advanceTimersByTime(10000);
      expect(MockWebSocket).toHaveBeenCalledTimes(1); // Only initial connection
    });

    it('should handle disconnect when not connected', () => {
      wsClient = new WebSocketClient({
        url: 'ws://localhost:5000/ws',
      });

      // Should not throw
      expect(() => wsClient.disconnect()).not.toThrow();
    });
  });

  describe('isConnected', () => {
    beforeEach(() => {
      wsClient = new WebSocketClient({
        url: 'ws://localhost:5000/ws',
      });
    });

    it('should return false when not connected', () => {
      expect(wsClient.isConnected()).toBe(false);
    });

    it('should return true when connected', () => {
      wsClient.connect();
      mockWs.readyState = WebSocket.OPEN;

      expect(wsClient.isConnected()).toBe(true);
    });

    it('should return false when connection is closed', () => {
      wsClient.connect();
      mockWs.readyState = WebSocket.CLOSED;

      expect(wsClient.isConnected()).toBe(false);
    });
  });

  describe('getReadyState', () => {
    beforeEach(() => {
      wsClient = new WebSocketClient({
        url: 'ws://localhost:5000/ws',
      });
    });

    it('should return undefined when not connected', () => {
      expect(wsClient.getReadyState()).toBeUndefined();
    });

    it('should return WebSocket ready state', () => {
      wsClient.connect();
      mockWs.readyState = WebSocket.CONNECTING;

      expect(wsClient.getReadyState()).toBe(WebSocket.CONNECTING);
    });
  });
});
