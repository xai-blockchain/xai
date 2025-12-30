/**
 * Index Exports Tests
 *
 * Verifies all expected exports are available from the SDK entry point.
 */

import * as SDK from '../index';

describe('SDK Exports', () => {
  describe('Main Client', () => {
    it('should export XAIClient as named export', () => {
      expect(SDK.XAIClient).toBeDefined();
      expect(typeof SDK.XAIClient).toBe('function');
    });

    it('should export XAIClient as default export', () => {
      expect(SDK.default).toBeDefined();
      expect(typeof SDK.default).toBe('function');
    });
  });

  describe('Client Classes', () => {
    it('should export WalletClient', () => {
      expect(SDK.WalletClient).toBeDefined();
      expect(typeof SDK.WalletClient).toBe('function');
    });

    it('should export TransactionClient', () => {
      expect(SDK.TransactionClient).toBeDefined();
      expect(typeof SDK.TransactionClient).toBe('function');
    });

    it('should export BlockchainClient', () => {
      expect(SDK.BlockchainClient).toBeDefined();
      expect(typeof SDK.BlockchainClient).toBe('function');
    });

    it('should export MiningClient', () => {
      expect(SDK.MiningClient).toBeDefined();
      expect(typeof SDK.MiningClient).toBe('function');
    });

    it('should export GovernanceClient', () => {
      expect(SDK.GovernanceClient).toBeDefined();
      expect(typeof SDK.GovernanceClient).toBe('function');
    });

    it('should export AIClient', () => {
      expect(SDK.AIClient).toBeDefined();
      expect(typeof SDK.AIClient).toBe('function');
    });
  });

  describe('Utility Classes', () => {
    it('should export HTTPClient', () => {
      expect(SDK.HTTPClient).toBeDefined();
      expect(typeof SDK.HTTPClient).toBe('function');
    });

    it('should export WebSocketClient', () => {
      expect(SDK.WebSocketClient).toBeDefined();
      expect(typeof SDK.WebSocketClient).toBe('function');
    });
  });

  describe('Error Classes', () => {
    it('should export XAIError', () => {
      expect(SDK.XAIError).toBeDefined();
      expect(typeof SDK.XAIError).toBe('function');
    });

    it('should export AuthenticationError', () => {
      expect(SDK.AuthenticationError).toBeDefined();
      expect(typeof SDK.AuthenticationError).toBe('function');
    });

    it('should export AuthorizationError', () => {
      expect(SDK.AuthorizationError).toBeDefined();
      expect(typeof SDK.AuthorizationError).toBe('function');
    });

    it('should export ValidationError', () => {
      expect(SDK.ValidationError).toBeDefined();
      expect(typeof SDK.ValidationError).toBe('function');
    });

    it('should export RateLimitError', () => {
      expect(SDK.RateLimitError).toBeDefined();
      expect(typeof SDK.RateLimitError).toBe('function');
    });

    it('should export NetworkError', () => {
      expect(SDK.NetworkError).toBeDefined();
      expect(typeof SDK.NetworkError).toBe('function');
    });

    it('should export TimeoutError', () => {
      expect(SDK.TimeoutError).toBeDefined();
      expect(typeof SDK.TimeoutError).toBe('function');
    });

    it('should export NotFoundError', () => {
      expect(SDK.NotFoundError).toBeDefined();
      expect(typeof SDK.NotFoundError).toBe('function');
    });

    it('should export ConflictError', () => {
      expect(SDK.ConflictError).toBeDefined();
      expect(typeof SDK.ConflictError).toBe('function');
    });

    it('should export InternalServerError', () => {
      expect(SDK.InternalServerError).toBeDefined();
      expect(typeof SDK.InternalServerError).toBe('function');
    });

    it('should export ServiceUnavailableError', () => {
      expect(SDK.ServiceUnavailableError).toBeDefined();
      expect(typeof SDK.ServiceUnavailableError).toBe('function');
    });

    it('should export TransactionError', () => {
      expect(SDK.TransactionError).toBeDefined();
      expect(typeof SDK.TransactionError).toBe('function');
    });

    it('should export WalletError', () => {
      expect(SDK.WalletError).toBeDefined();
      expect(typeof SDK.WalletError).toBe('function');
    });

    it('should export MiningError', () => {
      expect(SDK.MiningError).toBeDefined();
      expect(typeof SDK.MiningError).toBe('function');
    });

    it('should export GovernanceError', () => {
      expect(SDK.GovernanceError).toBeDefined();
      expect(typeof SDK.GovernanceError).toBe('function');
    });

    it('should export WebSocketError', () => {
      expect(SDK.WebSocketError).toBeDefined();
      expect(typeof SDK.WebSocketError).toBe('function');
    });

    it('should export AIError', () => {
      expect(SDK.AIError).toBeDefined();
      expect(typeof SDK.AIError).toBe('function');
    });
  });

  describe('Enums', () => {
    it('should export TransactionStatus', () => {
      expect(SDK.TransactionStatus).toBeDefined();
      expect(SDK.TransactionStatus.PENDING).toBe('pending');
      expect(SDK.TransactionStatus.CONFIRMED).toBe('confirmed');
      expect(SDK.TransactionStatus.FAILED).toBe('failed');
    });

    it('should export WalletType', () => {
      expect(SDK.WalletType).toBeDefined();
      expect(SDK.WalletType.STANDARD).toBe('standard');
      expect(SDK.WalletType.EMBEDDED).toBe('embedded');
      expect(SDK.WalletType.HARDWARE).toBe('hardware');
    });

    it('should export ProposalStatus', () => {
      expect(SDK.ProposalStatus).toBeDefined();
      expect(SDK.ProposalStatus.PENDING).toBe('pending');
      expect(SDK.ProposalStatus.ACTIVE).toBe('active');
      expect(SDK.ProposalStatus.PASSED).toBe('passed');
      expect(SDK.ProposalStatus.FAILED).toBe('failed');
    });

    it('should export VoteChoice', () => {
      expect(SDK.VoteChoice).toBeDefined();
      expect(SDK.VoteChoice.YES).toBe('yes');
      expect(SDK.VoteChoice.NO).toBe('no');
      expect(SDK.VoteChoice.ABSTAIN).toBe('abstain');
    });

    it('should export WebSocketEventType', () => {
      expect(SDK.WebSocketEventType).toBeDefined();
      expect(SDK.WebSocketEventType.NEW_BLOCK).toBe('new_block');
      expect(SDK.WebSocketEventType.NEW_TRANSACTION).toBe('new_transaction');
    });
  });
});
