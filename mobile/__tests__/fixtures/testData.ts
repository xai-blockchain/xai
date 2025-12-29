/**
 * Test fixtures and mock data for XAI mobile tests
 */

import { Transaction, Block, BlockchainStats, MempoolStats, NodeInfo, HealthStatus } from '../../src/types';

// ============== Wallet Fixtures ==============

export const mockWallet = {
  address: 'XAIa1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2',
  publicKey: 'publickey123456789012345678901234567890123456789012345678901234',
  privateKey: 'privatekey12345678901234567890123456789012345678901234567890123',
  createdAt: 1700000000000,
};

export const mockAltWallet = {
  address: 'XAIf1e2d3c4b5a6f1e2d3c4b5a6f1e2d3c4b5a6f1e2',
  publicKey: 'altpublickey12345678901234567890123456789012345678901234567890',
  privateKey: 'altprivatekey1234567890123456789012345678901234567890123456789',
  createdAt: 1700100000000,
};

// ============== Transaction Fixtures ==============

export const mockOutgoingTransaction: Transaction = {
  txid: 'outtxid123456789012345678901234567890123456789012345678901234',
  sender: mockWallet.address,
  recipient: mockAltWallet.address,
  amount: 100.5,
  fee: 0.001,
  timestamp: 1700000000,
  nonce: 5,
  signature: 'sig123456789',
  status: 'confirmed',
  confirmations: 10,
  blockIndex: 1000,
};

export const mockIncomingTransaction: Transaction = {
  txid: 'intxid1234567890123456789012345678901234567890123456789012345',
  sender: mockAltWallet.address,
  recipient: mockWallet.address,
  amount: 50.25,
  fee: 0.001,
  timestamp: 1700000100,
  nonce: 3,
  signature: 'sig987654321',
  status: 'confirmed',
  confirmations: 5,
  blockIndex: 1001,
};

export const mockPendingTransaction: Transaction = {
  txid: 'pendtxid12345678901234567890123456789012345678901234567890123',
  sender: mockWallet.address,
  recipient: mockAltWallet.address,
  amount: 25,
  fee: 0.002,
  timestamp: 1700000200,
  nonce: 6,
  signature: 'sig111222333',
  status: 'pending',
};

export function createMockTransaction(overrides: Partial<Transaction> = {}): Transaction {
  return {
    txid: `tx${Math.random().toString(36).substr(2, 9)}`.padEnd(64, '0'),
    sender: mockWallet.address,
    recipient: mockAltWallet.address,
    amount: 100,
    fee: 0.001,
    timestamp: Math.floor(Date.now() / 1000),
    nonce: 1,
    status: 'confirmed',
    ...overrides,
  };
}

// ============== Block Fixtures ==============

export const mockBlock: Block = {
  index: 1000,
  hash: 'blockhash12345678901234567890123456789012345678901234567890123456',
  previousHash: 'prevhash123456789012345678901234567890123456789012345678901234',
  timestamp: 1700000000,
  difficulty: 100000,
  nonce: 12345678,
  miner: mockWallet.address,
  merkleRoot: 'merkle12345678901234567890123456789012345678901234567890123456',
  transactions: [mockOutgoingTransaction],
};

export const mockGenesisBlock: Block = {
  index: 0,
  hash: 'genesishash0000000000000000000000000000000000000000000000000000',
  previousHash: '0000000000000000000000000000000000000000000000000000000000000000',
  timestamp: 1690000000,
  difficulty: 1,
  nonce: 0,
  miner: 'XAIgenesis00000000000000000000000000000000',
  merkleRoot: 'genesismerkle00000000000000000000000000000000000000000000000000',
  transactions: [],
};

export function createMockBlock(overrides: Partial<Block> = {}): Block {
  return {
    index: 1000,
    hash: `hash${Math.random().toString(36).substr(2, 9)}`.padEnd(64, '0'),
    previousHash: `prevhash${Math.random().toString(36).substr(2, 9)}`.padEnd(64, '0'),
    timestamp: Math.floor(Date.now() / 1000),
    difficulty: 100000,
    nonce: Math.floor(Math.random() * 1000000),
    miner: mockWallet.address,
    merkleRoot: `merkle${Math.random().toString(36).substr(2, 9)}`.padEnd(64, '0'),
    transactions: [],
    ...overrides,
  };
}

