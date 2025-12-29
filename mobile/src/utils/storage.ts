/**
 * Secure Storage Manager for XAI Mobile App
 *
 * Production-ready storage with:
 * - Multi-wallet support
 * - Offline transaction queue
 * - Data caching with expiration
 * - Contact management
 * - Notification storage
 */

import * as SecureStore from 'expo-secure-store';
import {
  Wallet,
  WalletColor,
  Contact,
  QueuedTransaction,
  AppSettings,
  AppNotification,
  CachedData,
  Transaction,
  TransactionSendRequest,
} from '../types';
import * as Crypto from 'expo-crypto';

// ============== Storage Keys ==============

const STORAGE_KEYS = {
  // Wallet keys (per wallet)
  WALLET_LIST: 'xai_wallet_list',
  WALLET_PREFIX: 'xai_wallet_',
  ACTIVE_WALLET: 'xai_active_wallet',

  // Contacts
  CONTACTS: 'xai_contacts',

  // Transaction queue (offline support)
  TX_QUEUE: 'xai_tx_queue',

  // Cache
  CACHE_PREFIX: 'xai_cache_',

  // Settings
  SETTINGS: 'xai_settings',

  // Notifications
  NOTIFICATIONS: 'xai_notifications',

  // Transaction history cache per address
  TX_HISTORY_PREFIX: 'xai_tx_history_',

  // Sync state
  SYNC_STATE: 'xai_sync_state',
};

// ============== Default Values ==============

const DEFAULT_SETTINGS: AppSettings = {
  nodeUrl: 'http://localhost:12001',
  theme: 'dark',
  currency: 'USD',
  language: 'en',
  notifications: {
    enabled: true,
    incomingTransactions: true,
    outgoingConfirmations: true,
    priceAlerts: false,
    networkAlerts: true,
    soundEnabled: true,
    vibrationEnabled: true,
  },
  security: {
    biometricEnabled: false,
    pinEnabled: false,
    autoLockTimeout: 5,
    hideBalance: false,
    requireAuthForSend: true,
    requireAuthForExport: true,
  },
  display: {
    showFiatValue: false,
    defaultFeeLevel: 'standard',
    confirmationThreshold: 6,
    compactTransactionList: false,
  },
};

const WALLET_COLORS: WalletColor[] = [
  'indigo',
  'emerald',
  'amber',
  'rose',
  'cyan',
  'purple',
];

// ============== Utility Functions ==============

async function generateId(): Promise<string> {
  const bytes = await Crypto.getRandomBytesAsync(16);
  return Array.from(bytes)
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('');
}

function getNextColor(usedColors: WalletColor[]): WalletColor {
  const colorCounts = WALLET_COLORS.reduce(
    (acc, color) => {
      acc[color] = usedColors.filter((c) => c === color).length;
      return acc;
    },
    {} as Record<WalletColor, number>
  );

  return WALLET_COLORS.reduce((min, color) =>
    colorCounts[color] < colorCounts[min] ? color : min
  );
}

// ============== Wallet Storage ==============

export interface StoredWallet {
  id: string;
  name: string;
  address: string;
  publicKey: string;
  privateKey?: string;
  createdAt: number;
  isWatchOnly: boolean;
  isBackedUp: boolean;
  color: WalletColor;
}

/**
 * Get list of wallet IDs
 */
export async function getWalletList(): Promise<string[]> {
  try {
    const data = await SecureStore.getItemAsync(STORAGE_KEYS.WALLET_LIST);
    return data ? JSON.parse(data) : [];
  } catch (error) {
    console.error('Failed to get wallet list:', error);
    return [];
  }
}

/**
 * Get all wallets
 */
export async function getAllWallets(): Promise<StoredWallet[]> {
  try {
    const ids = await getWalletList();
    const wallets = await Promise.all(
      ids.map((id) => getWallet(id))
    );
    return wallets.filter((w): w is StoredWallet => w !== null);
  } catch (error) {
    console.error('Failed to get all wallets:', error);
    return [];
  }
}

/**
 * Get a specific wallet
 */
export async function getWallet(id: string): Promise<StoredWallet | null> {
  try {
    const data = await SecureStore.getItemAsync(
      `${STORAGE_KEYS.WALLET_PREFIX}${id}`
    );
    return data ? JSON.parse(data) : null;
  } catch (error) {
    console.error('Failed to get wallet:', error);
    return null;
  }
}

