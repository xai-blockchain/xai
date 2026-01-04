import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Vote, ChevronLeft, CheckCircle, XCircle, MinusCircle, AlertTriangle, Users } from 'lucide-react';
import { Card, CardHeader } from '../components/Card';
import { Table, TableHeader, TableHead, TableBody, TableRow, TableCell } from '../components/Table';
import { Badge } from '../components/Badge';
import { AddressLink } from '../components/HashLink';
import { CopyButton } from '../components/CopyButton';
import { Loading } from '../components/Loading';
import { Pagination } from '../components/Pagination';
import { getProposal, getProposalVotes } from '../api/client';
import { formatDate, formatTimeAgo, formatXAI, formatNumber } from '../utils/format';
import type { Proposal, Vote as VoteType } from '../types';

const VOTES_PER_PAGE = 20;

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

function getVoteOptionVariant(option: VoteType['option']): 'success' | 'error' | 'warning' | 'default' {
  switch (option) {
    case 'yes':
      return 'success';
    case 'no':
      return 'error';
    case 'no_with_veto':
      return 'error';
    case 'abstain':
      return 'warning';
    default:
      return 'default';
  }
}

function VoteTallyChart({ proposal }: { proposal: Proposal }) {
  const yes = parseFloat(proposal.yesVotes) || 0;
  const no = parseFloat(proposal.noVotes) || 0;
  const abstain = parseFloat(proposal.abstainVotes) || 0;
  const noWithVeto = parseFloat(proposal.noWithVetoVotes) || 0;
  const total = yes + no + abstain + noWithVeto;

  if (total === 0) {
    return (
      <div className="text-center py-8 text-xai-muted">
        No votes yet
      </div>
    );
  }

  const yesPercent = (yes / total) * 100;
  const noPercent = (no / total) * 100;
  const abstainPercent = (abstain / total) * 100;
  const vetoPercent = (noWithVeto / total) * 100;

  return (
    <div className="space-y-4">
      {/* Stacked bar */}
      <div className="h-8 rounded-lg overflow-hidden flex">
        {yesPercent > 0 && (
          <div
            className="bg-green-500 h-full transition-all"
            style={{ width: `${yesPercent}%` }}
            title={`Yes: ${yesPercent.toFixed(1)}%`}
          />
        )}
        {noPercent > 0 && (
          <div
            className="bg-red-500 h-full transition-all"
            style={{ width: `${noPercent}%` }}
            title={`No: ${noPercent.toFixed(1)}%`}
          />
        )}
        {vetoPercent > 0 && (
          <div
            className="bg-red-700 h-full transition-all"
            style={{ width: `${vetoPercent}%` }}
            title={`No with Veto: ${vetoPercent.toFixed(1)}%`}
          />
        )}
        {abstainPercent > 0 && (
          <div
            className="bg-yellow-500 h-full transition-all"
            style={{ width: `${abstainPercent}%` }}
            title={`Abstain: ${abstainPercent.toFixed(1)}%`}
          />
        )}
      </div>

      {/* Legend */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="flex items-center gap-2">
          <CheckCircle className="h-4 w-4 text-green-500" />
          <div>
            <div className="text-sm text-white">{formatXAI(yes)}</div>
            <div className="text-xs text-xai-muted">Yes ({yesPercent.toFixed(1)}%)</div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <XCircle className="h-4 w-4 text-red-500" />
          <div>
            <div className="text-sm text-white">{formatXAI(no)}</div>
            <div className="text-xs text-xai-muted">No ({noPercent.toFixed(1)}%)</div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 text-red-700" />
          <div>
            <div className="text-sm text-white">{formatXAI(noWithVeto)}</div>
            <div className="text-xs text-xai-muted">Veto ({vetoPercent.toFixed(1)}%)</div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <MinusCircle className="h-4 w-4 text-yellow-500" />
          <div>
            <div className="text-sm text-white">{formatXAI(abstain)}</div>
            <div className="text-xs text-xai-muted">Abstain ({abstainPercent.toFixed(1)}%)</div>
          </div>
        </div>
      </div>

      {/* Quorum/Threshold indicators */}
      {proposal.tallyResult && (
        <div className="flex gap-4 pt-2 border-t border-xai-border">
          <div className="flex items-center gap-2">
            {proposal.tallyResult.quorumReached ? (
              <CheckCircle className="h-4 w-4 text-green-500" />
            ) : (
              <XCircle className="h-4 w-4 text-red-500" />
            )}
            <span className="text-sm text-xai-muted">
              Quorum {proposal.tallyResult.quorumReached ? 'Reached' : 'Not Reached'}
            </span>
          </div>
          <div className="flex items-center gap-2">
            {proposal.tallyResult.thresholdReached ? (
              <CheckCircle className="h-4 w-4 text-green-500" />
            ) : (
              <XCircle className="h-4 w-4 text-red-500" />
            )}
            <span className="text-sm text-xai-muted">
              Threshold {proposal.tallyResult.thresholdReached ? 'Reached' : 'Not Reached'}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

export function GovernanceDetail() {
  const { id } = useParams<{ id: string }>();
  const proposalId = parseInt(id || '0', 10);
  const [votesPage, setVotesPage] = useState(1);

  const { data: proposal, isLoading, error } = useQuery({
    queryKey: ['proposal', proposalId],
    queryFn: () => getProposal(proposalId),
    enabled: proposalId > 0,
  });

  const { data: votesData, isLoading: votesLoading } = useQuery({
    queryKey: ['proposalVotes', proposalId, votesPage, VOTES_PER_PAGE],
    queryFn: () => getProposalVotes(proposalId, votesPage, VOTES_PER_PAGE),
    enabled: proposalId > 0,
  });

  if (isLoading) {
    return <Loading message="Loading proposal..." />;
  }

  if (error || !proposal) {
    return (
      <div className="text-center py-12">
        <Vote className="h-16 w-16 text-xai-muted mx-auto mb-4" />
        <h2 className="text-xl font-semibold text-white mb-2">Proposal Not Found</h2>
        <p className="text-xai-muted mb-6">
          The proposal you're looking for doesn't exist.
        </p>
        <Link
          to="/governance"
          className="inline-flex items-center gap-2 px-4 py-2 bg-xai-primary text-black rounded-lg font-medium hover:bg-xai-secondary transition-colors"
        >
          <ChevronLeft className="h-4 w-4" />
          Back to Governance
        </Link>
      </div>
    );
  }

  const votesTotalPages = votesData ? Math.ceil(votesData.total / VOTES_PER_PAGE) : 1;

  const details = [
    { label: 'Proposal ID', value: `#${proposal.proposalId}` },
    {
      label: 'Status',
      value: <Badge variant={getProposalStatusVariant(proposal.status)}>{proposal.status}</Badge>,
    },
    {
      label: 'Proposer',
      value: (
        <span className="flex items-center gap-2">
          <AddressLink address={proposal.proposer} truncate={false} />
          <CopyButton text={proposal.proposer} />
        </span>
      ),
    },
    { label: 'Submit Time', value: `${formatDate(proposal.submitTime)} (${formatTimeAgo(proposal.submitTime)})` },
    { label: 'Deposit End', value: formatDate(proposal.depositEndTime) },
    { label: 'Voting Start', value: formatDate(proposal.votingStartTime) },
    { label: 'Voting End', value: formatDate(proposal.votingEndTime) },
    { label: 'Total Deposit', value: formatXAI(proposal.totalDeposit) },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-3">
          <Link
            to="/governance"
            className="flex h-10 w-10 items-center justify-center rounded-lg bg-xai-card hover:bg-xai-border transition-colors"
          >
            <ChevronLeft className="h-5 w-5 text-xai-muted" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-white">
              Proposal #{proposal.proposalId}
            </h1>
            <p className="text-sm text-xai-muted">{proposal.title}</p>
          </div>
        </div>
        <Badge variant={getProposalStatusVariant(proposal.status)} className="text-sm px-4 py-1">
          {proposal.status.toUpperCase()}
        </Badge>
      </div>

      {/* Proposal Details */}
      <Card>
        <CardHeader title="Proposal Details" />
        <div className="space-y-4">
          {details.map((item, index) => (
            <div
              key={item.label}
              className={`flex flex-col sm:flex-row sm:items-start gap-2 py-3 ${
                index < details.length - 1 ? 'border-b border-xai-border' : ''
              }`}
            >
              <span className="text-xai-muted sm:w-40 shrink-0">{item.label}</span>
              <span className="text-white flex-1">{item.value}</span>
            </div>
          ))}
        </div>
      </Card>

      {/* Description */}
      <Card>
        <CardHeader title="Description" />
        <div className="prose prose-invert max-w-none">
          <pre className="whitespace-pre-wrap text-sm text-xai-muted bg-xai-darker p-4 rounded-lg overflow-auto">
            {proposal.description}
          </pre>
        </div>
      </Card>

      {/* Vote Tally */}
      <Card>
        <CardHeader title="Vote Tally" />
        <VoteTallyChart proposal={proposal} />
      </Card>

      {/* Voters List */}
      <Card padding="none">
        <div className="p-6 pb-0">
          <CardHeader
            title={`Voters (${votesData?.total || 0})`}
            subtitle="All votes cast for this proposal"
          />
        </div>
        {votesLoading ? (
          <div className="p-6">
            <Loading size="sm" />
          </div>
        ) : votesData?.votes.length === 0 ? (
          <div className="p-8 text-center">
            <Users className="h-12 w-12 text-xai-muted mx-auto mb-3" />
            <p className="text-xai-muted">No votes yet</p>
          </div>
        ) : (
          <>
            <Table>
              <TableHeader>
                <TableHead>Voter</TableHead>
                <TableHead align="center">Vote</TableHead>
                <TableHead align="right">Voting Power</TableHead>
                <TableHead align="right">Time</TableHead>
              </TableHeader>
              <TableBody>
                {votesData?.votes.map((vote) => (
                  <TableRow key={vote.voter}>
                    <TableCell>
                      <AddressLink address={vote.voter} />
                    </TableCell>
                    <TableCell align="center">
                      <Badge variant={getVoteOptionVariant(vote.option)}>
                        {vote.option.replace('_', ' ')}
                      </Badge>
                    </TableCell>
                    <TableCell align="right" className="text-white">
                      {formatXAI(vote.votingPower)}
                    </TableCell>
                    <TableCell align="right" className="text-xai-muted">
                      {formatTimeAgo(vote.timestamp)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>

            {votesTotalPages > 1 && (
              <div className="p-4 border-t border-xai-border">
                <Pagination
                  currentPage={votesPage}
                  totalPages={votesTotalPages}
                  onPageChange={setVotesPage}
                />
              </div>
            )}
          </>
        )}
      </Card>
    </div>
  );
}
