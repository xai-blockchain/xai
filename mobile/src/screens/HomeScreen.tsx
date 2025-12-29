/**
 * Home Screen - Dashboard view with wallet balance and recent transactions
 */

import React, { useEffect, useState, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  RefreshControl,
  TouchableOpacity,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { useWallet } from '../context/WalletContext';
import { Card, Button, TransactionItem, StatusBadge } from '../components';
import { formatXaiWithSymbol, formatAddress, formatCompactNumber } from '../utils/format';
import { xaiApi } from '../services/api';
import { Transaction, BlockchainStats } from '../types';

export function HomeScreen() {
  const navigation = useNavigation<any>();
  const { wallet, balance, isConnected, refreshBalance, refreshConnection } = useWallet();
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [stats, setStats] = useState<BlockchainStats | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    try {
      // Fetch stats
      const statsResult = await xaiApi.getStats();
      if (statsResult.success && statsResult.data) {
        setStats(statsResult.data);
      }

      // Fetch recent transactions if wallet exists
      if (wallet) {
        const historyResult = await xaiApi.getHistory(wallet.address, 5, 0);
        if (historyResult.success && historyResult.data) {
          setTransactions(historyResult.data.transactions);
        }
      }
    } catch (error) {
      console.error('Failed to fetch data:', error);
    } finally {
      setLoading(false);
    }
  }, [wallet]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await Promise.all([refreshBalance(), refreshConnection(), fetchData()]);
    setRefreshing(false);
  }, [refreshBalance, refreshConnection, fetchData]);

  // No wallet state
  if (!wallet) {
    return (
      <View style={styles.container}>
        <View style={styles.noWalletContainer}>
          <Text style={styles.noWalletTitle}>Welcome to XAI</Text>
          <Text style={styles.noWalletSubtitle}>
            Create or import a wallet to get started
          </Text>
          <View style={styles.noWalletButtons}>
            <Button
              title="Create Wallet"
              onPress={() => navigation.navigate('Wallet')}
              style={{ marginBottom: 12 }}
            />
            <Button
              title="Import Wallet"
              variant="outline"
              onPress={() => navigation.navigate('Wallet')}
            />
          </View>
        </View>
      </View>
    );
  }

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={onRefresh}
          tintColor="#6366f1"
        />
      }
    >
      {/* Connection Status */}
      <View style={styles.statusBar}>
        <StatusBadge
          status={isConnected ? 'success' : 'error'}
          label={isConnected ? 'Connected' : 'Disconnected'}
        />
        {stats && (
          <Text style={styles.blockHeight}>
            Block #{formatCompactNumber(stats.chainHeight)}
          </Text>
        )}
      </View>

      {/* Balance Card */}
      <Card style={styles.balanceCard}>
        <Text style={styles.balanceLabel}>Total Balance</Text>
        <Text style={styles.balanceAmount}>{formatXaiWithSymbol(balance)}</Text>
        <Text style={styles.addressText}>{formatAddress(wallet.address, 10)}</Text>
        <View style={styles.balanceActions}>
          <Button
            title="Send"
            onPress={() => navigation.navigate('Send')}
            size="small"
            style={{ flex: 1, marginRight: 8 }}
          />
          <Button
            title="Receive"
            variant="outline"
            onPress={() => navigation.navigate('Wallet')}
            size="small"
            style={{ flex: 1 }}
          />
        </View>
      </Card>

      {/* Network Stats */}
      {stats && (
        <Card title="Network">
          <View style={styles.statsGrid}>
            <View style={styles.statItem}>
              <Text style={styles.statValue}>{formatCompactNumber(stats.chainHeight)}</Text>
              <Text style={styles.statLabel}>Blocks</Text>
            </View>
            <View style={styles.statItem}>
              <Text style={styles.statValue}>{stats.peers}</Text>
              <Text style={styles.statLabel}>Peers</Text>
            </View>
            <View style={styles.statItem}>
              <Text style={styles.statValue}>{stats.pendingTransactionsCount}</Text>
              <Text style={styles.statLabel}>Pending TX</Text>
            </View>
            <View style={styles.statItem}>
              <Text style={styles.statValue}>
                {formatCompactNumber(stats.totalSupply)}
              </Text>
              <Text style={styles.statLabel}>Supply</Text>
            </View>
          </View>
        </Card>
      )}

      {/* Recent Transactions */}
      <Card title="Recent Activity">
        {loading ? (
          <Text style={styles.emptyText}>Loading...</Text>
        ) : transactions.length === 0 ? (
          <Text style={styles.emptyText}>No transactions yet</Text>
        ) : (
          <>
            {transactions.map((tx) => (
              <TransactionItem
                key={tx.txid}
                transaction={tx}
                currentAddress={wallet.address}
                onPress={() => {
                  // Navigate to transaction detail
                }}
              />
            ))}
            <TouchableOpacity
              style={styles.viewAllButton}
              onPress={() => navigation.navigate('Wallet')}
            >
              <Text style={styles.viewAllText}>View All Transactions</Text>
            </TouchableOpacity>
          </>
        )}
      </Card>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0f0f1a',
  },
  content: {
    padding: 16,
    paddingBottom: 32,
  },
  statusBar: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  blockHeight: {
    fontSize: 12,
    color: '#6b7280',
    fontFamily: 'monospace',
  },
  balanceCard: {
    alignItems: 'center',
    paddingVertical: 24,
  },
  balanceLabel: {
    fontSize: 14,
    color: '#9ca3af',
    marginBottom: 8,
  },
  balanceAmount: {
    fontSize: 36,
    fontWeight: '700',
    color: '#ffffff',
    marginBottom: 8,
  },
  addressText: {
    fontSize: 14,
    color: '#6b7280',
    fontFamily: 'monospace',
    marginBottom: 20,
  },
  balanceActions: {
    flexDirection: 'row',
    width: '100%',
  },
  statsGrid: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  statItem: {
    alignItems: 'center',
  },
  statValue: {
    fontSize: 18,
    fontWeight: '700',
    color: '#ffffff',
    marginBottom: 4,
  },
  statLabel: {
    fontSize: 12,
    color: '#6b7280',
  },
  emptyText: {
    textAlign: 'center',
    color: '#6b7280',
    paddingVertical: 20,
  },
  viewAllButton: {
    alignItems: 'center',
    paddingVertical: 12,
    marginTop: 8,
  },
  viewAllText: {
    color: '#6366f1',
    fontWeight: '600',
    fontSize: 14,
  },
  // No wallet state
  noWalletContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 32,
  },
  noWalletTitle: {
    fontSize: 28,
    fontWeight: '700',
    color: '#ffffff',
    marginBottom: 12,
  },
  noWalletSubtitle: {
    fontSize: 16,
    color: '#6b7280',
    textAlign: 'center',
    marginBottom: 32,
  },
  noWalletButtons: {
    width: '100%',
    maxWidth: 280,
  },
});
