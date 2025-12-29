/**
 * Explorer Screen - Enhanced Block Explorer
 *
 * Production-ready features:
 * - Block and transaction browsing with pagination
 * - Enhanced search (block #, hash, txid, address)
 * - Full address lookup with transaction history
 * - Recent searches history
 * - Search suggestions
 * - Network stats dashboard
 * - Mempool monitoring
 * - Copy/share functionality
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  RefreshControl,
  TouchableOpacity,
  Modal,
  ScrollView,
  Alert,
  Keyboard,
} from 'react-native';
import * as Clipboard from 'expo-clipboard';
import {
  Card,
  BlockItem,
  TransactionItem,
  StatusBadge,
  Input,
  Button,
  Icon,
} from '../components';
import { xaiApi } from '../services/api';
import { useTheme } from '../theme';
import { spacing, borderRadius } from '../theme/spacing';
import { triggerHaptic } from '../hooks/useHaptics';
import { Block, Transaction, BlockchainStats, MempoolStats } from '../types';
import {
  formatHash,
  formatDateTime,
  formatDifficulty,
  formatCompactNumber,
  formatUptime,
  formatXaiWithSymbol,
  formatAddress,
  formatRelativeTime,
} from '../utils/format';
import {
  cacheBlocks,
  getCachedBlocks,
  cacheStats,
  getCachedStats,
  cacheMempoolStats,
  getCachedMempoolStats,
  isOnline,
} from '../utils/offline';
import * as SecureStore from 'expo-secure-store';

// ============== Types ==============

type ExplorerTab = 'blocks' | 'transactions' | 'mempool' | 'search';

interface SearchResult {
  type: 'block' | 'transaction' | 'address' | 'not_found' | 'error';
  data?: any;
  query?: string;
  message?: string;
}

interface AddressInfo {
  address: string;
  balance: number;
  totalReceived?: number;
  totalSent?: number;
  transactionCount: number;
  transactions: Transaction[];
  firstSeen?: number;
  lastSeen?: number;
}

interface RecentSearch {
  query: string;
  type: 'block' | 'transaction' | 'address';
  timestamp: number;
  label?: string;
}

// ============== Constants ==============

const LIMIT = 20;
const MAX_RECENT_SEARCHES = 10;
const RECENT_SEARCHES_KEY = 'xai_recent_searches';

// Search suggestions based on common queries
const SEARCH_SUGGESTIONS = [
  { label: 'Genesis Block', query: '0' },
  { label: 'Latest Block', query: 'latest' },
  { label: 'Mempool', query: 'mempool' },
];

// ============== Component ==============

export function ExplorerScreen() {
  const theme = useTheme();

  // Tab state
  const [activeTab, setActiveTab] = useState<ExplorerTab>('blocks');

  // Data state
  const [blocks, setBlocks] = useState<Block[]>([]);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [mempoolTxs, setMempoolTxs] = useState<Transaction[]>([]);
  const [stats, setStats] = useState<BlockchainStats | null>(null);
  const [mempoolStats, setMempoolStats] = useState<MempoolStats | null>(null);

  // UI state
  const [selectedBlock, setSelectedBlock] = useState<Block | null>(null);
  const [addressInfo, setAddressInfo] = useState<AddressInfo | null>(null);
  const [showAddressModal, setShowAddressModal] = useState(false);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [page, setPage] = useState(0);
  const [hasMore, setHasMore] = useState(true);

  // Search state
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResult, setSearchResult] = useState<SearchResult | null>(null);
  const [searching, setSearching] = useState(false);
  const [recentSearches, setRecentSearches] = useState<RecentSearch[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);

  // Offline state
  const [isOffline, setIsOffline] = useState(false);

  // ============== Data Fetching ==============

  const fetchBlocks = useCallback(
    async (reset: boolean = false) => {
      const offset = reset ? 0 : page * LIMIT;
      if (!reset) setLoading(true);

      try {
        const online = isOnline();
        setIsOffline(!online);

        if (!online) {
          const cached = await getCachedBlocks();
          if (cached) {
            setBlocks(cached.blocks);
            setHasMore(false);
          }
          return;
        }

        const result = await xaiApi.getBlocks(LIMIT, offset);
        if (result.success && result.data) {
          const newBlocks = result.data.blocks;
          if (reset) {
            setBlocks(newBlocks);
            setPage(1);
            // Cache blocks
            await cacheBlocks(newBlocks, result.data.total);
          } else {
            setBlocks((prev) => [...prev, ...newBlocks]);
            setPage((prev) => prev + 1);
          }
          setHasMore(newBlocks.length === LIMIT);
        }
      } catch (error) {
        console.error('Failed to fetch blocks:', error);
        // Try cache on error
        const cached = await getCachedBlocks();
        if (cached) {
          setBlocks(cached.blocks);
          setIsOffline(true);
        }
      } finally {
        setLoading(false);
      }
    },
    [page]
  );

  const fetchTransactions = useCallback(
    async (reset: boolean = false) => {
      const offset = reset ? 0 : page * LIMIT;
      if (!reset) setLoading(true);

      try {
        const result = await xaiApi.getRecentTransactions(LIMIT, offset);
        if (result.success && result.data) {
          if (reset) {
            setTransactions(result.data.transactions);
            setPage(1);
          } else {
            setTransactions((prev) => [...prev, ...result.data!.transactions]);
            setPage((prev) => prev + 1);
          }
          setHasMore(result.data.transactions.length === LIMIT);
        }
      } catch (error) {
        console.error('Failed to fetch transactions:', error);
      } finally {
        setLoading(false);
      }
    },
    [page]
  );

  const fetchMempoolTransactions = useCallback(
    async (reset: boolean = false) => {
      const offset = reset ? 0 : page * LIMIT;
      if (!reset) setLoading(true);

      try {
        const online = isOnline();
        if (!online) {
          const cached = await getCachedMempoolStats();
          if (cached) {
            setMempoolStats(cached);
          }
          return;
        }

        const [txResult, statsResult] = await Promise.all([
          xaiApi.getPendingTransactions(LIMIT, offset),
          xaiApi.getMempoolStats(),
        ]);

        if (txResult.success && txResult.data) {
          if (reset) {
            setMempoolTxs(txResult.data.transactions);
            setPage(1);
          } else {
            setMempoolTxs((prev) => [...prev, ...txResult.data!.transactions]);
            setPage((prev) => prev + 1);
          }
          setHasMore(txResult.data.transactions.length === LIMIT);
        }

        if (statsResult.success && statsResult.data) {
          setMempoolStats(statsResult.data);
          await cacheMempoolStats(statsResult.data);
        }
      } catch (error) {
        console.error('Failed to fetch mempool:', error);
      } finally {
        setLoading(false);
      }
    },
    [page]
  );

  const fetchStats = useCallback(async () => {
    try {
      const online = isOnline();
      if (!online) {
        const cached = await getCachedStats();
        if (cached) {
          setStats(cached);
        }
        return;
      }

      const result = await xaiApi.getStats();
      if (result.success && result.data) {
        setStats(result.data);
        await cacheStats(result.data);
      }
    } catch (error) {
      console.error('Failed to fetch stats:', error);
      const cached = await getCachedStats();
      if (cached) {
        setStats(cached);
      }
    }
  }, []);

  // ============== Search ==============

  const loadRecentSearches = useCallback(async () => {
    try {
      const raw = await SecureStore.getItemAsync(RECENT_SEARCHES_KEY);
      if (raw) {
        setRecentSearches(JSON.parse(raw));
      }
    } catch {
      // Ignore
    }
  }, []);

  const saveRecentSearch = useCallback(
    async (search: RecentSearch) => {
      try {
        const updated = [search, ...recentSearches.filter((s) => s.query !== search.query)].slice(
          0,
          MAX_RECENT_SEARCHES
        );
        setRecentSearches(updated);
        await SecureStore.setItemAsync(RECENT_SEARCHES_KEY, JSON.stringify(updated));
      } catch {
        // Ignore
      }
    },
    [recentSearches]
  );

  const clearRecentSearches = useCallback(async () => {
    setRecentSearches([]);
    await SecureStore.deleteItemAsync(RECENT_SEARCHES_KEY);
    triggerHaptic('success');
  }, []);

  const handleSearch = useCallback(
    async (query?: string) => {
      const searchText = (query || searchQuery).trim();
      if (!searchText) return;

      Keyboard.dismiss();
      setSearching(true);
      setSearchResult(null);
      setShowSuggestions(false);

      try {
        // Handle special queries
        if (searchText.toLowerCase() === 'latest') {
          const result = await xaiApi.getBlocks(1, 0);
          if (result.success && result.data?.blocks[0]) {
            setSearchResult({ type: 'block', data: result.data.blocks[0] });
            await saveRecentSearch({
              query: searchText,
              type: 'block',
              timestamp: Date.now(),
              label: `Block #${result.data.blocks[0].index}`,
            });
          }
          return;
        }

        if (searchText.toLowerCase() === 'mempool') {
          setActiveTab('mempool');
          return;
        }

        // Try block by number first
        const blockNum = parseInt(searchText, 10);
        if (!isNaN(blockNum) && blockNum >= 0) {
          const blockResult = await xaiApi.getBlock(blockNum);
          if (blockResult.success && blockResult.data) {
            setSearchResult({ type: 'block', data: blockResult.data });
            await saveRecentSearch({
              query: searchText,
              type: 'block',
              timestamp: Date.now(),
              label: `Block #${blockNum}`,
            });
            return;
          }
        }

        // Try block by hash or transaction
        if (searchText.length === 64 || searchText.startsWith('0x')) {
          const hash = searchText.startsWith('0x') ? searchText.slice(2) : searchText;

          // Try block by hash
          const blockResult = await xaiApi.getBlockByHash(hash);
          if (blockResult.success && blockResult.data) {
            setSearchResult({ type: 'block', data: blockResult.data });
            await saveRecentSearch({
              query: searchText,
              type: 'block',
              timestamp: Date.now(),
              label: `Block #${blockResult.data.index}`,
            });
            return;
          }

          // Try transaction
          const txResult = await xaiApi.getTransaction(hash);
          if (txResult.success && txResult.data?.found) {
            setSearchResult({ type: 'transaction', data: txResult.data });
            await saveRecentSearch({
              query: searchText,
              type: 'transaction',
              timestamp: Date.now(),
              label: `Tx ${formatHash(hash, 8)}`,
            });
            return;
          }
        }

        // Try address (XAI prefix)
        if (searchText.startsWith('XAI') || searchText.length === 40) {
          const balanceResult = await xaiApi.getBalance(searchText);
          if (balanceResult.success && balanceResult.data) {
            const historyResult = await xaiApi.getHistory(searchText, 50, 0);
            const txs = historyResult.data?.transactions || [];

            const addressData: AddressInfo = {
              address: searchText,
              balance: balanceResult.data.balance,
              transactionCount: historyResult.data?.total || txs.length,
              transactions: txs,
              firstSeen: txs.length > 0 ? txs[txs.length - 1].timestamp : undefined,
              lastSeen: txs.length > 0 ? txs[0].timestamp : undefined,
            };

            setSearchResult({ type: 'address', data: addressData });
            await saveRecentSearch({
              query: searchText,
              type: 'address',
              timestamp: Date.now(),
              label: formatAddress(searchText, 8),
            });
            return;
          }
        }

        // Not found
        setSearchResult({ type: 'not_found', query: searchText });
      } catch (error) {
        console.error('Search error:', error);
        setSearchResult({ type: 'error', message: 'Search failed. Please try again.' });
      } finally {
        setSearching(false);
      }
    },
    [searchQuery, saveRecentSearch]
  );

  // ============== Effects ==============

  useEffect(() => {
    fetchStats();
    fetchBlocks(true);
    loadRecentSearches();
  }, []);

  useEffect(() => {
    setPage(0);
    setHasMore(true);

    if (activeTab === 'blocks') {
      fetchBlocks(true);
    } else if (activeTab === 'transactions') {
      fetchTransactions(true);
    } else if (activeTab === 'mempool') {
      fetchMempoolTransactions(true);
    }
  }, [activeTab]);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await fetchStats();

    if (activeTab === 'blocks') {
      await fetchBlocks(true);
    } else if (activeTab === 'transactions') {
      await fetchTransactions(true);
    } else if (activeTab === 'mempool') {
      await fetchMempoolTransactions(true);
    }

    setRefreshing(false);
  }, [activeTab, fetchBlocks, fetchTransactions, fetchMempoolTransactions, fetchStats]);

  // ============== Handlers ==============

  const handleCopy = async (value: string, label: string) => {
    try {
      await Clipboard.setStringAsync(value);
      triggerHaptic('success');
      Alert.alert('Copied', `${label} copied to clipboard`);
    } catch {
      Alert.alert('Error', 'Failed to copy');
    }
  };

  const handleViewAddress = (address: string) => {
    setSearchQuery(address);
    handleSearch(address);
    setActiveTab('search');
  };

  // ============== Render Helpers ==============

  const renderTab = (tab: ExplorerTab, label: string, icon: string) => (
    <TouchableOpacity
      key={tab}
      style={[
        styles.tab,
        { backgroundColor: theme.colors.surfaceOverlay },
        activeTab === tab && { backgroundColor: theme.colors.brand.primary },
      ]}
      onPress={() => {
        setActiveTab(tab);
        triggerHaptic('selection');
      }}
    >
      <Icon
        name={icon as any}
        size={16}
        color={activeTab === tab ? '#ffffff' : theme.colors.textMuted}
      />
      <Text
        style={[
          styles.tabText,
          { color: theme.colors.textMuted },
          activeTab === tab && styles.activeTabText,
        ]}
      >
        {label}
      </Text>
    </TouchableOpacity>
  );

  const renderStatsCard = () => {
    if (!stats) return null;

    return (
      <Card style={styles.statsCard}>
        <View style={styles.statsGrid}>
          <View style={styles.statItem}>
            <Text style={[styles.statValue, { color: theme.colors.text }]}>
              {formatCompactNumber(stats.chainHeight)}
            </Text>
            <Text style={[styles.statLabel, { color: theme.colors.textMuted }]}>Height</Text>
          </View>
          <View style={styles.statItem}>
            <Text style={[styles.statValue, { color: theme.colors.text }]}>
              {formatDifficulty(stats.difficulty)}
            </Text>
            <Text style={[styles.statLabel, { color: theme.colors.textMuted }]}>Difficulty</Text>
          </View>
          <View style={styles.statItem}>
            <Text style={[styles.statValue, { color: theme.colors.text }]}>{stats.peers}</Text>
            <Text style={[styles.statLabel, { color: theme.colors.textMuted }]}>Peers</Text>
          </View>
          <View style={styles.statItem}>
            <Text style={[styles.statValue, { color: theme.colors.text }]}>
              {formatUptime(stats.nodeUptime)}
            </Text>
            <Text style={[styles.statLabel, { color: theme.colors.textMuted }]}>Uptime</Text>
          </View>
        </View>
        {isOffline && (
          <View style={[styles.offlineBanner, { backgroundColor: theme.colors.semantic.warningMuted }]}>
            <Icon name="wifi-off" size={14} color={theme.colors.semantic.warning} />
            <Text style={[styles.offlineText, { color: theme.colors.semantic.warning }]}>
              Offline - Showing cached data
            </Text>
          </View>
        )}
      </Card>
    );
  };

  const renderMempoolStats = () => {
    if (!mempoolStats) return null;

    return (
      <Card style={styles.mempoolStatsCard}>
        <View style={styles.mempoolStatsRow}>
          <View style={styles.mempoolStatItem}>
            <Icon name="layers" size={20} color={theme.colors.brand.primary} />
            <Text style={[styles.mempoolStatValue, { color: theme.colors.text }]}>
              {mempoolStats.count}
            </Text>
            <Text style={[styles.mempoolStatLabel, { color: theme.colors.textMuted }]}>
              Pending Txs
            </Text>
          </View>
          <View style={styles.mempoolStatItem}>
            <Icon name="dollar-sign" size={20} color={theme.colors.semantic.success} />
            <Text style={[styles.mempoolStatValue, { color: theme.colors.text }]}>
              {formatXaiWithSymbol(mempoolStats.totalFees || 0)}
            </Text>
            <Text style={[styles.mempoolStatLabel, { color: theme.colors.textMuted }]}>
              Total Fees
            </Text>
          </View>
          <View style={styles.mempoolStatItem}>
            <Icon name="database" size={20} color={theme.colors.semantic.warning} />
            <Text style={[styles.mempoolStatValue, { color: theme.colors.text }]}>
              {formatCompactNumber(mempoolStats.size || 0)}
            </Text>
            <Text style={[styles.mempoolStatLabel, { color: theme.colors.textMuted }]}>Size</Text>
          </View>
        </View>
      </Card>
    );
  };

  const renderSearchContent = () => (
    <ScrollView
      style={styles.searchContainer}
      contentContainerStyle={styles.searchContent}
      keyboardShouldPersistTaps="handled"
    >
      {/* Search Input */}
      <View style={styles.searchInputRow}>
        <View style={{ flex: 1 }}>
          <Input
            placeholder="Block #, hash, txid, or address"
            value={searchQuery}
            onChangeText={(text) => {
              setSearchQuery(text);
              setShowSuggestions(text.length === 0);
            }}
            onFocus={() => setShowSuggestions(searchQuery.length === 0)}
            autoCapitalize="none"
            autoCorrect={false}
            returnKeyType="search"
            onSubmitEditing={() => handleSearch()}
            leftIcon={<Icon name="search" size={18} color={theme.colors.textMuted} />}
            rightIcon={
              searchQuery.length > 0 ? (
                <TouchableOpacity
                  onPress={() => {
                    setSearchQuery('');
                    setSearchResult(null);
                    setShowSuggestions(true);
                  }}
                >
                  <Icon name="x-circle" size={18} color={theme.colors.textMuted} />
                </TouchableOpacity>
              ) : undefined
            }
          />
        </View>
        <Button
          title="Search"
          onPress={() => handleSearch()}
          loading={searching}
          style={styles.searchButton}
        />
      </View>

      {/* Search Suggestions */}
      {showSuggestions && !searchResult && (
        <Card title="Quick Search" style={styles.suggestionsCard}>
          {SEARCH_SUGGESTIONS.map((suggestion) => (
            <TouchableOpacity
              key={suggestion.query}
              style={[styles.suggestionItem, { borderBottomColor: theme.colors.border }]}
              onPress={() => {
                setSearchQuery(suggestion.query);
                handleSearch(suggestion.query);
              }}
            >
              <Icon name="search" size={16} color={theme.colors.textMuted} />
              <Text style={[styles.suggestionText, { color: theme.colors.text }]}>
                {suggestion.label}
              </Text>
              <Icon name="chevron-right" size={16} color={theme.colors.textMuted} />
            </TouchableOpacity>
          ))}
        </Card>
      )}

      {/* Recent Searches */}
      {showSuggestions && !searchResult && recentSearches.length > 0 && (
        <Card
          title="Recent Searches"
          style={styles.recentSearchesCard}
          rightContent={
            <TouchableOpacity onPress={clearRecentSearches}>
              <Text style={[styles.clearText, { color: theme.colors.brand.primary }]}>Clear</Text>
            </TouchableOpacity>
          }
        >
          {recentSearches.map((search, index) => (
            <TouchableOpacity
              key={`${search.query}-${index}`}
              style={[styles.recentItem, { borderBottomColor: theme.colors.border }]}
              onPress={() => {
                setSearchQuery(search.query);
                handleSearch(search.query);
              }}
            >
              <Icon
                name={
                  search.type === 'block'
                    ? 'box'
                    : search.type === 'transaction'
                      ? 'arrow-right'
                      : 'user'
                }
                size={16}
                color={theme.colors.textMuted}
              />
              <View style={styles.recentItemContent}>
                <Text style={[styles.recentLabel, { color: theme.colors.text }]}>
                  {search.label || formatHash(search.query, 12)}
                </Text>
                <Text style={[styles.recentTime, { color: theme.colors.textMuted }]}>
                  {formatRelativeTime(search.timestamp)}
                </Text>
              </View>
              <Icon name="chevron-right" size={16} color={theme.colors.textMuted} />
            </TouchableOpacity>
          ))}
        </Card>
      )}

      {/* Search Results */}
      {renderSearchResult()}
    </ScrollView>
  );

  const renderSearchResult = () => {
    if (!searchResult) return null;

    if (searchResult.type === 'not_found') {
      return (
        <Card style={styles.resultCard}>
          <View style={styles.notFoundContainer}>
            <Icon name="search" size={48} color={theme.colors.textMuted} />
            <Text style={[styles.notFoundTitle, { color: theme.colors.text }]}>No Results</Text>
            <Text style={[styles.notFoundText, { color: theme.colors.textMuted }]}>
              No results found for "{searchResult.query}"
            </Text>
            <Text style={[styles.notFoundHint, { color: theme.colors.textMuted }]}>
              Try searching for a block number, transaction ID, or XAI address
            </Text>
          </View>
        </Card>
      );
    }

    if (searchResult.type === 'error') {
      return (
        <Card style={styles.resultCard}>
          <View style={styles.errorContainer}>
            <Icon name="alert-circle" size={48} color={theme.colors.semantic.error} />
            <Text style={[styles.errorText, { color: theme.colors.semantic.error }]}>
              {searchResult.message}
            </Text>
          </View>
        </Card>
      );
    }

    if (searchResult.type === 'block') {
      return (
        <Card title="Block Found" style={styles.resultCard}>
          <BlockItem block={searchResult.data} onPress={() => setSelectedBlock(searchResult.data)} />
        </Card>
      );
    }

    if (searchResult.type === 'transaction') {
      const tx = searchResult.data.transaction;
      return (
        <Card title="Transaction Found" style={styles.resultCard}>
          <View style={styles.txResultContent}>
            <DetailRow
              label="Transaction ID"
              value={formatHash(tx.txid, 10)}
              fullValue={tx.txid}
              copyable
              theme={theme}
              onCopy={handleCopy}
            />
            <DetailRow
              label="Status"
              value={
                <StatusBadge
                  status={searchResult.data.status === 'pending' ? 'warning' : 'success'}
                  label={searchResult.data.status || 'confirmed'}
                  size="small"
                />
              }
              theme={theme}
            />
            {searchResult.data.confirmations !== undefined && (
              <DetailRow
                label="Confirmations"
                value={searchResult.data.confirmations.toString()}
                theme={theme}
              />
            )}
            <DetailRow
              label="Amount"
              value={formatXaiWithSymbol(tx.amount)}
              theme={theme}
            />
            <DetailRow
              label="Fee"
              value={formatXaiWithSymbol(tx.fee)}
              theme={theme}
            />
            <DetailRow
              label="From"
              value={formatAddress(tx.sender, 10)}
              fullValue={tx.sender}
              copyable
              onPress={() => handleViewAddress(tx.sender)}
              theme={theme}
              onCopy={handleCopy}
            />
            <DetailRow
              label="To"
              value={formatAddress(tx.recipient, 10)}
              fullValue={tx.recipient}
              copyable
              onPress={() => handleViewAddress(tx.recipient)}
              theme={theme}
              onCopy={handleCopy}
              isLast
            />
          </View>
        </Card>
      );
    }

    if (searchResult.type === 'address') {
      const addr: AddressInfo = searchResult.data;
      return (
        <Card title="Address Found" style={styles.resultCard}>
          <View style={styles.addressResultContent}>
            <DetailRow
              label="Address"
              value={formatAddress(addr.address, 10)}
              fullValue={addr.address}
              copyable
              theme={theme}
              onCopy={handleCopy}
            />
            <DetailRow
              label="Balance"
              value={formatXaiWithSymbol(addr.balance)}
              valueStyle={{ color: theme.colors.semantic.success, fontWeight: '700' }}
              theme={theme}
            />
            <DetailRow
              label="Transactions"
              value={addr.transactionCount.toString()}
              theme={theme}
            />
            {addr.firstSeen && (
              <DetailRow
                label="First Seen"
                value={formatRelativeTime(addr.firstSeen)}
                theme={theme}
              />
            )}
            {addr.lastSeen && (
              <DetailRow
                label="Last Seen"
                value={formatRelativeTime(addr.lastSeen)}
                theme={theme}
                isLast={addr.transactions.length === 0}
              />
            )}
          </View>

          {/* Transaction History */}
          {addr.transactions.length > 0 && (
            <View style={styles.addressTxSection}>
              <Text style={[styles.addressTxTitle, { color: theme.colors.text }]}>
                Recent Transactions ({addr.transactionCount})
              </Text>
              {addr.transactions.slice(0, 10).map((tx) => (
                <TransactionItem
                  key={tx.txid}
                  transaction={tx}
                  currentAddress={addr.address}
                  onPress={() => {
                    setSearchQuery(tx.txid);
                    handleSearch(tx.txid);
                  }}
                />
              ))}
              {addr.transactionCount > 10 && (
                <Button
                  title={`View All ${addr.transactionCount} Transactions`}
                  variant="ghost"
                  onPress={() => {
                    setAddressInfo(addr);
                    setShowAddressModal(true);
                  }}
                  style={styles.viewAllButton}
                />
              )}
            </View>
          )}
        </Card>
      );
    }

    return null;
  };

  const renderBlockModal = () => (
    <Modal
      visible={!!selectedBlock}
      animationType="slide"
      transparent
      onRequestClose={() => setSelectedBlock(null)}
    >
      <View style={[styles.modalOverlay, { backgroundColor: 'rgba(0, 0, 0, 0.8)' }]}>
        <View style={[styles.modalContent, { backgroundColor: theme.colors.surface }]}>
          <View style={[styles.modalHeader, { borderBottomColor: theme.colors.border }]}>
            <Text style={[styles.modalTitle, { color: theme.colors.text }]}>
              Block #{selectedBlock?.index}
            </Text>
            <Button
              title="Close"
              variant="ghost"
              size="small"
              onPress={() => setSelectedBlock(null)}
            />
          </View>
          <ScrollView style={styles.modalScroll}>
            {selectedBlock && (
              <>
                <DetailRow
                  label="Hash"
                  value={formatHash(selectedBlock.hash, 12)}
                  fullValue={selectedBlock.hash}
                  copyable
                  theme={theme}
                  onCopy={handleCopy}
                />
                <DetailRow
                  label="Previous Hash"
                  value={formatHash(selectedBlock.previousHash, 12)}
                  fullValue={selectedBlock.previousHash}
                  copyable
                  theme={theme}
                  onCopy={handleCopy}
                />
                <DetailRow
                  label="Timestamp"
                  value={formatDateTime(selectedBlock.timestamp)}
                  theme={theme}
                />
                <DetailRow
                  label="Difficulty"
                  value={selectedBlock.difficulty.toString()}
                  theme={theme}
                />
                <DetailRow
                  label="Nonce"
                  value={selectedBlock.nonce.toString()}
                  theme={theme}
                />
                <DetailRow
                  label="Merkle Root"
                  value={formatHash(selectedBlock.merkleRoot, 12)}
                  fullValue={selectedBlock.merkleRoot}
                  copyable
                  theme={theme}
                  onCopy={handleCopy}
                />
                {selectedBlock.miner && (
                  <DetailRow
                    label="Miner"
                    value={formatAddress(selectedBlock.miner, 10)}
                    fullValue={selectedBlock.miner}
                    copyable
                    onPress={() => {
                      setSelectedBlock(null);
                      handleViewAddress(selectedBlock.miner!);
                    }}
                    theme={theme}
                    onCopy={handleCopy}
                    isLast={selectedBlock.transactions.length === 0}
                  />
                )}
                {selectedBlock.transactions.length > 0 && (
                  <>
                    <Text style={[styles.txHeader, { color: theme.colors.text }]}>
                      Transactions ({selectedBlock.transactions.length})
                    </Text>
                    {selectedBlock.transactions.map((tx) => (
                      <TransactionItem
                        key={tx.txid}
                        transaction={tx}
                        currentAddress=""
                        onPress={() => {
                          setSelectedBlock(null);
                          setSearchQuery(tx.txid);
                          handleSearch(tx.txid);
                          setActiveTab('search');
                        }}
                      />
                    ))}
                  </>
                )}
              </>
            )}
          </ScrollView>
        </View>
      </View>
    </Modal>
  );

  const renderAddressModal = () => (
    <Modal
      visible={showAddressModal && !!addressInfo}
      animationType="slide"
      transparent
      onRequestClose={() => setShowAddressModal(false)}
    >
      <View style={[styles.modalOverlay, { backgroundColor: 'rgba(0, 0, 0, 0.8)' }]}>
        <View style={[styles.modalContent, { backgroundColor: theme.colors.surface }]}>
          <View style={[styles.modalHeader, { borderBottomColor: theme.colors.border }]}>
            <View>
              <Text style={[styles.modalTitle, { color: theme.colors.text }]}>
                Address History
              </Text>
              <Text style={[styles.modalSubtitle, { color: theme.colors.textMuted }]}>
                {addressInfo ? formatAddress(addressInfo.address, 12) : ''}
              </Text>
            </View>
            <Button
              title="Close"
              variant="ghost"
              size="small"
              onPress={() => setShowAddressModal(false)}
            />
          </View>
          <FlatList
            data={addressInfo?.transactions || []}
            keyExtractor={(item) => item.txid}
            renderItem={({ item }) => (
              <TransactionItem
                transaction={item}
                currentAddress={addressInfo?.address || ''}
                onPress={() => {
                  setShowAddressModal(false);
                  setSearchQuery(item.txid);
                  handleSearch(item.txid);
                }}
              />
            )}
            contentContainerStyle={styles.addressTxList}
          />
        </View>
      </View>
    </Modal>
  );

  // ============== Main Render ==============

  return (
    <View style={[styles.container, { backgroundColor: theme.colors.background }]}>
      {/* Stats Header */}
      {renderStatsCard()}

      {/* Tabs */}
      <View style={styles.tabs}>
        {renderTab('blocks', 'Blocks', 'box')}
        {renderTab('transactions', 'Recent', 'activity')}
        {renderTab('mempool', 'Mempool', 'layers')}
        {renderTab('search', 'Search', 'search')}
      </View>

      {/* Content */}
      {activeTab === 'search' ? (
        renderSearchContent()
      ) : activeTab === 'mempool' ? (
        <View style={styles.mempoolContainer}>
          {renderMempoolStats()}
          <FlatList
            data={mempoolTxs}
            keyExtractor={(item) => item.txid}
            renderItem={({ item }) => (
              <TransactionItem
                transaction={item}
                currentAddress=""
                onPress={() => {
                  setSearchQuery(item.txid);
                  handleSearch(item.txid);
                  setActiveTab('search');
                }}
              />
            )}
            onEndReached={() => {
              if (!loading && hasMore) {
                fetchMempoolTransactions();
              }
            }}
            onEndReachedThreshold={0.3}
            refreshControl={
              <RefreshControl
                refreshing={refreshing}
                onRefresh={onRefresh}
                tintColor={theme.colors.brand.primary}
              />
            }
            contentContainerStyle={styles.listContent}
            ListEmptyComponent={
              loading ? (
                <Text style={[styles.emptyText, { color: theme.colors.textMuted }]}>
                  Loading...
                </Text>
              ) : (
                <View style={styles.emptyContainer}>
                  <Icon name="inbox" size={48} color={theme.colors.textMuted} />
                  <Text style={[styles.emptyText, { color: theme.colors.textMuted }]}>
                    No pending transactions
                  </Text>
                </View>
              )
            }
          />
        </View>
      ) : (
        <FlatList
          data={activeTab === 'blocks' ? blocks : transactions}
          keyExtractor={(item: Block | Transaction) =>
            'index' in item ? `block-${item.index}` : item.txid
          }
          renderItem={({ item }) =>
            activeTab === 'blocks' ? (
              <BlockItem block={item as Block} onPress={() => setSelectedBlock(item as Block)} />
            ) : (
              <TransactionItem
                transaction={item as Transaction}
                currentAddress=""
                onPress={() => {
                  setSearchQuery((item as Transaction).txid);
                  handleSearch((item as Transaction).txid);
                  setActiveTab('search');
                }}
              />
            )
          }
          onEndReached={() => {
            if (!loading && hasMore) {
              if (activeTab === 'blocks') {
                fetchBlocks();
              } else {
                fetchTransactions();
              }
            }
          }}
          onEndReachedThreshold={0.3}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={onRefresh}
              tintColor={theme.colors.brand.primary}
            />
          }
          contentContainerStyle={styles.listContent}
          ListEmptyComponent={
            loading ? (
              <Text style={[styles.emptyText, { color: theme.colors.textMuted }]}>Loading...</Text>
            ) : (
              <Text style={[styles.emptyText, { color: theme.colors.textMuted }]}>No data</Text>
            )
          }
        />
      )}

      {/* Modals */}
      {renderBlockModal()}
      {renderAddressModal()}
    </View>
  );
}

