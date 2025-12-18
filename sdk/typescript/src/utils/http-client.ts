/**
 * HTTP Client for XAI SDK
 *
 * Handles all HTTP communication with retry logic, connection pooling,
 * and comprehensive error handling.
 */

import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse, AxiosError } from 'axios';
import axiosRetry from 'axios-retry';
import {
  XAIError,
  AuthenticationError,
  RateLimitError,
  NetworkError,
  TimeoutError,
  NotFoundError,
  ValidationError,
  InternalServerError,
  ServiceUnavailableError,
  AuthorizationError,
  ConflictError,
} from '../errors';

/**
 * HTTP client configuration
 */
export interface HTTPClientConfig {
  baseUrl: string;
  apiKey?: string;
  timeout?: number;
  maxRetries?: number;
  retryDelay?: number;
}

/**
 * HTTP client for making API requests with retry logic and connection pooling
 *
 * Features:
 * - Automatic retry with exponential backoff
 * - Connection pooling via axios keepalive
 * - Rate limit handling
 * - Comprehensive error handling
 * - Request logging (optional)
 */
export class HTTPClient {
  private client: AxiosInstance;
  private apiKey?: string;
  private timeout: number;

  constructor(config: HTTPClientConfig) {
    this.apiKey = config.apiKey;
    this.timeout = config.timeout || 30000;

    // Create axios instance with connection pooling
    this.client = axios.create({
      baseURL: config.baseUrl,
      timeout: this.timeout,
      headers: {
        'Content-Type': 'application/json',
        'User-Agent': 'XAI-SDK-TS/1.0',
      },
      // Enable keep-alive for connection pooling
      httpAgent: this.createHttpAgent(),
      httpsAgent: this.createHttpsAgent(),
    });

    // Setup retry strategy
    this.setupRetryStrategy(config.maxRetries || 3, config.retryDelay || 500);

    // Setup request/response interceptors
    this.setupInterceptors();
  }

  /**
   * Create HTTP agent with keep-alive
   */
  private createHttpAgent(): unknown {
    // Dynamic import for Node.js http module
    try {
      const http = require('http');
      return new http.Agent({
        keepAlive: true,
        keepAliveMsecs: 30000,
        maxSockets: 50,
        maxFreeSockets: 10,
      });
    } catch {
      return undefined;
    }
  }

  /**
   * Create HTTPS agent with keep-alive
   */
  private createHttpsAgent(): unknown {
    // Dynamic import for Node.js https module
    try {
      const https = require('https');
      return new https.Agent({
        keepAlive: true,
        keepAliveMsecs: 30000,
        maxSockets: 50,
        maxFreeSockets: 10,
      });
    } catch {
      return undefined;
    }
  }

  /**
   * Setup retry strategy with exponential backoff
   */
  private setupRetryStrategy(maxRetries: number, retryDelay: number): void {
    axiosRetry(this.client, {
      retries: maxRetries,
      retryDelay: (retryCount) => {
        return retryCount * retryDelay;
      },
      retryCondition: (error: AxiosError) => {
        // Retry on network errors and specific status codes
        if (axiosRetry.isNetworkError(error)) {
          return true;
        }
        if (!error.response) {
          return true;
        }
        const status = error.response.status;
        return status === 429 || status === 500 || status === 502 || status === 503 || status === 504;
      },
      onRetry: (retryCount, error, requestConfig) => {
        console.warn(
          `Retrying request to ${requestConfig.url} (attempt ${retryCount}/${maxRetries})`
        );
      },
    });
  }

  /**
   * Setup request and response interceptors
   */
  private setupInterceptors(): void {
    // Request interceptor
    this.client.interceptors.request.use(
      (config) => {
        // Add API key if available
        if (this.apiKey) {
          config.headers['X-API-Key'] = this.apiKey;
        }
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Response interceptor
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        return Promise.reject(this.handleError(error));
      }
    );
  }

  /**
   * Handle API errors and convert to typed exceptions
   */
  private handleError(error: AxiosError): Error {
    // Network errors
    if (!error.response) {
      if (error.code === 'ECONNABORTED' || error.message.includes('timeout')) {
        return new TimeoutError(`Request timeout after ${this.timeout}ms`);
      }
      return new NetworkError(`Network error: ${error.message}`);
    }

    const response = error.response;
    const data = response.data as { message?: string; error?: string; code?: number };
    const errorMessage = data?.message || data?.error || 'Unknown error';
    const errorCode = data?.code || response.status;

    // Handle specific status codes
    switch (response.status) {
      case 400:
        return new ValidationError(errorMessage, errorCode);
      case 401:
        return new AuthenticationError(errorMessage, errorCode);
      case 403:
        return new AuthorizationError(errorMessage, errorCode);
      case 404:
        return new NotFoundError(errorMessage, errorCode);
      case 409:
        return new ConflictError(errorMessage, errorCode);
      case 429: {
        const retryAfter = response.headers['retry-after'];
        return new RateLimitError(
          errorMessage,
          retryAfter ? parseInt(retryAfter, 10) : undefined,
          errorCode
        );
      }
      case 500:
        return new InternalServerError(errorMessage, errorCode);
      case 503:
        return new ServiceUnavailableError(errorMessage, errorCode);
      default:
        return new XAIError(errorMessage, errorCode);
    }
  }

  /**
   * Make a GET request
   */
  async get<T = unknown>(
    endpoint: string,
    params?: Record<string, unknown>,
    config?: AxiosRequestConfig
  ): Promise<T> {
    const response: AxiosResponse<T> = await this.client.get(endpoint, {
      params,
      ...config,
    });
    return response.data;
  }

  /**
   * Make a POST request
   */
  async post<T = unknown>(
    endpoint: string,
    data?: Record<string, unknown>,
    config?: AxiosRequestConfig
  ): Promise<T> {
    const response: AxiosResponse<T> = await this.client.post(endpoint, data, config);
    return response.data;
  }

  /**
   * Make a PUT request
   */
  async put<T = unknown>(
    endpoint: string,
    data?: Record<string, unknown>,
    config?: AxiosRequestConfig
  ): Promise<T> {
    const response: AxiosResponse<T> = await this.client.put(endpoint, data, config);
    return response.data;
  }

  /**
   * Make a DELETE request
   */
  async delete<T = unknown>(
    endpoint: string,
    params?: Record<string, unknown>,
    config?: AxiosRequestConfig
  ): Promise<T> {
    const response: AxiosResponse<T> = await this.client.delete(endpoint, {
      params,
      ...config,
    });
    return response.data;
  }

  /**
   * Close the HTTP client
   */
  close(): void {
    // Axios doesn't have a close method, but we can clear interceptors
    this.client.interceptors.request.clear();
    this.client.interceptors.response.clear();
  }
}
