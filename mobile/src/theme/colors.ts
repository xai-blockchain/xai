/**
 * XAI Color System
 *
 * A comprehensive color palette for the XAI mobile app.
 * Designed for WCAG AA compliance with proper contrast ratios.
 */

// Brand colors - XAI primary identity
export const brand = {
  primary: '#6366f1',       // Indigo - main brand color
  primaryLight: '#818cf8',  // Lighter variant for hover/pressed states
  primaryDark: '#4f46e5',   // Darker variant for emphasis
  primaryMuted: '#6366f120', // 12% opacity for backgrounds
  secondary: '#8b5cf6',     // Purple - secondary accent
  secondaryMuted: '#8b5cf620',
  accent: '#06b6d4',        // Cyan - accent for highlights
  accentMuted: '#06b6d420',
} as const;

// Semantic colors for status and feedback
export const semantic = {
  success: '#10b981',       // Green - confirmations, positive
  successLight: '#34d399',
  successMuted: '#10b98120',
  warning: '#f59e0b',       // Amber - warnings, pending
  warningLight: '#fbbf24',
  warningMuted: '#f59e0b20',
  error: '#ef4444',         // Red - errors, destructive
  errorLight: '#f87171',
  errorMuted: '#ef444420',
  info: '#3b82f6',          // Blue - informational
  infoLight: '#60a5fa',
  infoMuted: '#3b82f620',
} as const;

// Transaction-specific colors
export const transaction = {
  incoming: '#10b981',      // Green for received
  incomingBg: '#10b98120',
  outgoing: '#ef4444',      // Red for sent
  outgoingBg: '#ef444420',
  pending: '#f59e0b',       // Amber for pending
  pendingBg: '#f59e0b20',
} as const;

// Dark theme palette
export const dark = {
  // Backgrounds
  background: '#0f0f1a',          // Main app background
  backgroundElevated: '#1a1a2e',  // Elevated surfaces (modals)
  surface: '#1e1e2e',             // Cards, panels
  surfaceElevated: '#252538',     // Elevated cards (pressed)
  surfaceOverlay: '#2e2e3e',      // Overlays, borders
  
  // Text hierarchy
  text: '#ffffff',                // Primary text
  textSecondary: '#e5e7eb',       // Secondary text
  textMuted: '#9ca3af',           // Muted text, labels
  textDisabled: '#6b7280',        // Disabled text
  textPlaceholder: '#4b5563',     // Input placeholders
  
  // Borders and dividers
  border: '#2e2e3e',              // Default border
  borderLight: '#374151',         // Light border
  borderFocus: '#6366f1',         // Focus ring color
  divider: '#1f2937',             // Subtle dividers
  
  // Interactive elements
  overlay: 'rgba(0, 0, 0, 0.8)',  // Modal backdrop
  overlayLight: 'rgba(0, 0, 0, 0.5)',
  scrim: 'rgba(15, 15, 26, 0.9)', // Bottom sheet scrim
  
  // Status bar
  statusBar: '#0f0f1a',
} as const;

// Light theme palette
export const light = {
  // Backgrounds
  background: '#ffffff',
  backgroundElevated: '#f9fafb',
  surface: '#f3f4f6',
  surfaceElevated: '#e5e7eb',
  surfaceOverlay: '#d1d5db',
  
  // Text hierarchy
  text: '#111827',
  textSecondary: '#374151',
  textMuted: '#6b7280',
  textDisabled: '#9ca3af',
  textPlaceholder: '#9ca3af',
  
  // Borders and dividers
  border: '#e5e7eb',
  borderLight: '#f3f4f6',
  borderFocus: '#6366f1',
  divider: '#f3f4f6',
  
  // Interactive elements
  overlay: 'rgba(0, 0, 0, 0.5)',
  overlayLight: 'rgba(0, 0, 0, 0.3)',
  scrim: 'rgba(255, 255, 255, 0.9)',
  
  // Status bar
  statusBar: '#ffffff',
} as const;

// Gradient definitions
export const gradients = {
  primary: ['#6366f1', '#8b5cf6'],
  primaryToAccent: ['#6366f1', '#06b6d4'],
  success: ['#10b981', '#34d399'],
  warning: ['#f59e0b', '#fbbf24'],
  error: ['#ef4444', '#f87171'],
  darkOverlay: ['rgba(0,0,0,0)', 'rgba(0,0,0,0.8)'],
  lightOverlay: ['rgba(255,255,255,0)', 'rgba(255,255,255,0.8)'],
} as const;

// Shadow colors (for platform-specific shadows)
export const shadows = {
  dark: {
    small: 'rgba(0, 0, 0, 0.3)',
    medium: 'rgba(0, 0, 0, 0.4)',
    large: 'rgba(0, 0, 0, 0.5)',
    colored: 'rgba(99, 102, 241, 0.3)', // Primary color shadow
  },
  light: {
    small: 'rgba(0, 0, 0, 0.1)',
    medium: 'rgba(0, 0, 0, 0.15)',
    large: 'rgba(0, 0, 0, 0.2)',
    colored: 'rgba(99, 102, 241, 0.2)',
  },
} as const;

// Color type definitions
export type BrandColors = typeof brand;
export type SemanticColors = typeof semantic;
export type TransactionColors = typeof transaction;
export type DarkThemeColors = typeof dark;
export type LightThemeColors = typeof light;
export type GradientColors = typeof gradients;
export type ShadowColors = typeof shadows;

// Theme-aware color getter type
export type ThemeColors = DarkThemeColors | LightThemeColors;
