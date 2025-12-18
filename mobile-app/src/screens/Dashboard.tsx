import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  RefreshControl,
  ScrollView,
  SafeAreaView,
} from 'react-native';
import { useWalletStore } from '@/store/wallet';
import { useAppStore } from '@/store/app';
import { formatBalance, formatAddress, formatRelativeTime } from '@/utils/format';
import { COLORS } from '@/constants';
import WebSocketService from '@/services/websocket';
import { Transaction } from '@/types';

const Dashboard: React.FC = () => {
  const { wallet, balance, refreshBalance, pendingTransactions } = useWalletStore();
  const { updateActivity } = useAppStore();
  const [recentTransactions, setRecentTransactions] = useState<Transaction[]>([]);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    updateActivity();
    loadData();

    // Connect WebSocket for real-time updates
    WebSocketService.connect();

    // Subscribe to balance updates
    const unsubBalance = WebSocketService.on('balance', handleBalanceUpdate);
    const unsubTransaction = WebSocketService.on('transaction', handleNewTransaction);

    return () => {
      unsubBalance();
      unsubTransaction();
    };
  }, []);

  const loadData = async () => {
    await refreshBalance();
    // Load recent transactions from API
    // This would be implemented with APIService.getHistory()
  };

  const handleBalanceUpdate = (data: any) => {
    if (data.address === wallet?.address) {
      refreshBalance();
    }
  };

  const handleNewTransaction = (tx: Transaction) => {
    if (tx.sender === wallet?.address || tx.recipient === wallet?.address) {
      setRecentTransactions(prev => [tx, ...prev].slice(0, 5));
      refreshBalance();
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await loadData();
    setRefreshing(false);
  };

  if (!wallet) return null;

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView
        style={styles.scrollView}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}>
        {/* Balance Card */}
        <View style={styles.balanceCard}>
          <Text style={styles.balanceLabel}>Total Balance</Text>
          <Text style={styles.balance}>{formatBalance(balance)} XAI</Text>
          <Text style={styles.address}>{formatAddress(wallet.address, 12)}</Text>
        </View>

        {/* Quick Actions */}
        <View style={styles.actionsContainer}>
          <QuickAction icon="↑" label="Send" color={COLORS.error} />
          <QuickAction icon="↓" label="Receive" color={COLORS.success} />
          <QuickAction icon="↻" label="Swap" color={COLORS.primary} />
        </View>

        {/* Pending Transactions */}
        {pendingTransactions.length > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Pending Transactions</Text>
            {pendingTransactions.map(ptx => (
              <TransactionItem key={ptx.transaction.txid} tx={ptx.transaction} pending />
            ))}
          </View>
        )}

        {/* Recent Transactions */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>Recent Activity</Text>
            <TouchableOpacity>
              <Text style={styles.seeAll}>See All</Text>
            </TouchableOpacity>
          </View>

          {recentTransactions.length > 0 ? (
            recentTransactions.map(tx => <TransactionItem key={tx.txid} tx={tx} />)
          ) : (
            <View style={styles.emptyState}>
              <Text style={styles.emptyStateText}>No transactions yet</Text>
            </View>
          )}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
};

const QuickAction: React.FC<{ icon: string; label: string; color: string }> = ({
  icon,
  label,
  color,
}) => (
  <TouchableOpacity style={styles.quickAction}>
    <View style={[styles.quickActionIcon, { backgroundColor: color + '20' }]}>
      <Text style={[styles.quickActionIconText, { color }]}>{icon}</Text>
    </View>
    <Text style={styles.quickActionLabel}>{label}</Text>
  </TouchableOpacity>
);

const TransactionItem: React.FC<{ tx: Transaction; pending?: boolean }> = ({ tx, pending }) => {
  const isReceived = true; // Determine based on wallet address
  return (
    <TouchableOpacity style={styles.transactionItem}>
      <View style={[styles.txIcon, { backgroundColor: isReceived ? COLORS.success + '20' : COLORS.error + '20' }]}>
        <Text style={{ color: isReceived ? COLORS.success : COLORS.error }}>
          {isReceived ? '↓' : '↑'}
        </Text>
      </View>
      <View style={styles.txInfo}>
        <Text style={styles.txAddress}>{formatAddress(isReceived ? tx.sender : tx.recipient)}</Text>
        <Text style={styles.txTime}>{formatRelativeTime(tx.timestamp)}</Text>
      </View>
      <View style={styles.txAmount}>
        <Text style={[styles.txAmountText, { color: isReceived ? COLORS.success : COLORS.text }]}>
          {isReceived ? '+' : '-'}{formatBalance(tx.amount)} XAI
        </Text>
        {pending && <Text style={styles.pendingBadge}>Pending</Text>}
      </View>
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.background,
  },
  scrollView: {
    flex: 1,
  },
  balanceCard: {
    backgroundColor: COLORS.primary,
    margin: 16,
    padding: 24,
    borderRadius: 16,
    alignItems: 'center',
  },
  balanceLabel: {
    fontSize: 14,
    color: '#FFFFFF',
    opacity: 0.8,
    marginBottom: 8,
  },
  balance: {
    fontSize: 40,
    fontWeight: 'bold',
    color: '#FFFFFF',
    marginBottom: 12,
  },
  address: {
    fontSize: 14,
    color: '#FFFFFF',
    opacity: 0.7,
    fontFamily: 'monospace',
  },
  actionsContainer: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    paddingHorizontal: 16,
    marginBottom: 24,
  },
  quickAction: {
    alignItems: 'center',
    gap: 8,
  },
  quickActionIcon: {
    width: 56,
    height: 56,
    borderRadius: 28,
    alignItems: 'center',
    justifyContent: 'center',
  },
  quickActionIconText: {
    fontSize: 24,
    fontWeight: 'bold',
  },
  quickActionLabel: {
    fontSize: 14,
    color: COLORS.text,
    fontWeight: '500',
  },
  section: {
    paddingHorizontal: 16,
    marginBottom: 24,
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: COLORS.text,
  },
  seeAll: {
    fontSize: 14,
    color: COLORS.primary,
    fontWeight: '500',
  },
  transactionItem: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: COLORS.card,
    padding: 12,
    borderRadius: 12,
    marginBottom: 8,
  },
  txIcon: {
    width: 40,
    height: 40,
    borderRadius: 20,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
  txInfo: {
    flex: 1,
  },
  txAddress: {
    fontSize: 14,
    fontWeight: '500',
    color: COLORS.text,
    marginBottom: 4,
  },
  txTime: {
    fontSize: 12,
    color: COLORS.text,
    opacity: 0.6,
  },
  txAmount: {
    alignItems: 'flex-end',
  },
  txAmountText: {
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 4,
  },
  pendingBadge: {
    fontSize: 10,
    color: COLORS.warning,
    backgroundColor: COLORS.warning + '20',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
  },
  emptyState: {
    alignItems: 'center',
    paddingVertical: 40,
  },
  emptyStateText: {
    fontSize: 14,
    color: COLORS.text,
    opacity: 0.5,
  },
});

export default Dashboard;
