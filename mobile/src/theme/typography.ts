/**
 * XAI Typography System
 *
 * A comprehensive typography scale for consistent text styling.
 * Supports dynamic type scaling for accessibility.
 */

import { Platform, TextStyle, PixelRatio } from 'react-native';

// Font families
export const fontFamily = {
  // System fonts for best native feel and performance
  regular: Platform.select({
    ios: 'System',
    android: 'Roboto',
    default: 'System',
  }),
  medium: Platform.select({
    ios: 'System',
    android: 'Roboto-Medium',
    default: 'System',
  }),
  semibold: Platform.select({
    ios: 'System',
    android: 'Roboto-Medium',
    default: 'System',
  }),
  bold: Platform.select({
    ios: 'System',
    android: 'Roboto-Bold',
    default: 'System',
  }),
  // Monospace for addresses, hashes, amounts
  mono: Platform.select({
    ios: 'Menlo',
    android: 'monospace',
    default: 'monospace',
  }),
} as const;

// Font weights (cross-platform safe values)
export const fontWeight = {
  regular: '400' as const,
  medium: '500' as const,
  semibold: '600' as const,
  bold: '700' as const,
  extrabold: '800' as const,
};

// Base font sizes (in points)
// Uses a modular scale with ratio ~1.25 (major third)
export const fontSize = {
  xs: 11,
  sm: 12,
  base: 14,
  md: 16,
  lg: 18,
  xl: 20,
  '2xl': 24,
  '3xl': 28,
  '4xl': 32,
  '5xl': 40,
  '6xl': 48,
} as const;

// Line heights (multipliers)
export const lineHeight = {
  tight: 1.1,
  snug: 1.25,
  normal: 1.4,
  relaxed: 1.5,
  loose: 1.75,
} as const;

// Letter spacing
export const letterSpacing = {
  tighter: -0.5,
  tight: -0.25,
  normal: 0,
  wide: 0.5,
  wider: 1,
  widest: 2,
} as const;

// Calculate scaled font size respecting user's accessibility settings
function scaledFontSize(size: number, maxScaleFactor: number = 1.5): number {
  const scale = PixelRatio.getFontScale();
  const scaledSize = size * Math.min(scale, maxScaleFactor);
  return Math.round(scaledSize);
}

