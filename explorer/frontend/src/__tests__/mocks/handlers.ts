import { http, HttpResponse } from 'msw';
import {
  mockBlocks,
  mockBlock,
  mockTransaction,
  mockAddress,
  mockNetworkStats,
  mockAITasks,
  mockAITask,
  mockAIModels,
  mockAIStats,
  mockSearchResults,
} from './data';

export const handlers = [
  // Blocks API
  http.get('/api/v1/blocks', ({ request }) => {
    const url = new URL(request.url);
    const page = parseInt(url.searchParams.get('page') || '1');
    const limit = parseInt(url.searchParams.get('limit') || '20');

    return HttpResponse.json({
      blocks: mockBlocks.slice(0, limit),
      total: 100,
    });
  }),

  http.get('/api/v1/blocks/:blockId', ({ params }) => {
    const { blockId } = params;
    if (blockId === 'notfound') {
      return new HttpResponse(null, { status: 404 });
    }
    return HttpResponse.json({
      ...mockBlock,
      height: parseInt(blockId as string) || mockBlock.height,
    });
  }),

  // Transactions API
  http.get('/api/v1/transactions/:txid', ({ params }) => {
    const { txid } = params;
    if (txid === 'notfound') {
      return new HttpResponse(null, { status: 404 });
    }
    return HttpResponse.json({
      ...mockTransaction,
      txid: txid as string,
    });
  }),

  // Address API
  http.get('/api/v1/addresses/:address', ({ params }) => {
    const { address } = params;
    if (address === 'notfound') {
      return new HttpResponse(null, { status: 404 });
    }
    return HttpResponse.json({
      ...mockAddress,
      address: address as string,
    });
  }),

  // Search API
  http.get('/api/v1/search', ({ request }) => {
    const url = new URL(request.url);
    const query = url.searchParams.get('q');

    if (!query) {
      return HttpResponse.json({ results: [] });
    }

    return HttpResponse.json({
      results: mockSearchResults,
    });
  }),

  // Network Stats API
  http.get('/api/v1/analytics/network', () => {
    return HttpResponse.json({
      blockchain: {
        total_blocks: mockNetworkStats.blockchain.totalBlocks,
        total_transactions: mockNetworkStats.blockchain.totalTransactions,
        total_addresses: mockNetworkStats.blockchain.totalAddresses,
        active_addresses_24h: mockNetworkStats.blockchain.activeAddresses24h,
        avg_block_time: mockNetworkStats.blockchain.avgBlockTime,
        network_hashrate: mockNetworkStats.blockchain.networkHashrate,
        difficulty: mockNetworkStats.blockchain.difficulty,
        total_supply: mockNetworkStats.blockchain.totalSupply,
      },
      mempool: {
        pending_transactions: mockNetworkStats.mempool.pendingTransactions,
        total_size_kb: mockNetworkStats.mempool.totalSizeKb,
      },
      updated_at: mockNetworkStats.updatedAt,
    });
  }),

  // AI Tasks API
  http.get('/api/v1/ai/tasks', ({ request }) => {
    const url = new URL(request.url);
    const status = url.searchParams.get('status');
    const aiModel = url.searchParams.get('aiModel');

    let tasks = mockAITasks;

    if (status) {
      tasks = tasks.filter((t) => t.status === status);
    }
    if (aiModel) {
      tasks = tasks.filter((t) => t.aiModel === aiModel);
    }

    return HttpResponse.json({
      tasks: tasks.map((task) => ({
        task_id: task.taskId,
        task_type: task.taskType,
        complexity: task.complexity,
        status: task.status,
        provider_address: task.providerAddress,
        requester_address: task.requesterAddress,
        ai_model: task.aiModel,
        cost_estimate: task.costEstimate,
        actual_cost: task.actualCost,
        compute_time_seconds: task.computeTimeSeconds,
        created_at: task.createdAt,
        completed_at: task.completedAt,
        result_hash: task.resultHash,
        result_data: task.resultData,
      })),
      total: tasks.length,
    });
  }),

  http.get('/api/v1/ai/tasks/:taskId', ({ params }) => {
    const { taskId } = params;
    if (taskId === 'notfound') {
      return new HttpResponse(null, { status: 404 });
    }

    return HttpResponse.json({
      task_id: mockAITask.taskId,
      task_type: mockAITask.taskType,
      complexity: mockAITask.complexity,
      status: mockAITask.status,
      provider_address: mockAITask.providerAddress,
      requester_address: mockAITask.requesterAddress,
      ai_model: mockAITask.aiModel,
      cost_estimate: mockAITask.costEstimate,
      actual_cost: mockAITask.actualCost,
      compute_time_seconds: mockAITask.computeTimeSeconds,
      created_at: mockAITask.createdAt,
      completed_at: mockAITask.completedAt,
      result_hash: mockAITask.resultHash,
      result_data: mockAITask.resultData,
    });
  }),

  http.get('/api/v1/ai/models', () => {
    return HttpResponse.json({
      models: mockAIModels.map((model) => ({
        model_name: model.modelName,
        provider: model.provider,
        total_tasks: model.totalTasks,
        success_rate: model.successRate,
        average_compute_time: model.averageComputeTime,
        average_cost: model.averageCost,
        quality_score: model.qualityScore,
        last_used: model.lastUsed,
      })),
    });
  }),

  http.get('/api/v1/ai/stats', () => {
    return HttpResponse.json({
      total_tasks: mockAIStats.totalTasks,
      completed_tasks: mockAIStats.completedTasks,
      active_tasks: mockAIStats.activeTasks,
      failed_tasks: mockAIStats.failedTasks,
      total_compute_hours: mockAIStats.totalComputeHours,
      total_cost: mockAIStats.totalCost,
      active_providers: mockAIStats.activeProviders,
      models_in_use: mockAIStats.modelsInUse,
      average_task_time: mockAIStats.averageTaskTime,
      success_rate: mockAIStats.successRate,
    });
  }),
];
