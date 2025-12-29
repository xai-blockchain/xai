/**
 * Status Badge Component
 *
 * Visual indicator for various status states with accessibility support.
 */

import React, { useEffect, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  Animated,
  Easing,
} from 'react-native';
import { useTheme } from '../theme';
import { useReduceMotion } from '../hooks/useAnimation';
import { spacing } from '../theme/spacing';

export type StatusType = 'success' | 'warning' | 'error' | 'info' | 'neutral' | 'pending';

interface StatusBadgeProps {
  status: StatusType;
  label: string;
  size?: 'small' | 'medium' | 'large';
  showDot?: boolean;
  animated?: boolean;
  // For live status updates
  pulsing?: boolean;
}

export function StatusBadge({
  status,
  label,
  size = 'medium',
  showDot = true,
  animated = false,
  pulsing = false,
}: StatusBadgeProps) {
  const theme = useTheme();
  const reduceMotion = useReduceMotion();
  const pulseAnim = useRef(new Animated.Value(1)).current;

  // Start pulse animation for live status
  useEffect(() => {
    if (!pulsing || reduceMotion) return;

    const animation = Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, {
          toValue: 0.4,
          duration: 800,
          easing: Easing.inOut(Easing.ease),
          useNativeDriver: true,
        }),
        Animated.timing(pulseAnim, {
          toValue: 1,
          duration: 800,
          easing: Easing.inOut(Easing.ease),
          useNativeDriver: true,
        }),
      ])
    );

    animation.start();

    return () => animation.stop();
  }, [pulsing, reduceMotion, pulseAnim]);

  // Get colors based on status
  const getStatusColors = () => {
    const { semantic } = theme.colors;

    const colors: Record<StatusType, { bg: string; dot: string; text: string }> = {
      success: {
        bg: semantic.successMuted,
        dot: semantic.success,
        text: semantic.success,
      },
      warning: {
        bg: semantic.warningMuted,
        dot: semantic.warning,
        text: semantic.warning,
      },
      error: {
        bg: semantic.errorMuted,
        dot: semantic.error,
        text: semantic.error,
      },
      info: {
        bg: semantic.infoMuted,
        dot: semantic.info,
        text: semantic.info,
      },
      neutral: {
        bg: theme.colors.surfaceOverlay,
        dot: theme.colors.textMuted,
        text: theme.colors.textMuted,
      },
      pending: {
        bg: semantic.warningMuted,
        dot: semantic.warning,
        text: semantic.warning,
      },
    };

    return colors[status];
  };

  // Get size styles
  const getSizeStyles = () => {
    const sizes = {
      small: {
        paddingH: 8,
        paddingV: 3,
        fontSize: 11,
        dotSize: 5,
        gap: 5,
      },
      medium: {
        paddingH: 10,
        paddingV: 4,
        fontSize: 12,
        dotSize: 6,
        gap: 6,
      },
      large: {
        paddingH: 12,
        paddingV: 5,
        fontSize: 13,
        dotSize: 8,
        gap: 8,
      },
    };

    return sizes[size];
  };

  const statusColors = getStatusColors();
  const sizeStyles = getSizeStyles();

  // Accessibility label
  const accessibilityLabel = `Status: ${label}`;

  return (
    <View
      style={[
        styles.container,
        {
          backgroundColor: statusColors.bg,
          paddingHorizontal: sizeStyles.paddingH,
          paddingVertical: sizeStyles.paddingV,
          gap: sizeStyles.gap,
        },
      ]}
      accessible
      accessibilityRole="text"
      accessibilityLabel={accessibilityLabel}
      accessibilityLiveRegion={animated ? 'polite' : 'off'}
    >
      {showDot && (
        <Animated.View
          style={[
            styles.dot,
            {
              width: sizeStyles.dotSize,
              height: sizeStyles.dotSize,
              borderRadius: sizeStyles.dotSize / 2,
              backgroundColor: statusColors.dot,
              opacity: pulsing ? pulseAnim : 1,
            },
          ]}
        />
      )}
      <Text
        style={[
          styles.label,
          {
            fontSize: sizeStyles.fontSize,
            color: statusColors.text,
          },
        ]}
        numberOfLines={1}
      >
        {label}
      </Text>
    </View>
  );
}

// Connection status badge with auto-updating
export function ConnectionBadge({
  isConnected,
  size = 'medium',
}: {
  isConnected: boolean;
  size?: 'small' | 'medium' | 'large';
}) {
  return (
    <StatusBadge
      status={isConnected ? 'success' : 'error'}
      label={isConnected ? 'Connected' : 'Disconnected'}
      size={size}
      pulsing={isConnected}
      animated
    />
  );
}

// Transaction status badge
export function TransactionStatusBadge({
  status,
  confirmations,
  size = 'small',
}: {
  status: 'pending' | 'confirmed' | 'failed';
  confirmations?: number;
  size?: 'small' | 'medium' | 'large';
}) {
  const getStatusInfo = (): { type: StatusType; label: string } => {
    switch (status) {
      case 'pending':
        return { type: 'pending', label: 'Pending' };
      case 'confirmed':
        return {
          type: 'success',
          label: confirmations ? `${confirmations} confirmations` : 'Confirmed',
        };
      case 'failed':
        return { type: 'error', label: 'Failed' };
      default:
        return { type: 'neutral', label: 'Unknown' };
    }
  };

  const { type, label } = getStatusInfo();

  return (
    <StatusBadge
      status={type}
      label={label}
      size={size}
      pulsing={status === 'pending'}
    />
  );
}

// Network status badge with pressure indicator
export function NetworkPressureBadge({
  pressure,
  size = 'small',
}: {
  pressure: 'normal' | 'moderate' | 'elevated' | 'critical';
  size?: 'small' | 'medium' | 'large';
}) {
  const getPressureInfo = (): { type: StatusType; label: string } => {
    switch (pressure) {
      case 'normal':
        return { type: 'success', label: 'Normal' };
      case 'moderate':
        return { type: 'info', label: 'Moderate' };
      case 'elevated':
        return { type: 'warning', label: 'Elevated' };
      case 'critical':
        return { type: 'error', label: 'Critical' };
      default:
        return { type: 'neutral', label: 'Unknown' };
    }
  };

  const { type, label } = getPressureInfo();

  return (
    <StatusBadge
      status={type}
      label={label}
      size={size}
    />
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    borderRadius: 20,
    alignSelf: 'flex-start',
  },
  dot: {},
  label: {
    fontWeight: '600',
  },
});

export default StatusBadge;
