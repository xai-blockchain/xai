// Secure API Client
import config from './config.js';
import { CSRF, RateLimiter } from './security.js';

class APIClient {
  constructor() {
    this.baseURL = config.API_BASE_URL;
    this.rateLimiter = new RateLimiter(config.MAX_API_CALLS_PER_MINUTE);
    this.authToken = null;
  }

  setAuthToken(token) {
    this.authToken = token;
  }

  clearAuthToken() {
    this.authToken = null;
  }

  getHeaders(includeAuth = true) {
    const headers = {
      'Content-Type': 'application/json',
    };

    // Add CSRF token if enabled
    if (config.CSRF_ENABLED) {
      const csrfToken = CSRF.getToken();
      if (csrfToken) {
        headers[CSRF.TOKEN_HEADER] = csrfToken;
      }
    }

    // Add authorization token if available
    if (includeAuth && this.authToken) {
      headers['Authorization'] = `Bearer ${this.authToken}`;
    }

    return headers;
  }

  async request(endpoint, options = {}) {
    // Check rate limit
    if (!this.rateLimiter.canMakeRequest()) {
      const resetTime = this.rateLimiter.getResetTime();
      const waitTime = Math.ceil((resetTime - Date.now()) / 1000);
      throw new Error(`Rate limit exceeded. Try again in ${waitTime} seconds.`);
    }

    const url = `${this.baseURL}${endpoint}`;
    const requestOptions = {
      ...options,
      headers: {
        ...this.getHeaders(options.includeAuth !== false),
        ...options.headers,
      },
    };

    try {
      const response = await fetch(url, requestOptions);

      // Update CSRF token if provided in response
      if (config.CSRF_ENABLED) {
        const newCsrfToken = response.headers.get(CSRF.TOKEN_HEADER);
        if (newCsrfToken) {
          CSRF.setToken(newCsrfToken);
        }
      }

      // Handle error responses
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new APIError(
          errorData.error || errorData.message || 'Request failed',
          response.status,
          errorData
        );
      }

      return await response.json();
    } catch (error) {
      if (error instanceof APIError) {
        throw error;
      }

      // Network or other errors
      throw new APIError(error.message || 'Network error occurred', 0, { originalError: error });
    }
  }

  async get(endpoint, options = {}) {
    return this.request(endpoint, { ...options, method: 'GET' });
  }

  async post(endpoint, data, options = {}) {
    return this.request(endpoint, {
      ...options,
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async put(endpoint, data, options = {}) {
    return this.request(endpoint, {
      ...options,
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async delete(endpoint, options = {}) {
    return this.request(endpoint, { ...options, method: 'DELETE' });
  }

  // Authentication endpoints
  async login(username, password) {
    const data = await this.post('/auth/login', { username, password }, { includeAuth: false });
    if (data.token) {
      this.setAuthToken(data.token);
    }
    return data;
  }

  async register(username, password) {
    return this.post('/auth/register', { username, password }, { includeAuth: false });
  }

  async logout() {
    try {
      await this.post('/auth/logout');
    } finally {
      this.clearAuthToken();
    }
  }

  // Wallet endpoints
  async getBalance() {
    return this.get('/wallet/balance');
  }

  // Order endpoints
  async getOrderBook() {
    return this.get('/orders/book');
  }

  async createOrder(orderType, price, amount) {
    return this.post('/orders/create', {
      order_type: orderType,
      price,
      amount,
    });
  }

  async getUserOrders() {
    return this.get('/orders/user');
  }

  async cancelOrder(orderId) {
    return this.delete(`/orders/${orderId}`);
  }

  // Trade endpoints
  async getRecentTrades(limit = 20) {
    return this.get(`/trades/recent?limit=${limit}`);
  }

  async getUserTrades() {
    return this.get('/trades/user');
  }

  // Health check
  async healthCheck() {
    return this.get('/health', { includeAuth: false });
  }
}

// Custom API Error class
class APIError extends Error {
  constructor(message, statusCode, data = {}) {
    super(message);
    this.name = 'APIError';
    this.statusCode = statusCode;
    this.data = data;
  }

  isAuthError() {
    return this.statusCode === 401 || this.statusCode === 403;
  }

  isRateLimitError() {
    return this.statusCode === 429;
  }

  isServerError() {
    return this.statusCode >= 500;
  }

  isClientError() {
    return this.statusCode >= 400 && this.statusCode < 500;
  }
}

export { APIClient, APIError };
export default new APIClient();
