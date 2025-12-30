import { describe, it, expect, beforeAll, afterAll, afterEach } from 'vitest';
import { render, screen, waitFor } from '../__tests__/test-utils';
import { server } from '../__tests__/mocks/server';
import { http, HttpResponse } from 'msw';
import { AITaskDetail } from './AITaskDetail';
import { Routes, Route } from 'react-router-dom';

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function renderWithRoute(taskId: string) {
  return render(
    <Routes>
      <Route path="/ai/:taskId" element={<AITaskDetail />} />
    </Routes>,
    { initialEntries: [`/ai/${taskId}`] }
  );
}

describe('AITaskDetail', () => {
  it('shows loading state initially', () => {
    renderWithRoute('task123');

    expect(screen.getByText('Loading AI task...')).toBeInTheDocument();
  });

  it('renders task header after loading', async () => {
    renderWithRoute('task123');

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('AI Task Details');
    }, { timeout: 10000 });
  });

  it('renders Back to Tasks link', async () => {
    renderWithRoute('task123');

    await waitFor(() => {
      expect(screen.getByText('Back to Tasks')).toBeInTheDocument();
    });

    expect(screen.getByText('Back to Tasks').closest('a')).toHaveAttribute('href', '/ai');
  });

  it('displays quick stats cards', async () => {
    renderWithRoute('task123');

    await waitFor(() => {
      expect(screen.getByText('Cost')).toBeInTheDocument();
    });

    expect(screen.getByText('Compute Time')).toBeInTheDocument();
    expect(screen.getByText('Tokens')).toBeInTheDocument();
    expect(screen.getAllByText('Status').length).toBeGreaterThan(0);
  });

  it('renders Task Information card', async () => {
    renderWithRoute('task123');

    await waitFor(() => {
      expect(screen.getByText('Task Information')).toBeInTheDocument();
    });
  });

  it('displays task ID with copy button', async () => {
    renderWithRoute('task123');

    await waitFor(() => {
      expect(screen.getByText('Task ID')).toBeInTheDocument();
    });

    const copyButtons = screen.getAllByRole('button');
    expect(copyButtons.length).toBeGreaterThan(0);
  });

  it('displays task type', async () => {
    renderWithRoute('task123');

    await waitFor(() => {
      expect(screen.getByText('Task Type')).toBeInTheDocument();
    });
  });

  it('displays complexity', async () => {
    renderWithRoute('task123');

    await waitFor(() => {
      expect(screen.getByText('Complexity')).toBeInTheDocument();
    });
  });

  it('displays AI model', async () => {
    renderWithRoute('task123');

    await waitFor(() => {
      expect(screen.getByText('AI Model')).toBeInTheDocument();
    });
  });

  it('displays provider address', async () => {
    renderWithRoute('task123');

    await waitFor(() => {
      expect(screen.getByText('Provider')).toBeInTheDocument();
    });
  });

  it('displays created timestamp', async () => {
    renderWithRoute('task123');

    await waitFor(() => {
      expect(screen.getByText('Created')).toBeInTheDocument();
    });
  });

  it('displays completed timestamp for finished tasks', async () => {
    renderWithRoute('task123');

    await waitFor(() => {
      expect(screen.getByText('Completed')).toBeInTheDocument();
    });
  });

  it('shows task not found for invalid task', async () => {
    renderWithRoute('notfound');

    await waitFor(() => {
      expect(screen.getByText('AI Task Not Found')).toBeInTheDocument();
    });

    expect(
      screen.getByText(/The AI task you're looking for doesn't exist/)
    ).toBeInTheDocument();

    expect(screen.getByText('Back to AI Tasks')).toBeInTheDocument();
  });

  it('renders Result Data section when available', async () => {
    renderWithRoute('task123');

    await waitFor(() => {
      expect(screen.getByText('Result Data')).toBeInTheDocument();
    });

    expect(screen.getByText('Output from AI compute task')).toBeInTheDocument();
  });

  it('renders Result Hash section when available', async () => {
    renderWithRoute('task123');

    await waitFor(() => {
      expect(screen.getByText('Result Hash')).toBeInTheDocument();
    });

    expect(screen.getByText('Cryptographic hash of the task result')).toBeInTheDocument();
  });

  it('shows progress indicator for pending tasks', async () => {
    server.use(
      http.get('/api/v1/ai/tasks/:taskId', () => {
        return HttpResponse.json({
          task_id: 'task123',
          task_type: 'text_generation',
          complexity: 'moderate',
          status: 'pending',
          provider_address: 'XAIprovider123',
          ai_model: 'gpt-4',
          cost_estimate: 0.05,
          created_at: '2024-01-15T10:00:00Z',
        });
      })
    );

    renderWithRoute('task123');

    await waitFor(() => {
      expect(screen.getByText('Task Pending')).toBeInTheDocument();
    });

    expect(
      screen.getByText(/Waiting for a compute provider to pick up this task/)
    ).toBeInTheDocument();
  });

  it('shows progress indicator for in-progress tasks', async () => {
    server.use(
      http.get('/api/v1/ai/tasks/:taskId', () => {
        return HttpResponse.json({
          task_id: 'task123',
          task_type: 'text_generation',
          complexity: 'moderate',
          status: 'in_progress',
          provider_address: 'XAIprovider123',
          ai_model: 'gpt-4',
          cost_estimate: 0.05,
          created_at: '2024-01-15T10:00:00Z',
        });
      })
    );

    renderWithRoute('task123');

    await waitFor(() => {
      expect(screen.getByText('Task In Progress')).toBeInTheDocument();
    });

    expect(
      screen.getByText(/AI model is processing your request/)
    ).toBeInTheDocument();
  });

  it('displays CPU icon', () => {
    const { container } = renderWithRoute('task123');

    const svg = container.querySelector('svg');
    expect(svg).toBeInTheDocument();
  });
});
