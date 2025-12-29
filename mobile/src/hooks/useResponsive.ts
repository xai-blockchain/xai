/**
 * Responsive Design Hooks
 *
 * Provides utilities for responsive layouts, safe areas, and keyboard handling.
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Dimensions,
  ScaledSize,
  Platform,
  StatusBar,
  Keyboard,
  KeyboardEvent,
  LayoutAnimation,
  UIManager,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

// Enable LayoutAnimation on Android
if (Platform.OS === 'android' && UIManager.setLayoutAnimationEnabledExperimental) {
  UIManager.setLayoutAnimationEnabledExperimental(true);
}

// Breakpoint definitions
export const breakpoints = {
  xs: 0,      // Small phones
  sm: 360,    // Standard phones
  md: 414,    // Large phones
  lg: 768,    // Small tablets
  xl: 1024,   // Large tablets
  '2xl': 1280, // Desktop
} as const;

export type Breakpoint = keyof typeof breakpoints;

// Screen size categories
export type ScreenCategory = 'phone' | 'tablet' | 'desktop';

// Orientation type
export type Orientation = 'portrait' | 'landscape';

// Hook to get current dimensions with listener
export function useDimensions() {
  const [dimensions, setDimensions] = useState(() => ({
    window: Dimensions.get('window'),
    screen: Dimensions.get('screen'),
  }));

  useEffect(() => {
    const subscription = Dimensions.addEventListener('change', ({ window, screen }) => {
      setDimensions({ window, screen });
    });

    return () => {
      subscription?.remove();
    };
  }, []);

  return dimensions;
}

// Hook to get responsive layout information
export function useResponsive() {
  const { window } = useDimensions();
  const insets = useSafeAreaInsets();

  const width = window.width;
  const height = window.height;

  // Current breakpoint
  const breakpoint = useMemo((): Breakpoint => {
    if (width >= breakpoints['2xl']) return '2xl';
    if (width >= breakpoints.xl) return 'xl';
    if (width >= breakpoints.lg) return 'lg';
    if (width >= breakpoints.md) return 'md';
    if (width >= breakpoints.sm) return 'sm';
    return 'xs';
  }, [width]);

  // Screen category
  const category = useMemo((): ScreenCategory => {
    if (width >= breakpoints.xl) return 'desktop';
    if (width >= breakpoints.lg) return 'tablet';
    return 'phone';
  }, [width]);

  // Orientation
  const orientation = useMemo((): Orientation => {
    return width > height ? 'landscape' : 'portrait';
  }, [width, height]);

  // Breakpoint comparison helpers
  const isXs = useMemo(() => width < breakpoints.sm, [width]);
  const isSm = useMemo(() => width >= breakpoints.sm && width < breakpoints.md, [width]);
  const isMd = useMemo(() => width >= breakpoints.md && width < breakpoints.lg, [width]);
  const isLg = useMemo(() => width >= breakpoints.lg && width < breakpoints.xl, [width]);
  const isXl = useMemo(() => width >= breakpoints.xl && width < breakpoints['2xl'], [width]);
  const is2Xl = useMemo(() => width >= breakpoints['2xl'], [width]);

  const isPhone = category === 'phone';
  const isTablet = category === 'tablet';
  const isDesktop = category === 'desktop';
  const isPortrait = orientation === 'portrait';
  const isLandscape = orientation === 'landscape';

  // Responsive value selector
  const select = useCallback(<T,>(values: Partial<Record<Breakpoint, T>> & { default: T }): T => {
    const orderedBreakpoints: Breakpoint[] = ['2xl', 'xl', 'lg', 'md', 'sm', 'xs'];
    
    for (const bp of orderedBreakpoints) {
      if (width >= breakpoints[bp] && values[bp] !== undefined) {
        return values[bp] as T;
      }
    }
    
    return values.default;
  }, [width]);

  // Responsive spacing scale factor
  const spacingScale = useMemo(() => {
    if (isTablet) return 1.25;
    if (isDesktop) return 1.5;
    return 1;
  }, [isTablet, isDesktop]);

  // Safe content area
  const contentWidth = useMemo(() => {
    const maxWidth = isDesktop ? 1200 : isTablet ? 720 : width;
    return Math.min(width - insets.left - insets.right, maxWidth);
  }, [width, insets, isTablet, isDesktop]);

  // Column count for grids
  const columns = useMemo(() => {
    if (isDesktop) return 4;
    if (isTablet && isLandscape) return 3;
    if (isTablet) return 2;
    return 1;
  }, [isTablet, isDesktop, isLandscape]);

  return {
    // Dimensions
    width,
    height,
    breakpoint,
    category,
    orientation,
    
    // Breakpoint booleans
    isXs,
    isSm,
    isMd,
    isLg,
    isXl,
    is2Xl,
    
    // Category booleans
    isPhone,
    isTablet,
    isDesktop,
    
    // Orientation booleans
    isPortrait,
    isLandscape,
    
    // Utilities
    select,
    spacingScale,
    contentWidth,
    columns,
    
    // Safe areas
    insets,
  };
}

// Keyboard hook
export function useKeyboard() {
  const [keyboardState, setKeyboardState] = useState({
    isVisible: false,
    height: 0,
    animating: false,
  });

  useEffect(() => {
    const showEvent = Platform.OS === 'ios' ? 'keyboardWillShow' : 'keyboardDidShow';
    const hideEvent = Platform.OS === 'ios' ? 'keyboardWillHide' : 'keyboardDidHide';

    const handleKeyboardShow = (event: KeyboardEvent) => {
      if (Platform.OS === 'ios') {
        setKeyboardState((prev) => ({ ...prev, animating: true }));
      }
      
      LayoutAnimation.configureNext(LayoutAnimation.Presets.easeInEaseOut);
      
      setKeyboardState({
        isVisible: true,
        height: event.endCoordinates.height,
        animating: false,
      });
    };

    const handleKeyboardHide = () => {
      if (Platform.OS === 'ios') {
        setKeyboardState((prev) => ({ ...prev, animating: true }));
      }
      
      LayoutAnimation.configureNext(LayoutAnimation.Presets.easeInEaseOut);
      
      setKeyboardState({
        isVisible: false,
        height: 0,
        animating: false,
      });
    };

    const showSubscription = Keyboard.addListener(showEvent, handleKeyboardShow);
    const hideSubscription = Keyboard.addListener(hideEvent, handleKeyboardHide);

    return () => {
      showSubscription.remove();
      hideSubscription.remove();
    };
  }, []);

  const dismiss = useCallback(() => {
    Keyboard.dismiss();
  }, []);

  return {
    ...keyboardState,
    dismiss,
  };
}

// Safe area hook with additional utilities
export function useSafeArea() {
  const insets = useSafeAreaInsets();
  const { height } = useDimensions().window;

  // Status bar height (useful for custom headers)
  const statusBarHeight = Platform.select({
    ios: insets.top,
    android: StatusBar.currentHeight || 0,
    default: 0,
  });

  // Bottom bar height (home indicator on iOS, nav bar on Android)
  const bottomBarHeight = insets.bottom;

  // Safe content height
  const safeHeight = height - insets.top - insets.bottom;

  // Padding styles for different container types
  const containerPadding = useMemo(() => ({
    paddingTop: insets.top,
    paddingBottom: insets.bottom,
    paddingLeft: insets.left,
    paddingRight: insets.right,
  }), [insets]);

  const horizontalPadding = useMemo(() => ({
    paddingLeft: insets.left,
    paddingRight: insets.right,
  }), [insets]);

  const verticalPadding = useMemo(() => ({
    paddingTop: insets.top,
    paddingBottom: insets.bottom,
  }), [insets]);

  return {
    insets,
    statusBarHeight,
    bottomBarHeight,
    safeHeight,
    containerPadding,
    horizontalPadding,
    verticalPadding,
  };
}

// Grid layout calculator
export function useGridLayout(
  itemCount: number,
  options?: {
    minItemWidth?: number;
    maxColumns?: number;
    gap?: number;
    padding?: number;
  }
) {
  const { width, insets } = useResponsive();
  const {
    minItemWidth = 150,
    maxColumns = 4,
    gap = 16,
    padding = 16,
  } = options || {};

  const layout = useMemo(() => {
    const availableWidth = width - (padding * 2) - insets.left - insets.right;
    
    // Calculate optimal column count
    let columns = Math.floor((availableWidth + gap) / (minItemWidth + gap));
    columns = Math.max(1, Math.min(columns, maxColumns));
    
    // Calculate item width
    const totalGap = (columns - 1) * gap;
    const itemWidth = (availableWidth - totalGap) / columns;
    
    // Calculate rows
    const rows = Math.ceil(itemCount / columns);
    
    return {
      columns,
      rows,
      itemWidth,
      gap,
      containerStyle: {
        flexDirection: 'row' as const,
        flexWrap: 'wrap' as const,
        gap,
        paddingHorizontal: padding + Math.max(insets.left, insets.right),
      },
      itemStyle: {
        width: itemWidth,
      },
    };
  }, [width, insets, itemCount, minItemWidth, maxColumns, gap, padding]);

  return layout;
}
