/**
 * Empty State Component
 *
 * Displays helpful messages when there's no data.
 * Supports icons, actions, and accessibility.
 */

import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  ViewStyle,
} from 'react-native';
import { useTheme } from '../theme';
import { Button } from './Button';
import { spacing, borderRadius } from '../theme/spacing';

// Common empty state types
export type EmptyStateType =
  | 'no-wallet'
  | 'no-transactions'
  | 'no-blocks'
  | 'no-results'
  | 'connection-error'
  | 'empty-search'
  | 'generic';

interface EmptyStateProps {
  type?: EmptyStateType;
  title?: string;
  message?: string;
  icon?: React.ReactNode;
  actionLabel?: string;
  onAction?: () => void;
  secondaryActionLabel?: string;
  onSecondaryAction?: () => void;
  style?: ViewStyle;
  compact?: boolean;
}

// Preset content for common empty states
const presets: Record<EmptyStateType, { title: string; message: string; icon: string }> = {
  'no-wallet': {
    title: 'No Wallet Yet',
    message: 'Create a new wallet or import an existing one to get started with XAI.',
    icon: '',
  },
  'no-transactions': {
    title: 'No Transactions',
    message: 'Your transaction history will appear here once you send or receive XAI.',
    icon: '',
  },
  'no-blocks': {
    title: 'No Blocks Found',
    message: 'Block data is currently unavailable. Pull down to refresh.',
    icon: '',
  },
  'no-results': {
    title: 'No Results',
    message: 'We couldn\'t find what you\'re looking for. Try a different search.',
    icon: '',
  },
  'connection-error': {
    title: 'Connection Error',
    message: 'Unable to connect to the XAI network. Please check your connection and try again.',
    icon: '',
  },
  'empty-search': {
    title: 'Search XAI',
    message: 'Enter a block number, transaction ID, or address to search the blockchain.',
    icon: '',
  },
  'generic': {
    title: 'Nothing Here',
    message: 'There\'s nothing to display at the moment.',
    icon: '',
  },
};

export function EmptyState({
  type = 'generic',
  title: customTitle,
  message: customMessage,
  icon,
  actionLabel,
  onAction,
  secondaryActionLabel,
  onSecondaryAction,
  style,
  compact = false,
}: EmptyStateProps) {
  const theme = useTheme();
  const preset = presets[type];

  const title = customTitle || preset.title;
  const message = customMessage || preset.message;

  return (
    <View
      style={[
        styles.container,
        compact && styles.compact,
        style,
      ]}
      accessible
      accessibilityRole="alert"
      accessibilityLabel={`${title}. ${message}`}
    >
      {/* Icon placeholder */}
      {icon && (
        <View style={styles.iconContainer}>
          {icon}
        </View>
      )}

      {/* Empty state icon circles */}
      {!icon && (
        <View style={styles.illustrationContainer}>
          <View
            style={[
              styles.circle,
              styles.circleLarge,
              { backgroundColor: theme.colors.brand.primaryMuted },
            ]}
          />
          <View
            style={[
              styles.circle,
              styles.circleMedium,
              { backgroundColor: theme.colors.surfaceOverlay },
            ]}
          />
          <View
            style={[
              styles.circle,
              styles.circleSmall,
              { backgroundColor: theme.colors.brand.primary },
            ]}
          />
        </View>
      )}

      {/* Text content */}
      <Text
        style={[
          styles.title,
          compact && styles.titleCompact,
          { color: theme.colors.text },
        ]}
        accessibilityRole="header"
      >
        {title}
      </Text>

      <Text
        style={[
          styles.message,
          compact && styles.messageCompact,
          { color: theme.colors.textMuted },
        ]}
      >
        {message}
      </Text>

      {/* Action buttons */}
      {(actionLabel || secondaryActionLabel) && (
        <View style={styles.actions}>
          {actionLabel && onAction && (
            <Button
              title={actionLabel}
              onPress={onAction}
              size={compact ? 'small' : 'medium'}
              style={styles.actionButton}
            />
          )}
          {secondaryActionLabel && onSecondaryAction && (
            <Button
              title={secondaryActionLabel}
              onPress={onSecondaryAction}
              variant="outline"
              size={compact ? 'small' : 'medium'}
              style={styles.actionButton}
            />
          )}
        </View>
      )}
    </View>
  );
}

// Quick access empty state components
export function NoTransactionsEmpty({ onAction }: { onAction?: () => void }) {
  return (
    <EmptyState
      type="no-transactions"
      actionLabel={onAction ? 'Claim Test Tokens' : undefined}
      onAction={onAction}
    />
  );
}

export function NoWalletEmpty({ onAction }: { onAction?: () => void }) {
  return (
    <EmptyState
      type="no-wallet"
      actionLabel="Create Wallet"
      onAction={onAction}
    />
  );
}

export function ConnectionErrorEmpty({ onRetry }: { onRetry?: () => void }) {
  return (
    <EmptyState
      type="connection-error"
      actionLabel="Retry"
      onAction={onRetry}
    />
  );
}

export function SearchEmpty() {
  return <EmptyState type="empty-search" compact />;
}

export function NoResultsEmpty({
  query,
  onClear,
}: {
  query?: string;
  onClear?: () => void;
}) {
  return (
    <EmptyState
      type="no-results"
      message={
        query
          ? `No results found for "${query}". Try a different search term.`
          : 'No results found. Try a different search.'
      }
      actionLabel={onClear ? 'Clear Search' : undefined}
      onAction={onClear}
    />
  );
}

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: spacing['10'],
    paddingHorizontal: spacing['6'],
  },
  compact: {
    paddingVertical: spacing['6'],
  },
  iconContainer: {
    marginBottom: spacing['4'],
  },
  illustrationContainer: {
    position: 'relative',
    width: 80,
    height: 80,
    marginBottom: spacing['6'],
    alignItems: 'center',
    justifyContent: 'center',
  },
  circle: {
    position: 'absolute',
    borderRadius: 9999,
  },
  circleLarge: {
    width: 80,
    height: 80,
    opacity: 0.5,
  },
  circleMedium: {
    width: 50,
    height: 50,
    opacity: 0.8,
  },
  circleSmall: {
    width: 24,
    height: 24,
  },
  title: {
    fontSize: 20,
    fontWeight: '700',
    textAlign: 'center',
    marginBottom: spacing['2'],
  },
  titleCompact: {
    fontSize: 16,
  },
  message: {
    fontSize: 14,
    textAlign: 'center',
    lineHeight: 22,
    maxWidth: 280,
    marginBottom: spacing['6'],
  },
  messageCompact: {
    fontSize: 13,
    marginBottom: spacing['4'],
  },
  actions: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing['3'],
    justifyContent: 'center',
  },
  actionButton: {
    minWidth: 120,
  },
});

export default EmptyState;
