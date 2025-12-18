/**
 * useBalance Hook
 * React hook for fetching and monitoring wallet balance
 */

import { useState, useEffect, useCallback } from 'react';
import { XAIClient } from '../clients/XAIClient';
import { UseBalanceReturn } from '../types';

export interface UseBalanceOptions {
  client: XAIClient;
  address: string | null;
  autoRefresh?: boolean;
  refreshInterval?: number;
}

export function useBalance(options: UseBalanceOptions): UseBalanceReturn {
  const {
    client,
    address,
    autoRefresh = true,
    refreshInterval = 30000,
  } = options;

  const [balance, setBalance] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<Error | null>(null);

  /**
   * Fetch balance
   */
  const fetchBalance = useCallback(async () => {
    if (!address) {
      setBalance(null);
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const balanceData = await client.getBalance(address);
      setBalance(balanceData.balance);
    } catch (err: any) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [client, address]);

  /**
   * Refresh balance manually
   */
  const refresh = useCallback(async () => {
    await fetchBalance();
  }, [fetchBalance]);

  /**
   * Fetch balance when address changes
   */
  useEffect(() => {
    fetchBalance();
  }, [fetchBalance]);

  /**
   * Auto-refresh balance
   */
  useEffect(() => {
    if (!address || !autoRefresh) {
      return;
    }

    const interval = setInterval(() => {
      fetchBalance();
    }, refreshInterval);

    return () => clearInterval(interval);
  }, [address, autoRefresh, refreshInterval, fetchBalance]);

  return {
    balance,
    loading,
    error,
    refresh,
  };
}