// ============== Stats Fixtures ==============

export const mockBlockchainStats: BlockchainStats = {
  chainHeight: 5000,
  difficulty: 150000,
  totalSupply: 21000000,
  pendingTransactionsCount: 25,
  latestBlockHash: mockBlock.hash,
  minerAddress: mockWallet.address,
  peers: 8,
  isMining: true,
  nodeUptime: 86400,
};

export const mockMempoolStats: MempoolStats = {
  fees: {
    averageFee: 0.0012,
    medianFee: 0.001,
    averageFeeRate: 0.00001,
    medianFeeRate: 0.000008,
    minFeeRate: 0.000005,
    maxFeeRate: 0.0001,
    recommendedFeeRates: {
      slow: 0.0005,
      standard: 0.001,
      priority: 0.002,
    },
  },
  pressure: {
    status: 'normal',
    capacityRatio: 0.3,
    pendingTransactions: 25,
    maxTransactions: 1000,
  },
};

export const mockCongestionMempoolStats: MempoolStats = {
  ...mockMempoolStats,
  pressure: {
    status: 'elevated',
    capacityRatio: 0.8,
    pendingTransactions: 800,
    maxTransactions: 1000,
  },
};

// ============== Node Info Fixtures ==============

export const mockNodeInfo: NodeInfo = {
  status: 'online',
  node: 'xai-node-primary',
  version: '1.0.0',
  algorithmicFeatures: true,
};

export const mockHealthStatus: HealthStatus = {
  status: 'healthy',
  timestamp: 1700000000,
  blockchain: {
    accessible: true,
    height: 5000,
    difficulty: 150000,
    totalSupply: 21000000,
    latestBlockHash: mockBlock.hash,
  },
  services: {
    api: 'running',
    storage: 'running',
    p2p: 'running',
  },
  network: {
    peers: 8,
  },
};

export const mockUnhealthyStatus: HealthStatus = {
  status: 'unhealthy',
  timestamp: 1700000000,
  blockchain: {
    accessible: false,
  },
  services: {
    api: 'error',
  },
  network: {
    peers: 0,
  },
};

// ============== API Response Fixtures ==============

export function createSuccessResponse<T>(data: T) {
  return { success: true, data };
}

export function createErrorResponse(error: string, code?: string) {
  return { success: false, error, code };
}

// ============== Address Fixtures ==============

export const validAddresses = [
  'XAIa1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2',
  'XAI0000000000000000000000000000000000000000',
  'XAIFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFffff',
  'XAIABCDEF1234567890abcdef1234567890ABCDEF',
];

export const invalidAddresses = [
  '',
  'invalid',
  'XAI', // Too short
  'XAIabc123', // Too short
  'BTCa1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2', // Wrong prefix
  'XAIg1h2i3j4k5l6g1h2i3j4k5l6g1h2i3j4k5l6g1h2', // Invalid hex
  'XAIa1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2extra', // Too long
];

// ============== Helper Functions ==============

export function generateTransactionHistory(count: number): Transaction[] {
  return Array.from({ length: count }, (_, i) => ({
    txid: `tx${i.toString().padStart(60, '0')}`,
    sender: i % 2 === 0 ? mockWallet.address : mockAltWallet.address,
    recipient: i % 2 === 0 ? mockAltWallet.address : mockWallet.address,
    amount: (i + 1) * 10,
    fee: 0.001,
    timestamp: 1700000000 - i * 600,
    nonce: i + 1,
    status: 'confirmed' as const,
    confirmations: count - i,
    blockIndex: 1000 - i,
  }));
}

export function generateBlockChain(count: number): Block[] {
  return Array.from({ length: count }, (_, i) => ({
    index: count - i,
    hash: `hash${(count - i).toString().padStart(60, '0')}`,
    previousHash: i === count - 1
      ? '0'.repeat(64)
      : `hash${(count - i - 1).toString().padStart(60, '0')}`,
    timestamp: 1700000000 - i * 60,
    difficulty: 100000,
    nonce: Math.floor(Math.random() * 1000000),
    miner: mockWallet.address,
    merkleRoot: `merkle${i.toString().padStart(58, '0')}`,
    transactions: [],
  }));
}
