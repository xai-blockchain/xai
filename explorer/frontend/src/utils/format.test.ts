import { describe, it, expect } from 'vitest';
import {
  truncateHash,
  truncateAddress,
  formatAmount,
  formatXAI,
  formatTimeAgo,
  formatDate,
  formatNumber,
  formatBytes,
  formatDuration,
  formatUSD,
  formatPercentage,
  getStatusColor,
  getComplexityColor,
} from './format';

describe('truncateHash', () => {
  it('truncates long hashes correctly', () => {
    const hash = '0000000000000000000abc123def456789012345678901234567890123456789';
    expect(truncateHash(hash)).toBe('00000000...456789');
  });

  it('uses custom start and end lengths', () => {
    const hash = '0000000000000000000abc123def456789012345678901234567890123456789';
    expect(truncateHash(hash, 4, 4)).toBe('0000...6789');
  });

  it('returns short hashes unchanged', () => {
    const hash = 'abc123';
    expect(truncateHash(hash)).toBe('abc123');
  });

  it('handles edge case at exact boundary', () => {
    const hash = 'abcdef123456789'; // 15 chars
    expect(truncateHash(hash, 6, 6)).toBe('abcdef123456789'); // 6 + 6 + 3 = 15, so no truncation
  });
});

describe('truncateAddress', () => {
  it('truncates long addresses correctly', () => {
    const address = 'XAIaddress12345678901234567890123456';
    // Default len=8, so takes first 8 and last 8 chars
    expect(truncateAddress(address)).toBe('XAIaddre...90123456');
  });

  it('uses custom length', () => {
    const address = 'XAIaddress12345678901234567890123456';
    expect(truncateAddress(address, 4)).toBe('XAIa...3456');
  });

  it('returns short addresses unchanged', () => {
    const address = 'XAI123';
    expect(truncateAddress(address)).toBe('XAI123');
  });
});

describe('formatAmount', () => {
  it('formats string amounts correctly', () => {
    expect(formatAmount('1234567.89')).toMatch(/1,234,567\.89/);
  });

  it('formats number amounts correctly', () => {
    expect(formatAmount(1234567.89)).toMatch(/1,234,567\.89/);
  });

  it('handles custom decimals', () => {
    const result = formatAmount(123.456789, 4);
    expect(result).toMatch(/123\.456/);
  });

  it('returns 0 for NaN', () => {
    expect(formatAmount('not-a-number')).toBe('0');
  });

  it('handles zero', () => {
    expect(formatAmount(0)).toMatch(/0\.00/);
  });
});

describe('formatXAI', () => {
  it('formats amount with XAI suffix', () => {
    expect(formatXAI(100)).toMatch(/100\.00.*XAI/);
  });

  it('formats string amounts', () => {
    expect(formatXAI('1234.56')).toMatch(/1,234\.56.*XAI/);
  });
});

describe('formatTimeAgo', () => {
  it('formats recent dates', () => {
    const now = new Date();
    const fiveMinutesAgo = new Date(now.getTime() - 5 * 60 * 1000);
    const result = formatTimeAgo(fiveMinutesAgo);
    expect(result).toContain('minute');
    expect(result).toContain('ago');
  });

  it('handles string dates', () => {
    const recentDate = new Date(Date.now() - 60000).toISOString();
    const result = formatTimeAgo(recentDate);
    expect(result).toContain('ago');
  });
});

describe('formatDate', () => {
  it('formats dates correctly', () => {
    const date = new Date('2024-01-15T10:30:45Z');
    const result = formatDate(date);
    expect(result).toMatch(/Jan.*15.*2024/);
  });

  it('handles string dates', () => {
    const result = formatDate('2024-06-20T14:25:00Z');
    expect(result).toMatch(/Jun.*20.*2024/);
  });
});

