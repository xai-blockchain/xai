import { describe, it, expect, beforeAll, afterAll, afterEach } from 'vitest';
import { render, screen, waitFor } from '../__tests__/test-utils';
import userEvent from '@testing-library/user-event';
import { server } from '../__tests__/mocks/server';
import { http, HttpResponse } from 'msw';
import { Transactions } from './Transactions';

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe('Transactions', () => {
  it('renders page header', () => {
    render(<Transactions />);

    expect(screen.getByRole('heading', { name: 'Transactions' })).toBeInTheDocument();
  });

  it('renders search input', () => {
    render(<Transactions />);

    expect(
      screen.getByPlaceholderText('Search by transaction ID...')
    ).toBeInTheDocument();
  });

  it('shows loading state initially', () => {
    render(<Transactions />);

    expect(screen.getByText('Loading transactions...')).toBeInTheDocument();
  });

  it('renders transactions table after loading', async () => {
    render(<Transactions />);

    await waitFor(() => {
      expect(screen.getByText('Transaction ID')).toBeInTheDocument();
    });

    expect(screen.getByText('Block')).toBeInTheDocument();
    expect(screen.getByText('From')).toBeInTheDocument();
    expect(screen.getByText('To')).toBeInTheDocument();
    expect(screen.getByText('Amount')).toBeInTheDocument();
    expect(screen.getByText('Status')).toBeInTheDocument();
    expect(screen.getByText('Age')).toBeInTheDocument();
  });

  it('shows total transactions count', async () => {
    render(<Transactions />);

    await waitFor(() => {
      expect(screen.getByText(/total transactions/)).toBeInTheDocument();
    });
  });

  it('displays transaction icon', () => {
    const { container } = render(<Transactions />);

    const svg = container.querySelector('svg');
    expect(svg).toBeInTheDocument();
  });

  it('has search input for entering query', () => {
    render(<Transactions />);

    const searchInput = screen.getByPlaceholderText('Search by transaction ID...');
    expect(searchInput).toBeInTheDocument();
    expect(searchInput).toHaveAttribute('type', 'text');
  });

  it('displays search icon', () => {
    const { container } = render(<Transactions />);

    // Search icon should be present in the form
    const svgs = container.querySelectorAll('svg');
    expect(svgs.length).toBeGreaterThan(0);
  });

  it('shows error message when API fails', async () => {
    server.use(
      http.get('/api/v1/blocks', () => {
        return new HttpResponse(null, { status: 500 });
      })
    );

    render(<Transactions />);

    await waitFor(() => {
      expect(
        screen.getByText('Failed to load transactions. Please try again.')
      ).toBeInTheDocument();
    });
  });

  it('renders pagination after loading', async () => {
    render(<Transactions />);

    await waitFor(() => {
      expect(screen.queryByText('Loading transactions...')).not.toBeInTheDocument();
    });

    // Should have pagination buttons
    const buttons = screen.getAllByRole('button');
    expect(buttons.length).toBeGreaterThan(0);
  });
});
