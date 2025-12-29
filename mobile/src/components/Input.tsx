/**
 * XAI Input Component
 *
 * Production-ready text input with validation, accessibility, and animations.
 */

import React, { useState, useRef, useCallback, forwardRef, useMemo } from 'react';
import {
  View,
  Text,
  TextInput,
  StyleSheet,
  TextInputProps,
  ViewStyle,
  Animated,
  Pressable,
  Platform,
} from 'react-native';
import { useTheme } from '../theme';
import { useHaptics } from '../hooks/useHaptics';
import { spacing, borderRadius, touchTarget } from '../theme/spacing';
import { Icon, IconName } from './Icon';

interface InputProps extends TextInputProps {
  label?: string;
  error?: string;
  hint?: string;
  containerStyle?: ViewStyle;
  inputStyle?: ViewStyle;
  // Right element (button, icon, etc.)
  rightElement?: React.ReactNode;
  // Left icon
  leftIcon?: IconName;
  // Input variants
  variant?: 'default' | 'filled' | 'outlined';
  // Size
  size?: 'small' | 'medium' | 'large';
  // Loading state
  loading?: boolean;
  // Character count
  showCharacterCount?: boolean;
  maxCharacters?: number;
  // Clear button
  showClearButton?: boolean;
  onClear?: () => void;
  // Accessibility
  accessibilityLabel?: string;
  accessibilityHint?: string;
}

export const Input = forwardRef<TextInput, InputProps>(function Input(
  {
    label,
    error,
    hint,
    containerStyle,
    inputStyle,
    rightElement,
    leftIcon,
    variant = 'default',
    size = 'medium',
    loading = false,
    showCharacterCount = false,
    maxCharacters,
    showClearButton = false,
    onClear,
    value,
    onFocus,
    onBlur,
    editable = true,
    accessibilityLabel,
    accessibilityHint,
    ...props
  },
  ref
) {
  const theme = useTheme();
  const haptics = useHaptics();
  const [isFocused, setIsFocused] = useState(false);
  const borderColor = useRef(new Animated.Value(0)).current;

  // Handle focus animation
  const handleFocus = useCallback(
    (e: any) => {
      setIsFocused(true);
      Animated.timing(borderColor, {
        toValue: 1,
        duration: 150,
        useNativeDriver: false,
      }).start();
      onFocus?.(e);
    },
    [borderColor, onFocus]
  );

  // Handle blur animation
  const handleBlur = useCallback(
    (e: any) => {
      setIsFocused(false);
      Animated.timing(borderColor, {
        toValue: 0,
        duration: 150,
        useNativeDriver: false,
      }).start();
      onBlur?.(e);
    },
    [borderColor, onBlur]
  );

  // Handle clear
  const handleClear = useCallback(() => {
    haptics.light();
    onClear?.();
  }, [haptics, onClear]);

  // Get size styles
  const getSizeStyles = () => {
    const sizes = {
      small: {
        height: 40,
        fontSize: 14,
        paddingHorizontal: spacing['3'],
        iconSize: 16,
      },
      medium: {
        height: touchTarget.medium,
        fontSize: 16,
        paddingHorizontal: spacing['4'],
        iconSize: 20,
      },
      large: {
        height: touchTarget.large,
        fontSize: 18,
        paddingHorizontal: spacing['5'],
        iconSize: 24,
      },
    };
    return sizes[size];
  };

  const sizeStyles = getSizeStyles();

  // Get variant styles
  const getVariantStyles = (): ViewStyle => {
    const { surface, background, border, surfaceOverlay } = theme.colors;

    switch (variant) {
      case 'filled':
        return {
          backgroundColor: surfaceOverlay,
          borderWidth: 0,
        };
      case 'outlined':
        return {
          backgroundColor: 'transparent',
          borderWidth: 2,
          borderColor: border,
        };
      default:
        return {
          backgroundColor: surface,
          borderWidth: 1,
          borderColor: border,
        };
    }
  };

  // Animated border color
  const animatedBorderColor = borderColor.interpolate({
    inputRange: [0, 1],
    outputRange: [
      error ? theme.colors.semantic.error : theme.colors.border,
      error ? theme.colors.semantic.error : theme.colors.brand.primary,
    ],
  });

  // Character count
  const characterCount = value?.length || 0;
  const isOverLimit = maxCharacters ? characterCount > maxCharacters : false;

  // Compute accessibility label
  const computedA11yLabel = useMemo(() => {
    let a11yLabel = accessibilityLabel || label || '';
    if (error) {
      a11yLabel += `. Error: ${error}`;
    }
    if (hint) {
      a11yLabel += `. Hint: ${hint}`;
    }
    return a11yLabel;
  }, [accessibilityLabel, label, error, hint]);

  return (
    <View style={[styles.container, containerStyle]}>
      {/* Label */}
      {label && (
        <Text
          style={[
            styles.label,
            { color: error ? theme.colors.semantic.error : theme.colors.textMuted },
          ]}
        >
          {label}
        </Text>
      )}

      {/* Input container */}
      <Animated.View
        style={[
          styles.inputContainer,
          getVariantStyles(),
          {
            height: sizeStyles.height,
            borderColor: animatedBorderColor,
          },
          !editable && styles.disabled,
        ]}
      >
        {/* Left icon */}
        {leftIcon && (
          <View style={[styles.leftIcon, { marginRight: spacing['2'] }]}>
            <Icon
              name={leftIcon}
              size={sizeStyles.iconSize}
              color={theme.colors.textMuted}
            />
          </View>
        )}

        {/* Text input */}
        <TextInput
          ref={ref}
          style={[
            styles.input,
            {
              fontSize: sizeStyles.fontSize,
              color: theme.colors.text,
              paddingHorizontal: leftIcon ? 0 : sizeStyles.paddingHorizontal,
            },
            inputStyle,
          ]}
          placeholderTextColor={theme.colors.textPlaceholder}
          value={value}
          onFocus={handleFocus}
          onBlur={handleBlur}
          editable={editable && !loading}
          maxLength={maxCharacters}
          // Accessibility
          accessible
          accessibilityLabel={computedA11yLabel}
          accessibilityHint={accessibilityHint}
          accessibilityState={{
            disabled: !editable,
            busy: loading,
          }}
          {...props}
        />

        {/* Clear button */}
        {showClearButton && value && value.length > 0 && editable && (
          <Pressable
            onPress={handleClear}
            style={styles.clearButton}
            hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
            accessibilityRole="button"
            accessibilityLabel="Clear input"
          >
            <Icon
              name="close"
              size={16}
              color={theme.colors.textMuted}
            />
          </Pressable>
        )}

        {/* Right element */}
        {rightElement && (
          <View style={styles.rightElement}>{rightElement}</View>
        )}
      </Animated.View>

      {/* Bottom row: error/hint and character count */}
      <View style={styles.bottomRow}>
        {/* Error or hint */}
        {(error || hint) && (
          <Text
            style={[
              styles.helperText,
              {
                color: error ? theme.colors.semantic.error : theme.colors.textMuted,
              },
            ]}
            accessibilityLiveRegion={error ? 'polite' : 'off'}
          >
            {error || hint}
          </Text>
        )}

        {/* Character count */}
        {showCharacterCount && maxCharacters && (
          <Text
            style={[
              styles.characterCount,
              {
                color: isOverLimit
                  ? theme.colors.semantic.error
                  : theme.colors.textMuted,
              },
            ]}
          >
            {characterCount}/{maxCharacters}
          </Text>
        )}
      </View>
    </View>
  );
});