/**
 * Save a new wallet
 */
export async function saveWallet(wallet: {
  address: string;
  publicKey: string;
  privateKey?: string;
  name?: string;
  isWatchOnly?: boolean;
}): Promise<StoredWallet> {
  const id = await generateId();
  const existingWallets = await getAllWallets();
  const usedColors = existingWallets.map((w) => w.color);

  const storedWallet: StoredWallet = {
    id,
    name: wallet.name || `Wallet ${existingWallets.length + 1}`,
    address: wallet.address,
    publicKey: wallet.publicKey,
    privateKey: wallet.privateKey,
    createdAt: Date.now(),
    isWatchOnly: wallet.isWatchOnly ?? !wallet.privateKey,
    isBackedUp: wallet.isWatchOnly ?? false,
    color: getNextColor(usedColors),
  };

  // Save wallet
  await SecureStore.setItemAsync(
    `${STORAGE_KEYS.WALLET_PREFIX}${id}`,
    JSON.stringify(storedWallet)
  );

  // Update wallet list
  const ids = await getWalletList();
  ids.push(id);
  await SecureStore.setItemAsync(
    STORAGE_KEYS.WALLET_LIST,
    JSON.stringify(ids)
  );

  // Set as active if first wallet
  if (ids.length === 1) {
    await setActiveWallet(id);
  }

  return storedWallet;
}

/**
 * Update wallet properties
 */
export async function updateWallet(
  id: string,
  updates: Partial<Omit<StoredWallet, 'id' | 'address' | 'publicKey' | 'createdAt'>>
): Promise<StoredWallet | null> {
  const wallet = await getWallet(id);
  if (!wallet) return null;

  const updated = { ...wallet, ...updates };
  await SecureStore.setItemAsync(
    `${STORAGE_KEYS.WALLET_PREFIX}${id}`,
    JSON.stringify(updated)
  );

  return updated;
}

/**
 * Delete a wallet
 */
export async function deleteWallet(id: string): Promise<boolean> {
  try {
    // Remove wallet data
    await SecureStore.deleteItemAsync(`${STORAGE_KEYS.WALLET_PREFIX}${id}`);

    // Update wallet list
    const ids = await getWalletList();
    const newIds = ids.filter((i) => i !== id);
    await SecureStore.setItemAsync(
      STORAGE_KEYS.WALLET_LIST,
      JSON.stringify(newIds)
    );

    // Update active wallet if needed
    const activeId = await getActiveWalletId();
    if (activeId === id && newIds.length > 0) {
      await setActiveWallet(newIds[0]);
    } else if (newIds.length === 0) {
      await SecureStore.deleteItemAsync(STORAGE_KEYS.ACTIVE_WALLET);
    }

    return true;
  } catch (error) {
    console.error('Failed to delete wallet:', error);
    return false;
  }
}

/**
 * Get active wallet ID
 */
export async function getActiveWalletId(): Promise<string | null> {
  try {
    return await SecureStore.getItemAsync(STORAGE_KEYS.ACTIVE_WALLET);
  } catch (error) {
    console.error('Failed to get active wallet:', error);
    return null;
  }
}

/**
 * Set active wallet
 */
export async function setActiveWallet(id: string): Promise<void> {
  await SecureStore.setItemAsync(STORAGE_KEYS.ACTIVE_WALLET, id);
}

/**
 * Get active wallet
 */
export async function getActiveWallet(): Promise<StoredWallet | null> {
  const id = await getActiveWalletId();
  if (!id) return null;
  return getWallet(id);
}

/**
 * Check if any wallet exists
 */
export async function hasWallet(): Promise<boolean> {
  const ids = await getWalletList();
  return ids.length > 0;
}

/**
 * Mark wallet as backed up
 */
export async function markWalletBackedUp(id: string): Promise<void> {
  await updateWallet(id, { isBackedUp: true });
}

/**
 * Legacy support: load single wallet
 */
export async function loadWallet(): Promise<StoredWallet | null> {
  return getActiveWallet();
}

// ============== Contacts Storage ==============

/**
 * Get all contacts
 */
export async function getContacts(): Promise<Contact[]> {
  try {
    const data = await SecureStore.getItemAsync(STORAGE_KEYS.CONTACTS);
    return data ? JSON.parse(data) : [];
  } catch (error) {
    console.error('Failed to get contacts:', error);
    return [];
  }
}

