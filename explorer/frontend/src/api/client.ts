import axios from 'axios';
import type {
  Block,
  Transaction,
  Address,
  NetworkStats,
  AITask,
  AIModel,
  AIStats,
  SearchResult,
  TransactionAnalytics,
  BlockAnalytics,
  AddressAnalytics,
  AIAnalytics,
  RichListResponse,
  Proposal,
  Vote,
  Validator,
  StakingPool,
  Delegation,
  Rewards,
  UnbondingResponse,
  Delegator,
} from '../types';

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Blocks API
export async function getBlocks(page = 1, limit = 20): Promise<{ blocks: Block[]; total: number }> {
  const { data } = await api.get('/blocks', { params: { page, limit } });
  return {
    blocks: data.blocks || [],
    total: data.total || 0,
  };
}

export async function getBlock(blockId: string): Promise<Block> {
  const { data } = await api.get(`/blocks/${blockId}`);
  return data;
}

// Transactions API
export async function getTransactions(page = 1, limit = 20): Promise<{ transactions: Transaction[]; total: number }> {
  const { data } = await api.get('/blocks', { params: { page, limit } });
  // Aggregate transactions from blocks for now
  const transactions: Transaction[] = [];
  for (const block of data.blocks || []) {
    if (block.transactions) {
      for (const tx of block.transactions) {
        transactions.push(typeof tx === 'string' ? { txid: tx } as Transaction : tx);
      }
    }
  }
  return { transactions, total: data.total || 0 };
}

export async function getTransaction(txid: string): Promise<Transaction> {
  const { data } = await api.get(`/transactions/${txid}`);
  return data;
}

// Address API
export async function getAddress(address: string): Promise<Address> {
  const { data } = await api.get(`/addresses/${address}`);
  return data;
}

// Search API
export async function search(query: string): Promise<SearchResult[]> {
  const { data } = await api.get('/search', { params: { q: query } });
  return data.results || [];
}

// Network Stats API
export async function getNetworkStats(): Promise<NetworkStats> {
  const { data } = await api.get('/analytics/network');
  return {
    blockchain: {
      totalBlocks: data.blockchain?.total_blocks || 0,
      totalTransactions: data.blockchain?.total_transactions || 0,
      totalAddresses: data.blockchain?.total_addresses || 0,
      activeAddresses24h: data.blockchain?.active_addresses_24h || 0,
      avgBlockTime: data.blockchain?.avg_block_time || 0,
      networkHashrate: data.blockchain?.network_hashrate || '0',
      difficulty: data.blockchain?.difficulty || 0,
      totalSupply: data.blockchain?.total_supply || '0',
    },
    mempool: {
      pendingTransactions: data.mempool?.pending_transactions || 0,
      totalSizeKb: data.mempool?.total_size_kb || 0,
    },
    updatedAt: data.updated_at || new Date().toISOString(),
  };
}

// AI Tasks API
export async function getAITasks(params?: {
  status?: string;
  taskType?: string;
  aiModel?: string;
  page?: number;
  limit?: number;
}): Promise<{ tasks: AITask[]; total: number }> {
  const { data } = await api.get('/ai/tasks', { params });
  return {
    tasks: (data.tasks || []).map(transformAITask),
    total: data.total || 0,
  };
}

export async function getAITask(taskId: string): Promise<AITask> {
  const { data } = await api.get(`/ai/tasks/${taskId}`);
  return transformAITask(data);
}

export async function getAIModels(): Promise<AIModel[]> {
  const { data } = await api.get('/ai/models');
  return (data.models || []).map(transformAIModel);
}

export async function getAIStats(): Promise<AIStats> {
  const { data } = await api.get('/ai/stats');
  return {
    totalTasks: data.total_tasks || 0,
    completedTasks: data.completed_tasks || 0,
    activeTasks: data.active_tasks || 0,
    failedTasks: data.failed_tasks || 0,
    totalComputeHours: data.total_compute_hours || 0,
    totalCost: data.total_cost || 0,
    activeProviders: data.active_providers || 0,
    modelsInUse: data.models_in_use || 0,
    averageTaskTime: data.average_task_time || 0,
    successRate: data.success_rate || 0,
  };
}

