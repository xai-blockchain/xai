import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Cpu, ChevronLeft, Clock, DollarSign, Zap, CheckCircle } from 'lucide-react';
import { Card, CardHeader } from '../components/Card';
import { Badge, getStatusVariant } from '../components/Badge';
import { AddressLink } from '../components/HashLink';
import { CopyButton } from '../components/CopyButton';
import { Loading } from '../components/Loading';
import { getAITask } from '../api/client';
import { formatDate, formatTimeAgo, formatXAI, formatDuration, formatNumber, getComplexityColor } from '../utils/format';

export function AITaskDetail() {
  const { taskId } = useParams<{ taskId: string }>();

  const { data: task, isLoading, error } = useQuery({
    queryKey: ['aiTask', taskId],
    queryFn: () => getAITask(taskId!),
    enabled: !!taskId,
    refetchInterval: 10000, // Refresh frequently for in-progress tasks
  });

  if (isLoading) {
    return <Loading message="Loading AI task..." />;
  }

  if (error || !task) {
    return (
      <div className="text-center py-12">
        <Cpu className="h-16 w-16 text-xai-muted mx-auto mb-4" />
        <h2 className="text-xl font-semibold text-white mb-2">AI Task Not Found</h2>
        <p className="text-xai-muted mb-6">
          The AI task you're looking for doesn't exist.
        </p>
        <Link
          to="/ai"
          className="inline-flex items-center gap-2 px-4 py-2 bg-xai-primary text-black rounded-lg font-medium hover:bg-xai-secondary transition-colors"
        >
          <ChevronLeft className="h-4 w-4" />
          Back to AI Tasks
        </Link>
      </div>
    );
  }

  const details = [
    {
      label: 'Task ID',
      value: (
        <span className="flex items-center gap-2">
          <span className="font-mono text-sm break-all">{task.taskId}</span>
          <CopyButton text={task.taskId} />
        </span>
      ),
    },
    {
      label: 'Status',
      value: (
        <Badge variant={getStatusVariant(task.status)}>
          {task.status.replace('_', ' ')}
        </Badge>
      ),
    },
    {
      label: 'Task Type',
      value: <span className="capitalize">{task.taskType.replace('_', ' ')}</span>,
    },
    {
      label: 'Complexity',
      value: (
        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${getComplexityColor(task.complexity)}`}>
          {task.complexity}
        </span>
      ),
    },
    {
      label: 'AI Model',
      value: <span className="text-xai-primary font-medium">{task.aiModel}</span>,
    },
    {
      label: 'Provider',
      value: <AddressLink address={task.providerAddress} truncate={false} showCopy />,
    },
    ...(task.requesterAddress ? [{
      label: 'Requester',
      value: <AddressLink address={task.requesterAddress} truncate={false} showCopy />,
    }] : []),
    { label: 'Created', value: `${formatDate(task.createdAt)} (${formatTimeAgo(task.createdAt)})` },
    ...(task.completedAt ? [{
      label: 'Completed',
      value: `${formatDate(task.completedAt)} (${formatTimeAgo(task.completedAt)})`,
    }] : []),
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-xai-primary/10">
            <Cpu className="h-5 w-5 text-xai-primary" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">AI Task Details</h1>
            <p className="text-sm text-xai-muted font-mono">
              {task.taskId.slice(0, 16)}...
            </p>
          </div>
        </div>

        <Link
          to="/ai"
          className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm bg-xai-card text-white hover:bg-xai-border transition-colors"
        >
          <ChevronLeft className="h-4 w-4" />
          Back to Tasks
        </Link>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="rounded-xl border border-xai-border bg-xai-card p-4">
          <div className="flex items-center gap-2 text-xai-muted mb-2">
            <DollarSign className="h-4 w-4" />
            <span className="text-sm">Cost</span>
          </div>
          <p className="text-xl font-semibold text-white">
            {formatXAI(task.actualCost || task.costEstimate)}
          </p>
          {task.actualCost && task.costEstimate !== task.actualCost && (
            <p className="text-xs text-xai-muted mt-1">
              Est: {formatXAI(task.costEstimate)}
            </p>
          )}
        </div>

        <div className="rounded-xl border border-xai-border bg-xai-card p-4">
          <div className="flex items-center gap-2 text-xai-muted mb-2">
            <Clock className="h-4 w-4" />
            <span className="text-sm">Compute Time</span>
          </div>
          <p className="text-xl font-semibold text-white">
            {task.computeTimeSeconds
              ? formatDuration(task.computeTimeSeconds)
              : 'In Progress'}
          </p>
        </div>

        <div className="rounded-xl border border-xai-border bg-xai-card p-4">
          <div className="flex items-center gap-2 text-xai-muted mb-2">
            <Zap className="h-4 w-4" />
            <span className="text-sm">Tokens</span>
          </div>
          <p className="text-xl font-semibold text-white">
            {formatNumber(task.resultData?.actual_tokens as number || task.resultData?.estimated_tokens as number || 0)}
          </p>
        </div>

        <div className="rounded-xl border border-xai-border bg-xai-card p-4">
          <div className="flex items-center gap-2 text-xai-muted mb-2">
            <CheckCircle className="h-4 w-4" />
            <span className="text-sm">Status</span>
          </div>
          <Badge variant={getStatusVariant(task.status)} className="text-sm">
            {task.status.replace('_', ' ')}
          </Badge>
        </div>
      </div>

      {/* Task Details */}
      <Card>
        <CardHeader title="Task Information" />
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

      {/* Result Data */}
      {task.resultData && Object.keys(task.resultData).length > 0 && (
        <Card>
          <CardHeader
            title="Result Data"
            subtitle="Output from AI compute task"
          />
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {Object.entries(task.resultData).map(([key, value]) => (
              <div key={key} className="p-3 rounded-lg bg-xai-dark">
                <p className="text-xai-muted text-sm capitalize">
                  {key.replace(/_/g, ' ')}
                </p>
                <p className="text-white font-medium mt-1">
                  {typeof value === 'number'
                    ? value.toLocaleString()
                    : String(value)}
                </p>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Result Hash */}
      {task.resultHash && (
        <Card>
          <CardHeader
            title="Result Hash"
            subtitle="Cryptographic hash of the task result"
          />
          <div className="flex items-center gap-2 p-3 rounded-lg bg-xai-dark">
            <code className="font-mono text-sm text-xai-primary break-all">
              {task.resultHash}
            </code>
            <CopyButton text={task.resultHash} />
          </div>
        </Card>
      )}

      {/* Progress indicator for in-progress tasks */}
      {(task.status === 'pending' || task.status === 'in_progress') && (
        <Card>
          <div className="text-center py-8">
            <div className="animate-pulse">
              <Cpu className="h-12 w-12 text-xai-primary mx-auto mb-4" />
              <h3 className="text-lg font-medium text-white mb-2">
                Task {task.status === 'pending' ? 'Pending' : 'In Progress'}
              </h3>
              <p className="text-xai-muted">
                {task.status === 'pending'
                  ? 'Waiting for a compute provider to pick up this task...'
                  : 'AI model is processing your request...'}
              </p>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}