describe('formatNumber', () => {
  it('formats billions correctly', () => {
    expect(formatNumber(1500000000)).toBe('1.50B');
  });

  it('formats millions correctly', () => {
    expect(formatNumber(2500000)).toBe('2.50M');
  });

  it('formats thousands correctly', () => {
    expect(formatNumber(5500)).toBe('5.50K');
  });

  it('formats small numbers with locale string', () => {
    const result = formatNumber(999);
    expect(result).toMatch(/999/);
  });
});

describe('formatBytes', () => {
  it('formats bytes correctly', () => {
    expect(formatBytes(0)).toBe('0 B');
    expect(formatBytes(512)).toBe('512 B');
  });

  it('formats kilobytes correctly', () => {
    expect(formatBytes(1024)).toBe('1 KB');
    expect(formatBytes(2048)).toBe('2 KB');
  });

  it('formats megabytes correctly', () => {
    expect(formatBytes(1048576)).toBe('1 MB');
  });

  it('formats gigabytes correctly', () => {
    expect(formatBytes(1073741824)).toBe('1 GB');
  });
});

describe('formatDuration', () => {
  it('formats seconds correctly', () => {
    expect(formatDuration(30)).toBe('30s');
  });

  it('formats minutes and seconds correctly', () => {
    expect(formatDuration(90)).toBe('1m 30s');
    expect(formatDuration(125)).toBe('2m 5s');
  });

  it('formats hours and minutes correctly', () => {
    expect(formatDuration(3720)).toBe('1h 2m');
    expect(formatDuration(7260)).toBe('2h 1m');
  });
});

describe('formatUSD', () => {
  it('formats USD amounts correctly', () => {
    expect(formatUSD(1234.56)).toBe('$1,234.56');
  });

  it('handles zero', () => {
    expect(formatUSD(0)).toBe('$0.00');
  });

  it('handles negative amounts', () => {
    expect(formatUSD(-100)).toBe('-$100.00');
  });
});

describe('formatPercentage', () => {
  it('formats percentages correctly', () => {
    expect(formatPercentage(75.5)).toBe('75.5%');
    expect(formatPercentage(100)).toBe('100.0%');
    expect(formatPercentage(0)).toBe('0.0%');
  });
});

describe('getStatusColor', () => {
  it('returns green for success states', () => {
    expect(getStatusColor('confirmed')).toBe('text-green-400');
    expect(getStatusColor('completed')).toBe('text-green-400');
    expect(getStatusColor('success')).toBe('text-green-400');
    expect(getStatusColor('CONFIRMED')).toBe('text-green-400'); // case insensitive
  });

  it('returns yellow for pending states', () => {
    expect(getStatusColor('pending')).toBe('text-yellow-400');
    expect(getStatusColor('in_progress')).toBe('text-yellow-400');
  });

  it('returns red for error states', () => {
    expect(getStatusColor('failed')).toBe('text-red-400');
    expect(getStatusColor('error')).toBe('text-red-400');
  });

  it('returns muted for unknown states', () => {
    expect(getStatusColor('unknown')).toBe('text-xai-muted');
  });
});

describe('getComplexityColor', () => {
  it('returns green for low complexity', () => {
    expect(getComplexityColor('low')).toBe('bg-green-500/20 text-green-400');
  });

  it('returns yellow for moderate complexity', () => {
    expect(getComplexityColor('moderate')).toBe('bg-yellow-500/20 text-yellow-400');
  });

  it('returns orange for complex', () => {
    expect(getComplexityColor('complex')).toBe('bg-orange-500/20 text-orange-400');
  });

  it('returns red for critical', () => {
    expect(getComplexityColor('critical')).toBe('bg-red-500/20 text-red-400');
  });

  it('returns gray for unknown complexity', () => {
    expect(getComplexityColor('unknown')).toBe('bg-gray-500/20 text-gray-400');
  });

  it('handles case insensitivity', () => {
    expect(getComplexityColor('LOW')).toBe('bg-green-500/20 text-green-400');
  });
});
