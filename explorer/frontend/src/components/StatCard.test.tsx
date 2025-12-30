import { describe, it, expect } from 'vitest';
import { render, screen } from '../__tests__/test-utils';
import { StatCard } from './StatCard';
import { Activity, Cpu } from 'lucide-react';

describe('StatCard', () => {
  it('renders label and value correctly', () => {
    render(<StatCard label="Total Blocks" value="12,345" />);

    expect(screen.getByText('Total Blocks')).toBeInTheDocument();
    expect(screen.getByText('12,345')).toBeInTheDocument();
  });

  it('renders numeric value correctly', () => {
    render(<StatCard label="Count" value={99} />);

    expect(screen.getByText('99')).toBeInTheDocument();
  });

  it('renders icon when provided', () => {
    const { container } = render(
      <StatCard label="Activity" value="100" icon={Activity} />
    );

    // Icon should be rendered (lucide-react renders SVG)
    const svg = container.querySelector('svg');
    expect(svg).toBeInTheDocument();
  });

  it('renders positive change correctly', () => {
    render(
      <StatCard
        label="Revenue"
        value="$1,000"
        change={{ value: 15, label: 'vs last week' }}
      />
    );

    expect(screen.getByText('+15% vs last week')).toBeInTheDocument();
    expect(screen.getByText('+15% vs last week')).toHaveClass('text-green-400');
  });

  it('renders negative change correctly', () => {
    render(
      <StatCard
        label="Users"
        value="500"
        change={{ value: -10, label: 'vs yesterday' }}
      />
    );

    expect(screen.getByText('-10% vs yesterday')).toBeInTheDocument();
    expect(screen.getByText('-10% vs yesterday')).toHaveClass('text-red-400');
  });

  it('does not render change when not provided', () => {
    render(<StatCard label="Simple" value="100" />);

    expect(screen.queryByText('%')).not.toBeInTheDocument();
  });

  it('applies custom className', () => {
    const { container } = render(
      <StatCard label="Custom" value="200" className="custom-stat-class" />
    );

    expect(container.firstChild).toHaveClass('custom-stat-class');
  });

  it('has correct base styles', () => {
    const { container } = render(<StatCard label="Test" value="300" />);

    expect(container.firstChild).toHaveClass('rounded-xl');
    expect(container.firstChild).toHaveClass('border');
    expect(container.firstChild).toHaveClass('border-xai-border');
    expect(container.firstChild).toHaveClass('bg-xai-card');
    expect(container.firstChild).toHaveClass('p-6');
  });

  it('renders zero change as positive', () => {
    render(
      <StatCard
        label="Stable"
        value="1000"
        change={{ value: 0, label: 'no change' }}
      />
    );

    expect(screen.getByText('+0% no change')).toBeInTheDocument();
    expect(screen.getByText('+0% no change')).toHaveClass('text-green-400');
  });
});
