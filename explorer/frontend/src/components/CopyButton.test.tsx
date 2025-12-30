import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '../__tests__/test-utils';
import { CopyButton } from './CopyButton';

describe('CopyButton', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders copy button', () => {
    render(<CopyButton text="test text" />);

    const button = screen.getByRole('button');
    expect(button).toBeInTheDocument();
    expect(button).toHaveAttribute('title', 'Copy to clipboard');
  });

  it('applies custom className', () => {
    render(<CopyButton text="test" className="custom-copy-btn" />);

    expect(screen.getByRole('button')).toHaveClass('custom-copy-btn');
  });

  it('has correct base styles', () => {
    render(<CopyButton text="test" />);

    const button = screen.getByRole('button');
    expect(button).toHaveClass('inline-flex', 'items-center', 'justify-center');
    expect(button).toHaveClass('h-6', 'w-6', 'rounded');
    expect(button).toHaveClass('text-xai-muted', 'hover:text-xai-primary');
  });

  it('has correct transition classes', () => {
    render(<CopyButton text="test" />);

    const button = screen.getByRole('button');
    expect(button).toHaveClass('transition-colors');
  });

  it('renders SVG icon', () => {
    const { container } = render(<CopyButton text="test" />);

    const svg = container.querySelector('svg');
    expect(svg).toBeInTheDocument();
    expect(svg).toHaveClass('h-3.5', 'w-3.5');
  });

  it('is clickable', () => {
    render(<CopyButton text="test" />);

    const button = screen.getByRole('button');
    expect(() => fireEvent.click(button)).not.toThrow();
  });

  it('accepts text prop for clipboard content', () => {
    render(<CopyButton text="copy this text" />);

    const button = screen.getByRole('button');
    expect(button).toBeInTheDocument();
  });
});
