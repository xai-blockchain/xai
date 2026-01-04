import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router-dom';
import { Shield, Filter, ArrowUpDown, CheckCircle, XCircle, AlertTriangle } from 'lucide-react';
import { Card, CardHeader } from '../components/Card';
import { Table, TableHeader, TableHead, TableBody, TableRow, TableCell } from '../components/Table';
import { Badge } from '../components/Badge';
import { Pagination } from '../components/Pagination';
import { Loading } from '../components/Loading';
import { StatCard } from '../components/StatCard';
import { getValidators, getStakingPool } from '../api/client';
import { formatNumber, formatXAI, formatPercentage } from '../utils/format';
import type { Validator } from '../types';

const ITEMS_PER_PAGE = 50;

function getValidatorStatusVariant(status: Validator['status']): 'success' | 'error' | 'warning' | 'default' {
  switch (status) {
    case 'active':
      return 'success';
    case 'jailed':
      return 'error';
    case 'inactive':
      return 'warning';
    default:
      return 'default';
  }
}

function getStatusIcon(status: Validator['status']) {
  switch (status) {
    case 'active':
      return <CheckCircle className="h-4 w-4 text-green-500" />;
    case 'jailed':
      return <AlertTriangle className="h-4 w-4 text-red-500" />;
    case 'inactive':
      return <XCircle className="h-4 w-4 text-yellow-500" />;
    default:
      return null;
  }
}

export function Validators() {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [sortBy, setSortBy] = useState<string>('voting_power');

  const { data: poolData } = useQuery({
    queryKey: ['stakingPool'],
    queryFn: getStakingPool,
    refetchInterval: 60000,
  });

  const { data, isLoading, error } = useQuery({
    queryKey: ['validators', page, ITEMS_PER_PAGE, statusFilter, sortBy],
    queryFn: () => getValidators({
      page,
      limit: ITEMS_PER_PAGE,
      status: statusFilter === 'all' ? undefined : statusFilter,
      sortBy,
    }),
    refetchInterval: 30000,
  });

  const totalPages = data ? Math.ceil(data.total / ITEMS_PER_PAGE) : 1;

  // Calculate stats
  const activeValidators = data?.validators.filter(v => v.status === 'active').length || 0;
  const totalBonded = poolData ? formatXAI(poolData.bondedTokens) : '...';
  const bondedRatio = poolData ? formatPercentage(poolData.bondedRatio * 100) : '...';

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-xai-primary/10">
            <Shield className="h-5 w-5 text-xai-primary" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">Validators</h1>
            <p className="text-sm text-xai-muted">
              {data ? `${data.total} total validators` : 'Loading...'}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4 text-xai-muted" />
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setPage(1);
              }}
              className="rounded-lg border border-xai-border bg-xai-card py-2 px-3 text-sm text-white focus:border-xai-primary focus:outline-none"
            >
              <option value="all">All Status</option>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
              <option value="jailed">Jailed</option>
            </select>
          </div>

          <div className="flex items-center gap-2">
            <ArrowUpDown className="h-4 w-4 text-xai-muted" />
            <select
              value={sortBy}
              onChange={(e) => {
                setSortBy(e.target.value);
                setPage(1);
              }}
              className="rounded-lg border border-xai-border bg-xai-card py-2 px-3 text-sm text-white focus:border-xai-primary focus:outline-none"
            >
              <option value="voting_power">Voting Power</option>
              <option value="commission">Commission</option>
              <option value="name">Name</option>
            </select>
          </div>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Active Validators"
          value={formatNumber(activeValidators)}
          icon={Shield}
        />
        <StatCard
          label="Total Bonded"
          value={totalBonded}
          icon={Shield}
        />
        <StatCard
          label="Bonded Ratio"
          value={bondedRatio}
          icon={Shield}
        />
        <StatCard
          label="Inflation Rate"
          value={poolData ? formatPercentage(poolData.inflationRate * 100) : '...'}
          icon={Shield}
        />
      </div>

      <Card padding="none">
        {isLoading ? (
          <div className="p-8">
            <Loading message="Loading validators..." />
          </div>
        ) : error ? (
          <div className="p-8 text-center text-red-400">
            Failed to load validators. Please try again.
          </div>
        ) : data?.validators.length === 0 ? (
          <div className="p-8 text-center text-xai-muted">
            No validators found.
          </div>
        ) : (
          <>
            <Table>
              <TableHeader>
                <TableHead className="w-16">Rank</TableHead>
                <TableHead>Validator</TableHead>
                <TableHead align="center">Status</TableHead>
                <TableHead align="right">Voting Power</TableHead>
                <TableHead align="right">Commission</TableHead>
                <TableHead align="right">Uptime</TableHead>
              </TableHeader>
              <TableBody>
                {data?.validators.map((validator) => (
                  <TableRow
                    key={validator.operatorAddress}
                    onClick={() => navigate(`/validators/${validator.operatorAddress}`)}
                  >
                    <TableCell className="font-medium text-xai-muted">
                      #{validator.rank}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-3">
                        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-xai-primary/10">
                          <span className="text-xs font-bold text-xai-primary">
                            {validator.moniker.charAt(0).toUpperCase()}
                          </span>
                        </div>
                        <div>
                          <Link
                            to={`/validators/${validator.operatorAddress}`}
                            className="text-white hover:text-xai-primary font-medium"
                            onClick={(e) => e.stopPropagation()}
                          >
                            {validator.moniker}
                          </Link>
                          {validator.website && (
                            <a
                              href={validator.website}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="block text-xs text-xai-muted hover:text-xai-primary truncate max-w-[200px]"
                              onClick={(e) => e.stopPropagation()}
                            >
                              {validator.website.replace(/^https?:\/\//, '')}
                            </a>
                          )}
                        </div>
                      </div>
                    </TableCell>
                    <TableCell align="center">
                      <div className="flex items-center justify-center gap-2">
                        {getStatusIcon(validator.status)}
                        <Badge variant={getValidatorStatusVariant(validator.status)}>
                          {validator.status}
                        </Badge>
                      </div>
                    </TableCell>
                    <TableCell align="right">
                      <div>
                        <div className="text-white">{formatXAI(validator.votingPower)}</div>
                        <div className="text-xs text-xai-muted">
                          {formatPercentage(validator.votingPowerPercentage)}
                        </div>
                      </div>
                    </TableCell>
                    <TableCell align="right" className="text-white">
                      {formatPercentage(validator.commissionRate * 100)}
                    </TableCell>
                    <TableCell align="right">
                      <span className={validator.uptimePercentage >= 99 ? 'text-green-400' : validator.uptimePercentage >= 95 ? 'text-yellow-400' : 'text-red-400'}>
                        {formatPercentage(validator.uptimePercentage)}
                      </span>
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
