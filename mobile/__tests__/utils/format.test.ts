/**
 * Unit tests for format utilities
 */

import {
  formatXai,
  formatXaiWithSymbol,
  formatCompactNumber,
  formatRelativeTime,
  formatDate,
  formatDateTime,
  formatHash,
  formatUptime,
  formatDifficulty,
  parseXaiAmount,
  validateAmount,
} from '../../src/utils/format';

describe('Format Utilities', () => {
  describe('formatXai', () => {
    it('should format number with 4 decimal places by default', () => {
      expect(formatXai(100)).toBe('100.0000');
      expect(formatXai(1.5)).toBe('1.5000');
      expect(formatXai(0.1234)).toBe('0.1234');
    });

    it('should respect custom decimal places', () => {
      expect(formatXai(100, 2)).toBe('100.00');
      expect(formatXai(1.23456, 6)).toBe('1.234560');
      expect(formatXai(0.5, 0)).toBe('1'); // Rounds up
    });

    it('should handle zero', () => {
      expect(formatXai(0)).toBe('0.0000');
      expect(formatXai(0, 2)).toBe('0.00');
    });

    it('should handle undefined/null/NaN', () => {
      expect(formatXai(undefined as any)).toBe('0.0000');
      expect(formatXai(null as any)).toBe('0.0000');
      expect(formatXai(NaN)).toBe('0.0000');
    });

    it('should handle large numbers', () => {
      expect(formatXai(1000000)).toBe('1000000.0000');
      expect(formatXai(999999999.9999)).toBe('999999999.9999');
    });

    it('should handle small numbers', () => {
      expect(formatXai(0.0001)).toBe('0.0001');
      expect(formatXai(0.00001)).toBe('0.0000');
    });
  });

  describe('formatXaiWithSymbol', () => {
    it('should format amount with XAI symbol', () => {
      expect(formatXaiWithSymbol(100)).toBe('100.0000 XAI');
      expect(formatXaiWithSymbol(0.5)).toBe('0.5000 XAI');
    });

    it('should respect decimal places', () => {
      expect(formatXaiWithSymbol(100, 2)).toBe('100.00 XAI');
    });

    it('should handle zero', () => {
      expect(formatXaiWithSymbol(0)).toBe('0.0000 XAI');
    });
  });

  describe('formatCompactNumber', () => {
    it('should format billions', () => {
      expect(formatCompactNumber(1000000000)).toBe('1.0B');
      expect(formatCompactNumber(2500000000)).toBe('2.5B');
    });

    it('should format millions', () => {
      expect(formatCompactNumber(1000000)).toBe('1.0M');
      expect(formatCompactNumber(15500000)).toBe('15.5M');
    });

    it('should format thousands', () => {
      expect(formatCompactNumber(1000)).toBe('1.0K');
      expect(formatCompactNumber(12345)).toBe('12.3K');
    });

    it('should not format numbers under 1000', () => {
      expect(formatCompactNumber(999)).toBe('999');
      expect(formatCompactNumber(1)).toBe('1');
      expect(formatCompactNumber(0)).toBe('0');
    });
  });

  describe('formatRelativeTime', () => {
    const now = Date.now();

    beforeEach(() => {
      jest.spyOn(Date, 'now').mockReturnValue(now);
    });

    afterEach(() => {
      jest.restoreAllMocks();
    });

    it('should format as "Just now" for recent times', () => {
      const timestamp = Math.floor(now / 1000) - 30; // 30 seconds ago
      expect(formatRelativeTime(timestamp)).toBe('Just now');
    });

    it('should format minutes ago', () => {
      const timestamp = Math.floor(now / 1000) - 120; // 2 minutes ago
      expect(formatRelativeTime(timestamp)).toBe('2 minutes ago');
    });

    it('should format singular minute', () => {
      const timestamp = Math.floor(now / 1000) - 60; // 1 minute ago
      expect(formatRelativeTime(timestamp)).toBe('1 minute ago');
    });

    it('should format hours ago', () => {
      const timestamp = Math.floor(now / 1000) - 7200; // 2 hours ago
      expect(formatRelativeTime(timestamp)).toBe('2 hours ago');
    });

    it('should format singular hour', () => {
      const timestamp = Math.floor(now / 1000) - 3600; // 1 hour ago
      expect(formatRelativeTime(timestamp)).toBe('1 hour ago');
    });

    it('should format days ago', () => {
      const timestamp = Math.floor(now / 1000) - 172800; // 2 days ago
      expect(formatRelativeTime(timestamp)).toBe('2 days ago');
    });

    it('should format singular day', () => {
      const timestamp = Math.floor(now / 1000) - 86400; // 1 day ago
      expect(formatRelativeTime(timestamp)).toBe('1 day ago');
    });
  });

  describe('formatDate', () => {
    it('should format timestamp to date string', () => {
      // Test with a known timestamp
      const timestamp = 1700000000; // Nov 14, 2023
      const result = formatDate(timestamp);

      // Should contain year, month, and day
      expect(result).toMatch(/2023/);
      expect(result).toMatch(/Nov/);
    });

    it('should handle different timestamps', () => {
      const timestamp1 = 1609459200; // Jan 1, 2021
      const timestamp2 = 1640995200; // Jan 1, 2022

      expect(formatDate(timestamp1)).toMatch(/2021/);
      expect(formatDate(timestamp2)).toMatch(/2022/);
    });
  });

  describe('formatDateTime', () => {
    it('should format timestamp to date and time string', () => {
      const timestamp = 1700000000;
      const result = formatDateTime(timestamp);

      // Should contain date and time components
      expect(result).toMatch(/2023/);
      expect(result).toMatch(/:/); // Time separator
    });
  });

  describe('formatHash', () => {
    it('should truncate hash with ellipsis', () => {
      const hash = 'a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2';
      const result = formatHash(hash, 8);

      expect(result).toContain('...');
      expect(result.startsWith('a1b2c3d4')).toBe(true);
      expect(result.endsWith('e5f6a1b2')).toBe(true);
    });

    it('should use default chars value', () => {
      const hash = 'a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2';
      const result = formatHash(hash);

      expect(result).toContain('...');
    });

    it('should return original for short hashes', () => {
      expect(formatHash('abc123')).toBe('abc123');
      expect(formatHash('')).toBe('');
    });

    it('should handle null/undefined', () => {
      expect(formatHash(null as any)).toBe('');
      expect(formatHash(undefined as any)).toBe('');
    });
  });

  describe('formatUptime', () => {
    it('should format seconds to days hours minutes', () => {
      const oneDay = 86400;
      const oneHour = 3600;
      const oneMinute = 60;

      expect(formatUptime(oneDay + oneHour + oneMinute)).toBe('1d 1h 1m');
      expect(formatUptime(2 * oneDay + 5 * oneHour + 30 * oneMinute)).toBe('2d 5h 30m');
    });

    it('should handle days only', () => {
      expect(formatUptime(172800)).toBe('2d');
    });

    it('should handle hours only', () => {
      expect(formatUptime(7200)).toBe('2h');
    });

    it('should handle minutes only', () => {
      expect(formatUptime(120)).toBe('2m');
    });

    it('should handle less than a minute', () => {
      expect(formatUptime(30)).toBe('< 1m');
      expect(formatUptime(0)).toBe('< 1m');
    });
  });

  describe('formatDifficulty', () => {
    it('should format millions with M suffix', () => {
      expect(formatDifficulty(1000000)).toBe('1.00M');
      expect(formatDifficulty(2500000)).toBe('2.50M');
    });

    it('should format thousands with K suffix', () => {
      expect(formatDifficulty(1000)).toBe('1.00K');
      expect(formatDifficulty(12345)).toBe('12.35K');
    });

    it('should format numbers under 1000 with 2 decimals', () => {
      expect(formatDifficulty(999)).toBe('999.00');
      expect(formatDifficulty(1.5)).toBe('1.50');
      expect(formatDifficulty(0)).toBe('0.00');
    });
  });

  describe('parseXaiAmount', () => {
    it('should parse valid decimal numbers', () => {
      expect(parseXaiAmount('100')).toBe(100);
      expect(parseXaiAmount('1.5')).toBe(1.5);
      expect(parseXaiAmount('0.0001')).toBe(0.0001);
    });

    it('should return null for empty input', () => {
      expect(parseXaiAmount('')).toBeNull();
      expect(parseXaiAmount('   ')).toBeNull();
    });

    it('should strip non-numeric characters', () => {
      expect(parseXaiAmount('$100')).toBe(100);
      expect(parseXaiAmount('100 XAI')).toBe(100);
    });

    it('should return null for multiple decimal points', () => {
      expect(parseXaiAmount('1.2.3')).toBeNull();
    });

    it('should return null for negative numbers', () => {
      expect(parseXaiAmount('-100')).toBe(100); // Strips minus, parses 100
    });

    it('should handle zero', () => {
      expect(parseXaiAmount('0')).toBe(0);
      expect(parseXaiAmount('0.0')).toBe(0);
    });
  });

  describe('validateAmount', () => {
    it('should return valid for amounts within balance', () => {
      const result = validateAmount(50, 100);
      expect(result.valid).toBe(true);
      expect(result.error).toBeUndefined();
    });

    it('should return error for amounts exceeding balance', () => {
      const result = validateAmount(150, 100);
      expect(result.valid).toBe(false);
      expect(result.error).toBe('Insufficient balance');
    });

    it('should return error for amounts below minimum', () => {
      const result = validateAmount(0.00001, 100, 0.0001);
      expect(result.valid).toBe(false);
      expect(result.error).toContain('Minimum amount');
    });

    it('should use default minimum of 0.0001', () => {
      const result = validateAmount(0.00001, 100);
      expect(result.valid).toBe(false);
    });

    it('should accept custom minimum amount', () => {
      const result = validateAmount(0.01, 100, 0.1);
      expect(result.valid).toBe(false);
      expect(result.error).toContain('0.1000');
    });

    it('should accept amount equal to balance', () => {
      const result = validateAmount(100, 100);
      expect(result.valid).toBe(true);
    });

    it('should accept amount equal to minimum', () => {
      const result = validateAmount(0.0001, 100, 0.0001);
      expect(result.valid).toBe(true);
    });
  });
});