// Specialized input variants
export function SearchInput(props: Omit<InputProps, 'leftIcon' | 'showClearButton'>) {
  return (
    <Input
      leftIcon="search"
      showClearButton
      placeholder="Search..."
      returnKeyType="search"
      {...props}
    />
  );
}

export function PasswordInput(
  props: Omit<InputProps, 'secureTextEntry'> & { showToggle?: boolean }
) {
  const theme = useTheme();
  const [isVisible, setIsVisible] = useState(false);

  const toggleVisibility = () => {
    setIsVisible(!isVisible);
  };

  return (
    <Input
      secureTextEntry={!isVisible}
      autoCapitalize="none"
      autoCorrect={false}
      rightElement={
        props.showToggle !== false ? (
          <Pressable
            onPress={toggleVisibility}
            hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
            accessibilityRole="button"
            accessibilityLabel={isVisible ? 'Hide password' : 'Show password'}
          >
            <Icon
              name={isVisible ? 'eye-off' : 'eye'}
              size={20}
              color={theme.colors.textMuted}
            />
          </Pressable>
        ) : undefined
      }
      {...props}
    />
  );
}

export function AmountInput(
  props: Omit<InputProps, 'keyboardType'> & {
    symbol?: string;
    onMax?: () => void;
  }
) {
  const theme = useTheme();

  return (
    <Input
      keyboardType="decimal-pad"
      rightElement={
        <View style={styles.amountRight}>
          {props.symbol && (
            <Text style={[styles.symbol, { color: theme.colors.textMuted }]}>
              {props.symbol}
            </Text>
          )}
          {props.onMax && (
            <Pressable
              onPress={props.onMax}
              style={[styles.maxButton, { backgroundColor: theme.colors.brand.primaryMuted }]}
              accessibilityRole="button"
              accessibilityLabel="Set maximum amount"
            >
              <Text style={[styles.maxText, { color: theme.colors.brand.primary }]}>
                MAX
              </Text>
            </Pressable>
          )}
        </View>
      }
      {...props}
    />
  );
}

const styles = StyleSheet.create({
  container: {
    marginBottom: spacing['4'],
  },
  label: {
    fontSize: 14,
    fontWeight: '500',
    marginBottom: spacing['2'],
  },
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    borderRadius: borderRadius.lg,
    overflow: 'hidden',
  },
  disabled: {
    opacity: 0.5,
  },
  leftIcon: {
    marginLeft: spacing['4'],
  },
  input: {
    flex: 1,
    height: '100%',
    padding: 0,
    ...Platform.select({
      web: {
        outlineStyle: 'none',
      },
    }),
  },
  clearButton: {
    padding: spacing['2'],
    marginRight: spacing['1'],
  },
  rightElement: {
    marginRight: spacing['3'],
  },
  bottomRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginTop: spacing['1'],
    minHeight: 16,
  },
  helperText: {
    fontSize: 12,
    flex: 1,
  },
  characterCount: {
    fontSize: 12,
    marginLeft: spacing['2'],
  },
  // Amount input
  amountRight: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing['2'],
  },
  symbol: {
    fontSize: 14,
    fontWeight: '600',
  },
  maxButton: {
    paddingHorizontal: spacing['2'],
    paddingVertical: spacing['1'],
    borderRadius: borderRadius.sm,
  },
  maxText: {
    fontSize: 11,
    fontWeight: '700',
  },
});

export default Input;
