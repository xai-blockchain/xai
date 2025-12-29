/**
 * Onboarding Component
 *
 * Welcome flow for new users with swipeable slides.
 */

import React, { useState, useRef, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  Dimensions,
  Animated,
  NativeScrollEvent,
  NativeSyntheticEvent,
  ViewStyle,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useTheme } from '../theme';
import { Button } from './Button';
import { Icon, IconName } from './Icon';
import { useHaptics } from '../hooks/useHaptics';
import { spacing, borderRadius } from '../theme/spacing';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

interface OnboardingSlide {
  id: string;
  title: string;
  description: string;
  icon: IconName;
  iconColor?: string;
}

interface OnboardingProps {
  slides?: OnboardingSlide[];
  onComplete: () => void;
  onSkip?: () => void;
}

// Default onboarding slides for XAI wallet
const defaultSlides: OnboardingSlide[] = [
  {
    id: '1',
    title: 'Welcome to XAI',
    description: 'Your gateway to the next generation of blockchain technology. Secure, fast, and intelligent.',
    icon: 'xai-logo',
  },
  {
    id: '2',
    title: 'Secure Wallet',
    description: 'Your private keys are encrypted and stored securely on your device. Only you have access to your funds.',
    icon: 'lock',
  },
  {
    id: '3',
    title: 'Send & Receive',
    description: 'Easily send and receive XAI tokens. Scan QR codes for quick transactions.',
    icon: 'send',
  },
  {
    id: '4',
    title: 'Track Everything',
    description: 'Monitor your transactions, explore blocks, and stay updated with real-time network status.',
    icon: 'explorer',
  },
];

export function Onboarding({
  slides = defaultSlides,
  onComplete,
  onSkip,
}: OnboardingProps) {
  const theme = useTheme();
  const insets = useSafeAreaInsets();
  const haptics = useHaptics();
  const [currentIndex, setCurrentIndex] = useState(0);
  const flatListRef = useRef<FlatList>(null);
  const scrollX = useRef(new Animated.Value(0)).current;

  const isLastSlide = currentIndex === slides.length - 1;

  // Handle scroll
  const handleScroll = Animated.event(
    [{ nativeEvent: { contentOffset: { x: scrollX } } }],
    { useNativeDriver: false }
  );

  // Handle momentum scroll end
  const handleMomentumScrollEnd = useCallback(
    (event: NativeSyntheticEvent<NativeScrollEvent>) => {
      const newIndex = Math.round(event.nativeEvent.contentOffset.x / SCREEN_WIDTH);
      if (newIndex !== currentIndex) {
        setCurrentIndex(newIndex);
        haptics.selection();
      }
    },
    [currentIndex, haptics]
  );

  // Go to next slide
  const handleNext = useCallback(() => {
    if (isLastSlide) {
      haptics.success();
      onComplete();
    } else {
      haptics.selection();
      flatListRef.current?.scrollToIndex({
        index: currentIndex + 1,
        animated: true,
      });
    }
  }, [isLastSlide, currentIndex, haptics, onComplete]);

  // Handle skip
  const handleSkip = useCallback(() => {
    haptics.light();
    onSkip?.() || onComplete();
  }, [haptics, onSkip, onComplete]);

  // Render slide
  const renderSlide = ({ item, index }: { item: OnboardingSlide; index: number }) => {
    // Animated values for this slide
    const inputRange = [
      (index - 1) * SCREEN_WIDTH,
      index * SCREEN_WIDTH,
      (index + 1) * SCREEN_WIDTH,
    ];

    const scale = scrollX.interpolate({
      inputRange,
      outputRange: [0.8, 1, 0.8],
      extrapolate: 'clamp',
    });

    const opacity = scrollX.interpolate({
      inputRange,
      outputRange: [0.4, 1, 0.4],
      extrapolate: 'clamp',
    });

    const translateY = scrollX.interpolate({
      inputRange,
      outputRange: [20, 0, 20],
      extrapolate: 'clamp',
    });

    return (
      <View style={styles.slide}>
        <Animated.View
          style={[
            styles.slideContent,
            {
              opacity,
              transform: [{ scale }, { translateY }],
            },
          ]}
        >
          {/* Icon */}
          <View
            style={[
              styles.iconContainer,
              { backgroundColor: theme.colors.brand.primaryMuted },
            ]}
          >
            <Icon
              name={item.icon}
              size={60}
              color={item.iconColor || theme.colors.brand.primary}
            />
          </View>

          {/* Title */}
          <Text style={[styles.title, { color: theme.colors.text }]}>
            {item.title}
          </Text>

          {/* Description */}
          <Text style={[styles.description, { color: theme.colors.textMuted }]}>
            {item.description}
          </Text>
        </Animated.View>
      </View>
    );
  };

  // Render pagination dots
  const renderPagination = () => {
    return (
      <View style={styles.pagination}>
        {slides.map((_, index) => {
          const inputRange = [
            (index - 1) * SCREEN_WIDTH,
            index * SCREEN_WIDTH,
            (index + 1) * SCREEN_WIDTH,
          ];

          const dotWidth = scrollX.interpolate({
            inputRange,
            outputRange: [8, 24, 8],
            extrapolate: 'clamp',
          });

          const dotOpacity = scrollX.interpolate({
            inputRange,
            outputRange: [0.3, 1, 0.3],
            extrapolate: 'clamp',
          });

          return (
            <Animated.View
              key={index}
              style={[
                styles.dot,
                {
                  width: dotWidth,
                  opacity: dotOpacity,
                  backgroundColor: theme.colors.brand.primary,
                },
              ]}
            />
          );
        })}
      </View>
    );
  };

  return (
    <View
      style={[
        styles.container,
        { backgroundColor: theme.colors.background },
      ]}
    >
      {/* Skip button */}
      {!isLastSlide && onSkip && (
        <View style={[styles.skipContainer, { top: insets.top + spacing['2'] }]}>
          <Button
            title="Skip"
            variant="ghost"
            size="small"
            onPress={handleSkip}
            accessibilityLabel="Skip onboarding"
          />
        </View>
      )}

      {/* Slides */}
      <FlatList
        ref={flatListRef}
        data={slides}
        renderItem={renderSlide}
        keyExtractor={(item) => item.id}
        horizontal
        pagingEnabled
        showsHorizontalScrollIndicator={false}
        onScroll={handleScroll}
        onMomentumScrollEnd={handleMomentumScrollEnd}
        scrollEventThrottle={16}
        getItemLayout={(_, index) => ({
          length: SCREEN_WIDTH,
          offset: SCREEN_WIDTH * index,
          index,
        })}
      />

      {/* Bottom section */}
      <View
        style={[
          styles.bottomSection,
          { paddingBottom: insets.bottom + spacing['4'] },
        ]}
      >
        {/* Pagination */}
        {renderPagination()}

        {/* Next/Get Started button */}
        <Button
          title={isLastSlide ? 'Get Started' : 'Next'}
          onPress={handleNext}
          fullWidth
          size="large"
          style={styles.nextButton}
          accessibilityLabel={isLastSlide ? 'Complete onboarding and get started' : 'Go to next slide'}
        />
      </View>
    </View>
  );
}

