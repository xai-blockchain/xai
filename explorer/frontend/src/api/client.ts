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

export default api;
