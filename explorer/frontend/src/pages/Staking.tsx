import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link, useSearchParams } from 'react-router-dom';
import { Coins, Search, TrendingUp, Clock, Gift, AlertCircle } from 'lucide-react';
import { Card, CardHeader } from '../components/Card';
import { Table, TableHeader, TableHead, TableBody, TableRow, TableCell } from '../components/Table';
import { Badge } from '../components/Badge';
import { AddressLink } from '../components/HashLink';
import { Loading } from '../components/Loading';
import { StatCard } from '../components/StatCard';
import { getDelegations, getRewards, getUnbonding, getStakingPool } from '../api/client';
import { formatXAI, formatTimeAgo, formatPercentage, formatNumber } from '../utils/format';

export function Staking() {
  const [searchParams, setSearchParams] = useSearchParams();
  const addressFromParams = searchParams.get('address') || '';
  const [address, setAddress] = useState(addressFromParams);
  const [searchInput, setSearchInput] = useState(addressFromParams);

  const { data: poolData, isLoading: poolLoading } = useQuery({
    queryKey: ['stakingPool'],
    queryFn: getStakingPool,
    refetchInterval: 60000,
  });

  const { data: delegationsData, isLoading: delegationsLoading, error: delegationsError } = useQuery({
    queryKey: ['delegations', address],
    queryFn: () => getDelegations(address),
    enabled: !!address,
  });

  const { data: rewardsData, isLoading: rewardsLoading } = useQuery({
    queryKey: ['rewards', address],
    queryFn: () => getRewards(address),
    enabled: !!address,
  });

  const { data: unbondingData, isLoading: unbondingLoading } = useQuery({
    queryKey: ['unbonding', address],
    queryFn: () => getUnbonding(address),
    enabled: !!address,
  });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchInput.trim()) {
      setAddress(searchInput.trim());
      setSearchParams({ address: searchInput.trim() });
    }
  };

  const isLoading = delegationsLoading || rewardsLoading || unbondingLoading;

  // Calculate totals
  const totalDelegated = delegationsData?.delegations.reduce(
    (sum, d) => sum + parseFloat(d.balance || '0'),
    0
  ) || 0;

  const totalRewards = rewardsData?.totalRewards ? parseFloat(rewardsData.totalRewards) : 0;

  const totalUnbonding = unbondingData?.totalUnbonding ? parseFloat(unbondingData.totalUnbonding) : 0;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-xai-primary/10">
            <Coins className="h-5 w-5 text-xai-primary" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">Staking</h1>
            <p className="text-sm text-xai-muted">
              View delegations, rewards, and unbonding
            </p>
          </div>
        </div>
      </div>

      {/* Network Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Total Bonded"
          value={poolLoading ? '...' : formatXAI(poolData?.bondedTokens || '0')}
          icon={Coins}
        />
        <StatCard
          label="Bonded Ratio"
          value={poolLoading ? '...' : formatPercentage((poolData?.bondedRatio || 0) * 100)}
          icon={TrendingUp}
        />
        <StatCard
          label="Inflation Rate"
          value={poolLoading ? '...' : formatPercentage((poolData?.inflationRate || 0) * 100)}
          icon={TrendingUp}
        />
        <StatCard
          label="Community Pool"
          value={poolLoading ? '...' : formatXAI(poolData?.communityPool || '0')}
          icon={Gift}
        />
      </div>

      {/* Address Search */}
      <Card>
        <CardHeader title="View Staking Info" subtitle="Enter an address to view delegations and rewards" />
        <form onSubmit={handleSearch} className="flex gap-3">
          <div className="relative flex-1">
            <input
              type="text"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="Enter address (e.g., xai1...)"
              className="w-full rounded-lg border border-xai-border bg-xai-darker py-3 pl-10 pr-4 text-white placeholder-xai-muted focus:border-xai-primary focus:outline-none"
            />
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-xai-muted" />
          </div>
          <button
            type="submit"
            className="px-6 py-3 bg-xai-primary text-black rounded-lg font-medium hover:bg-xai-secondary transition-colors"
          >
            Search
          </button>
        </form>
      </Card>

      {/* Address-specific content */}
      {address && (
        <>
          {/* User Stats */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <Card>
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-green-500/10">
                  <Coins className="h-5 w-5 text-green-500" />
                </div>
                <div>
                  <div className="text-sm text-xai-muted">Total Delegated</div>
                  <div className="text-xl font-bold text-white">{formatXAI(totalDelegated)}</div>
                </div>
              </div>
            </Card>
            <Card>
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-xai-primary/10">
                  <Gift className="h-5 w-5 text-xai-primary" />
                </div>
                <div>
                  <div className="text-sm text-xai-muted">Pending Rewards</div>
                  <div className="text-xl font-bold text-white">{formatXAI(totalRewards)}</div>
                </div>
              </div>
            </Card>
            <Card>
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-yellow-500/10">
                  <Clock className="h-5 w-5 text-yellow-500" />
                </div>
                <div>
                  <div className="text-sm text-xai-muted">Unbonding</div>
                  <div className="text-xl font-bold text-white">{formatXAI(totalUnbonding)}</div>
                </div>
              </div>
            </Card>
          </div>

          {/* Delegations */}
          <Card padding="none">
            <div className="p-6 pb-0">
              <CardHeader
                title={`Delegations (${delegationsData?.delegations.length || 0})`}
                subtitle="Active delegations to validators"
              />
            </div>
            {isLoading ? (
              <div className="p-6">
                <Loading size="sm" />
              </div>
            ) : delegationsError ? (
              <div className="p-8 text-center text-red-400">
                Failed to load delegations. Please try again.
              </div>
            ) : delegationsData?.delegations.length === 0 ? (
              <div className="p-8 text-center">
                <Coins className="h-12 w-12 text-xai-muted mx-auto mb-3" />
                <p className="text-xai-muted">No delegations found for this address</p>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableHead>Validator</TableHead>
                  <TableHead align="right">Delegated</TableHead>
                  <TableHead align="right">Rewards</TableHead>
                </TableHeader>
                <TableBody>
                  {delegationsData?.delegations.map((delegation) => (
                    <TableRow key={delegation.validatorAddress}>
                      <TableCell>
                        <Link
                          to={`/validators/${delegation.validatorAddress}`}
                          className="text-xai-primary hover:underline"
                        >
                          {delegation.validatorName || delegation.validatorAddress.slice(0, 20) + '...'}
                        </Link>
                      </TableCell>
                      <TableCell align="right" className="text-white">
                        {formatXAI(delegation.balance)}
                      </TableCell>
                      <TableCell align="right" className="text-green-400">
                        {delegation.rewards ? formatXAI(delegation.rewards) : '-'}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </Card>

          {/* Rewards by Validator */}
          {rewardsData && rewardsData.rewardsByValidator.length > 0 && (
            <Card padding="none">
              <div className="p-6 pb-0">
                <CardHeader
                  title="Rewards by Validator"
                  subtitle="Pending rewards breakdown"
                />
              </div>
              <Table>
                <TableHeader>
                  <TableHead>Validator</TableHead>
                  <TableHead align="right">Reward</TableHead>
                </TableHeader>
                <TableBody>
                  {rewardsData.rewardsByValidator.map((reward) => (
                    <TableRow key={reward.validatorAddress}>
                      <TableCell>
                        <Link
                          to={`/validators/${reward.validatorAddress}`}
                          className="text-xai-primary hover:underline"
                        >
                          {reward.validatorName || reward.validatorAddress.slice(0, 20) + '...'}
                        </Link>
                      </TableCell>
                      <TableCell align="right" className="text-green-400">
                        {formatXAI(reward.reward)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Card>
          )}

          {/* Unbonding Delegations */}
          {unbondingData && unbondingData.unbondingDelegations.length > 0 && (
            <Card padding="none">
              <div className="p-6 pb-0">
                <CardHeader
                  title="Unbonding Delegations"
                  subtitle="Tokens being unbonded"
                />
              </div>
              <Table>
                <TableHeader>
                  <TableHead>Validator</TableHead>
                  <TableHead align="right">Amount</TableHead>
                  <TableHead align="right">Completion</TableHead>
                </TableHeader>
                <TableBody>
                  {unbondingData.unbondingDelegations.flatMap((ud) =>
                    ud.entries.map((entry, idx) => (
                      <TableRow key={`${ud.validatorAddress}-${idx}`}>
                        <TableCell>
                          <Link
                            to={`/validators/${ud.validatorAddress}`}
                            className="text-xai-primary hover:underline"
                          >
                            {ud.validatorName || ud.validatorAddress.slice(0, 20) + '...'}
                          </Link>
                        </TableCell>
                        <TableCell align="right" className="text-yellow-400">
                          {formatXAI(entry.balance)}
                        </TableCell>
                        <TableCell align="right" className="text-xai-muted">
                          {formatTimeAgo(entry.completionTime)}
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </Card>
          )}
        </>
      )}

      {/* No address state */}
      {!address && (
        <Card>
          <div className="text-center py-12">
            <AlertCircle className="h-16 w-16 text-xai-muted mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-white mb-2">Enter an Address</h2>
            <p className="text-xai-muted max-w-md mx-auto">
              Enter a wallet address above to view delegations, pending rewards, and unbonding tokens.
            </p>
          </div>
        </Card>
      )}
    </div>
  );
}
