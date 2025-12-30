import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router-dom';
import { Blocks as BlocksIcon, Search } from 'lucide-react';
import { Card, CardHeader } from '../components/Card';
import { Table, TableHeader, TableHead, TableBody, TableRow, TableCell } from '../components/Table';
import { Badge } from '../components/Badge';
import { HashLink, AddressLink } from '../components/HashLink';
import { Pagination } from '../components/Pagination';
import { Loading } from '../components/Loading';
import { getBlocks } from '../api/client';
import { formatNumber, formatTimeAgo, formatBytes } from '../utils/format';

const ITEMS_PER_PAGE = 20;

export function Blocks() {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [searchQuery, setSearchQuery] = useState('');

  const { data, isLoading, error } = useQuery({
    queryKey: ['blocks', page, ITEMS_PER_PAGE],
    queryFn: () => getBlocks(page, ITEMS_PER_PAGE),
    refetchInterval: 15000,
  });

  const totalPages = data ? Math.ceil(data.total / ITEMS_PER_PAGE) : 1;

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      // Navigate to block if it's a valid height or hash
      if (/^\d+$/.test(searchQuery)) {
        navigate(`/block/${searchQuery}`);
      } else if (/^[a-fA-F0-9]{64}$/.test(searchQuery)) {
        navigate(`/block/${searchQuery}`);
      }
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-xai-primary/10">
            <BlocksIcon className="h-5 w-5 text-xai-primary" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">Blocks</h1>
            <p className="text-sm text-xai-muted">
              {data ? `${formatNumber(data.total)} total blocks` : 'Loading...'}
            </p>
          </div>
        </div>

        <form onSubmit={handleSearch} className="relative">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by height or hash..."
            className="w-full sm:w-64 rounded-lg border border-xai-border bg-xai-card py-2 pl-10 pr-4 text-sm text-white placeholder-xai-muted focus:border-xai-primary focus:outline-none"
          />
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-xai-muted" />
        </form>
      </div>

      <Card padding="none">
        {isLoading ? (
          <div className="p-8">
            <Loading message="Loading blocks..." />
          </div>
        ) : error ? (
          <div className="p-8 text-center text-red-400">
            Failed to load blocks. Please try again.
          </div>
        ) : (
          <>
            <Table>
              <TableHeader>
                <TableHead>Height</TableHead>
                <TableHead>Hash</TableHead>
                <TableHead>Miner</TableHead>
                <TableHead align="center">Transactions</TableHead>
                <TableHead align="right">Size</TableHead>
                <TableHead align="right">Age</TableHead>
              </TableHeader>
              <TableBody>
                {data?.blocks.map((block) => (
                  <TableRow
                    key={block.hash}
                    onClick={() => navigate(`/block/${block.height}`)}
                  >
                    <TableCell>
                      <Link
                        to={`/block/${block.height}`}
                        className="text-xai-primary hover:underline font-medium"
                        onClick={(e) => e.stopPropagation()}
                      >
                        {formatNumber(block.height)}
                      </Link>
                    </TableCell>
                    <TableCell>
                      <HashLink
                        hash={block.hash}
                        to={`/block/${block.hash}`}
                      />
                    </TableCell>
                    <TableCell>
                      <AddressLink address={block.miner || 'Unknown'} />
                    </TableCell>
                    <TableCell align="center">
                      <Badge variant="info">
                        {block.transactionCount || block.transactions?.length || 0}
                      </Badge>
                    </TableCell>
                    <TableCell align="right" className="text-xai-muted">
                      {formatBytes(block.size || 0)}
                    </TableCell>
                    <TableCell align="right" className="text-xai-muted">
                      {formatTimeAgo(block.timestamp)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>

            <div className="p-4 border-t border-xai-border">
              <Pagination
                currentPage={page}
                totalPages={totalPages}
                onPageChange={setPage}
              />
            </div>
          </>
        )}
      </Card>
    </div>
  );
}
