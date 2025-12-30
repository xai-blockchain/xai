import { describe, it, expect } from 'vitest';
import { render, screen } from '../__tests__/test-utils';
import { Loading, LoadingSkeleton } from './Loading';

describe('Loading', () => {
  it('renders default loading message', () => {
    render(<Loading />);

    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });

  it('renders custom message', () => {
    render(<Loading message="Fetching data..." />);

    expect(screen.getByText('Fetching data...')).toBeInTheDocument();
  });

  it('renders spinner with correct default size', () => {
    const { container } = render(<Loading />);

    const spinner = container.querySelector('svg');
    expect(spinner).toBeInTheDocument();
    expect(spinner).toHaveClass('h-8', 'w-8');
  });

  it('renders spinner with small size', () => {
    const { container } = render(<Loading size="sm" />);

    const spinner = container.querySelector('svg');
    expect(spinner).toHaveClass('h-4', 'w-4');
  });

  it('renders spinner with large size', () => {
    const { container } = render(<Loading size="lg" />);

    const spinner = container.querySelector('svg');
    expect(spinner).toHaveClass('h-12', 'w-12');
  });

  it('has spinning animation', () => {
    const { container } = render(<Loading />);

    const spinner = container.querySelector('svg');
    expect(spinner).toHaveClass('animate-spin');
  });

  it('has correct layout styles', () => {
    const { container } = render(<Loading />);

    expect(container.firstChild).toHaveClass('flex', 'flex-col', 'items-center', 'justify-center', 'py-12');
  });
});

describe('LoadingSkeleton', () => {
  it('renders skeleton elements', () => {
    const { container } = render(<LoadingSkeleton />);

    // Should have 3 skeleton bars
    const bars = container.querySelectorAll('.bg-xai-border');
    expect(bars.length).toBe(3);
  });

  it('has pulse animation', () => {
    const { container } = render(<LoadingSkeleton />);

    expect(container.firstChild).toHaveClass('animate-pulse');
  });

  it('has different width skeleton bars', () => {
    const { container } = render(<LoadingSkeleton />);

    const bars = container.querySelectorAll('.bg-xai-border');
    expect(bars[0]).toHaveClass('w-3/4');
    expect(bars[1]).toHaveClass('w-1/2');
    expect(bars[2]).toHaveClass('w-5/6');
  });
});
