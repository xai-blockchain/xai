/**
 * XAIClient Unit Tests
 *
 * Comprehensive tests for the main XAIClient class including:
 * - Client initialization with various configurations
 * - Sub-client access
 * - WebSocket connection management
 * - Health check and info methods
 * - Error handling
 */

import { XAIClient } from '../client';
import { HTTPClient } from '../utils/http-client';
import { WebSocketClient } from '../utils/websocket-client';

// Mock the dependencies
jest.mock('../utils/http-client');
jest.mock('../utils/websocket-client');

const MockHTTPClient = HTTPClient as jest.MockedClass<typeof HTTPClient>;
const MockWebSocketClient = WebSocketClient as jest.MockedClass<typeof WebSocketClient>;

describe('XAIClient', () => {
  let client: XAIClient;

  beforeEach(() => {
    jest.clearAllMocks();
  });

  afterEach(() => {
    if (client) {
      client.close();
    }
  });

  describe('constructor', () => {
    it('should create client with default configuration', () => {
      client = new XAIClient();

      expect(MockHTTPClient).toHaveBeenCalledWith({
        baseUrl: 'http://localhost:5000',
        apiKey: undefined,
        timeout: 30000,
        maxRetries: 3,
        retryDelay: 500,
      });
    });

    it('should create client with custom configuration', () => {
      client = new XAIClient({
        baseUrl: 'https://api.xai.io',
        apiKey: 'test-api-key',
        timeout: 60000,
        maxRetries: 5,
        retryDelay: 1000,
      });

      expect(MockHTTPClient).toHaveBeenCalledWith({
        baseUrl: 'https://api.xai.io',
        apiKey: 'test-api-key',
        timeout: 60000,
        maxRetries: 5,
        retryDelay: 1000,
      });
    });

    it('should create client with partial configuration', () => {
      client = new XAIClient({
        baseUrl: 'https://custom.xai.io',
        apiKey: 'my-key',
      });

      expect(MockHTTPClient).toHaveBeenCalledWith({
        baseUrl: 'https://custom.xai.io',
        apiKey: 'my-key',
        timeout: 30000,
        maxRetries: 3,
        retryDelay: 500,
      });
    });
  });

  describe('sub-clients', () => {
    beforeEach(() => {
      client = new XAIClient();
    });

    it('should expose wallet client', () => {
      expect(client.wallet).toBeDefined();
    });

    it('should expose transaction client', () => {
      expect(client.transaction).toBeDefined();
    });

    it('should expose blockchain client', () => {
      expect(client.blockchain).toBeDefined();
    });

    it('should expose mining client', () => {
      expect(client.mining).toBeDefined();
    });

    it('should expose governance client', () => {
      expect(client.governance).toBeDefined();
    });

    it('should expose ai client', () => {
      expect(client.ai).toBeDefined();
    });
  });

  describe('WebSocket management', () => {
    beforeEach(() => {
      client = new XAIClient({ baseUrl: 'http://localhost:5000' });
    });

    it('should connect to WebSocket with default URL', () => {
      // Setup mock for HTTP client baseURL
      const mockHttpClient = MockHTTPClient.mock.instances[0];
      (mockHttpClient as any)['client'] = {
        defaults: { baseURL: 'http://localhost:5000' },
      };
      (mockHttpClient as any)['apiKey'] = undefined;

      MockWebSocketClient.prototype.isConnected = jest.fn().mockReturnValue(false);
      MockWebSocketClient.prototype.connect = jest.fn();

      client.connectWebSocket();

      expect(MockWebSocketClient).toHaveBeenCalled();
      expect(MockWebSocketClient.prototype.connect).toHaveBeenCalled();
    });

    it('should connect to WebSocket with custom URL', () => {
      const mockHttpClient = MockHTTPClient.mock.instances[0];
      (mockHttpClient as any)['apiKey'] = 'test-key';

      MockWebSocketClient.prototype.isConnected = jest.fn().mockReturnValue(false);
      MockWebSocketClient.prototype.connect = jest.fn();

      client.connectWebSocket('ws://custom.xai.io/ws');

      expect(MockWebSocketClient).toHaveBeenCalledWith({
        url: 'ws://custom.xai.io/ws',
        apiKey: 'test-key',
      });
    });

    it('should not reconnect if already connected', () => {
      const mockHttpClient = MockHTTPClient.mock.instances[0];
      (mockHttpClient as any)['client'] = {
        defaults: { baseURL: 'http://localhost:5000' },
      };
      (mockHttpClient as any)['apiKey'] = undefined;

      // Initially not connected
      let isConnected = false;
      MockWebSocketClient.prototype.isConnected = jest.fn(() => isConnected);
      MockWebSocketClient.prototype.connect = jest.fn(() => {
        isConnected = true;
      });

      client.connectWebSocket();

      // Try connecting again (should be no-op because already connected)
      client.connectWebSocket();

      // WebSocketClient constructor is called once per connectWebSocket when not connected
      // Since first call connects and sets isConnected to true, second call returns early
      expect(MockWebSocketClient).toHaveBeenCalledTimes(1);
    });

    it('should disconnect WebSocket', () => {
      const mockHttpClient = MockHTTPClient.mock.instances[0];
      (mockHttpClient as any)['client'] = {
        defaults: { baseURL: 'http://localhost:5000' },
      };
      (mockHttpClient as any)['apiKey'] = undefined;

      MockWebSocketClient.prototype.isConnected = jest.fn().mockReturnValue(false);
      MockWebSocketClient.prototype.connect = jest.fn();
      MockWebSocketClient.prototype.disconnect = jest.fn();

      client.connectWebSocket();
      client.disconnectWebSocket();

      expect(MockWebSocketClient.prototype.disconnect).toHaveBeenCalled();
    });

    it('should handle disconnectWebSocket when not connected', () => {
      // Should not throw when called without a connection
      expect(() => client.disconnectWebSocket()).not.toThrow();
    });

    it('should report WebSocket connection status', () => {
      expect(client.isWebSocketConnected()).toBe(false);

      const mockHttpClient = MockHTTPClient.mock.instances[0];
      (mockHttpClient as any)['client'] = {
        defaults: { baseURL: 'http://localhost:5000' },
      };
      (mockHttpClient as any)['apiKey'] = undefined;

      MockWebSocketClient.prototype.isConnected = jest.fn().mockReturnValue(true);
      MockWebSocketClient.prototype.connect = jest.fn();

      client.connectWebSocket();

      expect(client.isWebSocketConnected()).toBe(true);
    });
  });

  describe('event subscription', () => {
    beforeEach(() => {
      client = new XAIClient({ baseUrl: 'http://localhost:5000' });

      const mockHttpClient = MockHTTPClient.mock.instances[0];
      (mockHttpClient as any)['client'] = {
        defaults: { baseURL: 'http://localhost:5000' },
      };
      (mockHttpClient as any)['apiKey'] = undefined;

      MockWebSocketClient.prototype.isConnected = jest.fn().mockReturnValue(false);
      MockWebSocketClient.prototype.connect = jest.fn();
      MockWebSocketClient.prototype.on = jest.fn();
      MockWebSocketClient.prototype.off = jest.fn();
    });

    it('should throw error when subscribing without WebSocket connection', () => {
      const listener = jest.fn();
      expect(() => client.on('new_block', listener)).toThrow(
        'WebSocket not connected. Call connectWebSocket() first.'
      );
    });

    it('should subscribe to events when WebSocket is connected', () => {
      client.connectWebSocket();

      const listener = jest.fn();
      client.on('new_block', listener);

      expect(MockWebSocketClient.prototype.on).toHaveBeenCalledWith('new_block', listener);
    });

    it('should unsubscribe from events', () => {
      client.connectWebSocket();

      const listener = jest.fn();
      client.off('new_block', listener);

      expect(MockWebSocketClient.prototype.off).toHaveBeenCalledWith('new_block', listener);
    });

    it('should handle off() when WebSocket is not connected', () => {
      const listener = jest.fn();
      // Should not throw
      expect(() => client.off('new_block', listener)).not.toThrow();
    });
  });

  describe('healthCheck', () => {
    beforeEach(() => {
      client = new XAIClient();
    });

    it('should call blockchain.getHealth()', async () => {
      const mockResponse = {
        status: 'healthy',
        timestamp: Date.now(),
      };

      client.blockchain.getHealth = jest.fn().mockResolvedValue(mockResponse);

      const result = await client.healthCheck();

      expect(client.blockchain.getHealth).toHaveBeenCalled();
      expect(result).toEqual(mockResponse);
    });

    it('should propagate errors from getHealth', async () => {
      const error = new Error('Health check failed');
      client.blockchain.getHealth = jest.fn().mockRejectedValue(error);

      await expect(client.healthCheck()).rejects.toThrow('Health check failed');
    });
  });

  describe('getInfo', () => {
    beforeEach(() => {
      client = new XAIClient();
    });

    it('should call blockchain.getNodeInfo()', async () => {
      const mockResponse = {
        status: 'running',
        node: 'xai-node',
        version: '1.0.0',
      };

      client.blockchain.getNodeInfo = jest.fn().mockResolvedValue(mockResponse);

      const result = await client.getInfo();

      expect(client.blockchain.getNodeInfo).toHaveBeenCalled();
      expect(result).toEqual(mockResponse);
    });

    it('should propagate errors from getNodeInfo', async () => {
      const error = new Error('Node info failed');
      client.blockchain.getNodeInfo = jest.fn().mockRejectedValue(error);

      await expect(client.getInfo()).rejects.toThrow('Node info failed');
    });
  });

  describe('close', () => {
    it('should close HTTP client and disconnect WebSocket', () => {
      client = new XAIClient();

      const mockHttpClient = MockHTTPClient.mock.instances[0];
      mockHttpClient.close = jest.fn();
      (mockHttpClient as any)['client'] = {
        defaults: { baseURL: 'http://localhost:5000' },
      };
      (mockHttpClient as any)['apiKey'] = undefined;

      MockWebSocketClient.prototype.isConnected = jest.fn().mockReturnValue(false);
      MockWebSocketClient.prototype.connect = jest.fn();
      MockWebSocketClient.prototype.disconnect = jest.fn();

      client.connectWebSocket();
      client.close();

      expect(mockHttpClient.close).toHaveBeenCalled();
      expect(MockWebSocketClient.prototype.disconnect).toHaveBeenCalled();
    });

    it('should handle close without WebSocket connection', () => {
      client = new XAIClient();

      const mockHttpClient = MockHTTPClient.mock.instances[0];
      mockHttpClient.close = jest.fn();

      client.close();

      expect(mockHttpClient.close).toHaveBeenCalled();
    });
  });
});
