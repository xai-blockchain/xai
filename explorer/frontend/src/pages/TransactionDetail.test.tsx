import { describe, it, expect, beforeAll, afterAll, afterEach } from 'vitest';
import { render, screen, waitFor } from '../__tests__/test-utils';
import { server } from '../__tests__/mocks/server';
import { TransactionDetail } from './TransactionDetail';
import { Routes, Route } from 'react-router-dom';

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function renderWithRoute(txid: string) {
  return render(
    <Routes>
      <Route path="/tx/:txid" element={<TransactionDetail />} />
    </Routes>,
    { initialEntries: [`/tx/${txid}`] }
  );
}

describe('TransactionDetail', () => {
  it('shows loading state initially', () => {
    renderWithRoute('tx123');

    expect(screen.getByText('Loading transaction...')).toBeInTheDocument();
  });

  it('renders transaction header after loading', async () => {
    renderWithRoute('tx123');

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Transaction Details');
    });
  });

  it('renders Overview card', async () => {
    renderWithRoute('tx123');

    await waitFor(() => {
      expect(screen.getByText('Overview')).toBeInTheDocument();
    });
  });

  it('displays transaction ID with copy button', async () => {
    renderWithRoute('tx123');

    await waitFor(() => {
      expect(screen.getByText('Transaction ID')).toBeInTheDocument();
    });

    const copyButtons = screen.getAllByRole('button');
    expect(copyButtons.length).toBeGreaterThan(0);
  });

  it('displays status badge', async () => {
    renderWithRoute('tx123');

    await waitFor(() => {
      expect(screen.getByText('Status')).toBeInTheDocument();
    });
  });

  it('displays block link', async () => {
    renderWithRoute('tx123');

    await waitFor(() => {
      expect(screen.getByText('Block')).toBeInTheDocument();
    });
  });

  it('displays timestamp', async () => {
    renderWithRoute('tx123');

    await waitFor(() => {
      expect(screen.getByText('Timestamp')).toBeInTheDocument();
    });
  });

  it('displays transaction type', async () => {
    renderWithRoute('tx123');

    await waitFor(() => {
      expect(screen.getByText('Type')).toBeInTheDocument();
    });
  });

  it('displays from address', async () => {
    renderWithRoute('tx123');

    await waitFor(() => {
      expect(screen.getByText('From')).toBeInTheDocument();
    });
  });

  it('displays to address', async () => {
    renderWithRoute('tx123');

    await waitFor(() => {
      expect(screen.getByText('To')).toBeInTheDocument();
    });
  });

  it('displays amount', async () => {
    renderWithRoute('tx123');

    await waitFor(() => {
      expect(screen.getByText('Amount')).toBeInTheDocument();
    });
  });

  it('displays fee', async () => {
    renderWithRoute('tx123');

    await waitFor(() => {
      expect(screen.getByText('Fee')).toBeInTheDocument();
    });
  });

  it('renders Inputs section', async () => {
    renderWithRoute('tx123');

    await waitFor(() => {
      expect(screen.getByText(/Inputs/)).toBeInTheDocument();
    });
  });

  it('renders Outputs section', async () => {
    renderWithRoute('tx123');

    await waitFor(() => {
      expect(screen.getByText(/Outputs/)).toBeInTheDocument();
    });
  });

  it('shows transaction not found for invalid transaction', async () => {
    renderWithRoute('notfound');

    await waitFor(() => {
      expect(screen.getByText('Transaction Not Found')).toBeInTheDocument();
    });

    expect(
      screen.getByText(/The transaction you're looking for doesn't exist/)
    ).toBeInTheDocument();

    expect(screen.getByText('Back to Transactions')).toBeInTheDocument();
  });

  it('displays icon in header', () => {
    const { container } = renderWithRoute('tx123');

    const svg = container.querySelector('svg');
    expect(svg).toBeInTheDocument();
  });
});
