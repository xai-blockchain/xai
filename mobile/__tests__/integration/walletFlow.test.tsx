/**
 * Integration tests for wallet creation and management flow
 */

import React from 'react';
import { render, fireEvent, screen, waitFor, act } from '@testing-library/react-native';
import { Alert } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { WalletProvider } from '../../src/context/WalletContext';
import { WalletScreen } from '../../src/screens/WalletScreen';
import { HomeScreen } from '../../src/screens/HomeScreen';
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
    getStats: jest.fn(),
    getHistory: jest.fn(),
    getBalance: jest.fn(),
    getHealth: jest.fn(),
    claimFaucet: jest.fn(),
  },
}));

// Mock storage with in-memory implementation
let mockStorage: Record<string, string> = {};
jest.mock('../../src/utils/storage', () => ({
  loadWallet: jest.fn().mockImplementation(async () => {
    const address = mockStorage['xai_wallet_address'];
    if (!address) return null;
    return {
      address,
      publicKey: mockStorage['xai_wallet_public_key'],
      privateKey: mockStorage['xai_wallet_private_key'],
      createdAt: parseInt(mockStorage['xai_wallet_created_at'] || '0', 10),
    };
  }),
  hasWallet: jest.fn().mockImplementation(async () => {
    return !!mockStorage['xai_wallet_address'];
  }),
  saveWallet: jest.fn().mockImplementation(async (wallet) => {
    mockStorage['xai_wallet_address'] = wallet.address;
    mockStorage['xai_wallet_public_key'] = wallet.publicKey;
    mockStorage['xai_wallet_private_key'] = wallet.privateKey;
    mockStorage['xai_wallet_created_at'] = String(Date.now());
  }),
  deleteWallet: jest.fn().mockImplementation(async () => {
    mockStorage = {};
  }),
}));

// Mock crypto
jest.mock('../../src/utils/crypto', () => ({
  createWallet: jest.fn().mockImplementation(async () => ({
    address: 'XAInewwallet123456789012345678901234567',
    publicKey: 'newpublickey12345678901234567890123456789',
    privateKey: 'newprivatekey1234567890123456789012345678',
  })),
  deriveAddress: jest.fn().mockResolvedValue('XAIimported123456789012345678901234567'),
}));

const storage = require('../../src/utils/storage');
const crypto = require('../../src/utils/crypto');

const Tab = createBottomTabNavigator();

function TestApp() {
  return (
    <WalletProvider>
      <NavigationContainer>
        <Tab.Navigator>
          <Tab.Screen name="Home" component={HomeScreen} />
          <Tab.Screen name="Wallet" component={WalletScreen} />
        </Tab.Navigator>
      </NavigationContainer>
    </WalletProvider>
  );
}

