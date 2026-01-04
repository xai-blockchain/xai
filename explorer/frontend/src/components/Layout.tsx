import { Outlet, Link, useLocation } from 'react-router-dom';
import { Blocks, ArrowRightLeft, Home, Cpu, Search, BarChart2, Trophy, Vote, Shield, Coins } from 'lucide-react';
import { clsx } from 'clsx';
import { SearchBar } from './SearchBar';

const navigation = [
  { name: 'Home', href: '/', icon: Home },
  { name: 'Blocks', href: '/blocks', icon: Blocks },
  { name: 'Transactions', href: '/transactions', icon: ArrowRightLeft },
  { name: 'AI Tasks', href: '/ai', icon: Cpu },
  { name: 'Validators', href: '/validators', icon: Shield },
  { name: 'Governance', href: '/governance', icon: Vote },
  { name: 'Staking', href: '/staking', icon: Coins },
  { name: 'Analytics', href: '/analytics', icon: BarChart2 },
];

export function Layout() {
  const location = useLocation();

  return (
    <div className="min-h-screen bg-xai-darker">
      {/* Devnet Banner */}
      <div className="bg-gradient-to-r from-amber-500 to-orange-500 text-white py-2 px-4">
        <div className="mx-auto max-w-7xl flex items-center justify-center gap-4 text-sm">
          <span className="bg-black/30 px-3 py-1 rounded text-xs font-bold tracking-wider">DEVNET</span>
          <span>This is an invite-only development network. Tokens have no value.</span>
          <a href="https://discord.gg/jqNEDhG8" target="_blank" rel="noopener noreferrer" className="underline hover:text-amber-100 font-medium">Apply via Discord</a>
        </div>
      </div>

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
                <h1 className="text-lg font-semibold text-white flex items-center gap-2">
                  XAI Explorer
                  <span className="text-xs bg-amber-500/20 text-amber-400 px-2 py-0.5 rounded">Devnet</span>
                </h1>
                <p className="text-xs text-xai-muted">AI-Powered Blockchain</p>
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
            <div className="text-sm text-xai-muted text-center sm:text-left">
              <p>XAI Blockchain Explorer - AI-Powered Blockchain</p>
              <p className="text-xs mt-1">Chain ID: xai-testnet-1 | Network: Devnet</p>
            </div>
            <div className="flex items-center gap-4 text-sm text-xai-muted">
              <a href="https://artifacts.xaiblockchain.com" target="_blank" rel="noopener" className="hover:text-xai-primary">Artifacts</a>
              <a href="/docs" className="hover:text-xai-primary">API Docs</a>
              <a href="https://github.com/xai-blockchain/testnets" target="_blank" rel="noopener" className="hover:text-xai-primary">GitHub</a>
              <a href="https://discord.gg/jqNEDhG8" target="_blank" rel="noopener" className="hover:text-xai-primary">Discord</a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
