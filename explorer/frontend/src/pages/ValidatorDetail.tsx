import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Shield,
  ChevronLeft,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Globe,
  Mail,
  Users,
  TrendingUp,
  Clock,
  ExternalLink,
} from 'lucide-react';
import { Card, CardHeader } from '../components/Card';
import { Table, TableHeader, TableHead, TableBody, TableRow, TableCell } from '../components/Table';
import { Badge } from '../components/Badge';
import { AddressLink } from '../components/HashLink';
import { CopyButton } from '../components/CopyButton';
import { Loading } from '../components/Loading';
import { Pagination } from '../components/Pagination';
import { StatCard } from '../components/StatCard';
import { getValidator, getValidatorDelegators } from '../api/client';
import { formatDate, formatTimeAgo, formatXAI, formatNumber, formatPercentage } from '../utils/format';
import type { Validator } from '../types';

const DELEGATORS_PER_PAGE = 20;

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
      return <CheckCircle className="h-5 w-5 text-green-500" />;
    case 'jailed':
      return <AlertTriangle className="h-5 w-5 text-red-500" />;
    case 'inactive':
      return <XCircle className="h-5 w-5 text-yellow-500" />;
    default:
      return null;
  }
}

export function ValidatorDetail() {
  const { address } = useParams<{ address: string }>();
  const [delegatorsPage, setDelegatorsPage] = useState(1);

  const { data: validator, isLoading, error } = useQuery({
    queryKey: ['validator', address],
    queryFn: () => getValidator(address!),
    enabled: !!address,
  });

  const { data: delegatorsData, isLoading: delegatorsLoading } = useQuery({
    queryKey: ['validatorDelegators', address, delegatorsPage, DELEGATORS_PER_PAGE],
    queryFn: () => getValidatorDelegators(address!, delegatorsPage, DELEGATORS_PER_PAGE),
    enabled: !!address,
  });

  if (isLoading) {
    return <Loading message="Loading validator..." />;
  }

  if (error || !validator) {
    return (
      <div className="text-center py-12">
        <Shield className="h-16 w-16 text-xai-muted mx-auto mb-4" />
        <h2 className="text-xl font-semibold text-white mb-2">Validator Not Found</h2>
        <p className="text-xai-muted mb-6">
          The validator you're looking for doesn't exist.
        </p>
        <Link
          to="/validators"
          className="inline-flex items-center gap-2 px-4 py-2 bg-xai-primary text-black rounded-lg font-medium hover:bg-xai-secondary transition-colors"
        >
          <ChevronLeft className="h-4 w-4" />
          Back to Validators
        </Link>
      </div>
    );
  }

  const delegatorsTotalPages = delegatorsData ? Math.ceil(delegatorsData.total / DELEGATORS_PER_PAGE) : 1;

  const details = [
    {
      label: 'Operator Address',
      value: (
        <span className="flex items-center gap-2">
          <span className="font-mono text-sm break-all">{validator.operatorAddress}</span>
          <CopyButton text={validator.operatorAddress} />
        </span>
      ),
    },
    {
      label: 'Status',
      value: (
        <div className="flex items-center gap-2">
          {getStatusIcon(validator.status)}
          <Badge variant={getValidatorStatusVariant(validator.status)}>{validator.status}</Badge>
          {validator.jailed && <Badge variant="error">Jailed</Badge>}
        </div>
      ),
    },
    { label: 'Rank', value: `#${validator.rank}` },
    { label: 'Voting Power', value: `${formatXAI(validator.votingPower)} (${formatPercentage(validator.votingPowerPercentage)})` },
    { label: 'Self Delegation', value: validator.selfDelegation ? formatXAI(validator.selfDelegation) : 'N/A' },
    { label: 'Delegators', value: validator.delegatorCount ? formatNumber(validator.delegatorCount) : 'N/A' },
    { label: 'Commission Rate', value: formatPercentage(validator.commissionRate * 100) },
    { label: 'Max Commission', value: formatPercentage(validator.commissionMaxRate * 100) },
    { label: 'Max Change Rate', value: formatPercentage(validator.commissionMaxChangeRate * 100) },
    { label: 'Min Self Delegation', value: formatXAI(validator.minSelfDelegation) },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
        <div className="flex items-start gap-3">
          <Link
            to="/validators"
            className="flex h-10 w-10 items-center justify-center rounded-lg bg-xai-card hover:bg-xai-border transition-colors shrink-0"
          >
            <ChevronLeft className="h-5 w-5 text-xai-muted" />
          </Link>
          <div className="flex items-center gap-4">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-xai-primary/10">
              <span className="text-2xl font-bold text-xai-primary">
                {validator.moniker.charAt(0).toUpperCase()}
              </span>
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white">{validator.moniker}</h1>
              <div className="flex items-center gap-3 mt-1">
                <Badge variant={getValidatorStatusVariant(validator.status)}>
                  {validator.status}
                </Badge>
                <span className="text-sm text-xai-muted">Rank #{validator.rank}</span>
              </div>
              {validator.website && (
                <a
                  href={validator.website}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1 text-sm text-xai-primary hover:underline mt-1"
                >
                  <Globe className="h-3 w-3" />
                  {validator.website.replace(/^https?:\/\//, '')}
                  <ExternalLink className="h-3 w-3" />
                </a>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Voting Power"
          value={formatXAI(validator.votingPower)}
          icon={TrendingUp}
        />
        <StatCard
          label="Commission"
          value={formatPercentage(validator.commissionRate * 100)}
          icon={Shield}
        />
        <StatCard
          label="Uptime"
          value={formatPercentage(validator.uptimePercentage)}
          icon={Clock}
        />
        <StatCard
          label="Delegators"
          value={validator.delegatorCount ? formatNumber(validator.delegatorCount) : 'N/A'}
          icon={Users}
        />
      </div>

      {/* Description */}
      {validator.details && (
        <Card>
          <CardHeader title="Description" />
          <p className="text-xai-muted">{validator.details}</p>
          <div className="flex gap-4 mt-4 pt-4 border-t border-xai-border">
            {validator.website && (
              <a
                href={validator.website}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 text-sm text-xai-primary hover:underline"
              >
                <Globe className="h-4 w-4" />
                Website
              </a>
            )}
            {validator.securityContact && (
              <a
                href={`mailto:${validator.securityContact}`}
                className="flex items-center gap-2 text-sm text-xai-primary hover:underline"
              >
                <Mail className="h-4 w-4" />
                Contact
              </a>
            )}
          </div>
        </Card>
      )}

      {/* Validator Details */}
      <Card>
        <CardHeader title="Validator Details" />
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

      {/* Uptime Info */}
      {validator.uptime && (
        <Card>
          <CardHeader title="Uptime & Performance" />
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="p-4 bg-xai-darker rounded-lg">
              <div className="text-sm text-xai-muted">Uptime</div>
              <div className={`text-2xl font-bold ${
                validator.uptime.uptimePercentage >= 99 ? 'text-green-400' :
                validator.uptime.uptimePercentage >= 95 ? 'text-yellow-400' : 'text-red-400'
              }`}>
                {formatPercentage(validator.uptime.uptimePercentage)}
              </div>
            </div>
            <div className="p-4 bg-xai-darker rounded-lg">
              <div className="text-sm text-xai-muted">Missed Blocks</div>
              <div className="text-2xl font-bold text-white">
                {formatNumber(validator.uptime.missedBlocksCounter)}
              </div>
            </div>
            <div className="p-4 bg-xai-darker rounded-lg">
              <div className="text-sm text-xai-muted">Signed Blocks Window</div>
              <div className="text-2xl font-bold text-white">
                {formatNumber(validator.uptime.signedBlocksWindow)}
              </div>
            </div>
            <div className="p-4 bg-xai-darker rounded-lg">
              <div className="text-sm text-xai-muted">Start Height</div>
              <div className="text-2xl font-bold text-white">
                {formatNumber(validator.uptime.startHeight)}
              </div>
            </div>
          </div>
        </Card>
      )}

      {/* Delegators List */}
      <Card padding="none">
        <div className="p-6 pb-0">
          <CardHeader
            title={`Delegators (${delegatorsData?.total || 0})`}
            subtitle="Users who have delegated tokens to this validator"
          />
        </div>
        {delegatorsLoading ? (
          <div className="p-6">
            <Loading size="sm" />
          </div>
        ) : delegatorsData?.delegators.length === 0 ? (
          <div className="p-8 text-center">
            <Users className="h-12 w-12 text-xai-muted mx-auto mb-3" />
            <p className="text-xai-muted">No delegators yet</p>
          </div>
        ) : (
          <>
            <Table>
              <TableHeader>
                <TableHead>Delegator</TableHead>
                <TableHead align="right">Shares</TableHead>
                <TableHead align="right">Balance</TableHead>
              </TableHeader>
              <TableBody>
                {delegatorsData?.delegators.map((delegator) => (
                  <TableRow key={delegator.delegatorAddress}>
                    <TableCell>
                      <AddressLink address={delegator.delegatorAddress} />
                    </TableCell>
                    <TableCell align="right" className="text-xai-muted">
                      {formatXAI(delegator.shares)}
                    </TableCell>
                    <TableCell align="right" className="text-white">
                      {formatXAI(delegator.balance)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>

            {delegatorsTotalPages > 1 && (
              <div className="p-4 border-t border-xai-border">
                <Pagination
                  currentPage={delegatorsPage}
                  totalPages={delegatorsTotalPages}
                  onPageChange={setDelegatorsPage}
                />
              </div>
            )}
          </>
        )}
      </Card>
    </div>
  );
}