/**
 * Get contact by ID
 */
export async function getContact(id: string): Promise<Contact | null> {
  const contacts = await getContacts();
  return contacts.find((c) => c.id === id) || null;
}

/**
 * Get contact by address
 */
export async function getContactByAddress(address: string): Promise<Contact | null> {
  const contacts = await getContacts();
  return contacts.find((c) => c.address.toLowerCase() === address.toLowerCase()) || null;
}

/**
 * Save a new contact
 */
export async function saveContact(contact: Omit<Contact, 'id' | 'createdAt' | 'transactionCount'>): Promise<Contact> {
  const contacts = await getContacts();
  const id = await generateId();

  const newContact: Contact = {
    ...contact,
    id,
    createdAt: Date.now(),
    transactionCount: 0,
  };

  contacts.push(newContact);
  await SecureStore.setItemAsync(STORAGE_KEYS.CONTACTS, JSON.stringify(contacts));

  return newContact;
}

/**
 * Update a contact
 */
export async function updateContact(
  id: string,
  updates: Partial<Omit<Contact, 'id' | 'createdAt'>>
): Promise<Contact | null> {
  const contacts = await getContacts();
  const index = contacts.findIndex((c) => c.id === id);
  if (index === -1) return null;

  contacts[index] = { ...contacts[index], ...updates };
  await SecureStore.setItemAsync(STORAGE_KEYS.CONTACTS, JSON.stringify(contacts));

  return contacts[index];
}

/**
 * Delete a contact
 */
export async function deleteContact(id: string): Promise<boolean> {
  try {
    const contacts = await getContacts();
    const filtered = contacts.filter((c) => c.id !== id);
    await SecureStore.setItemAsync(STORAGE_KEYS.CONTACTS, JSON.stringify(filtered));
    return true;
  } catch (error) {
    console.error('Failed to delete contact:', error);
    return false;
  }
}

/**
 * Increment contact transaction count
 */
export async function incrementContactTransactionCount(address: string): Promise<void> {
  const contact = await getContactByAddress(address);
  if (contact) {
    await updateContact(contact.id, {
      transactionCount: contact.transactionCount + 1,
      lastUsed: Date.now(),
    });
  }
}

/**
 * Search contacts
 */
export async function searchContacts(query: string): Promise<Contact[]> {
  const contacts = await getContacts();
  const lowerQuery = query.toLowerCase();
  return contacts.filter(
    (c) =>
      c.name.toLowerCase().includes(lowerQuery) ||
      c.address.toLowerCase().includes(lowerQuery) ||
      c.label?.toLowerCase().includes(lowerQuery)
  );
}

// ============== Transaction Queue (Offline Support) ==============

/**
 * Get pending transaction queue
 */
export async function getTransactionQueue(): Promise<QueuedTransaction[]> {
  try {
    const data = await SecureStore.getItemAsync(STORAGE_KEYS.TX_QUEUE);
    return data ? JSON.parse(data) : [];
  } catch (error) {
    console.error('Failed to get transaction queue:', error);
    return [];
  }
}

/**
 * Add transaction to queue
 */
export async function queueTransaction(
  transaction: TransactionSendRequest
): Promise<QueuedTransaction> {
  const queue = await getTransactionQueue();
  const id = await generateId();

  const queued: QueuedTransaction = {
    id,
    transaction,
    createdAt: Date.now(),
    retryCount: 0,
    status: 'queued',
  };

  queue.push(queued);
  await SecureStore.setItemAsync(STORAGE_KEYS.TX_QUEUE, JSON.stringify(queue));

  return queued;
}

/**
 * Update queued transaction status
 */
export async function updateQueuedTransaction(
  id: string,
  updates: Partial<Pick<QueuedTransaction, 'status' | 'retryCount' | 'lastAttempt' | 'error'>>
): Promise<void> {
  const queue = await getTransactionQueue();
  const index = queue.findIndex((q) => q.id === id);
  if (index !== -1) {
    queue[index] = { ...queue[index], ...updates };
    await SecureStore.setItemAsync(STORAGE_KEYS.TX_QUEUE, JSON.stringify(queue));
  }
}

/**
 * Remove transaction from queue
 */
export async function removeFromQueue(id: string): Promise<void> {
  const queue = await getTransactionQueue();
  const filtered = queue.filter((q) => q.id !== id);
  await SecureStore.setItemAsync(STORAGE_KEYS.TX_QUEUE, JSON.stringify(filtered));
}

