/**
 * Progress Indicator Components
 *
 * Various loading and progress indicators with animations.
 */

import React, { useEffect, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  Animated,
  Easing,
  ViewStyle,
} from 'react-native';
import { useTheme } from '../theme';
import { useReduceMotion } from '../hooks/useAnimation';
import { spacing, borderRadius } from '../theme/spacing';

// Spinning loader
interface SpinnerProps {
  size?: 'small' | 'medium' | 'large';
  color?: string;
  style?: ViewStyle;
}

export function Spinner({ size = 'medium', color, style }: SpinnerProps) {
  const theme = useTheme();
  const reduceMotion = useReduceMotion();
  const rotation = useRef(new Animated.Value(0)).current;

  const sizes = {
    small: 20,
    medium: 32,
    large: 48,
  };

  const strokeWidths = {
    small: 2,
    medium: 3,
    large: 4,
  };

  useEffect(() => {
    if (reduceMotion) return;

    const animation = Animated.loop(
      Animated.timing(rotation, {
        toValue: 1,
        duration: 1000,
        easing: Easing.linear,
        useNativeDriver: true,
      })
    );

    animation.start();

    return () => animation.stop();
  }, [reduceMotion, rotation]);

  const spin = rotation.interpolate({
    inputRange: [0, 1],
    outputRange: ['0deg', '360deg'],
  });

  const spinnerSize = sizes[size];
  const strokeWidth = strokeWidths[size];
  const spinnerColor = color || theme.colors.brand.primary;

  return (
    <Animated.View
      style={[
        styles.spinner,
        {
          width: spinnerSize,
          height: spinnerSize,
          borderRadius: spinnerSize / 2,
          borderWidth: strokeWidth,
          borderColor: theme.colors.surfaceOverlay,
          borderTopColor: spinnerColor,
          transform: [{ rotate: spin }],
        },
        style,
      ]}
      accessibilityRole="progressbar"
      accessibilityLabel="Loading"
    />
  );
}

// Pulsing dots loader
interface DotsLoaderProps {
  count?: number;
  color?: string;
  size?: number;
  style?: ViewStyle;
}

export function DotsLoader({ count = 3, color, size = 8, style }: DotsLoaderProps) {
  const theme = useTheme();
  const reduceMotion = useReduceMotion();
  const animations = useRef(
    Array.from({ length: count }, () => new Animated.Value(0.3))
  ).current;

  useEffect(() => {
    if (reduceMotion) {
      animations.forEach((anim) => anim.setValue(1));
      return;
    }

    const animateDots = () => {
      const sequence = animations.map((anim, index) =>
        Animated.sequence([
          Animated.delay(index * 150),
          Animated.timing(anim, {
            toValue: 1,
            duration: 300,
            easing: Easing.inOut(Easing.ease),
            useNativeDriver: true,
          }),
          Animated.timing(anim, {
            toValue: 0.3,
            duration: 300,
            easing: Easing.inOut(Easing.ease),
            useNativeDriver: true,
          }),
        ])
      );

      Animated.loop(Animated.stagger(100, sequence)).start();
    };

    animateDots();

    return () => {
      animations.forEach((anim) => anim.stopAnimation());
    };
  }, [reduceMotion, animations]);

  const dotColor = color || theme.colors.brand.primary;

  return (
    <View style={[styles.dotsContainer, style]} accessibilityLabel="Loading">
      {animations.map((anim, index) => (
        <Animated.View
          key={index}
          style={[
            styles.dot,
            {
              width: size,
              height: size,
              borderRadius: size / 2,
              backgroundColor: dotColor,
              opacity: anim,
              transform: [
                {
                  scale: anim.interpolate({
                    inputRange: [0.3, 1],
                    outputRange: [0.8, 1],
                  }),
                },
              ],
            },
          ]}
        />
      ))}
    </View>
  );
}

// Linear progress bar
interface ProgressBarProps {
  progress: number; // 0-100
  color?: string;
  height?: number;
  animated?: boolean;
  showLabel?: boolean;
  style?: ViewStyle;
}

export function ProgressBar({
  progress,
  color,
  height = 6,
  animated = true,
  showLabel = false,
  style,
}: ProgressBarProps) {
  const theme = useTheme();
  const reduceMotion = useReduceMotion();
  const width = useRef(new Animated.Value(0)).current;

  const clampedProgress = Math.max(0, Math.min(100, progress));
  const barColor = color || theme.colors.brand.primary;

  useEffect(() => {
    if (reduceMotion || !animated) {
      width.setValue(clampedProgress);
      return;
    }

    Animated.timing(width, {
      toValue: clampedProgress,
      duration: 300,
      easing: Easing.out(Easing.ease),
      useNativeDriver: false,
    }).start();
  }, [clampedProgress, reduceMotion, animated, width]);

  const widthPercent = width.interpolate({
    inputRange: [0, 100],
    outputRange: ['0%', '100%'],
  });

  return (
    <View style={style}>
      {showLabel && (
        <Text
          style={[styles.progressLabel, { color: theme.colors.textMuted }]}
          accessibilityLabel={`${Math.round(clampedProgress)}% complete`}
        >
          {Math.round(clampedProgress)}%
        </Text>
      )}
      <View
        style={[
          styles.progressTrack,
          { height, backgroundColor: theme.colors.surfaceOverlay },
        ]}
        accessibilityRole="progressbar"
        accessibilityValue={{ now: clampedProgress, min: 0, max: 100 }}
      >
        <Animated.View
          style={[
            styles.progressFill,
            { height, backgroundColor: barColor, width: widthPercent },
          ]}
        />
      </View>
    </View>
  );
}

