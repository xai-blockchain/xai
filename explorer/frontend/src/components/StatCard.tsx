import { clsx } from 'clsx';
import type { LucideIcon } from 'lucide-react';

interface StatCardProps {
  label: string;
  value: string | number;
  icon?: LucideIcon;
  change?: {
    value: number;
    label: string;
  };
  className?: string;
}

export function StatCard({ label, value, icon: Icon, change, className }: StatCardProps) {
  return (
    <div
      className={clsx(
        'rounded-xl border border-xai-border bg-xai-card p-6',
        className
      )}
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-xai-muted">{label}</p>
          <p className="mt-2 text-2xl font-semibold text-white">{value}</p>
          {change && (
            <p
              className={clsx(
                'mt-1 text-sm',
                change.value >= 0 ? 'text-green-400' : 'text-red-400'
              )}
            >
              {change.value >= 0 ? '+' : ''}
              {change.value}% {change.label}
            </p>
          )}
        </div>
        {Icon && (
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-xai-primary/10">
            <Icon className="h-5 w-5 text-xai-primary" />
          </div>
        )}
      </div>
    </div>
  );
}
