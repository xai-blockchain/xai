import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '../__tests__/test-utils';
import userEvent from '@testing-library/user-event';
import { Pagination } from './Pagination';

describe('Pagination', () => {
  it('does not render when totalPages is 1', () => {
    const { container } = render(
      <Pagination currentPage={1} totalPages={1} onPageChange={() => {}} />
    );

    expect(container.firstChild).toBeNull();
  });

  it('does not render when totalPages is 0', () => {
    const { container } = render(
      <Pagination currentPage={1} totalPages={0} onPageChange={() => {}} />
    );

    expect(container.firstChild).toBeNull();
  });

  it('renders all pages when totalPages <= 7', () => {
    render(<Pagination currentPage={1} totalPages={5} onPageChange={() => {}} />);

    expect(screen.getByText('1')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
    expect(screen.getByText('4')).toBeInTheDocument();
    expect(screen.getByText('5')).toBeInTheDocument();
    expect(screen.queryByText('...')).not.toBeInTheDocument();
  });

  it('renders ellipsis for large page count at start', () => {
    render(<Pagination currentPage={1} totalPages={10} onPageChange={() => {}} />);

    expect(screen.getByText('1')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
    expect(screen.getByText('4')).toBeInTheDocument();
    expect(screen.getByText('...')).toBeInTheDocument();
    expect(screen.getByText('10')).toBeInTheDocument();
  });

  it('renders ellipsis for large page count at end', () => {
    render(<Pagination currentPage={10} totalPages={10} onPageChange={() => {}} />);

    expect(screen.getByText('1')).toBeInTheDocument();
    expect(screen.getByText('...')).toBeInTheDocument();
    expect(screen.getByText('7')).toBeInTheDocument();
    expect(screen.getByText('8')).toBeInTheDocument();
    expect(screen.getByText('9')).toBeInTheDocument();
    expect(screen.getByText('10')).toBeInTheDocument();
  });

  it('renders double ellipsis in middle', () => {
    render(<Pagination currentPage={5} totalPages={10} onPageChange={() => {}} />);

    expect(screen.getByText('1')).toBeInTheDocument();
    const ellipses = screen.getAllByText('...');
    expect(ellipses).toHaveLength(2);
    expect(screen.getByText('4')).toBeInTheDocument();
    expect(screen.getByText('5')).toBeInTheDocument();
    expect(screen.getByText('6')).toBeInTheDocument();
    expect(screen.getByText('10')).toBeInTheDocument();
  });

  it('calls onPageChange when clicking next page', async () => {
    const user = userEvent.setup();
    const handlePageChange = vi.fn();

    render(
      <Pagination currentPage={1} totalPages={5} onPageChange={handlePageChange} />
    );

    await user.click(screen.getByText('2'));
    expect(handlePageChange).toHaveBeenCalledWith(2);
  });

  it('calls onPageChange when clicking next button', async () => {
    const user = userEvent.setup();
    const handlePageChange = vi.fn();

    render(
      <Pagination currentPage={1} totalPages={5} onPageChange={handlePageChange} />
    );

    // Find and click next button (ChevronRight)
    const buttons = screen.getAllByRole('button');
    const nextButton = buttons[buttons.length - 1];
    await user.click(nextButton);

    expect(handlePageChange).toHaveBeenCalledWith(2);
  });

  it('calls onPageChange when clicking previous button', async () => {
    const user = userEvent.setup();
    const handlePageChange = vi.fn();

    render(
      <Pagination currentPage={3} totalPages={5} onPageChange={handlePageChange} />
    );

    // Find and click previous button (ChevronLeft)
    const buttons = screen.getAllByRole('button');
    const prevButton = buttons[0];
    await user.click(prevButton);

    expect(handlePageChange).toHaveBeenCalledWith(2);
  });

  it('disables previous button on first page', () => {
    render(<Pagination currentPage={1} totalPages={5} onPageChange={() => {}} />);

    const buttons = screen.getAllByRole('button');
    const prevButton = buttons[0];
    expect(prevButton).toBeDisabled();
    expect(prevButton).toHaveClass('cursor-not-allowed');
  });

  it('disables next button on last page', () => {
    render(<Pagination currentPage={5} totalPages={5} onPageChange={() => {}} />);

    const buttons = screen.getAllByRole('button');
    const nextButton = buttons[buttons.length - 1];
    expect(nextButton).toBeDisabled();
    expect(nextButton).toHaveClass('cursor-not-allowed');
  });

  it('highlights current page', () => {
    render(<Pagination currentPage={3} totalPages={5} onPageChange={() => {}} />);

    const currentPageButton = screen.getByText('3');
    expect(currentPageButton).toHaveClass('bg-xai-primary');
  });

  it('does not call onPageChange when clicking ellipsis', async () => {
    const user = userEvent.setup();
    const handlePageChange = vi.fn();

    render(
      <Pagination currentPage={5} totalPages={10} onPageChange={handlePageChange} />
    );

    const ellipses = screen.getAllByText('...');
    await user.click(ellipses[0]);

    expect(handlePageChange).not.toHaveBeenCalled();
  });
});
