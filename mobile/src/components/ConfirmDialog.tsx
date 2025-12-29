/**
 * Confirmation Dialog Component
 *
 * Modal dialog for confirming destructive actions.
 * Supports haptic feedback and accessibility.
 */

import React, { useCallback, useRef, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  Modal,
  Pressable,
  Animated,
  BackHandler,
  Platform,
} from 'react-native';
import { useTheme } from '../theme';
import { Button } from './Button';
import { useHaptics } from '../hooks/useHaptics';
import { useFadeAnimation, useSlideAnimation } from '../hooks/useAnimation';
import { spacing, borderRadius } from '../theme/spacing';

export type DialogVariant = 'confirm' | 'danger' | 'warning' | 'info';

interface ConfirmDialogProps {
  visible: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: DialogVariant;
  onConfirm: () => void;
  onCancel: () => void;
  loading?: boolean;
  // Additional details (e.g., transaction summary)
  details?: Array<{ label: string; value: string }>;
  // Icon component
  icon?: React.ReactNode;
}

export function ConfirmDialog({
  visible,
  title,
  message,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  variant = 'confirm',
  onConfirm,
  onCancel,
  loading = false,
  details,
  icon,
}: ConfirmDialogProps) {
  const theme = useTheme();
  const haptics = useHaptics();
  const { opacity: backdropOpacity, fadeIn, fadeOut } = useFadeAnimation(0, 200);
  const { transform, opacity: contentOpacity, slideIn, slideOut } = useSlideAnimation('y', 30);

  // Handle animations on visibility change
  useEffect(() => {
    if (visible) {
      fadeIn();
      slideIn();
      // Haptic for dialog appearance
      if (variant === 'danger') {
        haptics.warning();
      }
    }
  }, [visible, fadeIn, slideIn, haptics, variant]);

  // Handle Android back button
  useEffect(() => {
    if (!visible) return;

    const backHandler = BackHandler.addEventListener('hardwareBackPress', () => {
      if (!loading) {
        onCancel();
      }
      return true;
    });

    return () => backHandler.remove();
  }, [visible, loading, onCancel]);

  const handleConfirm = useCallback(() => {
    if (loading) return;

    if (variant === 'danger') {
      haptics.heavy();
    } else {
      haptics.medium();
    }
    onConfirm();
  }, [loading, variant, haptics, onConfirm]);

  const handleCancel = useCallback(() => {
    if (loading) return;
    
    haptics.light();
    fadeOut();
    slideOut(() => {
      onCancel();
    });
  }, [loading, haptics, fadeOut, slideOut, onCancel]);

  // Get variant colors
  const getVariantColor = () => {
    switch (variant) {
      case 'danger':
        return theme.colors.semantic.error;
      case 'warning':
        return theme.colors.semantic.warning;
      case 'info':
        return theme.colors.semantic.info;
      default:
        return theme.colors.brand.primary;
    }
  };

  const variantColor = getVariantColor();

  if (!visible) return null;

  return (
    <Modal
      visible={visible}
      transparent
      animationType="none"
      statusBarTranslucent
      onRequestClose={handleCancel}
    >
      {/* Backdrop */}
      <Animated.View
        style={[
          styles.backdrop,
          { opacity: backdropOpacity },
        ]}
      >
        <Pressable
          style={StyleSheet.absoluteFill}
          onPress={handleCancel}
          disabled={loading}
          accessibilityRole="button"
          accessibilityLabel="Close dialog"
        />
      </Animated.View>

      {/* Dialog content */}
      <View style={styles.container}>
        <Animated.View
          style={[
            styles.dialog,
            { backgroundColor: theme.colors.surface },
            { transform },
            { opacity: contentOpacity },
          ]}
          accessibilityViewIsModal
          accessibilityRole="alertdialog"
          accessibilityLabel={title}
        >
          {/* Accent line at top */}
          <View
            style={[styles.accentLine, { backgroundColor: variantColor }]}
          />

          {/* Icon */}
          {icon && (
            <View style={styles.iconContainer}>
              {icon}
            </View>
          )}

          {/* Title */}
          <Text
            style={[styles.title, { color: theme.colors.text }]}
            accessibilityRole="header"
          >
            {title}
          </Text>

          {/* Message */}
          <Text style={[styles.message, { color: theme.colors.textMuted }]}>
            {message}
          </Text>

          {/* Details section */}
          {details && details.length > 0 && (
            <View
              style={[
                styles.detailsContainer,
                { backgroundColor: theme.colors.background },
              ]}
            >
              {details.map((detail, index) => (
                <View
                  key={index}
                  style={[
                    styles.detailRow,
                    index < details.length - 1 && {
                      borderBottomWidth: 1,
                      borderBottomColor: theme.colors.border,
                    },
                  ]}
                >
                  <Text style={[styles.detailLabel, { color: theme.colors.textMuted }]}>
                    {detail.label}
                  </Text>
                  <Text style={[styles.detailValue, { color: theme.colors.text }]}>
                    {detail.value}
                  </Text>
                </View>
              ))}
            </View>
          )}

          {/* Action buttons */}
          <View style={styles.actions}>
            <Button
              title={cancelLabel}
              onPress={handleCancel}
              variant="secondary"
              disabled={loading}
              style={styles.cancelButton}
              accessibilityLabel={cancelLabel}
            />
            <Button
              title={confirmLabel}
              onPress={handleConfirm}
              variant={variant === 'danger' ? 'danger' : 'primary'}
              loading={loading}
              style={styles.confirmButton}
              accessibilityLabel={confirmLabel}
            />
          </View>
        </Animated.View>
      </View>
    </Modal>
  );
}

