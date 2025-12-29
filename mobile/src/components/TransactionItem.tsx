/**
 * Transaction List Item Component
 *
 * Displays a transaction with amount, status, and accessibility support.
 */

import React, { useRef, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  Pressable,
  Animated,
} from 'react-native';
import { useTheme } from '../theme';
import { useHaptics } from '../hooks/useHaptics';
import { Icon } from './Icon';
import { Transaction } from '../types';
import { formatXai, formatRelativeTime, formatAddress } from '../utils/format';
import { spacing, borderRadius, touchTarget } from '../theme/spacing';

interface TransactionItemProps {
  transaction: Transaction;
  currentAddress: string;
  onPress?: () => void;
  showStatus?: boolean;
}

export function TransactionItem({
  transaction,
  currentAddress,
  onPress,
  showStatus = true,
}: TransactionItemProps) {
  const theme = useTheme();
  const haptics = useHaptics();
  const scaleValue = useRef(new Animated.Value(1)).current;

  const isOutgoing = transaction.sender === currentAddress;
  const counterparty = isOutgoing ? transaction.recipient : transaction.sender;
  const isPending = transaction.status === 'pending';

  // Press animation
  const handlePressIn = useCallback(() => {
    if (!onPress) return;
    Animated.spring(scaleValue, {
      toValue: 0.98,
      useNativeDriver: true,
      speed: 50,
      bounciness: 4,
    }).start();
  }, [scaleValue, onPress]);

  const handlePressOut = useCallback(() => {
    Animated.spring(scaleValue, {
      toValue: 1,
      useNativeDriver: true,
      speed: 50,
      bounciness: 4,
    }).start();
  }, [scaleValue]);

  const handlePress = useCallback(() => {
    if (!onPress) return;
    haptics.light();
    onPress();
  }, [haptics, onPress]);

  // Get icon and colors based on transaction type
  const getTransactionStyle = () => {
    if (isOutgoing) {
      return {
        icon: 'arrow-up' as const,
        iconBg: theme.colors.transaction.outgoingBg,
        iconColor: theme.colors.transaction.outgoing,
        amountColor: theme.colors.transaction.outgoing,
        prefix: '-',
        label: 'Sent',
      };
    }
    return {
      icon: 'arrow-down' as const,
      iconBg: theme.colors.transaction.incomingBg,
      iconColor: theme.colors.transaction.incoming,
      amountColor: theme.colors.transaction.incoming,
      prefix: '+',
      label: 'Received',
    };
  };

  const txStyle = getTransactionStyle();

  // Accessibility label
  const accessibilityLabel = `${txStyle.label} ${formatXai(transaction.amount)} XAI ${
    isOutgoing ? 'to' : 'from'
  } ${formatAddress(counterparty, 8)}, ${formatRelativeTime(transaction.timestamp)}${
    isPending ? ', pending confirmation' : ''
  }`;

  const content = (
    <View style={styles.container}>
      {/* Icon */}
      <View
        style={[
          styles.iconContainer,
          { backgroundColor: txStyle.iconBg },
        ]}
      >
        <Icon
          name={txStyle.icon}
          size={20}
          color={txStyle.iconColor}
        />
      </View>

      {/* Details */}
      <View style={styles.details}>
        <Text
          style={[styles.type, { color: theme.colors.text }]}
          numberOfLines={1}
        >
          {txStyle.label}
        </Text>
        <Text
          style={[styles.address, { color: theme.colors.textMuted }]}
          numberOfLines={1}
        >
          {formatAddress(counterparty, 8)}
        </Text>
      </View>

      {/* Amount and status */}
      <View style={styles.amountContainer}>
        <Text
          style={[styles.amount, { color: txStyle.amountColor }]}
          numberOfLines={1}
        >
          {txStyle.prefix}{formatXai(transaction.amount)} XAI
        </Text>
        <Text
          style={[styles.time, { color: theme.colors.textMuted }]}
          numberOfLines={1}
        >
          {formatRelativeTime(transaction.timestamp)}
        </Text>
        {showStatus && isPending && (
          <View
            style={[
              styles.pendingBadge,
              { backgroundColor: theme.colors.transaction.pendingBg },
            ]}
          >
            <Text
              style={[styles.pendingText, { color: theme.colors.transaction.pending }]}
            >
              Pending
            </Text>
          </View>
        )}
      </View>

      {/* Chevron for pressable items */}
      {onPress && (
        <Icon
          name="chevron-right"
          size={16}
          color={theme.colors.textMuted}
          style={styles.chevron}
        />
      )}
    </View>
  );

  if (onPress) {
    return (
      <Animated.View style={{ transform: [{ scale: scaleValue }] }}>
        <Pressable
          style={[
            styles.pressable,
            { borderBottomColor: theme.colors.border },
          ]}
          onPress={handlePress}
          onPressIn={handlePressIn}
          onPressOut={handlePressOut}
          accessible
          accessibilityRole="button"
          accessibilityLabel={accessibilityLabel}
          accessibilityHint="Double tap to view transaction details"
        >
          {content}
        </Pressable>
      </Animated.View>
    );
  }

  return (
    <View
      style={[styles.pressable, { borderBottomColor: theme.colors.border }]}
      accessible
      accessibilityLabel={accessibilityLabel}
    >
      {content}
    </View>
  );
}

const styles = StyleSheet.create({
  pressable: {
    borderBottomWidth: 1,
  },
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: spacing['3.5'],
    paddingHorizontal: spacing['1'],
    minHeight: touchTarget.medium,
  },
  iconContainer: {
    width: 40,
    height: 40,
    borderRadius: 20,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: spacing['3'],
  },
  details: {
    flex: 1,
    marginRight: spacing['3'],
  },
  type: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 4,
  },
  address: {
    fontSize: 14,
    fontFamily: 'monospace',
  },
  amountContainer: {
    alignItems: 'flex-end',
  },
  amount: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 4,
  },
  time: {
    fontSize: 12,
  },
  pendingBadge: {
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 4,
    marginTop: 4,
  },
  pendingText: {
    fontSize: 10,
    fontWeight: '600',
  },
  chevron: {
    marginLeft: spacing['2'],
  },
});

export default TransactionItem;
