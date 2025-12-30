import { describe, it, expect, beforeAll, afterAll, afterEach } from 'vitest';
import { render, screen, waitFor } from '../__tests__/test-utils';
import userEvent from '@testing-library/user-event';
import { server } from '../__tests__/mocks/server';
import { http, HttpResponse } from 'msw';
import { AITasks } from './AITasks';

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe('AITasks', () => {
  it('renders page header', () => {
    render(<AITasks />);

    expect(screen.getByRole('heading', { name: 'AI Tasks' })).toBeInTheDocument();
    expect(
      screen.getByText('Explore AI compute tasks on the XAI network')
    ).toBeInTheDocument();
  });

  it('renders stat cards', async () => {
    render(<AITasks />);

    await waitFor(() => {
      expect(screen.getByText('Total Tasks')).toBeInTheDocument();
    });

    expect(screen.getByText('Success Rate')).toBeInTheDocument();
    expect(screen.getByText('Active Providers')).toBeInTheDocument();
    expect(screen.getByText('Total Cost')).toBeInTheDocument();
  });

  it('renders filter dropdowns', async () => {
    render(<AITasks />);

    await waitFor(() => {
      expect(screen.getByText('Filters:')).toBeInTheDocument();
    });

    // There are two comboboxes (status and model filters)
    const comboboxes = screen.getAllByRole('combobox');
    expect(comboboxes.length).toBe(2);
    expect(screen.getByText('All Status')).toBeInTheDocument();
  });

  it('shows loading state initially', () => {
    render(<AITasks />);

    expect(screen.getByText('Loading AI tasks...')).toBeInTheDocument();
  });

  it('renders AI tasks table after loading', async () => {
    render(<AITasks />);

    await waitFor(() => {
      expect(screen.getByText('Task ID')).toBeInTheDocument();
    });

    expect(screen.getByText('Type')).toBeInTheDocument();
    expect(screen.getByText('Model')).toBeInTheDocument();
    expect(screen.getByText('Provider')).toBeInTheDocument();
    expect(screen.getByText('Complexity')).toBeInTheDocument();
    expect(screen.getByText('Status')).toBeInTheDocument();
    expect(screen.getByText('Cost')).toBeInTheDocument();
    expect(screen.getByText('Time')).toBeInTheDocument();
  });

  it('filters by status', async () => {
    const user = userEvent.setup();
    render(<AITasks />);

    await waitFor(() => {
      expect(screen.queryByText('Loading AI tasks...')).not.toBeInTheDocument();
    });

    const statusSelect = screen.getAllByRole('combobox')[0];
    await user.selectOptions(statusSelect, 'completed');

    expect(statusSelect).toHaveValue('completed');
  });

  it('shows Clear Filters button when filters are active', async () => {
    const user = userEvent.setup();
    render(<AITasks />);

    await waitFor(() => {
      expect(screen.queryByText('Loading AI tasks...')).not.toBeInTheDocument();
    });

    const statusSelect = screen.getAllByRole('combobox')[0];
    await user.selectOptions(statusSelect, 'completed');

    expect(screen.getByText('Clear Filters')).toBeInTheDocument();
  });

  it('clears filters when Clear Filters is clicked', async () => {
    const user = userEvent.setup();
    render(<AITasks />);

    await waitFor(() => {
      expect(screen.queryByText('Loading AI tasks...')).not.toBeInTheDocument();
    });

    const statusSelect = screen.getAllByRole('combobox')[0];
    await user.selectOptions(statusSelect, 'completed');

    await user.click(screen.getByText('Clear Filters'));

    expect(statusSelect).toHaveValue('');
    expect(screen.queryByText('Clear Filters')).not.toBeInTheDocument();
  });

  it('shows error message when API fails', async () => {
    server.use(
      http.get('/api/v1/ai/tasks', () => {
        return new HttpResponse(null, { status: 500 });
      })
    );

    render(<AITasks />);

    await waitFor(() => {
      expect(
        screen.getByText('Failed to load AI tasks. Please try again.')
      ).toBeInTheDocument();
    });
  });

  it('renders AI Model Performance section', async () => {
    render(<AITasks />);

    await waitFor(() => {
      expect(screen.getByText('AI Model Performance')).toBeInTheDocument();
    });

    expect(
      screen.getByText('Compare models by tasks, success rate, and cost')
    ).toBeInTheDocument();
  });

  it('displays model cards', async () => {
    render(<AITasks />);

    await waitFor(() => {
      // Model name may appear in multiple places (table + cards)
      const gpt4Elements = screen.getAllByText('gpt-4');
      expect(gpt4Elements.length).toBeGreaterThan(0);
    });

    expect(screen.getAllByText('claude-3').length).toBeGreaterThan(0);
    expect(screen.getAllByText('codellama').length).toBeGreaterThan(0);
  });

  it('displays CPU icon in header', () => {
    const { container } = render(<AITasks />);

    const svg = container.querySelector('svg');
    expect(svg).toBeInTheDocument();
  });
});
