/**
 * HTTP Client Utility
 * Axios-based HTTP client with retry logic and error handling for XAI blockchain API
 */

import axios, { AxiosInstance, AxiosError, AxiosRequestConfig } from 'axios';
import axiosRetry from 'axios-retry';
import { XAIConfig, NetworkError } from '../types';

export class HttpClient {
  private client: AxiosInstance;
  private config: XAIConfig;

  constructor(config: XAIConfig) {
    this.config = {
      timeout: 30000,
      retries: 3,
      retryDelay: 1000,
      ...config,
    };

    this.client = axios.create({
      baseURL: this.config.baseUrl,
      timeout: this.config.timeout,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Configure retry logic
    axiosRetry(this.client, {
      retries: this.config.retries,
      retryDelay: (retryCount) => {
        return retryCount * (this.config.retryDelay || 1000);
      },
      retryCondition: (error: AxiosError) => {
        // Retry on network errors or 5xx server errors
        return (
          axiosRetry.isNetworkOrIdempotentRequestError(error) ||
          (error.response?.status ? error.response.status >= 500 : false)
        );
      },
    });

    // Add response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        throw this.handleError(error);
      }
    );
  }

  private handleError(error: AxiosError): NetworkError {
    if (error.response) {
      // Server responded with error status
      const message =
        (error.response.data as any)?.error ||
        (error.response.data as any)?.message ||
        `Request failed with status ${error.response.status}`;

      return new NetworkError(message, {
        status: error.response.status,
        data: error.response.data,
      });
    } else if (error.request) {
      // Request made but no response received
      return new NetworkError('No response from server', {
        request: error.request,
      });
    } else {
      // Error setting up request
      return new NetworkError(error.message || 'Network request failed');
    }
  }

  async get<T = any>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.get<T>(url, config);
    return response.data;
  }

  async post<T = any>(
    url: string,
    data?: any,
    config?: AxiosRequestConfig
  ): Promise<T> {
    const response = await this.client.post<T>(url, data, config);
    return response.data;
  }

  async put<T = any>(
    url: string,
    data?: any,
    config?: AxiosRequestConfig
  ): Promise<T> {
    const response = await this.client.put<T>(url, data, config);
    return response.data;
  }

  async delete<T = any>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.delete<T>(url, config);
    return response.data;
  }

  updateBaseUrl(baseUrl: string): void {
    this.config.baseUrl = baseUrl;
    this.client.defaults.baseURL = baseUrl;
  }

  getBaseUrl(): string {
    return this.config.baseUrl;
  }
}
