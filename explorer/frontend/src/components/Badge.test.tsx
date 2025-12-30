import { describe, it, expect } from 'vitest';
import { render, screen } from '../__tests__/test-utils';
import { Badge, getStatusVariant } from './Badge';

describe('Badge', () => {
  it('renders children correctly', () => {
    render(<Badge>Test Badge</Badge>);

    expect(screen.getByText('Test Badge')).toBeInTheDocument();
  });

  it('applies default variant styles', () => {
    const { container } = render(<Badge>Default</Badge>);

    expect(container.firstChild).toHaveClass('bg-gray-500/20');
    expect(container.firstChild).toHaveClass('text-gray-400');
  });

  it('applies success variant styles', () => {
    const { container } = render(<Badge variant="success">Success</Badge>);

    expect(container.firstChild).toHaveClass('bg-green-500/20');
    expect(container.firstChild).toHaveClass('text-green-400');
  });

  it('applies warning variant styles', () => {
    const { container } = render(<Badge variant="warning">Warning</Badge>);

    expect(container.firstChild).toHaveClass('bg-yellow-500/20');
    expect(container.firstChild).toHaveClass('text-yellow-400');
  });

  it('applies error variant styles', () => {
    const { container } = render(<Badge variant="error">Error</Badge>);

    expect(container.firstChild).toHaveClass('bg-red-500/20');
    expect(container.firstChild).toHaveClass('text-red-400');
  });

  it('applies info variant styles', () => {
    const { container } = render(<Badge variant="info">Info</Badge>);

    expect(container.firstChild).toHaveClass('bg-blue-500/20');
    expect(container.firstChild).toHaveClass('text-blue-400');
  });

  it('applies primary variant styles', () => {
    const { container } = render(<Badge variant="primary">Primary</Badge>);

    expect(container.firstChild).toHaveClass('bg-xai-primary/20');
    expect(container.firstChild).toHaveClass('text-xai-primary');
  });

  it('applies custom className', () => {
    const { container } = render(
      <Badge className="custom-badge-class">Custom</Badge>
    );

    expect(container.firstChild).toHaveClass('custom-badge-class');
  });

  it('has correct base styles', () => {
    const { container } = render(<Badge>Test</Badge>);

    expect(container.firstChild).toHaveClass('inline-flex');
    expect(container.firstChild).toHaveClass('items-center');
    expect(container.firstChild).toHaveClass('px-2.5');
    expect(container.firstChild).toHaveClass('py-0.5');
    expect(container.firstChild).toHaveClass('rounded-full');
    expect(container.firstChild).toHaveClass('text-xs');
    expect(container.firstChild).toHaveClass('font-medium');
  });
});

describe('getStatusVariant', () => {
  it('returns success for confirmed status', () => {
    expect(getStatusVariant('confirmed')).toBe('success');
    expect(getStatusVariant('CONFIRMED')).toBe('success');
  });

  it('returns success for completed status', () => {
    expect(getStatusVariant('completed')).toBe('success');
    expect(getStatusVariant('COMPLETED')).toBe('success');
  });

  it('returns success for success status', () => {
    expect(getStatusVariant('success')).toBe('success');
    expect(getStatusVariant('SUCCESS')).toBe('success');
  });

  it('returns warning for pending status', () => {
    expect(getStatusVariant('pending')).toBe('warning');
    expect(getStatusVariant('PENDING')).toBe('warning');
  });

  it('returns warning for in_progress status', () => {
    expect(getStatusVariant('in_progress')).toBe('warning');
    expect(getStatusVariant('IN_PROGRESS')).toBe('warning');
  });

  it('returns error for failed status', () => {
    expect(getStatusVariant('failed')).toBe('error');
    expect(getStatusVariant('FAILED')).toBe('error');
  });

  it('returns error for error status', () => {
    expect(getStatusVariant('error')).toBe('error');
    expect(getStatusVariant('ERROR')).toBe('error');
  });

  it('returns default for unknown status', () => {
    expect(getStatusVariant('unknown')).toBe('default');
    expect(getStatusVariant('anything')).toBe('default');
  });
});
