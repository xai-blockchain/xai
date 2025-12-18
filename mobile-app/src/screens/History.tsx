import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  SafeAreaView,
  RefreshControl,
  ActivityIndicator,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { useWalletStore } from '@/store/wallet';
import { useAppStore } from '@/store/app';
import APIService from '@/services/api';
import { Transaction } from '@/types';
import { formatAddress, formatBalance, formatDate } from '@/utils/format';
import { COLORS, UI } from '@/constants';

const History: React.FC = () => {
  const navigation = useNavigation();
  const { wallet } = useWalletStore();
  const { updateActivity } = useAppStore();
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [offset, setOffset] = useState(0);

  useEffect(() => {
    updateActivity();
    loadTransactions();
  }, []);

  const loadTransactions = async (loadMore: boolean = false) => {
    if (!wallet) return;

    try {
      const currentOffset = loadMore ? offset : 0;
      const history = await APIService.getHistory(
        wallet.address,
        UI.PAGINATION_LIMIT,
        currentOffset,
      );

      if (loadMore) {
        setTransactions(prev => [...prev, ...history.transactions]);
      } else {
        setTransactions(history.transactions);
      }

      setOffset(currentOffset + history.transactions.length);
      setHasMore(history.transactions.length === UI.PAGINATION_LIMIT);
    } catch (error) {
      console.error('Failed to load transactions:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const onRefresh = () => {
    setRefreshing(true);
    setOffset(0);
    loadTransactions(false);
  };

  const onEndReached = () => {
    if (!loading && hasMore) {
      loadTransactions(true);
    }
  };

  const handleTransactionPress = (txid: string) => {
    navigation.navigate('TransactionDetail' as never, { txid } as never);
  };

  const renderTransaction = ({ item }: { item: Transaction }) => {
    const isReceived = item.recipient === wallet?.address;

    return (
      <TouchableOpacity
        style={styles.transactionItem}
        onPress={() => handleTransactionPress(item.txid)}>
        <View
          style={[
            styles.txIcon,
            { backgroundColor: isReceived ? COLORS.success + '20' : COLORS.error + '20' },
          ]}>
          <Text style={{ color: isReceived ? COLORS.success : COLORS.error, fontSize: 20 }}>
            {isReceived ? '↓' : '↑'}
          </Text>
        </View>

        <View style={styles.txInfo}>
          <Text style={styles.txType}>{isReceived ? 'Received' : 'Sent'}</Text>
          <Text style={styles.txAddress}>
            {isReceived ? `From: ${formatAddress(item.sender)}` : `To: ${formatAddress(item.recipient)}`}
          </Text>
          <Text style={styles.txDate}>{formatDate(item.timestamp)}</Text>
        </View>

        <View style={styles.txAmount}>
          <Text
            style={[
              styles.txAmountText,
              { color: isReceived ? COLORS.success : COLORS.text },
            ]}>
            {isReceived ? '+' : '-'}
            {formatBalance(item.amount)} XAI
          </Text>
          {item.confirmations !== undefined && (
            <Text style={styles.confirmations}>
              {item.confirmations > 6 ? 'Confirmed' : `${item.confirmations} conf`}
            </Text>
          )}
        </View>
      </TouchableOpacity>
    );
  };

  const renderEmpty = () => (
    <View style={styles.emptyState}>
      <Text style={styles.emptyStateIcon}>📭</Text>
      <Text style={styles.emptyStateText}>No transactions yet</Text>
      <Text style={styles.emptyStateSubtext}>Your transaction history will appear here</Text>
    </View>
  );

  const renderFooter = () => {
    if (!loading || transactions.length === 0) return null;
    return (
      <View style={styles.footer}>
        <ActivityIndicator size="small" color={COLORS.primary} />
      </View>
    );
  };

  if (loading && transactions.length === 0) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={COLORS.primary} />
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <FlatList
        data={transactions}
        renderItem={renderTransaction}
        keyExtractor={item => item.txid}
        contentContainerStyle={styles.listContent}
        ListEmptyComponent={renderEmpty}
        ListFooterComponent={renderFooter}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
        onEndReached={onEndReached}
        onEndReachedThreshold={0.5}
      />
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.background,
  },
  listContent: {
    padding: 16,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
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
    width: 44,
    height: 44,
    borderRadius: 22,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
  txInfo: {
    flex: 1,
  },
  txType: {
    fontSize: 16,
    fontWeight: '600',
    color: COLORS.text,
    marginBottom: 4,
  },
  txAddress: {
    fontSize: 12,
    color: COLORS.text,
    opacity: 0.7,
    marginBottom: 2,
  },
  txDate: {
    fontSize: 11,
    color: COLORS.text,
    opacity: 0.5,
  },
  txAmount: {
    alignItems: 'flex-end',
  },
  txAmountText: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 4,
  },
  confirmations: {
    fontSize: 10,
    color: COLORS.text,
    opacity: 0.6,
  },
  emptyState: {
    alignItems: 'center',
    paddingVertical: 80,
  },
  emptyStateIcon: {
    fontSize: 64,
    marginBottom: 16,
  },
  emptyStateText: {
    fontSize: 18,
    fontWeight: '600',
    color: COLORS.text,
    marginBottom: 8,
  },
  emptyStateSubtext: {
    fontSize: 14,
    color: COLORS.text,
    opacity: 0.6,
  },
  footer: {
    paddingVertical: 20,
    alignItems: 'center',
  },
});

export default History;
