/**
 * useWallet Hook
 * React hook for wallet management with biometric authentication
 */

import { useState, useEffect, useCallback } from 'react';
import { getXAIWallet } from '../clients/XAIWallet';
import { XAIClient } from '../clients/XAIClient';
import { Wallet, UseWalletReturn, BiometricConfig } from '../types';

export interface UseWalletOptions {
  client: XAIClient;
  autoRefreshBalance?: boolean;
  refreshInterval?: number;
}

export function useWallet(options: UseWalletOptions): UseWalletReturn {
  const { client, autoRefreshBalance = true, refreshInterval = 30000 } = options;

  const [wallet, setWallet] = useState<Wallet | null>(null);
  const [balance, setBalance] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<Error | null>(null);

  const walletClient = getXAIWallet();

  /**
   * Load existing wallet
   */
  const loadWallet = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      await walletClient.initialize();

      const currentWallet = walletClient.getCurrentWallet();
      setWallet(currentWallet);

      if (currentWallet && autoRefreshBalance) {
        await fetchBalance(currentWallet.address);
      }
    } catch (err: any) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [autoRefreshBalance]);

  /**
   * Fetch wallet balance
   */
  const fetchBalance = useCallback(async (address: string) => {
    try {
      const balanceData = await client.getBalance(address);
      setBalance(balanceData.balance);
    } catch (err: any) {
      console.error('Failed to fetch balance:', err);
      // Don't set error state for balance failures
    }
  }, [client]);

  /**
   * Create a new wallet
   */
  const createWallet = useCallback(
    async (biometricEnabled: boolean = false): Promise<Wallet> => {
      try {
        setLoading(true);
        setError(null);

        const newWallet = await walletClient.createWallet(biometricEnabled);
        setWallet({
          address: newWallet.address,
          publicKey: newWallet.publicKey,
        });

        if (autoRefreshBalance) {
          await fetchBalance(newWallet.address);
        }

        return newWallet;
      } catch (err: any) {
        setError(err);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [autoRefreshBalance, fetchBalance]
  );

  /**
   * Import wallet from mnemonic
   */
  const importWallet = useCallback(
    async (
      mnemonic: string,
      biometricEnabled: boolean = false
    ): Promise<Wallet> => {
      try {
        setLoading(true);
        setError(null);

        const importedWallet = await walletClient.importWallet(
          mnemonic,
          biometricEnabled
        );
        setWallet({
          address: importedWallet.address,
          publicKey: importedWallet.publicKey,
        });

        if (autoRefreshBalance) {
          await fetchBalance(importedWallet.address);
        }

        return importedWallet;
      } catch (err: any) {
        setError(err);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [autoRefreshBalance, fetchBalance]
  );

  /**
   * Delete wallet
   */
  const deleteWallet = useCallback(async (config?: BiometricConfig) => {
    try {
      setLoading(true);
      setError(null);

      await walletClient.deleteWallet(config);
      setWallet(null);
      setBalance(null);
    } catch (err: any) {
      setError(err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Refresh balance
   */
  const refreshBalance = useCallback(async () => {
    if (!wallet) {
      return;
    }

    try {
      await fetchBalance(wallet.address);
    } catch (err: any) {
      console.error('Failed to refresh balance:', err);
    }
  }, [wallet, fetchBalance]);

  /**
   * Load wallet on mount
   */
  useEffect(() => {
    loadWallet();
  }, [loadWallet]);

  /**
   * Auto-refresh balance
   */
  useEffect(() => {
    if (!wallet || !autoRefreshBalance) {
      return;
    }

    const interval = setInterval(() => {
      fetchBalance(wallet.address);
    }, refreshInterval);

    return () => clearInterval(interval);
  }, [wallet, autoRefreshBalance, refreshInterval, fetchBalance]);

  return {
    wallet,
    balance,
    loading,
    error,
    createWallet,
    importWallet,
    deleteWallet,
    refreshBalance,
  };
}
