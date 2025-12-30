import { Outlet, Link, useLocation } from 'react-router-dom';
import { Blocks, ArrowRightLeft, Home, Cpu, Search } from 'lucide-react';
import { clsx } from 'clsx';
import { SearchBar } from './SearchBar';

const navigation = [
  { name: 'Home', href: '/', icon: Home },
  { name: 'Blocks', href: '/blocks', icon: Blocks },
  { name: 'Transactions', href: '/transactions', icon: ArrowRightLeft },
  { name: 'AI Tasks', href: '/ai', icon: Cpu },
];

export function Layout() {
  const location = useLocation();

  return (
    <div className="min-h-screen bg-xai-darker">
      {/* Header */}
      <header className="sticky top-0 z-50 border-b border-xai-border bg-xai-dark/95 backdrop-blur">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between">
            {/* Logo */}
            <Link to="/" className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-xai-primary/10">
                <span className="text-xl font-bold text-xai-primary">X</span>
              </div>
              <div>
                <h1 className="text-lg font-semibold text-white">XAI Explorer</h1>
                <p className="text-xs text-xai-muted">Blockchain Explorer</p>
              </div>
            </Link>

            {/* Navigation */}
            <nav className="hidden md:flex items-center gap-1">
              {navigation.map((item) => {
                const isActive = location.pathname === item.href ||
                  (item.href !== '/' && location.pathname.startsWith(item.href));
                return (
                  <Link
                    key={item.name}
                    to={item.href}
                    className={clsx(
                      'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors',
                      isActive
                        ? 'bg-xai-primary/10 text-xai-primary'
                        : 'text-xai-muted hover:text-white hover:bg-xai-card'
                    )}
                  >
                    <item.icon className="h-4 w-4" />
                    {item.name}
                  </Link>
                );
              })}
            </nav>

            {/* Search */}
            <div className="hidden lg:block w-80">
              <SearchBar />
            </div>

            {/* Mobile search button */}
            <button className="lg:hidden p-2 text-xai-muted hover:text-white">
              <Search className="h-5 w-5" />
            </button>
          </div>
        </div>
      </header>

      {/* Mobile Navigation */}
      <nav className="md:hidden border-b border-xai-border bg-xai-dark">
        <div className="flex overflow-x-auto px-4 py-2 gap-2">
          {navigation.map((item) => {
            const isActive = location.pathname === item.href ||
              (item.href !== '/' && location.pathname.startsWith(item.href));
            return (
              <Link
                key={item.name}
                to={item.href}
                className={clsx(
                  'flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium whitespace-nowrap transition-colors',
                  isActive
                    ? 'bg-xai-primary/10 text-xai-primary'
                    : 'text-xai-muted hover:text-white'
                )}
              >
                <item.icon className="h-4 w-4" />
                {item.name}
              </Link>
            );
          })}
        </div>
      </nav>

      {/* Main Content */}
      <main className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-8">
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="border-t border-xai-border bg-xai-dark mt-auto">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
            <p className="text-sm text-xai-muted">
              XAI Blockchain Explorer - AI-Powered Blockchain
            </p>
            <div className="flex items-center gap-4 text-sm text-xai-muted">
              <a href="/docs" className="hover:text-xai-primary">API Docs</a>
              <a href="https://github.com/xai" className="hover:text-xai-primary">GitHub</a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
