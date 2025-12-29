/**
 * XAI Mobile App Type Definitions
 * Production-ready types for multi-wallet, contacts, offline support
 */

// ============== Wallet Types ==============

export interface Wallet {
  id: string;
  name: string;
  address: string;
  publicKey: string;
  privateKey?: string; // Not present for watch-only wallets
  mnemonic?: string; // Only stored temporarily during backup flow
  balance: number;
  createdAt: number;
  lastSynced?: number;
  isWatchOnly: boolean;
  isBackedUp: boolean;
  derivationPath?: string;
  color?: WalletColor;
}

export type WalletColor =
  | 'indigo'
  | 'emerald'
  | 'amber'
  | 'rose'
  | 'cyan'
  | 'purple';

export interface WalletBackup {
  walletId: string;
  mnemonic: string[];
  verifiedAt?: number;
}

// ============== Transaction Types ==============

export interface Transaction {
  txid: string;
  sender: string;
  recipient: string;
  amount: number;
  fee: number;
  timestamp: number;
  nonce: number;
  signature?: string;
  status: TransactionStatus;
  confirmations?: number;
  blockIndex?: number;
  blockHash?: string;
  memo?: string;
  metadata?: TransactionMetadata;
  error?: string;
}

export type TransactionStatus =
  | 'pending'
  | 'confirmed'
  | 'failed'
  | 'queued'
  | 'replaced';

export interface TransactionMetadata {
  contactName?: string;
  note?: string;
  category?: TransactionCategory;
  tags?: string[];
}

export type TransactionCategory =
  | 'payment'
  | 'transfer'
  | 'reward'
  | 'fee'
  | 'other';

export interface TransactionFilter {
  status?: TransactionStatus[];
  type?: 'incoming' | 'outgoing' | 'all';
  dateFrom?: number;
  dateTo?: number;
  minAmount?: number;
  maxAmount?: number;
  address?: string;
}

export interface BatchTransaction {
  id: string;
  recipients: BatchRecipient[];
  totalAmount: number;
  totalFee: number;
  status: 'draft' | 'pending' | 'partial' | 'complete' | 'failed';
  createdAt: number;
  completedTxids: string[];
  failedRecipients: string[];
}

export interface BatchRecipient {
  address: string;
  amount: number;
  contactName?: string;
  memo?: string;
  txid?: string;
  status: 'pending' | 'sent' | 'failed';
  error?: string;
}

// ============== Address Book / Contacts ==============

export interface Contact {
  id: string;
  name: string;
  address: string;
  label?: string;
  notes?: string;
  createdAt: number;
  lastUsed?: number;
  isFavorite: boolean;
  avatar?: string;
  transactionCount: number;
}

// ============== Block Types ==============

export interface Block {
  index: number;
  hash: string;
  previousHash: string;
  timestamp: number;
  difficulty: number;
  nonce: number;
  miner?: string;
  transactions: Transaction[];
  merkleRoot: string;
  size?: number;
  weight?: number;
  version?: number;
}

export interface BlockDetails extends Block {
  confirmations: number;
  totalValue: number;
  totalFees: number;
  avgFeeRate: number;
  nextBlockHash?: string;
}

// ============== Network / Node Types ==============

export interface NodeInfo {
  status: 'online' | 'offline' | 'syncing';
  node: string;
  version: string;
  algorithmicFeatures: boolean;
  latency?: number;
}

export interface BlockchainStats {
  chainHeight: number;
  difficulty: number;
  totalSupply: number;
  pendingTransactionsCount: number;
  latestBlockHash: string;
  minerAddress?: string;
  peers: number;
  isMining: boolean;
  nodeUptime: number;
  networkHashrate?: number;
  avgBlockTime?: number;
}

export interface HealthStatus {
  status: 'healthy' | 'degraded' | 'unhealthy';
  timestamp: number;
  blockchain: {
    accessible: boolean;
    height?: number;
    difficulty?: number;
    totalSupply?: number;
    latestBlockHash?: string;
  };
  services: {
    api: string;
    storage?: string;
    p2p?: string;
  };
  network: {
    peers: number;
  };
}

export interface MempoolStats {
  fees: {
    averageFee: number;
    medianFee: number;
    averageFeeRate: number;
    medianFeeRate: number;
    minFeeRate: number;
    maxFeeRate: number;
    recommendedFeeRates: {
      slow: number;
      standard: number;
      priority: number;
    };
  };
  pressure: {
    status: 'normal' | 'moderate' | 'elevated' | 'critical';
    capacityRatio: number;
    pendingTransactions: number;
    maxTransactions: number;
  };
  transactions?: MempoolTransaction[];
  ageDistribution?: {
    under1m: number;
    under5m: number;
    under15m: number;
    over15m: number;
  };
}

