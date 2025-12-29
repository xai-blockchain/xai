/**
 * Haptic Feedback Hook
 *
 * Provides haptic feedback for user interactions.
 * Gracefully degrades on platforms without haptic support.
 */

import { useCallback, useEffect, useRef } from 'react';
import { Platform, Vibration } from 'react-native';

// Try to import expo-haptics if available
let Haptics: any = null;
try {
  Haptics = require('expo-haptics');
} catch {
  // expo-haptics not available
}

// Haptic impact types
export type ImpactType = 'light' | 'medium' | 'heavy';
export type NotificationType = 'success' | 'warning' | 'error';

export function useHaptics() {
  const isEnabled = useRef(true);

  // Enable/disable haptics
  const setEnabled = useCallback((enabled: boolean) => {
    isEnabled.current = enabled;
  }, []);

  // Light impact - for UI selections
  const light = useCallback(async () => {
    if (!isEnabled.current) return;

    if (Haptics && Platform.OS !== 'web') {
      try {
        await Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
      } catch {
        // Fallback to vibration on failure
        if (Platform.OS === 'android') {
          Vibration.vibrate(10);
        }
      }
    } else if (Platform.OS === 'android') {
      Vibration.vibrate(10);
    }
  }, []);

  // Medium impact - for button presses
  const medium = useCallback(async () => {
    if (!isEnabled.current) return;

    if (Haptics && Platform.OS !== 'web') {
      try {
        await Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
      } catch {
        if (Platform.OS === 'android') {
          Vibration.vibrate(20);
        }
      }
    } else if (Platform.OS === 'android') {
      Vibration.vibrate(20);
    }
  }, []);

  // Heavy impact - for significant actions
  const heavy = useCallback(async () => {
    if (!isEnabled.current) return;

    if (Haptics && Platform.OS !== 'web') {
      try {
        await Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Heavy);
      } catch {
        if (Platform.OS === 'android') {
          Vibration.vibrate(30);
        }
      }
    } else if (Platform.OS === 'android') {
      Vibration.vibrate(30);
    }
  }, []);

  // Selection feedback - for picker/toggle changes
  const selection = useCallback(async () => {
    if (!isEnabled.current) return;

    if (Haptics && Platform.OS !== 'web') {
      try {
        await Haptics.selectionAsync();
      } catch {
        if (Platform.OS === 'android') {
          Vibration.vibrate(5);
        }
      }
    } else if (Platform.OS === 'android') {
      Vibration.vibrate(5);
    }
  }, []);

  // Success notification - transaction confirmed
  const success = useCallback(async () => {
    if (!isEnabled.current) return;

    if (Haptics && Platform.OS !== 'web') {
      try {
        await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
      } catch {
        if (Platform.OS === 'android') {
          Vibration.vibrate([0, 40, 60, 40]);
        }
      }
    } else if (Platform.OS === 'android') {
      Vibration.vibrate([0, 40, 60, 40]);
    }
  }, []);

  // Warning notification - pending action
  const warning = useCallback(async () => {
    if (!isEnabled.current) return;

    if (Haptics && Platform.OS !== 'web') {
      try {
        await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Warning);
      } catch {
        if (Platform.OS === 'android') {
          Vibration.vibrate([0, 50, 100, 50]);
        }
      }
    } else if (Platform.OS === 'android') {
      Vibration.vibrate([0, 50, 100, 50]);
    }
  }, []);

  // Error notification - transaction failed
  const error = useCallback(async () => {
    if (!isEnabled.current) return;

    if (Haptics && Platform.OS !== 'web') {
      try {
        await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error);
      } catch {
        if (Platform.OS === 'android') {
          Vibration.vibrate([0, 100, 50, 100, 50, 100]);
        }
      }
    } else if (Platform.OS === 'android') {
      Vibration.vibrate([0, 100, 50, 100, 50, 100]);
    }
  }, []);

  // Generic impact by type
  const impact = useCallback(async (type: ImpactType) => {
    switch (type) {
      case 'light':
        await light();
        break;
      case 'medium':
        await medium();
        break;
      case 'heavy':
        await heavy();
        break;
    }
  }, [light, medium, heavy]);

  // Generic notification by type
  const notification = useCallback(async (type: NotificationType) => {
    switch (type) {
      case 'success':
        await success();
        break;
      case 'warning':
        await warning();
        break;
      case 'error':
        await error();
        break;
    }
  }, [success, warning, error]);

  return {
    light,
    medium,
    heavy,
    selection,
    success,
    warning,
    error,
    impact,
    notification,
    setEnabled,
  };
}

// Convenience function for one-off haptic feedback
export async function triggerHaptic(
  type: ImpactType | NotificationType | 'selection'
) {
  if (Haptics && Platform.OS !== 'web') {
    try {
      switch (type) {
        case 'light':
          await Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
          break;
        case 'medium':
          await Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
          break;
        case 'heavy':
          await Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Heavy);
          break;
        case 'selection':
          await Haptics.selectionAsync();
          break;
        case 'success':
          await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
          break;
        case 'warning':
          await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Warning);
          break;
        case 'error':
          await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error);
          break;
      }
    } catch {
      // Ignore errors
    }
  } else if (Platform.OS === 'android') {
    const patterns: Record<typeof type, number | number[]> = {
      light: 10,
      medium: 20,
      heavy: 30,
      selection: 5,
      success: [0, 40, 60, 40],
      warning: [0, 50, 100, 50],
      error: [0, 100, 50, 100, 50, 100],
    };
    Vibration.vibrate(patterns[type]);
  }
}
