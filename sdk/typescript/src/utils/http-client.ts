/**
 * HTTP Client with Retry Logic
 * Handles all HTTP communication with the XAI blockchain node
 */

import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse, AxiosError } from 'axios';
import axiosRetry from 'axios-retry';
import {
  XAIError,
  NetworkError,
  ValidationError,
  AuthenticationError,
  NotFoundError,
  TimeoutError,
  RateLimitError,
} from '../errors';

export interface HTTPClientConfig {
  baseUrl: string;
  timeout?: number;
  retries?: number;
  retryDelay?: number;
  apiKey?: string;
}

export class HTTPClient {
  private client: AxiosInstance;
  private readonly baseUrl: string;

  constructor(config: HTTPClientConfig) {
    this.baseUrl = config.baseUrl;

    this.client = axios.create({
      baseURL: config.baseUrl,
      timeout: config.timeout || 30000,
      headers: {
        'Content-Type': 'application/json',
        ...(config.apiKey && { 'X-API-Key': config.apiKey }),
      },
    });

    // Configure automatic retries with exponential backoff
    axiosRetry(this.client, {
      retries: config.retries || 3,
      retryDelay: (retryCount) => {
        const baseDelay = config.retryDelay || 1000;
        return baseDelay * Math.pow(2, retryCount - 1);
      },
      retryCondition: (error) => {
        return (
          axiosRetry.isNetworkOrIdempotentRequestError(error) ||
          error.response?.status === 429 ||
          error.response?.status === 503
        );
      },
    });

    // Add response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        throw this.handleError(error);
      }
    );
  }

  private handleError(error: AxiosError): Error {
    if (error.response) {
      const status = error.response.status;
      const data = error.response.data as any;
      const message = data?.error || data?.message || error.message;

      switch (status) {
        case 400:
          return new ValidationError(message, data);
        case 401:
        case 403:
          return new AuthenticationError(message);
        case 404:
          return new NotFoundError(message);
        case 408:
          return new TimeoutError(message);
        case 429:
          return new RateLimitError(message);
        default:
          return new XAIError(message, data?.code, status, data);
      }
    } else if (error.code === 'ECONNABORTED') {
      return new TimeoutError('Request timeout');
    } else if (error.request) {
      return new NetworkError('No response from server', { originalError: error });
    } else {
      return new NetworkError(error.message, { originalError: error });
    }
  }

  public async get<T = any>(path: string, config?: AxiosRequestConfig): Promise<T> {
    const response: AxiosResponse<T> = await this.client.get(path, config);
    return response.data;
  }

  public async post<T = any>(path: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    const response: AxiosResponse<T> = await this.client.post(path, data, config);
    return response.data;
  }

  public async put<T = any>(path: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    const response: AxiosResponse<T> = await this.client.put(path, data, config);
    return response.data;
  }

  public async delete<T = any>(path: string, config?: AxiosRequestConfig): Promise<T> {
    const response: AxiosResponse<T> = await this.client.delete(path, config);
    return response.data;
  }

  public getBaseUrl(): string {
    return this.baseUrl;
  }
}
