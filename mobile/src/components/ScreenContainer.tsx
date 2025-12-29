/**
 * Screen Container Component
 *
 * Provides consistent safe area handling, keyboard avoiding, and responsive layout.
 */

import React, { ReactNode } from 'react';
import {
  View,
  ScrollView,
  StyleSheet,
  ViewStyle,
  KeyboardAvoidingView,
  Platform,
  StatusBar,
  RefreshControl,
} from 'react-native';
import { useSafeAreaInsets, Edge, SafeAreaView } from 'react-native-safe-area-context';
import { useTheme } from '../theme';
import { useKeyboard, useResponsive } from '../hooks/useResponsive';
import { spacing } from '../theme/spacing';
import { Spinner } from './ProgressIndicator';

interface ScreenContainerProps {
  children: ReactNode;
  // Layout options
  scroll?: boolean;
  keyboardAvoiding?: boolean;
  // Safe area edges to apply
  edges?: Edge[];
  // Padding options
  noPadding?: boolean;
  horizontalPadding?: boolean;
  // Background color override
  backgroundColor?: string;
  // Content container style
  contentContainerStyle?: ViewStyle;
  // Style for the main container
  style?: ViewStyle;
  // Pull to refresh
  refreshing?: boolean;
  onRefresh?: () => void;
  // Loading state
  loading?: boolean;
  // Header component
  header?: ReactNode;
  // Footer component (fixed at bottom)
  footer?: ReactNode;
  // Accessibility
  accessibilityLabel?: string;
}

export function ScreenContainer({
  children,
  scroll = false,
  keyboardAvoiding = true,
  edges = ['top', 'left', 'right'],
  noPadding = false,
  horizontalPadding = true,
  backgroundColor,
  contentContainerStyle,
  style,
  refreshing = false,
  onRefresh,
  loading = false,
  header,
  footer,
  accessibilityLabel,
}: ScreenContainerProps) {
  const theme = useTheme();
  const insets = useSafeAreaInsets();
  const keyboard = useKeyboard();
  const { isTablet, contentWidth } = useResponsive();

  const bgColor = backgroundColor || theme.colors.background;

  // Compute padding
  const getPadding = (): ViewStyle => {
    if (noPadding) return {};

    const basePadding: ViewStyle = {};

    if (horizontalPadding) {
      // On tablets, center content with max width
      if (isTablet) {
        basePadding.paddingHorizontal = Math.max(
          spacing['4'],
          (contentWidth - 600) / 2
        );
      } else {
        basePadding.paddingHorizontal = spacing['4'];
      }
    }

    return basePadding;
  };

  // Content wrapper
  const renderContent = () => {
    if (loading) {
      return (
        <View style={styles.loadingContainer}>
          <Spinner size="large" />
        </View>
      );
    }

    const contentStyle = [
      getPadding(),
      { flexGrow: 1 },
      contentContainerStyle,
    ];

    if (scroll) {
      return (
        <ScrollView
          style={styles.scrollView}
          contentContainerStyle={[
            contentStyle,
            { paddingBottom: insets.bottom + (footer ? 80 : spacing['8']) },
          ]}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}
          refreshControl={
            onRefresh ? (
              <RefreshControl
                refreshing={refreshing}
                onRefresh={onRefresh}
                tintColor={theme.colors.brand.primary}
                colors={[theme.colors.brand.primary]}
                progressBackgroundColor={theme.colors.surface}
              />
            ) : undefined
          }
        >
          {children}
        </ScrollView>
      );
    }

    return (
      <View style={[styles.content, contentStyle]}>
        {children}
      </View>
    );
  };

  // Main container with keyboard avoiding
  const renderContainer = () => {
    const containerContent = (
      <>
        {header}
        {renderContent()}
        {footer && (
          <View
            style={[
              styles.footer,
              {
                backgroundColor: bgColor,
                paddingBottom: insets.bottom + spacing['4'],
                paddingHorizontal: horizontalPadding ? spacing['4'] : 0,
              },
            ]}
          >
            {footer}
          </View>
        )}
      </>
    );

    if (keyboardAvoiding && Platform.OS === 'ios') {
      return (
        <KeyboardAvoidingView
          style={styles.flex}
          behavior="padding"
          keyboardVerticalOffset={Platform.OS === 'ios' ? 0 : 0}
        >
          {containerContent}
        </KeyboardAvoidingView>
      );
    }

    return <View style={styles.flex}>{containerContent}</View>;
  };

  return (
    <SafeAreaView
      edges={edges}
      style={[
        styles.container,
        { backgroundColor: bgColor },
        style,
      ]}
      accessibilityLabel={accessibilityLabel}
    >
      <StatusBar
        barStyle={theme.isDark ? 'light-content' : 'dark-content'}
        backgroundColor={bgColor}
      />
      {renderContainer()}
    </SafeAreaView>
  );
}

// Tab screen container with consistent tab bar handling
export function TabScreenContainer(props: Omit<ScreenContainerProps, 'edges'>) {
  return (
    <ScreenContainer
      edges={['left', 'right']}
      {...props}
    />
  );
}

// Modal screen container
export function ModalScreenContainer(
  props: Omit<ScreenContainerProps, 'edges' | 'keyboardAvoiding'>
) {
  const theme = useTheme();
  const insets = useSafeAreaInsets();

  return (
    <View style={[styles.modalContainer, { backgroundColor: theme.colors.background }]}>
      {/* Handle bar */}
      <View style={styles.handleContainer}>
        <View style={[styles.handle, { backgroundColor: theme.colors.surfaceOverlay }]} />
      </View>
      <ScreenContainer
        edges={[]}
        keyboardAvoiding
        contentContainerStyle={{ paddingTop: spacing['2'] }}
        {...props}
      />
    </View>
  );
}

// Full screen container (no safe areas, for splash/onboarding)
export function FullScreenContainer({
  children,
  backgroundColor,
  style,
}: {
  children: ReactNode;
  backgroundColor?: string;
  style?: ViewStyle;
}) {
  const theme = useTheme();
  const bgColor = backgroundColor || theme.colors.background;

  return (
    <View style={[styles.container, { backgroundColor: bgColor }, style]}>
      <StatusBar
        barStyle={theme.isDark ? 'light-content' : 'dark-content'}
        backgroundColor="transparent"
        translucent
      />
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  flex: {
    flex: 1,
  },
  scrollView: {
    flex: 1,
  },
  content: {
    flex: 1,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  footer: {
    position: 'absolute',
    left: 0,
    right: 0,
    bottom: 0,
    paddingTop: spacing['4'],
    borderTopWidth: 1,
    borderTopColor: 'rgba(0,0,0,0.1)',
  },
  modalContainer: {
    flex: 1,
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    overflow: 'hidden',
  },
  handleContainer: {
    alignItems: 'center',
    paddingVertical: spacing['3'],
  },
  handle: {
    width: 40,
    height: 4,
    borderRadius: 2,
  },
});

export default ScreenContainer;
