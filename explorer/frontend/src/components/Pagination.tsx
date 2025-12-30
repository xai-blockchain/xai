import { ChevronLeft, ChevronRight } from 'lucide-react';
import { clsx } from 'clsx';

interface PaginationProps {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}

export function Pagination({ currentPage, totalPages, onPageChange }: PaginationProps) {
  const pages = generatePageNumbers(currentPage, totalPages);

  if (totalPages <= 1) return null;

  return (
    <div className="flex items-center justify-center gap-1 mt-6">
      <button
        onClick={() => onPageChange(currentPage - 1)}
        disabled={currentPage === 1}
        className={clsx(
          'flex items-center justify-center h-9 w-9 rounded-lg text-sm transition-colors',
          currentPage === 1
            ? 'text-xai-muted cursor-not-allowed'
            : 'text-white hover:bg-xai-card'
        )}
      >
        <ChevronLeft className="h-4 w-4" />
      </button>

      {pages.map((page, index) => (
        <button
          key={index}
          onClick={() => typeof page === 'number' && onPageChange(page)}
          disabled={page === '...'}
          className={clsx(
            'flex items-center justify-center h-9 min-w-9 px-2 rounded-lg text-sm transition-colors',
            page === currentPage
              ? 'bg-xai-primary text-black font-medium'
              : page === '...'
              ? 'text-xai-muted cursor-default'
              : 'text-white hover:bg-xai-card'
          )}
        >
          {page}
        </button>
      ))}

      <button
        onClick={() => onPageChange(currentPage + 1)}
        disabled={currentPage === totalPages}
        className={clsx(
          'flex items-center justify-center h-9 w-9 rounded-lg text-sm transition-colors',
          currentPage === totalPages
            ? 'text-xai-muted cursor-not-allowed'
            : 'text-white hover:bg-xai-card'
        )}
      >
        <ChevronRight className="h-4 w-4" />
      </button>
    </div>
  );
}

function generatePageNumbers(current: number, total: number): (number | '...')[] {
  if (total <= 7) {
    return Array.from({ length: total }, (_, i) => i + 1);
  }

  const pages: (number | '...')[] = [];

  if (current <= 3) {
    pages.push(1, 2, 3, 4, '...', total);
  } else if (current >= total - 2) {
    pages.push(1, '...', total - 3, total - 2, total - 1, total);
  } else {
    pages.push(1, '...', current - 1, current, current + 1, '...', total);
  }

  return pages;
}
