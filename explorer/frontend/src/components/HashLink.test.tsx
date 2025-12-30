import { describe, it, expect } from 'vitest';
import { render, screen } from '../__tests__/test-utils';
import { HashLink, AddressLink } from './HashLink';

describe('HashLink', () => {
  const longHash = '0000000000000000000abc123def456789012345678901234567890123456789';

  it('renders link with truncated hash by default', () => {
    render(<HashLink hash={longHash} to="/block/123" />);

    const link = screen.getByRole('link');
    expect(link).toBeInTheDocument();
    expect(link).toHaveTextContent('00000000...456789');
    expect(link).toHaveAttribute('href', '/block/123');
  });

  it('renders full hash when truncate is false', () => {
    render(<HashLink hash={longHash} to="/block/123" truncate={false} />);

    expect(screen.getByRole('link')).toHaveTextContent(longHash);
  });

  it('shows full hash in title attribute', () => {
    render(<HashLink hash={longHash} to="/block/123" />);

    expect(screen.getByRole('link')).toHaveAttribute('title', longHash);
  });

  it('renders copy button when showCopy is true', () => {
    render(<HashLink hash={longHash} to="/block/123" showCopy />);

    expect(screen.getByRole('button')).toBeInTheDocument();
  });

  it('does not render copy button by default', () => {
    render(<HashLink hash={longHash} to="/block/123" />);

    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });

  it('applies custom className', () => {
    render(<HashLink hash={longHash} to="/block/123" className="custom-link" />);

    expect(screen.getByRole('link')).toHaveClass('custom-link');
  });

  it('has correct base styles', () => {
    render(<HashLink hash={longHash} to="/block/123" />);

    const link = screen.getByRole('link');
    expect(link).toHaveClass('font-mono', 'text-xai-primary', 'hover:underline');
  });

  it('wraps link and copy button in span', () => {
    const { container } = render(<HashLink hash={longHash} to="/block/123" showCopy />);

    const wrapper = container.firstChild;
    expect(wrapper?.nodeName).toBe('SPAN');
    expect(wrapper).toHaveClass('inline-flex', 'items-center', 'gap-1');
  });
});

describe('AddressLink', () => {
  const longAddress = 'XAIaddress123456789012345678901234567890';

  it('renders link to address page', () => {
    render(<AddressLink address={longAddress} />);

    const link = screen.getByRole('link');
    expect(link).toHaveAttribute('href', `/address/${longAddress}`);
  });

  it('renders truncated address by default', () => {
    render(<AddressLink address={longAddress} />);

    const link = screen.getByRole('link');
    // truncateHash(address, 6, 6) is used
    expect(link).toHaveTextContent('XAIadd...567890');
  });

  it('renders full address when truncate is false', () => {
    render(<AddressLink address={longAddress} truncate={false} />);

    expect(screen.getByRole('link')).toHaveTextContent(longAddress);
  });

  it('shows full address in title attribute', () => {
    render(<AddressLink address={longAddress} />);

    expect(screen.getByRole('link')).toHaveAttribute('title', longAddress);
  });

  it('renders copy button when showCopy is true', () => {
    render(<AddressLink address={longAddress} showCopy />);

    expect(screen.getByRole('button')).toBeInTheDocument();
  });

  it('does not render copy button by default', () => {
    render(<AddressLink address={longAddress} />);

    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });

  it('applies custom className', () => {
    render(<AddressLink address={longAddress} className="custom-address-link" />);

    expect(screen.getByRole('link')).toHaveClass('custom-address-link');
  });

  it('has correct base styles', () => {
    render(<AddressLink address={longAddress} />);

    const link = screen.getByRole('link');
    expect(link).toHaveClass('font-mono', 'text-xai-primary', 'hover:underline');
  });

  it('handles short address without truncation', () => {
    const shortAddress = 'XAI123';
    render(<AddressLink address={shortAddress} />);

    expect(screen.getByRole('link')).toHaveTextContent('XAI123');
  });
});
