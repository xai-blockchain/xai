import { clsx } from 'clsx';
import type { ReactNode } from 'react';

type BadgeVariant = 'default' | 'success' | 'warning' | 'error' | 'info' | 'primary';

interface BadgeProps {
  children: ReactNode;
  variant?: BadgeVariant;
  className?: string;
}

const variantStyles: Record<BadgeVariant, string> = {
  default: 'bg-gray-500/20 text-gray-400',
  success: 'bg-green-500/20 text-green-400',
  warning: 'bg-yellow-500/20 text-yellow-400',
  error: 'bg-red-500/20 text-red-400',
  info: 'bg-blue-500/20 text-blue-400',
  primary: 'bg-xai-primary/20 text-xai-primary',
};

export function Badge({ children, variant = 'default', className }: BadgeProps) {
  return (
    <span
      className={clsx(
        'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
        variantStyles[variant],
        className
      )}
    >
      {children}
    </span>
  );
}

export function getStatusVariant(status: string): BadgeVariant {
  switch (status.toLowerCase()) {
    case 'confirmed':
    case 'completed':
    case 'success':
      return 'success';
    case 'pending':
    case 'in_progress':
      return 'warning';
    case 'failed':
    case 'error':
      return 'error';
    default:
      return 'default';
  }
}
