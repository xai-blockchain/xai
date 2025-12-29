/**
 * XAI Spacing System
 *
 * A consistent spacing scale based on 4px base unit.
 * Covers margins, padding, gaps, and layout dimensions.
 */

import { Dimensions, Platform, StatusBar } from 'react-native';

// Base unit for the spacing scale
const BASE_UNIT = 4;

// Spacing scale (in pixels)
export const spacing = {
  // Micro spacing
  none: 0,
  px: 1,           // 1px - hairline borders
  '0.5': 2,        // 2px - minimal spacing
  
  // Small spacing
  '1': 4,          // 4px - tight spacing
  '1.5': 6,        // 6px
  '2': 8,          // 8px - small gap
  '2.5': 10,       // 10px
  '3': 12,         // 12px - default small
  '3.5': 14,       // 14px
  
  // Medium spacing
  '4': 16,         // 16px - default padding
  '5': 20,         // 20px
  '6': 24,         // 24px - section gap
  '7': 28,         // 28px
  '8': 32,         // 32px - large gap
  
  // Large spacing
  '10': 40,        // 40px - major section
  '12': 48,        // 48px
  '14': 56,        // 56px
  '16': 64,        // 64px - screen padding
  
  // Extra large spacing
  '20': 80,        // 80px
  '24': 96,        // 96px
  '32': 128,       // 128px - hero spacing
} as const;

// Semantic spacing aliases
export const layout = {
  // Screen padding
  screenPaddingHorizontal: spacing['4'],    // 16px
  screenPaddingVertical: spacing['4'],      // 16px
  screenPaddingBottom: spacing['8'],        // 32px (extra for scroll)
  
  // Card spacing
  cardPadding: spacing['4'],                // 16px
  cardPaddingSmall: spacing['3'],           // 12px
  cardPaddingLarge: spacing['6'],           // 24px
  cardMargin: spacing['3'],                 // 12px
  cardBorderRadius: spacing['4'],           // 16px
  cardBorderRadiusSmall: spacing['3'],      // 12px
  
  // List item spacing
  listItemPaddingVertical: spacing['3.5'],  // 14px
  listItemPaddingHorizontal: spacing['4'],  // 16px
  listItemGap: spacing['3'],                // 12px
  
  // Button spacing
  buttonPaddingVertical: spacing['3.5'],    // 14px
  buttonPaddingHorizontalSmall: spacing['4'], // 16px
  buttonPaddingHorizontal: spacing['6'],    // 24px
  buttonPaddingHorizontalLarge: spacing['8'], // 32px
  buttonBorderRadius: spacing['3'],         // 12px
  buttonGap: spacing['2'],                  // 8px
  
  // Input spacing
  inputPaddingVertical: spacing['3.5'],     // 14px
  inputPaddingHorizontal: spacing['4'],     // 16px
  inputBorderRadius: spacing['3'],          // 12px
  inputLabelGap: spacing['2'],              // 8px
  
  // Section spacing
  sectionGap: spacing['6'],                 // 24px
  sectionGapLarge: spacing['8'],            // 32px
  
  // Icon spacing
  iconSizeSmall: spacing['4'],              // 16px
  iconSizeMedium: spacing['6'],             // 24px
  iconSizeLarge: spacing['8'],              // 32px
  iconSizeXLarge: spacing['10'],            // 40px
  iconGap: spacing['2'],                    // 8px
  
  // Modal spacing
  modalPadding: spacing['4'],               // 16px
  modalBorderRadius: spacing['5'],          // 20px
  
  // Header spacing
  headerHeight: spacing['14'],              // 56px
  headerPadding: spacing['4'],              // 16px
  
  // Tab bar
  tabBarHeight: spacing['16'],              // 64px (includes safe area)
  tabBarPadding: spacing['2'],              // 8px
  
  // Bottom sheet
  bottomSheetHandleWidth: spacing['10'],    // 40px
  bottomSheetHandleHeight: spacing['1'],    // 4px
  bottomSheetHeaderHeight: spacing['14'],   // 56px
} as const;

// Border radius scale
export const borderRadius = {
  none: 0,
  sm: 4,           // Subtle rounding
  md: 8,           // Default rounding
  lg: 12,          // Cards, buttons
  xl: 16,          // Large cards
  '2xl': 20,       // Modals, bottom sheets
  '3xl': 24,       // Large modals
  full: 9999,      // Pills, circular
} as const;

// Touch target sizes (minimum 44x44 for accessibility)
export const touchTarget = {
  minimum: 44,     // WCAG minimum
  small: 36,       // Small inline buttons (with hitSlop)
  medium: 44,      // Default
  large: 56,       // Primary actions
  xlarge: 64,      // Hero buttons
} as const;

// Hit slop for smaller visual elements
export const hitSlop = {
  small: { top: 8, bottom: 8, left: 8, right: 8 },
  medium: { top: 12, bottom: 12, left: 12, right: 12 },
  large: { top: 16, bottom: 16, left: 16, right: 16 },
} as const;

// Screen dimensions (for responsive calculations)
export const screen = {
  width: Dimensions.get('window').width,
  height: Dimensions.get('window').height,
  isSmall: Dimensions.get('window').width < 375,
  isMedium: Dimensions.get('window').width >= 375 && Dimensions.get('window').width < 414,
  isLarge: Dimensions.get('window').width >= 414,
  isTablet: Dimensions.get('window').width >= 768,
} as const;

// Safe area defaults (will be overridden by SafeAreaContext)
export const safeArea = {
  top: Platform.select({
    ios: 44,
    android: StatusBar.currentHeight || 24,
    default: 0,
  }),
  bottom: Platform.select({
    ios: 34,  // iPhone X and later
    android: 0,
    default: 0,
  }),
  left: 0,
  right: 0,
} as const;

// Z-index scale for layering
export const zIndex = {
  base: 0,
  dropdown: 10,
  sticky: 20,
  fixed: 30,
  modalBackdrop: 40,
  modal: 50,
  popover: 60,
  tooltip: 70,
  toast: 80,
  max: 100,
} as const;

// Animation durations
export const durations = {
  instant: 0,
  fast: 100,
  normal: 200,
  slow: 300,
  slower: 500,
  slowest: 1000,
} as const;

// Type definitions
export type Spacing = typeof spacing;
export type Layout = typeof layout;
export type BorderRadius = typeof borderRadius;
export type TouchTarget = typeof touchTarget;