// ============== Detail Row Component ==============

interface DetailRowProps {
  label: string;
  value: string | React.ReactNode;
  fullValue?: string;
  copyable?: boolean;
  onPress?: () => void;
  isLast?: boolean;
  valueStyle?: any;
  theme: any;
  onCopy?: (value: string, label: string) => void;
}

function DetailRow({
  label,
  value,
  fullValue,
  copyable,
  onPress,
  isLast,
  valueStyle,
  theme,
  onCopy,
}: DetailRowProps) {
  const content = (
    <View
      style={[
        styles.detailRow,
        !isLast && { borderBottomWidth: 1, borderBottomColor: theme.colors.border },
      ]}
    >
      <Text style={[styles.detailLabel, { color: theme.colors.textMuted }]}>{label}</Text>
      <View style={styles.detailValueContainer}>
        {typeof value === 'string' ? (
          <Text
            style={[styles.detailValue, { color: theme.colors.text }, valueStyle]}
            numberOfLines={1}
          >
            {value}
          </Text>
        ) : (
          value
        )}
        {copyable && onCopy && (
          <TouchableOpacity
            onPress={() => onCopy(fullValue || (value as string), label)}
            style={styles.copyButton}
          >
            <Icon name="copy" size={14} color={theme.colors.brand.primary} />
          </TouchableOpacity>
        )}
        {onPress && (
          <TouchableOpacity onPress={onPress} style={styles.linkButton}>
            <Icon name="external-link" size={14} color={theme.colors.brand.primary} />
          </TouchableOpacity>
        )}
      </View>
    </View>
  );

  if (onPress && !copyable) {
    return <TouchableOpacity onPress={onPress}>{content}</TouchableOpacity>;
  }

  return content;
}

