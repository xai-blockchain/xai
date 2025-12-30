import { useState, useRef, useEffect } from 'react';
import { Search, Loader2, X } from 'lucide-react';
import { useSearch } from '../hooks/useSearch';

export function SearchBar() {
  const [isFocused, setIsFocused] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const { query, setQuery, isSearching, handleSearch } = useSearch();

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    handleSearch(query);
  };

  const onClear = () => {
    setQuery('');
    inputRef.current?.focus();
  };

  // Keyboard shortcut: Ctrl/Cmd + K to focus search
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        inputRef.current?.focus();
      }
      if (e.key === 'Escape' && isFocused) {
        inputRef.current?.blur();
        setIsFocused(false);
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isFocused]);

  return (
    <form onSubmit={onSubmit} className="relative">
      <div className="relative">
        <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
          {isSearching ? (
            <Loader2 className="h-4 w-4 text-xai-muted animate-spin" />
          ) : (
            <Search className="h-4 w-4 text-xai-muted" />
          )}
        </div>
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          placeholder="Search by block, tx, address..."
          className="block w-full rounded-lg border border-xai-border bg-xai-card py-2 pl-10 pr-10 text-sm text-white placeholder-xai-muted focus:border-xai-primary focus:outline-none focus:ring-1 focus:ring-xai-primary"
        />
        {query && (
          <button
            type="button"
            onClick={onClear}
            className="absolute inset-y-0 right-0 flex items-center pr-3 text-xai-muted hover:text-white"
          >
            <X className="h-4 w-4" />
          </button>
        )}
        {!query && !isFocused && (
          <div className="absolute inset-y-0 right-0 flex items-center pr-3">
            <kbd className="hidden sm:inline-flex h-5 items-center gap-1 rounded border border-xai-border bg-xai-dark px-1.5 font-mono text-[10px] text-xai-muted">
              <span className="text-xs">Ctrl</span>K
            </kbd>
          </div>
        )}
      </div>
    </form>
  );
}
