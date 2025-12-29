/**
 * Accessibility Hooks
 *
 * Provides accessibility utilities and state management.
 */

import { useCallback, useEffect, useState, useMemo } from 'react';
import {
  AccessibilityInfo,
  Platform,
  PixelRatio,
  Dimensions,
  AccessibilityChangeEventName,
} from 'react-native';

// Accessibility state interface
export interface AccessibilityState {
  isScreenReaderEnabled: boolean;
  isReduceMotionEnabled: boolean;
  isBoldTextEnabled: boolean;
  isGrayscaleEnabled: boolean;
  isInvertColorsEnabled: boolean;
  isReduceTransparencyEnabled: boolean;
  fontScale: number;
}

// Hook to get all accessibility settings
export function useAccessibility(): AccessibilityState {
  const [state, setState] = useState<AccessibilityState>({
    isScreenReaderEnabled: false,
    isReduceMotionEnabled: false,
    isBoldTextEnabled: false,
    isGrayscaleEnabled: false,
    isInvertColorsEnabled: false,
    isReduceTransparencyEnabled: false,
    fontScale: PixelRatio.getFontScale(),
  });

  useEffect(() => {
    // Initial check
    const checkAccessibility = async () => {
      const [
        screenReader,
        reduceMotion,
        boldText,
        grayscale,
        invertColors,
        reduceTransparency,
      ] = await Promise.all([
        AccessibilityInfo.isScreenReaderEnabled(),
        AccessibilityInfo.isReduceMotionEnabled(),
        Platform.OS === 'ios' ? AccessibilityInfo.isBoldTextEnabled() : Promise.resolve(false),
        Platform.OS === 'ios' ? AccessibilityInfo.isGrayscaleEnabled() : Promise.resolve(false),
        Platform.OS === 'ios' ? AccessibilityInfo.isInvertColorsEnabled() : Promise.resolve(false),
        Platform.OS === 'ios' ? AccessibilityInfo.isReduceTransparencyEnabled() : Promise.resolve(false),
      ]);

      setState({
        isScreenReaderEnabled: screenReader,
        isReduceMotionEnabled: reduceMotion,
        isBoldTextEnabled: boldText,
        isGrayscaleEnabled: grayscale,
        isInvertColorsEnabled: invertColors,
        isReduceTransparencyEnabled: reduceTransparency,
        fontScale: PixelRatio.getFontScale(),
      });
    };

    checkAccessibility();

    // Subscribe to accessibility changes
    const subscriptions: any[] = [];

    const addListener = (
      event: AccessibilityChangeEventName,
      key: keyof AccessibilityState
    ) => {
      const subscription = AccessibilityInfo.addEventListener(event, (isEnabled) => {
        setState((prev) => ({ ...prev, [key]: isEnabled }));
      });
      subscriptions.push(subscription);
    };

    addListener('screenReaderChanged', 'isScreenReaderEnabled');
    addListener('reduceMotionChanged', 'isReduceMotionEnabled');

    if (Platform.OS === 'ios') {
      addListener('boldTextChanged', 'isBoldTextEnabled');
      addListener('grayscaleChanged', 'isGrayscaleEnabled');
      addListener('invertColorsChanged', 'isInvertColorsEnabled');
      addListener('reduceTransparencyChanged', 'isReduceTransparencyEnabled');
    }

    // Listen for dimension changes (font scale)
    const dimensionSubscription = Dimensions.addEventListener('change', () => {
      setState((prev) => ({ ...prev, fontScale: PixelRatio.getFontScale() }));
    });

    return () => {
      subscriptions.forEach((sub) => sub?.remove());
      dimensionSubscription?.remove();
    };
  }, []);

  return state;
}

// Hook specifically for screen reader state
export function useScreenReader(): boolean {
  const [isEnabled, setIsEnabled] = useState(false);

  useEffect(() => {
    AccessibilityInfo.isScreenReaderEnabled().then(setIsEnabled);

    const subscription = AccessibilityInfo.addEventListener(
      'screenReaderChanged',
      setIsEnabled
    );

    return () => {
      subscription?.remove();
    };
  }, []);

  return isEnabled;
}

