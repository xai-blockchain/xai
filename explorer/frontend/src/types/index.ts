export interface Block {
  height: number;
  hash: string;
  previousHash: string;
  timestamp: string;
  transactions: string[];
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
