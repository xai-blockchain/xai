import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router-dom';
import { Vote, Filter } from 'lucide-react';
import { Card, CardHeader } from '../components/Card';
import { Table, TableHeader, TableHead, TableBody, TableRow, TableCell } from '../components/Table';
import { Badge } from '../components/Badge';
import { AddressLink } from '../components/HashLink';
import { Pagination } from '../components/Pagination';
import { Loading } from '../components/Loading';
import { getProposals } from '../api/client';
import { formatTimeAgo, formatXAI } from '../utils/format';
import type { Proposal } from '../types';

const ITEMS_PER_PAGE = 20;

function getProposalStatusVariant(status: Proposal['status']): 'success' | 'warning' | 'error' | 'info' | 'default' {
  switch (status) {
    case 'passed':
      return 'success';
    case 'voting':
      return 'warning';
    case 'rejected':
      return 'error';
    case 'deposit':
      return 'info';
    default:
      return 'default';
  }
}

export function Governance() {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<string>('all');

  const { data, isLoading, error } = useQuery({
    queryKey: ['proposals', page, ITEMS_PER_PAGE, statusFilter],
    queryFn: () => getProposals({
      page,
      limit: ITEMS_PER_PAGE,
      status: statusFilter === 'all' ? undefined : statusFilter,
    }),
    refetchInterval: 30000,
  });

  const totalPages = data ? Math.ceil(data.total / ITEMS_PER_PAGE) : 1;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-xai-primary/10">
            <Vote className="h-5 w-5 text-xai-primary" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">Governance</h1>
            <p className="text-sm text-xai-muted">
              {data ? `${data.total} total proposals` : 'Loading...'}
            </p>
          </div>
        </div>

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
            <option value="all">All Proposals</option>
            <option value="voting">Voting</option>
            <option value="passed">Passed</option>
            <option value="rejected">Rejected</option>
            <option value="deposit">Deposit Period</option>
          </select>
        </div>
      </div>

      <Card padding="none">
        {isLoading ? (
          <div className="p-8">
            <Loading message="Loading proposals..." />
          </div>
        ) : error ? (
          <div className="p-8 text-center text-red-400">
            Failed to load proposals. Please try again.
          </div>
        ) : data?.proposals.length === 0 ? (
          <div className="p-8 text-center text-xai-muted">
            No proposals found.
          </div>
        ) : (
          <>
            <Table>
              <TableHeader>
                <TableHead>ID</TableHead>
                <TableHead>Title</TableHead>
                <TableHead>Proposer</TableHead>
                <TableHead align="center">Status</TableHead>
                <TableHead align="right">Deposit</TableHead>
                <TableHead align="right">Voting Ends</TableHead>
              </TableHeader>
              <TableBody>
                {data?.proposals.map((proposal) => (
                  <TableRow
                    key={proposal.proposalId}
                    onClick={() => navigate(`/governance/${proposal.proposalId}`)}
                  >
                    <TableCell>
                      <Link
                        to={`/governance/${proposal.proposalId}`}
                        className="text-xai-primary hover:underline font-medium"
                        onClick={(e) => e.stopPropagation()}
                      >
                        #{proposal.proposalId}
                      </Link>
                    </TableCell>
                    <TableCell>
                      <div className="max-w-xs truncate text-white">
                        {proposal.title}
                      </div>
                    </TableCell>
                    <TableCell>
                      <AddressLink address={proposal.proposer} />
                    </TableCell>
                    <TableCell align="center">
                      <Badge variant={getProposalStatusVariant(proposal.status)}>
                        {proposal.status}
                      </Badge>
                    </TableCell>
                    <TableCell align="right" className="text-white">
                      {formatXAI(proposal.totalDeposit)}
                    </TableCell>
                    <TableCell align="right" className="text-xai-muted">
                      {proposal.status === 'voting'
                        ? formatTimeAgo(proposal.votingEndTime)
                        : '-'}
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
