import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '../__tests__/test-utils';
import userEvent from '@testing-library/user-event';
import { SearchBar } from './SearchBar';

// Mock the useSearch hook
vi.mock('../hooks/useSearch', () => ({
  useSearch: vi.fn(() => ({
    query: '',
    setQuery: vi.fn(),
    isSearching: false,
    handleSearch: vi.fn(),
  })),
}));

import { useSearch } from '../hooks/useSearch';

describe('SearchBar', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders search input', () => {
    render(<SearchBar />);

    expect(
      screen.getByPlaceholderText('Search by block, tx, address...')
    ).toBeInTheDocument();
  });

  it('renders search icon when not searching', () => {
    const { container } = render(<SearchBar />);

    const svg = container.querySelector('svg');
    expect(svg).toBeInTheDocument();
  });

  it('renders loading spinner when searching', () => {
    vi.mocked(useSearch).mockReturnValue({
      query: 'test',
      setQuery: vi.fn(),
      isSearching: true,
      handleSearch: vi.fn(),
      results: [],
      error: null,
      navigateToResult: vi.fn(),
    });

    const { container } = render(<SearchBar />);

    const spinner = container.querySelector('.animate-spin');
    expect(spinner).toBeInTheDocument();
  });

  it('calls setQuery on input change', async () => {
    const mockSetQuery = vi.fn();
    vi.mocked(useSearch).mockReturnValue({
      query: '',
      setQuery: mockSetQuery,
      isSearching: false,
      handleSearch: vi.fn(),
      results: [],
      error: null,
      navigateToResult: vi.fn(),
    });

    const user = userEvent.setup();
    render(<SearchBar />);

    const input = screen.getByPlaceholderText('Search by block, tx, address...');
    await user.type(input, 'test');

    expect(mockSetQuery).toHaveBeenCalled();
  });

  it('calls handleSearch on form submit', async () => {
    const mockHandleSearch = vi.fn();
    vi.mocked(useSearch).mockReturnValue({
      query: 'test query',
      setQuery: vi.fn(),
      isSearching: false,
      handleSearch: mockHandleSearch,
      results: [],
      error: null,
      navigateToResult: vi.fn(),
    });

    const { container } = render(<SearchBar />);

    // Get form element directly since it doesn't have role="form" by default
    const form = container.querySelector('form');
    expect(form).toBeInTheDocument();
    if (form) {
      fireEvent.submit(form);
    }

    await waitFor(() => {
      expect(mockHandleSearch).toHaveBeenCalledWith('test query');
    });
  });

  it('shows clear button when query exists', () => {
    vi.mocked(useSearch).mockReturnValue({
      query: 'some query',
      setQuery: vi.fn(),
      isSearching: false,
      handleSearch: vi.fn(),
      results: [],
      error: null,
      navigateToResult: vi.fn(),
    });

    render(<SearchBar />);

    // X button should be visible
    const clearButton = screen.getByRole('button');
    expect(clearButton).toBeInTheDocument();
  });

  it('clears query when clear button is clicked', async () => {
    const mockSetQuery = vi.fn();
    vi.mocked(useSearch).mockReturnValue({
      query: 'some query',
      setQuery: mockSetQuery,
      isSearching: false,
      handleSearch: vi.fn(),
      results: [],
      error: null,
      navigateToResult: vi.fn(),
    });

    const user = userEvent.setup();
    render(<SearchBar />);

    const clearButton = screen.getByRole('button');
    await user.click(clearButton);

    expect(mockSetQuery).toHaveBeenCalledWith('');
  });

  it('shows keyboard shortcut hint when not focused and no query', () => {
    vi.mocked(useSearch).mockReturnValue({
      query: '',
      setQuery: vi.fn(),
      isSearching: false,
      handleSearch: vi.fn(),
      results: [],
      error: null,
      navigateToResult: vi.fn(),
    });

    render(<SearchBar />);

    // Keyboard shortcut should be visible
    expect(screen.getByText('Ctrl')).toBeInTheDocument();
    expect(screen.getByText('K')).toBeInTheDocument();
  });

  it('hides keyboard shortcut when focused', async () => {
    vi.mocked(useSearch).mockReturnValue({
      query: '',
      setQuery: vi.fn(),
      isSearching: false,
      handleSearch: vi.fn(),
      results: [],
      error: null,
      navigateToResult: vi.fn(),
    });

    render(<SearchBar />);

    const input = screen.getByPlaceholderText('Search by block, tx, address...');
    fireEvent.focus(input);

    // Wait for state update
    await waitFor(() => {
      expect(screen.queryByText('Ctrl')).not.toBeInTheDocument();
    });
  });

  it('has correct input styling', () => {
    vi.mocked(useSearch).mockReturnValue({
      query: '',
      setQuery: vi.fn(),
      isSearching: false,
      handleSearch: vi.fn(),
      results: [],
      error: null,
      navigateToResult: vi.fn(),
    });

    render(<SearchBar />);

    const input = screen.getByPlaceholderText('Search by block, tx, address...');
    expect(input).toHaveClass('rounded-lg', 'border', 'border-xai-border', 'bg-xai-card');
  });
});
