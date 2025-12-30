import { describe, it, expect, beforeAll, afterAll, afterEach } from 'vitest';
import { render, screen, waitFor } from '../__tests__/test-utils';
import { server } from '../__tests__/mocks/server';
import { http, HttpResponse } from 'msw';
import { BlockDetail } from './BlockDetail';
import { Routes, Route } from 'react-router-dom';

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function renderWithRoute(blockId: string) {
  return render(
    <Routes>
      <Route path="/block/:blockId" element={<BlockDetail />} />
    </Routes>,
    { initialEntries: [`/block/${blockId}`] }
  );
}

describe('BlockDetail', () => {
  it('shows loading state initially', () => {
    renderWithRoute('12345');

    expect(screen.getByText('Loading block...')).toBeInTheDocument();
  });

  it('renders block header after loading', async () => {
    renderWithRoute('12345');

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(/Block #/);
    });
  });

  it('renders Block Details card', async () => {
    renderWithRoute('12345');

    await waitFor(() => {
      expect(screen.getByText('Block Details')).toBeInTheDocument();
    });
  });

  it('displays block height', async () => {
    renderWithRoute('12345');

    await waitFor(() => {
      expect(screen.getByText('Block Height')).toBeInTheDocument();
    });
  });

  it('displays timestamp', async () => {
    renderWithRoute('12345');

    await waitFor(() => {
      expect(screen.getByText('Timestamp')).toBeInTheDocument();
    });
  });

  it('displays block hash with copy button', async () => {
    renderWithRoute('12345');

    await waitFor(() => {
      expect(screen.getByText('Block Hash')).toBeInTheDocument();
    });

    // Copy button should be present
    const copyButtons = screen.getAllByRole('button');
    expect(copyButtons.length).toBeGreaterThan(0);
  });

  it('displays previous hash link', async () => {
    renderWithRoute('12345');

    await waitFor(() => {
      expect(screen.getByText('Previous Hash')).toBeInTheDocument();
    });
  });

  it('displays miner address', async () => {
    renderWithRoute('12345');

    await waitFor(() => {
      expect(screen.getByText('Miner')).toBeInTheDocument();
    });
  });

  it('displays difficulty', async () => {
    renderWithRoute('12345');

    await waitFor(() => {
      expect(screen.getByText('Difficulty')).toBeInTheDocument();
    });
  });

  it('displays nonce', async () => {
    renderWithRoute('12345');

    await waitFor(() => {
      expect(screen.getByText('Nonce')).toBeInTheDocument();
    });
  });

  it('displays size', async () => {
    renderWithRoute('12345');

    await waitFor(() => {
      expect(screen.getByText('Size')).toBeInTheDocument();
    });
  });

  it('displays merkle root', async () => {
    renderWithRoute('12345');

    await waitFor(() => {
      expect(screen.getByText('Merkle Root')).toBeInTheDocument();
    });
  });

  it('renders navigation buttons', async () => {
    renderWithRoute('12345');

    await waitFor(() => {
      expect(screen.getByText('Previous')).toBeInTheDocument();
    });

    expect(screen.getByText('Next')).toBeInTheDocument();
  });

  it('shows block not found for invalid block', async () => {
    renderWithRoute('notfound');

    await waitFor(() => {
      expect(screen.getByText('Block Not Found')).toBeInTheDocument();
    });

    expect(
      screen.getByText(/The block you're looking for doesn't exist/)
    ).toBeInTheDocument();

    expect(screen.getByText('Back to Blocks')).toBeInTheDocument();
  });

  it('shows transactions section', async () => {
    renderWithRoute('12345');

    await waitFor(() => {
      expect(screen.getByText(/Transactions/)).toBeInTheDocument();
    });
  });

  it('shows no transactions message when block has none', async () => {
    server.use(
      http.get('/api/v1/blocks/:blockId', () => {
        return HttpResponse.json({
          height: 12345,
          hash: '0000000000000000000abc123def456789012345678901234567890123456789',
          previousHash: '0000000000000000000111222333444555666777888999000111222333444555',
          timestamp: '2024-01-15T10:30:00Z',
          transactions: [],
          transactionCount: 0,
          miner: 'XAIminer123',
          difficulty: 1234567890,
          nonce: 987654321,
          size: 256,
          merkleRoot: 'merkleroot123',
        });
      })
    );

    renderWithRoute('12345');

    await waitFor(() => {
      expect(screen.getByText('No transactions in this block')).toBeInTheDocument();
    });
  });

  it('renders transaction links', async () => {
    renderWithRoute('12345');

    await waitFor(() => {
      expect(screen.getByText('Transaction ID')).toBeInTheDocument();
    });

    expect(screen.getByText('Index')).toBeInTheDocument();
  });
});
