/**
 * XAI Shadow System
 *
 * Cross-platform shadow definitions for depth and elevation.
 */

import { Platform, ViewStyle } from 'react-native';

// Shadow definitions for dark theme
export const darkShadows = {
  none: Platform.select<ViewStyle>({
    ios: {
      shadowColor: 'transparent',
      shadowOffset: { width: 0, height: 0 },
      shadowOpacity: 0,
      shadowRadius: 0,
    },
    android: {
      elevation: 0,
    },
    default: {},
  }) as ViewStyle,
  
  xs: Platform.select<ViewStyle>({
    ios: {
      shadowColor: '#000000',
      shadowOffset: { width: 0, height: 1 },
      shadowOpacity: 0.2,
      shadowRadius: 2,
    },
    android: {
      elevation: 1,
    },
    default: {},
  }) as ViewStyle,
  
  sm: Platform.select<ViewStyle>({
    ios: {
      shadowColor: '#000000',
      shadowOffset: { width: 0, height: 2 },
      shadowOpacity: 0.25,
      shadowRadius: 4,
    },
    android: {
      elevation: 2,
    },
    default: {},
  }) as ViewStyle,
  
  md: Platform.select<ViewStyle>({
    ios: {
      shadowColor: '#000000',
      shadowOffset: { width: 0, height: 4 },
      shadowOpacity: 0.3,
      shadowRadius: 8,
    },
    android: {
      elevation: 4,
    },
    default: {},
  }) as ViewStyle,
  
  lg: Platform.select<ViewStyle>({
    ios: {
      shadowColor: '#000000',
      shadowOffset: { width: 0, height: 8 },
      shadowOpacity: 0.35,
      shadowRadius: 16,
    },
    android: {
      elevation: 8,
    },
    default: {},
  }) as ViewStyle,
  
  xl: Platform.select<ViewStyle>({
    ios: {
      shadowColor: '#000000',
      shadowOffset: { width: 0, height: 12 },
      shadowOpacity: 0.4,
      shadowRadius: 24,
    },
    android: {
      elevation: 12,
    },
    default: {},
  }) as ViewStyle,
  
  '2xl': Platform.select<ViewStyle>({
    ios: {
      shadowColor: '#000000',
      shadowOffset: { width: 0, height: 16 },
      shadowOpacity: 0.45,
      shadowRadius: 32,
    },
    android: {
      elevation: 16,
    },
    default: {},
  }) as ViewStyle,
  
  // Colored shadows for accented elements
  primary: Platform.select<ViewStyle>({
    ios: {
      shadowColor: '#6366f1',
      shadowOffset: { width: 0, height: 4 },
      shadowOpacity: 0.4,
      shadowRadius: 12,
    },
    android: {
      elevation: 6,
    },
    default: {},
  }) as ViewStyle,
  
  success: Platform.select<ViewStyle>({
    ios: {
      shadowColor: '#10b981',
      shadowOffset: { width: 0, height: 4 },
      shadowOpacity: 0.4,
      shadowRadius: 12,
    },
    android: {
      elevation: 6,
    },
    default: {},
  }) as ViewStyle,
  
  error: Platform.select<ViewStyle>({
    ios: {
      shadowColor: '#ef4444',
      shadowOffset: { width: 0, height: 4 },
      shadowOpacity: 0.4,
      shadowRadius: 12,
    },
    android: {
      elevation: 6,
    },
    default: {},
  }) as ViewStyle,
  
  // Glow effect for hero elements
  glow: Platform.select<ViewStyle>({
    ios: {
      shadowColor: '#6366f1',
      shadowOffset: { width: 0, height: 0 },
      shadowOpacity: 0.5,
      shadowRadius: 20,
    },
    android: {
      elevation: 8,
    },
    default: {},
  }) as ViewStyle,
  
  // Inner shadow simulation (border-based)
  inner: {
    borderWidth: 1,
    borderColor: 'rgba(0, 0, 0, 0.2)',
  } as ViewStyle,
};

