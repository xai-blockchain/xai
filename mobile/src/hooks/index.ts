/**
 * XAI Mobile App - Hooks Index
 *
 * Centralized export for all custom hooks.
 */

// Animation hooks
export {
  timingPresets,
  useReduceMotion,
  useFadeAnimation,
  useScaleAnimation,
  useSlideAnimation,
  useShakeAnimation,
  usePulseAnimation,
  useRotateAnimation,
  useStaggerAnimation,
  useSuccessAnimation,
  useCountAnimation,
} from './useAnimation';

// Haptic feedback hooks
export {
  useHaptics,
  triggerHaptic,
  type ImpactType,
  type NotificationType,
} from './useHaptics';

// Accessibility hooks
export {
  useAccessibility,
  useScreenReader,
  useAnnounceForAccessibility,
  useAccessibilityProps,
  formatAccessibleAmount,
  formatAccessibleAddress,
  formatAccessibleTime,
  type AccessibilityState,
} from './useAccessibility';

// Responsive design hooks
export {
  breakpoints,
  useDimensions,
  useResponsive,
  useKeyboard,
  useSafeArea,
  useGridLayout,
  type Breakpoint,
  type ScreenCategory,
  type Orientation,
} from './useResponsive';
