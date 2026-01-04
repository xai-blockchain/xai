import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { Trophy, Search, ChevronLeft, ChevronRight, TrendingUp, Coins, Users } from 'lucide-react';
import { Card, CardHeader } from '../components/Card';
import { StatCard } from '../components/StatCard';
import { Table, TableHeader, TableHead, TableBody, TableRow, TableCell } from '../components/Table';
import { Loading } from '../components/Loading';
import { AddressLink } from '../components/HashLink';
import { getRichList } from '../api/client';
import { formatNumber, formatXAI, formatTimeAgo } from '../utils/format';

const PAGE_SIZE = 50;

export function RichList() {
  const [page, setPage] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['richList', page],
    queryFn: () => getRichList(PAGE_SIZE, page * PAGE_SIZE),
  });

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0;

  // Filter by search query
  const filteredHolders = data?.holders.filter(holder =>
    holder.address.toLowerCase().includes(searchQuery.toLowerCase())
  ) || [];

  const displayHolders = searchQuery ? filteredHolders : data?.holders || [];

  // Calculate top 10 holdings percentage
  const top10Percentage = (data?.holders.slice(0, 10).reduce((sum, h) => sum + h.percentage, 0) || 0).toFixed(2);

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold text-white flex items-center gap-3">
            <Trophy className="h-8 w-8 text-yellow-500" />
            Rich List
          </h1>
          <p className="text-xai-muted mt-1">Top XAI token holders by balance</p>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Total Addresses"
          value={isLoading ? '...' : formatNumber(data?.total || 0)}
          icon={Users}
        />
        <StatCard
          label="Total Supply"
          value={isLoading ? '...' : formatXAI(data?.total_supply || 0)}
          icon={Coins}
        />
        <StatCard
          label="Circulating Supply"
          value={isLoading ? '...' : formatXAI(data?.circulating_supply || 0)}
          icon={TrendingUp}
        />
        <StatCard
          label="Top 10 Holdings"
          value={isLoading ? '...' : `${top10Percentage}%`}
          icon={Trophy}
        />
      </div>

      {/* Top 3 Holders Highlight */}
      {!isLoading && data?.holders && data.holders.length >= 3 && (
        <div className="grid md:grid-cols-3 gap-4">
          {data.holders.slice(0, 3).map((holder, index) => {
            const medals = ['text-yellow-500', 'text-gray-400', 'text-amber-600'];
            const medalLabels = ['1st Place', '2nd Place', '3rd Place'];
            return (
              <Card key={holder.address} className="relative overflow-hidden">
                <div className="absolute top-0 right-0 w-24 h-24 -mt-8 -mr-8 rounded-full bg-gradient-to-br from-yellow-500/10 to-transparent" />
                <div className="flex items-start gap-4">
                  <div className={`text-4xl font-bold ${medals[index]}`}>
                    #{holder.rank}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-xai-muted mb-1">{medalLabels[index]}</p>
                    <Link
                      to={`/address/${holder.address}`}
                      className="text-xai-primary hover:underline font-mono text-sm truncate block"
                    >
                      {holder.address}
                    </Link>
                    <p className="text-2xl font-bold text-white mt-2">
                      {formatXAI(holder.balance)}
                    </p>
                    <p className="text-sm text-xai-muted">
                      {holder.percentage.toFixed(4)}% of supply
                    </p>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}

      {/* Search and Table */}
      <Card padding="none">
        <div className="p-6 pb-4 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-xai-border">
          <CardHeader title="All Holders" />
          <div className="relative w-full sm:w-80">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-xai-muted" />
            <input
              type="text"
              placeholder="Search by address..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-xai-darker border border-xai-border rounded-lg text-white placeholder-xai-muted focus:outline-none focus:border-xai-primary"
            />
          </div>
        </div>

        {isLoading ? (
          <div className="p-8">
            <Loading />
          </div>
        ) : (
          <>
            <Table>
              <TableHeader>
                <TableHead className="w-20">Rank</TableHead>
                <TableHead>Address</TableHead>
                <TableHead align="right">Balance</TableHead>
                <TableHead align="right" className="hidden sm:table-cell">% Supply</TableHead>
                <TableHead align="right" className="hidden md:table-cell">Transactions</TableHead>
                <TableHead align="right" className="hidden lg:table-cell">Last Active</TableHead>
              </TableHeader>
              <TableBody>
                {displayHolders.map((holder) => (
                  <TableRow key={holder.address}>
                    <TableCell>
                      <span className={`font-bold ${
                        holder.rank === 1 ? 'text-yellow-500' :
                        holder.rank === 2 ? 'text-gray-400' :
                        holder.rank === 3 ? 'text-amber-600' :
                        'text-white'
                      }`}>
                        #{holder.rank}
                      </span>
                    </TableCell>
                    <TableCell>
                      <AddressLink address={holder.address} />
                    </TableCell>
                    <TableCell align="right" className="font-medium text-white">
                      {formatXAI(holder.balance)}
                    </TableCell>
                    <TableCell align="right" className="hidden sm:table-cell">
                      <div className="flex items-center justify-end gap-2">
                        <div className="w-24 h-2 bg-xai-darker rounded-full overflow-hidden">
                          <div
                            className="h-full bg-xai-primary rounded-full"
                            style={{ width: `${Math.min(holder.percentage * 10, 100)}%` }}
                          />
                        </div>
                        <span className="text-xai-muted w-16 text-right">
                          {holder.percentage.toFixed(4)}%
                        </span>
                      </div>
                    </TableCell>
                    <TableCell align="right" className="hidden md:table-cell text-xai-muted">
                      {formatNumber(holder.transaction_count)}
                    </TableCell>
                    <TableCell align="right" className="hidden lg:table-cell text-xai-muted">
                      {formatTimeAgo(holder.last_active)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>

            {/* Pagination */}
            {!searchQuery && totalPages > 1 && (
              <div className="p-4 border-t border-xai-border flex items-center justify-between">
                <p className="text-sm text-xai-muted">
                  Showing {page * PAGE_SIZE + 1} - {Math.min((page + 1) * PAGE_SIZE, data?.total || 0)} of {formatNumber(data?.total || 0)} addresses
                </p>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setPage(p => Math.max(0, p - 1))}
                    disabled={page === 0}
                    className="p-2 rounded-lg bg-xai-card hover:bg-xai-darker disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    <ChevronLeft className="h-5 w-5 text-white" />
                  </button>
                  <span className="text-sm text-white px-4">
                    Page {page + 1} of {totalPages}
                  </span>
                  <button
                    onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
                    disabled={page >= totalPages - 1}
                    className="p-2 rounded-lg bg-xai-card hover:bg-xai-darker disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    <ChevronRight className="h-5 w-5 text-white" />
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </Card>

      {/* Distribution Info */}
      <Card>
        <CardHeader title="Supply Distribution" />
        <div className="mt-4 space-y-4">
          <div className="h-4 bg-xai-darker rounded-full overflow-hidden flex">
            <div
              className="h-full bg-yellow-500"
              style={{ width: `${(data?.holders[0]?.percentage || 0) * 5}%` }}
              title="Top 1"
            />
            <div
              className="h-full bg-xai-primary"
              style={{ width: `${((parseFloat(top10Percentage) || 0) - (data?.holders[0]?.percentage || 0)) * 5}%` }}
              title="Top 2-10"
            />
            <div
              className="h-full bg-green-500"
              style={{ width: `${25}%` }}
              title="Top 11-100"
            />
            <div
              className="h-full bg-gray-600"
              style={{ width: 'auto' }}
              title="Others"
            />
          </div>
          <div className="flex flex-wrap gap-4 text-sm">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded bg-yellow-500" />
              <span className="text-xai-muted">Top 1</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded bg-xai-primary" />
              <span className="text-xai-muted">Top 2-10</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded bg-green-500" />
              <span className="text-xai-muted">Top 11-100</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded bg-gray-600" />
              <span className="text-xai-muted">Others</span>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}
