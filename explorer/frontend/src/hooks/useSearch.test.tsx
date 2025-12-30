import { describe, it, expect, vi, beforeAll, afterAll, afterEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { BrowserRouter, MemoryRouter, useLocation } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactNode, useEffect } from 'react';
import { server } from '../__tests__/mocks/server';
import { useSearch } from './useSearch';

// Start server before all tests
beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// Store for navigation
let currentPath = '/';

// Wrapper component that captures navigation
function TestWrapper({ children }: { children: ReactNode }) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
    },
  });

  return (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[currentPath]}>
        <LocationTracker />
        {children}
      </MemoryRouter>
    </QueryClientProvider>
  );
}

function LocationTracker() {
  const location = useLocation();
  useEffect(() => {
    currentPath = location.pathname;
  }, [location.pathname]);
  return null;
}

describe('useSearch', () => {
  beforeEach(() => {
    currentPath = '/';
  });

  it('initializes with empty state', () => {
    const { result } = renderHook(() => useSearch(), { wrapper: TestWrapper });

    expect(result.current.query).toBe('');
    expect(result.current.results).toEqual([]);
    expect(result.current.isSearching).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it('updates query when setQuery is called', () => {
    const { result } = renderHook(() => useSearch(), { wrapper: TestWrapper });

    act(() => {
      result.current.setQuery('test search');
    });

    expect(result.current.query).toBe('test search');
  });

  it('clears results when query is empty', async () => {
    const { result } = renderHook(() => useSearch(), { wrapper: TestWrapper });

    await act(async () => {
      await result.current.handleSearch('');
    });

    expect(result.current.results).toEqual([]);
    expect(result.current.isSearching).toBe(false);
  });

  it('clears results when query is whitespace', async () => {
    const { result } = renderHook(() => useSearch(), { wrapper: TestWrapper });

    await act(async () => {
      await result.current.handleSearch('   ');
    });

    expect(result.current.results).toEqual([]);
  });

  it('navigates to block page for numeric block height', async () => {
    const { result } = renderHook(() => useSearch(), { wrapper: TestWrapper });

    await act(async () => {
      await result.current.handleSearch('12345');
    });

    expect(currentPath).toBe('/block/12345');
  });

  it('navigates to transaction page for 64 hex char hash', async () => {
    const { result } = renderHook(() => useSearch(), { wrapper: TestWrapper });
    const txHash = 'abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890';

    await act(async () => {
      await result.current.handleSearch(txHash);
    });

    expect(currentPath).toBe(`/tx/${txHash}`);
  });

  it('navigates to transaction page for 64 hex chars (tx check comes before block)', async () => {
    const { result } = renderHook(() => useSearch(), { wrapper: TestWrapper });
    // In the useSearch hook, the tx check (/^[a-fA-F0-9]{64}$/) comes BEFORE the block hash check
    // So any 64 hex char string will navigate to /tx/ first
    // This is expected behavior based on the current implementation
    const hash = '00000000000000000000000000000000000000000000000000000000deadbeef';

    await act(async () => {
      await result.current.handleSearch(hash);
    });

    // Due to order of checks in useSearch, 64 hex chars always match tx pattern first
    expect(currentPath).toBe(`/tx/${hash}`);
  });

  it('navigates to address page for XAI prefix', async () => {
    const { result } = renderHook(() => useSearch(), { wrapper: TestWrapper });

    await act(async () => {
      await result.current.handleSearch('XAIaddress123456');
    });

    expect(currentPath).toBe('/address/XAIaddress123456');
  });

  it('navigates to address page for lowercase xai prefix', async () => {
    const { result } = renderHook(() => useSearch(), { wrapper: TestWrapper });

    await act(async () => {
      await result.current.handleSearch('xaiaddress123456');
    });

    expect(currentPath).toBe('/address/xaiaddress123456');
  });

  it('fetches search results for general queries', async () => {
    const { result } = renderHook(() => useSearch(), { wrapper: TestWrapper });

    await act(async () => {
      await result.current.handleSearch('general search query');
    });

    await waitFor(() => {
      expect(result.current.isSearching).toBe(false);
    });

    expect(result.current.results.length).toBeGreaterThan(0);
  });

  it('navigateToResult navigates to block', () => {
    const { result } = renderHook(() => useSearch(), { wrapper: TestWrapper });

    act(() => {
      result.current.navigateToResult({
        type: 'block',
        id: '12345',
        preview: 'Block #12345',
      });
    });

    expect(currentPath).toBe('/block/12345');
  });

  it('navigateToResult navigates to transaction', () => {
    const { result } = renderHook(() => useSearch(), { wrapper: TestWrapper });

    act(() => {
      result.current.navigateToResult({
        type: 'transaction',
        id: 'txhash123',
        preview: 'Transaction',
      });
    });

    expect(currentPath).toBe('/tx/txhash123');
  });

  it('navigateToResult navigates to address', () => {
    const { result } = renderHook(() => useSearch(), { wrapper: TestWrapper });

    act(() => {
      result.current.navigateToResult({
        type: 'address',
        id: 'XAIaddr123',
        preview: 'Address',
      });
    });

    expect(currentPath).toBe('/address/XAIaddr123');
  });
});
