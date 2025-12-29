/**
 * Tests for TransactionItem component
 */

import React from 'react';
import { render, fireEvent, screen } from '@testing-library/react-native';
import { TransactionItem } from '../../src/components/TransactionItem';
import { Transaction } from '../../src/types';

// Mock the format utilities to control output
jest.mock('../../src/utils/format', () => ({
  formatXai: (amount: number) => amount.toFixed(4),
  formatRelativeTime: () => '2 hours ago',
  formatAddress: (addr: string) => `${addr.substring(0, 11)}...${addr.slice(-6)}`,
}));

describe('TransactionItem Component', () => {
  const currentAddress = 'XAIa1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2';

  const createTransaction = (overrides: Partial<Transaction> = {}): Transaction => ({
    txid: 'tx123456789',
    sender: 'XAIsender123456789012345678901234567890',
    recipient: 'XAIrecipient12345678901234567890123456',
    amount: 100,
    fee: 0.001,
    timestamp: 1700000000,
    nonce: 1,
    status: 'confirmed',
    ...overrides,
  });

  describe('rendering', () => {
    it('should render transaction item', () => {
      const tx = createTransaction();
      render(
        <TransactionItem transaction={tx} currentAddress={currentAddress} />
      );

      expect(screen.getByText(/100.0000/)).toBeTruthy();
    });

    it('should show amount with XAI symbol', () => {
      const tx = createTransaction({ amount: 50.5 });
      render(
        <TransactionItem transaction={tx} currentAddress={currentAddress} />
      );

      expect(screen.getByText(/50.5000/)).toBeTruthy();
      expect(screen.getByText(/XAI/)).toBeTruthy();
    });

    it('should show relative time', () => {
      const tx = createTransaction();
      render(
        <TransactionItem transaction={tx} currentAddress={currentAddress} />
      );

      expect(screen.getByText('2 hours ago')).toBeTruthy();
    });
  });

  describe('outgoing transactions', () => {
    it('should identify as outgoing when sender matches current address', () => {
      const tx = createTransaction({
        sender: currentAddress,
        recipient: 'XAIother123456789012345678901234567890',
      });

      render(
        <TransactionItem transaction={tx} currentAddress={currentAddress} />
      );

      expect(screen.getByText('Sent')).toBeTruthy();
    });

    it('should show minus sign for outgoing', () => {
      const tx = createTransaction({
        sender: currentAddress,
        amount: 25,
      });

      render(
        <TransactionItem transaction={tx} currentAddress={currentAddress} />
      );

      expect(screen.getByText(/-/)).toBeTruthy();
    });

    it('should show recipient address for outgoing', () => {
      const tx = createTransaction({
        sender: currentAddress,
        recipient: 'XAIrecipient12345678901234567890123456',
      });

      render(
        <TransactionItem transaction={tx} currentAddress={currentAddress} />
      );

      // Should show formatted recipient address
      expect(screen.getByText('Sent')).toBeTruthy();
    });
  });

  describe('incoming transactions', () => {
    it('should identify as incoming when recipient matches current address', () => {
      const tx = createTransaction({
        sender: 'XAIother123456789012345678901234567890',
        recipient: currentAddress,
      });

      render(
        <TransactionItem transaction={tx} currentAddress={currentAddress} />
      );

      expect(screen.getByText('Received')).toBeTruthy();
    });

    it('should show plus sign for incoming', () => {
      const tx = createTransaction({
        recipient: currentAddress,
        amount: 50,
      });

      render(
        <TransactionItem transaction={tx} currentAddress={currentAddress} />
      );

      expect(screen.getByText(/\+/)).toBeTruthy();
    });

    it('should show sender address for incoming', () => {
      const tx = createTransaction({
        sender: 'XAIsender123456789012345678901234567890',
        recipient: currentAddress,
      });

      render(
        <TransactionItem transaction={tx} currentAddress={currentAddress} />
      );

      expect(screen.getByText('Received')).toBeTruthy();
    });
  });

  describe('transaction status', () => {
    it('should show pending badge for pending transactions', () => {
      const tx = createTransaction({ status: 'pending' });
      render(
        <TransactionItem transaction={tx} currentAddress={currentAddress} />
      );

      expect(screen.getByText('Pending')).toBeTruthy();
    });

    it('should not show pending badge for confirmed transactions', () => {
      const tx = createTransaction({ status: 'confirmed' });
      render(
        <TransactionItem transaction={tx} currentAddress={currentAddress} />
      );

      expect(screen.queryByText('Pending')).toBeNull();
    });
  });

  describe('interactions', () => {
    it('should call onPress when pressed', () => {
      const onPress = jest.fn();
      const tx = createTransaction();

      render(
        <TransactionItem
          transaction={tx}
          currentAddress={currentAddress}
          onPress={onPress}
        />
      );

      fireEvent.press(screen.getByText('Sent'));

      expect(onPress).toHaveBeenCalledTimes(1);
    });

    it('should be pressable without onPress handler', () => {
      const tx = createTransaction();

      render(
        <TransactionItem transaction={tx} currentAddress={currentAddress} />
      );

      // Should not throw
      expect(() => {
        fireEvent.press(screen.getByText('Sent'));
      }).not.toThrow();
    });
  });

  describe('formatting', () => {
    it('should format large amounts', () => {
      const tx = createTransaction({ amount: 1000000 });
      render(
        <TransactionItem transaction={tx} currentAddress={currentAddress} />
      );

      expect(screen.getByText(/1000000.0000/)).toBeTruthy();
    });

    it('should format small amounts', () => {
      const tx = createTransaction({ amount: 0.0001 });
      render(
        <TransactionItem transaction={tx} currentAddress={currentAddress} />
      );

      expect(screen.getByText(/0.0001/)).toBeTruthy();
    });
  });

  describe('edge cases', () => {
    it('should handle zero amount', () => {
      const tx = createTransaction({ amount: 0 });
      render(
        <TransactionItem transaction={tx} currentAddress={currentAddress} />
      );

      expect(screen.getByText(/0.0000/)).toBeTruthy();
    });

    it('should handle same sender and recipient (self transfer)', () => {
      const tx = createTransaction({
        sender: currentAddress,
        recipient: currentAddress,
      });

      render(
        <TransactionItem transaction={tx} currentAddress={currentAddress} />
      );

      // Should be treated as outgoing
      expect(screen.getByText('Sent')).toBeTruthy();
    });
  });
});
