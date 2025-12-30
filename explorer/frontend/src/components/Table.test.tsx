import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '../__tests__/test-utils';
import userEvent from '@testing-library/user-event';
import {
  Table,
  TableHeader,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
} from './Table';

describe('Table', () => {
  it('renders table correctly', () => {
    render(
      <Table>
        <TableHeader>
          <TableHead>Column 1</TableHead>
          <TableHead>Column 2</TableHead>
        </TableHeader>
        <TableBody>
          <TableRow>
            <TableCell>Cell 1</TableCell>
            <TableCell>Cell 2</TableCell>
          </TableRow>
        </TableBody>
      </Table>
    );

    expect(screen.getByText('Column 1')).toBeInTheDocument();
    expect(screen.getByText('Column 2')).toBeInTheDocument();
    expect(screen.getByText('Cell 1')).toBeInTheDocument();
    expect(screen.getByText('Cell 2')).toBeInTheDocument();
  });

  it('applies custom className to Table', () => {
    const { container } = render(
      <Table className="custom-table">
        <TableBody>
          <TableRow>
            <TableCell>Content</TableCell>
          </TableRow>
        </TableBody>
      </Table>
    );

    expect(container.firstChild).toHaveClass('custom-table');
    expect(container.firstChild).toHaveClass('overflow-x-auto');
  });
});

describe('TableHeader', () => {
  it('renders header row in thead', () => {
    render(
      <table>
        <TableHeader>
          <TableHead>Header</TableHead>
        </TableHeader>
      </table>
    );

    const thead = screen.getByRole('rowgroup');
    expect(thead.tagName).toBe('THEAD');
  });

  it('has border styling', () => {
    const { container } = render(
      <table>
        <TableHeader>
          <TableHead>Header</TableHead>
        </TableHeader>
      </table>
    );

    const thead = container.querySelector('thead');
    expect(thead).toHaveClass('border-b', 'border-xai-border');
  });
});

describe('TableHead', () => {
  it('renders with default left alignment', () => {
    render(
      <table>
        <thead>
          <tr>
            <TableHead>Header</TableHead>
          </tr>
        </thead>
      </table>
    );

    expect(screen.getByText('Header')).toHaveClass('text-left');
  });

  it('renders with center alignment', () => {
    render(
      <table>
        <thead>
          <tr>
            <TableHead align="center">Header</TableHead>
          </tr>
        </thead>
      </table>
    );

    expect(screen.getByText('Header')).toHaveClass('text-center');
  });

  it('renders with right alignment', () => {
    render(
      <table>
        <thead>
          <tr>
            <TableHead align="right">Header</TableHead>
          </tr>
        </thead>
      </table>
    );

    expect(screen.getByText('Header')).toHaveClass('text-right');
  });

  it('applies custom className', () => {
    render(
      <table>
        <thead>
          <tr>
            <TableHead className="custom-head">Header</TableHead>
          </tr>
        </thead>
      </table>
    );

    expect(screen.getByText('Header')).toHaveClass('custom-head');
  });

  it('has correct base styles', () => {
    render(
      <table>
        <thead>
          <tr>
            <TableHead>Header</TableHead>
          </tr>
        </thead>
      </table>
    );

    const th = screen.getByText('Header');
    expect(th).toHaveClass('px-4', 'py-3', 'text-xs', 'font-medium', 'uppercase', 'tracking-wider', 'text-xai-muted');
  });
});

describe('TableBody', () => {
  it('renders tbody with divide styling', () => {
    const { container } = render(
      <table>
        <TableBody>
          <TableRow>
            <TableCell>Cell</TableCell>
          </TableRow>
        </TableBody>
      </table>
    );

    const tbody = container.querySelector('tbody');
    expect(tbody).toHaveClass('divide-y', 'divide-xai-border');
  });
});

describe('TableRow', () => {
  it('renders row correctly', () => {
    render(
      <table>
        <tbody>
          <TableRow>
            <TableCell>Cell content</TableCell>
          </TableRow>
        </tbody>
      </table>
    );

    expect(screen.getByText('Cell content')).toBeInTheDocument();
  });

  it('handles onClick', async () => {
    const user = userEvent.setup();
    const handleClick = vi.fn();

    render(
      <table>
        <tbody>
          <TableRow onClick={handleClick}>
            <TableCell>Clickable</TableCell>
          </TableRow>
        </tbody>
      </table>
    );

    await user.click(screen.getByText('Clickable'));
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('has hover styles when clickable', () => {
    render(
      <table>
        <tbody>
          <TableRow onClick={() => {}}>
            <TableCell>Clickable</TableCell>
          </TableRow>
        </tbody>
      </table>
    );

    const row = screen.getByRole('row');
    expect(row).toHaveClass('cursor-pointer', 'hover:bg-xai-dark');
  });

  it('does not have hover styles when not clickable', () => {
    render(
      <table>
        <tbody>
          <TableRow>
            <TableCell>Not clickable</TableCell>
          </TableRow>
        </tbody>
      </table>
    );

    const row = screen.getByRole('row');
    expect(row).not.toHaveClass('cursor-pointer');
  });

  it('applies custom className', () => {
    render(
      <table>
        <tbody>
          <TableRow className="custom-row">
            <TableCell>Cell</TableCell>
          </TableRow>
        </tbody>
      </table>
    );

    const row = screen.getByRole('row');
    expect(row).toHaveClass('custom-row');
  });
});

describe('TableCell', () => {
  it('renders with default left alignment', () => {
    render(
      <table>
        <tbody>
          <tr>
            <TableCell>Cell</TableCell>
          </tr>
        </tbody>
      </table>
    );

    expect(screen.getByText('Cell')).toHaveClass('text-left');
  });

  it('renders with center alignment', () => {
    render(
      <table>
        <tbody>
          <tr>
            <TableCell align="center">Cell</TableCell>
          </tr>
        </tbody>
      </table>
    );

    expect(screen.getByText('Cell')).toHaveClass('text-center');
  });

  it('renders with right alignment', () => {
    render(
      <table>
        <tbody>
          <tr>
            <TableCell align="right">Cell</TableCell>
          </tr>
        </tbody>
      </table>
    );

    expect(screen.getByText('Cell')).toHaveClass('text-right');
  });

  it('applies custom className', () => {
    render(
      <table>
        <tbody>
          <tr>
            <TableCell className="custom-cell">Cell</TableCell>
          </tr>
        </tbody>
      </table>
    );

    expect(screen.getByText('Cell')).toHaveClass('custom-cell');
  });

  it('has correct base styles', () => {
    render(
      <table>
        <tbody>
          <tr>
            <TableCell>Cell</TableCell>
          </tr>
        </tbody>
      </table>
    );

    const td = screen.getByText('Cell');
    expect(td).toHaveClass('px-4', 'py-3', 'text-sm');
  });
});