/**
 * Clear failed transactions from queue
 */
export async function clearFailedFromQueue(): Promise<void> {
  const queue = await getTransactionQueue();
  const filtered = queue.filter((q) => q.status !== 'failed');
  await SecureStore.setItemAsync(STORAGE_KEYS.TX_QUEUE, JSON.stringify(filtered));
}

/**
 * Get queue statistics
 */
export async function getQueueStats(): Promise<{
  pending: number;
  failed: number;
  sending: number;
}> {
  const queue = await getTransactionQueue();
  return {
    pending: queue.filter((q) => q.status === 'queued').length,
    failed: queue.filter((q) => q.status === 'failed').length,
    sending: queue.filter((q) => q.status === 'sending').length,
  };
}

// ============== Cache Storage ==============

const CACHE_DURATIONS = {
  balance: 30 * 1000, // 30 seconds
  transactions: 60 * 1000, // 1 minute
  blocks: 30 * 1000, // 30 seconds
  stats: 15 * 1000, // 15 seconds
  mempool: 10 * 1000, // 10 seconds
};

/**
 * Set cached data
 */
export async function setCachedData<T>(
  key: string,
  data: T,
  durationMs: number = 60000
): Promise<void> {
  const cached: CachedData<T> = {
    data,
    timestamp: Date.now(),
    expiresAt: Date.now() + durationMs,
  };
  await SecureStore.setItemAsync(
    `${STORAGE_KEYS.CACHE_PREFIX}${key}`,
    JSON.stringify(cached)
  );
}

/**
 * Get cached data (returns null if expired)
 */
export async function getCachedData<T>(key: string): Promise<T | null> {
  try {
    const data = await SecureStore.getItemAsync(`${STORAGE_KEYS.CACHE_PREFIX}${key}`);
    if (!data) return null;

    const cached: CachedData<T> = JSON.parse(data);
    if (Date.now() > cached.expiresAt) {
      // Expired, clean up
      await SecureStore.deleteItemAsync(`${STORAGE_KEYS.CACHE_PREFIX}${key}`);
      return null;
    }

    return cached.data;
  } catch (error) {
    return null;
  }
}

/**
 * Cache balance for an address
 */
export async function cacheBalance(address: string, balance: number): Promise<void> {
  await setCachedData(`balance_${address}`, balance, CACHE_DURATIONS.balance);
}

/**
 * Get cached balance
 */
export async function getCachedBalance(address: string): Promise<number | null> {
  return getCachedData<number>(`balance_${address}`);
}

/**
 * Cache transaction history
 */
export async function cacheTransactionHistory(
  address: string,
  transactions: Transaction[]
): Promise<void> {
  await setCachedData(
    `tx_history_${address}`,
    transactions,
    CACHE_DURATIONS.transactions
  );
}

/**
 * Get cached transaction history
 */
export async function getCachedTransactionHistory(
  address: string
): Promise<Transaction[] | null> {
  return getCachedData<Transaction[]>(`tx_history_${address}`);
}

/**
 * Clear all cache
 */
export async function clearCache(): Promise<void> {
  // Note: SecureStore doesn't have a way to list keys, so we track known cache keys
  const knownCacheKeys = ['stats', 'blocks', 'mempool'];
  for (const key of knownCacheKeys) {
    await SecureStore.deleteItemAsync(`${STORAGE_KEYS.CACHE_PREFIX}${key}`);
  }
}

// ============== Settings Storage ==============

/**
 * Get app settings
 */
export async function loadSettings(): Promise<AppSettings> {
  try {
    const data = await SecureStore.getItemAsync(STORAGE_KEYS.SETTINGS);
    if (data) {
      const stored = JSON.parse(data);
      // Merge with defaults to handle new settings
      return {
        ...DEFAULT_SETTINGS,
        ...stored,
        notifications: { ...DEFAULT_SETTINGS.notifications, ...stored.notifications },
        security: { ...DEFAULT_SETTINGS.security, ...stored.security },
        display: { ...DEFAULT_SETTINGS.display, ...stored.display },
      };
    }
  } catch (error) {
    console.error('Failed to load settings:', error);
  }
  return DEFAULT_SETTINGS;
}

/**
 * Save app settings
 */
