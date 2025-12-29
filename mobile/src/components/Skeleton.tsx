/**
 * Skeleton Loader Component
 *
 * Animated placeholder for loading states.
 * Respects reduce motion preferences.
 */

import React, { useEffect, useRef } from 'react';
import {
  View,
  StyleSheet,
  Animated,
  ViewStyle,
  Easing,
} from 'react-native';
import { useTheme } from '../theme';
import { useReduceMotion } from '../hooks/useAnimation';
import { borderRadius, spacing } from '../theme/spacing';

interface SkeletonProps {
  width?: number | string;
  height?: number;
  borderRadius?: number;
  style?: ViewStyle;
  variant?: 'text' | 'circular' | 'rectangular' | 'rounded';
}

export function Skeleton({
  width = '100%',
  height = 20,
  borderRadius: customRadius,
  style,
  variant = 'rounded',
}: SkeletonProps) {
  const theme = useTheme();
  const reduceMotion = useReduceMotion();
  const opacity = useRef(new Animated.Value(0.3)).current;

  useEffect(() => {
    if (reduceMotion) {
      opacity.setValue(0.5);
      return;
    }

    const animation = Animated.loop(
      Animated.sequence([
        Animated.timing(opacity, {
          toValue: 0.6,
          duration: 800,
          easing: Easing.inOut(Easing.ease),
          useNativeDriver: true,
        }),
        Animated.timing(opacity, {
          toValue: 0.3,
          duration: 800,
          easing: Easing.inOut(Easing.ease),
          useNativeDriver: true,
        }),
      ])
    );

    animation.start();

    return () => animation.stop();
  }, [reduceMotion, opacity]);

  // Calculate border radius based on variant
  const getRadius = () => {
    if (customRadius !== undefined) return customRadius;

    switch (variant) {
      case 'circular':
        return height / 2;
      case 'rectangular':
        return 0;
      case 'text':
        return 4;
      case 'rounded':
      default:
        return borderRadius.md;
    }
  };

  return (
    <Animated.View
      style={[
        styles.skeleton,
        {
          width,
          height,
          borderRadius: getRadius(),
          backgroundColor: theme.colors.surfaceOverlay,
          opacity,
        },
        style,
      ]}
      accessibilityRole="none"
      importantForAccessibility="no"
    />
  );
}

// Common skeleton patterns
export function SkeletonText({
  lines = 3,
  lineHeight = 16,
  gap = 8,
  style,
}: {
  lines?: number;
  lineHeight?: number;
  gap?: number;
  style?: ViewStyle;
}) {
  return (
    <View style={[styles.textContainer, style]}>
      {Array.from({ length: lines }).map((_, index) => (
        <Skeleton
          key={index}
          height={lineHeight}
          width={index === lines - 1 ? '75%' : '100%'}
          variant="text"
          style={{ marginBottom: index < lines - 1 ? gap : 0 }}
        />
      ))}
    </View>
  );
}

export function SkeletonCard({ style }: { style?: ViewStyle }) {
  const theme = useTheme();

  return (
    <View
      style={[
        styles.card,
        {
          backgroundColor: theme.colors.surface,
          borderColor: theme.colors.border,
        },
        style,
      ]}
    >
      <View style={styles.cardHeader}>
        <Skeleton
          width={40}
          height={40}
          variant="circular"
        />
        <View style={styles.cardHeaderText}>
          <Skeleton width={120} height={16} variant="text" />
          <Skeleton width={80} height={12} variant="text" style={{ marginTop: 8 }} />
        </View>
      </View>
      <SkeletonText lines={2} style={{ marginTop: 16 }} />
    </View>
  );
}

export function SkeletonTransaction({ style }: { style?: ViewStyle }) {
  return (
    <View style={[styles.transaction, style]}>
      <Skeleton width={40} height={40} variant="circular" />
      <View style={styles.transactionContent}>
        <Skeleton width={80} height={16} variant="text" />
        <Skeleton width={120} height={12} variant="text" style={{ marginTop: 6 }} />
      </View>
      <View style={styles.transactionRight}>
        <Skeleton width={60} height={16} variant="text" />
        <Skeleton width={40} height={12} variant="text" style={{ marginTop: 6 }} />
      </View>
    </View>
  );
}

export function SkeletonBalance({ style }: { style?: ViewStyle }) {
  return (
    <View style={[styles.balance, style]}>
      <Skeleton width={100} height={14} variant="text" />
      <Skeleton width={180} height={36} variant="rounded" style={{ marginTop: 8 }} />
      <Skeleton width={140} height={14} variant="text" style={{ marginTop: 8 }} />
    </View>
  );
}

export function SkeletonBlock({ style }: { style?: ViewStyle }) {
  const theme = useTheme();

  return (
    <View
      style={[
        styles.block,
        {
          backgroundColor: theme.colors.surface,
          borderColor: theme.colors.border,
        },
        style,
      ]}
    >
      <View style={styles.blockHeader}>
        <Skeleton width={60} height={24} variant="rounded" />
        <Skeleton width={80} height={12} variant="text" />
      </View>
      <View style={styles.blockContent}>
        <View style={styles.blockRow}>
          <Skeleton width={40} height={12} variant="text" />
          <Skeleton width={100} height={12} variant="text" />
        </View>
        <View style={styles.blockRow}>
          <Skeleton width={80} height={12} variant="text" />
          <Skeleton width={30} height={12} variant="text" />
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  skeleton: {
    overflow: 'hidden',
  },
  textContainer: {
    width: '100%',
  },
  card: {
    padding: spacing['4'],
    borderRadius: borderRadius.xl,
    borderWidth: 1,
    marginBottom: spacing['3'],
  },
  cardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  cardHeaderText: {
    marginLeft: spacing['3'],
    flex: 1,
  },
  transaction: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: spacing['3.5'],
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255,255,255,0.1)',
  },
  transactionContent: {
    flex: 1,
    marginLeft: spacing['3'],
  },
  transactionRight: {
    alignItems: 'flex-end',
  },
  balance: {
    alignItems: 'center',
    paddingVertical: spacing['6'],
  },
  block: {
    padding: spacing['3.5'],
    borderRadius: borderRadius.lg,
    borderWidth: 1,
    marginBottom: spacing['2.5'],
  },
  blockHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing['3'],
  },
  blockContent: {
    gap: spacing['2'],
  },
  blockRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
});

export default Skeleton;
