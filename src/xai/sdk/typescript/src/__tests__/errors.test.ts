/**
 * Error Classes Unit Tests
 *
 * Comprehensive tests for all XAI SDK error classes including:
 * - Base XAIError class
 * - Specific error types (Authentication, Authorization, etc.)
 * - Error properties (code, message, errorDetails)
 * - Prototype chain and instanceof checks
 */

import {
  XAIError,
  AuthenticationError,
  AuthorizationError,
  ValidationError,
  RateLimitError,
  NetworkError,
  TimeoutError,
  NotFoundError,
  ConflictError,
  InternalServerError,
  ServiceUnavailableError,
  TransactionError,
  WalletError,
  MiningError,
  GovernanceError,
  WebSocketError,
  AIError,
} from '../errors';

describe('XAI SDK Errors', () => {
  describe('XAIError', () => {
    it('should create error with message only', () => {
      const error = new XAIError('Something went wrong');

      expect(error.message).toBe('Something went wrong');
      expect(error.code).toBeUndefined();
      expect(error.errorDetails).toBeUndefined();
      expect(error.name).toBe('XAIError');
    });

    it('should create error with message and code', () => {
      const error = new XAIError('Something went wrong', 500);

      expect(error.message).toBe('Something went wrong');
      expect(error.code).toBe(500);
    });

    it('should create error with all parameters', () => {
      const details = { field: 'email', reason: 'invalid format' };
      const error = new XAIError('Validation failed', 400, details);

      expect(error.message).toBe('Validation failed');
      expect(error.code).toBe(400);
      expect(error.errorDetails).toEqual(details);
    });

    it('should be instanceof Error', () => {
      const error = new XAIError('Test error');

      expect(error).toBeInstanceOf(Error);
      expect(error).toBeInstanceOf(XAIError);
    });

    it('should have correct toString with code', () => {
      const error = new XAIError('Error message', 404);

      expect(error.toString()).toBe('[404] Error message');
    });

    it('should have correct toString without code', () => {
      const error = new XAIError('Error message');

      expect(error.toString()).toBe('Error message');
    });

    it('should maintain prototype chain', () => {
      const error = new XAIError('Test');

      expect(Object.getPrototypeOf(error)).toBe(XAIError.prototype);
    });
  });

  describe('AuthenticationError', () => {
    it('should create authentication error', () => {
      const error = new AuthenticationError('Invalid credentials');

      expect(error.message).toBe('Invalid credentials');
      expect(error.name).toBe('AuthenticationError');
      expect(error).toBeInstanceOf(AuthenticationError);
      expect(error).toBeInstanceOf(XAIError);
      expect(error).toBeInstanceOf(Error);
    });

    it('should accept code and details', () => {
      const error = new AuthenticationError('Token expired', 401, { expired_at: '2024-01-01' });

      expect(error.code).toBe(401);
      expect(error.errorDetails).toEqual({ expired_at: '2024-01-01' });
    });
  });

  describe('AuthorizationError', () => {
    it('should create authorization error', () => {
      const error = new AuthorizationError('Access denied');

      expect(error.message).toBe('Access denied');
      expect(error.name).toBe('AuthorizationError');
      expect(error).toBeInstanceOf(AuthorizationError);
      expect(error).toBeInstanceOf(XAIError);
    });

    it('should accept code and details', () => {
      const error = new AuthorizationError('Insufficient permissions', 403, {
        required: 'admin',
        current: 'user',
      });

      expect(error.code).toBe(403);
      expect(error.errorDetails).toEqual({ required: 'admin', current: 'user' });
    });
  });

  describe('ValidationError', () => {
    it('should create validation error', () => {
      const error = new ValidationError('Invalid input');

      expect(error.message).toBe('Invalid input');
      expect(error.name).toBe('ValidationError');
      expect(error).toBeInstanceOf(ValidationError);
      expect(error).toBeInstanceOf(XAIError);
    });

    it('should accept code and details', () => {
      const error = new ValidationError('Validation failed', 400, {
        fields: ['email', 'password'],
      });

      expect(error.code).toBe(400);
      expect(error.errorDetails).toEqual({ fields: ['email', 'password'] });
    });
  });

  describe('RateLimitError', () => {
    it('should create rate limit error', () => {
      const error = new RateLimitError('Rate limit exceeded');

      expect(error.message).toBe('Rate limit exceeded');
      expect(error.name).toBe('RateLimitError');
      expect(error.retryAfter).toBeUndefined();
      expect(error).toBeInstanceOf(RateLimitError);
      expect(error).toBeInstanceOf(XAIError);
    });

    it('should accept retryAfter', () => {
      const error = new RateLimitError('Rate limit exceeded', 60);

      expect(error.retryAfter).toBe(60);
    });

    it('should accept all parameters', () => {
      const error = new RateLimitError('Rate limit exceeded', 120, 429, {
        limit: 100,
        remaining: 0,
      });

      expect(error.retryAfter).toBe(120);
      expect(error.code).toBe(429);
      expect(error.errorDetails).toEqual({ limit: 100, remaining: 0 });
    });
  });

  describe('NetworkError', () => {
    it('should create network error', () => {
      const error = new NetworkError('Connection refused');

      expect(error.message).toBe('Connection refused');
      expect(error.name).toBe('NetworkError');
      expect(error).toBeInstanceOf(NetworkError);
      expect(error).toBeInstanceOf(XAIError);
    });

    it('should accept code and details', () => {
      const error = new NetworkError('DNS lookup failed', undefined, { host: 'api.xai.io' });

      expect(error.errorDetails).toEqual({ host: 'api.xai.io' });
    });
  });

  describe('TimeoutError', () => {
    it('should create timeout error', () => {
      const error = new TimeoutError('Request timed out');

      expect(error.message).toBe('Request timed out');
      expect(error.name).toBe('TimeoutError');
      expect(error).toBeInstanceOf(TimeoutError);
      expect(error).toBeInstanceOf(XAIError);
    });

    it('should accept code and details', () => {
      const error = new TimeoutError('Timeout after 30s', undefined, { timeout: 30000 });

      expect(error.errorDetails).toEqual({ timeout: 30000 });
    });
  });

  describe('NotFoundError', () => {
    it('should create not found error', () => {
      const error = new NotFoundError('Resource not found');

      expect(error.message).toBe('Resource not found');
      expect(error.name).toBe('NotFoundError');
      expect(error).toBeInstanceOf(NotFoundError);
      expect(error).toBeInstanceOf(XAIError);
    });

    it('should accept code and details', () => {
      const error = new NotFoundError('Wallet not found', 404, { address: '0x1234' });

      expect(error.code).toBe(404);
      expect(error.errorDetails).toEqual({ address: '0x1234' });
    });
  });

  describe('ConflictError', () => {
    it('should create conflict error', () => {
      const error = new ConflictError('Resource already exists');

      expect(error.message).toBe('Resource already exists');
      expect(error.name).toBe('ConflictError');
      expect(error).toBeInstanceOf(ConflictError);
      expect(error).toBeInstanceOf(XAIError);
    });

    it('should accept code and details', () => {
      const error = new ConflictError('Duplicate entry', 409, { field: 'email' });

      expect(error.code).toBe(409);
      expect(error.errorDetails).toEqual({ field: 'email' });
    });
  });

  describe('InternalServerError', () => {
    it('should create internal server error', () => {
      const error = new InternalServerError('Server error');

      expect(error.message).toBe('Server error');
      expect(error.name).toBe('InternalServerError');
      expect(error).toBeInstanceOf(InternalServerError);
      expect(error).toBeInstanceOf(XAIError);
    });

    it('should accept code and details', () => {
      const error = new InternalServerError('Database connection failed', 500, {
        trace_id: 'abc123',
      });

      expect(error.code).toBe(500);
      expect(error.errorDetails).toEqual({ trace_id: 'abc123' });
    });
  });

  describe('ServiceUnavailableError', () => {
    it('should create service unavailable error', () => {
      const error = new ServiceUnavailableError('Service temporarily unavailable');

      expect(error.message).toBe('Service temporarily unavailable');
      expect(error.name).toBe('ServiceUnavailableError');
      expect(error).toBeInstanceOf(ServiceUnavailableError);
      expect(error).toBeInstanceOf(XAIError);
    });

    it('should accept code and details', () => {
      const error = new ServiceUnavailableError('Maintenance mode', 503, {
        estimated_downtime: '2 hours',
      });

      expect(error.code).toBe(503);
      expect(error.errorDetails).toEqual({ estimated_downtime: '2 hours' });
    });
  });

  describe('TransactionError', () => {
    it('should create transaction error', () => {
      const error = new TransactionError('Transaction failed');

      expect(error.message).toBe('Transaction failed');
      expect(error.name).toBe('TransactionError');
      expect(error).toBeInstanceOf(TransactionError);
      expect(error).toBeInstanceOf(XAIError);
    });

    it('should accept code and details', () => {
      const error = new TransactionError('Insufficient funds', undefined, {
        required: '1000',
        available: '500',
      });

      expect(error.errorDetails).toEqual({ required: '1000', available: '500' });
    });
  });

  describe('WalletError', () => {
    it('should create wallet error', () => {
      const error = new WalletError('Wallet creation failed');

      expect(error.message).toBe('Wallet creation failed');
      expect(error.name).toBe('WalletError');
      expect(error).toBeInstanceOf(WalletError);
      expect(error).toBeInstanceOf(XAIError);
    });

    it('should accept code and details', () => {
      const error = new WalletError('Invalid mnemonic', undefined, { word_count: 11 });

      expect(error.errorDetails).toEqual({ word_count: 11 });
    });
  });

  describe('MiningError', () => {
    it('should create mining error', () => {
      const error = new MiningError('Mining failed');

      expect(error.message).toBe('Mining failed');
      expect(error.name).toBe('MiningError');
      expect(error).toBeInstanceOf(MiningError);
      expect(error).toBeInstanceOf(XAIError);
    });

    it('should accept code and details', () => {
      const error = new MiningError('Hardware error', undefined, { gpu: 0 });

      expect(error.errorDetails).toEqual({ gpu: 0 });
    });
  });

  describe('GovernanceError', () => {
    it('should create governance error', () => {
      const error = new GovernanceError('Voting failed');

      expect(error.message).toBe('Voting failed');
      expect(error.name).toBe('GovernanceError');
      expect(error).toBeInstanceOf(GovernanceError);
      expect(error).toBeInstanceOf(XAIError);
    });

    it('should accept code and details', () => {
      const error = new GovernanceError('Already voted', undefined, { proposal_id: 1 });

      expect(error.errorDetails).toEqual({ proposal_id: 1 });
    });
  });

  describe('WebSocketError', () => {
    it('should create websocket error', () => {
      const error = new WebSocketError('Connection closed');

      expect(error.message).toBe('Connection closed');
      expect(error.name).toBe('WebSocketError');
      expect(error).toBeInstanceOf(WebSocketError);
      expect(error).toBeInstanceOf(XAIError);
    });

    it('should accept code and details', () => {
      const error = new WebSocketError('Connection failed', 1006, { reason: 'abnormal_closure' });

      expect(error.code).toBe(1006);
      expect(error.errorDetails).toEqual({ reason: 'abnormal_closure' });
    });
  });

  describe('AIError', () => {
    it('should create AI error', () => {
      const error = new AIError('AI processing failed');

      expect(error.message).toBe('AI processing failed');
      expect(error.name).toBe('AIError');
      expect(error).toBeInstanceOf(AIError);
      expect(error).toBeInstanceOf(XAIError);
    });

    it('should accept code and details', () => {
      const error = new AIError('Model unavailable', undefined, { model: 'gpt-4' });

      expect(error.errorDetails).toEqual({ model: 'gpt-4' });
    });
  });

  describe('Error inheritance', () => {
    it('should allow catching specific errors', () => {
      const errors = [
        new AuthenticationError('Auth failed'),
        new ValidationError('Validation failed'),
        new NetworkError('Network failed'),
      ];

      for (const error of errors) {
        try {
          throw error;
        } catch (e) {
          if (e instanceof XAIError) {
            expect(e).toBeDefined();
          }
        }
      }
    });

    it('should distinguish between error types', () => {
      const authError = new AuthenticationError('Auth');
      const validationError = new ValidationError('Validation');

      expect(authError).toBeInstanceOf(AuthenticationError);
      expect(authError).not.toBeInstanceOf(ValidationError);
      expect(validationError).toBeInstanceOf(ValidationError);
      expect(validationError).not.toBeInstanceOf(AuthenticationError);
    });

    it('should all be instances of XAIError', () => {
      const allErrors = [
        new XAIError('Base'),
        new AuthenticationError('Auth'),
        new AuthorizationError('Authz'),
        new ValidationError('Valid'),
        new RateLimitError('Rate'),
        new NetworkError('Network'),
        new TimeoutError('Timeout'),
        new NotFoundError('NotFound'),
        new ConflictError('Conflict'),
        new InternalServerError('Internal'),
        new ServiceUnavailableError('Service'),
        new TransactionError('Transaction'),
        new WalletError('Wallet'),
        new MiningError('Mining'),
        new GovernanceError('Governance'),
        new WebSocketError('WebSocket'),
        new AIError('AI'),
      ];

      for (const error of allErrors) {
        expect(error).toBeInstanceOf(XAIError);
        expect(error).toBeInstanceOf(Error);
      }
    });
  });

  describe('Error serialization', () => {
    it('should serialize to JSON correctly', () => {
      const error = new ValidationError('Invalid email', 400, { field: 'email' });

      const json = JSON.stringify({
        name: error.name,
        message: error.message,
        code: error.code,
        details: error.errorDetails,
      });

      const parsed = JSON.parse(json);

      expect(parsed.name).toBe('ValidationError');
      expect(parsed.message).toBe('Invalid email');
      expect(parsed.code).toBe(400);
      expect(parsed.details).toEqual({ field: 'email' });
    });
  });
});
