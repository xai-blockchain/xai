/**
 * Wallet Context - Multi-wallet state management with offline support
 *
 * Production-ready features:
 * - Multi-wallet support (create, import, switch, delete)
 * - Mnemonic generation and backup verification
 * - Watch-only wallet support
 * - Offline transaction queue
 * - Balance caching
 * - Network connectivity monitoring
 */

import React, {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  useRef,
} from 'react';
import * as Crypto from 'expo-crypto';
import { AppState, AppStateStatus } from 'react-native';
import { xaiApi } from '../services/api';
import {
  StoredWallet,
  getAllWallets,
  getActiveWallet,
  setActiveWallet,
  saveWallet,
  deleteWallet as removeWallet,
  updateWallet,
  markWalletBackedUp,
  hasWallet,
  getTransactionQueue,
  queueTransaction,
  updateQueuedTransaction,
  removeFromQueue,
  cacheBalance,
  getCachedBalance,
  loadSettings,
  addNotification,
} from '../utils/storage';
import {
  createWallet as generateNewWallet,
  deriveAddress,
  signTransaction,
  generateMnemonic,
  walletFromMnemonic,
} from '../utils/crypto';
import {
  Transaction,
  QueuedTransaction,
  TransactionSendRequest,
  SyncStatus,
  AppSettings,
} from '../types';

// ============== Types ==============

interface WalletBalance {
  [walletId: string]: number;
}

interface WalletState {
  wallets: StoredWallet[];
  activeWallet: StoredWallet | null;
  balances: WalletBalance;
  isLoading: boolean;
  isConnected: boolean;
  isSyncing: boolean;
  error: string | null;
  syncStatus: SyncStatus;
  transactionQueue: QueuedTransaction[];
}

interface WalletContextType extends WalletState {
  // Wallet management
  createWallet: (name?: string) => Promise<{ wallet: StoredWallet; mnemonic: string[] }>;
  importWalletFromMnemonic: (mnemonic: string[], name?: string) => Promise<StoredWallet>;
  importWalletFromPrivateKey: (privateKey: string, name?: string) => Promise<StoredWallet>;
  addWatchOnlyWallet: (address: string, name?: string) => Promise<StoredWallet>;
  switchWallet: (walletId: string) => Promise<void>;
  removeWallet: (walletId: string) => Promise<boolean>;
  renameWallet: (walletId: string, name: string) => Promise<void>;
  verifyBackup: (walletId: string) => Promise<void>;

  // Balance and refresh
  refreshBalance: (walletId?: string) => Promise<void>;
  refreshAllBalances: () => Promise<void>;
  refreshConnection: () => Promise<void>;

  // Transaction queue (offline support)
  sendTransaction: (
    recipient: string,
    amount: number,
    fee: number,
    memo?: string
  ) => Promise<{ txid: string; queued: boolean }>;
  processQueue: () => Promise<void>;
  cancelQueuedTransaction: (queueId: string) => Promise<void>;

  // Sync
  sync: () => Promise<void>;
  clearError: () => void;
}

// ============== Context ==============

const WalletContext = createContext<WalletContextType | undefined>(undefined);

// ============== Constants ==============

const BALANCE_REFRESH_INTERVAL = 30000; // 30 seconds
const QUEUE_RETRY_INTERVAL = 60000; // 1 minute
const MAX_QUEUE_RETRIES = 5;

// ============== Provider ==============

