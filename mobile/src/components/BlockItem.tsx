/**
 * Block List Item Component
 *
 * Displays block information with hash, transactions, and accessibility support.
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
import { Block } from '../types';
import { formatRelativeTime, formatHash } from '../utils/format';
import { spacing, borderRadius, touchTarget } from '../theme/spacing';

interface BlockItemProps {
  block: Block;
  onPress?: () => void;
  compact?: boolean;
}

export function BlockItem({ block, onPress, compact = false }: BlockItemProps) {
  const theme = useTheme();
  const haptics = useHaptics();
  const scaleValue = useRef(new Animated.Value(1)).current;

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

  // Accessibility label
  const accessibilityLabel = `Block number ${block.index}, ${
    block.transactions.length
  } transactions, mined ${formatRelativeTime(block.timestamp)}`;

  const content = (
    <>
      {/* Header */}
      <View style={styles.header}>
        <View
          style={[
            styles.blockNumber,
            { backgroundColor: theme.colors.brand.primaryMuted },
          ]}
        >
          <Icon
            name="block"
            size={14}
            color={theme.colors.brand.primary}
            style={styles.blockIcon}
          />
          <Text
            style={[styles.blockNumberText, { color: theme.colors.brand.primary }]}
          >
            #{block.index.toLocaleString()}
          </Text>
        </View>
        <Text style={[styles.time, { color: theme.colors.textMuted }]}>
          {formatRelativeTime(block.timestamp)}
        </Text>
      </View>

      {/* Details */}
      {!compact && (
        <View style={styles.details}>
          <View style={styles.row}>
            <Text style={[styles.label, { color: theme.colors.textMuted }]}>
              Hash
            </Text>
            <Text
              style={[styles.value, { color: theme.colors.text }]}
              numberOfLines={1}
            >
              {formatHash(block.hash, 10)}
            </Text>
          </View>
          <View style={styles.row}>
            <Text style={[styles.label, { color: theme.colors.textMuted }]}>
              Transactions
            </Text>
            <View style={styles.txCountContainer}>
              <Text style={[styles.value, { color: theme.colors.text }]}>
                {block.transactions.length}
              </Text>
              <Icon
                name="transaction"
                size={12}
                color={theme.colors.textMuted}
                style={styles.txIcon}
              />
            </View>
          </View>
          {block.miner && (
            <View style={styles.row}>
              <Text style={[styles.label, { color: theme.colors.textMuted }]}>
                Miner
              </Text>
              <Text
                style={[styles.value, { color: theme.colors.text }]}
                numberOfLines={1}
              >
                {formatHash(block.miner, 8)}
              </Text>
            </View>
          )}
        </View>
      )}

      {/* Compact mode: single row */}
      {compact && (
        <View style={styles.compactRow}>
          <Text style={[styles.compactHash, { color: theme.colors.textMuted }]}>
            {formatHash(block.hash, 12)}
          </Text>
          <View style={styles.compactTxCount}>
            <Icon
              name="transaction"
              size={12}
              color={theme.colors.textMuted}
            />
            <Text style={[styles.compactTxText, { color: theme.colors.text }]}>
              {block.transactions.length}
            </Text>
          </View>
        </View>
      )}

      {/* Press indicator */}
      {onPress && (
        <View style={styles.pressIndicator}>
          <Icon
            name="chevron-right"
            size={16}
            color={theme.colors.textMuted}
          />
        </View>
      )}
    </>
  );

  const containerStyle = [
    styles.container,
    {
      backgroundColor: theme.colors.surface,
      borderColor: theme.colors.border,
    },
    compact && styles.containerCompact,
  ];

  if (onPress) {
    return (
      <Animated.View style={{ transform: [{ scale: scaleValue }] }}>
        <Pressable
          style={containerStyle}
          onPress={handlePress}
          onPressIn={handlePressIn}
          onPressOut={handlePressOut}
          accessible
          accessibilityRole="button"
          accessibilityLabel={accessibilityLabel}
          accessibilityHint="Double tap to view block details"
        >
          {content}
        </Pressable>
      </Animated.View>
    );
  }

  return (
    <View style={containerStyle} accessible accessibilityLabel={accessibilityLabel}>
      {content}
    </View>
  );
}

// Summary card for latest block
export function LatestBlockCard({ block, onPress }: BlockItemProps) {
  const theme = useTheme();

  return (
    <Pressable
      style={[
        styles.latestBlockCard,
        {
          backgroundColor: theme.colors.surface,
          borderColor: theme.colors.border,
        },
      ]}
      onPress={onPress}
      accessible
      accessibilityRole="button"
      accessibilityLabel={`Latest block: ${block.index}`}
    >
      <View style={styles.latestBlockHeader}>
        <Icon name="block" size={20} color={theme.colors.brand.primary} />
        <Text style={[styles.latestBlockTitle, { color: theme.colors.text }]}>
          Latest Block
        </Text>
      </View>
      <Text style={[styles.latestBlockNumber, { color: theme.colors.brand.primary }]}>
        #{block.index.toLocaleString()}
      </Text>
      <Text style={[styles.latestBlockTime, { color: theme.colors.textMuted }]}>
        {formatRelativeTime(block.timestamp)}
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  container: {
    borderRadius: borderRadius.lg,
    padding: spacing['3.5'],
    marginBottom: spacing['2.5'],
    borderWidth: 1,
  },
  containerCompact: {
    padding: spacing['3'],
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing['3'],
  },
  blockNumber: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: spacing['3'],
    paddingVertical: spacing['1'],
    borderRadius: borderRadius.md,
  },
  blockIcon: {
    marginRight: spacing['1.5'],
  },
  blockNumberText: {
    fontSize: 14,
    fontWeight: '700',
  },
  time: {
    fontSize: 12,
  },
  details: {
    gap: spacing['2'],
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  label: {
    fontSize: 13,
  },
  value: {
    fontSize: 13,
    fontFamily: 'monospace',
  },
  txCountContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  txIcon: {
    marginLeft: spacing['1.5'],
  },
  // Compact mode
  compactRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: -spacing['1'],
  },
  compactHash: {
    fontSize: 12,
    fontFamily: 'monospace',
  },
  compactTxCount: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  compactTxText: {
    fontSize: 12,
    marginLeft: spacing['1'],
    fontWeight: '600',
  },
  pressIndicator: {
    position: 'absolute',
    right: spacing['3'],
    top: '50%',
    marginTop: -8,
  },
  // Latest block card
  latestBlockCard: {
    borderRadius: borderRadius.xl,
    padding: spacing['4'],
    borderWidth: 1,
    alignItems: 'center',
  },
  latestBlockHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: spacing['2'],
  },
  latestBlockTitle: {
    fontSize: 14,
    fontWeight: '500',
    marginLeft: spacing['2'],
  },
  latestBlockNumber: {
    fontSize: 28,
    fontWeight: '700',
    marginBottom: spacing['1'],
  },
  latestBlockTime: {
    fontSize: 12,
  },
});

export default BlockItem;