// ============== Styles ==============

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  statsCard: {
    margin: spacing['4'],
    marginBottom: spacing['2'],
  },
  statsGrid: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  statItem: {
    alignItems: 'center',
  },
  statValue: {
    fontSize: 16,
    fontWeight: '700',
    marginBottom: 2,
  },
  statLabel: {
    fontSize: 11,
  },
  offlineBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing['2'],
    marginTop: spacing['3'],
    paddingVertical: spacing['2'],
    borderRadius: borderRadius.md,
  },
  offlineText: {
    fontSize: 12,
    fontWeight: '500',
  },
  // Tabs
  tabs: {
    flexDirection: 'row',
    paddingHorizontal: spacing['4'],
    marginBottom: spacing['2'],
    gap: spacing['2'],
  },
  tab: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing['1'],
    paddingVertical: spacing['2'],
    borderRadius: borderRadius.md,
  },
  tabText: {
    fontSize: 12,
    fontWeight: '600',
  },
  activeTabText: {
    color: '#ffffff',
  },
  // Lists
  listContent: {
    padding: spacing['4'],
    paddingTop: spacing['2'],
  },
  emptyContainer: {
    alignItems: 'center',
    paddingVertical: spacing['10'],
  },
  emptyText: {
    textAlign: 'center',
    paddingVertical: spacing['10'],
  },
  // Search
  searchContainer: {
    flex: 1,
  },
  searchContent: {
    padding: spacing['4'],
  },
  searchInputRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: spacing['2'],
    marginBottom: spacing['4'],
  },
  searchButton: {
    marginTop: spacing['1'],
  },
  suggestionsCard: {
    marginBottom: spacing['4'],
  },
  suggestionItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing['3'],
    paddingVertical: spacing['3'],
    borderBottomWidth: 1,
  },
  suggestionText: {
    flex: 1,
    fontSize: 14,
  },
  recentSearchesCard: {
    marginBottom: spacing['4'],
  },
  clearText: {
    fontSize: 14,
    fontWeight: '500',
  },
  recentItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing['3'],
    paddingVertical: spacing['3'],
    borderBottomWidth: 1,
  },
  recentItemContent: {
    flex: 1,
  },
  recentLabel: {
    fontSize: 14,
  },
  recentTime: {
    fontSize: 12,
    marginTop: 2,
  },
  // Results
  resultCard: {
    marginTop: spacing['2'],
  },
  notFoundContainer: {
    alignItems: 'center',
    paddingVertical: spacing['6'],
  },
  notFoundTitle: {
    fontSize: 18,
    fontWeight: '600',
    marginTop: spacing['3'],
  },
  notFoundText: {
    fontSize: 14,
    marginTop: spacing['2'],
    textAlign: 'center',
  },
  notFoundHint: {
    fontSize: 12,
    marginTop: spacing['2'],
    textAlign: 'center',
  },
  errorContainer: {
    alignItems: 'center',
    paddingVertical: spacing['6'],
  },
  errorText: {
    fontSize: 14,
    marginTop: spacing['3'],
    textAlign: 'center',
  },
  txResultContent: {
    paddingTop: spacing['2'],
  },
  addressResultContent: {
    paddingTop: spacing['2'],
  },
  addressTxSection: {
    marginTop: spacing['4'],
    borderTopWidth: 1,
    borderTopColor: '#2e2e3e',
    paddingTop: spacing['3'],
  },
  addressTxTitle: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: spacing['3'],
  },
  viewAllButton: {
    marginTop: spacing['2'],
  },
  // Mempool
  mempoolContainer: {
    flex: 1,
  },
  mempoolStatsCard: {
    marginHorizontal: spacing['4'],
    marginBottom: spacing['2'],
  },
  mempoolStatsRow: {
    flexDirection: 'row',
    justifyContent: 'space-around',
  },
  mempoolStatItem: {
    alignItems: 'center',
  },
  mempoolStatValue: {
    fontSize: 16,
    fontWeight: '700',
    marginTop: spacing['1'],
  },
  mempoolStatLabel: {
    fontSize: 11,
    marginTop: 2,
  },
  // Modal
  modalOverlay: {
    flex: 1,
    justifyContent: 'flex-end',
  },
  modalContent: {
    borderTopLeftRadius: borderRadius.xl,
    borderTopRightRadius: borderRadius.xl,
    maxHeight: '85%',
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: spacing['4'],
    borderBottomWidth: 1,
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: '700',
  },
  modalSubtitle: {
    fontSize: 12,
    marginTop: 2,
    fontFamily: 'monospace',
  },
  modalScroll: {
    padding: spacing['4'],
  },
  txHeader: {
    fontSize: 16,
    fontWeight: '600',
    marginTop: spacing['4'],
    marginBottom: spacing['3'],
  },
  addressTxList: {
    padding: spacing['4'],
  },
  // Detail Row
  detailRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: spacing['3'],
  },
  detailLabel: {
    fontSize: 14,
    flex: 1,
  },
  detailValueContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 2,
    justifyContent: 'flex-end',
  },
  detailValue: {
    fontSize: 14,
    fontFamily: 'monospace',
    textAlign: 'right',
  },
  copyButton: {
    marginLeft: spacing['2'],
    padding: spacing['1'],
  },
  linkButton: {
    marginLeft: spacing['2'],
    padding: spacing['1'],
  },
});
