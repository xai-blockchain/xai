/**
 * XAI Card Component
 *
 * Versatile card component with variants, shadows, and accessibility.
 */

import React, { useRef, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ViewStyle,
  Pressable,
  Animated,
} from 'react-native';
import { useTheme } from '../theme';
import { useHaptics } from '../hooks/useHaptics';
import { spacing, borderRadius } from '../theme/spacing';

export type CardVariant = 'default' | 'elevated' | 'outlined' | 'filled';

interface CardProps {
  children: React.ReactNode;
  title?: string;
  subtitle?: string;
  style?: ViewStyle;
  contentStyle?: ViewStyle;
  onPress?: () => void;
  variant?: CardVariant;
  disabled?: boolean;
  // Header actions
  headerRight?: React.ReactNode;
  // Accessibility
  accessibilityLabel?: string;
  accessibilityHint?: string;
  testID?: string;
}

export function Card({
  children,
  title,
  subtitle,
  style,
  contentStyle,
  onPress,
  variant = 'default',
  disabled = false,
  headerRight,
  accessibilityLabel,
  accessibilityHint,
  testID,
}: CardProps) {
  const theme = useTheme();
  const haptics = useHaptics();
  const scaleValue = useRef(new Animated.Value(1)).current;

  // Press animation
  const handlePressIn = useCallback(() => {
    if (disabled || !onPress) return;

    Animated.spring(scaleValue, {
      toValue: 0.98,
      useNativeDriver: true,
      speed: 50,
      bounciness: 4,
    }).start();
  }, [scaleValue, disabled, onPress]);

  const handlePressOut = useCallback(() => {
    Animated.spring(scaleValue, {
      toValue: 1,
      useNativeDriver: true,
      speed: 50,
      bounciness: 4,
    }).start();
  }, [scaleValue]);

  const handlePress = useCallback(() => {
    if (disabled || !onPress) return;

    haptics.light();
    onPress();
  }, [disabled, onPress, haptics]);

  // Get variant styles
  const getVariantStyles = (): ViewStyle => {
    const { surface, surfaceElevated, border, background } = theme.colors;

    switch (variant) {
      case 'elevated':
        return {
          backgroundColor: surfaceElevated,
          borderWidth: 0,
          ...theme.shadows.md,
        };
      case 'outlined':
        return {
          backgroundColor: 'transparent',
          borderWidth: 1,
          borderColor: border,
        };
      case 'filled':
        return {
          backgroundColor: background,
          borderWidth: 1,
          borderColor: border,
        };
      default:
        return {
          backgroundColor: surface,
          borderWidth: 1,
          borderColor: border,
        };
    }
  };

  const cardStyle: ViewStyle = {
    ...styles.card,
    ...getVariantStyles(),
    ...(disabled && styles.disabled),
    ...style,
  };

  const content = (
    <>
      {/* Header */}
      {(title || subtitle || headerRight) && (
        <View style={styles.header}>
          <View style={styles.headerText}>
            {title && (
              <Text
                style={[styles.title, { color: theme.colors.textMuted }]}
                accessibilityRole="header"
              >
                {title}
              </Text>
            )}
            {subtitle && (
              <Text style={[styles.subtitle, { color: theme.colors.textDisabled }]}>
                {subtitle}
              </Text>
            )}
          </View>
          {headerRight && <View style={styles.headerRight}>{headerRight}</View>}
        </View>
      )}

      {/* Content */}
      <View style={[styles.content, contentStyle]}>{children}</View>
    </>
  );

  // Interactive card
  if (onPress) {
    return (
      <Animated.View style={{ transform: [{ scale: scaleValue }] }}>
        <Pressable
          style={cardStyle}
          onPress={handlePress}
          onPressIn={handlePressIn}
          onPressOut={handlePressOut}
          disabled={disabled}
          accessible
          accessibilityRole="button"
          accessibilityLabel={accessibilityLabel || title}
          accessibilityHint={accessibilityHint}
          accessibilityState={{ disabled }}
          testID={testID}
        >
          {content}
        </Pressable>
      </Animated.View>
    );
  }

  // Static card
  return (
    <View
      style={cardStyle}
      accessible={!!accessibilityLabel}
      accessibilityLabel={accessibilityLabel}
      testID={testID}
    >
      {content}
    </View>
  );
}

// Specialized card variants
export function BalanceCard({
  balance,
  symbol = 'XAI',
  label = 'Total Balance',
  style,
  children,
}: {
  balance: string;
  symbol?: string;
  label?: string;
  style?: ViewStyle;
  children?: React.ReactNode;
}) {
  const theme = useTheme();

  return (
    <Card variant="elevated" style={[styles.balanceCard, style]}>
      <Text style={[styles.balanceLabel, { color: theme.colors.textMuted }]}>
        {label}
      </Text>
      <Text
        style={[styles.balanceAmount, { color: theme.colors.text }]}
        accessibilityLabel={`${balance} ${symbol}`}
      >
        {balance}
        <Text style={[styles.balanceSymbol, { color: theme.colors.textMuted }]}>
          {' '}{symbol}
        </Text>
      </Text>
      {children}
    </Card>
  );
}

export function StatCard({
  label,
  value,
  trend,
  style,
}: {
  label: string;
  value: string;
  trend?: 'up' | 'down' | 'neutral';
  style?: ViewStyle;
}) {
  const theme = useTheme();

  const getTrendColor = () => {
    switch (trend) {
      case 'up':
        return theme.colors.semantic.success;
      case 'down':
        return theme.colors.semantic.error;
      default:
        return theme.colors.text;
    }
  };

  return (
    <Card style={[styles.statCard, style]}>
      <Text
        style={[styles.statValue, { color: getTrendColor() }]}
        accessibilityLabel={`${label}: ${value}`}
      >
        {value}
      </Text>
      <Text style={[styles.statLabel, { color: theme.colors.textMuted }]}>
        {label}
      </Text>
    </Card>
  );
}

const styles = StyleSheet.create({
  card: {
    borderRadius: borderRadius.xl,
    marginBottom: spacing['3'],
    overflow: 'hidden',
  },
  disabled: {
    opacity: 0.5,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: spacing['4'],
    paddingTop: spacing['4'],
    paddingBottom: spacing['2'],
  },
  headerText: {
    flex: 1,
  },
  headerRight: {
    marginLeft: spacing['3'],
  },
  title: {
    fontSize: 14,
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  subtitle: {
    fontSize: 12,
    marginTop: 2,
  },
  content: {
    padding: spacing['4'],
    paddingTop: spacing['2'],
  },
  // Balance card
  balanceCard: {
    alignItems: 'center',
    paddingVertical: spacing['6'],
  },
  balanceLabel: {
    fontSize: 14,
    marginBottom: spacing['2'],
  },
  balanceAmount: {
    fontSize: 36,
    fontWeight: '700',
  },
  balanceSymbol: {
    fontSize: 20,
    fontWeight: '500',
  },
  // Stat card
  statCard: {
    alignItems: 'center',
    padding: spacing['3'],
  },
  statValue: {
    fontSize: 18,
    fontWeight: '700',
    marginBottom: spacing['1'],
  },
  statLabel: {
    fontSize: 12,
  },
});

export default Card;
