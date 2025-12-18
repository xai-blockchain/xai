import { create } from 'zustand';
import { Wallet, Transaction, PendingTransaction } from '@/types';
import { WalletStorage, Storage } from '@/utils/storage';
import { STORAGE_KEYS } from '@/constants';
import APIService from '@/services/api';
import WebSocketService from '@/services/websocket';
import { generateWallet, importWalletFromMnemonic, importWalletFromPrivateKey } from '@/utils/crypto';

interface WalletState {
  wallet: Wallet | null;
  balance: number;
  isLoading: boolean;
  error: string | null;
  pendingTransactions: PendingTransaction[];

  // Actions
  createWallet: () => Promise<{ success: boolean; mnemonic?: string; error?: string }>;
  importWallet: (method: 'mnemonic' | 'privateKey', value: string) => Promise<{ success: boolean; error?: string }>;
  loadWallet: () => Promise<void>;
  deleteWallet: () => Promise<void>;
  refreshBalance: () => Promise<void>;
  addPendingTransaction: (tx: PendingTransaction) => Promise<void>;
  removePendingTransaction: (txid: string) => Promise<void>;
  syncPendingTransactions: () => Promise<void>;
  setError: (error: string | null) => void;
}

export const useWalletStore = create<WalletState>((set, get) => ({
  wallet: null,
  balance: 0,
  isLoading: false,
  error: null,
  pendingTransactions: [],

  createWallet: async () => {
    set({ isLoading: true, error: null });
    try {
      const { mnemonic, keyPair } = await generateWallet();

      const newWallet: Wallet = {
        address: keyPair.address,
        publicKey: keyPair.publicKey,
        privateKey: keyPair.privateKey,
        mnemonic,
        createdAt: Date.now(),
        balance: 0,
      };

      await WalletStorage.saveWallet(newWallet);
      set({ wallet: newWallet, isLoading: false });

      // Subscribe to wallet updates
      WebSocketService.subscribeToAddress(newWallet.address);

      return { success: true, mnemonic };
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : 'Failed to create wallet';
      set({ error: errorMsg, isLoading: false });
      return { success: false, error: errorMsg };
    }
  },

  importWallet: async (method, value) => {
    set({ isLoading: true, error: null });
    try {
      let keyPair;
      let mnemonic: string | undefined;

      if (method === 'mnemonic') {
        keyPair = await importWalletFromMnemonic(value);
        mnemonic = value;
      } else {
        keyPair = importWalletFromPrivateKey(value);
      }

      const newWallet: Wallet = {
        address: keyPair.address,
        publicKey: keyPair.publicKey,
        privateKey: keyPair.privateKey,
        mnemonic,
        createdAt: Date.now(),
        balance: 0,
      };

      await WalletStorage.saveWallet(newWallet);
      set({ wallet: newWallet, isLoading: false });

      // Subscribe to wallet updates
      WebSocketService.subscribeToAddress(newWallet.address);

      // Fetch initial balance
      await get().refreshBalance();

      return { success: true };
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : 'Failed to import wallet';
      set({ error: errorMsg, isLoading: false });
      return { success: false, error: errorMsg };
    }
  },

  loadWallet: async () => {
    set({ isLoading: true, error: null });
    try {
      const wallet = await WalletStorage.loadWallet();

      if (wallet) {
        set({ wallet, isLoading: false });

        // Subscribe to wallet updates
        WebSocketService.subscribeToAddress(wallet.address);

        // Fetch balance
        await get().refreshBalance();

        // Load and sync pending transactions
        await get().syncPendingTransactions();
      } else {
        set({ isLoading: false });
      }
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : 'Failed to load wallet';
      set({ error: errorMsg, isLoading: false });
    }
  },

  deleteWallet: async () => {
    const { wallet } = get();
    if (wallet) {
      WebSocketService.unsubscribeFromAddress(wallet.address);
    }

    await WalletStorage.deleteWallet();
    await Storage.remove(STORAGE_KEYS.PENDING_TRANSACTIONS);
    set({ wallet: null, balance: 0, pendingTransactions: [] });
  },

  refreshBalance: async () => {
    const { wallet } = get();
    if (!wallet) return;

    try {
      const balance = await APIService.getBalance(wallet.address);
      set({ balance, wallet: { ...wallet, balance } });
    } catch (error) {
      console.error('Failed to refresh balance:', error);
    }
  },

  addPendingTransaction: async (tx: PendingTransaction) => {
    const { pendingTransactions } = get();
    const updated = [...pendingTransactions, tx];
    set({ pendingTransactions: updated });
    await Storage.set(STORAGE_KEYS.PENDING_TRANSACTIONS, updated);
  },

  removePendingTransaction: async (txid: string) => {
    const { pendingTransactions } = get();
    const updated = pendingTransactions.filter(ptx => ptx.transaction.txid !== txid);
    set({ pendingTransactions: updated });
    await Storage.set(STORAGE_KEYS.PENDING_TRANSACTIONS, updated);
  },

  syncPendingTransactions: async () => {
    // Load pending transactions from storage
    const stored = await Storage.get<PendingTransaction[]>(STORAGE_KEYS.PENDING_TRANSACTIONS);
    if (!stored || stored.length === 0) {
      set({ pendingTransactions: [] });
      return;
    }

    // Check status of each pending transaction
    const stillPending: PendingTransaction[] = [];

    for (const ptx of stored) {
      try {
        const tx = await APIService.getTransaction(ptx.transaction.txid);

        if (!tx || tx.status === 'pending') {
          // Still pending, check if we should retry
          if (ptx.retryCount < 3) {
            stillPending.push(ptx);
          }
        }
        // If confirmed or failed, don't add to stillPending (remove it)
      } catch (error) {
        // Keep in pending list if we can't check status
        stillPending.push(ptx);
      }
    }

    set({ pendingTransactions: stillPending });
    await Storage.set(STORAGE_KEYS.PENDING_TRANSACTIONS, stillPending);
  },

  setError: (error: string | null) => {
    set({ error });
  },
}));