export async function saveSettings(settings: Partial<AppSettings>): Promise<void> {
  const current = await loadSettings();
  const merged = {
    ...current,
    ...settings,
    notifications: { ...current.notifications, ...settings.notifications },
    security: { ...current.security, ...settings.security },
    display: { ...current.display, ...settings.display },
  };
  await SecureStore.setItemAsync(STORAGE_KEYS.SETTINGS, JSON.stringify(merged));
}

/**
 * Reset settings to defaults
 */
export async function resetSettings(): Promise<void> {
  await SecureStore.setItemAsync(
    STORAGE_KEYS.SETTINGS,
    JSON.stringify(DEFAULT_SETTINGS)
  );
}

// ============== Notifications Storage ==============

const MAX_NOTIFICATIONS = 100;

/**
 * Get all notifications
 */
export async function getNotifications(): Promise<AppNotification[]> {
  try {
    const data = await SecureStore.getItemAsync(STORAGE_KEYS.NOTIFICATIONS);
    return data ? JSON.parse(data) : [];
  } catch (error) {
    console.error('Failed to get notifications:', error);
    return [];
  }
}

/**
 * Add a notification
 */
export async function addNotification(
  notification: Omit<AppNotification, 'id' | 'timestamp' | 'read'>
): Promise<AppNotification> {
  const notifications = await getNotifications();
  const id = await generateId();

  const newNotification: AppNotification = {
    ...notification,
    id,
    timestamp: Date.now(),
    read: false,
  };

  // Add to beginning and limit size
  notifications.unshift(newNotification);
  const trimmed = notifications.slice(0, MAX_NOTIFICATIONS);

  await SecureStore.setItemAsync(
    STORAGE_KEYS.NOTIFICATIONS,
    JSON.stringify(trimmed)
  );

  return newNotification;
}

/**
 * Mark notification as read
 */
export async function markNotificationRead(id: string): Promise<void> {
  const notifications = await getNotifications();
  const index = notifications.findIndex((n) => n.id === id);
  if (index !== -1) {
    notifications[index].read = true;
    await SecureStore.setItemAsync(
      STORAGE_KEYS.NOTIFICATIONS,
      JSON.stringify(notifications)
    );
  }
}

/**
 * Mark all notifications as read
 */
export async function markAllNotificationsRead(): Promise<void> {
  const notifications = await getNotifications();
  notifications.forEach((n) => (n.read = true));
  await SecureStore.setItemAsync(
    STORAGE_KEYS.NOTIFICATIONS,
    JSON.stringify(notifications)
  );
}

/**
 * Delete a notification
 */
export async function deleteNotification(id: string): Promise<void> {
  const notifications = await getNotifications();
  const filtered = notifications.filter((n) => n.id !== id);
  await SecureStore.setItemAsync(
    STORAGE_KEYS.NOTIFICATIONS,
    JSON.stringify(filtered)
  );
}

/**
 * Clear all notifications
 */
export async function clearNotifications(): Promise<void> {
  await SecureStore.setItemAsync(STORAGE_KEYS.NOTIFICATIONS, JSON.stringify([]));
}

/**
 * Get unread notification count
 */
export async function getUnreadNotificationCount(): Promise<number> {
  const notifications = await getNotifications();
  return notifications.filter((n) => !n.read).length;
}

// ============== Export Private Key ==============

/**
 * Export wallet private key (requires wallet ID)
 */
export async function exportPrivateKey(walletId: string): Promise<string | null> {
  const wallet = await getWallet(walletId);
  return wallet?.privateKey || null;
}

// ============== Data Export/Import ==============

export interface ExportedData {
  version: number;
  exportedAt: number;
  contacts: Contact[];
  settings: AppSettings;
  notifications: AppNotification[];
}

/**
 * Export all non-sensitive data
 */
export async function exportData(): Promise<ExportedData> {
  return {
    version: 1,
    exportedAt: Date.now(),
    contacts: await getContacts(),
    settings: await loadSettings(),
    notifications: await getNotifications(),
  };
}

/**
 * Import data (merges with existing)
 */
export async function importData(data: ExportedData): Promise<void> {
  // Import contacts (skip duplicates by address)
  const existingContacts = await getContacts();
  const existingAddresses = new Set(existingContacts.map((c) => c.address.toLowerCase()));

  for (const contact of data.contacts) {
    if (!existingAddresses.has(contact.address.toLowerCase())) {
      await saveContact(contact);
    }
  }

  // Import settings (merge)
  await saveSettings(data.settings);
}
