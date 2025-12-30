import { describe, it, expect } from 'vitest';
import { render, screen } from '../__tests__/test-utils';
import { NotFound } from './NotFound';

describe('NotFound', () => {
  it('renders 404 heading', () => {
    render(<NotFound />);

    expect(screen.getByText('404')).toBeInTheDocument();
  });

  it('renders page not found message', () => {
    render(<NotFound />);

    expect(screen.getByText('Page Not Found')).toBeInTheDocument();
  });

  it('renders description text', () => {
    render(<NotFound />);

    expect(
      screen.getByText(/The page you're looking for doesn't exist or has been moved/)
    ).toBeInTheDocument();
  });

  it('renders Go Home link', () => {
    render(<NotFound />);

    const homeLink = screen.getByRole('link', { name: /Go Home/i });
    expect(homeLink).toBeInTheDocument();
    expect(homeLink).toHaveAttribute('href', '/');
  });

  it('renders Browse Blocks link', () => {
    render(<NotFound />);

    const blocksLink = screen.getByRole('link', { name: /Browse Blocks/i });
    expect(blocksLink).toBeInTheDocument();
    expect(blocksLink).toHaveAttribute('href', '/blocks');
  });

  it('has correct styling classes', () => {
    const { container } = render(<NotFound />);

    expect(container.firstChild).toHaveClass(
      'flex',
      'flex-col',
      'items-center',
      'justify-center',
      'py-20'
    );
  });

  it('renders icons in links', () => {
    const { container } = render(<NotFound />);

    // Should have 2 icons (Home and Search)
    const svgs = container.querySelectorAll('svg');
    expect(svgs.length).toBe(2);
  });
});
