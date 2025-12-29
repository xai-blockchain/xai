/**
 * Offline Support Utilities
 *
 * Production-ready offline support features:
 * - Cache recent data with AsyncStorage
 * - Queue transactions when offline
 * - Sync status tracking
 * - Network connectivity monitoring
 * - Data expiration management
 */

import * as SecureStore from 'expo-secure-store';
import NetInfo, { NetInfoState } from '@react-native-community/netinfo';
import {
  Transaction,
  Block,
  BlockchainStats,
  MempoolStats,
  TransactionSendRequest,
  QueuedTransaction,
  SyncStatus,
  CachedData,
} from '../types';

// ============== Constants ==============

const STORAGE_PREFIX = 'xai_offline_';

// Cache durations in milliseconds
export const CACHE_DURATIONS = {
  BALANCE: 30 * 1000, // 30 seconds
  TRANSACTIONS: 60 * 1000, // 1 minute
  BLOCKS: 30 * 1000, // 30 seconds
  STATS: 15 * 1000, // 15 seconds
  MEMPOOL: 10 * 1000, // 10 seconds
  CONTACTS: 5 * 60 * 1000, // 5 minutes
  SETTINGS: 30 * 60 * 1000, // 30 minutes
};

// Maximum items to keep in cache
const MAX_CACHED_TRANSACTIONS = 100;
const MAX_CACHED_BLOCKS = 50;
const MAX_QUEUED_TRANSACTIONS = 20;

// Retry configuration
const MAX_RETRY_ATTEMPTS = 5;
const RETRY_DELAYS = [5000, 15000, 30000, 60000, 120000]; // Exponential backoff

// ============== Storage Keys ==============

const KEYS = {
  NETWORK_STATUS: `${STORAGE_PREFIX}network_status`,
  SYNC_STATUS: `${STORAGE_PREFIX}sync_status`,
  TX_QUEUE: `${STORAGE_PREFIX}tx_queue`,
  CACHE_BALANCE: `${STORAGE_PREFIX}cache_balance_`,
  CACHE_TRANSACTIONS: `${STORAGE_PREFIX}cache_tx_`,
  CACHE_BLOCKS: `${STORAGE_PREFIX}cache_blocks`,
  CACHE_STATS: `${STORAGE_PREFIX}cache_stats`,
  CACHE_MEMPOOL: `${STORAGE_PREFIX}cache_mempool`,
  LAST_SYNC: `${STORAGE_PREFIX}last_sync`,
};

// ============== Network Monitoring ==============

export interface NetworkStatus {
  isConnected: boolean;
  isInternetReachable: boolean | null;
  type: string;
  timestamp: number;
}

let currentNetworkStatus: NetworkStatus = {
  isConnected: true,
  isInternetReachable: true,
  type: 'unknown',
  timestamp: Date.now(),
};

let networkListeners: ((status: NetworkStatus) => void)[] = [];
let unsubscribeNetInfo: (() => void) | null = null;

/**
 * Initialize network monitoring
 */
export function initNetworkMonitoring(): void {
  if (unsubscribeNetInfo) return;

  unsubscribeNetInfo = NetInfo.addEventListener((state: NetInfoState) => {
    const newStatus: NetworkStatus = {
      isConnected: state.isConnected ?? false,
      isInternetReachable: state.isInternetReachable,
      type: state.type,
      timestamp: Date.now(),
    };

    currentNetworkStatus = newStatus;

    // Persist status
    SecureStore.setItemAsync(KEYS.NETWORK_STATUS, JSON.stringify(newStatus)).catch(
      console.error
    );

    // Notify listeners
    networkListeners.forEach((listener) => listener(newStatus));
  });
}

/**
 * Stop network monitoring
 */
export function stopNetworkMonitoring(): void {
  if (unsubscribeNetInfo) {
    unsubscribeNetInfo();
    unsubscribeNetInfo = null;
  }
  networkListeners = [];
}

/**
 * Subscribe to network status changes
 */
export function subscribeToNetworkChanges(
  listener: (status: NetworkStatus) => void
): () => void {
  networkListeners.push(listener);
  // Immediately call with current status
  listener(currentNetworkStatus);

  return () => {
    networkListeners = networkListeners.filter((l) => l !== listener);
  };
}