// Compact onboarding tips for returning users
export function OnboardingTip({
  title,
  description,
  icon,
  onDismiss,
  style,
}: {
  title: string;
  description: string;
  icon: IconName;
  onDismiss?: () => void;
  style?: ViewStyle;
}) {
  const theme = useTheme();

  return (
    <View
      style={[
        styles.tip,
        { backgroundColor: theme.colors.surface, borderColor: theme.colors.border },
        style,
      ]}
    >
      <View style={[styles.tipIcon, { backgroundColor: theme.colors.brand.primaryMuted }]}>
        <Icon name={icon} size={20} color={theme.colors.brand.primary} />
      </View>
      <View style={styles.tipContent}>
        <Text style={[styles.tipTitle, { color: theme.colors.text }]}>{title}</Text>
        <Text style={[styles.tipDescription, { color: theme.colors.textMuted }]}>
          {description}
        </Text>
      </View>
      {onDismiss && (
        <Button
          title=""
          variant="ghost"
          size="small"
          onPress={onDismiss}
          icon={<Icon name="close" size={16} color={theme.colors.textMuted} />}
          accessibilityLabel="Dismiss tip"
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  skipContainer: {
    position: 'absolute',
    right: spacing['4'],
    zIndex: 10,
  },
  slide: {
    width: SCREEN_WIDTH,
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: spacing['8'],
  },
  slideContent: {
    alignItems: 'center',
    maxWidth: 320,
  },
  iconContainer: {
    width: 120,
    height: 120,
    borderRadius: 60,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: spacing['8'],
  },
  title: {
    fontSize: 28,
    fontWeight: '700',
    textAlign: 'center',
    marginBottom: spacing['4'],
  },
  description: {
    fontSize: 16,
    textAlign: 'center',
    lineHeight: 24,
  },
  bottomSection: {
    paddingHorizontal: spacing['6'],
  },
  pagination: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: spacing['6'],
    gap: spacing['2'],
  },
  dot: {
    height: 8,
    borderRadius: 4,
  },
  nextButton: {
    marginTop: spacing['2'],
  },
  // Tip styles
  tip: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: spacing['3'],
    borderRadius: borderRadius.lg,
    borderWidth: 1,
  },
  tipIcon: {
    width: 40,
    height: 40,
    borderRadius: 20,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: spacing['3'],
  },
  tipContent: {
    flex: 1,
  },
  tipTitle: {
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 2,
  },
  tipDescription: {
    fontSize: 12,
    lineHeight: 18,
  },
});

export default Onboarding;
