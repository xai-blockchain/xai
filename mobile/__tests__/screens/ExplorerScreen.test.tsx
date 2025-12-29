/**
 * Tests for ExplorerScreen
 */

import React from 'react';
import { render, fireEvent, screen, waitFor } from '@testing-library/react-native';
import { ExplorerScreen } from '../../src/screens/ExplorerScreen';
import { xaiApi } from '../../src/services/api';

// Mock API
jest.mock('../../src/services/api', () => ({
  xaiApi: {
    getStats: jest.fn(),
    getBlocks: jest.fn(),
    getBlock: jest.fn(),
    getBlockByHash: jest.fn(),
    getPendingTransactions: jest.fn(),
    getTransaction: jest.fn(),
    getBalance: jest.fn(),
    getHistory: jest.fn(),
  },
}));

describe('ExplorerScreen', () => {
  beforeEach(() => {
    jest.clearAllMocks();

    // Default mock responses
    (xaiApi.getStats as jest.Mock).mockResolvedValue({
      success: true,
      data: {
        chainHeight: 5000,
        difficulty: 100000,
        totalSupply: 1000000,
        pendingTransactionsCount: 10,
        peers: 5,
        nodeUptime: 86400,
      },
    });

    (xaiApi.getBlocks as jest.Mock).mockResolvedValue({
      success: true,
      data: {
        total: 5000,
        blocks: [
          {
            index: 5000,
            hash: 'block5000hash123456789012345678901234567890123456789012345678',
            previousHash: 'prevhash',
            timestamp: 1700000000,
            difficulty: 100000,
            nonce: 12345,
            miner: 'XAIminer123456789012345678901234567890',
            merkleRoot: 'merkle',
            transactions: [],
          },
          {
            index: 4999,
            hash: 'block4999hash123456789012345678901234567890123456789012345678',
            previousHash: 'prevhash2',
            timestamp: 1699999900,
            difficulty: 100000,
            nonce: 12344,
            merkleRoot: 'merkle2',
            transactions: [],
          },
        ],
      },
    });

    (xaiApi.getPendingTransactions as jest.Mock).mockResolvedValue({
      success: true,
      data: {
        count: 2,
        transactions: [
          {
            txid: 'tx1',
            sender: 'XAIsender1',
            recipient: 'XAIrecipient1',
            amount: 100,
            fee: 0.001,
            timestamp: 1700000000,
            nonce: 1,
          },
          {
            txid: 'tx2',
            sender: 'XAIsender2',
            recipient: 'XAIrecipient2',
            amount: 50,
            fee: 0.001,
            timestamp: 1700000010,
            nonce: 1,
          },
        ],
      },
    });
  });

  describe('rendering', () => {
    it('should render explorer screen', async () => {
      render(<ExplorerScreen />);

      await waitFor(() => {
        expect(screen.getByText('Blocks')).toBeTruthy();
      });
    });

    it('should display stats card', async () => {
      render(<ExplorerScreen />);

      await waitFor(() => {
        expect(screen.getByText('Height')).toBeTruthy();
        expect(screen.getByText('Difficulty')).toBeTruthy();
        expect(screen.getByText('Peers')).toBeTruthy();
        expect(screen.getByText('Uptime')).toBeTruthy();
      });
    });

    it('should display tabs', async () => {
      render(<ExplorerScreen />);

      await waitFor(() => {
        expect(screen.getByText('Blocks')).toBeTruthy();
        expect(screen.getByText('Pending')).toBeTruthy();
        expect(screen.getByText('Search')).toBeTruthy();
      });
    });
  });

  describe('blocks tab', () => {
    it('should display blocks by default', async () => {
      render(<ExplorerScreen />);

      await waitFor(() => {
        expect(screen.getByText('#5000')).toBeTruthy();
        expect(screen.getByText('#4999')).toBeTruthy();
      });
    });

    it('should display block details', async () => {
      render(<ExplorerScreen />);

      await waitFor(() => {
        expect(screen.getByText('Hash')).toBeTruthy();
        expect(screen.getByText('Transactions')).toBeTruthy();
      });
    });

    it('should show block modal on press', async () => {
      render(<ExplorerScreen />);

      await waitFor(() => {
        expect(screen.getByText('#5000')).toBeTruthy();
      });

      fireEvent.press(screen.getByText('#5000'));

      await waitFor(() => {
        expect(screen.getByText('Block #5000')).toBeTruthy();
        expect(screen.getByText('Close')).toBeTruthy();
      });
    });

    it('should close block modal on close press', async () => {
      render(<ExplorerScreen />);

      await waitFor(() => {
        expect(screen.getByText('#5000')).toBeTruthy();
      });

      fireEvent.press(screen.getByText('#5000'));

      await waitFor(() => {
        expect(screen.getByText('Close')).toBeTruthy();
      });

      fireEvent.press(screen.getByText('Close'));

      await waitFor(() => {
        expect(screen.queryByText('Block #5000')).toBeNull();
      });
    });
  });

  describe('pending tab', () => {
    it('should switch to pending tab', async () => {
      render(<ExplorerScreen />);

      await waitFor(() => {
        expect(screen.getByText('Pending')).toBeTruthy();
      });

      fireEvent.press(screen.getByText('Pending'));

      await waitFor(() => {
        expect(xaiApi.getPendingTransactions).toHaveBeenCalled();
      });
    });

    it('should display pending transactions', async () => {
      render(<ExplorerScreen />);

      await waitFor(() => {
        fireEvent.press(screen.getByText('Pending'));
      });

      await waitFor(() => {
        // Should show transaction items
        expect(xaiApi.getPendingTransactions).toHaveBeenCalled();
      });
    });
  });

  describe('search tab', () => {
    it('should switch to search tab', async () => {
      render(<ExplorerScreen />);

      await waitFor(() => {
        expect(screen.getByText('Search')).toBeTruthy();
      });

      fireEvent.press(screen.getByText('Search'));

      await waitFor(() => {
        expect(screen.getByPlaceholderText('Block #, hash, txid, or address')).toBeTruthy();
      });
    });

    it('should display search input', async () => {
      render(<ExplorerScreen />);

      await waitFor(() => {
        fireEvent.press(screen.getByText('Search'));
      });

      await waitFor(() => {
        expect(screen.getByPlaceholderText('Block #, hash, txid, or address')).toBeTruthy();
        expect(screen.getByText('Search')).toBeTruthy();
      });
    });

    it('should search for block by number', async () => {
      (xaiApi.getBlock as jest.Mock).mockResolvedValue({
        success: true,
        data: {
          index: 100,
          hash: 'blockhash100',
          previousHash: 'prev',
          timestamp: 1700000000,
          difficulty: 1000,
          nonce: 123,
          merkleRoot: 'merkle',
          transactions: [],
        },
      });

      render(<ExplorerScreen />);

      await waitFor(() => {
        fireEvent.press(screen.getByText('Search'));
      });

      await waitFor(() => {
        fireEvent.changeText(
          screen.getByPlaceholderText('Block #, hash, txid, or address'),
          '100'
        );
      });

      // There are multiple elements with "Search" text (tab and button)
      const searchButtons = screen.getAllByText('Search');
      fireEvent.press(searchButtons[searchButtons.length - 1]); // Press the button

      await waitFor(() => {
        expect(xaiApi.getBlock).toHaveBeenCalledWith(100);
      });
    });

    it('should search for block by hash', async () => {
      (xaiApi.getBlockByHash as jest.Mock).mockResolvedValue({
        success: true,
        data: {
          index: 50,
          hash: 'a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2',
          previousHash: 'prev',
          timestamp: 1700000000,
          difficulty: 1000,
          nonce: 123,
          merkleRoot: 'merkle',
          transactions: [],
        },
      });

      render(<ExplorerScreen />);

      await waitFor(() => {
        fireEvent.press(screen.getByText('Search'));
      });

      const hash = 'a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2';

      await waitFor(() => {
        fireEvent.changeText(
          screen.getByPlaceholderText('Block #, hash, txid, or address'),
          hash
        );
      });

      const searchButtons = screen.getAllByText('Search');
      fireEvent.press(searchButtons[searchButtons.length - 1]);

      await waitFor(() => {
        expect(xaiApi.getBlockByHash).toHaveBeenCalledWith(hash);
      });
    });

    it('should search for transaction by txid', async () => {
      (xaiApi.getBlockByHash as jest.Mock).mockResolvedValue({
        success: false,
      });

      (xaiApi.getTransaction as jest.Mock).mockResolvedValue({
        success: true,
        data: {
          found: true,
          transaction: {
            txid: 'a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2',
            sender: 'XAIsender',
            recipient: 'XAIrecipient',
            amount: 100,
            fee: 0.001,
            timestamp: 1700000000,
            nonce: 1,
          },
          confirmations: 10,
          status: 'confirmed',
        },
      });

      render(<ExplorerScreen />);

      await waitFor(() => {
        fireEvent.press(screen.getByText('Search'));
      });

      const txid = 'a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2';

      await waitFor(() => {
        fireEvent.changeText(
          screen.getByPlaceholderText('Block #, hash, txid, or address'),
          txid
        );
      });

      const searchButtons = screen.getAllByText('Search');
      fireEvent.press(searchButtons[searchButtons.length - 1]);

      await waitFor(() => {
        expect(xaiApi.getTransaction).toHaveBeenCalledWith(txid);
      });
    });

    it('should search for address balance', async () => {
      (xaiApi.getBalance as jest.Mock).mockResolvedValue({
        success: true,
        data: { address: 'XAItest', balance: 500 },
      });

      (xaiApi.getHistory as jest.Mock).mockResolvedValue({
        success: true,
        data: { transactions: [] },
      });

      render(<ExplorerScreen />);

      await waitFor(() => {
        fireEvent.press(screen.getByText('Search'));
      });

      const address = 'XAItest123456789012345678901234567890';

      await waitFor(() => {
        fireEvent.changeText(
          screen.getByPlaceholderText('Block #, hash, txid, or address'),
          address
        );
      });

      const searchButtons = screen.getAllByText('Search');
      fireEvent.press(searchButtons[searchButtons.length - 1]);

      await waitFor(() => {
        expect(xaiApi.getBalance).toHaveBeenCalledWith(address);
      });
    });

    it('should show not found message', async () => {
      (xaiApi.getBlock as jest.Mock).mockResolvedValue({
        success: false,
      });

      render(<ExplorerScreen />);

      await waitFor(() => {
        fireEvent.press(screen.getByText('Search'));
      });

      await waitFor(() => {
        fireEvent.changeText(
          screen.getByPlaceholderText('Block #, hash, txid, or address'),
          'nonexistent'
        );
      });

      const searchButtons = screen.getAllByText('Search');
      fireEvent.press(searchButtons[searchButtons.length - 1]);

      await waitFor(() => {
        expect(screen.getByText(/No results found/)).toBeTruthy();
      });
    });
  });

  describe('block modal', () => {
    it('should show block details in modal', async () => {
      render(<ExplorerScreen />);

      await waitFor(() => {
        expect(screen.getByText('#5000')).toBeTruthy();
      });

      fireEvent.press(screen.getByText('#5000'));

      await waitFor(() => {
        expect(screen.getByText('Block #5000')).toBeTruthy();
        expect(screen.getByText('Previous Hash')).toBeTruthy();
        expect(screen.getByText('Timestamp')).toBeTruthy();
        expect(screen.getByText('Nonce')).toBeTruthy();
        expect(screen.getByText('Merkle Root')).toBeTruthy();
      });
    });

    it('should show miner if present', async () => {
      render(<ExplorerScreen />);

      await waitFor(() => {
        fireEvent.press(screen.getByText('#5000'));
      });

      await waitFor(() => {
        expect(screen.getByText('Miner')).toBeTruthy();
      });
    });

    it('should show transaction count', async () => {
      render(<ExplorerScreen />);

      await waitFor(() => {
        fireEvent.press(screen.getByText('#5000'));
      });

      await waitFor(() => {
        expect(screen.getByText('Transactions (0)')).toBeTruthy();
      });
    });
  });

  describe('loading states', () => {
    it('should show loading text initially', async () => {
      (xaiApi.getBlocks as jest.Mock).mockImplementation(
        () => new Promise(() => {}) // Never resolves
      );

      render(<ExplorerScreen />);

      await waitFor(() => {
        expect(screen.getByText('Loading...')).toBeTruthy();
      });
    });

    it('should show empty text when no data', async () => {
      (xaiApi.getBlocks as jest.Mock).mockResolvedValue({
        success: true,
        data: { total: 0, blocks: [] },
      });

      render(<ExplorerScreen />);

      await waitFor(() => {
        expect(screen.getByText('No data')).toBeTruthy();
      });
    });
  });

  describe('refresh functionality', () => {
    it('should fetch stats on mount', async () => {
      render(<ExplorerScreen />);

      await waitFor(() => {
        expect(xaiApi.getStats).toHaveBeenCalled();
      });
    });

    it('should fetch blocks on mount', async () => {
      render(<ExplorerScreen />);

      await waitFor(() => {
        expect(xaiApi.getBlocks).toHaveBeenCalled();
      });
    });
  });

  describe('error handling', () => {
    it('should handle stats fetch failure', async () => {
      (xaiApi.getStats as jest.Mock).mockResolvedValue({
        success: false,
        error: 'Failed',
      });

      render(<ExplorerScreen />);

      // Should still render without crashing
      await waitFor(() => {
        expect(screen.getByText('Blocks')).toBeTruthy();
      });
    });

    it('should handle blocks fetch failure', async () => {
      (xaiApi.getBlocks as jest.Mock).mockResolvedValue({
        success: false,
        error: 'Failed',
      });

      render(<ExplorerScreen />);

      await waitFor(() => {
        expect(screen.getByText('No data')).toBeTruthy();
      });
    });
  });
});
