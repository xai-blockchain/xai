import type { Block, Transaction, Address, NetworkStats, AITask, AIModel, AIStats, SearchResult } from '../../types';

export const mockBlock: Block = {
  height: 12345,
  hash: '0000000000000000000abc123def456789012345678901234567890123456789',
  previousHash: '0000000000000000000111222333444555666777888999000111222333444555',
  timestamp: '2024-01-15T10:30:00Z',
  transactions: ['tx1hash123456789012345678901234567890123456789012345678901234567'],
  transactionCount: 1,
  miner: 'XAIminer123456789012345678901234',
  difficulty: 1234567890,
  nonce: 987654321,
  size: 1024,
  merkleRoot: 'merkle123456789012345678901234567890123456789012345678901234567',
};

export const mockBlocks: Block[] = [
  mockBlock,
  {
    ...mockBlock,
    height: 12344,
    hash: '0000000000000000000bbb123def456789012345678901234567890123456789',
    previousHash: '0000000000000000000ccc222333444555666777888999000111222333444555',
    transactionCount: 3,
  },
  {
    ...mockBlock,
    height: 12343,
    hash: '0000000000000000000ccc123def456789012345678901234567890123456789',
    previousHash: '0000000000000000000ddd222333444555666777888999000111222333444555',
    transactionCount: 5,
  },
];

export const mockTransaction: Transaction = {
  txid: 'tx1hash1234567890123456789012345678901234567890123456789012345678',
  blockHash: mockBlock.hash,
  blockHeight: mockBlock.height,
  timestamp: '2024-01-15T10:30:00Z',
  type: 'transfer',
  from: 'XAIsender12345678901234567890123',
  to: 'XAIreceiver123456789012345678901',
  amount: '100.5',
  fee: '0.001',
  status: 'confirmed',
  confirmations: 10,
  inputs: [
    {
      txid: 'prev_tx_hash_12345678901234567890123456789012345678901234567890',
      vout: 0,
      address: 'XAIsender12345678901234567890123',
      amount: '100.501',
    },
  ],
  outputs: [
    {
      index: 0,
      address: 'XAIreceiver123456789012345678901',
      amount: '100.5',
    },
  ],
};

export const mockTransactions: Transaction[] = [
  mockTransaction,
  {
    ...mockTransaction,
    txid: 'tx2hash1234567890123456789012345678901234567890123456789012345678',
    amount: '50.25',
    type: 'ai_task',
  },
  {
    ...mockTransaction,
    txid: 'tx3hash1234567890123456789012345678901234567890123456789012345678',
    amount: '200',
    status: 'pending',
  },
];

export const mockAddress: Address = {
  address: 'XAIaddress123456789012345678901234',
  balance: '1000.5',
  totalReceived: '5000',
  totalSent: '3999.5',
  transactionCount: 25,
  transactions: mockTransactions,
};

export const mockNetworkStats: NetworkStats = {
  blockchain: {
    totalBlocks: 100000,
    totalTransactions: 500000,
    totalAddresses: 10000,
    activeAddresses24h: 500,
    avgBlockTime: 12.5,
    networkHashrate: '125.5 TH/s',
    difficulty: 1234567890,
    totalSupply: '21000000',
  },
  mempool: {
    pendingTransactions: 150,
    totalSizeKb: 256.5,
  },
  updatedAt: '2024-01-15T10:30:00Z',
};

export const mockAITask: AITask = {
  taskId: 'task123456789012345678901234567890',
  taskType: 'text_generation',
  complexity: 'moderate',
  status: 'completed',
  providerAddress: 'XAIprovider12345678901234567890',
  requesterAddress: 'XAIrequester123456789012345678',
  aiModel: 'gpt-4',
  costEstimate: 0.05,
  actualCost: 0.048,
  computeTimeSeconds: 12.5,
  createdAt: '2024-01-15T10:00:00Z',
  completedAt: '2024-01-15T10:00:12Z',
  resultHash: 'result_hash_1234567890123456789012345678901234567890123456789',
  resultData: {
    estimated_tokens: 500,
    actual_tokens: 485,
  },
};

export const mockAITasks: AITask[] = [
  mockAITask,
  {
    ...mockAITask,
    taskId: 'task223456789012345678901234567890',
    taskType: 'image_generation',
    complexity: 'complex',
    status: 'in_progress',
    aiModel: 'dall-e-3',
  },
  {
    ...mockAITask,
    taskId: 'task323456789012345678901234567890',
    taskType: 'code_review',
    complexity: 'low',
    status: 'pending',
    aiModel: 'codellama',
  },
  {
    ...mockAITask,
    taskId: 'task423456789012345678901234567890',
    taskType: 'analysis',
    complexity: 'critical',
    status: 'failed',
    aiModel: 'claude-3',
  },
];

export const mockAIModel: AIModel = {
  modelName: 'gpt-4',
  provider: 'OpenAI',
  totalTasks: 1500,
  successRate: 98.5,
  averageComputeTime: 8.5,
  averageCost: 0.045,
  qualityScore: 9.2,
  lastUsed: '2024-01-15T10:30:00Z',
};

export const mockAIModels: AIModel[] = [
  mockAIModel,
  {
    modelName: 'claude-3',
    provider: 'Anthropic',
    totalTasks: 1200,
    successRate: 97.8,
    averageComputeTime: 10.2,
    averageCost: 0.052,
    qualityScore: 9.4,
    lastUsed: '2024-01-15T09:45:00Z',
  },
  {
    modelName: 'codellama',
    provider: 'Meta',
    totalTasks: 800,
    successRate: 96.5,
    averageComputeTime: 5.5,
    averageCost: 0.025,
    qualityScore: 8.8,
    lastUsed: '2024-01-15T08:30:00Z',
  },
];

export const mockAIStats: AIStats = {
  totalTasks: 50000,
  completedTasks: 48000,
  activeTasks: 150,
  failedTasks: 1850,
  totalComputeHours: 12500,
  totalCost: 25000,
  activeProviders: 45,
  modelsInUse: 12,
  averageTaskTime: 15.5,
  successRate: 96.3,
};

export const mockSearchResults: SearchResult[] = [
  { type: 'block', id: '12345', preview: 'Block #12345' },
  { type: 'transaction', id: 'tx1hash123...', preview: 'Transfer 100 XAI' },
  { type: 'address', id: 'XAIaddress123...', preview: 'Balance: 1000 XAI' },
];
