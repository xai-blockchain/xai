/**
 * Animation Hooks for XAI Mobile App
 *
 * Provides reusable animation primitives with accessibility support.
 */

import { useRef, useCallback, useEffect } from 'react';
import {
  Animated,
  Easing,
  AccessibilityInfo,
  Platform,
} from 'react-native';
import { durations } from '../theme/spacing';

// Animation timing presets
export const timingPresets = {
  // Standard easing curves
  easeIn: Easing.bezier(0.4, 0, 1, 1),
  easeOut: Easing.bezier(0, 0, 0.2, 1),
  easeInOut: Easing.bezier(0.4, 0, 0.2, 1),
  
  // Spring-like curves
  spring: Easing.bezier(0.175, 0.885, 0.32, 1.275),
  bounce: Easing.bezier(0.175, 0.885, 0.32, 1.5),
  
  // Sharp curves
  sharp: Easing.bezier(0.4, 0, 0.6, 1),
  
  // Linear for continuous animations
  linear: Easing.linear,
} as const;

// Hook to check if reduce motion is enabled
export function useReduceMotion(): boolean {
  const reduceMotion = useRef(false);

  useEffect(() => {
    const checkReduceMotion = async () => {
      const isEnabled = await AccessibilityInfo.isReduceMotionEnabled();
      reduceMotion.current = isEnabled;
    };
    
    checkReduceMotion();
    
    const subscription = AccessibilityInfo.addEventListener(
      'reduceMotionChanged',
      (isEnabled) => {
        reduceMotion.current = isEnabled;
      }
    );

    return () => {
      subscription?.remove();
    };
  }, []);

  return reduceMotion.current;
}

// Fade animation hook
export function useFadeAnimation(
  initialValue: number = 0,
  duration: number = durations.normal
) {
  const opacity = useRef(new Animated.Value(initialValue)).current;
  const reduceMotion = useReduceMotion();

  const fadeIn = useCallback((callback?: () => void) => {
    if (reduceMotion) {
      opacity.setValue(1);
      callback?.();
      return;
    }

    Animated.timing(opacity, {
      toValue: 1,
      duration,
      easing: timingPresets.easeOut,
      useNativeDriver: true,
    }).start(callback);
  }, [opacity, duration, reduceMotion]);

  const fadeOut = useCallback((callback?: () => void) => {
    if (reduceMotion) {
      opacity.setValue(0);
      callback?.();
      return;
    }

    Animated.timing(opacity, {
      toValue: 0,
      duration,
      easing: timingPresets.easeIn,
      useNativeDriver: true,
    }).start(callback);
  }, [opacity, duration, reduceMotion]);

  return { opacity, fadeIn, fadeOut };
}

// Scale animation hook (for press feedback)
export function useScaleAnimation(
  initialValue: number = 1,
  pressedValue: number = 0.95
) {
  const scale = useRef(new Animated.Value(initialValue)).current;
  const reduceMotion = useReduceMotion();

  const scaleDown = useCallback(() => {
    if (reduceMotion) {
      scale.setValue(pressedValue);
      return;
    }

    Animated.spring(scale, {
      toValue: pressedValue,
      useNativeDriver: true,
      speed: 50,
      bounciness: 4,
    }).start();
  }, [scale, pressedValue, reduceMotion]);

  const scaleUp = useCallback(() => {
    if (reduceMotion) {
      scale.setValue(initialValue);
      return;
    }

    Animated.spring(scale, {
      toValue: initialValue,
      useNativeDriver: true,
      speed: 50,
      bounciness: 4,
    }).start();
  }, [scale, initialValue, reduceMotion]);

  return { scale, scaleDown, scaleUp };
}

