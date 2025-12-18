/**
 * XAI React Native SDK Type Definitions
 * Complete type system for blockchain operations, wallet management, and mobile features
 */

// ============================================================================
// Configuration Types
// ============================================================================

export interface XAIConfig {
  baseUrl: string;
  timeout?: number;
  retries?: number;
  retryDelay?: number;
}

export interface BiometricConfig {
  title?: string;
  subtitle?: string;
  description?: string;
  cancelText?: string;
  fallbackEnabled?: boolean;
}

// ============================================================================
// Wallet Types
// ============================================================================

export interface Wallet {
  address: string;
  publicKey: string;
  privateKey?: string; // Only available when explicitly requested
  mnemonic?: string; // Only available during creation
}

export interface WalletBalance {
  address: string;
  balance: string;
  pendingBalance?: string;
}

export interface StoredWallet {
  address: string;
  publicKey: string;
  encryptedPrivateKey: string;
  biometricEnabled: boolean;
  createdAt: number;
  label?: string;
}

// ============================================================================
// Transaction Types
// ============================================================================

export interface Transaction {
  hash: string;
  from: string;
  to: string;
  value: string;
  fee: string;
  nonce: number;
  timestamp: number;
  signature: string;
  data?: string;
  status: TransactionStatus;
  blockNumber?: number;
  confirmations?: number;
}

export enum TransactionStatus {
  PENDING = 'pending',
  CONFIRMED = 'confirmed',
  FAILED = 'failed',
}

export interface SendTransactionParams {
  from: string;
  to: string;
  value: string;
  data?: string;
  nonce?: number;
}

export interface SignedTransaction {
  transaction: Transaction;
  signature: string;
  rawTransaction: string;
}

// ============================================================================
// Block Types
// ============================================================================

export interface Block {
  number: number;
  hash: string;
  parentHash: string;
  timestamp: number;
  miner: string;
  difficulty: number;
  transactions: Transaction[];
  nonce: number;
  gasUsed?: string;
  gasLimit?: string;
}

export interface BlockchainInfo {
  height: number;
  latestBlockHash: string;
  difficulty: number;
  totalTransactions: number;
  networkHashRate?: string;
}

// ============================================================================
// Mining Types
// ============================================================================

export interface MiningStats {
  isMining: boolean;
  hashRate: string;
  blocksFound: number;
  lastBlockTime?: number;
  difficulty: number;
}

// ============================================================================
// Governance Types
// ============================================================================

export interface Proposal {
  id: string;
  title: string;
  description: string;
  proposer: string;
  status: ProposalStatus;
  votesFor: string;
  votesAgainst: string;
  votesAbstain: string;
  startTime: number;
  endTime: number;
  executionTime?: number;
}

export enum ProposalStatus {
  PENDING = 'pending',
  ACTIVE = 'active',
  PASSED = 'passed',
  REJECTED = 'rejected',
  EXECUTED = 'executed',
}

export interface Vote {
  proposalId: string;
  voter: string;
  vote: VoteOption;
  weight: string;
  timestamp: number;
}

export enum VoteOption {
  FOR = 'for',
  AGAINST = 'against',
  ABSTAIN = 'abstain',
}

// ============================================================================
// Network Types
// ============================================================================

export interface Peer {
  id: string;
  address: string;
  port: number;
  latency?: number;
  lastSeen: number;
  version?: string;
}

export interface NetworkStats {
  peers: number;
  latency: number;
  bandwidth: {
    upload: number;
    download: number;
  };
  connected: boolean;
}

// ============================================================================
// Storage Types
// ============================================================================

export interface SecureStorageOptions {
  service?: string;
  biometricPrompt?: BiometricConfig;
}

export interface StorageItem<T = any> {
  key: string;
  value: T;
  timestamp: number;
  encrypted: boolean;
}

// ============================================================================
// Notification Types
// ============================================================================

export interface PushNotificationConfig {
  enabled: boolean;
  transactionAlerts: boolean;
  governanceAlerts: boolean;
  priceAlerts: boolean;
  securityAlerts: boolean;
}

export interface NotificationPayload {
  type: NotificationType;
  title: string;
  body: string;
  data?: Record<string, any>;
  timestamp: number;
}

export enum NotificationType {
  TRANSACTION = 'transaction',
  GOVERNANCE = 'governance',
  SECURITY = 'security',
  PRICE = 'price',
  SYSTEM = 'system',
}

// ============================================================================
// Error Types
// ============================================================================

export class XAIError extends Error {
  constructor(
    message: string,
    public code: string,
    public details?: any
  ) {
    super(message);
    this.name = 'XAIError';
  }
}

export class WalletError extends XAIError {
  constructor(message: string, details?: any) {
    super(message, 'WALLET_ERROR', details);
    this.name = 'WalletError';
  }
}

export class TransactionError extends XAIError {
  constructor(message: string, details?: any) {
    super(message, 'TRANSACTION_ERROR', details);
    this.name = 'TransactionError';
  }
}

export class NetworkError extends XAIError {
  constructor(message: string, details?: any) {
    super(message, 'NETWORK_ERROR', details);
    this.name = 'NetworkError';
  }
}

export class BiometricError extends XAIError {
  constructor(message: string, details?: any) {
    super(message, 'BIOMETRIC_ERROR', details);
    this.name = 'BiometricError';
  }
}

export class StorageError extends XAIError {
  constructor(message: string, details?: any) {
    super(message, 'STORAGE_ERROR', details);
    this.name = 'StorageError';
  }
}

// ============================================================================
// Hook Return Types
// ============================================================================

export interface UseWalletReturn {
  wallet: Wallet | null;
  balance: string | null;
  loading: boolean;
  error: Error | null;
  createWallet: (biometricEnabled?: boolean) => Promise<Wallet>;
  importWallet: (mnemonic: string, biometricEnabled?: boolean) => Promise<Wallet>;
  deleteWallet: () => Promise<void>;
  refreshBalance: () => Promise<void>;
}

export interface UseTransactionsReturn {
  transactions: Transaction[];
  loading: boolean;
  error: Error | null;
  sendTransaction: (params: SendTransactionParams) => Promise<Transaction>;
  getTransaction: (hash: string) => Promise<Transaction | null>;
  refresh: () => Promise<void>;
}

export interface UseBalanceReturn {
  balance: string | null;
  loading: boolean;
  error: Error | null;
  refresh: () => Promise<void>;
}

// ============================================================================
// Event Types
// ============================================================================

export interface BlockchainEvent {
  type: BlockchainEventType;
  data: any;
  timestamp: number;
}

export enum BlockchainEventType {
  NEW_BLOCK = 'new_block',
  NEW_TRANSACTION = 'new_transaction',
  TRANSACTION_CONFIRMED = 'transaction_confirmed',
  BALANCE_UPDATED = 'balance_updated',
}

// ============================================================================
// Utility Types
// ============================================================================

export type AsyncResult<T> = Promise<T>;

export interface PaginationParams {
  page?: number;
  limit?: number;
  offset?: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  limit: number;
  hasMore: boolean;
}