export interface MempoolTransaction {
  txid: string;
  fee: number;
  feeRate: number;
  size: number;
  age: number;
  sender: string;
  recipient: string;
  amount: number;
}

// ============== API Types ==============

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  code?: string;
}

export interface PaginatedResponse<T> {
  total: number;
  limit: number;
  offset: number;
  items: T[];
}

export interface TransactionSendRequest {
  sender: string;
  recipient: string;
  amount: number;
  fee: number;
  publicKey: string;
  signature: string;
  nonce: number;
  timestamp: number;
  txid?: string;
  metadata?: Record<string, unknown>;
}

export interface FaucetClaimRequest {
  address: string;
}

export interface FaucetClaimResponse {
  amount: number;
  txid: string;
  message: string;
  note: string;
}

export interface NonceInfo {
  address: string;
  confirmedNonce: number;
  nextNonce: number;
  pendingNonce?: number;
}

// ============== Offline / Sync Types ==============

export interface SyncStatus {
  lastSyncTime: number;
  syncInProgress: boolean;
  pendingQueueCount: number;
  failedQueueCount: number;
  isOnline: boolean;
  syncError?: string;
}

export interface QueuedTransaction {
  id: string;
  transaction: TransactionSendRequest;
  createdAt: number;
  retryCount: number;
  lastAttempt?: number;
  error?: string;
  status: 'queued' | 'sending' | 'failed' | 'sent';
}

export interface CachedData<T> {
  data: T;
  timestamp: number;
  expiresAt: number;
}

// ============== Settings Types ==============

export interface AppSettings {
  nodeUrl: string;
  apiKey?: string;
  theme: 'light' | 'dark' | 'system';
  currency: string;
  language: string;
  notifications: NotificationSettings;
  security: SecuritySettings;
  display: DisplaySettings;
}

export interface NotificationSettings {
  enabled: boolean;
  incomingTransactions: boolean;
  outgoingConfirmations: boolean;
  priceAlerts: boolean;
  networkAlerts: boolean;
  soundEnabled: boolean;
  vibrationEnabled: boolean;
}

export interface SecuritySettings {
  biometricEnabled: boolean;
  pinEnabled: boolean;
  autoLockTimeout: number; // in minutes, 0 = never
  hideBalance: boolean;
  requireAuthForSend: boolean;
  requireAuthForExport: boolean;
}

export interface DisplaySettings {
  showFiatValue: boolean;
  defaultFeeLevel: 'slow' | 'standard' | 'priority';
  confirmationThreshold: number;
  compactTransactionList: boolean;
}

// ============== Notification Types ==============

export interface AppNotification {
  id: string;
  type: NotificationType;
  title: string;
  message: string;
  timestamp: number;
  read: boolean;
  data?: Record<string, unknown>;
  action?: NotificationAction;
}

export type NotificationType =
  | 'transaction_received'
  | 'transaction_confirmed'
  | 'transaction_failed'
  | 'price_alert'
  | 'network_issue'
  | 'backup_reminder'
  | 'security_alert'
  | 'system';

export interface NotificationAction {
  type: 'navigate' | 'url' | 'dismiss';
  target?: string;
  params?: Record<string, unknown>;
}

// ============== Navigation Types ==============

export type RootStackParamList = {
  Main: undefined;
  Send: { recipient?: string; amount?: number; contactId?: string };
  Receive: { walletId?: string };
  TransactionDetail: { txid: string };
  BlockDetail: { index: number } | { hash: string };
  AddressDetail: { address: string };
  Settings: undefined;
  Security: undefined;
  Notifications: undefined;
  AddressBook: undefined;
  ContactDetail: { contactId: string };
  EditContact: { contactId?: string; address?: string };
  WalletBackup: { walletId: string };
  WalletImport: { type: 'mnemonic' | 'privateKey' | 'watchOnly' };
  QRScanner: { onScan: (data: string) => void };
  BatchSend: undefined;
};

export type MainTabParamList = {
  Home: undefined;
  Wallet: undefined;
  Explorer: undefined;
  Settings: undefined;
};

// ============== Error Types ==============

export interface AppError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
  timestamp: number;
  recoverable: boolean;
  action?: ErrorAction;
}

export interface ErrorAction {
  label: string;
  handler: () => void;
}

export type ErrorCode =
  | 'NETWORK_ERROR'
  | 'INVALID_ADDRESS'
  | 'INSUFFICIENT_BALANCE'
  | 'TRANSACTION_FAILED'
  | 'NONCE_ERROR'
  | 'SIGNATURE_ERROR'
  | 'TIMEOUT'
  | 'RATE_LIMITED'
  | 'UNAUTHORIZED'
  | 'WALLET_LOCKED'
  | 'BACKUP_REQUIRED'
  | 'SYNC_FAILED'
  | 'UNKNOWN';
