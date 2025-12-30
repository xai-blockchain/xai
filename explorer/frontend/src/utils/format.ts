import { formatDistanceToNow, format } from 'date-fns';

export function truncateHash(hash: string, startLen = 8, endLen = 6): string {
  if (hash.length <= startLen + endLen + 3) return hash;
  return `${hash.slice(0, startLen)}...${hash.slice(-endLen)}`;
}

export function truncateAddress(address: string, len = 8): string {
  if (address.length <= len * 2 + 3) return address;
  return `${address.slice(0, len)}...${address.slice(-len)}`;
}

export function formatAmount(amount: string | number, decimals = 8): string {
  const num = typeof amount === 'string' ? parseFloat(amount) : amount;
  if (isNaN(num)) return '0';
  return num.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: decimals,
  });
}

export function formatXAI(amount: string | number): string {
  return `${formatAmount(amount)} XAI`;
}

export function formatTimeAgo(timestamp: string | Date): string {
  const date = typeof timestamp === 'string' ? new Date(timestamp) : timestamp;
  return formatDistanceToNow(date, { addSuffix: true });
}

export function formatDate(timestamp: string | Date): string {
  const date = typeof timestamp === 'string' ? new Date(timestamp) : timestamp;
  return format(date, 'MMM d, yyyy HH:mm:ss');
}

export function formatNumber(num: number): string {
  if (num >= 1_000_000_000) {
    return `${(num / 1_000_000_000).toFixed(2)}B`;
  }
  if (num >= 1_000_000) {
    return `${(num / 1_000_000).toFixed(2)}M`;
  }
  if (num >= 1_000) {
    return `${(num / 1_000).toFixed(2)}K`;
  }
  return num.toLocaleString();
}

export function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
}

export function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds.toFixed(0)}s`;
  if (seconds < 3600) {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}m ${secs}s`;
  }
  const hours = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  return `${hours}h ${mins}m`;
}

export function formatUSD(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);
}

export function formatPercentage(value: number): string {
  return `${value.toFixed(1)}%`;
}

export function getStatusColor(status: string): string {
  switch (status.toLowerCase()) {
    case 'confirmed':
    case 'completed':
    case 'success':
      return 'text-green-400';
    case 'pending':
    case 'in_progress':
      return 'text-yellow-400';
    case 'failed':
    case 'error':
      return 'text-red-400';
    default:
      return 'text-xai-muted';
  }
}

export function getComplexityColor(complexity: string): string {
  switch (complexity.toLowerCase()) {
    case 'low':
      return 'bg-green-500/20 text-green-400';
    case 'moderate':
      return 'bg-yellow-500/20 text-yellow-400';
    case 'complex':
      return 'bg-orange-500/20 text-orange-400';
    case 'critical':
      return 'bg-red-500/20 text-red-400';
    default:
      return 'bg-gray-500/20 text-gray-400';
  }
}
