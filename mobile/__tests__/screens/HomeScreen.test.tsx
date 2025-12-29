/**
 * Tests for HomeScreen
 */

import React from 'react';
import { render, fireEvent, screen, waitFor, act } from '@testing-library/react-native';
import { HomeScreen } from '../../src/screens/HomeScreen';
import { WalletProvider } from '../../src/context/WalletContext';
import { xaiApi } from '../../src/services/api';

// Mock navigation
const mockNavigate = jest.fn();
jest.mock('@react-navigation/native', () => ({
  ...jest.requireActual('@react-navigation/native'),
  useNavigation: () => ({
    navigate: mockNavigate,
    goBack: jest.fn(),
  }),
}));

// Mock API
jest.mock('../../src/services/api', () => ({
  xaiApi: {
    getStats: jest.fn(),
    getHistory: jest.fn(),
    getBalance: jest.fn(),
    getHealth: jest.fn(),
  },
}));

// Mock storage
jest.mock('../../src/utils/storage', () => ({
  loadWallet: jest.fn(),
  hasWallet: jest.fn(),
  saveWallet: jest.fn(),
  deleteWallet: jest.fn(),
}));

// Mock crypto
jest.mock('../../src/utils/crypto', () => ({
  createWallet: jest.fn().mockResolvedValue({
    address: 'XAItest123456789012345678901234567890',
    publicKey: 'pubkey',
    privateKey: 'privkey',
  }),
  deriveAddress: jest.fn(),
}));

const storage = require('../../src/utils/storage');

