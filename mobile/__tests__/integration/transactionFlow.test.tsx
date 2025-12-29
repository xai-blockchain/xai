/**
 * Integration tests for transaction sending flow
 */

import React from 'react';
import { render, fireEvent, screen, waitFor } from '@testing-library/react-native';
import { Alert } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { WalletProvider } from '../../src/context/WalletContext';
import { SendScreen } from '../../src/screens/SendScreen';
import { HomeScreen } from '../../src/screens/HomeScreen';
import { xaiApi } from '../../src/services/api';

// Mock Alert
jest.spyOn(Alert, 'alert');

// Mock API
jest.mock('../../src/services/api', () => ({
  xaiApi: {
    getStats: jest.fn(),
    getHistory: jest.fn(),
    getBalance: jest.fn(),
    getHealth: jest.fn(),
    getMempoolStats: jest.fn(),
    getNonce: jest.fn(),
    sendTransaction: jest.fn(),
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
  signTransaction: jest.fn().mockResolvedValue('valid-signature-hex'),
  isValidAddress: jest.fn((addr) => addr?.startsWith('XAI') && addr.length === 43),
}));

const storage = require('../../src/utils/storage');
const crypto = require('../../src/utils/crypto');

const Stack = createNativeStackNavigator();

function TestApp() {
  return (
    <WalletProvider>
      <NavigationContainer>
        <Stack.Navigator>
          <Stack.Screen name="Home" component={HomeScreen} />
          <Stack.Screen name="Send" component={SendScreen} />
        </Stack.Navigator>
      </NavigationContainer>
    </WalletProvider>
  );
}

describe('Transaction Flow Integration', () => {
  const walletData = {
    address: 'XAIsender123456789012345678901234567890',
    publicKey: 'senderpublickey12345678901234567890123',
    privateKey: 'senderprivatekey1234567890123456789012',
    createdAt: Date.now(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
    (Alert.alert as jest.Mock).mockClear();

    // Setup wallet
    storage.hasWallet.mockResolvedValue(true);
    storage.loadWallet.mockResolvedValue(walletData);

    // Default API responses
    (xaiApi.getStats as jest.Mock).mockResolvedValue({
      success: true,
      data: {
        chainHeight: 1000,
        difficulty: 10000,
        totalSupply: 1000000,
        pendingTransactionsCount: 5,
        peers: 3,
      },
    });

    (xaiApi.getHistory as jest.Mock).mockResolvedValue({
      success: true,
      data: { transactions: [], total: 0 },
    });

    (xaiApi.getBalance as jest.Mock).mockResolvedValue({
      success: true,
      data: { balance: 1000 },
    });

    (xaiApi.getHealth as jest.Mock).mockResolvedValue({
      success: true,
      data: { status: 'healthy' },
    });

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
      data: { nextNonce: 5 },
    });

    (xaiApi.sendTransaction as jest.Mock).mockResolvedValue({
      success: true,
      data: { txid: 'newtxid123456789', message: 'Transaction accepted' },
    });
  });

  describe('complete transaction flow', () => {
    it('should navigate to send screen and display form', async () => {
      render(<TestApp />);

      await waitFor(() => {
        expect(screen.getByText('Send')).toBeTruthy();
      });

      fireEvent.press(screen.getByText('Send'));

      await waitFor(() => {
        expect(screen.getByText('Available Balance')).toBeTruthy();
        expect(screen.getByText('Recipient Address')).toBeTruthy();
        expect(screen.getByText('Amount (XAI)')).toBeTruthy();
      });
    });

    it('should fill form and send transaction', async () => {
      // Mock Alert to auto-confirm
      (Alert.alert as jest.Mock).mockImplementation((title, message, buttons) => {
        const sendButton = buttons?.find((b: any) => b.text === 'Send');
        if (sendButton?.onPress) sendButton.onPress();
        const okButton = buttons?.find((b: any) => b.text === 'OK');
        if (okButton?.onPress) okButton.onPress();
      });

      render(<TestApp />);

      // Navigate to send
      await waitFor(() => {
        fireEvent.press(screen.getByText('Send'));
      });

      await waitFor(() => {
        expect(screen.getByPlaceholderText('XAI...')).toBeTruthy();
      });

      // Fill form
      const validRecipient = 'XAIrecipient123456789012345678901234567';
      fireEvent.changeText(screen.getByPlaceholderText('XAI...'), validRecipient);
      fireEvent.changeText(screen.getByPlaceholderText('0.0000'), '100');

      // Submit
      fireEvent.press(screen.getByText('Send Transaction'));

      // Verify transaction was sent
      await waitFor(() => {
        expect(xaiApi.getNonce).toHaveBeenCalledWith(walletData.address);
      });

      await waitFor(() => {
        expect(crypto.signTransaction).toHaveBeenCalledWith(
          expect.objectContaining({
            sender: walletData.address,
            recipient: validRecipient,
            amount: 100,
          }),
          walletData.privateKey
        );
      });

      await waitFor(() => {
        expect(xaiApi.sendTransaction).toHaveBeenCalledWith(
          expect.objectContaining({
            sender: walletData.address,
            recipient: validRecipient,
            amount: 100,
            signature: 'valid-signature-hex',
            publicKey: walletData.publicKey,
          })
        );
      });
    });

    it('should display summary before sending', async () => {
      render(<TestApp />);

      await waitFor(() => {
        fireEvent.press(screen.getByText('Send'));
      });

      await waitFor(() => {
        fireEvent.changeText(screen.getByPlaceholderText('0.0000'), '500');
      });

      await waitFor(() => {
        expect(screen.getByText('Summary')).toBeTruthy();
        expect(screen.getByText('Amount')).toBeTruthy();
        expect(screen.getByText('Fee')).toBeTruthy();
        expect(screen.getByText('Total')).toBeTruthy();
      });
    });
  });

  describe('fee selection', () => {
    it('should switch between fee levels', async () => {
      render(<TestApp />);

      await waitFor(() => {
        fireEvent.press(screen.getByText('Send'));
      });

      await waitFor(() => {
        expect(screen.getByText('Slow')).toBeTruthy();
        expect(screen.getByText('Standard')).toBeTruthy();
        expect(screen.getByText('Priority')).toBeTruthy();
      });

      // Switch to slow
      fireEvent.press(screen.getByText('Slow'));

      // Switch to priority
      fireEvent.press(screen.getByText('Priority'));

      // Should update fee display
      await waitFor(() => {
        expect(screen.getByText(/Fee:/)).toBeTruthy();
      });
    });

    it('should use custom fee when entered', async () => {
      render(<TestApp />);

      await waitFor(() => {
        fireEvent.press(screen.getByText('Send'));
      });

      await waitFor(() => {
        fireEvent.changeText(screen.getByPlaceholderText('0.001'), '0.005');
      });

      // Fill rest of form
      await waitFor(() => {
        fireEvent.changeText(
          screen.getByPlaceholderText('XAI...'),
          'XAIrecipient123456789012345678901234567'
        );
        fireEvent.changeText(screen.getByPlaceholderText('0.0000'), '100');
      });

      // Mock confirmation
      (Alert.alert as jest.Mock).mockImplementation((title, message, buttons) => {
        const sendButton = buttons?.find((b: any) => b.text === 'Send');
        if (sendButton?.onPress) sendButton.onPress();
        const okButton = buttons?.find((b: any) => b.text === 'OK');
        if (okButton?.onPress) okButton.onPress();
      });

      fireEvent.press(screen.getByText('Send Transaction'));

      await waitFor(() => {
        expect(xaiApi.sendTransaction).toHaveBeenCalledWith(
          expect.objectContaining({
            fee: 0.005,
          })
        );
      });
    });
  });

  describe('validation errors', () => {
    it('should show error for empty recipient', async () => {
      render(<TestApp />);

      await waitFor(() => {
        fireEvent.press(screen.getByText('Send'));
      });

      await waitFor(() => {
        fireEvent.changeText(screen.getByPlaceholderText('0.0000'), '100');
      });

      fireEvent.press(screen.getByText('Send Transaction'));

      await waitFor(() => {
        expect(screen.getByText('Recipient address is required')).toBeTruthy();
      });
    });

    it('should show error for invalid address', async () => {
      render(<TestApp />);

      await waitFor(() => {
        fireEvent.press(screen.getByText('Send'));
      });

      await waitFor(() => {
        fireEvent.changeText(screen.getByPlaceholderText('XAI...'), 'invalid');
        fireEvent.changeText(screen.getByPlaceholderText('0.0000'), '100');
      });

      fireEvent.press(screen.getByText('Send Transaction'));

      await waitFor(() => {
        expect(screen.getByText('Invalid XAI address format')).toBeTruthy();
      });
    });

    it('should show error for insufficient balance', async () => {
      render(<TestApp />);

      await waitFor(() => {
        fireEvent.press(screen.getByText('Send'));
      });

      await waitFor(() => {
        fireEvent.changeText(
          screen.getByPlaceholderText('XAI...'),
          'XAIrecipient123456789012345678901234567'
        );
        fireEvent.changeText(screen.getByPlaceholderText('0.0000'), '2000'); // More than 1000 balance
      });

      fireEvent.press(screen.getByText('Send Transaction'));

      await waitFor(() => {
        expect(screen.getByText('Insufficient balance')).toBeTruthy();
      });
    });

    it('should show error for sending to self', async () => {
      render(<TestApp />);

      await waitFor(() => {
        fireEvent.press(screen.getByText('Send'));
      });

      await waitFor(() => {
        // Use sender's own address
        fireEvent.changeText(
          screen.getByPlaceholderText('XAI...'),
          walletData.address
        );
        fireEvent.changeText(screen.getByPlaceholderText('0.0000'), '100');
      });

      fireEvent.press(screen.getByText('Send Transaction'));

      await waitFor(() => {
        expect(screen.getByText('Cannot send to yourself')).toBeTruthy();
      });
    });
  });

  describe('max amount button', () => {
    it('should set max amount minus fee', async () => {
      render(<TestApp />);

      await waitFor(() => {
        fireEvent.press(screen.getByText('Send'));
      });

      await waitFor(() => {
        expect(screen.getByText('Max')).toBeTruthy();
      });

      fireEvent.press(screen.getByText('Max'));

      // Balance is 1000, standard fee is 0.001
      // Max should be 999.999
      await waitFor(() => {
        const amountInput = screen.getByPlaceholderText('0.0000');
        expect(parseFloat(amountInput.props.value)).toBeCloseTo(999.999, 2);
      });
    });
  });

  describe('network errors', () => {
    it('should handle nonce fetch failure', async () => {
      (xaiApi.getNonce as jest.Mock).mockResolvedValue({
        success: false,
        error: 'Network error',
      });

      // Auto-confirm
      (Alert.alert as jest.Mock).mockImplementation((title, message, buttons) => {
        const sendButton = buttons?.find((b: any) => b.text === 'Send');
        if (sendButton?.onPress) sendButton.onPress();
      });

      render(<TestApp />);

      await waitFor(() => {
        fireEvent.press(screen.getByText('Send'));
      });

      await waitFor(() => {
        fireEvent.changeText(
          screen.getByPlaceholderText('XAI...'),
          'XAIrecipient123456789012345678901234567'
        );
        fireEvent.changeText(screen.getByPlaceholderText('0.0000'), '100');
      });

      fireEvent.press(screen.getByText('Send Transaction'));

      await waitFor(() => {
        expect(Alert.alert).toHaveBeenCalledWith('Error', 'Failed to get nonce');
      });
    });

    it('should handle transaction rejection', async () => {
      (xaiApi.sendTransaction as jest.Mock).mockResolvedValue({
        success: false,
        error: 'Insufficient funds',
      });

      // Auto-confirm
      (Alert.alert as jest.Mock).mockImplementation((title, message, buttons) => {
        const sendButton = buttons?.find((b: any) => b.text === 'Send');
        if (sendButton?.onPress) sendButton.onPress();
      });

      render(<TestApp />);

      await waitFor(() => {
        fireEvent.press(screen.getByText('Send'));
      });

      await waitFor(() => {
        fireEvent.changeText(
          screen.getByPlaceholderText('XAI...'),
          'XAIrecipient123456789012345678901234567'
        );
        fireEvent.changeText(screen.getByPlaceholderText('0.0000'), '100');
      });

      fireEvent.press(screen.getByText('Send Transaction'));

      await waitFor(() => {
        expect(Alert.alert).toHaveBeenCalledWith('Error', 'Insufficient funds');
      });
    });
  });

  describe('successful transaction', () => {
    it('should show success alert with txid', async () => {
      // Track Alert calls
      const alertCalls: any[] = [];
      (Alert.alert as jest.Mock).mockImplementation((title, message, buttons) => {
        alertCalls.push({ title, message, buttons });
        const sendButton = buttons?.find((b: any) => b.text === 'Send');
        if (sendButton?.onPress) sendButton.onPress();
        const okButton = buttons?.find((b: any) => b.text === 'OK');
        if (okButton?.onPress) okButton.onPress();
      });

      render(<TestApp />);

      await waitFor(() => {
        fireEvent.press(screen.getByText('Send'));
      });

      await waitFor(() => {
        fireEvent.changeText(
          screen.getByPlaceholderText('XAI...'),
          'XAIrecipient123456789012345678901234567'
        );
        fireEvent.changeText(screen.getByPlaceholderText('0.0000'), '100');
      });

      fireEvent.press(screen.getByText('Send Transaction'));

      await waitFor(() => {
        const successCall = alertCalls.find((c) => c.title === 'Success');
        expect(successCall).toBeDefined();
        expect(successCall.message).toContain('newtxid123456789');
      });
    });

    it('should refresh balance after successful send', async () => {
      // Auto-confirm and OK
      (Alert.alert as jest.Mock).mockImplementation((title, message, buttons) => {
        const sendButton = buttons?.find((b: any) => b.text === 'Send');
        if (sendButton?.onPress) sendButton.onPress();
        const okButton = buttons?.find((b: any) => b.text === 'OK');
        if (okButton?.onPress) okButton.onPress();
      });

      render(<TestApp />);

      await waitFor(() => {
        fireEvent.press(screen.getByText('Send'));
      });

      await waitFor(() => {
        fireEvent.changeText(
          screen.getByPlaceholderText('XAI...'),
          'XAIrecipient123456789012345678901234567'
        );
        fireEvent.changeText(screen.getByPlaceholderText('0.0000'), '100');
      });

      const initialBalanceCalls = (xaiApi.getBalance as jest.Mock).mock.calls.length;

      fireEvent.press(screen.getByText('Send Transaction'));

      await waitFor(() => {
        // Balance should be refreshed after successful send
        expect((xaiApi.getBalance as jest.Mock).mock.calls.length).toBeGreaterThan(
          initialBalanceCalls
        );
      });
    });
  });

  describe('mempool status', () => {
    it('should display mempool pressure', async () => {
      render(<TestApp />);

      await waitFor(() => {
        fireEvent.press(screen.getByText('Send'));
      });

      await waitFor(() => {
        expect(screen.getByText(/Network:/)).toBeTruthy();
        expect(screen.getByText(/normal/)).toBeTruthy();
      });
    });

    it('should show pending transaction count', async () => {
      render(<TestApp />);

      await waitFor(() => {
        fireEvent.press(screen.getByText('Send'));
      });

      await waitFor(() => {
        expect(screen.getByText(/10 pending/)).toBeTruthy();
      });
    });
  });
});
