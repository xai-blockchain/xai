/**
 * useTransactions Hook
 * React hook for managing transactions
 */

import { useState, useEffect, useCallback } from 'react';
import { XAIClient } from '../clients/XAIClient';
import { XAIWallet, getXAIWallet } from '../clients/XAIWallet';
import {
  Transaction,
  SendTransactionParams,
  UseTransactionsReturn,
  BiometricConfig,
} from '../types';

export interface UseTransactionsOptions {
  client: XAIClient;
  address: string | null;
  autoRefresh?: boolean;
  refreshInterval?: number;
  biometricConfig?: BiometricConfig;
}

export function useTransactions(
  options: UseTransactionsOptions
): UseTransactionsReturn {
  const {
    client,
    address,
    autoRefresh = true,
    refreshInterval = 15000,
    biometricConfig,
  } = options;

  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<Error | null>(null);

  const walletClient = getXAIWallet();

  /**
   * Fetch transactions for address
   */
  const fetchTransactions = useCallback(async () => {
    if (!address) {
      setTransactions([]);
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const response = await client.getTransactionsByAddress(address, {
        limit: 50,
      });
      setTransactions(response.items);
    } catch (err: any) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [client, address]);

  /**
   * Send a transaction
   */
  const sendTransaction = useCallback(
    async (params: SendTransactionParams): Promise<Transaction> => {
      try {
        setLoading(true);
        setError(null);

        // Get nonce if not provided
        if (params.nonce === undefined) {
          const { count } = await client.getTransactionCount(params.from);
          params.nonce = count;
        }

        // Estimate fee
        const { fee } = await client.estimateFee(params);

        // Create transaction object for signing
        const txData = JSON.stringify({
          from: params.from,
          to: params.to,
          value: params.value,
          fee,
          nonce: params.nonce,
          data: params.data || '',
          timestamp: Date.now(),
        });

        // Sign transaction with wallet
        const signature = await walletClient.signMessage(
          txData,
          biometricConfig
        );

        // Send signed transaction
        const transaction = await client.sendTransaction({
          ...params,
          // Attach signature in data field for demo
          // In production, use proper transaction serialization
          data: JSON.stringify({ ...params, signature }),
        });

        // Refresh transactions list
        await fetchTransactions();

        return transaction;
      } catch (err: any) {
        setError(err);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [client, walletClient, biometricConfig, fetchTransactions]
  );

  /**
   * Get a specific transaction by hash
   */
  const getTransaction = useCallback(
    async (hash: string): Promise<Transaction | null> => {
      try {
        return await client.getTransaction(hash);
      } catch (err: any) {
        console.error('Failed to get transaction:', err);
        return null;
      }
    },
    [client]
  );

  /**
   * Refresh transactions manually
   */
  const refresh = useCallback(async () => {
    await fetchTransactions();
  }, [fetchTransactions]);

  /**
   * Fetch transactions when address changes
   */
  useEffect(() => {
    fetchTransactions();
  }, [fetchTransactions]);

  /**
   * Auto-refresh transactions
   */
  useEffect(() => {
    if (!address || !autoRefresh) {
      return;
    }

    const interval = setInterval(() => {
      fetchTransactions();
    }, refreshInterval);

    return () => clearInterval(interval);
  }, [address, autoRefresh, refreshInterval, fetchTransactions]);

  return {
    transactions,
    loading,
    error,
    sendTransaction,
    getTransaction,
    refresh,
  };
}
