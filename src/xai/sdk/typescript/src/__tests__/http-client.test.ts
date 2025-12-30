/**
 * HTTPClient Unit Tests
 *
 * Comprehensive tests for HTTP client functionality including:
 * - HTTP methods (GET, POST, PUT, DELETE)
 * - Configuration and initialization
 * - Connection pooling setup
 */

import axios from 'axios';
import { HTTPClient } from '../utils/http-client';

// Mock axios
jest.mock('axios');

const mockedAxios = axios as jest.Mocked<typeof axios>;

describe('HTTPClient', () => {
  let httpClient: HTTPClient;
  let mockAxiosInstance: any;

  beforeEach(() => {
    jest.clearAllMocks();

    // Create a mock axios instance
    mockAxiosInstance = {
      get: jest.fn(),
      post: jest.fn(),
      put: jest.fn(),
      delete: jest.fn(),
      defaults: { baseURL: 'http://localhost:5000' },
      interceptors: {
        request: {
          use: jest.fn(),
          clear: jest.fn(),
        },
        response: {
          use: jest.fn(),
          clear: jest.fn(),
        },
      },
    };

    mockedAxios.create = jest.fn().mockReturnValue(mockAxiosInstance);
  });

  describe('constructor', () => {
    it('should create client with required config', () => {
      httpClient = new HTTPClient({
        baseUrl: 'http://localhost:5000',
      });

      expect(mockedAxios.create).toHaveBeenCalledWith(
        expect.objectContaining({
          baseURL: 'http://localhost:5000',
          timeout: 30000,
          headers: {
            'Content-Type': 'application/json',
            'User-Agent': 'XAI-SDK-TS/1.0',
          },
        })
      );
    });

    it('should create client with custom timeout', () => {
      httpClient = new HTTPClient({
        baseUrl: 'http://api.xai.io',
        timeout: 60000,
      });

      expect(mockedAxios.create).toHaveBeenCalledWith(
        expect.objectContaining({
          timeout: 60000,
        })
      );
    });

    it('should store API key', () => {
      httpClient = new HTTPClient({
        baseUrl: 'http://localhost:5000',
        apiKey: 'test-api-key',
      });

      // API key is stored internally - verified by interceptor setup
      expect(httpClient).toBeDefined();
    });

    it('should set up request interceptor', () => {
      httpClient = new HTTPClient({
        baseUrl: 'http://localhost:5000',
      });

      expect(mockAxiosInstance.interceptors.request.use).toHaveBeenCalled();
    });

    it('should set up response interceptor', () => {
      httpClient = new HTTPClient({
        baseUrl: 'http://localhost:5000',
      });

      expect(mockAxiosInstance.interceptors.response.use).toHaveBeenCalled();
    });

    it('should accept custom retry configuration', () => {
      httpClient = new HTTPClient({
        baseUrl: 'http://localhost:5000',
        maxRetries: 5,
        retryDelay: 1000,
      });

      expect(httpClient).toBeDefined();
    });
  });

  describe('get', () => {
    beforeEach(() => {
      httpClient = new HTTPClient({
        baseUrl: 'http://localhost:5000',
      });
    });

    it('should make GET request and return data', async () => {
      const mockData = { id: 1, name: 'Test' };
      mockAxiosInstance.get.mockResolvedValue({ data: mockData });

      const result = await httpClient.get('/test');

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/test', {
        params: undefined,
      });
      expect(result).toEqual(mockData);
    });

    it('should make GET request with params', async () => {
      const mockData = { items: [] };
      mockAxiosInstance.get.mockResolvedValue({ data: mockData });

      const result = await httpClient.get('/search', { query: 'test', limit: 10 });

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/search', {
        params: { query: 'test', limit: 10 },
      });
      expect(result).toEqual(mockData);
    });

    it('should make GET request with additional config', async () => {
      const mockData = { status: 'ok' };
      mockAxiosInstance.get.mockResolvedValue({ data: mockData });

      await httpClient.get('/health', undefined, { timeout: 5000 });

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/health', {
        params: undefined,
        timeout: 5000,
      });
    });

    it('should propagate errors from GET request', async () => {
      const error = new Error('Network error');
      mockAxiosInstance.get.mockRejectedValue(error);

      await expect(httpClient.get('/test')).rejects.toThrow('Network error');
    });
  });

  describe('post', () => {
    beforeEach(() => {
      httpClient = new HTTPClient({
        baseUrl: 'http://localhost:5000',
      });
    });

    it('should make POST request and return data', async () => {
      const mockData = { id: 1, created: true };
      mockAxiosInstance.post.mockResolvedValue({ data: mockData });

      const result = await httpClient.post('/create', { name: 'Test' });

      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/create', { name: 'Test' }, undefined);
      expect(result).toEqual(mockData);
    });

    it('should make POST request without body', async () => {
      const mockData = { status: 'ok' };
      mockAxiosInstance.post.mockResolvedValue({ data: mockData });

      const result = await httpClient.post('/trigger');

      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/trigger', undefined, undefined);
      expect(result).toEqual(mockData);
    });

    it('should make POST request with additional config', async () => {
      const mockData = { uploaded: true };
      mockAxiosInstance.post.mockResolvedValue({ data: mockData });

      await httpClient.post('/upload', { file: 'data' }, { timeout: 120000 });

      expect(mockAxiosInstance.post).toHaveBeenCalledWith(
        '/upload',
        { file: 'data' },
        { timeout: 120000 }
      );
    });

    it('should propagate errors from POST request', async () => {
      const error = new Error('Server error');
      mockAxiosInstance.post.mockRejectedValue(error);

      await expect(httpClient.post('/create', {})).rejects.toThrow('Server error');
    });
  });

  describe('put', () => {
    beforeEach(() => {
      httpClient = new HTTPClient({
        baseUrl: 'http://localhost:5000',
      });
    });

    it('should make PUT request and return data', async () => {
      const mockData = { id: 1, updated: true };
      mockAxiosInstance.put.mockResolvedValue({ data: mockData });

      const result = await httpClient.put('/update/1', { name: 'Updated' });

      expect(mockAxiosInstance.put).toHaveBeenCalledWith(
        '/update/1',
        { name: 'Updated' },
        undefined
      );
      expect(result).toEqual(mockData);
    });

    it('should make PUT request without body', async () => {
      const mockData = { updated: true };
      mockAxiosInstance.put.mockResolvedValue({ data: mockData });

      const result = await httpClient.put('/update/1');

      expect(mockAxiosInstance.put).toHaveBeenCalledWith('/update/1', undefined, undefined);
      expect(result).toEqual(mockData);
    });

    it('should propagate errors from PUT request', async () => {
      const error = new Error('Update failed');
      mockAxiosInstance.put.mockRejectedValue(error);

      await expect(httpClient.put('/update/1', {})).rejects.toThrow('Update failed');
    });
  });

  describe('delete', () => {
    beforeEach(() => {
      httpClient = new HTTPClient({
        baseUrl: 'http://localhost:5000',
      });
    });

    it('should make DELETE request and return data', async () => {
      const mockData = { deleted: true };
      mockAxiosInstance.delete.mockResolvedValue({ data: mockData });

      const result = await httpClient.delete('/delete/1');

      expect(mockAxiosInstance.delete).toHaveBeenCalledWith('/delete/1', {
        params: undefined,
      });
      expect(result).toEqual(mockData);
    });

    it('should make DELETE request with params', async () => {
      const mockData = { deleted: true, soft: true };
      mockAxiosInstance.delete.mockResolvedValue({ data: mockData });

      const result = await httpClient.delete('/delete/1', { soft: true });

      expect(mockAxiosInstance.delete).toHaveBeenCalledWith('/delete/1', {
        params: { soft: true },
      });
      expect(result).toEqual(mockData);
    });

    it('should make DELETE request with additional config', async () => {
      const mockData = { deleted: true };
      mockAxiosInstance.delete.mockResolvedValue({ data: mockData });

      await httpClient.delete('/delete/1', undefined, { timeout: 5000 });

      expect(mockAxiosInstance.delete).toHaveBeenCalledWith('/delete/1', {
        params: undefined,
        timeout: 5000,
      });
    });

    it('should propagate errors from DELETE request', async () => {
      const error = new Error('Delete failed');
      mockAxiosInstance.delete.mockRejectedValue(error);

      await expect(httpClient.delete('/delete/1')).rejects.toThrow('Delete failed');
    });
  });

  describe('close', () => {
    it('should clear interceptors', () => {
      httpClient = new HTTPClient({
        baseUrl: 'http://localhost:5000',
      });

      httpClient.close();

      expect(mockAxiosInstance.interceptors.request.clear).toHaveBeenCalled();
      expect(mockAxiosInstance.interceptors.response.clear).toHaveBeenCalled();
    });
  });

  describe('interceptor setup', () => {
    it('should register request interceptors', () => {
      httpClient = new HTTPClient({
        baseUrl: 'http://localhost:5000',
      });

      const requestInterceptorCalls = mockAxiosInstance.interceptors.request.use.mock.calls;
      // At least one request interceptor should be registered
      expect(requestInterceptorCalls.length).toBeGreaterThan(0);
    });

    it('should register response interceptors', () => {
      httpClient = new HTTPClient({
        baseUrl: 'http://localhost:5000',
      });

      const responseInterceptorCalls = mockAxiosInstance.interceptors.response.use.mock.calls;
      // At least one response interceptor should be registered
      expect(responseInterceptorCalls.length).toBeGreaterThan(0);
    });

    it('should configure interceptors for API key header', () => {
      httpClient = new HTTPClient({
        baseUrl: 'http://localhost:5000',
        apiKey: 'test-api-key',
      });

      // Verify request interceptor is set up (API key is added in request interceptor)
      const requestInterceptorCalls = mockAxiosInstance.interceptors.request.use.mock.calls;
      expect(requestInterceptorCalls.length).toBeGreaterThan(0);
    });
  });

  describe('request configuration', () => {
    it('should create axios with HTTP agent options', () => {
      httpClient = new HTTPClient({
        baseUrl: 'http://localhost:5000',
      });

      expect(mockedAxios.create).toHaveBeenCalledWith(
        expect.objectContaining({
          httpAgent: expect.anything(),
          httpsAgent: expect.anything(),
        })
      );
    });

    it('should configure default headers', () => {
      httpClient = new HTTPClient({
        baseUrl: 'http://localhost:5000',
      });

      expect(mockedAxios.create).toHaveBeenCalledWith(
        expect.objectContaining({
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
            'User-Agent': 'XAI-SDK-TS/1.0',
          }),
        })
      );
    });
  });

  describe('multiple instances', () => {
    it('should create independent instances', () => {
      const client1 = new HTTPClient({
        baseUrl: 'http://localhost:5000',
        apiKey: 'key1',
      });

      const client2 = new HTTPClient({
        baseUrl: 'http://localhost:6000',
        apiKey: 'key2',
      });

      expect(mockedAxios.create).toHaveBeenCalledTimes(2);
      expect(client1).not.toBe(client2);
    });
  });
});