// Slide animation hook
export function useSlideAnimation(
  axis: 'x' | 'y' = 'y',
  initialOffset: number = 50
) {
  const translateValue = useRef(new Animated.Value(initialOffset)).current;
  const opacity = useRef(new Animated.Value(0)).current;
  const reduceMotion = useReduceMotion();

  const slideIn = useCallback((callback?: () => void) => {
    if (reduceMotion) {
      translateValue.setValue(0);
      opacity.setValue(1);
      callback?.();
      return;
    }

    Animated.parallel([
      Animated.timing(translateValue, {
        toValue: 0,
        duration: durations.slow,
        easing: timingPresets.easeOut,
        useNativeDriver: true,
      }),
      Animated.timing(opacity, {
        toValue: 1,
        duration: durations.normal,
        easing: timingPresets.easeOut,
        useNativeDriver: true,
      }),
    ]).start(callback);
  }, [translateValue, opacity, reduceMotion]);

  const slideOut = useCallback((callback?: () => void) => {
    if (reduceMotion) {
      translateValue.setValue(initialOffset);
      opacity.setValue(0);
      callback?.();
      return;
    }

    Animated.parallel([
      Animated.timing(translateValue, {
        toValue: initialOffset,
        duration: durations.slow,
        easing: timingPresets.easeIn,
        useNativeDriver: true,
      }),
      Animated.timing(opacity, {
        toValue: 0,
        duration: durations.normal,
        easing: timingPresets.easeIn,
        useNativeDriver: true,
      }),
    ]).start(callback);
  }, [translateValue, opacity, initialOffset, reduceMotion]);

  const transform = axis === 'x'
    ? [{ translateX: translateValue }]
    : [{ translateY: translateValue }];

  return { transform, opacity, slideIn, slideOut };
}

// Shake animation hook (for error feedback)
export function useShakeAnimation() {
  const translateX = useRef(new Animated.Value(0)).current;
  const reduceMotion = useReduceMotion();

  const shake = useCallback((callback?: () => void) => {
    if (reduceMotion) {
      callback?.();
      return;
    }

    Animated.sequence([
      Animated.timing(translateX, { toValue: -10, duration: 50, useNativeDriver: true }),
      Animated.timing(translateX, { toValue: 10, duration: 50, useNativeDriver: true }),
      Animated.timing(translateX, { toValue: -10, duration: 50, useNativeDriver: true }),
      Animated.timing(translateX, { toValue: 10, duration: 50, useNativeDriver: true }),
      Animated.timing(translateX, { toValue: 0, duration: 50, useNativeDriver: true }),
    ]).start(callback);
  }, [translateX, reduceMotion]);

  return { translateX, shake };
}

// Pulse animation hook (for loading states)
export function usePulseAnimation(
  minOpacity: number = 0.4,
  maxOpacity: number = 1,
  duration: number = 1000
) {
  const opacity = useRef(new Animated.Value(maxOpacity)).current;
  const animationRef = useRef<Animated.CompositeAnimation | null>(null);
  const reduceMotion = useReduceMotion();

  const startPulse = useCallback(() => {
    if (reduceMotion) return;

    animationRef.current = Animated.loop(
      Animated.sequence([
        Animated.timing(opacity, {
          toValue: minOpacity,
          duration: duration / 2,
          easing: timingPresets.easeInOut,
          useNativeDriver: true,
        }),
        Animated.timing(opacity, {
          toValue: maxOpacity,
          duration: duration / 2,
          easing: timingPresets.easeInOut,
          useNativeDriver: true,
        }),
      ])
    );
    animationRef.current.start();
  }, [opacity, minOpacity, maxOpacity, duration, reduceMotion]);

  const stopPulse = useCallback(() => {
    animationRef.current?.stop();
    opacity.setValue(maxOpacity);
  }, [opacity, maxOpacity]);

  useEffect(() => {
    return () => {
      animationRef.current?.stop();
    };
  }, []);

  return { opacity, startPulse, stopPulse };
}