// Transform helpers (snake_case to camelCase)
function transformAITask(task: Record<string, unknown>): AITask {
  return {
    taskId: task.task_id as string,
    taskType: task.task_type as string,
    complexity: task.complexity as AITask['complexity'],
    status: task.status as AITask['status'],
    providerAddress: task.provider_address as string,
    requesterAddress: task.requester_address as string | undefined,
    aiModel: task.ai_model as string,
    costEstimate: task.cost_estimate as number,
    actualCost: task.actual_cost as number | undefined,
    computeTimeSeconds: task.compute_time_seconds as number | undefined,
    createdAt: task.created_at as string,
    completedAt: task.completed_at as string | undefined,
    resultHash: task.result_hash as string | undefined,
    resultData: task.result_data as Record<string, unknown> | undefined,
  };
}

function transformAIModel(model: Record<string, unknown>): AIModel {
  return {
    modelName: model.model_name as string,
    provider: model.provider as string,
    totalTasks: model.total_tasks as number,
    successRate: model.success_rate as number,
    averageComputeTime: model.average_compute_time as number,
    averageCost: model.average_cost as number,
    qualityScore: model.quality_score as number,
    lastUsed: model.last_used as string,
  };
}

// Analytics API
export async function getTransactionAnalytics(period = '24h'): Promise<TransactionAnalytics> {
  const { data } = await api.get('/analytics/transactions', { params: { period } });
  return data;
}

export async function getBlockAnalytics(period = '24h'): Promise<BlockAnalytics> {
  const { data } = await api.get('/analytics/blocks', { params: { period } });
  return data;
}

export async function getAddressAnalytics(period = '24h'): Promise<AddressAnalytics> {
  const { data } = await api.get('/analytics/addresses', { params: { period } });
  return data;
}

export async function getAIAnalytics(period = '24h'): Promise<AIAnalytics> {
  const { data } = await api.get('/analytics/ai', { params: { period } });
  return data;
}

// Rich List API
export async function getRichList(limit = 100, offset = 0): Promise<RichListResponse> {
  const { data } = await api.get('/analytics/richlist', { params: { limit, offset } });
  return data;
}

// Governance API
export async function getProposals(params?: {
  page?: number;
  limit?: number;
  status?: string;
}): Promise<{ proposals: Proposal[]; total: number }> {
  const { data } = await api.get('/governance/proposals', { params });
  return {
    proposals: (data.proposals || []).map(transformProposal),
    total: data.total || 0,
  };
}

export async function getProposal(proposalId: number): Promise<Proposal> {
  const { data } = await api.get(`/governance/proposals/${proposalId}`);
  return transformProposal(data);
}

export async function getProposalVotes(
  proposalId: number,
  page = 1,
  limit = 50
): Promise<{ votes: Vote[]; total: number }> {
  const { data } = await api.get(`/governance/proposals/${proposalId}/votes`, {
    params: { page, limit },
  });
  return {
    votes: (data.votes || []).map(transformVote),
    total: data.total || 0,
  };
}

// Staking API
export async function getStakingPool(): Promise<StakingPool> {
  const { data } = await api.get('/staking/pool');
  return transformStakingPool(data);
}

export async function getValidators(params?: {
  page?: number;
  limit?: number;
  status?: string;
  sortBy?: string;
}): Promise<{ validators: Validator[]; total: number }> {
  const { data } = await api.get('/staking/validators', { params });
  return {
    validators: (data.validators || []).map(transformValidator),
    total: data.total || 0,
  };
}

export async function getValidator(address: string): Promise<Validator> {
  const { data } = await api.get(`/staking/validators/${address}`);
  return transformValidator(data);
}

export async function getValidatorDelegators(
  address: string,
  page = 1,
  limit = 50
): Promise<{ delegators: Delegator[]; total: number }> {
  const { data } = await api.get(`/staking/validators/${address}/delegators`, {
    params: { page, limit },
  });
  return {
    delegators: (data.delegators || []).map(transformDelegator),
    total: data.total || 0,
  };
}

