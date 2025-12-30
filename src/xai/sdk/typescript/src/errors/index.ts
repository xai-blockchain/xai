/**
 * XAI SDK Error Classes
 *
 * Comprehensive typed error handling for all SDK operations.
 */

/**
 * Base error class for all XAI SDK errors
 */
export class XAIError extends Error {
  public readonly code?: number;
  public readonly errorDetails?: Record<string, unknown>;

  constructor(message: string, code?: number, errorDetails?: Record<string, unknown>) {
    super(message);
    this.name = 'XAIError';
    this.code = code;
    this.errorDetails = errorDetails;
    Object.setPrototypeOf(this, XAIError.prototype);
  }

  toString(): string {
    if (this.code) {
      return `[${this.code}] ${this.message}`;
    }
    return this.message;
  }
}

/**
 * Authentication error - raised when authentication fails
 */
export class AuthenticationError extends XAIError {
  constructor(message: string, code?: number, errorDetails?: Record<string, unknown>) {
    super(message, code, errorDetails);
    this.name = 'AuthenticationError';
    Object.setPrototypeOf(this, AuthenticationError.prototype);
  }
}

/**
 * Authorization error - raised when user lacks required permissions
 */
export class AuthorizationError extends XAIError {
  constructor(message: string, code?: number, errorDetails?: Record<string, unknown>) {
    super(message, code, errorDetails);
    this.name = 'AuthorizationError';
    Object.setPrototypeOf(this, AuthorizationError.prototype);
  }
}

/**
 * Validation error - raised when input validation fails
 */
export class ValidationError extends XAIError {
  constructor(message: string, code?: number, errorDetails?: Record<string, unknown>) {
    super(message, code, errorDetails);
    this.name = 'ValidationError';
    Object.setPrototypeOf(this, ValidationError.prototype);
  }
}

/**
 * Rate limit error - raised when rate limit is exceeded
 */
export class RateLimitError extends XAIError {
  public readonly retryAfter?: number;

  constructor(
    message: string,
    retryAfter?: number,
    code?: number,
    errorDetails?: Record<string, unknown>
  ) {
    super(message, code, errorDetails);
    this.name = 'RateLimitError';
    this.retryAfter = retryAfter;
    Object.setPrototypeOf(this, RateLimitError.prototype);
  }
}

/**
 * Network error - raised when network connectivity issue occurs
 */
export class NetworkError extends XAIError {
  constructor(message: string, code?: number, errorDetails?: Record<string, unknown>) {
    super(message, code, errorDetails);
    this.name = 'NetworkError';
    Object.setPrototypeOf(this, NetworkError.prototype);
  }
}

/**
 * Timeout error - raised when request times out
 */
export class TimeoutError extends XAIError {
  constructor(message: string, code?: number, errorDetails?: Record<string, unknown>) {
    super(message, code, errorDetails);
    this.name = 'TimeoutError';
    Object.setPrototypeOf(this, TimeoutError.prototype);
  }
}

/**
 * Not found error - raised when requested resource is not found
 */
export class NotFoundError extends XAIError {
  constructor(message: string, code?: number, errorDetails?: Record<string, unknown>) {
    super(message, code, errorDetails);
    this.name = 'NotFoundError';
    Object.setPrototypeOf(this, NotFoundError.prototype);
  }
}

/**
 * Conflict error - raised when resource conflict occurs
 */
export class ConflictError extends XAIError {
  constructor(message: string, code?: number, errorDetails?: Record<string, unknown>) {
    super(message, code, errorDetails);
    this.name = 'ConflictError';
    Object.setPrototypeOf(this, ConflictError.prototype);
  }
}

/**
 * Internal server error - raised when server encounters an error
 */
export class InternalServerError extends XAIError {
  constructor(message: string, code?: number, errorDetails?: Record<string, unknown>) {
    super(message, code, errorDetails);
    this.name = 'InternalServerError';
    Object.setPrototypeOf(this, InternalServerError.prototype);
  }
}

/**
 * Service unavailable error - raised when service is temporarily unavailable
 */
export class ServiceUnavailableError extends XAIError {
  constructor(message: string, code?: number, errorDetails?: Record<string, unknown>) {
    super(message, code, errorDetails);
    this.name = 'ServiceUnavailableError';
    Object.setPrototypeOf(this, ServiceUnavailableError.prototype);
  }
}

/**
 * Transaction error - raised when transaction operation fails
 */
export class TransactionError extends XAIError {
  constructor(message: string, code?: number, errorDetails?: Record<string, unknown>) {
    super(message, code, errorDetails);
    this.name = 'TransactionError';
    Object.setPrototypeOf(this, TransactionError.prototype);
  }
}

/**
 * Wallet error - raised when wallet operation fails
 */
export class WalletError extends XAIError {
  constructor(message: string, code?: number, errorDetails?: Record<string, unknown>) {
    super(message, code, errorDetails);
    this.name = 'WalletError';
    Object.setPrototypeOf(this, WalletError.prototype);
  }
}

/**
 * Mining error - raised when mining operation fails
 */
export class MiningError extends XAIError {
  constructor(message: string, code?: number, errorDetails?: Record<string, unknown>) {
    super(message, code, errorDetails);
    this.name = 'MiningError';
    Object.setPrototypeOf(this, MiningError.prototype);
  }
}

/**
 * Governance error - raised when governance operation fails
 */
export class GovernanceError extends XAIError {
  constructor(message: string, code?: number, errorDetails?: Record<string, unknown>) {
    super(message, code, errorDetails);
    this.name = 'GovernanceError';
    Object.setPrototypeOf(this, GovernanceError.prototype);
  }
}

/**
 * WebSocket error - raised when WebSocket connection fails
 */
export class WebSocketError extends XAIError {
  constructor(message: string, code?: number, errorDetails?: Record<string, unknown>) {
    super(message, code, errorDetails);
    this.name = 'WebSocketError';
    Object.setPrototypeOf(this, WebSocketError.prototype);
  }
}

/**
 * AI error - raised when AI operation fails
 */
export class AIError extends XAIError {
  constructor(message: string, code?: number, errorDetails?: Record<string, unknown>) {
    super(message, code, errorDetails);
    this.name = 'AIError';
    Object.setPrototypeOf(this, AIError.prototype);
  }
}