export function WalletProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<WalletState>({
    wallets: [],
    activeWallet: null,
    balances: {},
    isLoading: true,
    isConnected: false,
    isSyncing: false,
    error: null,
    syncStatus: {
      lastSyncTime: 0,
      syncInProgress: false,
      pendingQueueCount: 0,
      failedQueueCount: 0,
      isOnline: false,
    },
    transactionQueue: [],
  });

  const refreshIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const queueIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const appStateRef = useRef<AppStateStatus>(AppState.currentState);

  // ============== Initialization ==============

  useEffect(() => {
    initializeWallets();

    // Handle app state changes
    const subscription = AppState.addEventListener('change', handleAppStateChange);

    return () => {
      subscription.remove();
      if (refreshIntervalRef.current) {
        clearInterval(refreshIntervalRef.current);
      }
      if (queueIntervalRef.current) {
        clearInterval(queueIntervalRef.current);
      }
    };
  }, []);

  // Set up periodic refresh when connected and wallet exists
  useEffect(() => {
    if (state.activeWallet && state.isConnected) {
      // Clear existing interval
      if (refreshIntervalRef.current) {
        clearInterval(refreshIntervalRef.current);
      }

      // Set up new interval
      refreshIntervalRef.current = setInterval(() => {
        refreshBalance();
      }, BALANCE_REFRESH_INTERVAL);

      return () => {
        if (refreshIntervalRef.current) {
          clearInterval(refreshIntervalRef.current);
        }
      };
    }
  }, [state.activeWallet?.id, state.isConnected]);

  // Set up queue processing when connected
  useEffect(() => {
    if (state.isConnected && state.transactionQueue.length > 0) {
      if (queueIntervalRef.current) {
        clearInterval(queueIntervalRef.current);
      }

      queueIntervalRef.current = setInterval(() => {
        processQueue();
      }, QUEUE_RETRY_INTERVAL);

      // Process immediately
      processQueue();

      return () => {
        if (queueIntervalRef.current) {
          clearInterval(queueIntervalRef.current);
        }
      };
    }
  }, [state.isConnected, state.transactionQueue.length]);

  const handleAppStateChange = async (nextAppState: AppStateStatus) => {
    if (
      appStateRef.current.match(/inactive|background/) &&
      nextAppState === 'active'
    ) {
      // App came to foreground - refresh
      await refreshConnection();
      if (state.activeWallet) {
        await refreshBalance();
      }
    }
    appStateRef.current = nextAppState;
  };

  const initializeWallets = async () => {
    try {
      const wallets = await getAllWallets();
      const active = await getActiveWallet();
      const queue = await getTransactionQueue();

      // Load cached balances
      const balances: WalletBalance = {};
      for (const wallet of wallets) {
        const cached = await getCachedBalance(wallet.address);
        if (cached !== null) {
          balances[wallet.id] = cached;
        }
      }

      setState((prev) => ({
        ...prev,
        wallets,
        activeWallet: active,
        balances,
        transactionQueue: queue,
        isLoading: false,
        syncStatus: {
          ...prev.syncStatus,
          pendingQueueCount: queue.filter((q) => q.status === 'queued').length,
          failedQueueCount: queue.filter((q) => q.status === 'failed').length,
        },
      }));

      // Check connection and fetch balances
      await refreshConnection();
      if (active) {
        await refreshBalance(active.id);
      }
    } catch (error) {
      console.error('Failed to initialize wallets:', error);
      setState((prev) => ({
        ...prev,
        isLoading: false,
        error: 'Failed to load wallets',
      }));
    }
  };

  // ============== Wallet Management ==============

  const createWallet = useCallback(async (name?: string) => {
    try {
      setState((prev) => ({ ...prev, isLoading: true, error: null }));

      // Generate mnemonic and derive wallet
      const mnemonic = await generateMnemonic();
      const walletKeys = await walletFromMnemonic(mnemonic);

      const storedWallet = await saveWallet({
        address: walletKeys.address,
        publicKey: walletKeys.publicKey,
        privateKey: walletKeys.privateKey,
        name: name || `Wallet ${state.wallets.length + 1}`,
        isWatchOnly: false,
      });

      // Set as active
      await setActiveWallet(storedWallet.id);

      setState((prev) => ({
        ...prev,
        wallets: [...prev.wallets, storedWallet],
        activeWallet: storedWallet,
        balances: { ...prev.balances, [storedWallet.id]: 0 },
        isLoading: false,
      }));

      // Add backup reminder notification
      await addNotification({
        type: 'backup_reminder',
        title: 'Backup Your Wallet',
        message: 'Please backup your recovery phrase to secure your funds.',
        data: { walletId: storedWallet.id },
      });

      return { wallet: storedWallet, mnemonic };
    } catch (error) {
      console.error('Failed to create wallet:', error);
      setState((prev) => ({
        ...prev,
        isLoading: false,
        error: 'Failed to create wallet',
      }));
      throw error;
    }
  }, [state.wallets.length]);

  const importWalletFromMnemonic = useCallback(async (mnemonic: string[], name?: string) => {
    try {
      setState((prev) => ({ ...prev, isLoading: true, error: null }));

      const walletKeys = await walletFromMnemonic(mnemonic);

      // Check if wallet already exists
      const existing = state.wallets.find(
        (w) => w.address.toLowerCase() === walletKeys.address.toLowerCase()
      );
      if (existing) {
        setState((prev) => ({ ...prev, isLoading: false }));
        throw new Error('Wallet already exists');
      }

      const storedWallet = await saveWallet({
        address: walletKeys.address,
        publicKey: walletKeys.publicKey,
        privateKey: walletKeys.privateKey,
        name: name || `Imported Wallet ${state.wallets.length + 1}`,
        isWatchOnly: false,
      });

      // Mark as backed up since user already has mnemonic
      await markWalletBackedUp(storedWallet.id);
      storedWallet.isBackedUp = true;

      await setActiveWallet(storedWallet.id);

      setState((prev) => ({
        ...prev,
        wallets: [...prev.wallets, storedWallet],
        activeWallet: storedWallet,
        balances: { ...prev.balances, [storedWallet.id]: 0 },
        isLoading: false,
      }));

      // Fetch balance
      await refreshBalance(storedWallet.id);

      return storedWallet;
    } catch (error) {
      console.error('Failed to import wallet:', error);
      setState((prev) => ({
        ...prev,
        isLoading: false,
        error: error instanceof Error ? error.message : 'Failed to import wallet',
      }));
      throw error;
    }
  }, [state.wallets]);

  const importWalletFromPrivateKey = useCallback(async (privateKey: string, name?: string) => {
    try {
      setState((prev) => ({ ...prev, isLoading: true, error: null }));

      // Derive public key and address
      const publicKey = await Crypto.digestStringAsync(
        Crypto.CryptoDigestAlgorithm.SHA256,
        privateKey
      );
      const address = await deriveAddress(publicKey);

      // Check if wallet already exists
      const existing = state.wallets.find(
        (w) => w.address.toLowerCase() === address.toLowerCase()
      );
      if (existing) {
        setState((prev) => ({ ...prev, isLoading: false }));
        throw new Error('Wallet already exists');
      }

      const storedWallet = await saveWallet({
        address,
        publicKey,
        privateKey,
        name: name || `Imported Wallet ${state.wallets.length + 1}`,
        isWatchOnly: false,
      });

      // Mark as backed up since user has private key
      await markWalletBackedUp(storedWallet.id);
      storedWallet.isBackedUp = true;

      await setActiveWallet(storedWallet.id);

      setState((prev) => ({
        ...prev,
        wallets: [...prev.wallets, storedWallet],
        activeWallet: storedWallet,
        balances: { ...prev.balances, [storedWallet.id]: 0 },
        isLoading: false,
      }));

      // Fetch balance
      await refreshBalance(storedWallet.id);

      return storedWallet;
    } catch (error) {
      console.error('Failed to import wallet:', error);
      setState((prev) => ({
        ...prev,
        isLoading: false,
        error: error instanceof Error ? error.message : 'Failed to import wallet',
      }));
      throw error;
    }
  }, [state.wallets]);

  const addWatchOnlyWallet = useCallback(async (address: string, name?: string) => {
    try {
      setState((prev) => ({ ...prev, isLoading: true, error: null }));

      // Check if wallet already exists
      const existing = state.wallets.find(
        (w) => w.address.toLowerCase() === address.toLowerCase()
      );
      if (existing) {
        setState((prev) => ({ ...prev, isLoading: false }));
        throw new Error('Wallet already exists');
      }

      const storedWallet = await saveWallet({
        address,
        publicKey: '', // No public key for watch-only
        name: name || `Watch-Only ${state.wallets.length + 1}`,
        isWatchOnly: true,
      });

      setState((prev) => ({
        ...prev,
        wallets: [...prev.wallets, storedWallet],
        balances: { ...prev.balances, [storedWallet.id]: 0 },
        isLoading: false,
      }));

      // Fetch balance
      await refreshBalance(storedWallet.id);

      return storedWallet;
    } catch (error) {
      console.error('Failed to add watch-only wallet:', error);
      setState((prev) => ({
        ...prev,
        isLoading: false,
        error: error instanceof Error ? error.message : 'Failed to add wallet',
      }));
      throw error;
    }
  }, [state.wallets]);

  const switchWallet = useCallback(async (walletId: string) => {
    const wallet = state.wallets.find((w) => w.id === walletId);
    if (!wallet) {
      throw new Error('Wallet not found');
    }

    await setActiveWallet(walletId);
    setState((prev) => ({ ...prev, activeWallet: wallet }));

    // Refresh balance for new active wallet
    await refreshBalance(walletId);
  }, [state.wallets]);

  const deleteWallet = useCallback(async (walletId: string) => {
    try {
      const success = await removeWallet(walletId);
      if (!success) {
        throw new Error('Failed to delete wallet');
      }

      const newWallets = state.wallets.filter((w) => w.id !== walletId);
      const newBalances = { ...state.balances };
      delete newBalances[walletId];

      let newActive = state.activeWallet;
      if (state.activeWallet?.id === walletId) {
        newActive = newWallets.length > 0 ? newWallets[0] : null;
        if (newActive) {
          await setActiveWallet(newActive.id);
        }
      }

      setState((prev) => ({
        ...prev,
        wallets: newWallets,
        activeWallet: newActive,
        balances: newBalances,
      }));

      return true;
    } catch (error) {
      console.error('Failed to delete wallet:', error);
      return false;
    }
  }, [state.wallets, state.activeWallet, state.balances]);

  const renameWallet = useCallback(async (walletId: string, name: string) => {
    await updateWallet(walletId, { name });

    setState((prev) => ({
      ...prev,
      wallets: prev.wallets.map((w) =>
        w.id === walletId ? { ...w, name } : w
      ),
      activeWallet:
        prev.activeWallet?.id === walletId
          ? { ...prev.activeWallet, name }
          : prev.activeWallet,
    }));
  }, []);

  const verifyBackup = useCallback(async (walletId: string) => {
    await markWalletBackedUp(walletId);

    setState((prev) => ({
      ...prev,
      wallets: prev.wallets.map((w) =>
        w.id === walletId ? { ...w, isBackedUp: true } : w
      ),
      activeWallet:
        prev.activeWallet?.id === walletId
          ? { ...prev.activeWallet, isBackedUp: true }
          : prev.activeWallet,
    }));
  }, []);

  // ============== Balance Operations ==============

  const refreshBalance = useCallback(async (walletId?: string) => {
    const targetId = walletId || state.activeWallet?.id;
    const wallet = state.wallets.find((w) => w.id === targetId);
    if (!wallet) return;

    try {
      const result = await xaiApi.getBalance(wallet.address);
      if (result.success && result.data) {
        const balance = result.data.balance;

        // Cache the balance
        await cacheBalance(wallet.address, balance);

        setState((prev) => ({
          ...prev,
          balances: { ...prev.balances, [wallet.id]: balance },
          isConnected: true,
          syncStatus: {
            ...prev.syncStatus,
            lastSyncTime: Date.now(),
            isOnline: true,
          },
        }));
      }
    } catch (error) {
      console.error('Failed to refresh balance:', error);
      setState((prev) => ({
        ...prev,
        isConnected: false,
        syncStatus: { ...prev.syncStatus, isOnline: false },
      }));
    }
  }, [state.activeWallet, state.wallets]);

  const refreshAllBalances = useCallback(async () => {
    setState((prev) => ({ ...prev, isSyncing: true }));

    try {
      const balancePromises = state.wallets.map(async (wallet) => {
        try {
          const result = await xaiApi.getBalance(wallet.address);
          if (result.success && result.data) {
            await cacheBalance(wallet.address, result.data.balance);
            return { id: wallet.id, balance: result.data.balance };
          }
        } catch (error) {
          // Use cached balance if available
          const cached = await getCachedBalance(wallet.address);
          if (cached !== null) {
            return { id: wallet.id, balance: cached };
          }
        }
        return null;
      });

      const results = await Promise.all(balancePromises);
      const newBalances: WalletBalance = { ...state.balances };

      for (const result of results) {
        if (result) {
          newBalances[result.id] = result.balance;
        }
      }

      setState((prev) => ({
        ...prev,
        balances: newBalances,
        isSyncing: false,
        syncStatus: {
          ...prev.syncStatus,
          lastSyncTime: Date.now(),
        },
      }));
    } catch (error) {
      console.error('Failed to refresh all balances:', error);
      setState((prev) => ({ ...prev, isSyncing: false }));
    }
  }, [state.wallets, state.balances]);

  const refreshConnection = useCallback(async () => {
    try {
      const result = await xaiApi.getHealth();
      const isConnected = result.success && result.data?.status !== 'unhealthy';

      setState((prev) => ({
        ...prev,
        isConnected,
        syncStatus: { ...prev.syncStatus, isOnline: isConnected },
      }));

      return isConnected;
    } catch (error) {
      setState((prev) => ({
        ...prev,
        isConnected: false,
        syncStatus: { ...prev.syncStatus, isOnline: false },
      }));
      return false;
    }
  }, []);

  // ============== Transaction Operations ==============

  const sendTransaction = useCallback(async (
    recipient: string,
    amount: number,
    fee: number,
    memo?: string
  ): Promise<{ txid: string; queued: boolean }> => {
    if (!state.activeWallet) {
      throw new Error('No active wallet');
    }

    if (state.activeWallet.isWatchOnly) {
      throw new Error('Cannot send from watch-only wallet');
    }

    const wallet = state.activeWallet;

    try {
      // Get nonce
      const nonceResult = await xaiApi.getNonce(wallet.address);
      if (!nonceResult.success || !nonceResult.data) {
        throw new Error('Failed to get nonce');
      }

      const nonce = nonceResult.data.nextNonce;
      const timestamp = Math.floor(Date.now() / 1000);

      // Create transaction
      const tx = {
        sender: wallet.address,
        recipient,
        amount,
        fee,
        nonce,
        timestamp,
      };

      // Sign transaction
      const signature = await signTransaction(tx, wallet.privateKey!);

      const txRequest: TransactionSendRequest = {
        ...tx,
        publicKey: wallet.publicKey,
        signature,
      };

      // Try to send
      if (state.isConnected) {
        const result = await xaiApi.sendTransaction(txRequest);
        if (result.success && result.data) {
          // Update balance
          setState((prev) => ({
            ...prev,
            balances: {
              ...prev.balances,
              [wallet.id]: Math.max(0, prev.balances[wallet.id] - amount - fee),
            },
          }));

          // Add notification
          await addNotification({
            type: 'transaction_confirmed',
            title: 'Transaction Sent',
            message: `Sent ${amount} XAI`,
            data: { txid: result.data.txid, recipient, amount },
          });

          return { txid: result.data.txid, queued: false };
        } else {
          throw new Error(result.error || 'Transaction failed');
        }
      } else {
        // Queue for later
        const queued = await queueTransaction(txRequest);

        setState((prev) => ({
          ...prev,
          transactionQueue: [...prev.transactionQueue, queued],
          syncStatus: {
            ...prev.syncStatus,
            pendingQueueCount: prev.syncStatus.pendingQueueCount + 1,
          },
        }));

        return { txid: `queued_${queued.id}`, queued: true };
      }
    } catch (error) {
      console.error('Failed to send transaction:', error);
      throw error;
    }
  }, [state.activeWallet, state.isConnected]);

  const processQueue = useCallback(async () => {
    if (!state.isConnected) return;

    const pendingTxs = state.transactionQueue.filter(
      (q) => q.status === 'queued' || (q.status === 'failed' && q.retryCount < MAX_QUEUE_RETRIES)
    );

    for (const queued of pendingTxs) {
      try {
        await updateQueuedTransaction(queued.id, {
          status: 'sending',
          lastAttempt: Date.now(),
        });

        const result = await xaiApi.sendTransaction(queued.transaction);

        if (result.success && result.data) {
          await removeFromQueue(queued.id);

          setState((prev) => ({
            ...prev,
            transactionQueue: prev.transactionQueue.filter((q) => q.id !== queued.id),
            syncStatus: {
              ...prev.syncStatus,
              pendingQueueCount: Math.max(0, prev.syncStatus.pendingQueueCount - 1),
            },
          }));

          await addNotification({
            type: 'transaction_confirmed',
            title: 'Queued Transaction Sent',
            message: `Transaction ${result.data.txid.substring(0, 10)}... has been sent`,
            data: { txid: result.data.txid },
          });
        } else {
          throw new Error(result.error || 'Transaction failed');
        }
      } catch (error) {
        const newRetryCount = queued.retryCount + 1;
        const newStatus = newRetryCount >= MAX_QUEUE_RETRIES ? 'failed' : 'queued';

        await updateQueuedTransaction(queued.id, {
          status: newStatus,
          retryCount: newRetryCount,
          error: error instanceof Error ? error.message : 'Unknown error',
        });

        setState((prev) => ({
          ...prev,
          transactionQueue: prev.transactionQueue.map((q) =>
            q.id === queued.id
              ? { ...q, status: newStatus, retryCount: newRetryCount }
              : q
          ),
          syncStatus: {
            ...prev.syncStatus,
            failedQueueCount:
              newStatus === 'failed'
                ? prev.syncStatus.failedQueueCount + 1
                : prev.syncStatus.failedQueueCount,
          },
        }));
      }
    }
  }, [state.isConnected, state.transactionQueue]);

  const cancelQueuedTransaction = useCallback(async (queueId: string) => {
    await removeFromQueue(queueId);

    setState((prev) => ({
      ...prev,
      transactionQueue: prev.transactionQueue.filter((q) => q.id !== queueId),
      syncStatus: {
        ...prev.syncStatus,
        pendingQueueCount: Math.max(0, prev.syncStatus.pendingQueueCount - 1),
      },
    }));
  }, []);

  // ============== Sync Operations ==============

  const sync = useCallback(async () => {
    setState((prev) => ({
      ...prev,
      isSyncing: true,
      syncStatus: { ...prev.syncStatus, syncInProgress: true },
    }));

    try {
      await refreshConnection();
      await refreshAllBalances();
      await processQueue();

      setState((prev) => ({
        ...prev,
        isSyncing: false,
        syncStatus: {
          ...prev.syncStatus,
          syncInProgress: false,
          lastSyncTime: Date.now(),
        },
      }));
    } catch (error) {
      console.error('Sync failed:', error);
      setState((prev) => ({
        ...prev,
        isSyncing: false,
        syncStatus: {
          ...prev.syncStatus,
          syncInProgress: false,
          syncError: error instanceof Error ? error.message : 'Sync failed',
        },
      }));
    }
  }, [refreshConnection, refreshAllBalances, processQueue]);

  const clearError = useCallback(() => {
    setState((prev) => ({ ...prev, error: null }));
  }, []);

  // ============== Context Value ==============

  const activeBalance = state.activeWallet
    ? state.balances[state.activeWallet.id] || 0
    : 0;

  return (
    <WalletContext.Provider
      value={{
        ...state,
        // Convenience accessor for active wallet balance
        balances: state.balances,

        // Wallet management
        createWallet,
        importWalletFromMnemonic,
        importWalletFromPrivateKey,
        addWatchOnlyWallet,
        switchWallet,
        removeWallet: deleteWallet,
        renameWallet,
        verifyBackup,

        // Balance and refresh
        refreshBalance,
        refreshAllBalances,
        refreshConnection,

        // Transaction queue
        sendTransaction,
        processQueue,
        cancelQueuedTransaction,

        // Sync
        sync,
        clearError,
      }}
    >
      {children}
    </WalletContext.Provider>
  );
}

// ============== Hook ==============

export function useWallet() {
  const context = useContext(WalletContext);
  if (context === undefined) {
    throw new Error('useWallet must be used within a WalletProvider');
  }
  return context;
}

// ============== Convenience Hooks ==============

export function useActiveWallet() {
  const { activeWallet, balances } = useWallet();
  const balance = activeWallet ? balances[activeWallet.id] || 0 : 0;
  return { wallet: activeWallet, balance };
}

export function useWalletList() {
  const { wallets, balances } = useWallet();
  return wallets.map((wallet) => ({
    ...wallet,
    balance: balances[wallet.id] || 0,
  }));
}

export function useSyncStatus() {
  const { syncStatus, isConnected, isSyncing, transactionQueue } = useWallet();
  return {
    ...syncStatus,
    isConnected,
    isSyncing,
    queuedTransactions: transactionQueue.filter((q) => q.status === 'queued'),
    failedTransactions: transactionQueue.filter((q) => q.status === 'failed'),
  };
}
