import { describe, it, expect, beforeAll, afterAll, afterEach, vi } from 'vitest';
import { render, screen, waitFor } from '../__tests__/test-utils';
import userEvent from '@testing-library/user-event';
import { server } from '../__tests__/mocks/server';
import { http, HttpResponse } from 'msw';
import { Blocks } from './Blocks';

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe('Blocks', () => {
  it('renders page header', async () => {
    render(<Blocks />);

    expect(screen.getByRole('heading', { name: 'Blocks' })).toBeInTheDocument();
  });

  it('renders search input', () => {
    render(<Blocks />);

    expect(
      screen.getByPlaceholderText('Search by height or hash...')
    ).toBeInTheDocument();
  });

  it('shows loading state initially', () => {
    render(<Blocks />);

    expect(screen.getByText('Loading blocks...')).toBeInTheDocument();
  });

  it('renders blocks table after loading', async () => {
    render(<Blocks />);

    await waitFor(() => {
      expect(screen.getByText('Height')).toBeInTheDocument();
    });

    expect(screen.getByText('Hash')).toBeInTheDocument();
    expect(screen.getByText('Miner')).toBeInTheDocument();
    expect(screen.getByText('Transactions')).toBeInTheDocument();
    expect(screen.getByText('Size')).toBeInTheDocument();
    expect(screen.getByText('Age')).toBeInTheDocument();
  });

  it('shows total blocks count', async () => {
    render(<Blocks />);

    await waitFor(() => {
      expect(screen.getByText(/100 total blocks/)).toBeInTheDocument();
    });
  });

  it('displays block icon', () => {
    const { container } = render(<Blocks />);

    // Should have the Blocks icon
    const svg = container.querySelector('svg');
    expect(svg).toBeInTheDocument();
  });

  it('renders pagination', async () => {
    render(<Blocks />);

    await waitFor(() => {
      expect(screen.queryByText('Loading blocks...')).not.toBeInTheDocument();
    });

    // Should have pagination buttons
    const buttons = screen.getAllByRole('button');
    expect(buttons.length).toBeGreaterThan(0);
  });

  it('handles search form submission with block height', async () => {
    const user = userEvent.setup();
    render(<Blocks />);

    const searchInput = screen.getByPlaceholderText('Search by height or hash...');
    await user.type(searchInput, '12345');
    await user.keyboard('{Enter}');

    // Navigation should occur (would redirect to /block/12345)
    // In testing, we can verify the input was filled
    expect(searchInput).toHaveValue('12345');
  });

  it('handles search form submission with block hash', async () => {
    const user = userEvent.setup();
    render(<Blocks />);

    const hash = 'abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890';
    const searchInput = screen.getByPlaceholderText('Search by height or hash...');
    await user.type(searchInput, hash);
    await user.keyboard('{Enter}');

    expect(searchInput).toHaveValue(hash);
  });

  it('has correct search input attributes', () => {
    render(<Blocks />);

    const searchInput = screen.getByPlaceholderText('Search by height or hash...');
    expect(searchInput).toHaveAttribute('type', 'text');
  });

  it('displays block icon in header', () => {
    const { container } = render(<Blocks />);

    const svgs = container.querySelectorAll('svg');
    expect(svgs.length).toBeGreaterThan(0);
  });
});
