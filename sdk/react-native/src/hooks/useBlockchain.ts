/**
 * useBlockchain Hook
 * React hook for blockchain information and blocks
 */

import { useState, useEffect, useCallback } from 'react';
import { XAIClient } from '../clients/XAIClient';
import { Block, BlockchainInfo } from '../types';

export interface UseBlockchainOptions {
  client: XAIClient;
  autoRefresh?: boolean;
  refreshInterval?: number;
}

export interface UseBlockchainReturn {
  info: BlockchainInfo | null;
  latestBlock: Block | null;
  loading: boolean;
  error: Error | null;
  refresh: () => Promise<void>;
  getBlock: (numberOrHash: number | string) => Promise<Block | null>;
}

export function useBlockchain(
  options: UseBlockchainOptions
): UseBlockchainReturn {
  const { client, autoRefresh = true, refreshInterval = 10000 } = options;

  const [info, setInfo] = useState<BlockchainInfo | null>(null);
  const [latestBlock, setLatestBlock] = useState<Block | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<Error | null>(null);

  /**
   * Fetch blockchain information
   */
  const fetchInfo = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const [blockchainInfo, block] = await Promise.all([
        client.getBlockchainInfo(),
        client.getLatestBlock(),
      ]);

      setInfo(blockchainInfo);
      setLatestBlock(block);
    } catch (err: any) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [client]);

  /**
   * Get a specific block
   */
  const getBlock = useCallback(
    async (numberOrHash: number | string): Promise<Block | null> => {
      try {
        return await client.getBlock(numberOrHash);
      } catch (err: any) {
        console.error('Failed to get block:', err);
        return null;
      }
    },
    [client]
  );

  /**
   * Refresh manually
   */
  const refresh = useCallback(async () => {
    await fetchInfo();
  }, [fetchInfo]);

  /**
   * Fetch on mount
   */
  useEffect(() => {
    fetchInfo();
  }, [fetchInfo]);

  /**
   * Auto-refresh
   */
  useEffect(() => {
    if (!autoRefresh) {
      return;
    }

    const interval = setInterval(() => {
      fetchInfo();
    }, refreshInterval);

    return () => clearInterval(interval);
  }, [autoRefresh, refreshInterval, fetchInfo]);

  return {
    info,
    latestBlock,
    loading,
    error,
    refresh,
    getBlock,
  };
}
