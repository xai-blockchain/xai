export interface Block {
  height: number;
  hash: string;
  previousHash: string;
  timestamp: string;
  transactions: (string | { txid: string })[];
  transactionCount: number;
  miner: string;
  difficulty: number;
  nonce: number;
  size: number;
  merkleRoot: string;
}

export interface Transaction {
  txid: string;
  blockHash: string;
  blockHeight: number;
  timestamp: string;
  type: 'transfer' | 'ai_task' | 'coinbase' | 'contract';
  from: string;
  to: string;
  amount: string;
  fee: string;
  status: 'confirmed' | 'pending';
  confirmations: number;
  inputs?: TxInput[];
  outputs?: TxOutput[];
  aiTask?: AITask;
}

export interface TxInput {
  txid: string;
  vout: number;
  address: string;
  amount: string;
}

export interface TxOutput {
  index: number;
  address: string;
  amount: string;
}

export interface Address {
  address: string;
  balance: string;
  totalReceived: string;
  totalSent: string;
  transactionCount: number;
  transactions: Transaction[];
}

export interface NetworkStats {
  blockchain: {
    totalBlocks: number;
    totalTransactions: number;
    totalAddresses: number;
    activeAddresses24h: number;
    avgBlockTime: number;
    networkHashrate: string;
    difficulty: number;
    totalSupply: string;
  };
  mempool: {
    pendingTransactions: number;
    totalSizeKb: number;
  };
  updatedAt: string;
}

export interface AITask {
  taskId: string;
  taskType: string;
  complexity: 'low' | 'moderate' | 'complex' | 'critical';
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  providerAddress: string;
  requesterAddress?: string;
  aiModel: string;
  costEstimate: number;
  actualCost?: number;
  computeTimeSeconds?: number;
  createdAt: string;
  completedAt?: string;
  resultHash?: string;
  resultData?: Record<string, unknown>;
}

export interface AIModel {
  modelName: string;
  provider: string;
  totalTasks: number;
  successRate: number;
  averageComputeTime: number;
  averageCost: number;
  qualityScore: number;
  lastUsed: string;
}

export interface AIStats {
  totalTasks: number;
  completedTasks: number;
  activeTasks: number;
  failedTasks: number;
  totalComputeHours: number;
  totalCost: number;
  activeProviders: number;
  modelsInUse: number;
  averageTaskTime: number;
  successRate: number;
}

export interface SearchResult {
  type: 'block' | 'transaction' | 'address';
  id: string;
  preview: string;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  limit: number;
}

// Analytics Types
export interface TimelineDataPoint {
  timestamp: string;
  [key: string]: string | number;
}

export interface TransactionAnalytics {
  period: string;
  timeline: {
    timestamp: string;
    transaction_count: number;
    volume: number;
    ai_transactions: number;
    transfer_transactions: number;
    contract_transactions: number;
  }[];
  summary: {
    total_transactions: number;
    total_volume: number;
    avg_transactions_per_interval: number;
    peak_transactions: number;
  };
}

export interface BlockAnalytics {
  period: string;
  timeline: {
    timestamp: string;
    blocks_produced: number;
    avg_block_time: number;
    avg_transactions_per_block: number;
    difficulty: number;
    avg_block_size: number;
  }[];
  summary: {
    total_blocks: number;
    avg_block_time: number;
    avg_difficulty: number;
    total_transactions: number;
  };
}

export interface AddressAnalytics {
  period: string;
  timeline: {
    timestamp: string;
    active_addresses: number;
    new_addresses: number;
    unique_senders: number;
    unique_receivers: number;
  }[];
  summary: {
    total_active: number;
    total_new: number;
    peak_active: number;
    avg_active: number;
  };
}

export interface AIAnalytics {
  period: string;
  summary: {
    total_tasks: number;
    completed_tasks: number;
    total_compute_cost: number;
    average_providers: number;
  };
  timeline: {
    timestamp: string;
    tasks_created: number;
    tasks_completed: number;
    compute_cost: number;
    active_providers: number;
  }[];
  task_types: {
    type: string;
    count: number;
    percentage: number;
  }[];
  model_usage: {
    model: string;
    tasks: number;
    percentage: number;
  }[];
}

