/**
 * XAI Button Component
 *
 * Production-ready button with haptic feedback, animations, and accessibility.
 */

import React, { useCallback, useRef, useMemo } from 'react';
import {
  TouchableOpacity,
  Pressable,
  Text,
  StyleSheet,
  ActivityIndicator,
  ViewStyle,
  TextStyle,
  Animated,
  Platform,
  View,
} from 'react-native';
import { useTheme } from '../theme';
import { useHaptics } from '../hooks/useHaptics';
import { touchTarget, hitSlop } from '../theme/spacing';

// Button variants
export type ButtonVariant = 'primary' | 'secondary' | 'outline' | 'danger' | 'ghost' | 'success';
export type ButtonSize = 'small' | 'medium' | 'large';

interface ButtonProps {
  title: string;
  onPress: () => void;
  variant?: ButtonVariant;
  size?: ButtonSize;
  disabled?: boolean;
  loading?: boolean;
  fullWidth?: boolean;
  style?: ViewStyle;
  textStyle?: TextStyle;
  icon?: React.ReactNode;
  iconPosition?: 'left' | 'right';
  // Accessibility
  accessibilityLabel?: string;
  accessibilityHint?: string;
  testID?: string;
  // Haptics
  hapticFeedback?: boolean;
}

export function Button({
  title,
  onPress,
  variant = 'primary',
  size = 'medium',
  disabled = false,
  loading = false,
  fullWidth = false,
  style,
  textStyle,
  icon,
  iconPosition = 'left',
  accessibilityLabel,
  accessibilityHint,
  testID,
  hapticFeedback = true,
}: ButtonProps) {
  const theme = useTheme();
  const haptics = useHaptics();
  
  // Animation value for press feedback
  const scaleValue = useRef(new Animated.Value(1)).current;
  
  const isDisabled = disabled || loading;

  // Haptic and animation on press in
  const handlePressIn = useCallback(() => {
    if (isDisabled) return;
    
    Animated.spring(scaleValue, {
      toValue: 0.96,
      useNativeDriver: true,
      speed: 50,
      bounciness: 4,
    }).start();
  }, [scaleValue, isDisabled]);

  // Animation on press out
  const handlePressOut = useCallback(() => {
    Animated.spring(scaleValue, {
      toValue: 1,
      useNativeDriver: true,
      speed: 50,
      bounciness: 4,
    }).start();
  }, [scaleValue]);

  // Handle press with haptics
  const handlePress = useCallback(() => {
    if (isDisabled) return;
    
    if (hapticFeedback) {
      haptics.medium();
    }
    
    onPress();
  }, [isDisabled, hapticFeedback, haptics, onPress]);

  // Get variant styles
  const variantStyles = useMemo(() => {
    const { brand, semantic } = theme.colors;
    const { surface, border, text: textColor } = theme.colors;

    const styles: Record<ButtonVariant, { bg: string; text: string; border?: string }> = {
      primary: {
        bg: brand.primary,
        text: '#ffffff',
      },
      secondary: {
        bg: surface,
        text: textColor,
        border: border,
      },
      outline: {
        bg: 'transparent',
        text: brand.primary,
        border: brand.primary,
      },
      danger: {
        bg: semantic.error,
        text: '#ffffff',
      },
      ghost: {
        bg: 'transparent',
        text: brand.primary,
      },
      success: {
        bg: semantic.success,
        text: '#ffffff',
      },
    };

    return styles[variant];
  }, [theme, variant]);

  // Get size styles
  const sizeStyles = useMemo(() => {
    const sizes: Record<ButtonSize, { height: number; paddingH: number; fontSize: number }> = {
      small: {
        height: 36,
        paddingH: 16,
        fontSize: 14,
      },
      medium: {
        height: touchTarget.medium,
        paddingH: 24,
        fontSize: 16,
      },
      large: {
        height: touchTarget.large,
        paddingH: 32,
        fontSize: 18,
      },
    };

    return sizes[size];
  }, [size]);

  // Computed button style
  const buttonStyle = useMemo<ViewStyle[]>(() => [
    styles.button,
    {
      backgroundColor: variantStyles.bg,
      minHeight: sizeStyles.height,
      paddingHorizontal: sizeStyles.paddingH,
      borderWidth: variantStyles.border ? 2 : 0,
      borderColor: variantStyles.border,
    },
    fullWidth && styles.fullWidth,
    isDisabled && styles.disabled,
    style,
  ], [variantStyles, sizeStyles, fullWidth, isDisabled, style]);

  // Computed text style
  const computedTextStyle = useMemo<TextStyle[]>(() => [
    styles.text,
    {
      color: variantStyles.text,
      fontSize: sizeStyles.fontSize,
    },
    textStyle,
  ], [variantStyles, sizeStyles, textStyle]);

  // Spinner color
  const spinnerColor = variantStyles.text;

  // Content rendering
  const renderContent = () => {
    if (loading) {
      return (
        <ActivityIndicator
          color={spinnerColor}
          size={size === 'large' ? 'small' : 'small'}
        />
      );
    }

    return (
      <>
        {icon && iconPosition === 'left' && (
          <View style={styles.iconLeft}>{icon}</View>
        )}
        <Text
          style={computedTextStyle}
          numberOfLines={1}
          allowFontScaling
          maxFontSizeMultiplier={1.3}
        >
          {title}
        </Text>
        {icon && iconPosition === 'right' && (
          <View style={styles.iconRight}>{icon}</View>
        )}
      </>
    );
  };

  return (
    <Animated.View
      style={[
        { transform: [{ scale: scaleValue }] },
        fullWidth && styles.fullWidth,
      ]}
    >
      <Pressable
        style={buttonStyle}
        onPress={handlePress}
        onPressIn={handlePressIn}
        onPressOut={handlePressOut}
        disabled={isDisabled}
        hitSlop={size === 'small' ? hitSlop.medium : undefined}
        // Accessibility
        accessible
        accessibilityRole="button"
        accessibilityLabel={accessibilityLabel || title}
        accessibilityHint={accessibilityHint}
        accessibilityState={{
          disabled: isDisabled,
          busy: loading,
        }}
        testID={testID}
      >
        {renderContent()}
      </Pressable>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  button: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 12,
    gap: 8,
  },
  fullWidth: {
    width: '100%',
  },
  disabled: {
    opacity: 0.5,
  },
  text: {
    fontWeight: '600',
    textAlign: 'center',
  },
  iconLeft: {
    marginRight: 4,
  },
  iconRight: {
    marginLeft: 4,
  },
});

export default Button;
