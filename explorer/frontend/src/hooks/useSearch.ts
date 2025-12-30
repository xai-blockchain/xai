import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { search } from '../api/client';
import type { SearchResult } from '../types';

export function useSearch() {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = useCallback(async (searchQuery: string) => {
    if (!searchQuery.trim()) {
      setResults([]);
      return;
    }

    setIsSearching(true);
    setError(null);

    try {
      // Check if it looks like a block height (numeric)
      if (/^\d+$/.test(searchQuery)) {
        navigate(`/block/${searchQuery}`);
        return;
      }

      // Check if it looks like a transaction hash (64 hex chars)
      if (/^[a-fA-F0-9]{64}$/.test(searchQuery)) {
        navigate(`/tx/${searchQuery}`);
        return;
      }

      // Check if it looks like a block hash (64 hex chars starting with 0s)
      if (/^0{4,}[a-fA-F0-9]{60,}$/.test(searchQuery)) {
        navigate(`/block/${searchQuery}`);
        return;
      }

      // Check if it looks like an address (XAI prefix)
      if (searchQuery.startsWith('XAI') || searchQuery.startsWith('xai')) {
        navigate(`/address/${searchQuery}`);
        return;
      }

      // Otherwise, do a search
      const searchResults = await search(searchQuery);
      setResults(searchResults);

      if (searchResults.length === 1) {
        const result = searchResults[0];
        navigateToResult(result);
      }
    } catch (err) {
      setError('Search failed. Please try again.');
      console.error('Search error:', err);
    } finally {
      setIsSearching(false);
    }
  }, [navigate]);

  const navigateToResult = useCallback((result: SearchResult) => {
    switch (result.type) {
      case 'block':
        navigate(`/block/${result.id}`);
        break;
      case 'transaction':
        navigate(`/tx/${result.id}`);
        break;
      case 'address':
        navigate(`/address/${result.id}`);
        break;
    }
  }, [navigate]);

  return {
    query,
    setQuery,
    results,
    isSearching,
    error,
    handleSearch,
    navigateToResult,
  };
}
