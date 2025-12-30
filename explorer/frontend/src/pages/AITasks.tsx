import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router-dom';
import { Cpu, Search, Filter } from 'lucide-react';
import { Card, CardHeader } from '../components/Card';
import { StatCard } from '../components/StatCard';
import { Table, TableHeader, TableHead, TableBody, TableRow, TableCell } from '../components/Table';
import { Badge, getStatusVariant } from '../components/Badge';
import { AddressLink } from '../components/HashLink';
import { Pagination } from '../components/Pagination';
import { Loading } from '../components/Loading';
import { getAITasks, getAIStats, getAIModels } from '../api/client';
import { formatNumber, formatTimeAgo, formatXAI, formatDuration, getComplexityColor } from '../utils/format';

const ITEMS_PER_PAGE = 20;

export function AITasks() {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [modelFilter, setModelFilter] = useState<string>('');

  const { data: stats } = useQuery({
    queryKey: ['aiStats'],
    queryFn: getAIStats,
    refetchInterval: 30000,
  });

  const { data: models } = useQuery({
    queryKey: ['aiModels'],
    queryFn: getAIModels,
  });

  const { data, isLoading, error } = useQuery({
    queryKey: ['aiTasks', page, statusFilter, modelFilter],
    queryFn: () => getAITasks({
      page,
      limit: ITEMS_PER_PAGE,
      status: statusFilter || undefined,
      aiModel: modelFilter || undefined,
    }),
    refetchInterval: 15000,
  });

  const totalPages = data ? Math.ceil(data.total / ITEMS_PER_PAGE) : 1;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-xai-primary/10">
          <Cpu className="h-5 w-5 text-xai-primary" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-white">AI Tasks</h1>
          <p className="text-sm text-xai-muted">
            Explore AI compute tasks on the XAI network
          </p>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Total Tasks"
          value={stats ? formatNumber(stats.totalTasks) : '...'}
        />
        <StatCard
          label="Success Rate"
          value={stats ? `${stats.successRate.toFixed(1)}%` : '...'}
        />
        <StatCard
          label="Active Providers"
          value={stats ? formatNumber(stats.activeProviders) : '...'}
        />
        <StatCard
          label="Total Cost"
          value={stats ? formatXAI(stats.totalCost) : '...'}
        />
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-4">
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-xai-muted" />
          <span className="text-sm text-xai-muted">Filters:</span>
        </div>

        <select
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value);
            setPage(1);
          }}
          className="rounded-lg border border-xai-border bg-xai-card px-3 py-2 text-sm text-white focus:border-xai-primary focus:outline-none"
        >
          <option value="">All Status</option>
          <option value="pending">Pending</option>
          <option value="in_progress">In Progress</option>
          <option value="completed">Completed</option>
          <option value="failed">Failed</option>
        </select>

        <select
          value={modelFilter}
          onChange={(e) => {
            setModelFilter(e.target.value);
            setPage(1);
          }}
          className="rounded-lg border border-xai-border bg-xai-card px-3 py-2 text-sm text-white focus:border-xai-primary focus:outline-none"
        >
          <option value="">All Models</option>
          {models?.map((model) => (
            <option key={model.modelName} value={model.modelName}>
              {model.modelName}
            </option>
          ))}
        </select>

        {(statusFilter || modelFilter) && (
          <button
            onClick={() => {
              setStatusFilter('');
              setModelFilter('');
              setPage(1);
            }}
            className="text-sm text-xai-primary hover:underline"
          >
            Clear Filters
          </button>
        )}
      </div>

      {/* Tasks Table */}
      <Card padding="none">
        {isLoading ? (
          <div className="p-8">
            <Loading message="Loading AI tasks..." />
          </div>
        ) : error ? (
          <div className="p-8 text-center text-red-400">
            Failed to load AI tasks. Please try again.
          </div>
        ) : (
          <>
            <Table>
              <TableHeader>
                <TableHead>Task ID</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Model</TableHead>
                <TableHead>Provider</TableHead>
                <TableHead align="center">Complexity</TableHead>
                <TableHead align="center">Status</TableHead>
                <TableHead align="right">Cost</TableHead>
                <TableHead align="right">Time</TableHead>
              </TableHeader>
              <TableBody>
                {data?.tasks.map((task) => (
                  <TableRow
                    key={task.taskId}
                    onClick={() => navigate(`/ai/${task.taskId}`)}
                  >
                    <TableCell>
                      <Link
                        to={`/ai/${task.taskId}`}
                        className="text-xai-primary hover:underline font-mono text-sm"
                        onClick={(e) => e.stopPropagation()}
                      >
                        {task.taskId.slice(0, 12)}...
                      </Link>
                    </TableCell>
                    <TableCell className="text-xai-muted capitalize">
                      {task.taskType.replace('_', ' ')}
                    </TableCell>
                    <TableCell className="text-white">
                      {task.aiModel}
                    </TableCell>
                    <TableCell>
                      <AddressLink address={task.providerAddress} />
                    </TableCell>
                    <TableCell align="center">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${getComplexityColor(task.complexity)}`}>
                        {task.complexity}
                      </span>
                    </TableCell>
                    <TableCell align="center">
                      <Badge variant={getStatusVariant(task.status)}>
                        {task.status.replace('_', ' ')}
                      </Badge>
                    </TableCell>
                    <TableCell align="right" className="text-white font-medium">
                      {formatXAI(task.actualCost || task.costEstimate)}
                    </TableCell>
                    <TableCell align="right" className="text-xai-muted">
                      {task.computeTimeSeconds
                        ? formatDuration(task.computeTimeSeconds)
                        : formatTimeAgo(task.createdAt)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>

            <div className="p-4 border-t border-xai-border">
              <Pagination
                currentPage={page}
                totalPages={totalPages}
                onPageChange={setPage}
              />
            </div>
          </>
        )}
      </Card>

      {/* Model Stats */}
      {models && models.length > 0 && (
        <Card>
          <CardHeader
            title="AI Model Performance"
            subtitle="Compare models by tasks, success rate, and cost"
          />
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {models.map((model) => (
              <div
                key={model.modelName}
                className="p-4 rounded-lg bg-xai-dark border border-xai-border"
              >
                <div className="flex items-center justify-between mb-3">
                  <h4 className="font-medium text-white">{model.modelName}</h4>
                  <Badge variant="info">{model.provider}</Badge>
                </div>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-xai-muted">Total Tasks</span>
                    <span className="text-white">{formatNumber(model.totalTasks)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-xai-muted">Success Rate</span>
                    <span className={model.successRate >= 95 ? 'text-green-400' : 'text-yellow-400'}>
                      {model.successRate.toFixed(1)}%
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-xai-muted">Avg Cost</span>
                    <span className="text-white">{formatXAI(model.averageCost)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-xai-muted">Quality Score</span>
                    <span className="text-xai-primary">{model.qualityScore.toFixed(1)}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
