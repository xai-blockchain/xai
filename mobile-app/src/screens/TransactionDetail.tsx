import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  SafeAreaView,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
} from 'react-native';
import { RouteProp } from '@react-navigation/native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RootStackParamList, Transaction } from '@/types';
import APIService from '@/services/api';
import { formatBalance, formatDate, formatAddress } from '@/utils/format';
import { COLORS } from '@/constants';
import * as Clipboard from '@react-native-clipboard/clipboard';

type TransactionDetailScreenProps = {
  route: RouteProp<RootStackParamList, 'TransactionDetail'>;
  navigation: NativeStackNavigationProp<RootStackParamList, 'TransactionDetail'>;
};

const TransactionDetail: React.FC<TransactionDetailScreenProps> = ({ route }) => {
  const { txid } = route.params;
  const [transaction, setTransaction] = useState<Transaction | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadTransaction();
  }, [txid]);

  const loadTransaction = async () => {
    try {
      const tx = await APIService.getTransaction(txid);
      setTransaction(tx);
    } catch (error) {
      console.error('Failed to load transaction:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = (text: string) => {
    Clipboard.setString(text);
  };

  if (loading) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={COLORS.primary} />
        </View>
      </SafeAreaView>
    );
  }

  if (!transaction) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.errorContainer}>
          <Text style={styles.errorText}>Transaction not found</Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView style={styles.scrollView} contentContainerStyle={styles.content}>
        <View style={styles.statusCard}>
          <Text style={styles.statusIcon}>
            {transaction.status === 'confirmed' ? '✓' : '⏳'}
          </Text>
          <Text style={styles.statusText}>
            {transaction.status === 'confirmed' ? 'Confirmed' : 'Pending'}
          </Text>
          {transaction.confirmations !== undefined && (
            <Text style={styles.confirmations}>{transaction.confirmations} confirmations</Text>
          )}
        </View>

        <View style={styles.amountCard}>
          <Text style={styles.amountLabel}>Amount</Text>
          <Text style={styles.amount}>{formatBalance(transaction.amount)} XAI</Text>
        </View>

        <View style={styles.detailsCard}>
          <DetailRow
            label="Transaction ID"
            value={txid}
            monospace
            copyable
            onCopy={() => handleCopy(txid)}
          />
          <DetailRow
            label="From"
            value={transaction.sender}
            monospace
            copyable
            onCopy={() => handleCopy(transaction.sender)}
          />
          <DetailRow
            label="To"
            value={transaction.recipient}
            monospace
            copyable
            onCopy={() => handleCopy(transaction.recipient)}
          />
          <DetailRow label="Date" value={formatDate(transaction.timestamp)} />
          <DetailRow label="Fee" value={`${formatBalance(transaction.fee)} XAI`} />
          <DetailRow label="Nonce" value={transaction.nonce.toString()} />
          {transaction.data && <DetailRow label="Data" value={transaction.data} />}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
};

const DetailRow: React.FC<{
  label: string;
  value: string;
  monospace?: boolean;
  copyable?: boolean;
  onCopy?: () => void;
}> = ({ label, value, monospace, copyable, onCopy }) => (
  <View style={styles.detailRow}>
    <Text style={styles.detailLabel}>{label}</Text>
    <View style={styles.detailValueContainer}>
      <Text style={[styles.detailValue, monospace && styles.monospace]} numberOfLines={1}>
        {value}
      </Text>
      {copyable && onCopy && (
        <TouchableOpacity onPress={onCopy} style={styles.copyButton}>
          <Text style={styles.copyButtonText}>Copy</Text>
        </TouchableOpacity>
      )}
    </View>
  </View>
);

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.background,
  },
  scrollView: {
    flex: 1,
  },
  content: {
    padding: 16,
    gap: 16,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  errorContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  errorText: {
    fontSize: 16,
    color: COLORS.error,
  },
  statusCard: {
    backgroundColor: COLORS.card,
    padding: 24,
    borderRadius: 16,
    alignItems: 'center',
  },
  statusIcon: {
    fontSize: 48,
    marginBottom: 12,
  },
  statusText: {
    fontSize: 20,
    fontWeight: '600',
    color: COLORS.text,
    marginBottom: 4,
  },
  confirmations: {
    fontSize: 14,
    color: COLORS.text,
    opacity: 0.6,
  },
  amountCard: {
    backgroundColor: COLORS.primary + '20',
    padding: 20,
    borderRadius: 12,
    alignItems: 'center',
  },
  amountLabel: {
    fontSize: 14,
    color: COLORS.text,
    opacity: 0.7,
    marginBottom: 4,
  },
  amount: {
    fontSize: 32,
    fontWeight: 'bold',
    color: COLORS.primary,
  },
  detailsCard: {
    backgroundColor: COLORS.card,
    padding: 16,
    borderRadius: 12,
    gap: 16,
  },
  detailRow: {
    gap: 4,
  },
  detailLabel: {
    fontSize: 12,
    fontWeight: '600',
    color: COLORS.text,
    opacity: 0.6,
  },
  detailValueContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  detailValue: {
    fontSize: 14,
    color: COLORS.text,
    flex: 1,
  },
  monospace: {
    fontFamily: 'monospace',
  },
  copyButton: {
    paddingHorizontal: 8,
    paddingVertical: 4,
  },
  copyButtonText: {
    fontSize: 12,
    color: COLORS.primary,
    fontWeight: '600',
  },
});

export default TransactionDetail;
