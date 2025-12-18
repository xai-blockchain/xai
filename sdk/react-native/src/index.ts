/**
 * XAI React Native SDK
 * Production-ready mobile SDK for XAI blockchain with secure key storage and biometric authentication
 */

// Clients
export { XAIClient } from './clients/XAIClient';
export { XAIWallet, getXAIWallet } from './clients/XAIWallet';
export { BiometricAuth, getBiometricAuth } from './clients/BiometricAuth';
export { SecureStorage, getSecureStorage } from './clients/SecureStorage';
export {
  PushNotifications,
  getPushNotifications,
  type NotificationHandler,
} from './clients/PushNotifications';

// Hooks
export {
  useWallet,
  useBalance,
  useTransactions,
  useBlockchain,
  type UseWalletOptions,
  type UseBalanceOptions,
  type UseTransactionsOptions,
  type UseBlockchainOptions,
  type UseBlockchainReturn,
} from './hooks';

// Types
export type {
  XAIConfig,
  BiometricConfig,
  Wallet,
  WalletBalance,
  StoredWallet,
  Transaction,
  TransactionStatus,
  SendTransactionParams,
  SignedTransaction,
  Block,
  BlockchainInfo,
  MiningStats,
  Proposal,
  ProposalStatus,
  Vote,
  VoteOption,
  Peer,
  NetworkStats,
  SecureStorageOptions,
  StorageItem,
  PushNotificationConfig,
  NotificationPayload,
  NotificationType,
  UseWalletReturn,
  UseTransactionsReturn,
  UseBalanceReturn,
  BlockchainEvent,
  BlockchainEventType,
  PaginationParams,
  PaginatedResponse,
} from './types';

// Errors
export {
  XAIError,
  WalletError,
  TransactionError,
  NetworkError,
  BiometricError,
  StorageError,
} from './types';

// Utilities
export {
  generateMnemonic,
  validateMnemonic,
  generateWallet,
  generateWalletFromMnemonic,
  signMessage,
  verifySignature,
} from './utils/crypto';