/**
 * Get current network status
 */
export function getNetworkStatus(): NetworkStatus {
  return currentNetworkStatus;
}

/**
 * Check if online
 */
export function isOnline(): boolean {
  return currentNetworkStatus.isConnected && currentNetworkStatus.isInternetReachable !== false;
}

/**
 * Wait for network connection
 */
export function waitForConnection(timeoutMs: number = 30000): Promise<boolean> {
  return new Promise((resolve) => {
    if (isOnline()) {
      resolve(true);
      return;
    }

    const timeout = setTimeout(() => {
      unsubscribe();
      resolve(false);
    }, timeoutMs);

    const unsubscribe = subscribeToNetworkChanges((status) => {
      if (status.isConnected && status.isInternetReachable !== false) {
        clearTimeout(timeout);
        unsubscribe();
        resolve(true);
      }
    });
  });
}

// ============== Generic Caching ==============

/**
 * Set cached data with expiration
 */
export async function setCachedData<T>(
  key: string,
  data: T,
  durationMs: number
): Promise<void> {
  const cached: CachedData<T> = {
    data,
    timestamp: Date.now(),
    expiresAt: Date.now() + durationMs,
  };

  await SecureStore.setItemAsync(key, JSON.stringify(cached));
}

/**
 * Get cached data (returns null if expired or not found)
 */
export async function getCachedData<T>(key: string): Promise<T | null> {
  try {
    const raw = await SecureStore.getItemAsync(key);
    if (!raw) return null;

    const cached: CachedData<T> = JSON.parse(raw);

    // Check expiration
    if (Date.now() > cached.expiresAt) {
      // Clean up expired cache
      await SecureStore.deleteItemAsync(key);
      return null;
    }

    return cached.data;
  } catch {
    return null;
  }
}

/**
 * Get cached data with metadata
 */
export async function getCachedDataWithMeta<T>(
  key: string
): Promise<CachedData<T> | null> {
  try {
    const raw = await SecureStore.getItemAsync(key);
    if (!raw) return null;

    const cached: CachedData<T> = JSON.parse(raw);
    return cached;
  } catch {
    return null;
  }
}

/**
 * Check if cache is valid
 */
export async function isCacheValid(key: string): Promise<boolean> {
  try {
    const raw = await SecureStore.getItemAsync(key);
    if (!raw) return false;

    const cached = JSON.parse(raw);
    return Date.now() <= cached.expiresAt;
  } catch {
    return false;
  }
}

/**
 * Delete cached data
 */
export async function deleteCachedData(key: string): Promise<void> {
  await SecureStore.deleteItemAsync(key);
}

// ============== Balance Caching ==============

/**
 * Cache balance for an address
 */
export async function cacheBalance(address: string, balance: number): Promise<void> {
  await setCachedData(
    `${KEYS.CACHE_BALANCE}${address.toLowerCase()}`,
    balance,
    CACHE_DURATIONS.BALANCE
  );
}

/**
 * Get cached balance for an address
 */
export async function getCachedBalance(address: string): Promise<number | null> {
  return getCachedData<number>(`${KEYS.CACHE_BALANCE}${address.toLowerCase()}`);
}

// ============== Transaction History Caching ==============

interface TransactionCache {
  address: string;
  transactions: Transaction[];
  total: number;
  lastUpdated: number;
}

/**
 * Cache transaction history for an address
 */
export async function cacheTransactions(
  address: string,
  transactions: Transaction[],
  total: number
): Promise<void> {
  const cache: TransactionCache = {
    address: address.toLowerCase(),
    transactions: transactions.slice(0, MAX_CACHED_TRANSACTIONS),
    total,
    lastUpdated: Date.now(),
  };

  await setCachedData(
    `${KEYS.CACHE_TRANSACTIONS}${address.toLowerCase()}`,
    cache,
    CACHE_DURATIONS.TRANSACTIONS
  );
}

/**
 * Get cached transactions for an address
 */
export async function getCachedTransactions(
  address: string
): Promise<TransactionCache | null> {
  return getCachedData<TransactionCache>(
    `${KEYS.CACHE_TRANSACTIONS}${address.toLowerCase()}`
  );
}

