/**
 * XAI SDK Error Classes
 * Comprehensive error handling for the XAI blockchain SDK
 */

export class XAIError extends Error {
  public readonly code?: string;
  public readonly status?: number;
  public readonly details?: any;

  constructor(message: string, code?: string, status?: number, details?: any) {
    super(message);
    this.name = 'XAIError';
    this.code = code;
    this.status = status;
    this.details = details;
    Object.setPrototypeOf(this, XAIError.prototype);
  }
}

export class NetworkError extends XAIError {
  constructor(message: string, details?: any) {
    super(message, 'NETWORK_ERROR', undefined, details);
    this.name = 'NetworkError';
    Object.setPrototypeOf(this, NetworkError.prototype);
  }
}

export class ValidationError extends XAIError {
  constructor(message: string, details?: any) {
    super(message, 'VALIDATION_ERROR', 400, details);
    this.name = 'ValidationError';
    Object.setPrototypeOf(this, ValidationError.prototype);
  }
}

export class AuthenticationError extends XAIError {
  constructor(message: string = 'Authentication failed') {
    super(message, 'AUTHENTICATION_ERROR', 401);
    this.name = 'AuthenticationError';
    Object.setPrototypeOf(this, AuthenticationError.prototype);
  }
}

export class NotFoundError extends XAIError {
  constructor(resource: string) {
    super(`${resource} not found`, 'NOT_FOUND', 404);
    this.name = 'NotFoundError';
    Object.setPrototypeOf(this, NotFoundError.prototype);
  }
}

export class TransactionError extends XAIError {
  constructor(message: string, details?: any) {
    super(message, 'TRANSACTION_ERROR', undefined, details);
    this.name = 'TransactionError';
    Object.setPrototypeOf(this, TransactionError.prototype);
  }
}

export class WalletError extends XAIError {
  constructor(message: string, details?: any) {
    super(message, 'WALLET_ERROR', undefined, details);
    this.name = 'WalletError';
    Object.setPrototypeOf(this, WalletError.prototype);
  }
}

export class WebSocketError extends XAIError {
  constructor(message: string, details?: any) {
    super(message, 'WEBSOCKET_ERROR', undefined, details);
    this.name = 'WebSocketError';
    Object.setPrototypeOf(this, WebSocketError.prototype);
  }
}

export class TimeoutError extends XAIError {
  constructor(message: string = 'Request timeout') {
    super(message, 'TIMEOUT_ERROR', 408);
    this.name = 'TimeoutError';
    Object.setPrototypeOf(this, TimeoutError.prototype);
  }
}

export class RateLimitError extends XAIError {
  constructor(message: string = 'Rate limit exceeded') {
    super(message, 'RATE_LIMIT_ERROR', 429);
    this.name = 'RateLimitError';
    Object.setPrototypeOf(this, RateLimitError.prototype);
  }
}