// Hook for reduce motion preference
export function useReduceMotion(): boolean {
  const [isEnabled, setIsEnabled] = useState(false);

  useEffect(() => {
    AccessibilityInfo.isReduceMotionEnabled().then(setIsEnabled);

    const subscription = AccessibilityInfo.addEventListener(
      'reduceMotionChanged',
      setIsEnabled
    );

    return () => {
      subscription?.remove();
    };
  }, []);

  return isEnabled;
}

// Announce to screen reader
export function useAnnounceForAccessibility() {
  const announce = useCallback((message: string) => {
    AccessibilityInfo.announceForAccessibility(message);
  }, []);

  return announce;
}

// Generate accessibility props for common patterns
export function useAccessibilityProps() {
  const isScreenReaderEnabled = useScreenReader();

  const button = useCallback(
    (label: string, hint?: string, disabled?: boolean) => ({
      accessible: true,
      accessibilityRole: 'button' as const,
      accessibilityLabel: label,
      accessibilityHint: hint,
      accessibilityState: { disabled },
    }),
    []
  );

  const link = useCallback(
    (label: string, hint?: string) => ({
      accessible: true,
      accessibilityRole: 'link' as const,
      accessibilityLabel: label,
      accessibilityHint: hint,
    }),
    []
  );

  const heading = useCallback(
    (label: string, level?: 1 | 2 | 3 | 4 | 5 | 6) => ({
      accessible: true,
      accessibilityRole: 'header' as const,
      accessibilityLabel: label,
      // Note: accessibilityLevel is not standard in React Native
    }),
    []
  );

  const text = useCallback(
    (label?: string) => ({
      accessible: true,
      accessibilityRole: 'text' as const,
      ...(label && { accessibilityLabel: label }),
    }),
    []
  );

  const image = useCallback(
    (label: string, decorative: boolean = false) => ({
      accessible: !decorative,
      accessibilityRole: decorative ? undefined : ('image' as const),
      accessibilityLabel: decorative ? undefined : label,
      importantForAccessibility: decorative ? ('no' as const) : ('yes' as const),
    }),
    []
  );

  const textInput = useCallback(
    (
      label: string,
      hint?: string,
      error?: string,
      options?: {
        keyboardType?: string;
        isPassword?: boolean;
      }
    ) => ({
      accessible: true,
      accessibilityLabel: label,
      accessibilityHint: hint || (error ? `Error: ${error}` : undefined),
      accessibilityState: {
        error: !!error,
      },
    }),
    []
  );

  const progressBar = useCallback(
    (label: string, value: number, max: number = 100) => ({
      accessible: true,
      accessibilityRole: 'progressbar' as const,
      accessibilityLabel: label,
      accessibilityValue: {
        now: value,
        min: 0,
        max,
        text: `${Math.round((value / max) * 100)}%`,
      },
    }),
    []
  );

  const tab = useCallback(
    (label: string, selected: boolean, index: number, count: number) => ({
      accessible: true,
      accessibilityRole: 'tab' as const,
      accessibilityLabel: `${label}, tab ${index + 1} of ${count}`,
      accessibilityState: { selected },
    }),
    []
  );

  const listItem = useCallback(
    (label: string, index: number, count: number, selected?: boolean) => ({
      accessible: true,
      accessibilityRole: 'menuitem' as const,
      accessibilityLabel: `${label}, ${index + 1} of ${count}`,
      accessibilityState: { selected },
    }),
    []
  );

  return {
    isScreenReaderEnabled,
    button,
    link,
    heading,
    text,
    image,
    textInput,
    progressBar,
    tab,
    listItem,
  };
}

// Format currency for accessibility
export function formatAccessibleAmount(amount: number, currency: string = 'XAI'): string {
  const formatted = amount.toFixed(4);
  const parts = formatted.split('.');
  const whole = parts[0];
  const decimal = parts[1];
  
  if (decimal === '0000') {
    return `${whole} ${currency}`;
  }
  
  return `${whole} point ${decimal.replace(/0+$/, '')} ${currency}`;
}

// Format address for accessibility
export function formatAccessibleAddress(address: string): string {
  // Group characters for better screen reader output
  const groups = address.match(/.{1,4}/g) || [];
  return groups.join(' ');
}

// Format timestamp for accessibility
export function formatAccessibleTime(timestamp: number): string {
  const date = new Date(timestamp * 1000);
  return date.toLocaleString(undefined, {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: 'numeric',
    minute: 'numeric',
  });
}
