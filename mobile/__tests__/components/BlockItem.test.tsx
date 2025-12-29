/**
 * Tests for BlockItem component
 */

import React from 'react';
import { render, fireEvent, screen } from '@testing-library/react-native';
import { BlockItem } from '../../src/components/BlockItem';
import { Block } from '../../src/types';

// Mock the format utilities
jest.mock('../../src/utils/format', () => ({
  formatRelativeTime: () => '5 minutes ago',
  formatHash: (hash: string) => `${hash.substring(0, 10)}...${hash.slice(-10)}`,
}));

describe('BlockItem Component', () => {
  const createBlock = (overrides: Partial<Block> = {}): Block => ({
    index: 1000,
    hash: 'a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2',
    previousHash: '0000000000000000000000000000000000000000000000000000000000000000',
    timestamp: 1700000000,
    difficulty: 12345,
    nonce: 67890,
    miner: 'XAIa1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2',
    merkleRoot: 'merkle-root-hash',
    transactions: [],
    ...overrides,
  });

  describe('rendering', () => {
    it('should render block item', () => {
      const block = createBlock();
      render(<BlockItem block={block} />);

      expect(screen.getByText('#1000')).toBeTruthy();
    });

    it('should display block number with hash prefix', () => {
      const block = createBlock({ index: 5000 });
      render(<BlockItem block={block} />);

      expect(screen.getByText('#5000')).toBeTruthy();
    });

    it('should show relative time', () => {
      const block = createBlock();
      render(<BlockItem block={block} />);

      expect(screen.getByText('5 minutes ago')).toBeTruthy();
    });

    it('should show formatted hash', () => {
      const block = createBlock();
      render(<BlockItem block={block} />);

      // Hash label and truncated value
      expect(screen.getByText('Hash')).toBeTruthy();
    });

    it('should show transaction count', () => {
      const block = createBlock({
        transactions: [
          { txid: 'tx1' } as any,
          { txid: 'tx2' } as any,
          { txid: 'tx3' } as any,
        ],
      });

      render(<BlockItem block={block} />);

      expect(screen.getByText('Transactions')).toBeTruthy();
      expect(screen.getByText('3')).toBeTruthy();
    });
  });

  describe('miner display', () => {
    it('should show miner when present', () => {
      const block = createBlock({
        miner: 'XAIminer123456789012345678901234567890',
      });

      render(<BlockItem block={block} />);

      expect(screen.getByText('Miner')).toBeTruthy();
    });

    it('should not show miner when absent', () => {
      const block = createBlock({ miner: undefined });

      render(<BlockItem block={block} />);

      expect(screen.queryByText('Miner')).toBeNull();
    });

    it('should not show miner when empty string', () => {
      const block = createBlock({ miner: '' });

      render(<BlockItem block={block} />);

      // Empty string is falsy, should not show miner row
      expect(screen.queryByText('Miner')).toBeNull();
    });
  });

  describe('transaction count', () => {
    it('should show 0 for empty transactions', () => {
      const block = createBlock({ transactions: [] });
      render(<BlockItem block={block} />);

      expect(screen.getByText('0')).toBeTruthy();
    });

    it('should show correct count for multiple transactions', () => {
      const block = createBlock({
        transactions: new Array(10).fill({ txid: 'tx' }),
      });

      render(<BlockItem block={block} />);

      expect(screen.getByText('10')).toBeTruthy();
    });
  });

  describe('interactions', () => {
    it('should call onPress when pressed', () => {
      const onPress = jest.fn();
      const block = createBlock();

      render(<BlockItem block={block} onPress={onPress} />);

      fireEvent.press(screen.getByText('#1000'));

      expect(onPress).toHaveBeenCalledTimes(1);
    });

    it('should be pressable without onPress handler', () => {
      const block = createBlock();

      render(<BlockItem block={block} />);

      expect(() => {
        fireEvent.press(screen.getByText('#1000'));
      }).not.toThrow();
    });

    it('should call onPress on any content press', () => {
      const onPress = jest.fn();
      const block = createBlock();

      render(<BlockItem block={block} onPress={onPress} />);

      // Press on different elements
      fireEvent.press(screen.getByText('Hash'));
      expect(onPress).toHaveBeenCalled();
    });
  });

  describe('block numbers', () => {
    it('should display genesis block (0)', () => {
      const block = createBlock({ index: 0 });
      render(<BlockItem block={block} />);

      expect(screen.getByText('#0')).toBeTruthy();
    });

    it('should display large block numbers', () => {
      const block = createBlock({ index: 1000000 });
      render(<BlockItem block={block} />);

      expect(screen.getByText('#1000000')).toBeTruthy();
    });
  });

  describe('styling', () => {
    it('should render with correct structure', () => {
      const block = createBlock();
      const { toJSON } = render(<BlockItem block={block} />);

      expect(toJSON()).toBeTruthy();
    });
  });

  describe('hash formatting', () => {
    it('should show truncated hash', () => {
      const block = createBlock({
        hash: 'deadbeef1234567890abcdef1234567890deadbeef1234567890abcdef12345678',
      });

      render(<BlockItem block={block} />);

      // formatHash mock returns first 10 + ... + last 10
      expect(screen.getByText('Hash')).toBeTruthy();
    });
  });

  describe('edge cases', () => {
    it('should handle block with minimal data', () => {
      const block: Block = {
        index: 1,
        hash: 'hash',
        previousHash: 'prev',
        timestamp: 0,
        difficulty: 0,
        nonce: 0,
        merkleRoot: '',
        transactions: [],
      };

      render(<BlockItem block={block} />);

      expect(screen.getByText('#1')).toBeTruthy();
    });
  });
});