// Step progress indicator
interface StepProgressProps {
  currentStep: number;
  totalSteps: number;
  labels?: string[];
  style?: ViewStyle;
}

export function StepProgress({ currentStep, totalSteps, labels, style }: StepProgressProps) {
  const theme = useTheme();

  return (
    <View style={[styles.stepContainer, style]}>
      {Array.from({ length: totalSteps }).map((_, index) => {
        const isCompleted = index < currentStep;
        const isCurrent = index === currentStep;

        return (
          <React.Fragment key={index}>
            {/* Step circle */}
            <View style={styles.stepWrapper}>
              <View
                style={[
                  styles.stepCircle,
                  {
                    backgroundColor: isCompleted || isCurrent
                      ? theme.colors.brand.primary
                      : theme.colors.surfaceOverlay,
                    borderColor: isCurrent
                      ? theme.colors.brand.primaryLight
                      : 'transparent',
                    borderWidth: isCurrent ? 2 : 0,
                  },
                ]}
                accessibilityRole="progressbar"
                accessibilityLabel={
                  labels?.[index]
                    ? `Step ${index + 1}: ${labels[index]}, ${
                        isCompleted ? 'completed' : isCurrent ? 'current' : 'pending'
                      }`
                    : `Step ${index + 1} of ${totalSteps}`
                }
              >
                {isCompleted && (
                  <Text style={styles.stepCheck}>-</Text>
                )}
                {!isCompleted && (
                  <Text
                    style={[
                      styles.stepNumber,
                      {
                        color: isCurrent
                          ? '#ffffff'
                          : theme.colors.textDisabled,
                      },
                    ]}
                  >
                    {index + 1}
                  </Text>
                )}
              </View>
              {labels?.[index] && (
                <Text
                  style={[
                    styles.stepLabel,
                    {
                      color: isCurrent || isCompleted
                        ? theme.colors.text
                        : theme.colors.textMuted,
                    },
                  ]}
                  numberOfLines={1}
                >
                  {labels[index]}
                </Text>
              )}
            </View>

            {/* Connector line */}
            {index < totalSteps - 1 && (
              <View
                style={[
                  styles.stepConnector,
                  {
                    backgroundColor: isCompleted
                      ? theme.colors.brand.primary
                      : theme.colors.surfaceOverlay,
                  },
                ]}
              />
            )}
          </React.Fragment>
        );
      })}
    </View>
  );
}

// Full screen loading overlay
interface LoadingOverlayProps {
  visible: boolean;
  message?: string;
  transparent?: boolean;
}

export function LoadingOverlay({ visible, message, transparent = false }: LoadingOverlayProps) {
  const theme = useTheme();
  const opacity = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(opacity, {
      toValue: visible ? 1 : 0,
      duration: 200,
      useNativeDriver: true,
    }).start();
  }, [visible, opacity]);

  if (!visible) return null;

  return (
    <Animated.View
      style={[
        styles.overlay,
        {
          opacity,
          backgroundColor: transparent
            ? 'rgba(0, 0, 0, 0.5)'
            : theme.colors.background,
        },
      ]}
    >
      <View
        style={[
          styles.overlayContent,
          { backgroundColor: theme.colors.surface },
        ]}
      >
        <Spinner size="large" />
        {message && (
          <Text style={[styles.overlayMessage, { color: theme.colors.textMuted }]}>
            {message}
          </Text>
        )}
      </View>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  spinner: {
    alignSelf: 'center',
  },
  dotsContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
  },
  dot: {},
  progressTrack: {
    borderRadius: 100,
    overflow: 'hidden',
    width: '100%',
  },
  progressFill: {
    borderRadius: 100,
  },
  progressLabel: {
    fontSize: 12,
    fontWeight: '600',
    marginBottom: 4,
    textAlign: 'right',
  },
  stepContainer: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
  },
  stepWrapper: {
    alignItems: 'center',
    flex: 0,
  },
  stepCircle: {
    width: 32,
    height: 32,
    borderRadius: 16,
    alignItems: 'center',
    justifyContent: 'center',
  },
  stepNumber: {
    fontSize: 14,
    fontWeight: '600',
  },
  stepCheck: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '700',
  },
  stepLabel: {
    fontSize: 11,
    fontWeight: '500',
    marginTop: 6,
    maxWidth: 80,
    textAlign: 'center',
  },
  stepConnector: {
    flex: 1,
    height: 2,
    marginTop: 15,
    marginHorizontal: 8,
  },
  overlay: {
    ...StyleSheet.absoluteFillObject,
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 999,
  },
  overlayContent: {
    paddingVertical: spacing['8'],
    paddingHorizontal: spacing['10'],
    borderRadius: borderRadius.xl,
    alignItems: 'center',
  },
  overlayMessage: {
    marginTop: spacing['4'],
    fontSize: 14,
    fontWeight: '500',
  },
});

export default {
  Spinner,
  DotsLoader,
  ProgressBar,
  StepProgress,
  LoadingOverlay,
};
