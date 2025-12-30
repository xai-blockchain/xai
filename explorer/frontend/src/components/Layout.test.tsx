import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '../__tests__/test-utils';
import { Layout } from './Layout';
import { Routes, Route } from 'react-router-dom';

// Mock the SearchBar component to avoid hook complexities
vi.mock('./SearchBar', () => ({
  SearchBar: () => <div data-testid="search-bar">Search Bar</div>,
}));

function renderWithRoutes(initialPath = '/') {
  return render(
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<div>Home Content</div>} />
        <Route path="blocks" element={<div>Blocks Content</div>} />
        <Route path="transactions" element={<div>Transactions Content</div>} />
        <Route path="ai" element={<div>AI Tasks Content</div>} />
      </Route>
    </Routes>,
    { initialEntries: [initialPath] }
  );
}

describe('Layout', () => {
  it('renders logo and brand name', () => {
    renderWithRoutes();

    expect(screen.getByText('XAI Explorer')).toBeInTheDocument();
    expect(screen.getByText('Blockchain Explorer')).toBeInTheDocument();
  });

  it('renders navigation links', () => {
    renderWithRoutes();

    expect(screen.getAllByText('Home').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Blocks').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Transactions').length).toBeGreaterThan(0);
    expect(screen.getAllByText('AI Tasks').length).toBeGreaterThan(0);
  });

  it('renders search bar', () => {
    renderWithRoutes();

    expect(screen.getByTestId('search-bar')).toBeInTheDocument();
  });

  it('renders main content area with outlet', () => {
    renderWithRoutes('/');

    expect(screen.getByText('Home Content')).toBeInTheDocument();
  });

  it('renders different content based on route', () => {
    renderWithRoutes('/blocks');

    expect(screen.getByText('Blocks Content')).toBeInTheDocument();
  });

  it('renders footer', () => {
    renderWithRoutes();

    expect(
      screen.getByText('XAI Blockchain Explorer - AI-Powered Blockchain')
    ).toBeInTheDocument();
  });

  it('renders footer links', () => {
    renderWithRoutes();

    expect(screen.getByText('API Docs')).toBeInTheDocument();
    expect(screen.getByText('GitHub')).toBeInTheDocument();
  });

  it('highlights active navigation link for Home', () => {
    renderWithRoutes('/');

    // Find the desktop nav links
    const homeLinks = screen.getAllByText('Home');
    const activeHomeLink = homeLinks.find((link) =>
      link.closest('a')?.classList.contains('bg-xai-primary/10')
    );
    expect(activeHomeLink).toBeTruthy();
  });

  it('highlights active navigation link for Blocks', () => {
    renderWithRoutes('/blocks');

    const blocksLinks = screen.getAllByText('Blocks');
    const activeBlocksLink = blocksLinks.find((link) =>
      link.closest('a')?.classList.contains('bg-xai-primary/10')
    );
    expect(activeBlocksLink).toBeTruthy();
  });

  it('highlights active navigation link for AI Tasks', () => {
    renderWithRoutes('/ai');

    const aiLinks = screen.getAllByText('AI Tasks');
    const activeAiLink = aiLinks.find((link) =>
      link.closest('a')?.classList.contains('bg-xai-primary/10')
    );
    expect(activeAiLink).toBeTruthy();
  });

  it('has correct page layout structure', () => {
    const { container } = renderWithRoutes();

    // Should have min-h-screen
    expect(container.firstChild).toHaveClass('min-h-screen', 'bg-xai-darker');
  });

  it('renders header with sticky positioning', () => {
    renderWithRoutes();

    const header = document.querySelector('header');
    expect(header).toHaveClass('sticky', 'top-0', 'z-50');
  });

  it('renders mobile navigation', () => {
    renderWithRoutes();

    // Mobile nav should be present (md:hidden class)
    const mobileNav = document.querySelector('nav.md\\:hidden');
    expect(mobileNav).toBeInTheDocument();
  });

  it('logo links to home', () => {
    renderWithRoutes('/blocks');

    const logoLink = screen.getByText('XAI Explorer').closest('a');
    expect(logoLink).toHaveAttribute('href', '/');
  });
});