export interface RichListHolder {
  rank: number;
  address: string;
  balance: number;
  percentage: number;
  transaction_count: number;
  last_active: string;
}

export interface RichListResponse {
  holders: RichListHolder[];
  total: number;
  limit: number;
  offset: number;
  total_supply: number;
  circulating_supply: number;
}

// WebSocket Types
export interface WebSocketMessage {
  type: 'block' | 'transaction' | 'ai_task' | 'pong' | 'error';
  data: Block | Transaction | AITask | string;
  timestamp?: string;
}

// Governance Types
export interface Proposal {
  proposalId: number;
  title: string;
  description: string;
  status: 'deposit' | 'voting' | 'passed' | 'rejected';
  proposer: string;
  submitTime: string;
  depositEndTime: string;
  votingStartTime: string;
  votingEndTime: string;
  totalDeposit: string;
  yesVotes: string;
  noVotes: string;
  abstainVotes: string;
  noWithVetoVotes: string;
  tallyResult?: TallyResult;
}

export interface TallyResult {
  yes: string;
  no: string;
  abstain: string;
  noWithVeto: string;
  totalVotingPower: string;
  quorumReached: boolean;
  thresholdReached: boolean;
}

export interface Vote {
  voter: string;
  proposalId: number;
  option: 'yes' | 'no' | 'abstain' | 'no_with_veto';
  votingPower: string;
  timestamp: string;
}

// Staking Types
export interface StakingPool {
  bondedTokens: string;
  notBondedTokens: string;
  totalSupply: string;
  bondedRatio: number;
  inflationRate: number;
  annualProvisions: string;
  communityPool: string;
}

export interface Validator {
  operatorAddress: string;
  consensusPubkey: string;
  moniker: string;
  website?: string;
  details?: string;
  identity?: string;
  securityContact?: string;
  status: 'active' | 'inactive' | 'jailed';
  jailed: boolean;
  tokens: string;
  delegatorShares: string;
  votingPower: string;
  votingPowerPercentage: number;
  commissionRate: number;
  commissionMaxRate: number;
  commissionMaxChangeRate: number;
  minSelfDelegation: string;
  selfDelegation?: string;
  delegatorCount?: number;
  uptimePercentage: number;
  rank: number;
  commission?: ValidatorCommission;
  uptime?: ValidatorUptime;
  slashing?: ValidatorSlashing;
  createdAt?: string;
}

export interface ValidatorCommission {
  rate: number;
  maxRate: number;
  maxChangeRate: number;
  updateTime: string;
}

export interface ValidatorUptime {
  uptimePercentage: number;
  missedBlocksCounter: number;
  signedBlocksWindow: number;
  startHeight: number;
}

export interface ValidatorSlashing {
  slashEvents: SlashEvent[];
  totalSlashed: string;
}

export interface SlashEvent {
  height: number;
  fraction: string;
  reason: string;
  timestamp: string;
}

export interface Delegation {
  delegatorAddress: string;
  validatorAddress: string;
  validatorName?: string;
  shares: string;
  balance: string;
  rewards?: string;
}

export interface Rewards {
  address: string;
  totalRewards: string;
  rewardsByValidator: ValidatorReward[];
}

export interface ValidatorReward {
  validatorAddress: string;
  validatorName: string;
  reward: string;
}

export interface UnbondingDelegation {
  validatorAddress: string;
  validatorName?: string;
  entries: UnbondingEntry[];
}

export interface UnbondingEntry {
  creationHeight: number;
  completionTime: string;
  initialBalance: string;
  balance: string;
}

export interface UnbondingResponse {
  address: string;
  unbondingDelegations: UnbondingDelegation[];
  totalUnbonding: string;
}

export interface Delegator {
  delegatorAddress: string;
  shares: string;
  balance: string;
}
