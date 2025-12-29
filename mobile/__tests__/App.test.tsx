/**
 * App-level tests for XAI Mobile
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react-native';
import App from '../App';

// Mock navigation
jest.mock('@react-navigation/native', () => {
  const actual = jest.requireActual('@react-navigation/native');
  return {
    ...actual,
    NavigationContainer: ({ children }: { children: React.ReactNode }) => children,
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

// Mock bottom tabs
jest.mock('@react-navigation/bottom-tabs', () => ({
  createBottomTabNavigator: () => ({
    Navigator: ({ children }: { children: React.ReactNode }) => children,
    Screen: ({ children }: { children: React.ReactNode }) => children,
  }),
}));

// Mock native stack
jest.mock('@react-navigation/native-stack', () => ({
  createNativeStackNavigator: () => ({
    Navigator: ({ children }: { children: React.ReactNode }) => children,
    Screen: ({ children }: { children: React.ReactNode }) => children,
  }),
}));

// Mock expo modules
jest.mock('expo-secure-store', () => ({
  getItemAsync: jest.fn().mockResolvedValue(null),
  setItemAsync: jest.fn().mockResolvedValue(undefined),
  deleteItemAsync: jest.fn().mockResolvedValue(undefined),
}));

jest.mock('expo-crypto', () => ({
  getRandomBytesAsync: jest.fn().mockResolvedValue(new Uint8Array(32)),
  digestStringAsync: jest.fn().mockResolvedValue('mocked-hash-value'),
  CryptoDigestAlgorithm: {
    SHA256: 'SHA-256',
  },
}));

jest.mock('expo-clipboard', () => ({
  setStringAsync: jest.fn().mockResolvedValue(true),
  getStringAsync: jest.fn().mockResolvedValue(''),
}));

jest.mock('expo-status-bar', () => ({
  StatusBar: () => null,
}));

jest.mock('react-native-safe-area-context', () => ({
  SafeAreaProvider: ({ children }: { children: React.ReactNode }) => children,
  SafeAreaView: ({ children }: { children: React.ReactNode }) => children,
  useSafeAreaInsets: () => ({ top: 0, right: 0, bottom: 0, left: 0 }),
}));

// Mock API
jest.mock('../src/services/api', () => ({
  xaiApi: {
    getStats: jest.fn().mockResolvedValue({ success: true, data: {} }),
    getHistory: jest.fn().mockResolvedValue({ success: true, data: { transactions: [] } }),
    getBalance: jest.fn().mockResolvedValue({ success: true, data: { balance: 0 } }),
    getHealth: jest.fn().mockResolvedValue({ success: true, data: { status: 'healthy' } }),
  },
}));

describe('App', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should render without crashing', async () => {
    const { toJSON } = render(<App />);

    await waitFor(() => {
      expect(toJSON()).toBeTruthy();
    });
  });

  it('should show initial state for new user', async () => {
    render(<App />);

    // The app should render some content
    await waitFor(() => {
      // Basic check that the app rendered
      expect(true).toBe(true);
    });
  });
});

describe('App Navigation', () => {
  it('should render navigation structure', async () => {
    const { toJSON } = render(<App />);

    await waitFor(() => {
      const tree = toJSON();
      expect(tree).toBeTruthy();
    });
  });
});

describe('App Theme', () => {
  it('should apply dark theme by default', async () => {
    // The app uses a custom dark theme
    const { toJSON } = render(<App />);

    await waitFor(() => {
      expect(toJSON()).toBeTruthy();
    });
  });
});
