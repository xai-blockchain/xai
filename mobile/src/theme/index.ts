/**
 * XAI Design System - Main Theme Export
 *
 * Centralized theme configuration for the XAI mobile app.
 * Supports dark/light modes with comprehensive design tokens.
 */

import { useColorScheme } from 'react-native';
import { useMemo } from 'react';

// Re-export all theme modules
export * from './colors';
export * from './typography';
export * from './spacing';
export * from './shadows';

import {
  brand,
  semantic,
  transaction,
  dark,
  light,
  gradients,
  shadows as colorShadows,
} from './colors';
import { typography, fontFamily, fontWeight, fontSize, lineHeight, letterSpacing } from './typography';
import { spacing, layout, borderRadius, touchTarget, hitSlop, screen, safeArea, zIndex, durations } from './spacing';
import { darkShadows, lightShadows } from './shadows';

// Complete theme object for dark mode
export const darkTheme = {
  // Color tokens
  colors: {
    brand,
    semantic,
    transaction,
    ...dark,
  },
  gradients,
  
  // Typography tokens
  typography,
  fontFamily,
  fontWeight,
  fontSize,
  lineHeight,
  letterSpacing,
  
  // Spacing tokens
  spacing,
  layout,
  borderRadius,
  touchTarget,
  hitSlop,
  screen,
  safeArea,
  zIndex,
  durations,
  
  // Shadow tokens
  shadows: darkShadows,
  colorShadows: colorShadows.dark,
  
  // Theme metadata
  isDark: true,
  name: 'dark' as const,
} as const;

// Complete theme object for light mode
export const lightTheme = {
  // Color tokens
  colors: {
    brand,
    semantic,
    transaction,
    ...light,
  },
  gradients,
  
  // Typography tokens
  typography,
  fontFamily,
  fontWeight,
  fontSize,
  lineHeight,
  letterSpacing,
  
  // Spacing tokens
  spacing,
  layout,
  borderRadius,
  touchTarget,
  hitSlop,
  screen,
  safeArea,
  zIndex,
  durations,
  
  // Shadow tokens
  shadows: lightShadows,
  colorShadows: colorShadows.light,
  
  // Theme metadata
  isDark: false,
  name: 'light' as const,
} as const;

// Theme type definition
export type Theme = typeof darkTheme;
export type ThemeName = 'dark' | 'light' | 'system';

// Navigation theme for React Navigation
export const navigationDarkTheme = {
  dark: true,
  colors: {
    primary: brand.primary,
    background: dark.background,
    card: dark.surface,
    text: dark.text,
    border: dark.border,
    notification: semantic.error,
  },
};

export const navigationLightTheme = {
  dark: false,
  colors: {
    primary: brand.primary,
    background: light.background,
    card: light.surface,
    text: light.text,
    border: light.border,
    notification: semantic.error,
  },
};

// Custom hook to get current theme
export function useTheme(): Theme {
  const colorScheme = useColorScheme();
  
  return useMemo(() => {
    return colorScheme === 'light' ? lightTheme : darkTheme;
  }, [colorScheme]);
}

// Custom hook to get navigation theme
export function useNavigationTheme() {
  const colorScheme = useColorScheme();
  
  return useMemo(() => {
    return colorScheme === 'light' ? navigationLightTheme : navigationDarkTheme;
  }, [colorScheme]);
}

// Utility to create theme-aware styles
export function createThemedStyles<T extends Record<string, any>>(
  styleFactory: (theme: Theme) => T
): (theme: Theme) => T {
  return styleFactory;
}

// Default export for convenience
export default {
  dark: darkTheme,
  light: lightTheme,
  useTheme,
  useNavigationTheme,
};
