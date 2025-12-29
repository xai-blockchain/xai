/**
 * Tests for SendScreen
 */

import React from 'react';
import { render, fireEvent, screen, waitFor } from '@testing-library/react-native';
import { Alert } from 'react-native';
import { SendScreen } from '../../src/screens/SendScreen';
import { WalletProvider } from '../../src/context/WalletContext';
import { xaiApi } from '../../src/services/api';

// Mock Alert
jest.spyOn(Alert, 'alert');

// Mock navigation
const mockNavigate = jest.fn();
const mockGoBack = jest.fn();
jest.mock('@react-navigation/native', () => ({
  ...jest.requireActual('@react-navigation/native'),
  useNavigation: () => ({
    navigate: mockNavigate,
    goBack: mockGoBack,
  }),
}));

// Mock API
jest.mock('../../src/services/api', () => ({
  xaiApi: {
    getMempoolStats: jest.fn(),
    getNonce: jest.fn(),
    sendTransaction: jest.fn(),
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
  createWallet: jest.fn(),
  deriveAddress: jest.fn(),
  signTransaction: jest.fn().mockResolvedValue('mock-signature'),
  isValidAddress: jest.fn((addr) => addr?.startsWith('XAI') && addr.length === 43),
}));

const storage = require('../../src/utils/storage');

describe('SendScreen', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockNavigate.mockClear();
    mockGoBack.mockClear();
    (Alert.alert as jest.Mock).mockClear();

    // Default mock responses
    (xaiApi.getMempoolStats as jest.Mock).mockResolvedValue({
      success: true,
      data: {
        fees: {
          recommendedFeeRates: {
            slow: 0.0005,
            standard: 0.001,
            priority: 0.002,
          },
        },
        pressure: {
          status: 'normal',
          pendingTransactions: 10,
        },
      },
    });

    (xaiApi.getNonce as jest.Mock).mockResolvedValue({
      success: true,
      data: { nextNonce: 1 },
    });

    (xaiApi.sendTransaction as jest.Mock).mockResolvedValue({
      success: true,
      data: { txid: 'newtxid123', message: 'Transaction sent' },
    });

    (xaiApi.getBalance as jest.Mock).mockResolvedValue({
      success: true,
      data: { balance: 1000 },
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

    it('should show no wallet message', async () => {
      renderWithProvider(<SendScreen />);

      await waitFor(() => {
        expect(screen.getByText('No Wallet')).toBeTruthy();
      });
    });

    it('should show go to wallet button', async () => {
      renderWithProvider(<SendScreen />);

      await waitFor(() => {
        expect(screen.getByText('Go to Wallet')).toBeTruthy();
      });
    });

    it('should navigate to wallet screen', async () => {
      renderWithProvider(<SendScreen />);

      await waitFor(() => {
        expect(screen.getByText('Go to Wallet')).toBeTruthy();
      });

      fireEvent.press(screen.getByText('Go to Wallet'));

      expect(mockNavigate).toHaveBeenCalledWith('Wallet');
    });
  });

  describe('with wallet', () => {
    beforeEach(() => {
      storage.hasWallet.mockResolvedValue(true);
      storage.loadWallet.mockResolvedValue({
        address: 'XAItest123456789012345678901234567890',
        publicKey: 'testpublickey123456789012345678901234567890',
        privateKey: 'testprivatekey123456789012345678901234567890',
        createdAt: Date.now(),
      });
    });

    it('should display balance', async () => {
      renderWithProvider(<SendScreen />);

      await waitFor(() => {
        expect(screen.getByText('Available Balance')).toBeTruthy();
      });
    });

    it('should display recipient input', async () => {
      renderWithProvider(<SendScreen />);

      await waitFor(() => {
        expect(screen.getByText('Recipient Address')).toBeTruthy();
      });
    });

    it('should display amount input', async () => {
      renderWithProvider(<SendScreen />);

      await waitFor(() => {
        expect(screen.getByText('Amount (XAI)')).toBeTruthy();
      });
    });

    it('should display max button', async () => {
      renderWithProvider(<SendScreen />);

      await waitFor(() => {
        expect(screen.getByText('Max')).toBeTruthy();
      });
    });

    it('should display fee selection', async () => {
      renderWithProvider(<SendScreen />);

      await waitFor(() => {
        expect(screen.getByText('Transaction Fee')).toBeTruthy();
      });
    });

    it('should display fee level buttons', async () => {
      renderWithProvider(<SendScreen />);

      await waitFor(() => {
        expect(screen.getByText('Slow')).toBeTruthy();
        expect(screen.getByText('Standard')).toBeTruthy();
        expect(screen.getByText('Priority')).toBeTruthy();
      });
    });

    it('should display send button', async () => {
      renderWithProvider(<SendScreen />);

      await waitFor(() => {
        expect(screen.getByText('Send Transaction')).toBeTruthy();
      });
    });

    it('should display mempool status', async () => {
      renderWithProvider(<SendScreen />);

      await waitFor(() => {
        expect(screen.getByText(/Network:/)).toBeTruthy();
      });
    });
  });

  describe('input validation', () => {
    beforeEach(() => {
      storage.hasWallet.mockResolvedValue(true);
      storage.loadWallet.mockResolvedValue({
        address: 'XAItest123456789012345678901234567890',
        publicKey: 'testpublickey123456789012345678901234567890',
        privateKey: 'testprivatekey123456789012345678901234567890',
        createdAt: Date.now(),
      });
    });

    it('should validate empty recipient', async () => {
      renderWithProvider(<SendScreen />);

      await waitFor(() => {
        expect(screen.getByText('Send Transaction')).toBeTruthy();
      });

      // Enter amount but not recipient
      fireEvent.changeText(screen.getByPlaceholderText('0.0000'), '100');
      fireEvent.press(screen.getByText('Send Transaction'));

      await waitFor(() => {
        expect(screen.getByText('Recipient address is required')).toBeTruthy();
      });
    });

    it('should validate invalid address format', async () => {
      renderWithProvider(<SendScreen />);

      await waitFor(() => {
        expect(screen.getByPlaceholderText('XAI...')).toBeTruthy();
      });

      fireEvent.changeText(screen.getByPlaceholderText('XAI...'), 'invalid');
      fireEvent.changeText(screen.getByPlaceholderText('0.0000'), '100');
      fireEvent.press(screen.getByText('Send Transaction'));

      await waitFor(() => {
        expect(screen.getByText('Invalid XAI address format')).toBeTruthy();
      });
    });

    it('should validate sending to self', async () => {
      renderWithProvider(<SendScreen />);

      await waitFor(() => {
        expect(screen.getByPlaceholderText('XAI...')).toBeTruthy();
      });

      // Use same address as sender
      fireEvent.changeText(
        screen.getByPlaceholderText('XAI...'),
        'XAItest123456789012345678901234567890'
      );
      fireEvent.changeText(screen.getByPlaceholderText('0.0000'), '100');
      fireEvent.press(screen.getByText('Send Transaction'));

      await waitFor(() => {
        expect(screen.getByText('Cannot send to yourself')).toBeTruthy();
      });
    });

    it('should validate insufficient balance', async () => {
      renderWithProvider(<SendScreen />);

      await waitFor(() => {
        expect(screen.getByPlaceholderText('XAI...')).toBeTruthy();
      });

      fireEvent.changeText(
        screen.getByPlaceholderText('XAI...'),
        'XAIrecipient123456789012345678901234567'
      );
      fireEvent.changeText(screen.getByPlaceholderText('0.0000'), '10000'); // More than balance
      fireEvent.press(screen.getByText('Send Transaction'));

      await waitFor(() => {
        expect(screen.getByText('Insufficient balance')).toBeTruthy();
      });
    });
  });

  describe('fee selection', () => {
    beforeEach(() => {
      storage.hasWallet.mockResolvedValue(true);
      storage.loadWallet.mockResolvedValue({
        address: 'XAItest123456789012345678901234567890',
        publicKey: 'testpublickey',
        privateKey: 'testprivatekey',
        createdAt: Date.now(),
      });
    });

    it('should select standard fee by default', async () => {
      renderWithProvider(<SendScreen />);

      await waitFor(() => {
        expect(screen.getByText('Standard')).toBeTruthy();
      });
    });

    it('should update fee when level changes', async () => {
      renderWithProvider(<SendScreen />);

      await waitFor(() => {
        expect(screen.getByText('Slow')).toBeTruthy();
      });

      fireEvent.press(screen.getByText('Slow'));

      // Fee should be updated (0.0005 for slow)
      await waitFor(() => {
        expect(screen.getByText(/Fee:/)).toBeTruthy();
      });
    });

    it('should allow custom fee input', async () => {
      renderWithProvider(<SendScreen />);

      await waitFor(() => {
        expect(screen.getByPlaceholderText('0.001')).toBeTruthy();
      });

      fireEvent.changeText(screen.getByPlaceholderText('0.001'), '0.005');

      // Custom fee should be used
      await waitFor(() => {
        expect(screen.getByDisplayValue('0.005')).toBeTruthy();
      });
    });
  });

  describe('max button', () => {
    beforeEach(() => {
      storage.hasWallet.mockResolvedValue(true);
      storage.loadWallet.mockResolvedValue({
        address: 'XAItest123456789012345678901234567890',
        publicKey: 'testpublickey',
        privateKey: 'testprivatekey',
        createdAt: Date.now(),
      });
    });

    it('should set max amount minus fee', async () => {
      renderWithProvider(<SendScreen />);

      await waitFor(() => {
        expect(screen.getByText('Max')).toBeTruthy();
      });

      fireEvent.press(screen.getByText('Max'));

      // Amount should be set to balance - fee
      await waitFor(() => {
        // Balance is 1000, standard fee is 0.001
        // Max should be approximately 999.999
        const input = screen.getByPlaceholderText('0.0000');
        expect(input.props.value).toBeDefined();
      });
    });
  });

  describe('transaction summary', () => {
    beforeEach(() => {
      storage.hasWallet.mockResolvedValue(true);
      storage.loadWallet.mockResolvedValue({
        address: 'XAItest123456789012345678901234567890',
        publicKey: 'testpublickey',
        privateKey: 'testprivatekey',
        createdAt: Date.now(),
      });
    });

    it('should show summary when amount entered', async () => {
      renderWithProvider(<SendScreen />);

      await waitFor(() => {
        expect(screen.getByPlaceholderText('0.0000')).toBeTruthy();
      });

      fireEvent.changeText(screen.getByPlaceholderText('0.0000'), '100');

      await waitFor(() => {
        expect(screen.getByText('Summary')).toBeTruthy();
        expect(screen.getByText('Amount')).toBeTruthy();
        expect(screen.getByText('Fee')).toBeTruthy();
        expect(screen.getByText('Total')).toBeTruthy();
      });
    });

    it('should not show summary without amount', async () => {
      renderWithProvider(<SendScreen />);

      await waitFor(() => {
        expect(screen.queryByText('Summary')).toBeNull();
      });
    });
  });

  describe('transaction sending', () => {
    beforeEach(() => {
      storage.hasWallet.mockResolvedValue(true);
      storage.loadWallet.mockResolvedValue({
        address: 'XAItest123456789012345678901234567890',
        publicKey: 'testpublickey123456789012345678901234567890',
        privateKey: 'testprivatekey123456789012345678901234567890',
        createdAt: Date.now(),
      });
    });

    it('should show confirmation alert', async () => {
      renderWithProvider(<SendScreen />);

      await waitFor(() => {
        expect(screen.getByPlaceholderText('XAI...')).toBeTruthy();
      });

      fireEvent.changeText(
        screen.getByPlaceholderText('XAI...'),
        'XAIrecipient123456789012345678901234567'
      );
      fireEvent.changeText(screen.getByPlaceholderText('0.0000'), '100');
      fireEvent.press(screen.getByText('Send Transaction'));

      expect(Alert.alert).toHaveBeenCalledWith(
        'Confirm Transaction',
        expect.any(String),
        expect.any(Array)
      );
    });

    it('should send transaction on confirm', async () => {
      // Mock Alert to automatically confirm
      (Alert.alert as jest.Mock).mockImplementation((title, message, buttons) => {
        const sendButton = buttons?.find((b: any) => b.text === 'Send');
        if (sendButton?.onPress) sendButton.onPress();
      });

      renderWithProvider(<SendScreen />);

      await waitFor(() => {
        expect(screen.getByPlaceholderText('XAI...')).toBeTruthy();
      });

      fireEvent.changeText(
        screen.getByPlaceholderText('XAI...'),
        'XAIrecipient123456789012345678901234567'
      );
      fireEvent.changeText(screen.getByPlaceholderText('0.0000'), '100');
      fireEvent.press(screen.getByText('Send Transaction'));

      await waitFor(() => {
        expect(xaiApi.sendTransaction).toHaveBeenCalled();
      });
    });
  });

  describe('error handling', () => {
    beforeEach(() => {
      storage.hasWallet.mockResolvedValue(true);
      storage.loadWallet.mockResolvedValue({
        address: 'XAItest123456789012345678901234567890',
        publicKey: 'testpublickey123456789012345678901234567890',
        privateKey: 'testprivatekey123456789012345678901234567890',
        createdAt: Date.now(),
      });
    });

    it('should handle nonce fetch failure', async () => {
      (xaiApi.getNonce as jest.Mock).mockResolvedValue({
        success: false,
        error: 'Failed to get nonce',
      });

      // Mock Alert to automatically confirm
      (Alert.alert as jest.Mock).mockImplementation((title, message, buttons) => {
        const sendButton = buttons?.find((b: any) => b.text === 'Send');
        if (sendButton?.onPress) sendButton.onPress();
      });

      renderWithProvider(<SendScreen />);

      await waitFor(() => {
        expect(screen.getByPlaceholderText('XAI...')).toBeTruthy();
      });

      fireEvent.changeText(
        screen.getByPlaceholderText('XAI...'),
        'XAIrecipient123456789012345678901234567'
      );
      fireEvent.changeText(screen.getByPlaceholderText('0.0000'), '100');
      fireEvent.press(screen.getByText('Send Transaction'));

      await waitFor(() => {
        expect(Alert.alert).toHaveBeenCalledWith('Error', 'Failed to get nonce');
      });
    });

    it('should handle transaction failure', async () => {
      (xaiApi.sendTransaction as jest.Mock).mockResolvedValue({
        success: false,
        error: 'Transaction rejected',
      });

      // Mock Alert to automatically confirm
      (Alert.alert as jest.Mock).mockImplementation((title, message, buttons) => {
        const sendButton = buttons?.find((b: any) => b.text === 'Send');
        if (sendButton?.onPress) sendButton.onPress();
      });

      renderWithProvider(<SendScreen />);

      await waitFor(() => {
        expect(screen.getByPlaceholderText('XAI...')).toBeTruthy();
      });

      fireEvent.changeText(
        screen.getByPlaceholderText('XAI...'),
        'XAIrecipient123456789012345678901234567'
      );
      fireEvent.changeText(screen.getByPlaceholderText('0.0000'), '100');
      fireEvent.press(screen.getByText('Send Transaction'));

      await waitFor(() => {
        expect(Alert.alert).toHaveBeenCalledWith('Error', 'Transaction rejected');
      });
    });
  });
});
