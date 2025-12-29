/**
 * Formatting utilities for XAI mobile app
 */

/**
 * Format XAI amount with proper decimal places
 */
export function formatXai(amount: number, decimals: number = 4): string {
  if (amount === undefined || amount === null || isNaN(amount)) {
    return '0.0000';
  }

  return amount.toFixed(decimals);
}

/**
 * Format XAI amount with symbol
 */
export function formatXaiWithSymbol(amount: number, decimals: number = 4): string {
  return `${formatXai(amount, decimals)} XAI`;
}

/**
 * Format large numbers with K, M, B suffixes
 */
export function formatCompactNumber(num: number): string {
  if (num >= 1_000_000_000) {
    return `${(num / 1_000_000_000).toFixed(1)}B`;
  }
  if (num >= 1_000_000) {
    return `${(num / 1_000_000).toFixed(1)}M`;
  }
  if (num >= 1_000) {
    return `${(num / 1_000).toFixed(1)}K`;
  }
  return num.toString();
}

/**
 * Format timestamp to relative time (e.g., "2 hours ago")
 */
export function formatRelativeTime(timestamp: number): string {
  const now = Date.now();
  const diff = now - timestamp * 1000; // Convert seconds to milliseconds if needed

  const seconds = Math.floor(diff / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);

  if (days > 0) {
    return days === 1 ? '1 day ago' : `${days} days ago`;
  }
  if (hours > 0) {
    return hours === 1 ? '1 hour ago' : `${hours} hours ago`;
  }
  if (minutes > 0) {
    return minutes === 1 ? '1 minute ago' : `${minutes} minutes ago`;
  }
  return 'Just now';
}

/**
 * Format timestamp to date string
 */
export function formatDate(timestamp: number): string {
  const date = new Date(timestamp * 1000);
  return date.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

/**
 * Format timestamp to date and time string
 */
export function formatDateTime(timestamp: number): string {
  const date = new Date(timestamp * 1000);
  return date.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/**
 * Format hash for display (truncate middle)
 */
export function formatHash(hash: string, chars: number = 8): string {
  if (!hash || hash.length < chars * 2 + 3) {
    return hash || '';
  }
  return `${hash.substring(0, chars)}...${hash.substring(hash.length - chars)}`;
}

/**
 * Format uptime in seconds to human readable
 */
export function formatUptime(seconds: number): string {
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);

  const parts: string[] = [];
  if (days > 0) parts.push(`${days}d`);
  if (hours > 0) parts.push(`${hours}h`);
  if (minutes > 0) parts.push(`${minutes}m`);

  return parts.length > 0 ? parts.join(' ') : '< 1m';
}

/**
 * Format difficulty as human readable
 */
export function formatDifficulty(difficulty: number): string {
  if (difficulty >= 1_000_000) {
    return `${(difficulty / 1_000_000).toFixed(2)}M`;
  }
  if (difficulty >= 1_000) {
    return `${(difficulty / 1_000).toFixed(2)}K`;
  }
  return difficulty.toFixed(2);
}

/**
 * Parse XAI amount from string input
 */
export function parseXaiAmount(input: string): number | null {
  if (!input || input.trim() === '') {
    return null;
  }

  // Remove any non-numeric characters except decimal point
  const cleaned = input.replace(/[^0-9.]/g, '');

  // Ensure only one decimal point
  const parts = cleaned.split('.');
  if (parts.length > 2) {
    return null;
  }

  const parsed = parseFloat(cleaned);
  if (isNaN(parsed) || parsed < 0) {
    return null;
  }

  return parsed;
}

/**
 * Validate amount is within range
 */
export function validateAmount(
  amount: number,
  balance: number,
  minAmount: number = 0.0001
): { valid: boolean; error?: string } {
  if (amount < minAmount) {
    return { valid: false, error: `Minimum amount is ${formatXai(minAmount)} XAI` };
  }
  if (amount > balance) {
    return { valid: false, error: 'Insufficient balance' };
  }
  return { valid: true };
}