// Typography presets with full text styles
export const typography = {
  // Display - Hero text, splash screens
  displayLarge: {
    fontSize: fontSize['6xl'],
    fontWeight: fontWeight.bold,
    lineHeight: fontSize['6xl'] * lineHeight.tight,
    letterSpacing: letterSpacing.tight,
  } as TextStyle,
  
  displayMedium: {
    fontSize: fontSize['5xl'],
    fontWeight: fontWeight.bold,
    lineHeight: fontSize['5xl'] * lineHeight.tight,
    letterSpacing: letterSpacing.tight,
  } as TextStyle,
  
  displaySmall: {
    fontSize: fontSize['4xl'],
    fontWeight: fontWeight.bold,
    lineHeight: fontSize['4xl'] * lineHeight.tight,
    letterSpacing: letterSpacing.tight,
  } as TextStyle,
  
  // Headlines - Section headers
  headlineLarge: {
    fontSize: fontSize['3xl'],
    fontWeight: fontWeight.bold,
    lineHeight: fontSize['3xl'] * lineHeight.snug,
  } as TextStyle,
  
  headlineMedium: {
    fontSize: fontSize['2xl'],
    fontWeight: fontWeight.bold,
    lineHeight: fontSize['2xl'] * lineHeight.snug,
  } as TextStyle,
  
  headlineSmall: {
    fontSize: fontSize.xl,
    fontWeight: fontWeight.semibold,
    lineHeight: fontSize.xl * lineHeight.snug,
  } as TextStyle,
  
  // Titles - Card titles, list headers
  titleLarge: {
    fontSize: fontSize.lg,
    fontWeight: fontWeight.semibold,
    lineHeight: fontSize.lg * lineHeight.normal,
  } as TextStyle,
  
  titleMedium: {
    fontSize: fontSize.md,
    fontWeight: fontWeight.semibold,
    lineHeight: fontSize.md * lineHeight.normal,
  } as TextStyle,
  
  titleSmall: {
    fontSize: fontSize.base,
    fontWeight: fontWeight.semibold,
    lineHeight: fontSize.base * lineHeight.normal,
  } as TextStyle,
  
  // Body - Primary content text
  bodyLarge: {
    fontSize: fontSize.md,
    fontWeight: fontWeight.regular,
    lineHeight: fontSize.md * lineHeight.relaxed,
  } as TextStyle,
  
  bodyMedium: {
    fontSize: fontSize.base,
    fontWeight: fontWeight.regular,
    lineHeight: fontSize.base * lineHeight.relaxed,
  } as TextStyle,
  
  bodySmall: {
    fontSize: fontSize.sm,
    fontWeight: fontWeight.regular,
    lineHeight: fontSize.sm * lineHeight.relaxed,
  } as TextStyle,
  
  // Labels - Buttons, form labels
  labelLarge: {
    fontSize: fontSize.md,
    fontWeight: fontWeight.semibold,
    lineHeight: fontSize.md * lineHeight.tight,
    letterSpacing: letterSpacing.wide,
  } as TextStyle,
  
  labelMedium: {
    fontSize: fontSize.base,
    fontWeight: fontWeight.medium,
    lineHeight: fontSize.base * lineHeight.tight,
    letterSpacing: letterSpacing.wide,
  } as TextStyle,
  
  labelSmall: {
    fontSize: fontSize.sm,
    fontWeight: fontWeight.medium,
    lineHeight: fontSize.sm * lineHeight.tight,
    letterSpacing: letterSpacing.wide,
  } as TextStyle,
  
  // Caption - Secondary info, timestamps
  caption: {
    fontSize: fontSize.xs,
    fontWeight: fontWeight.regular,
    lineHeight: fontSize.xs * lineHeight.normal,
    letterSpacing: letterSpacing.wide,
  } as TextStyle,
  
  // Overline - Category labels, section markers
  overline: {
    fontSize: fontSize.xs,
    fontWeight: fontWeight.semibold,
    lineHeight: fontSize.xs * lineHeight.tight,
    letterSpacing: letterSpacing.widest,
    textTransform: 'uppercase',
  } as TextStyle,
  
  // Specialized - Blockchain specific
  mono: {
    fontSize: fontSize.base,
    fontFamily: fontFamily.mono,
    fontWeight: fontWeight.regular,
    lineHeight: fontSize.base * lineHeight.normal,
  } as TextStyle,
  
  monoSmall: {
    fontSize: fontSize.sm,
    fontFamily: fontFamily.mono,
    fontWeight: fontWeight.regular,
    lineHeight: fontSize.sm * lineHeight.normal,
  } as TextStyle,
  
  monoLarge: {
    fontSize: fontSize.md,
    fontFamily: fontFamily.mono,
    fontWeight: fontWeight.regular,
    lineHeight: fontSize.md * lineHeight.normal,
  } as TextStyle,
  
  // Amount - For displaying XAI amounts
  amountLarge: {
    fontSize: fontSize['4xl'],
    fontWeight: fontWeight.bold,
    lineHeight: fontSize['4xl'] * lineHeight.tight,
    letterSpacing: letterSpacing.tight,
  } as TextStyle,
  
  amountMedium: {
    fontSize: fontSize['2xl'],
    fontWeight: fontWeight.bold,
    lineHeight: fontSize['2xl'] * lineHeight.tight,
  } as TextStyle,
  
  amountSmall: {
    fontSize: fontSize.lg,
    fontWeight: fontWeight.semibold,
    lineHeight: fontSize.lg * lineHeight.tight,
  } as TextStyle,
} as const;

// Utility function to create accessible text styles
export function createAccessibleTextStyle(
  baseStyle: TextStyle,
  maxScaleFactor: number = 1.5
): TextStyle {
  const baseFontSize = baseStyle.fontSize || fontSize.base;
  return {
    ...baseStyle,
    fontSize: scaledFontSize(baseFontSize, maxScaleFactor),
    lineHeight: scaledFontSize(
      (baseStyle.lineHeight as number) || baseFontSize * lineHeight.normal,
      maxScaleFactor
    ),
  };
}

// Type definitions
export type FontFamily = typeof fontFamily;
export type FontWeight = typeof fontWeight;
export type FontSize = typeof fontSize;
export type Typography = typeof typography;