export async function getDelegations(
  address: string,
  page = 1,
  limit = 20
): Promise<{ delegations: Delegation[]; total: number }> {
  const { data } = await api.get(`/staking/delegations/${address}`, {
    params: { page, limit },
  });
  return {
    delegations: (data.delegations || []).map(transformDelegation),
    total: data.total || 0,
  };
}

export async function getRewards(address: string): Promise<Rewards> {
  const { data } = await api.get(`/staking/rewards/${address}`);
  return transformRewards(data);
}

export async function getUnbonding(address: string): Promise<UnbondingResponse> {
  const { data } = await api.get(`/staking/unbonding/${address}`);
  return transformUnbonding(data);
}

// Transform helpers for Governance
function transformProposal(p: Record<string, unknown>): Proposal {
  return {
    proposalId: (p.proposal_id as number) || 0,
    title: (p.title as string) || '',
    description: (p.description as string) || '',
    status: (p.status as Proposal['status']) || 'deposit',
    proposer: (p.proposer as string) || '',
    submitTime: (p.submit_time as string) || '',
    depositEndTime: (p.deposit_end_time as string) || '',
    votingStartTime: (p.voting_start_time as string) || '',
    votingEndTime: (p.voting_end_time as string) || '',
    totalDeposit: (p.total_deposit as string) || '0',
    yesVotes: (p.yes_votes as string) || '0',
    noVotes: (p.no_votes as string) || '0',
    abstainVotes: (p.abstain_votes as string) || '0',
    noWithVetoVotes: (p.no_with_veto_votes as string) || '0',
    tallyResult: p.tally_result
      ? {
          yes: ((p.tally_result as Record<string, unknown>).yes as string) || '0',
          no: ((p.tally_result as Record<string, unknown>).no as string) || '0',
          abstain: ((p.tally_result as Record<string, unknown>).abstain as string) || '0',
          noWithVeto: ((p.tally_result as Record<string, unknown>).no_with_veto as string) || '0',
          totalVotingPower: ((p.tally_result as Record<string, unknown>).total_voting_power as string) || '0',
          quorumReached: ((p.tally_result as Record<string, unknown>).quorum_reached as boolean) || false,
          thresholdReached: ((p.tally_result as Record<string, unknown>).threshold_reached as boolean) || false,
        }
      : undefined,
  };
}

function transformVote(v: Record<string, unknown>): Vote {
  return {
    voter: (v.voter as string) || '',
    proposalId: (v.proposal_id as number) || 0,
    option: (v.option as Vote['option']) || 'abstain',
    votingPower: (v.voting_power as string) || '0',
    timestamp: (v.timestamp as string) || '',
  };
}

// Transform helpers for Staking
function transformStakingPool(p: Record<string, unknown>): StakingPool {
  return {
    bondedTokens: (p.bonded_tokens as string) || '0',
    notBondedTokens: (p.not_bonded_tokens as string) || '0',
    totalSupply: (p.total_supply as string) || '0',
    bondedRatio: (p.bonded_ratio as number) || 0,
    inflationRate: (p.inflation_rate as number) || 0,
    annualProvisions: (p.annual_provisions as string) || '0',
    communityPool: (p.community_pool as string) || '0',
  };
}

