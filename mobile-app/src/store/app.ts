import { create } from 'zustand';
import { AppSettings, BiometricConfig } from '@/types';
import { Storage } from '@/utils/storage';
import { STORAGE_KEYS, API_CONFIG, SECURITY } from '@/constants';
import BiometricService from '@/services/biometric';
import APIService from '@/services/api';
import WebSocketService from '@/services/websocket';

interface AppState {
  settings: AppSettings;
  biometricConfig: BiometricConfig;
  isLocked: boolean;
  lastActivity: number;
  isInitialized: boolean;

  // Actions
  initialize: () => Promise<void>;
  updateSettings: (settings: Partial<AppSettings>) => Promise<void>;
  enableBiometric: () => Promise<{ success: boolean; error?: string }>;
  disableBiometric: () => Promise<void>;
  lockApp: () => void;
  unlockApp: () => void;
  updateActivity: () => void;
  checkSession: () => boolean;
}

const defaultSettings: AppSettings = {
  biometricEnabled: false,
  sessionTimeout: SECURITY.SESSION_TIMEOUT,
  autoLockEnabled: true,
  apiEndpoint: API_CONFIG.DEFAULT_ENDPOINT,
  wsEndpoint: API_CONFIG.DEFAULT_WS_ENDPOINT,
  lightClientMode: true,
  pushNotificationsEnabled: false,
  language: 'en',
  currency: 'USD',
  theme: 'light',
};

export const useAppStore = create<AppState>((set, get) => ({
  settings: defaultSettings,
  biometricConfig: {
    enabled: false,
  },
  isLocked: false,
  lastActivity: Date.now(),
  isInitialized: false,

  initialize: async () => {
    try {
      // Load settings
      const storedSettings = await Storage.get<AppSettings>(STORAGE_KEYS.SETTINGS);
      const settings = { ...defaultSettings, ...storedSettings };

      // Load biometric config
      const biometricConfig = await Storage.get<BiometricConfig>(STORAGE_KEYS.BIOMETRIC_CONFIG);

      // Check biometric availability
      const { available, biometryType } = await BiometricService.isAvailable();

      set({
        settings,
        biometricConfig: biometricConfig || { enabled: false },
        isInitialized: true,
        lastActivity: Date.now(),
      });

      // Update API endpoints
      APIService.setBaseURL(settings.apiEndpoint);
      WebSocketService.setURL(settings.wsEndpoint);

      // Check if session is still valid
      const sessionActive = await Storage.get<boolean>(STORAGE_KEYS.SESSION_ACTIVE);
      if (sessionActive && settings.autoLockEnabled) {
        set({ isLocked: true });
      }
    } catch (error) {
      console.error('Failed to initialize app:', error);
      set({ isInitialized: true }); // Set initialized anyway to avoid blocking
    }
  },

  updateSettings: async (newSettings: Partial<AppSettings>) => {
    const { settings } = get();
    const updated = { ...settings, ...newSettings };

    set({ settings: updated });
    await Storage.set(STORAGE_KEYS.SETTINGS, updated);

    // Update API endpoints if changed
    if (newSettings.apiEndpoint) {
      APIService.setBaseURL(newSettings.apiEndpoint);
    }
    if (newSettings.wsEndpoint) {
      WebSocketService.setURL(newSettings.wsEndpoint);
    }
  },

  enableBiometric: async () => {
    try {
      const { available, biometryType } = await BiometricService.isAvailable();

      if (!available) {
        return {
          success: false,
          error: 'Biometric authentication is not available on this device',
        };
      }

      // Authenticate to confirm
      const authenticated = await BiometricService.authenticate('Enable biometric authentication');

      if (!authenticated) {
        return { success: false, error: 'Authentication failed' };
      }

      // Create keys
      const keysCreated = await BiometricService.createKeys();

      if (!keysCreated) {
        return { success: false, error: 'Failed to create biometric keys' };
      }

      const config: BiometricConfig = {
        enabled: true,
        biometryType,
      };

      set({ biometricConfig: config });
      await Storage.set(STORAGE_KEYS.BIOMETRIC_CONFIG, config);
      await get().updateSettings({ biometricEnabled: true });

      return { success: true };
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : 'Failed to enable biometric';
      return { success: false, error: errorMsg };
    }
  },

  disableBiometric: async () => {
    await BiometricService.deleteKeys();

    const config: BiometricConfig = { enabled: false };

    set({ biometricConfig: config });
    await Storage.set(STORAGE_KEYS.BIOMETRIC_CONFIG, config);
    await get().updateSettings({ biometricEnabled: false });
  },

  lockApp: () => {
    set({ isLocked: true });
    Storage.set(STORAGE_KEYS.SESSION_ACTIVE, false);
  },

  unlockApp: () => {
    set({ isLocked: false, lastActivity: Date.now() });
    Storage.set(STORAGE_KEYS.SESSION_ACTIVE, true);
  },

  updateActivity: () => {
    set({ lastActivity: Date.now() });
  },

  checkSession: () => {
    const { lastActivity, settings, isLocked } = get();

    if (isLocked) return false;

    if (!settings.autoLockEnabled) return true;

    const now = Date.now();
    const elapsed = now - lastActivity;

    if (elapsed > settings.sessionTimeout) {
      get().lockApp();
      return false;
    }

    return true;
  },
}));