describe('HomeScreen', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockNavigate.mockClear();

    // Default mock responses
    (xaiApi.getStats as jest.Mock).mockResolvedValue({
      success: true,
      data: {
        chainHeight: 5000,
        difficulty: 100000,
        totalSupply: 1000000,
        pendingTransactionsCount: 10,
        latestBlockHash: 'hash123',
        peers: 5,
        isMining: true,
        nodeUptime: 3600,
      },
    });

    (xaiApi.getHistory as jest.Mock).mockResolvedValue({
      success: true,
      data: {
        transactions: [],
        total: 0,
      },
    });

    (xaiApi.getBalance as jest.Mock).mockResolvedValue({
      success: true,
      data: { balance: 100 },
    });

    (xaiApi.getHealth as jest.Mock).mockResolvedValue({
      success: true,
      data: { status: 'healthy' },
    });
  });

  const renderWithProvider = (component: React.ReactElement) => {
    return render(<WalletProvider>{component}</WalletProvider>);
  };

  describe('no wallet state', () => {
    beforeEach(() => {
      storage.hasWallet.mockResolvedValue(false);
      storage.loadWallet.mockResolvedValue(null);
    });

    it('should show welcome message when no wallet', async () => {
      renderWithProvider(<HomeScreen />);

      await waitFor(() => {
        expect(screen.getByText('Welcome to XAI')).toBeTruthy();
      });
    });

    it('should show create wallet button', async () => {
      renderWithProvider(<HomeScreen />);

      await waitFor(() => {
        expect(screen.getByText('Create Wallet')).toBeTruthy();
      });
    });

    it('should show import wallet button', async () => {
      renderWithProvider(<HomeScreen />);

      await waitFor(() => {
        expect(screen.getByText('Import Wallet')).toBeTruthy();
      });
    });

    it('should navigate to wallet screen on create wallet press', async () => {
      renderWithProvider(<HomeScreen />);

      await waitFor(() => {
        expect(screen.getByText('Create Wallet')).toBeTruthy();
      });

      fireEvent.press(screen.getByText('Create Wallet'));

      expect(mockNavigate).toHaveBeenCalledWith('Wallet');
    });

    it('should navigate to wallet screen on import wallet press', async () => {
      renderWithProvider(<HomeScreen />);

      await waitFor(() => {
        expect(screen.getByText('Import Wallet')).toBeTruthy();
      });

      fireEvent.press(screen.getByText('Import Wallet'));

      expect(mockNavigate).toHaveBeenCalledWith('Wallet');
    });
  });

  describe('with wallet', () => {
    beforeEach(() => {
      storage.hasWallet.mockResolvedValue(true);
      storage.loadWallet.mockResolvedValue({
        address: 'XAItest123456789012345678901234567890',
        publicKey: 'pubkey',
        privateKey: 'privkey',
        createdAt: Date.now(),
      });
    });

    it('should display balance', async () => {
      renderWithProvider(<HomeScreen />);

      await waitFor(() => {
        expect(screen.getByText('Total Balance')).toBeTruthy();
      });
    });

    it('should display send button', async () => {
      renderWithProvider(<HomeScreen />);

      await waitFor(() => {
        expect(screen.getByText('Send')).toBeTruthy();
      });
    });

    it('should display receive button', async () => {
      renderWithProvider(<HomeScreen />);

      await waitFor(() => {
        expect(screen.getByText('Receive')).toBeTruthy();
      });
    });

    it('should navigate to send screen on send press', async () => {
      renderWithProvider(<HomeScreen />);

      await waitFor(() => {
        expect(screen.getByText('Send')).toBeTruthy();
      });

      fireEvent.press(screen.getByText('Send'));

      expect(mockNavigate).toHaveBeenCalledWith('Send');
    });

    it('should display network stats', async () => {
      renderWithProvider(<HomeScreen />);

      await waitFor(() => {
        expect(screen.getByText('Network')).toBeTruthy();
      });
    });

    it('should display blocks stat', async () => {
      renderWithProvider(<HomeScreen />);

      await waitFor(() => {
        expect(screen.getByText('Blocks')).toBeTruthy();
      });
    });

    it('should display peers stat', async () => {
      renderWithProvider(<HomeScreen />);

      await waitFor(() => {
        expect(screen.getByText('Peers')).toBeTruthy();
      });
    });

    it('should display recent activity section', async () => {
      renderWithProvider(<HomeScreen />);

      await waitFor(() => {
        expect(screen.getByText('Recent Activity')).toBeTruthy();
      });
    });

    it('should show empty transactions message', async () => {
      renderWithProvider(<HomeScreen />);

      await waitFor(() => {
        expect(screen.getByText('No transactions yet')).toBeTruthy();
      });
    });
  });

  describe('connection status', () => {
    beforeEach(() => {
      storage.hasWallet.mockResolvedValue(true);
      storage.loadWallet.mockResolvedValue({
        address: 'XAItest123456789012345678901234567890',
        publicKey: 'pubkey',
        privateKey: 'privkey',
        createdAt: Date.now(),
      });
    });

    it('should show connected status when healthy', async () => {
      (xaiApi.getHealth as jest.Mock).mockResolvedValue({
        success: true,
        data: { status: 'healthy' },
      });

      renderWithProvider(<HomeScreen />);

      await waitFor(() => {
        expect(screen.getByText('Connected')).toBeTruthy();
      });
    });

    it('should show disconnected status on error', async () => {
      (xaiApi.getHealth as jest.Mock).mockResolvedValue({
        success: false,
        error: 'Connection failed',
      });

      renderWithProvider(<HomeScreen />);

      await waitFor(() => {
        expect(screen.getByText('Disconnected')).toBeTruthy();
      });
    });
  });

  describe('with transactions', () => {
    beforeEach(() => {
      storage.hasWallet.mockResolvedValue(true);
      storage.loadWallet.mockResolvedValue({
        address: 'XAItest123456789012345678901234567890',
        publicKey: 'pubkey',
        privateKey: 'privkey',
        createdAt: Date.now(),
      });

      (xaiApi.getHistory as jest.Mock).mockResolvedValue({
        success: true,
        data: {
          transactions: [
            {
              txid: 'tx1',
              sender: 'XAItest123456789012345678901234567890',
              recipient: 'XAIother123456789012345678901234567890',
              amount: 50,
              fee: 0.001,
              timestamp: 1700000000,
              nonce: 1,
              status: 'confirmed',
            },
          ],
          total: 1,
        },
      });
    });

    it('should display transaction items', async () => {
      renderWithProvider(<HomeScreen />);

      await waitFor(() => {
        expect(screen.getByText('Sent')).toBeTruthy();
      });
    });

    it('should show view all transactions button', async () => {
      renderWithProvider(<HomeScreen />);

      await waitFor(() => {
        expect(screen.getByText('View All Transactions')).toBeTruthy();
      });
    });
  });

  describe('loading state', () => {
    beforeEach(() => {
      storage.hasWallet.mockResolvedValue(true);
      storage.loadWallet.mockResolvedValue({
        address: 'XAItest123456789012345678901234567890',
        publicKey: 'pubkey',
        privateKey: 'privkey',
        createdAt: Date.now(),
      });
    });

    it('should show loading text initially', async () => {
      (xaiApi.getHistory as jest.Mock).mockImplementation(
        () => new Promise(() => {}) // Never resolves
      );

      renderWithProvider(<HomeScreen />);

      await waitFor(() => {
        expect(screen.getByText('Loading...')).toBeTruthy();
      });
    });
  });

  describe('error handling', () => {
    beforeEach(() => {
      storage.hasWallet.mockResolvedValue(true);
      storage.loadWallet.mockResolvedValue({
        address: 'XAItest123456789012345678901234567890',
        publicKey: 'pubkey',
        privateKey: 'privkey',
        createdAt: Date.now(),
      });
    });

    it('should handle stats fetch failure gracefully', async () => {
      (xaiApi.getStats as jest.Mock).mockResolvedValue({
        success: false,
        error: 'Failed to fetch',
      });

      renderWithProvider(<HomeScreen />);

      // Should still render without crashing
      await waitFor(() => {
        expect(screen.getByText('Total Balance')).toBeTruthy();
      });
    });

    it('should handle history fetch failure gracefully', async () => {
      (xaiApi.getHistory as jest.Mock).mockRejectedValue(new Error('Network error'));

      renderWithProvider(<HomeScreen />);

      // Should still render without crashing
      await waitFor(() => {
        expect(screen.getByText('Recent Activity')).toBeTruthy();
      });
    });
  });
});
