/**
 * Format balance for display
 */
export const formatBalance = (balance: number, decimals: number = 6): string => {
  return balance.toFixed(decimals);
};

/**
 * Format large numbers with commas
 */
export const formatNumber = (num: number): string => {
  return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
};

/**
 * Format timestamp to readable date
 */
export const formatDate = (timestamp: number): string => {
  const date = new Date(timestamp * 1000);
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};

/**
 * Format relative time (e.g., "2 hours ago")
 */
export const formatRelativeTime = (timestamp: number): string => {
  const now = Date.now();
  const diff = now - timestamp * 1000;
  const seconds = Math.floor(diff / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);

  if (days > 0) return `${days} day${days > 1 ? 's' : ''} ago`;
  if (hours > 0) return `${hours} hour${hours > 1 ? 's' : ''} ago`;
  if (minutes > 0) return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
  return 'Just now';
};

/**
 * Format transaction ID for display
 */
export const formatTxId = (txid: string, chars: number = 8): string => {
  if (!txid || txid.length < chars * 2) return txid;
  return `${txid.substring(0, chars)}...${txid.substring(txid.length - chars)}`;
};

/**
 * Validate and parse amount input
 */
export const parseAmount = (input: string): number | null => {
  const cleaned = input.replace(/[^0-9.]/g, '');
  const parsed = parseFloat(cleaned);
  return isNaN(parsed) ? null : parsed;
};

/**
 * Format currency with symbol
 */
export const formatCurrency = (amount: number, symbol: string = 'XAI'): string => {
  return `${formatBalance(amount)} ${symbol}`;
};
