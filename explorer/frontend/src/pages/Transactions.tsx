import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowRightLeft, Search } from 'lucide-react';
import { Card, CardHeader } from '../components/Card';
import { Table, TableHeader, TableHead, TableBody, TableRow, TableCell } from '../components/Table';
import { Badge, getStatusVariant } from '../components/Badge';
import { HashLink, AddressLink } from '../components/HashLink';
import { Pagination } from '../components/Pagination';
import { Loading } from '../components/Loading';
import { getBlocks } from '../api/client';
import { formatNumber, formatTimeAgo, formatXAI } from '../utils/format';
import type { Transaction } from '../types';

const ITEMS_PER_PAGE = 20;

export function Transactions() {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [searchQuery, setSearchQuery] = useState('');

  const { data, isLoading, error } = useQuery({
    queryKey: ['transactions', page, ITEMS_PER_PAGE],
    queryFn: async () => {
      // Get blocks and extract transactions
      const blocksData = await getBlocks(page, ITEMS_PER_PAGE);
      const transactions: Transaction[] = [];

      for (const block of blocksData.blocks) {
        if (block.transactions) {
          for (const tx of block.transactions) {
            const txid = typeof tx === 'string' ? tx : tx.txid;
            const transaction: Transaction = {
              txid,
              blockHash: block.hash,
              blockHeight: block.height,
              timestamp: block.timestamp,
              type: 'transfer',
              from: 'Unknown',
              to: 'Unknown',
              amount: '0',
              fee: '0',
              status: 'confirmed',
              confirmations: 1,
            };
            transactions.push(transaction);
          }
        }
      }

      return {
        transactions,
        total: blocksData.total * 5, // Estimate
      };
    },
    refetchInterval: 15000,
  });

  const totalPages = data ? Math.ceil(data.total / ITEMS_PER_PAGE) : 1;

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      if (/^[a-fA-F0-9]{64}$/.test(searchQuery)) {
        navigate(`/tx/${searchQuery}`);
      }
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-xai-primary/10">
            <ArrowRightLeft className="h-5 w-5 text-xai-primary" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">Transactions</h1>
            <p className="text-sm text-xai-muted">
              {data ? `${formatNumber(data.total)} total transactions` : 'Loading...'}
            </p>
          </div>
        </div>

        <form onSubmit={handleSearch} className="relative">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by transaction ID..."
            className="w-full sm:w-64 rounded-lg border border-xai-border bg-xai-card py-2 pl-10 pr-4 text-sm text-white placeholder-xai-muted focus:border-xai-primary focus:outline-none"
          />
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-xai-muted" />
        </form>
      </div>

      <Card padding="none">
        {isLoading ? (
          <div className="p-8">
            <Loading message="Loading transactions..." />
          </div>
        ) : error ? (
          <div className="p-8 text-center text-red-400">
            Failed to load transactions. Please try again.
          </div>
        ) : (
          <>
            <Table>
              <TableHeader>
                <TableHead>Transaction ID</TableHead>
                <TableHead>Block</TableHead>
                <TableHead>From</TableHead>
                <TableHead>To</TableHead>
                <TableHead align="right">Amount</TableHead>
                <TableHead align="center">Status</TableHead>
                <TableHead align="right">Age</TableHead>
              </TableHeader>
              <TableBody>
                {data?.transactions.map((tx) => (
                  <TableRow
                    key={tx.txid}
                    onClick={() => navigate(`/tx/${tx.txid}`)}
                  >
                    <TableCell>
                      <HashLink
                        hash={tx.txid}
                        to={`/tx/${tx.txid}`}
                      />
                    </TableCell>
                    <TableCell>
                      <Link
                        to={`/block/${tx.blockHeight}`}
                        className="text-xai-primary hover:underline"
                        onClick={(e) => e.stopPropagation()}
                      >
                        {formatNumber(tx.blockHeight)}
                      </Link>
                    </TableCell>
                    <TableCell>
                      <AddressLink address={tx.from} />
                    </TableCell>
                    <TableCell>
                      <AddressLink address={tx.to} />
                    </TableCell>
                    <TableCell align="right" className="text-white font-medium">
                      {formatXAI(tx.amount)}
                    </TableCell>
                    <TableCell align="center">
                      <Badge variant={getStatusVariant(tx.status)}>
                        {tx.status}
                      </Badge>
                    </TableCell>
                    <TableCell align="right" className="text-xai-muted">
                      {formatTimeAgo(tx.timestamp)}
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