// Rotate animation hook (for loading spinners)
export function useRotateAnimation(duration: number = 1000) {
  const rotation = useRef(new Animated.Value(0)).current;
  const animationRef = useRef<Animated.CompositeAnimation | null>(null);
  const reduceMotion = useReduceMotion();

  const startRotation = useCallback(() => {
    if (reduceMotion) return;

    rotation.setValue(0);
    animationRef.current = Animated.loop(
      Animated.timing(rotation, {
        toValue: 1,
        duration,
        easing: Easing.linear,
        useNativeDriver: true,
      })
    );
    animationRef.current.start();
  }, [rotation, duration, reduceMotion]);

  const stopRotation = useCallback(() => {
    animationRef.current?.stop();
    rotation.setValue(0);
  }, [rotation]);

  const rotate = rotation.interpolate({
    inputRange: [0, 1],
    outputRange: ['0deg', '360deg'],
  });

  useEffect(() => {
    return () => {
      animationRef.current?.stop();
    };
  }, []);

  return { rotate, startRotation, stopRotation };
}

// Staggered list animation hook
export function useStaggerAnimation(
  itemCount: number,
  staggerDelay: number = 50
) {
  const animations = useRef(
    Array.from({ length: itemCount }, () => ({
      opacity: new Animated.Value(0),
      translateY: new Animated.Value(20),
    }))
  ).current;
  const reduceMotion = useReduceMotion();

  const animateIn = useCallback((callback?: () => void) => {
    if (reduceMotion) {
      animations.forEach(({ opacity, translateY }) => {
        opacity.setValue(1);
        translateY.setValue(0);
      });
      callback?.();
      return;
    }

    const staggeredAnimations = animations.map(({ opacity, translateY }, index) =>
      Animated.delay(
        index * staggerDelay,
        Animated.parallel([
          Animated.timing(opacity, {
            toValue: 1,
            duration: durations.normal,
            useNativeDriver: true,
          }),
          Animated.timing(translateY, {
            toValue: 0,
            duration: durations.normal,
            easing: timingPresets.easeOut,
            useNativeDriver: true,
          }),
        ])
      )
    );

    Animated.parallel(staggeredAnimations).start(callback);
  }, [animations, staggerDelay, reduceMotion]);

  const reset = useCallback(() => {
    animations.forEach(({ opacity, translateY }) => {
      opacity.setValue(0);
      translateY.setValue(20);
    });
  }, [animations]);

  return { animations, animateIn, reset };
}

// Success checkmark animation
export function useSuccessAnimation() {
  const scale = useRef(new Animated.Value(0)).current;
  const opacity = useRef(new Animated.Value(0)).current;
  const reduceMotion = useReduceMotion();

  const animate = useCallback((callback?: () => void) => {
    if (reduceMotion) {
      scale.setValue(1);
      opacity.setValue(1);
      callback?.();
      return;
    }

    Animated.parallel([
      Animated.spring(scale, {
        toValue: 1,
        useNativeDriver: true,
        speed: 12,
        bounciness: 8,
      }),
      Animated.timing(opacity, {
        toValue: 1,
        duration: durations.fast,
        useNativeDriver: true,
      }),
    ]).start(callback);
  }, [scale, opacity, reduceMotion]);

  const reset = useCallback(() => {
    scale.setValue(0);
    opacity.setValue(0);
  }, [scale, opacity]);

  return { scale, opacity, animate, reset };
}

// Number counter animation
export function useCountAnimation(
  endValue: number,
  duration: number = 1000,
  startValue: number = 0
) {
  const animatedValue = useRef(new Animated.Value(startValue)).current;
  const reduceMotion = useReduceMotion();

  const animate = useCallback((callback?: () => void) => {
    if (reduceMotion) {
      animatedValue.setValue(endValue);
      callback?.();
      return;
    }

    animatedValue.setValue(startValue);
    Animated.timing(animatedValue, {
      toValue: endValue,
      duration,
      easing: timingPresets.easeOut,
      useNativeDriver: false, // Can't use native driver for text
    }).start(callback);
  }, [animatedValue, endValue, startValue, duration, reduceMotion]);

  return { animatedValue, animate };
}
