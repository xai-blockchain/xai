/**
 * Tests for WalletScreen
 */

import React from 'react';
import { render, fireEvent, screen, waitFor, act } from '@testing-library/react-native';
import { Alert } from 'react-native';
import { WalletScreen } from '../../src/screens/WalletScreen';
import { WalletProvider } from '../../src/context/WalletContext';
import { xaiApi } from '../../src/services/api';

// Mock Alert
jest.spyOn(Alert, 'alert');

// Mock Clipboard
jest.mock('expo-clipboard', () => ({
  setStringAsync: jest.fn().mockResolvedValue(true),
}));

// Mock API
jest.mock('../../src/services/api', () => ({
  xaiApi: {
    getHistory: jest.fn(),
    getBalance: jest.fn(),
    getHealth: jest.fn(),
    claimFaucet: jest.fn(),
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
    publicKey: 'testpublickey123456789012345678901234567890',
    privateKey: 'testprivatekey123456789012345678901234567890',
  }),
  deriveAddress: jest.fn().mockResolvedValue('XAIimported123456789012345678901234567'),
}));

const storage = require('../../src/utils/storage');
const crypto = require('../../src/utils/crypto');
const Clipboard = require('expo-clipboard');

describe('WalletScreen', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (Alert.alert as jest.Mock).mockClear();

    // Default mock responses
    (xaiApi.getHistory as jest.Mock).mockResolvedValue({
      success: true,
      data: { transactions: [], total: 0 },
    });

    (xaiApi.getBalance as jest.Mock).mockResolvedValue({
      success: true,
      data: { balance: 100 },
    });

    (xaiApi.getHealth as jest.Mock).mockResolvedValue({
      success: true,
      data: { status: 'healthy' },
    });

    (xaiApi.claimFaucet as jest.Mock).mockResolvedValue({
      success: true,
      data: { amount: 100, message: 'Tokens sent!' },
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

    it('should show wallet title', async () => {
      renderWithProvider(<WalletScreen />);

      await waitFor(() => {
        expect(screen.getByText('XAI Wallet')).toBeTruthy();
      });
    });

    it('should show create new wallet button', async () => {
      renderWithProvider(<WalletScreen />);

      await waitFor(() => {
        expect(screen.getByText('Create New Wallet')).toBeTruthy();
      });
    });

    it('should show import wallet button', async () => {
      renderWithProvider(<WalletScreen />);

      await waitFor(() => {
        expect(screen.getByText('Import Existing Wallet')).toBeTruthy();
      });
    });
  });

  describe('create wallet flow', () => {
    beforeEach(() => {
      storage.hasWallet.mockResolvedValue(false);
      storage.loadWallet.mockResolvedValue(null);
    });

    it('should show create wallet view when button pressed', async () => {
      renderWithProvider(<WalletScreen />);

      await waitFor(() => {
        expect(screen.getByText('Create New Wallet')).toBeTruthy();
      });

      fireEvent.press(screen.getByText('Create New Wallet'));

      await waitFor(() => {
        expect(screen.getByText('Create New Wallet')).toBeTruthy();
      });
    });

    it('should show cancel button in create view', async () => {
      renderWithProvider(<WalletScreen />);

      await waitFor(() => {
        expect(screen.getByText('Create New Wallet')).toBeTruthy();
      });

      fireEvent.press(screen.getByText('Create New Wallet'));

      await waitFor(() => {
        expect(screen.getByText('Cancel')).toBeTruthy();
      });
    });

    it('should create wallet when button pressed', async () => {
      storage.saveWallet.mockResolvedValue(undefined);

      renderWithProvider(<WalletScreen />);

      await waitFor(() => {
        expect(screen.getByText('Create New Wallet')).toBeTruthy();
      });

      fireEvent.press(screen.getByText('Create New Wallet'));

      await waitFor(() => {
        // In create view, there's another Create Wallet button
        const buttons = screen.getAllByText('Create Wallet');
        fireEvent.press(buttons[0]);
      });

      await waitFor(() => {
        expect(crypto.createWallet).toHaveBeenCalled();
      });
    });
  });

  describe('import wallet flow', () => {
    beforeEach(() => {
      storage.hasWallet.mockResolvedValue(false);
      storage.loadWallet.mockResolvedValue(null);
    });

    it('should show import wallet view when button pressed', async () => {
      renderWithProvider(<WalletScreen />);

      await waitFor(() => {
        expect(screen.getByText('Import Existing Wallet')).toBeTruthy();
      });

      fireEvent.press(screen.getByText('Import Existing Wallet'));

      await waitFor(() => {
        expect(screen.getByText('Import Wallet')).toBeTruthy();
      });
    });

    it('should show private key input', async () => {
      renderWithProvider(<WalletScreen />);

      await waitFor(() => {
        expect(screen.getByText('Import Existing Wallet')).toBeTruthy();
      });

      fireEvent.press(screen.getByText('Import Existing Wallet'));

      await waitFor(() => {
        expect(screen.getByText('Private Key')).toBeTruthy();
      });
    });

    it('should show error when importing with empty key', async () => {
      renderWithProvider(<WalletScreen />);

      await waitFor(() => {
        fireEvent.press(screen.getByText('Import Existing Wallet'));
      });

      await waitFor(() => {
        fireEvent.press(screen.getByText('Import'));
      });

      expect(Alert.alert).toHaveBeenCalledWith('Error', 'Please enter a private key');
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
      renderWithProvider(<WalletScreen />);

      await waitFor(() => {
        expect(screen.getByText('Balance')).toBeTruthy();
      });
    });

    it('should display address section', async () => {
      renderWithProvider(<WalletScreen />);

      await waitFor(() => {
        expect(screen.getByText('Your Address')).toBeTruthy();
      });
    });

    it('should display copy address button', async () => {
      renderWithProvider(<WalletScreen />);

      await waitFor(() => {
        expect(screen.getByText('Copy Address')).toBeTruthy();
      });
    });

    it('should copy address to clipboard', async () => {
      renderWithProvider(<WalletScreen />);

      await waitFor(() => {
        expect(screen.getByText('Copy Address')).toBeTruthy();
      });

      fireEvent.press(screen.getByText('Copy Address'));

      await waitFor(() => {
        expect(Clipboard.setStringAsync).toHaveBeenCalled();
        expect(Alert.alert).toHaveBeenCalledWith('Copied', 'Address copied to clipboard');
      });
    });

    it('should display faucet section', async () => {
      renderWithProvider(<WalletScreen />);

      await waitFor(() => {
        expect(screen.getByText('Testnet Faucet')).toBeTruthy();
      });
    });

    it('should display claim tokens button', async () => {
      renderWithProvider(<WalletScreen />);

      await waitFor(() => {
        expect(screen.getByText('Claim Tokens')).toBeTruthy();
      });
    });

    it('should claim faucet tokens', async () => {
      renderWithProvider(<WalletScreen />);

      await waitFor(() => {
        expect(screen.getByText('Claim Tokens')).toBeTruthy();
      });

      fireEvent.press(screen.getByText('Claim Tokens'));

      await waitFor(() => {
        expect(xaiApi.claimFaucet).toHaveBeenCalled();
        expect(Alert.alert).toHaveBeenCalledWith('Success', 'Tokens sent!');
      });
    });

    it('should display quick actions section', async () => {
      renderWithProvider(<WalletScreen />);

      await waitFor(() => {
        expect(screen.getByText('Quick Actions')).toBeTruthy();
      });
    });

    it('should display transaction history button', async () => {
      renderWithProvider(<WalletScreen />);

      await waitFor(() => {
        expect(screen.getByText('View Transaction History')).toBeTruthy();
      });
    });

    it('should display export key button', async () => {
      renderWithProvider(<WalletScreen />);

      await waitFor(() => {
        expect(screen.getByText('Export Private Key')).toBeTruthy();
      });
    });

    it('should display delete wallet button', async () => {
      renderWithProvider(<WalletScreen />);

      await waitFor(() => {
        expect(screen.getByText('Delete Wallet')).toBeTruthy();
      });
    });

    it('should display wallet info section', async () => {
      renderWithProvider(<WalletScreen />);

      await waitFor(() => {
        expect(screen.getByText('Wallet Info')).toBeTruthy();
      });
    });

    it('should show created date', async () => {
      renderWithProvider(<WalletScreen />);

      await waitFor(() => {
        expect(screen.getByText('Created')).toBeTruthy();
      });
    });

    it('should show public key', async () => {
      renderWithProvider(<WalletScreen />);

      await waitFor(() => {
        expect(screen.getByText('Public Key')).toBeTruthy();
      });
    });
  });

  describe('transaction history view', () => {
    beforeEach(() => {
      storage.hasWallet.mockResolvedValue(true);
      storage.loadWallet.mockResolvedValue({
        address: 'XAItest123456789012345678901234567890',
        publicKey: 'testpublickey',
        privateKey: 'testprivatekey',
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
            },
          ],
          total: 1,
        },
      });
    });

    it('should switch to history view', async () => {
      renderWithProvider(<WalletScreen />);

      await waitFor(() => {
        expect(screen.getByText('View Transaction History')).toBeTruthy();
      });

      fireEvent.press(screen.getByText('View Transaction History'));

      await waitFor(() => {
        expect(screen.getByText('Transaction History')).toBeTruthy();
      });
    });

    it('should show back button in history view', async () => {
      renderWithProvider(<WalletScreen />);

      await waitFor(() => {
        fireEvent.press(screen.getByText('View Transaction History'));
      });

      await waitFor(() => {
        expect(screen.getByText('Back')).toBeTruthy();
      });
    });
  });

  describe('export private key', () => {
    beforeEach(() => {
      storage.hasWallet.mockResolvedValue(true);
      storage.loadWallet.mockResolvedValue({
        address: 'XAItest123456789012345678901234567890',
        publicKey: 'testpublickey',
        privateKey: 'secret-private-key',
        createdAt: Date.now(),
      });
    });

    it('should show confirmation alert when exporting', async () => {
      renderWithProvider(<WalletScreen />);

      await waitFor(() => {
        expect(screen.getByText('Export Private Key')).toBeTruthy();
      });

      fireEvent.press(screen.getByText('Export Private Key'));

      expect(Alert.alert).toHaveBeenCalledWith(
        'Export Private Key',
        expect.any(String),
        expect.any(Array)
      );
    });
  });

  describe('delete wallet', () => {
    beforeEach(() => {
      storage.hasWallet.mockResolvedValue(true);
      storage.loadWallet.mockResolvedValue({
        address: 'XAItest123456789012345678901234567890',
        publicKey: 'testpublickey',
        privateKey: 'testprivatekey',
        createdAt: Date.now(),
      });
    });

    it('should show confirmation alert when deleting', async () => {
      renderWithProvider(<WalletScreen />);

      await waitFor(() => {
        expect(screen.getByText('Delete Wallet')).toBeTruthy();
      });

      fireEvent.press(screen.getByText('Delete Wallet'));

      expect(Alert.alert).toHaveBeenCalledWith(
        'Delete Wallet',
        expect.any(String),
        expect.any(Array)
      );
    });
  });

  describe('faucet error handling', () => {
    beforeEach(() => {
      storage.hasWallet.mockResolvedValue(true);
      storage.loadWallet.mockResolvedValue({
        address: 'XAItest123456789012345678901234567890',
        publicKey: 'testpublickey',
        privateKey: 'testprivatekey',
        createdAt: Date.now(),
      });
    });

    it('should show error when faucet fails', async () => {
      (xaiApi.claimFaucet as jest.Mock).mockResolvedValue({
        success: false,
        error: 'Faucet limit reached',
      });

      renderWithProvider(<WalletScreen />);

      await waitFor(() => {
        expect(screen.getByText('Claim Tokens')).toBeTruthy();
      });

      fireEvent.press(screen.getByText('Claim Tokens'));

      await waitFor(() => {
        expect(Alert.alert).toHaveBeenCalledWith('Error', 'Faucet limit reached');
      });
    });
  });
});