function transformValidator(v: Record<string, unknown>): Validator {
  return {
    operatorAddress: (v.operator_address as string) || '',
    consensusPubkey: (v.consensus_pubkey as string) || '',
    moniker: (v.moniker as string) || '',
    website: v.website as string | undefined,
    details: v.details as string | undefined,
    identity: v.identity as string | undefined,
    securityContact: v.security_contact as string | undefined,
    status: (v.status as Validator['status']) || 'inactive',
    jailed: (v.jailed as boolean) || false,
    tokens: (v.tokens as string) || '0',
    delegatorShares: (v.delegator_shares as string) || '0',
    votingPower: (v.voting_power as string) || '0',
    votingPowerPercentage: (v.voting_power_percentage as number) || 0,
    commissionRate: (v.commission_rate as number) || (v.commission as Record<string, unknown>)?.rate as number || 0,
    commissionMaxRate: (v.commission_max_rate as number) || (v.commission as Record<string, unknown>)?.max_rate as number || 0,
    commissionMaxChangeRate: (v.commission_max_change_rate as number) || (v.commission as Record<string, unknown>)?.max_change_rate as number || 0,
    minSelfDelegation: (v.min_self_delegation as string) || '1',
    selfDelegation: v.self_delegation as string | undefined,
    delegatorCount: v.delegator_count as number | undefined,
    uptimePercentage: (v.uptime_percentage as number) || (v.uptime as Record<string, unknown>)?.uptime_percentage as number || 0,
    rank: (v.rank as number) || 0,
    commission: v.commission
      ? {
          rate: ((v.commission as Record<string, unknown>).rate as number) || 0,
          maxRate: ((v.commission as Record<string, unknown>).max_rate as number) || 0,
          maxChangeRate: ((v.commission as Record<string, unknown>).max_change_rate as number) || 0,
          updateTime: ((v.commission as Record<string, unknown>).update_time as string) || '',
        }
      : undefined,
    uptime: v.uptime
      ? {
          uptimePercentage: ((v.uptime as Record<string, unknown>).uptime_percentage as number) || 0,
          missedBlocksCounter: ((v.uptime as Record<string, unknown>).missed_blocks_counter as number) || 0,
          signedBlocksWindow: ((v.uptime as Record<string, unknown>).signed_blocks_window as number) || 0,
          startHeight: ((v.uptime as Record<string, unknown>).start_height as number) || 0,
        }
      : undefined,
    slashing: v.slashing
      ? {
          slashEvents: (((v.slashing as Record<string, unknown>).slash_events as unknown[]) || []).map((e: unknown) => e as import('../types').SlashEvent),
          totalSlashed: ((v.slashing as Record<string, unknown>).total_slashed as string) || '0',
        }
      : undefined,
    createdAt: v.created_at as string | undefined,
  };
}

function transformDelegation(d: Record<string, unknown>): Delegation {
  return {
    delegatorAddress: (d.delegator_address as string) || '',
    validatorAddress: (d.validator_address as string) || '',
    validatorName: d.validator_name as string | undefined,
    shares: (d.shares as string) || '0',
    balance: (d.balance as string) || '0',
    rewards: d.rewards as string | undefined,
  };
}

function transformDelegator(d: Record<string, unknown>): Delegator {
  return {
    delegatorAddress: (d.delegator_address as string) || '',
    shares: (d.shares as string) || '0',
    balance: (d.balance as string) || '0',
  };
}

function transformRewards(r: Record<string, unknown>): Rewards {
  return {
    address: (r.address as string) || '',
    totalRewards: (r.total_rewards as string) || '0',
    rewardsByValidator: ((r.rewards_by_validator as Record<string, unknown>[]) || []).map((rv) => ({
      validatorAddress: (rv.validator_address as string) || '',
      validatorName: (rv.validator_name as string) || '',
      reward: (rv.reward as string) || '0',
    })),
  };
}

function transformUnbonding(u: Record<string, unknown>): UnbondingResponse {
  return {
    address: (u.address as string) || '',
    unbondingDelegations: ((u.unbonding_delegations as Record<string, unknown>[]) || []).map((ud) => ({
      validatorAddress: (ud.validator_address as string) || '',
      validatorName: ud.validator_name as string | undefined,
      entries: ((ud.entries as Record<string, unknown>[]) || []).map((e) => ({
        creationHeight: (e.creation_height as number) || 0,
        completionTime: (e.completion_time as string) || '',
        initialBalance: (e.initial_balance as string) || '0',
        balance: (e.balance as string) || '0',
      })),
    })),
    totalUnbonding: (u.total_unbonding as string) || '0',
  };
}

export default api;