// Pre-configured dialogs for common use cases
export function DeleteWalletDialog({
  visible,
  onConfirm,
  onCancel,
  loading,
}: {
  visible: boolean;
  onConfirm: () => void;
  onCancel: () => void;
  loading?: boolean;
}) {
  return (
    <ConfirmDialog
      visible={visible}
      title="Delete Wallet?"
      message="This will permanently remove your wallet from this device. Make sure you have backed up your private key. This action cannot be undone."
      confirmLabel="Delete Wallet"
      cancelLabel="Keep Wallet"
      variant="danger"
      onConfirm={onConfirm}
      onCancel={onCancel}
      loading={loading}
    />
  );
}

export function SendTransactionDialog({
  visible,
  recipient,
  amount,
  fee,
  total,
  onConfirm,
  onCancel,
  loading,
}: {
  visible: boolean;
  recipient: string;
  amount: string;
  fee: string;
  total: string;
  onConfirm: () => void;
  onCancel: () => void;
  loading?: boolean;
}) {
  return (
    <ConfirmDialog
      visible={visible}
      title="Confirm Transaction"
      message="Please review the transaction details before sending."
      confirmLabel="Send"
      cancelLabel="Cancel"
      variant="confirm"
      onConfirm={onConfirm}
      onCancel={onCancel}
      loading={loading}
      details={[
        { label: 'To', value: recipient },
        { label: 'Amount', value: amount },
        { label: 'Network Fee', value: fee },
        { label: 'Total', value: total },
      ]}
    />
  );
}

export function ExportKeyDialog({
  visible,
  onConfirm,
  onCancel,
}: {
  visible: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <ConfirmDialog
      visible={visible}
      title="Export Private Key"
      message="Your private key gives full access to your wallet. Never share it with anyone. Anyone with your private key can steal your funds."
      confirmLabel="Show Private Key"
      cancelLabel="Cancel"
      variant="warning"
      onConfirm={onConfirm}
      onCancel={onCancel}
    />
  );
}

const styles = StyleSheet.create({
  backdrop: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
  },
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: spacing['6'],
  },
  dialog: {
    width: '100%',
    maxWidth: 340,
    borderRadius: borderRadius['2xl'],
    overflow: 'hidden',
    paddingTop: spacing['6'],
    paddingHorizontal: spacing['5'],
    paddingBottom: spacing['5'],
  },
  accentLine: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    height: 4,
  },
  iconContainer: {
    alignItems: 'center',
    marginBottom: spacing['4'],
  },
  title: {
    fontSize: 20,
    fontWeight: '700',
    textAlign: 'center',
    marginBottom: spacing['2'],
  },
  message: {
    fontSize: 14,
    textAlign: 'center',
    lineHeight: 22,
    marginBottom: spacing['5'],
  },
  detailsContainer: {
    borderRadius: borderRadius.lg,
    marginBottom: spacing['5'],
    overflow: 'hidden',
  },
  detailRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: spacing['3'],
    paddingHorizontal: spacing['3'],
  },
  detailLabel: {
    fontSize: 13,
    fontWeight: '500',
  },
  detailValue: {
    fontSize: 13,
    fontWeight: '600',
    fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace',
    maxWidth: '60%',
    textAlign: 'right',
  },
  actions: {
    flexDirection: 'row',
    gap: spacing['3'],
  },
  cancelButton: {
    flex: 1,
  },
  confirmButton: {
    flex: 1,
  },
});

export default ConfirmDialog;
