/**
 * Jest setup file for XAI Mobile App
 * Mocks native modules and configures testing environment
 */

import '@testing-library/jest-native/extend-expect';

// Mock expo-crypto
jest.mock('expo-crypto', () => ({
  getRandomBytesAsync: jest.fn().mockImplementation(async (size) => {
    const bytes = new Uint8Array(size);
    for (let i = 0; i < size; i++) {
      bytes[i] = Math.floor(Math.random() * 256);
    }
    return bytes;
  }),
  digestStringAsync: jest.fn().mockImplementation(async (algorithm, data) => {
    // Simple mock hash - just return a consistent fake hash
    const hash = data.split('').reduce((acc, char) => {
      return ((acc << 5) - acc + char.charCodeAt(0)) | 0;
    }, 0);
    return Math.abs(hash).toString(16).padStart(64, '0');
  }),
  CryptoDigestAlgorithm: {
    SHA256: 'SHA-256',
    SHA384: 'SHA-384',
    SHA512: 'SHA-512',
  },
}));

// Mock expo-secure-store
const secureStoreData = new Map();
jest.mock('expo-secure-store', () => ({
  setItemAsync: jest.fn().mockImplementation(async (key, value) => {
    secureStoreData.set(key, value);
  }),
  getItemAsync: jest.fn().mockImplementation(async (key) => {
    return secureStoreData.get(key) || null;
  }),
  deleteItemAsync: jest.fn().mockImplementation(async (key) => {
    secureStoreData.delete(key);
  }),
}));

// Helper to clear secure store between tests
global.clearSecureStore = () => {
  secureStoreData.clear();
};

// Mock expo-clipboard
jest.mock('expo-clipboard', () => ({
  setStringAsync: jest.fn().mockResolvedValue(true),
  getStringAsync: jest.fn().mockResolvedValue(''),
}));

// Mock @react-navigation
jest.mock('@react-navigation/native', () => {
  const actualNav = jest.requireActual('@react-navigation/native');
  return {
    ...actualNav,
    useNavigation: () => ({
      navigate: jest.fn(),
      goBack: jest.fn(),
      dispatch: jest.fn(),
    }),
    useRoute: () => ({
      params: {},
    }),
    useFocusEffect: jest.fn(),
  };
});

// Mock react-native-safe-area-context
jest.mock('react-native-safe-area-context', () => {
  const inset = { top: 0, right: 0, bottom: 0, left: 0 };
  return {
    SafeAreaProvider: ({ children }) => children,
    SafeAreaView: ({ children }) => children,
    useSafeAreaInsets: () => inset,
    useSafeAreaFrame: () => ({ x: 0, y: 0, width: 390, height: 844 }),
  };
});

// Mock react-native-qrcode-svg
jest.mock('react-native-qrcode-svg', () => {
  const { View } = require('react-native');
  return ({ value, size }) => <View testID="qr-code" />;
});

// Mock react-native-svg
jest.mock('react-native-svg', () => {
  const { View } = require('react-native');
  return {
    Svg: View,
    Circle: View,
    Rect: View,
    Path: View,
    G: View,
    Text: View,
    default: View,
  };
});

// Mock fetch globally
global.fetch = jest.fn();

// Mock console methods to reduce noise in tests
const originalError = console.error;
console.error = (...args) => {
  // Filter out known React Native warnings
  if (
    args[0]?.includes?.('Warning:') ||
    args[0]?.includes?.('An update to')
  ) {
    return;
  }
  originalError.call(console, ...args);
};

// Reset mocks before each test
beforeEach(() => {
  jest.clearAllMocks();
  global.clearSecureStore();
  global.fetch.mockReset();
});

// Clean up after all tests
afterAll(() => {
  jest.restoreAllMocks();
});