// Shadow definitions for light theme
export const lightShadows = {
  none: Platform.select<ViewStyle>({
    ios: {
      shadowColor: 'transparent',
      shadowOffset: { width: 0, height: 0 },
      shadowOpacity: 0,
      shadowRadius: 0,
    },
    android: {
      elevation: 0,
    },
    default: {},
  }) as ViewStyle,
  
  xs: Platform.select<ViewStyle>({
    ios: {
      shadowColor: '#000000',
      shadowOffset: { width: 0, height: 1 },
      shadowOpacity: 0.05,
      shadowRadius: 2,
    },
    android: {
      elevation: 1,
    },
    default: {},
  }) as ViewStyle,
  
  sm: Platform.select<ViewStyle>({
    ios: {
      shadowColor: '#000000',
      shadowOffset: { width: 0, height: 2 },
      shadowOpacity: 0.08,
      shadowRadius: 4,
    },
    android: {
      elevation: 2,
    },
    default: {},
  }) as ViewStyle,
  
  md: Platform.select<ViewStyle>({
    ios: {
      shadowColor: '#000000',
      shadowOffset: { width: 0, height: 4 },
      shadowOpacity: 0.1,
      shadowRadius: 8,
    },
    android: {
      elevation: 4,
    },
    default: {},
  }) as ViewStyle,
  
  lg: Platform.select<ViewStyle>({
    ios: {
      shadowColor: '#000000',
      shadowOffset: { width: 0, height: 8 },
      shadowOpacity: 0.12,
      shadowRadius: 16,
    },
    android: {
      elevation: 8,
    },
    default: {},
  }) as ViewStyle,
  
  xl: Platform.select<ViewStyle>({
    ios: {
      shadowColor: '#000000',
      shadowOffset: { width: 0, height: 12 },
      shadowOpacity: 0.15,
      shadowRadius: 24,
    },
    android: {
      elevation: 12,
    },
    default: {},
  }) as ViewStyle,
  
  '2xl': Platform.select<ViewStyle>({
    ios: {
      shadowColor: '#000000',
      shadowOffset: { width: 0, height: 16 },
      shadowOpacity: 0.18,
      shadowRadius: 32,
    },
    android: {
      elevation: 16,
    },
    default: {},
  }) as ViewStyle,
  
  primary: Platform.select<ViewStyle>({
    ios: {
      shadowColor: '#6366f1',
      shadowOffset: { width: 0, height: 4 },
      shadowOpacity: 0.25,
      shadowRadius: 12,
    },
    android: {
      elevation: 6,
    },
    default: {},
  }) as ViewStyle,
  
  success: Platform.select<ViewStyle>({
    ios: {
      shadowColor: '#10b981',
      shadowOffset: { width: 0, height: 4 },
      shadowOpacity: 0.25,
      shadowRadius: 12,
    },
    android: {
      elevation: 6,
    },
    default: {},
  }) as ViewStyle,
  
  error: Platform.select<ViewStyle>({
    ios: {
      shadowColor: '#ef4444',
      shadowOffset: { width: 0, height: 4 },
      shadowOpacity: 0.25,
      shadowRadius: 12,
    },
    android: {
      elevation: 6,
    },
    default: {},
  }) as ViewStyle,
  
  glow: Platform.select<ViewStyle>({
    ios: {
      shadowColor: '#6366f1',
      shadowOffset: { width: 0, height: 0 },
      shadowOpacity: 0.3,
      shadowRadius: 20,
    },
    android: {
      elevation: 8,
    },
    default: {},
  }) as ViewStyle,
  
  inner: {
    borderWidth: 1,
    borderColor: 'rgba(0, 0, 0, 0.08)',
  } as ViewStyle,
};

export type ShadowName = keyof typeof darkShadows;
export type Shadows = typeof darkShadows;
