import { Loader2 } from 'lucide-react';

interface LoadingProps {
  message?: string;
  size?: 'sm' | 'md' | 'lg';
}

export function Loading({ message = 'Loading...', size = 'md' }: LoadingProps) {
  const sizeClasses = {
    sm: 'h-4 w-4',
    md: 'h-8 w-8',
    lg: 'h-12 w-12',
  };

  return (
    <div className="flex flex-col items-center justify-center py-12">
      <Loader2 className={`${sizeClasses[size]} text-xai-primary animate-spin`} />
      <p className="mt-4 text-sm text-xai-muted">{message}</p>
    </div>
  );
}

export function LoadingSkeleton() {
  return (
    <div className="animate-pulse">
      <div className="h-4 bg-xai-border rounded w-3/4 mb-4"></div>
      <div className="h-4 bg-xai-border rounded w-1/2 mb-4"></div>
      <div className="h-4 bg-xai-border rounded w-5/6"></div>
    </div>
  );
}