describe('Wallet Flow Integration', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockStorage = {};
    (Alert.alert as jest.Mock).mockClear();

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
      data: { balance: 0 },
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

  describe('new user wallet creation', () => {
    it('should start with no wallet', async () => {
      render(<TestApp />);

      await waitFor(() => {
        expect(screen.getByText('Welcome to XAI')).toBeTruthy();
      });
    });

    it('should create wallet and show balance', async () => {
      render(<TestApp />);

      // Initially on home screen with no wallet
      await waitFor(() => {
        expect(screen.getByText('Welcome to XAI')).toBeTruthy();
      });

      // Navigate to wallet screen
      fireEvent.press(screen.getByText('Wallet'));

      await waitFor(() => {
        expect(screen.getByText('Create New Wallet')).toBeTruthy();
      });

      // Start wallet creation
      fireEvent.press(screen.getByText('Create New Wallet'));

      await waitFor(() => {
        expect(screen.getByText('Create New Wallet')).toBeTruthy();
      });

      // Create the wallet
      const createButtons = screen.getAllByText('Create Wallet');
      fireEvent.press(createButtons[0]);

      await waitFor(() => {
        expect(crypto.createWallet).toHaveBeenCalled();
      });

      await waitFor(() => {
        expect(storage.saveWallet).toHaveBeenCalled();
      });
    });

    it('should persist wallet after creation', async () => {
      render(<TestApp />);

      // Navigate to wallet and create
      await waitFor(() => {
        expect(screen.getByText('Wallet')).toBeTruthy();
      });

      fireEvent.press(screen.getByText('Wallet'));

      await waitFor(() => {
        fireEvent.press(screen.getByText('Create New Wallet'));
      });

      await waitFor(() => {
        const buttons = screen.getAllByText('Create Wallet');
        fireEvent.press(buttons[0]);
      });

      await waitFor(() => {
        expect(storage.saveWallet).toHaveBeenCalledWith(
          expect.objectContaining({
            address: 'XAInewwallet123456789012345678901234567',
            publicKey: expect.any(String),
            privateKey: expect.any(String),
          })
        );
      });
    });
  });

  describe('wallet import flow', () => {
    it('should import wallet with private key', async () => {
      render(<TestApp />);

      // Navigate to wallet
      await waitFor(() => {
        fireEvent.press(screen.getByText('Wallet'));
      });

      await waitFor(() => {
        expect(screen.getByText('Import Existing Wallet')).toBeTruthy();
      });

      // Go to import view
      fireEvent.press(screen.getByText('Import Existing Wallet'));

      await waitFor(() => {
        expect(screen.getByText('Private Key')).toBeTruthy();
      });

      // Enter private key
      fireEvent.changeText(
        screen.getByPlaceholderText('Enter your private key'),
        'existing-private-key-12345678901234567890'
      );

      // Import
      fireEvent.press(screen.getByText('Import'));

      await waitFor(() => {
        expect(storage.saveWallet).toHaveBeenCalled();
      });
    });

    it('should show error for empty private key', async () => {
      render(<TestApp />);

      await waitFor(() => {
        fireEvent.press(screen.getByText('Wallet'));
      });

      await waitFor(() => {
        fireEvent.press(screen.getByText('Import Existing Wallet'));
      });

      await waitFor(() => {
        fireEvent.press(screen.getByText('Import'));
      });

      expect(Alert.alert).toHaveBeenCalledWith('Error', 'Please enter a private key');
    });
  });

  describe('existing wallet user', () => {
    beforeEach(() => {
      mockStorage = {
        xai_wallet_address: 'XAIexisting12345678901234567890123456',
        xai_wallet_public_key: 'existingpubkey',
        xai_wallet_private_key: 'existingprivkey',
        xai_wallet_created_at: String(Date.now()),
      };
    });

    it('should show wallet balance on home', async () => {
      (xaiApi.getBalance as jest.Mock).mockResolvedValue({
        success: true,
        data: { balance: 500 },
      });

      render(<TestApp />);

      await waitFor(() => {
        expect(screen.getByText('Total Balance')).toBeTruthy();
      });
    });

    it('should show wallet address in wallet screen', async () => {
      render(<TestApp />);

      await waitFor(() => {
        fireEvent.press(screen.getByText('Wallet'));
      });

      await waitFor(() => {
        expect(screen.getByText('Your Address')).toBeTruthy();
      });
    });
  });

  describe('wallet deletion flow', () => {
    beforeEach(() => {
      mockStorage = {
        xai_wallet_address: 'XAItodelete12345678901234567890123456',
        xai_wallet_public_key: 'deletepubkey',
        xai_wallet_private_key: 'deleteprivkey',
        xai_wallet_created_at: String(Date.now()),
      };
    });

    it('should show confirmation before delete', async () => {
      render(<TestApp />);

      await waitFor(() => {
        fireEvent.press(screen.getByText('Wallet'));
      });

      await waitFor(() => {
        expect(screen.getByText('Delete Wallet')).toBeTruthy();
      });

      fireEvent.press(screen.getByText('Delete Wallet'));

      expect(Alert.alert).toHaveBeenCalledWith(
        'Delete Wallet',
        expect.stringContaining('Are you sure'),
        expect.any(Array)
      );
    });

    it('should delete wallet on confirm', async () => {
      (Alert.alert as jest.Mock).mockImplementation((title, message, buttons) => {
        const deleteButton = buttons?.find((b: any) => b.text === 'Delete');
        if (deleteButton?.onPress) deleteButton.onPress();
      });

      render(<TestApp />);

      await waitFor(() => {
        fireEvent.press(screen.getByText('Wallet'));
      });

      await waitFor(() => {
        fireEvent.press(screen.getByText('Delete Wallet'));
      });

      await waitFor(() => {
        expect(storage.deleteWallet).toHaveBeenCalled();
      });
    });
  });

  describe('faucet claim flow', () => {
    beforeEach(() => {
      mockStorage = {
        xai_wallet_address: 'XAIfaucetuser123456789012345678901234',
        xai_wallet_public_key: 'faucetpubkey',
        xai_wallet_private_key: 'faucetprivkey',
        xai_wallet_created_at: String(Date.now()),
      };
    });

    it('should claim faucet tokens successfully', async () => {
      render(<TestApp />);

      await waitFor(() => {
        fireEvent.press(screen.getByText('Wallet'));
      });

      await waitFor(() => {
        expect(screen.getByText('Claim Tokens')).toBeTruthy();
      });

      fireEvent.press(screen.getByText('Claim Tokens'));

      await waitFor(() => {
        expect(xaiApi.claimFaucet).toHaveBeenCalledWith(
          'XAIfaucetuser123456789012345678901234'
        );
      });

      await waitFor(() => {
        expect(Alert.alert).toHaveBeenCalledWith('Success', 'Tokens sent!');
      });
    });

    it('should show error when faucet fails', async () => {
      (xaiApi.claimFaucet as jest.Mock).mockResolvedValue({
        success: false,
        error: 'Rate limit exceeded',
      });

      render(<TestApp />);

      await waitFor(() => {
        fireEvent.press(screen.getByText('Wallet'));
      });

      await waitFor(() => {
        fireEvent.press(screen.getByText('Claim Tokens'));
      });

      await waitFor(() => {
        expect(Alert.alert).toHaveBeenCalledWith('Error', 'Rate limit exceeded');
      });
    });
  });

  describe('address copy flow', () => {
    const Clipboard = require('expo-clipboard');

    beforeEach(() => {
      mockStorage = {
        xai_wallet_address: 'XAIcopytest12345678901234567890123456',
        xai_wallet_public_key: 'copypubkey',
        xai_wallet_private_key: 'copyprivkey',
        xai_wallet_created_at: String(Date.now()),
      };
    });

    it('should copy address to clipboard', async () => {
      render(<TestApp />);

      await waitFor(() => {
        fireEvent.press(screen.getByText('Wallet'));
      });

      await waitFor(() => {
        fireEvent.press(screen.getByText('Copy Address'));
      });

      await waitFor(() => {
        expect(Clipboard.setStringAsync).toHaveBeenCalledWith(
          'XAIcopytest12345678901234567890123456'
        );
        expect(Alert.alert).toHaveBeenCalledWith('Copied', 'Address copied to clipboard');
      });
    });
  });

  describe('connection status integration', () => {
    beforeEach(() => {
      mockStorage = {
        xai_wallet_address: 'XAIconntest12345678901234567890123456',
        xai_wallet_public_key: 'connpubkey',
        xai_wallet_private_key: 'connprivkey',
        xai_wallet_created_at: String(Date.now()),
      };
    });

    it('should show connected when health check passes', async () => {
      (xaiApi.getHealth as jest.Mock).mockResolvedValue({
        success: true,
        data: { status: 'healthy' },
      });

      render(<TestApp />);

      await waitFor(() => {
        expect(screen.getByText('Connected')).toBeTruthy();
      });
    });

    it('should show disconnected when health check fails', async () => {
      (xaiApi.getHealth as jest.Mock).mockResolvedValue({
        success: false,
        error: 'Network error',
      });

      render(<TestApp />);

      await waitFor(() => {
        expect(screen.getByText('Disconnected')).toBeTruthy();
      });
    });
  });
});