/**
 * Append a new transaction to cache (for optimistic updates)
 */
export async function appendTransactionToCache(
  address: string,
  transaction: Transaction
): Promise<void> {
  const cached = await getCachedTransactions(address);
  if (!cached) return;

  // Prepend new transaction
  const updatedTransactions = [transaction, ...cached.transactions].slice(
    0,
    MAX_CACHED_TRANSACTIONS
  );

  await cacheTransactions(address, updatedTransactions, cached.total + 1);
}

// ============== Block Caching ==============

interface BlockCache {
  blocks: Block[];
  total: number;
  highestBlock: number;
  lastUpdated: number;
}

/**
 * Cache recent blocks
 */
export async function cacheBlocks(blocks: Block[], total: number): Promise<void> {
  const cache: BlockCache = {
    blocks: blocks.slice(0, MAX_CACHED_BLOCKS),
    total,
    highestBlock: blocks.length > 0 ? Math.max(...blocks.map((b) => b.index)) : 0,
    lastUpdated: Date.now(),
  };

  await setCachedData(KEYS.CACHE_BLOCKS, cache, CACHE_DURATIONS.BLOCKS);
}

/**
 * Get cached blocks
 */
export async function getCachedBlocks(): Promise<BlockCache | null> {
  return getCachedData<BlockCache>(KEYS.CACHE_BLOCKS);
}

// ============== Stats Caching ==============

/**
 * Cache blockchain stats
 */
export async function cacheStats(stats: BlockchainStats): Promise<void> {
  await setCachedData(KEYS.CACHE_STATS, stats, CACHE_DURATIONS.STATS);
}

/**
 * Get cached stats
 */
export async function getCachedStats(): Promise<BlockchainStats | null> {
  return getCachedData<BlockchainStats>(KEYS.CACHE_STATS);
}

// ============== Mempool Caching ==============

/**
 * Cache mempool stats
 */
export async function cacheMempoolStats(stats: MempoolStats): Promise<void> {
  await setCachedData(KEYS.CACHE_MEMPOOL, stats, CACHE_DURATIONS.MEMPOOL);
}

/**
 * Get cached mempool stats
 */
export async function getCachedMempoolStats(): Promise<MempoolStats | null> {
  return getCachedData<MempoolStats>(KEYS.CACHE_MEMPOOL);
}

// ============== Transaction Queue ==============

/**
 * Get the transaction queue
 */
