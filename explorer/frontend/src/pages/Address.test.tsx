import { describe, it, expect, beforeAll, afterAll, afterEach } from 'vitest';
import { render, screen, waitFor } from '../__tests__/test-utils';
import { server } from '../__tests__/mocks/server';
import { Address } from './Address';
import { Routes, Route } from 'react-router-dom';

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function renderWithRoute(address: string) {
  return render(
    <Routes>
      <Route path="/address/:address" element={<Address />} />
    </Routes>,
    { initialEntries: [`/address/${address}`] }
  );
}

describe('Address', () => {
  it('shows loading state initially', () => {
    renderWithRoute('XAIaddress123');

    expect(screen.getByText('Loading address...')).toBeInTheDocument();
  });

  it('renders address header after loading', async () => {
    renderWithRoute('XAIaddress123');

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Address');
    }, { timeout: 10000 });
  });

  it('displays address with copy button', async () => {
    renderWithRoute('XAIaddress123');

    await waitFor(() => {
      expect(screen.getByText('XAIaddress123')).toBeInTheDocument();
    });

    const copyButtons = screen.getAllByRole('button');
    expect(copyButtons.length).toBeGreaterThan(0);
  });

  it('displays balance stat card', async () => {
    renderWithRoute('XAIaddress123');

    await waitFor(() => {
      expect(screen.getByText('Balance')).toBeInTheDocument();
    });
  });

  it('displays total received stat card', async () => {
    renderWithRoute('XAIaddress123');

    await waitFor(() => {
      expect(screen.getByText('Total Received')).toBeInTheDocument();
    });
  });

  it('displays total sent stat card', async () => {
    renderWithRoute('XAIaddress123');

    await waitFor(() => {
      expect(screen.getByText('Total Sent')).toBeInTheDocument();
    });
  });

  it('displays transactions count stat card', async () => {
    renderWithRoute('XAIaddress123');

    await waitFor(() => {
      expect(screen.getByText('Transactions')).toBeInTheDocument();
    });
  });

  it('renders Transaction History section', async () => {
    renderWithRoute('XAIaddress123');

    await waitFor(() => {
      expect(screen.getByText('Transaction History')).toBeInTheDocument();
    });
  });

  it('shows transactions found message', async () => {
    renderWithRoute('XAIaddress123');

    await waitFor(() => {
      expect(screen.getByText(/transactions found/)).toBeInTheDocument();
    });
  });

  it('renders transaction table headers', async () => {
    renderWithRoute('XAIaddress123');

    await waitFor(() => {
      expect(screen.getByText('Transaction ID')).toBeInTheDocument();
    });

    expect(screen.getByText('Direction')).toBeInTheDocument();
    expect(screen.getByText('Counterparty')).toBeInTheDocument();
    expect(screen.getByText('Amount')).toBeInTheDocument();
    expect(screen.getByText('Status')).toBeInTheDocument();
    expect(screen.getByText('Age')).toBeInTheDocument();
  });

  it('shows address not found for invalid address', async () => {
    renderWithRoute('notfound');

    await waitFor(() => {
      expect(screen.getByText('Address Not Found')).toBeInTheDocument();
    });

    expect(
      screen.getByText(/The address you're looking for doesn't exist/)
    ).toBeInTheDocument();

    expect(screen.getByText('Back to Home')).toBeInTheDocument();
  });

  it('displays wallet icon', () => {
    const { container } = renderWithRoute('XAIaddress123');

    const svg = container.querySelector('svg');
    expect(svg).toBeInTheDocument();
  });
});
