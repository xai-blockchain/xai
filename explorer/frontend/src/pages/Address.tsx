import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Wallet, ChevronLeft, ArrowUpRight, ArrowDownLeft, Copy } from 'lucide-react';
import { Card, CardHeader } from '../components/Card';
import { StatCard } from '../components/StatCard';
import { Table, TableHeader, TableHead, TableBody, TableRow, TableCell } from '../components/Table';
import { Badge, getStatusVariant } from '../components/Badge';
import { HashLink } from '../components/HashLink';
import { CopyButton } from '../components/CopyButton';
import { Pagination } from '../components/Pagination';
import { Loading } from '../components/Loading';
import { getAddress } from '../api/client';
import { formatNumber, formatTimeAgo, formatXAI } from '../utils/format';

const ITEMS_PER_PAGE = 10;

export function Address() {
  const { address } = useParams<{ address: string }>();
  const [page, setPage] = useState(1);

  const { data, isLoading, error } = useQuery({
    queryKey: ['address', address],
    queryFn: () => getAddress(address!),
    enabled: !!address,
  });

  if (isLoading) {
    return <Loading message="Loading address..." />;
  }

  if (error || !data) {
    return (
      <div className="text-center py-12">
        <Wallet className="h-16 w-16 text-xai-muted mx-auto mb-4" />
        <h2 className="text-xl font-semibold text-white mb-2">Address Not Found</h2>
        <p className="text-xai-muted mb-6">
          The address you're looking for doesn't exist or has no transactions.
        </p>
        <Link
          to="/"
          className="inline-flex items-center gap-2 px-4 py-2 bg-xai-primary text-black rounded-lg font-medium hover:bg-xai-secondary transition-colors"
        >
          <ChevronLeft className="h-4 w-4" />
          Back to Home
        </Link>
      </div>
    );
  }

  const paginatedTransactions = data.transactions.slice(
    (page - 1) * ITEMS_PER_PAGE,
    page * ITEMS_PER_PAGE
  );
  const totalPages = Math.ceil(data.transactions.length / ITEMS_PER_PAGE);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-xai-primary/10">
          <Wallet className="h-5 w-5 text-xai-primary" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-white">Address</h1>
          <div className="flex items-center gap-2">
            <p className="text-sm text-xai-muted font-mono break-all">
              {address}
            </p>
            <CopyButton text={address!} />
          </div>
        </div>
      </div>

      {/* Balance Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Balance"
          value={formatXAI(data.balance)}
          icon={Wallet}
        />
        <StatCard
          label="Total Received"
          value={formatXAI(data.totalReceived)}
          icon={ArrowDownLeft}
        />
        <StatCard
          label="Total Sent"
          value={formatXAI(data.totalSent)}
          icon={ArrowUpRight}
        />
        <StatCard
          label="Transactions"
          value={formatNumber(data.transactionCount)}
        />
      </div>

      {/* Transaction History */}
      <Card padding="none">
        <div className="p-6 pb-0">
          <CardHeader
            title="Transaction History"
            subtitle={`${data.transactionCount} transactions found`}
          />
        </div>
        {data.transactions.length > 0 ? (
          <>
            <Table>
              <TableHeader>
                <TableHead>Transaction ID</TableHead>
                <TableHead>Direction</TableHead>
                <TableHead>Counterparty</TableHead>
                <TableHead align="right">Amount</TableHead>
                <TableHead align="center">Status</TableHead>
                <TableHead align="right">Age</TableHead>
              </TableHeader>
              <TableBody>
                {paginatedTransactions.map((tx) => {
                  const isIncoming = tx.to === address;
                  return (
                    <TableRow key={tx.txid}>
                      <TableCell>
                        <HashLink hash={tx.txid} to={`/tx/${tx.txid}`} />
                      </TableCell>
                      <TableCell>
                        {isIncoming ? (
                          <Badge variant="success">
                            <ArrowDownLeft className="h-3 w-3 mr-1" />
                            IN
                          </Badge>
                        ) : (
                          <Badge variant="warning">
                            <ArrowUpRight className="h-3 w-3 mr-1" />
                            OUT
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell>
                        <Link
                          to={`/address/${isIncoming ? tx.from : tx.to}`}
                          className="text-xai-primary hover:underline font-mono text-sm"
                        >
                          {(isIncoming ? tx.from : tx.to).slice(0, 8)}...
                          {(isIncoming ? tx.from : tx.to).slice(-6)}
                        </Link>
                      </TableCell>
                      <TableCell align="right">
                        <span
                          className={`font-medium ${
                            isIncoming ? 'text-green-400' : 'text-red-400'
                          }`}
                        >
                          {isIncoming ? '+' : '-'}{formatXAI(tx.amount)}
                        </span>
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
                  );
                })}
              </TableBody>
            </Table>

            {totalPages > 1 && (
              <div className="p-4 border-t border-xai-border">
                <Pagination
                  currentPage={page}
                  totalPages={totalPages}
                  onPageChange={setPage}
                />
              </div>
            )}
          </>
        ) : (
          <div className="p-8 text-center">
            <p className="text-xai-muted">No transactions found for this address</p>
          </div>
        )}
      </Card>
    </div>
  );
}
