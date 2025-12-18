/**
 * XAI SDK Type Definitions
 *
 * Comprehensive TypeScript types for all blockchain operations.
 */

/**
 * Transaction status enumeration
 */
export enum TransactionStatus {
  PENDING = 'pending',
  CONFIRMED = 'confirmed',
  FAILED = 'failed',
}

/**
 * Wallet type enumeration
 */
export enum WalletType {
  STANDARD = 'standard',
  EMBEDDED = 'embedded',
  HARDWARE = 'hardware',
}

/**
 * Proposal status enumeration
 */
export enum ProposalStatus {
  PENDING = 'pending',
  ACTIVE = 'active',
  PASSED = 'passed',
  FAILED = 'failed',
}

/**
 * Vote choice enumeration
 */
export enum VoteChoice {
  YES = 'yes',
  NO = 'no',
  ABSTAIN = 'abstain',
}

/**
 * Wallet interface
 */
export interface Wallet {
  address: string;
  publicKey: string;
  createdAt: string;
  walletType?: WalletType;
  privateKey?: string;
  nonce?: number;
  metadata?: Record<string, unknown>;
}

/**
 * Balance information
 */
export interface Balance {
  address: string;
  balance: string;
  lockedBalance?: string;
  availableBalance?: string;
  nonce?: number;
  lastUpdated?: string;
}

/**
 * Transaction interface
 */
export interface Transaction {
  hash: string;
  from: string;
  to: string;
  amount: string;
  timestamp: string;
  status?: TransactionStatus;
  fee?: string;
  gasLimit?: string;
  gasUsed?: string;
  gasPrice?: string;
  nonce?: number;
  data?: string;
  blockNumber?: number;
  blockHash?: string;
  confirmations?: number;
  metadata?: Record<string, unknown>;
}

/**
 * Block interface
 */
export interface Block {
  number: number;
  hash: string;
  parentHash: string;
  timestamp: number;
  miner: string;
  difficulty: string;
  gasLimit: string;
  gasUsed: string;
  transactions: number;
  transactionHashes?: string[];
  metadata?: Record<string, unknown>;
}

/**
 * Proposal interface
 */
export interface Proposal {
  id: number;
  title: string;
  description: string;
  creator: string;
  status: ProposalStatus;
  createdAt: string;
  votingStartsAt?: string;
  votingEndsAt?: string;
  votesFor?: number;
  votesAgainst?: number;
  votesAbstain?: number;
  metadata?: Record<string, unknown>;
}

/**
 * Mining status interface
 */
export interface MiningStatus {
  mining: boolean;
  threads: number;
  hashrate: string;
  blocksFound: number;
  currentDifficulty: string;
  uptime: number;
  lastBlockTime?: number;
  metadata?: Record<string, unknown>;
}

/**
 * Blockchain statistics
 */
export interface BlockchainStats {
  totalBlocks: number;
  totalTransactions: number;
  totalAccounts: number;
  difficulty: string;
  hashrate: string;
  averageBlockTime: number;
  totalSupply: string;
  network?: string;
  timestamp?: string;
  metadata?: Record<string, unknown>;
}

/**
 * Trade order interface
 */
export interface TradeOrder {
  id: string;
  fromAddress: string;
  toAddress: string;
  fromAmount: string;
  toAmount: string;
  createdAt: string;
  status?: string;
  expiresAt?: string;
  metadata?: Record<string, unknown>;
}

/**
 * Paginated response interface
 */
export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  limit: number;
  offset: number;
}

/**
 * Node information
 */
export interface NodeInfo {
  status: string;
  node: string;
  version: string;
  algorithmicFeatures?: boolean;
  endpoints?: string[];
}

/**
 * Health check response
 */
export interface HealthCheckResponse {
  status: string;
  timestamp: number;
  blockchain?: Record<string, unknown>;
  services?: Record<string, unknown>;
  network?: Record<string, unknown>;
  backlog?: Record<string, unknown>;
  error?: string;
}

/**
 * Sync status response
 */
export interface SyncStatus {
  syncing: boolean;
  currentBlock?: number;
  highestBlock?: number;
  startingBlock?: number;
  syncProgress?: number;
}

/**
 * Fee estimation response
 */
export interface FeeEstimation {
  estimatedFee: string;
  gasLimit: string;
  gasPrice: string;
  baseFee?: string;
  priorityFee?: string;
}

/**
 * Transaction history query parameters
 */
export interface TransactionHistoryParams {
  address: string;
  limit?: number;
  offset?: number;
}

/**
 * Block query parameters
 */
export interface BlockQueryParams {
  limit?: number;
  offset?: number;
}

/**
 * Proposal query parameters
 */
export interface ProposalQueryParams {
  status?: string;
  limit?: number;
  offset?: number;
}

/**
 * Send transaction parameters
 */
export interface SendTransactionParams {
  from: string;
  to: string;
  amount: string;
  data?: string;
  gasLimit?: string;
  gasPrice?: string;
  nonce?: number;
  signature?: string;
}

/**
 * Create proposal parameters
 */
export interface CreateProposalParams {
  title: string;
  description: string;
  proposer: string;
  duration?: number;
  metadata?: Record<string, unknown>;
}

/**
 * Vote parameters
 */
export interface VoteParams {
  proposalId: number;
  voter: string;
  choice: VoteChoice;
}

/**
 * Create wallet parameters
 */
export interface CreateWalletParams {
  walletType?: WalletType;
  name?: string;
}

/**
 * Create embedded wallet parameters
 */
export interface CreateEmbeddedWalletParams {
  appId: string;
  userId: string;
  metadata?: Record<string, unknown>;
}

/**
 * Embedded wallet login parameters
 */
export interface EmbeddedWalletLoginParams {
  walletId: string;
  password: string;
}

/**
 * Mining rewards response
 */
export interface MiningRewards {
  address: string;
  totalRewards: string;
  pendingRewards: string;
  claimedRewards: string;
  blocksFound?: number;
}

/**
 * WebSocket event types
 */
export enum WebSocketEventType {
  NEW_BLOCK = 'new_block',
  NEW_TRANSACTION = 'new_transaction',
  TRANSACTION_CONFIRMED = 'transaction_confirmed',
  MINING_BLOCK_FOUND = 'mining_block_found',
  PROPOSAL_CREATED = 'proposal_created',
  PROPOSAL_VOTE = 'proposal_vote',
}

/**
 * WebSocket message
 */
export interface WebSocketMessage<T = unknown> {
  type: WebSocketEventType;
  data: T;
  timestamp: number;
}

/**
 * SDK configuration options
 */
export interface XAIClientConfig {
  baseUrl?: string;
  apiKey?: string;
  timeout?: number;
  maxRetries?: number;
  retryDelay?: number;
  poolConnections?: number;
  poolMaxSize?: number;
}
