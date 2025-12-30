import { describe, it, expect, beforeAll, afterAll, afterEach } from 'vitest';
import { render, screen, waitFor } from '../__tests__/test-utils';
import { server } from '../__tests__/mocks/server';
import { Home } from './Home';

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe('Home', () => {
  it('renders hero section', () => {
    render(<Home />);

    expect(screen.getByText('XAI Blockchain Explorer')).toBeInTheDocument();
    expect(
      screen.getByText(/Explore blocks, transactions, and AI compute tasks/)
    ).toBeInTheDocument();
  });

  it('renders network stat cards', async () => {
    render(<Home />);

    // Wait for data to load
    await waitFor(() => {
      expect(screen.getByText('Total Blocks')).toBeInTheDocument();
    });

    expect(screen.getByText('Total Transactions')).toBeInTheDocument();
    expect(screen.getByText('Active Addresses')).toBeInTheDocument();
    expect(screen.getByText('Avg Block Time')).toBeInTheDocument();
  });

  it('renders AI stat cards', async () => {
    render(<Home />);

    await waitFor(() => {
      expect(screen.getByText('AI Tasks')).toBeInTheDocument();
    });

    expect(screen.getByText('Active Providers')).toBeInTheDocument();
    expect(screen.getByText('Success Rate')).toBeInTheDocument();
    expect(screen.getByText('Active Tasks')).toBeInTheDocument();
  });

  it('renders Recent Blocks section', async () => {
    render(<Home />);

    await waitFor(() => {
      expect(screen.getByText('Recent Blocks')).toBeInTheDocument();
    });

    // View All link should point to blocks
    const viewAllLink = screen.getAllByText('View All')[0];
    expect(viewAllLink).toHaveAttribute('href', '/blocks');
  });

  it('renders Recent AI Tasks section', async () => {
    render(<Home />);

    await waitFor(() => {
      expect(screen.getByText('Recent AI Tasks')).toBeInTheDocument();
    });

    // View All link should point to AI tasks
    const viewAllLinks = screen.getAllByText('View All');
    expect(viewAllLinks[1]).toHaveAttribute('href', '/ai');
  });

  it('renders Network Information section', async () => {
    render(<Home />);

    await waitFor(() => {
      expect(screen.getByText('Network Information')).toBeInTheDocument();
    });

    expect(screen.getByText('Network Hashrate')).toBeInTheDocument();
    expect(screen.getByText('Difficulty')).toBeInTheDocument();
    expect(screen.getByText('Total Supply')).toBeInTheDocument();
    expect(screen.getByText('Pending Transactions')).toBeInTheDocument();
    expect(screen.getByText('Mempool Size')).toBeInTheDocument();
    expect(screen.getByText('AI Models in Use')).toBeInTheDocument();
  });

  it('shows loading state initially', () => {
    render(<Home />);

    // Should show loading placeholders
    const loadingTexts = screen.getAllByText('...');
    expect(loadingTexts.length).toBeGreaterThan(0);
  });

  it('renders blocks table headers', async () => {
    render(<Home />);

    await waitFor(() => {
      expect(screen.getByText('Height')).toBeInTheDocument();
    });

    expect(screen.getByText('Hash')).toBeInTheDocument();
    expect(screen.getByText('Txs')).toBeInTheDocument();
    expect(screen.getByText('Time')).toBeInTheDocument();
  });

  it('renders AI tasks table headers', async () => {
    render(<Home />);

    await waitFor(() => {
      expect(screen.getByText('Task ID')).toBeInTheDocument();
    });

    expect(screen.getByText('Model')).toBeInTheDocument();
    expect(screen.getByText('Status')).toBeInTheDocument();
    expect(screen.getByText('Cost')).toBeInTheDocument();
  });
});
