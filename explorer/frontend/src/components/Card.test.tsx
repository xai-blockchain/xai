import { describe, it, expect } from 'vitest';
import { render, screen } from '../__tests__/test-utils';
import { Card, CardHeader } from './Card';

describe('Card', () => {
  it('renders children correctly', () => {
    render(
      <Card>
        <p>Card content</p>
      </Card>
    );

    expect(screen.getByText('Card content')).toBeInTheDocument();
  });

  it('applies default medium padding', () => {
    const { container } = render(
      <Card>
        <p>Content</p>
      </Card>
    );

    expect(container.firstChild).toHaveClass('p-6');
  });

  it('applies no padding when padding="none"', () => {
    const { container } = render(
      <Card padding="none">
        <p>Content</p>
      </Card>
    );

    expect(container.firstChild).toHaveClass('p-0');
  });

  it('applies small padding when padding="sm"', () => {
    const { container } = render(
      <Card padding="sm">
        <p>Content</p>
      </Card>
    );

    expect(container.firstChild).toHaveClass('p-4');
  });

  it('applies large padding when padding="lg"', () => {
    const { container } = render(
      <Card padding="lg">
        <p>Content</p>
      </Card>
    );

    expect(container.firstChild).toHaveClass('p-8');
  });

  it('applies custom className', () => {
    const { container } = render(
      <Card className="custom-class">
        <p>Content</p>
      </Card>
    );

    expect(container.firstChild).toHaveClass('custom-class');
  });

  it('has correct base styles', () => {
    const { container } = render(
      <Card>
        <p>Content</p>
      </Card>
    );

    expect(container.firstChild).toHaveClass('rounded-xl');
    expect(container.firstChild).toHaveClass('border');
    expect(container.firstChild).toHaveClass('border-xai-border');
    expect(container.firstChild).toHaveClass('bg-xai-card');
  });
});

describe('CardHeader', () => {
  it('renders title correctly', () => {
    render(<CardHeader title="Test Title" />);

    expect(screen.getByText('Test Title')).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 3 })).toHaveTextContent('Test Title');
  });

  it('renders subtitle when provided', () => {
    render(<CardHeader title="Title" subtitle="Subtitle text" />);

    expect(screen.getByText('Subtitle text')).toBeInTheDocument();
  });

  it('does not render subtitle when not provided', () => {
    render(<CardHeader title="Title" />);

    expect(screen.queryByText('Subtitle text')).not.toBeInTheDocument();
  });

  it('renders action when provided', () => {
    render(
      <CardHeader
        title="Title"
        action={<button>Click me</button>}
      />
    );

    expect(screen.getByRole('button', { name: 'Click me' })).toBeInTheDocument();
  });
});
