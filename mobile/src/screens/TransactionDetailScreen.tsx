/**
 * Transaction Detail Screen - Full transaction information
 *
 * Production-ready features:
 * - Full transaction info display
 * - Inputs and outputs (for UTXO model compatibility)
 * - Confirmations count with visual indicator
 * - Share transaction link
 * - Copy transaction data
 * - Explorer link
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  RefreshControl,
  Alert,
  Share,
  Linking,
} from 'react-native';
import * as Clipboard from 'expo-clipboard';
import { useRoute, RouteProp, useNavigation } from '@react-navigation/native';
import { Card, Button, Icon, StatusBadge } from '../components';
import { useTheme } from '../theme';
import { useWallet } from '../context/WalletContext';
import { triggerHaptic } from '../hooks/useHaptics';
import { xaiApi } from '../services/api';
import {
  formatXai,
  formatXaiWithSymbol,
  formatHash,
  formatDateTime,
  formatRelativeTime,
  formatAddress,
} from '../utils/format';
import { spacing, borderRadius } from '../theme/spacing';
import { Transaction, RootStackParamList } from '../types';

type TransactionDetailRouteProp = RouteProp<RootStackParamList, 'TransactionDetail'>;

// Confirmation thresholds
const CONFIRMATION_THRESHOLDS = {
  UNCONFIRMED: 0,
  LOW: 1,
  MEDIUM: 3,
  HIGH: 6,
  FINAL: 12,
};

interface TransactionDetails {
  transaction: Transaction;
  confirmations: number;
  block?: number;
  blockHash?: string;
  status: 'pending' | 'confirmed' | 'failed';
  found: boolean;
}

export function TransactionDetailScreen() {
  const theme = useTheme();
  const navigation = useNavigation();
  const route = useRoute<TransactionDetailRouteProp>();
  const { activeWallet } = useWallet();

  const { txid } = route.params;

  // State
  const [details, setDetails] = useState<TransactionDetails | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch transaction details
  const fetchDetails = useCallback(async () => {
    try {
      const result = await xaiApi.getTransaction(txid);
      if (result.success && result.data) {
        setDetails({
          transaction: result.data.transaction || ({} as Transaction),
          confirmations: result.data.confirmations || 0,
          block: result.data.block,
          status: result.data.status === 'pending' ? 'pending' : 'confirmed',
          found: result.data.found,
        });
        setError(null);
      } else {
        setError(result.error || 'Transaction not found');
      }
    } catch (err) {
      setError('Failed to load transaction details');
      console.error('Transaction fetch error:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [txid]);

  // Initial load
  useEffect(() => {
    fetchDetails();
  }, [fetchDetails]);

  // Auto-refresh for pending transactions
  useEffect(() => {
    if (details?.status === 'pending') {
      const interval = setInterval(fetchDetails, 10000); // Every 10 seconds
      return () => clearInterval(interval);
    }
  }, [details?.status, fetchDetails]);

  // Pull to refresh
  const onRefresh = useCallback(() => {
    setRefreshing(true);
    fetchDetails();
  }, [fetchDetails]);

  // Get confirmation status
  const getConfirmationStatus = (confirmations: number) => {
    if (confirmations === 0) {
      return { label: 'Pending', type: 'warning' as const };
    }
    if (confirmations < CONFIRMATION_THRESHOLDS.MEDIUM) {
      return { label: 'Low', type: 'warning' as const };
    }
    if (confirmations < CONFIRMATION_THRESHOLDS.HIGH) {
      return { label: 'Medium', type: 'info' as const };
    }
    if (confirmations < CONFIRMATION_THRESHOLDS.FINAL) {
      return { label: 'High', type: 'success' as const };
    }
    return { label: 'Final', type: 'success' as const };
  };

  // Determine if incoming or outgoing
  const isIncoming = useCallback(
    (tx: Transaction) => {
      if (!activeWallet) return false;
      return tx.recipient.toLowerCase() === activeWallet.address.toLowerCase();
    },
    [activeWallet]
  );

  // Copy to clipboard
  const handleCopy = async (value: string, label: string) => {
    try {
      await Clipboard.setStringAsync(value);
      triggerHaptic('success');
      Alert.alert('Copied', `${label} copied to clipboard`);
    } catch {
      Alert.alert('Error', 'Failed to copy');
    }
  };

  // Share transaction
  const handleShare = async () => {
    if (!details) return;

    const tx = details.transaction;
    const message = `XAI Transaction\n\nTxID: ${tx.txid}\nAmount: ${formatXaiWithSymbol(
      tx.amount
    )}\nFrom: ${tx.sender}\nTo: ${tx.recipient}\nStatus: ${details.status}\nConfirmations: ${details.confirmations}`;

    try {
      await Share.share({
        message,
        title: 'XAI Transaction',
      });
    } catch (error) {
      // User cancelled
    }
  };

  // Open in explorer
  const handleOpenExplorer = () => {
    if (!details) return;
    // Would link to block explorer
    const url = `https://explorer.xai.network/tx/${details.transaction.txid}`;
    Linking.openURL(url).catch(() => {
      Alert.alert('Error', 'Could not open explorer');
    });
  };

  // Detail row component
  const DetailRow = ({
    label,
    value,
    copyable = false,
    fullValue,
    isLast = false,
  }: {
    label: string;
    value: string;
    copyable?: boolean;
    fullValue?: string;
    isLast?: boolean;
  }) => (
    <View
      style={[
        styles.detailRow,
        !isLast && { borderBottomWidth: 1, borderBottomColor: theme.colors.border },
      ]}
    >
      <Text style={[styles.detailLabel, { color: theme.colors.textMuted }]}>{label}</Text>
      <View style={styles.detailValueContainer}>
        <Text
          style={[styles.detailValue, { color: theme.colors.text }]}
          selectable={copyable}
          numberOfLines={copyable ? undefined : 1}
        >
          {value}
        </Text>
        {copyable && (
          <Button
            variant="ghost"
            size="small"
            onPress={() => handleCopy(fullValue || value, label)}
            style={styles.copyButton}
          >
            <Icon name="copy" size={14} color={theme.colors.brand.primary} />
          </Button>
        )}
      </View>
    </View>
  );

  // Loading state
  if (loading) {
    return (
      <View style={[styles.container, { backgroundColor: theme.colors.background }]}>
        <View style={styles.centerContent}>
          <Text style={[styles.loadingText, { color: theme.colors.textMuted }]}>
            Loading transaction...
          </Text>
        </View>
      </View>
    );
  }

  // Error state
  if (error || !details) {
    return (
      <View style={[styles.container, { backgroundColor: theme.colors.background }]}>
        <View style={styles.centerContent}>
          <Icon name="alert-circle" size={64} color={theme.colors.semantic.error} />
          <Text style={[styles.errorTitle, { color: theme.colors.text }]}>
            Transaction Not Found
          </Text>
          <Text style={[styles.errorSubtitle, { color: theme.colors.textMuted }]}>
            {error || 'The transaction could not be found'}
          </Text>
          <Button
            title="Go Back"
            variant="primary"
            onPress={() => navigation.goBack()}
            style={styles.backButton}
          />
        </View>
      </View>
    );
  }

  const tx = details.transaction;
  const incoming = isIncoming(tx);
  const confirmStatus = getConfirmationStatus(details.confirmations);

  return (
    <ScrollView
      style={[styles.container, { backgroundColor: theme.colors.background }]}
      contentContainerStyle={styles.content}
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={onRefresh}
          tintColor={theme.colors.brand.primary}
        />
      }
    >
      {/* Transaction Summary Card */}
      <Card style={styles.summaryCard}>
        {/* Status Badge */}
        <View style={styles.statusContainer}>
          <StatusBadge
            status={details.status === 'pending' ? 'warning' : 'success'}
            label={details.status === 'pending' ? 'Pending' : 'Confirmed'}
          />
          {details.confirmations > 0 && (
            <View
              style={[
                styles.confirmationBadge,
                { backgroundColor: theme.colors.semantic.successMuted },
              ]}
            >
              <Icon name="check-circle" size={14} color={theme.colors.semantic.success} />
              <Text style={[styles.confirmationText, { color: theme.colors.semantic.success }]}>
                {details.confirmations} confirmation{details.confirmations !== 1 ? 's' : ''}
              </Text>
            </View>
          )}
        </View>

        {/* Amount */}
        <View style={styles.amountContainer}>
          <Text
            style={[
              styles.amount,
              {
                color: incoming
                  ? theme.colors.semantic.success
                  : theme.colors.semantic.error,
              },
            ]}
          >
            {incoming ? '+' : '-'}
            {formatXaiWithSymbol(tx.amount)}
          </Text>
          <Text style={[styles.amountLabel, { color: theme.colors.textMuted }]}>
            {incoming ? 'Received' : 'Sent'}
          </Text>
        </View>

        {/* Transaction Direction */}
        <View style={styles.directionContainer}>
          <View style={styles.directionParty}>
            <Text style={[styles.directionLabel, { color: theme.colors.textMuted }]}>
              From
            </Text>
            <Text
              style={[styles.directionAddress, { color: theme.colors.text }]}
              numberOfLines={1}
            >
              {formatAddress(tx.sender, 10)}
            </Text>
          </View>
          <Icon name="arrow-right" size={24} color={theme.colors.textMuted} />
          <View style={[styles.directionParty, styles.directionPartyRight]}>
            <Text style={[styles.directionLabel, { color: theme.colors.textMuted }]}>
              To
            </Text>
            <Text
              style={[styles.directionAddress, { color: theme.colors.text }]}
              numberOfLines={1}
            >
              {formatAddress(tx.recipient, 10)}
            </Text>
          </View>
        </View>
      </Card>

      {/* Transaction Details Card */}
      <Card title="Transaction Details">
        <DetailRow
          label="Transaction ID"
          value={formatHash(tx.txid, 12)}
          fullValue={tx.txid}
          copyable
        />
        <DetailRow label="Date" value={formatDateTime(tx.timestamp)} />
        <DetailRow label="Relative Time" value={formatRelativeTime(tx.timestamp)} />
        <DetailRow label="Amount" value={formatXaiWithSymbol(tx.amount)} />
        <DetailRow label="Fee" value={formatXaiWithSymbol(tx.fee)} />
        <DetailRow
          label="Total"
          value={formatXaiWithSymbol(tx.amount + (incoming ? 0 : tx.fee))}
          isLast
        />
      </Card>

      {/* Addresses Card */}
      <Card title="Addresses">
        <DetailRow
          label="Sender"
          value={formatAddress(tx.sender, 10)}
          fullValue={tx.sender}
          copyable
        />
        <DetailRow
          label="Recipient"
          value={formatAddress(tx.recipient, 10)}
          fullValue={tx.recipient}
          copyable
          isLast
        />
      </Card>

      {/* Block Info Card */}
      <Card title="Block Information">
        <DetailRow
          label="Status"
          value={confirmStatus.label}
        />
        <DetailRow
          label="Confirmations"
          value={details.confirmations.toString()}
        />
        {details.block !== undefined && (
          <DetailRow
            label="Block Height"
            value={details.block.toString()}
          />
        )}
        <DetailRow label="Nonce" value={tx.nonce.toString()} isLast />
      </Card>

      {/* Confirmation Progress */}
      {details.confirmations < CONFIRMATION_THRESHOLDS.FINAL && (
        <Card title="Confirmation Progress">
          <View style={styles.progressContainer}>
            <View
              style={[
                styles.progressBar,
                { backgroundColor: theme.colors.surfaceOverlay },
              ]}
            >
              <View
                style={[
                  styles.progressFill,
                  {
                    backgroundColor: theme.colors.brand.primary,
                    width: `${Math.min(
                      100,
                      (details.confirmations / CONFIRMATION_THRESHOLDS.FINAL) * 100
                    )}%`,
                  },
                ]}
              />
            </View>
            <Text style={[styles.progressText, { color: theme.colors.textMuted }]}>
              {details.confirmations} / {CONFIRMATION_THRESHOLDS.FINAL} confirmations for finality
            </Text>
          </View>
        </Card>
      )}

      {/* Raw Data (Advanced) */}
      {tx.signature && (
        <Card title="Advanced">
          <DetailRow
            label="Signature"
            value={formatHash(tx.signature, 10)}
            fullValue={tx.signature}
            copyable
            isLast
          />
        </Card>
      )}

      {/* Action Buttons */}
      <View style={styles.actions}>
        <Button
          title="Share"
          variant="secondary"
          icon="share"
          onPress={handleShare}
          style={styles.actionButton}
        />
        <Button
          title="Explorer"
          variant="secondary"
          icon="external-link"
          onPress={handleOpenExplorer}
          style={styles.actionButton}
        />
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  content: {
    padding: spacing['4'],
    paddingBottom: spacing['8'],
  },
  centerContent: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: spacing['8'],
  },
  loadingText: {
    fontSize: 16,
  },
  errorTitle: {
    fontSize: 20,
    fontWeight: '600',
    marginTop: spacing['4'],
    textAlign: 'center',
  },
  errorSubtitle: {
    fontSize: 14,
    marginTop: spacing['2'],
    textAlign: 'center',
  },
  backButton: {
    marginTop: spacing['6'],
  },
  // Summary card
  summaryCard: {
    alignItems: 'center',
    paddingVertical: spacing['6'],
  },
  statusContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing['2'],
    marginBottom: spacing['4'],
  },
  confirmationBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing['1'],
    paddingHorizontal: spacing['2'],
    paddingVertical: spacing['1'],
    borderRadius: borderRadius.md,
  },
  confirmationText: {
    fontSize: 12,
    fontWeight: '500',
  },
  amountContainer: {
    alignItems: 'center',
    marginBottom: spacing['4'],
  },
  amount: {
    fontSize: 32,
    fontWeight: '700',
  },
  amountLabel: {
    fontSize: 14,
    marginTop: spacing['1'],
  },
  // Direction
  directionContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    width: '100%',
    paddingHorizontal: spacing['2'],
  },
  directionParty: {
    flex: 1,
  },
  directionPartyRight: {
    alignItems: 'flex-end',
  },
  directionLabel: {
    fontSize: 12,
    marginBottom: spacing['1'],
  },
  directionAddress: {
    fontSize: 14,
    fontFamily: 'monospace',
  },
  // Details
  detailRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
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
    flexShrink: 1,
  },
  copyButton: {
    marginLeft: spacing['2'],
    padding: spacing['1'],
  },
  // Progress
  progressContainer: {
    alignItems: 'center',
  },
  progressBar: {
    width: '100%',
    height: 8,
    borderRadius: 4,
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    borderRadius: 4,
  },
  progressText: {
    fontSize: 12,
    marginTop: spacing['2'],
    textAlign: 'center',
  },
  // Actions
  actions: {
    flexDirection: 'row',
    gap: spacing['3'],
    marginTop: spacing['4'],
  },
  actionButton: {
    flex: 1,
  },
});