export async function getTransactionQueue(): Promise<QueuedTransaction[]> {
  try {
    const raw = await SecureStore.getItemAsync(KEYS.TX_QUEUE);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

/**
 * Save the transaction queue
 */
async function saveTransactionQueue(queue: QueuedTransaction[]): Promise<void> {
  await SecureStore.setItemAsync(KEYS.TX_QUEUE, JSON.stringify(queue));
}

/**
 * Queue a transaction for later sending
 */
export async function queueTransaction(
  transaction: TransactionSendRequest
): Promise<QueuedTransaction> {
  const queue = await getTransactionQueue();

  // Check if we've hit the limit
  if (queue.length >= MAX_QUEUED_TRANSACTIONS) {
    throw new Error('Transaction queue is full');
  }

  const queuedTx: QueuedTransaction = {
    id: `${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
    transaction,
    createdAt: Date.now(),
    retryCount: 0,
    status: 'queued',
  };

  queue.push(queuedTx);
  await saveTransactionQueue(queue);

  return queuedTx;
}

/**
 * Update a queued transaction
 */
export async function updateQueuedTransaction(
  id: string,
  updates: Partial<Pick<QueuedTransaction, 'status' | 'retryCount' | 'lastAttempt' | 'error'>>
): Promise<void> {
  const queue = await getTransactionQueue();
  const index = queue.findIndex((tx) => tx.id === id);

  if (index !== -1) {
    queue[index] = { ...queue[index], ...updates };
    await saveTransactionQueue(queue);
  }
}

/**
 * Remove a transaction from the queue
 */
export async function removeFromQueue(id: string): Promise<void> {
  const queue = await getTransactionQueue();
  const filtered = queue.filter((tx) => tx.id !== id);
  await saveTransactionQueue(filtered);
}

/**
 * Get pending transactions from queue
 */
export async function getPendingQueuedTransactions(): Promise<QueuedTransaction[]> {
  const queue = await getTransactionQueue();
  return queue.filter(
    (tx) => tx.status === 'queued' || (tx.status === 'failed' && tx.retryCount < MAX_RETRY_ATTEMPTS)
  );
}

/**
 * Get retry delay for a queued transaction
 */
export function getRetryDelay(retryCount: number): number {
  return RETRY_DELAYS[Math.min(retryCount, RETRY_DELAYS.length - 1)];
}

/**
 * Clear failed transactions from queue
 */
export async function clearFailedTransactions(): Promise<void> {
  const queue = await getTransactionQueue();
  const filtered = queue.filter((tx) => tx.status !== 'failed');
  await saveTransactionQueue(filtered);
}

// ============== Sync Status ==============

/**
 * Get sync status
 */
export async function getSyncStatus(): Promise<SyncStatus> {
  try {
    const raw = await SecureStore.getItemAsync(KEYS.SYNC_STATUS);
    if (raw) {
      return JSON.parse(raw);
    }
  } catch {
    // Ignore
  }

  // Default status
  return {
    lastSyncTime: 0,
    syncInProgress: false,
    pendingQueueCount: 0,
    failedQueueCount: 0,
    isOnline: isOnline(),
  };
}

/**
 * Update sync status
 */
export async function updateSyncStatus(
  updates: Partial<SyncStatus>
): Promise<SyncStatus> {
  const current = await getSyncStatus();
  const updated = { ...current, ...updates };
  await SecureStore.setItemAsync(KEYS.SYNC_STATUS, JSON.stringify(updated));
  return updated;
}

/**
 * Record last sync time
 */
export async function recordSyncTime(): Promise<void> {
  await SecureStore.setItemAsync(KEYS.LAST_SYNC, Date.now().toString());
  await updateSyncStatus({ lastSyncTime: Date.now() });
}

/**
 * Get last sync time
 */
export async function getLastSyncTime(): Promise<number> {
  try {
    const raw = await SecureStore.getItemAsync(KEYS.LAST_SYNC);
    return raw ? parseInt(raw, 10) : 0;
  } catch {
    return 0;
  }
}

// ============== Cleanup ==============

/**
 * Clear all offline caches
 */
export async function clearAllCaches(): Promise<void> {
  const keysToDelete = [KEYS.CACHE_BLOCKS, KEYS.CACHE_STATS, KEYS.CACHE_MEMPOOL];

  await Promise.all(keysToDelete.map((key) => SecureStore.deleteItemAsync(key)));

  // Note: Balance and transaction caches use dynamic keys
  // They will expire naturally or can be cleared per-address
}

/**
 * Clear all data including queue
 */
export async function clearAllOfflineData(): Promise<void> {
  await clearAllCaches();
  await SecureStore.deleteItemAsync(KEYS.TX_QUEUE);
  await SecureStore.deleteItemAsync(KEYS.SYNC_STATUS);
  await SecureStore.deleteItemAsync(KEYS.LAST_SYNC);
  await SecureStore.deleteItemAsync(KEYS.NETWORK_STATUS);
}

// ============== Utilities ==============

/**
 * Calculate cache age in seconds
 */
export function getCacheAge(timestamp: number): number {
  return Math.floor((Date.now() - timestamp) / 1000);
}

/**
 * Format cache age for display
 */
export function formatCacheAge(timestamp: number): string {
  const ageSeconds = getCacheAge(timestamp);

  if (ageSeconds < 60) {
    return 'just now';
  }
  if (ageSeconds < 3600) {
    const minutes = Math.floor(ageSeconds / 60);
    return `${minutes}m ago`;
  }
  if (ageSeconds < 86400) {
    const hours = Math.floor(ageSeconds / 3600);
    return `${hours}h ago`;
  }

  const days = Math.floor(ageSeconds / 86400);
  return `${days}d ago`;
}

/**
 * Check if data needs refresh based on cache age
 */
export function needsRefresh(
  timestamp: number,
  maxAgeMs: number
): boolean {
  return Date.now() - timestamp > maxAgeMs;
}

// ============== Export Types ==============

export type {
  NetworkStatus,
  TransactionCache,
  BlockCache,
};
